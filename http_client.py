import json
import asyncio
from typing import Dict, Optional, List
from time import sleep
import websockets
from result_analizer import TemplateParser
from websockets.exceptions import ConnectionClosed
import aiohttp

class HttpClient:
    def __init__(self, ip):
        ''''''
        self.ip = ip
        self.test_handle = {
            'SYS_MODE': self.sys_mode,
            'WIFI_INFO': self.wifi_info,
            'G28': self.G28_test,
            'TEST_ENCODER': self.test_encoder,
            # 'ENCODER_GET_COUNTER': self.encoder_get_count,
            'AUTO_HOME_TUNE': self.auto_home_turn,
            'TEST_HOME': self.test_home,
            'TEST_RESONANCES': self.test_resonances,
            'TEST_XY_RANGE': self.tst_xy_range,
            'ENCODER_TEST': self.encoder_test,
            'TEST_XY_SPEED': self.test_xy_speed,
            'TEST_XY_SPEED_HYBRID': self.test_xy_speed_hybrid
        }
        self.mac = 'Unknow'
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_connected: bool = False
        self.ws_url = f"ws://{self.ip}/websocket"  # 根据你设备实际ws路径修改
        self.ws_msg_list: List = []
        self._listen_task: Optional[asyncio.Task] = None
        self._http_session: Optional[aiohttp.ClientSession] = None
        self.msg_in_waiting = ""
        self.wait_result = None
        self.error_handler = None
        self.ws_connected = False

    async def _get_http_session(self) -> aiohttp.ClientSession:
        """懒创建全局http会话"""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def close(self):
        """程序退出时统一释放资源"""
        await self.ws_disconnect()
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    async def ws_connect(self):
        """建立连接 + 启动监听"""
        try:
            # 先彻底清理旧连接（必须！）
            await self.ws_disconnect()

            # 新建连接
            self.ws = await websockets.connect(
                self.ws_url,
                ping_interval=25,  # 避免自动断开
                ping_timeout=10
            )
            self.ws_connected = True
            print(f"[{self.ip}] WebSocket 连接成功")

            # 启动监听（必须最后开！）
            self._listen_task = asyncio.create_task(self._ws_listen())
            return True
        except Exception as e:
            print(f"[{self.ip}] 连接失败: {e}")
            self.ws_connected = False
            return False

    async def ws_disconnect(self):
        """安全关闭：先停任务，再关连接"""
        # 1. 先标记断开
        self.ws_connected = False

        # 2. 取消监听任务（最关键）
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        # 3. 关闭 WebSocket
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None

        print(f"[{self.ip}] WebSocket 已安全关闭")

    async def ws_send_msg(self, data: dict):
        """通过websocket发送JSON消息"""
        if not self.ws_connected or not self.ws:
            print(f"[{self.ip}] WebSocket未连接，发送失败")
            return False
        try:
            msg = json.dumps(data)
            await self.ws.send(msg)
            return True
        except Exception as e:
            print(f"[{self.ip}] WS发送消息异常: {e}")
            self.ws_connected = False
            return False

    async def _ws_listen(self):
        """后台持续收消息（永远不会丢、不会卡住）"""
        print(f"[{self.ip}] 开始监听消息")
        while self.ws_connected:
            try:
                # 收消息
                recv_text = await self.ws.recv()
                data = json.loads(recv_text)
                self.on_ws_message(data)  # 你的消息处理

            except ConnectionClosed:
                print(f"[{self.ip}] 连接被服务器关闭")
                # if self.error_handler is not None:
                #     self.error_handler(self.ip, '连接已断开')
                break

            except asyncio.CancelledError:
                # 正常退出
                return

            except Exception as e:
                print(f"[{self.ip}] 接收异常: {e}")
                await asyncio.sleep(0.1)

        self.ws_connected = False

    def on_ws_message(self, data:dict):
        """收到设备WS消息回调，自行扩展业务"""
        if data.get('method') == 'push.gcode_response':
            new_msg = data.get('params')[0]
            print(f"[{self.ip}] WS收到数据: {new_msg}")
            self.ws_msg_list.append(new_msg)
            if self.msg_in_waiting:
                if self.msg_in_waiting in new_msg:
                    self.wait_result = new_msg

    async def wait_ws_message(self, msg_to_wait:str, timeout):
        self.msg_in_waiting = msg_to_wait
        self.wait_result = None 
        start_time = asyncio.get_event_loop().time()
        while True:
            if self.wait_result:
                return self.wait_result
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                print(f"[{self.ip}] 等待WS消息超时: {msg_to_wait}")
                return self.wait_result
            await asyncio.sleep(0.02)

    def get_ws_messages(self) -> List:
        """
        获取当前存储的所有WS接收消息
        :return: 消息字典列表
        """
        return self.ws_msg_list.copy()

    def clear_ws_messages(self):
        """清空WS消息缓存"""
        self.ws_msg_list.clear()

    async def send_gcode_safe(self, gcode: str, timeout: int = 30):
        """纯异步HTTP，不阻塞事件循环，替代原requests"""
        headers = {"Content-Type": "application/json"}
        payload = {"script": gcode}
        url = f"http://{self.ip}/api/laser/gcode/script"
        try:
            session = await self._get_http_session()
            timeout_ctx = aiohttp.ClientTimeout(total=timeout)
            print(f'Json发送 [{gcode}]')
            async with session.post(url, json=payload, headers=headers, timeout=timeout_ctx) as res:
                # 关键：必须读取响应体，清空buffer
                text = await res.text()
                status = "成功" if res.status == 200 else f"失败({res.status})"
                log = f"[{self.ip}] JSON发送指令 → {status}"
                print(log)
                return True
        except Exception as e:
            print(f"[{self.ip}] 发送失败：{str(e)}")
            return False

    def parse_result(self, logs: List[str], template: str):
        paser = TemplateParser(template)
        for l in reversed(logs):
            result = paser.parse(l)
            if result:
                return result
        return {}
    
    async def sys_mode(self, index, gcode:str, test_item):
        await self.send_gcode_safe(gcode, 300)
        await asyncio.sleep(5)
        # retry = 20
        # result = False
        # while retry :
        #     if await self.send_gcode_safe('G90', 2) == True:
        #         result = True
        #         break
        #     retry = retry - 1
        result = await self.wait_ws_message('Machine is ready for operation.\n', 50)
        await asyncio.sleep(5)
        return [index, result, 'ok']

    async def wifi_info(self, index, gcode:str, test_item):
        await self.send_gcode_safe('SET_PIN PIN=th_fan value=0', 10)
        await self.send_gcode_safe('SET_PIN PIN=qcs_fan value=0', 10)
        await self.send_gcode_safe(gcode, 10)
        result = await self.wait_ws_message('SSID', 20)
        if result:
            mac_pos = result.find('MAC:')
            if mac_pos > 0:
                self.mac = result[mac_pos:mac_pos+21].replace(':', '_')
        await asyncio.sleep(0.2)
        return [index, True, self.mac]

    async def G28_test(self, index, gcode:str, test_item):
        print(f'{self.ip}: test g28')
        await asyncio.sleep(0.2)
        print(f'{self.ip}: test complete')
        if self.ip == '172.16.22.126':
            return [index, True, 'ok']
        else:
            return [index, False, 'ok']
        # self.send_gcode(gcode)


    async def test_encoder(self, index, gcode:str, test_item):
        ''''''
        await self.send_gcode_safe(gcode, 5*60)
        await asyncio.sleep(0.2)
        result_x = self.parse_result(self.ws_msg_list, 'X axis: max diff = {max_diff_x}').get('max_diff_x', 100)
        result_y = self.parse_result(self.ws_msg_list, 'Y axis: max diff = {max_diff_y}').get('max_diff_y', 100)
        try:
            maxx, maxy = test_item.get('标准').split(';')
            maxx = float(maxx.split(':')[1])
            maxy = float(maxy.split(':')[1])
            if result_x > maxx or result_y > maxy:
                result = False
            else:
                result = True
        except:
            raise ValueError('标准不对')
        return [index, result, f'maxx:{result_x:0.3f}, maxy:{result_y:0.3f}']
    
    async def encoder_get_count(self, index, gcode:str, test_item):
        await self.send_gcode_safe(gcode, 5*60)
        await asyncio.sleep(0.2)
        return [index, 'Manual', 'ok']

    async def auto_home_turn(self, index, gcode:str, test_item):
        ''''''
        await self.send_gcode_safe(gcode, 10*60)
        await asyncio.sleep(0.2)
        return [index, True, 'ok']

    async def test_home(self, index, gcode:str, test_item):
        ''''''
        await self.send_gcode_safe(gcode, 10*60)
        await asyncio.sleep(0.2)
        result_x = self.parse_result(self.ws_msg_list, 'X: Range={x_range} mm, Min={x_min}, Max={x_max}').get('x_range', 100)
        result_y = self.parse_result(self.ws_msg_list, 'Y: Range={y_range} mm, Min={y_min}, Max={y_max}').get('y_range', 100)
        try:
            maxx, maxy = test_item.get('标准').split(';')
            maxx = float(maxx.split(':')[1])
            maxy = float(maxy.split(':')[1])
            if result_x > maxx or result_y > maxy:
                result = False
            else:
                result = True
        except:
            raise ValueError('标准不对')
        return [index, result, f'x:{result_x:0.3f}, y:{result_y:0.3f}']

    async def test_resonances(self, index, gcode:str, test_item):
        ''''''
        # await self.send_gcode_safe('SET_PIN PIN=TH_FAN value=0', 10)
        await self.send_gcode_safe('G28', 5 * 60)
        await asyncio.sleep(0.2)
        await self.send_gcode_safe(gcode, 10 * 60)
        await self.wait_ws_message('Resonances data written to', 20)
        await asyncio.sleep(0.2)
        # await self.send_gcode_safe('SET_PIN PIN=TH_FAN value=1', 10)
        return [index, True, 'ok']

    async def tst_xy_range(self, index, gcode:str, test_item):
        ''''''
        await self.send_gcode_safe(gcode, 10*60)
        await asyncio.sleep(0.2)
        max_y0 = self.parse_result(self.ws_msg_list, 'Side 1/4 - {RESULT} - Expected: {expected} mm, Detected: {Detected} mm').get('Detected', 100)
        max_x0 = self.parse_result(self.ws_msg_list, 'Side 2/4 - {RESULT} - Expected: {expected} mm, Detected: {Detected} mm').get('Detected', 100)
        max_y1 = self.parse_result(self.ws_msg_list, 'Side 3/4 - {RESULT} - Expected: {expected} mm, Detected: {Detected} mm').get('Detected', 100)
        max_x1 = self.parse_result(self.ws_msg_list, 'Side 4/4 - {RESULT} - Expected: {expected} mm, Detected: {Detected} mm').get('Detected', 100)
        result = False
        for l in self.ws_msg_list:
            if l == 'OVERALL RESULT: PASS - All corners within tolerance\n':
                result = True
                break
        return [index, result, f'x:{max_x0} {max_x1},y:{max_y0} {max_y1}']

    async def encoder_test(self, index, gcode:str, test_item):
        ''''''
        await self.send_gcode_safe(gcode, 13*60)
        await asyncio.sleep(0.5)
        parse_result = self.parse_result(self.ws_msg_list, 'max x deviation: {max_x_deviation:.03f}, max y deviation: {max_y_deviation:.03f}')
        result_x = parse_result.get('max_x_deviation', 100)
        result_y = parse_result.get('max_y_deviation', 100)
        try:
            maxx, maxy = test_item.get('标准').split(';')
            maxx = float(maxx.split(':')[1])
            maxy = float(maxy.split(':')[1])
            if result_x > maxx or result_y > maxy:
                result = False
            else:
                result = True
        except:
            raise ValueError('标准不对')
        return [index, result, f'x:{result_x:0.3f}, y:{result_y:0.3f}']

    async def test_xy_speed(self, index, gcode:str, test_item):
        ''''''
        await self.send_gcode_safe(gcode, 20*60)
        await asyncio.sleep(1)
        # test_result = self.ws_msg_list[-10:-1]
        # test_result.reverse()
        # try:
        #     print(test_result[0].split())
        #     accel, speed = test_result[0].split()
        #     accel = int(accel)
        #     speed = int(speed)
        #     max_acc, max_v = test_item.get('标准').split(';')
        #     maxaccel = float(max_acc.split(':')[1])
        #     maxspeed = float(max_v.split(':')[1])
        #     if accel >= maxaccel and speed >= maxspeed:
        #         result = True
        #     else:
        #         result = False
        # except Exception as e:
        #     result = False
        #     accel = 0
        #     speed = 0
        #     print(f'Test speed error: {e}')
        # return [index, result, f'Acc:{accel} Speed:{speed}']
        return [index, 'Manual', 'ok']

    async def test_xy_speed_hybrid(self, index, gcode:str, test_item):
        ''''''
        await self.send_gcode_safe(gcode, 30*60)
        print('hybrid 测试结束')
        await asyncio.sleep(0.5)
        # test_result = self.ws_msg_list[-10:-1]
        # test_result.reverse()
        # try:
        #     print(test_result[0].split())
        #     accel, speed = test_result[0].split()
        #     accel = int(accel)
        #     speed = int(speed)
        #     max_acc, max_v = test_item.get('标准').split(';')
        #     maxaccel = float(max_acc.split(':')[1])
        #     maxspeed = float(max_v.split(':')[1])
        #     if accel >= maxaccel and speed >= maxspeed:
        #         result = True
        #     else:
        #         result = False
        # except Exception as e:
        #     result = False
        #     accel = 0
        #     speed = 0
        #     print(f'Test speed error: {e}')
        # return [index, result, f'Acc:{accel} Speed:{speed}']
        return [index, 'Manual', 'ok']

    async def dummy_test(self, index, gcode:str, test_item):
        print(f'{self.ip}: dummy_test')
        await asyncio.sleep(0.2)
        print(f'{self.ip}: test complete')
        return [index, True, 'ok']
    
    async def run_gcode(self, gcode: str, timeout=3):
        ''''''
        if not self.ws_connected:
            await self.ws_connect()
        self.clear_ws_messages()
        await self.send_gcode_safe(gcode, timeout)
        await asyncio.sleep(0.5)
        res_msg = self.ws_msg_list
        await self.ws_disconnect()
        return res_msg

    async def test(self, test_items:Dict[str, Dict[str, str]], callback, error_callback):
        self.error_handler = error_callback
        for i, test in enumerate(test_items.values()):
            await asyncio.sleep(0.3)
            if not self.ws_connected:
                await self.ws_connect()
            self.clear_ws_messages()
            gcode = test.get('gcode')
            if not gcode:
                func = self.dummy_test
            else:
                gcode_cmd = gcode.split(' ')[0]
                print(f'测试项:{i}: {gcode_cmd}')
                if gcode_cmd in self.test_handle:
                    func = self.test_handle.get(gcode_cmd)
            result = await func(i, gcode, test)
            if callback(self.ip, result) == False:
                await self.ws_disconnect()
                return False, self.mac, self.ip
        await self.ws_disconnect()
        return True, self.mac, self.ip
