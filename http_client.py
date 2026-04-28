import requests
import json
import asyncio
from typing import Dict, Optional, List
from time import sleep
import websockets
from result_analizer import TemplateParser

class HttpClient:
    def __init__(self, ip):
        ''''''
        self.ip = ip
        self.test_handle = {
            'G28': self.G28_test,
            'TEST_ENCODER': self.test_encoder,
            'ENCODER_GET_COUNTER': self.encoder_get_count,
            'AUTO_HOME_TUNE': self.auto_home_turn,
            'TEST_HOME': self.test_home,
            'TEST_XY_SPEED': self.test_xy_speed,
            'TEST_RESONANCES': self.test_resonances,
            'TEST_XY_RANGE': self.tst_xy_range,
            'ENCODER_TEST': self.encoder_test,
            'TEST_XY_SPEED': self.test_xy_speed,
            'TEST_XY_SPEED_HYBRID': self.test_xy_speed_hybrid
        }
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_connected: bool = False
        self.ws_url = f"ws://{self.ip}/websocket"  # 根据你设备实际ws路径修改
        self.ws_msg_list: List = []

    async def ws_connect(self):
        """建立websocket长连接"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.ws_connected = True
            print(f"[{self.ip}] WebSocket 连接成功")
            # 后台持续监听消息
            asyncio.create_task(self._ws_listen())
            return True
        except Exception as e:
            print(f"[{self.ip}] WebSocket 连接失败: {e}")
            self.ws_connected = False
            return False

    async def ws_disconnect(self):
        """断开websocket"""
        if self.ws:
            await self.ws.close()
            self.ws_connected = False
            print(f"[{self.ip}] WebSocket 已断开")

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
        """内部循环：持续接收设备推送数据"""
        while self.ws_connected and self.ws:
            try:
                recv_text = await self.ws.recv()
                recv_data = json.loads(recv_text)
                # 这里写你自定义的消息解析逻辑
                self.on_ws_message(recv_data)
            except websockets.exceptions.ConnectionClosed:
                print(f"[{self.ip}] WebSocket 连接断开")
                self.ws_connected = False
                break
            except Exception as e:
                print(f"[{self.ip}] WS接收异常: {e}")
                await asyncio.sleep(0.5)

    def on_ws_message(self, data:dict):
        """收到设备WS消息回调，自行扩展业务"""
        if data.get('method') == 'push.gcode_response':
            print(f"[{self.ip}] WS收到数据: {data.get('params')}")
            self.ws_msg_list.append(data)

    def get_ws_messages(self) -> List:
        """
        获取当前存储的所有WS接收消息
        :return: 消息字典列表
        """
        return self.ws_msg_list.copy()

    def clear_ws_messages(self):
        """清空WS消息缓存"""
        self.ws_msg_list.clear()

    def send_gcode(self, gcode: str, timeout):
        headers = {"Content-Type": "application/json"}
        payload = {"script": gcode}
        try:
            url = f"http://{self.ip}/api/laser/gcode/script"
            res = requests.post(url, json=payload, headers=headers, timeout=timeout)
            status = "成功" if res.status_code == 200 else f"失败({res.status_code})"
            log = f"[{self.ip}] JSON发送指令 → {status}\n"
            data = res.json()
            return data.get('result')
        except Exception as e:
            print(f"[{self.ip}] 发送失败：{str(e)}\n")
        print(log)

    def parse_result(self, logs: List[str], template: str):
        paser = TemplateParser(template)
        for l in logs:
            result = paser.parse(l)
            if result:
                return result

    async def G28_test(self, index, gcode:str, test_item):
        print(f'{self.ip}: test g28')
        await asyncio.sleep(1)
        print(f'{self.ip}: test complete')
        if self.ip == '172.16.22.126':
            return [index, True, 'ok']
        else:
            return [index, False, 'ok']
        # self.send_gcode(gcode)


    async def test_encoder(self, index, gcode:str, test_item):
        ''''''
        self.send_gcode(gcode, 5*60)
        result_x = self.parse_result(self.ws_msg_list, 'X axis: max diff = {(max_diff_x or 0.0):.03f}').get('max_diff_x', 100)
        result_y = self.parse_result(self.ws_msg_list, 'Y axis: max diff = {(max_diff_y or 0.0):.03f}').get('max_diff_y', 100)
        try:
            maxx, maxy = test_item.get('标准').split(',')
            if result_x > maxx or result_y > maxy:
                result = False
            else:
                result = True
        except:
            raise '标准不对'
        return [index, result, 'ok']
    
    async def encoder_get_count(self, index, gcode:str):
        self.send_gcode(gcode, 5*60)
        return [index, 'Manual', 'ok']

    async def auto_home_turn(self, index, gcode:str):
        ''''''
        return [index, True, 'ok']

    async def test_home(self, index, gcode:str, test_item):
        ''''''
        self.send_gcode(gcode, 5*60)
        result_x = self.parse_result(self.ws_msg_list, 'X: Range={x_range:.3f} mm, Min={x_min:.3f}, Max={x_max:.3f}').get('x_range', 100)
        result_y = self.parse_result(self.ws_msg_list, 'Y: Range={y_range:.3f} mm, Min={y_min:.3f}, Max={y_max:.3f}').get('y_range', 100)
        try:
            maxx, maxy = test_item.get('标准').split(',')
            if result_x > maxx or result_y > maxy:
                result = False
            else:
                result = True
        except:
            raise '标准不对'
        return [index, result, 'ok']

    async def test_xy_speed(self, index, gcode:str, test_item):
        ''''''
        # self.send_gcode(gcode, 5*60)
        # parse_result = self.parse_result(self.ws_msg_list, "Accel (mm/s²)':<20} {'Max Speed (mm/s)':<20")
        # acc = parse_result.get('max_x_deviation', 100)
        # max_speed = parse_result.get('max_y_deviation', 100)
        # try:
        #     maxx, maxy = test_item.get('标准').split(',')
        #     if result_x > maxx or result_y > maxy:
        #         result = False
        #     else:
        #         result = True
        # except:
        #     raise '标准不对'
        return [index, True, 'ok']

    async def test_resonances(self, index, gcode:str, test_item):
        ''''''
        return [index, True, 'ok']

    async def tst_xy_range(self, index, gcode:str, test_item):
        ''''''
        return [index, True, 'ok']

    async def encoder_test(self, index, gcode:str, test_item):
        ''''''
        self.send_gcode(gcode, 5*60)
        parse_result = self.parse_result(self.ws_msg_list, 'max x deviation: {max_x_deviation:.03f}, max y deviation: {max_y_deviation:.03f}')
        result_x = parse_result.get('max_x_deviation', 100)
        result_y = parse_result.get('max_y_deviation', 100)
        try:
            maxx, maxy = test_item.get('标准').split(',')
            if result_x > maxx or result_y > maxy:
                result = False
            else:
                result = True
        except:
            raise '标准不对'
        return [index, result, 'ok']

    async def test_xy_speed(self, index, gcode:str, test_item):
        ''''''
        return [index, True, 'ok']

    async def test_xy_speed_hybrid(self, index, gcode:str, test_item):
        ''''''
        return [index, True, 'ok']

    async def dummy_test(self, index, gcode:str, test_item):
        print(f'{self.ip}: dummy_test')
        await asyncio.sleep(0.5)
        print(f'{self.ip}: test complete')
        return [index, True, 'ok']

    async def test(self, test_items:Dict[str, Dict[str, str]], callback):
        await self.ws_connect()
        for i, test in enumerate(test_items.values()):
            gcode = test.get('gcode')
            if not gcode:
                func = self.dummy_test
            else:
                print(gcode)
                gcode_cmd = gcode.split(' ')[0]
                if gcode_cmd in self.test_handle:
                    func = self.test_handle.get(gcode_cmd)
            result = await func(i, gcode, test)
            if callback(self.ip, result) == False:
                await self.ws_disconnect()
                return False
        await self.ws_disconnect()
        return True
