import serial
import serial.tools.list_ports
import threading
from threading import Lock
import time, re
from typing import Optional, List, Callable, Dict, Any

class SerialPort:
    def __init__(self):
        self.ser: Optional[serial.Serial] = None
        self.recv_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.recv_callback: Optional[Callable[[bytes], None]] = None
        # 新增：串口异常断开回调，交给UI处理按钮状态
        self.disconnect_callback: Optional[Callable[[], None]] = None
        self.wait_string_lock = Lock()
        self.recv_buff: str = ''
        self.wait_complete = None

    # 获取所有串口
    def get_all_com_ports(self) -> List[str]:
        port_list = serial.tools.list_ports.comports()
        ports = []
        for port in port_list:
            ports.append(port.device)
        return ports

    # 打开串口
    def open_port(self, port_name: str, baudrate: int = 115200, timeout: float = 0.1) -> bool:
        if self.ser and self.ser.is_open:
            self.close_port()
        try:
            self.ser = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                timeout=timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            self.is_running = True
            self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self.recv_thread.start()
            return True
        except Exception as e:
            print(f"打开串口失败: {e}")
            self.ser = None
            return False

    # 关闭串口
    def close_port(self):
        self.is_running = False
        if self.recv_thread and self.recv_thread.is_alive() and threading.current_thread() != self.recv_thread:
            self.recv_thread.join(timeout=1)
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None

    # 发送字节
    def send_data(self, data: bytes) -> bool:
        if not (self.ser and self.ser.is_open):
            return False
        try:
            self.ser.write(data)
            return True
        except Exception as e:
            print(f"发送异常，断开串口: {e}")
            self._handle_error_disconnect()
            return False

    def send_str(self, text: str) -> bool:
        return self.send_data(text.encode("utf-8"))
    
    def wait_reack(self, string_to_wait):
        self.wait_complete = WaitCompletion()
        self.string_to_wait = string_to_wait
        result = self.wait_complete.wait(2, None)
        self.wait_complete = None
        return result

    def on_data_arrive(self, recv_bytes: bytes):
        if recv_bytes and self.recv_callback:
            self.recv_callback(recv_bytes)
        self.recv_buff += recv_bytes.decode()
        if '\n' not in self.recv_buff:
            return
        line, self.recv_buff = self.recv_buff.split('\n', 1)
        if self.wait_complete is not None:
            print(line)
            print(self.string_to_wait)
            if self.string_to_wait in line:
                self.wait_complete.complete(line)

    # 接收循环
    def _recv_loop(self):
        while self.is_running and self.ser and self.ser.is_open:
            try:
                recv_bytes = self.ser.read(self.ser.in_waiting or 1)
                self.on_data_arrive(recv_bytes)
                
            except Exception as e:
                print(f"串口接收异常，自动断开: {e}")
                self._handle_error_disconnect()
                break
            time.sleep(0.01)

    # 异常统一处理：关闭串口 + 触发UI回调
    def _handle_error_disconnect(self):
        self.close_port()
        if self.disconnect_callback:
            self.disconnect_callback()

class WaitCompletion:
    def __init__(self):
        self.lock = Lock()

    def wait(self, timeout=3, timeout_result=None):
        with self.lock:
            self.waiting = True
        start = time.time()
        while True:
            time_elpase = time.time() - start
            if time_elpase > timeout:
                return timeout_result
            time.sleep(0.01)
            if self.waiting == False:
                result = self.wait_result
                return result

    def complete(self, data = None):
        with self.lock:
            self.waiting = False
            self.wait_result = data


class SerialTester(SerialPort):
    def __init__(self):
        super().__init__()
        self.command_handler: dict = {
            'WIFI_CONNECT': self.wifi_connect,
            'WIFI_INFO': self.wifi_info,
            'BEEPER_START': self.beeper_start,
            'PD_TEST': self.pd_test,
            '$I': self.query_version,
        }
    
    def run_command(self, command:str, **kwargs):
        try:
            pfun = self.command_handler.get(command)
            if pfun is not None:
               return pfun(kwargs)
        except Exception as e:
            print(f'Run command fail: {e}')

    def wifi_connect(self, kwargs: Dict[str, Any]):
        ssid = kwargs.get('ssid', None)
        password = kwargs.get('password', None)
        if ssid is None or password is None:
            return
        self.send_str(f'WIFI_CONNECT SSID={ssid} PASSWORD={password}\n')
        res = self.wait_reack(f'set Wi-Fi success')
        return res is not None

    def wifi_info(self, param):
        self.send_str(f'WIFI_INFO\n')
        res = self.wait_reack(f'SSID')
        if res is not None:
            res = self.to_dict(res)
            return res.get('IP')
        return ''
    
    def query_version(self, param):
        self.send_str(f'$I\n')
        res = self.wait_reack(f'version')
        if res is not None:
            return res
        return ''
    
    def beeper_start(self, param):
        c = param.get('count')
        self.send_str(f'BEEPER_START H=0.2 L=0.2 C={c}')

    def pd_test(self, param):
        self.send_str(f'PD_TEST')

    def to_dict(self, data):
        pattern = r"(\w+):([^\s]+)"
        matches = re.findall(pattern, data)
        result = dict(matches)
        return result