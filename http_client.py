import requests
import json
import asyncio
from typing import Dict, Optional, List
from time import sleep

class HttpClient:
    def __init__(self, ip):
        ''''''
        self.ip = ip
        self.test_handle = {
            'G28': self.G28_test,
        }
    
    def send_gcode(self, gcode: str):
        headers = {"Content-Type": "application/json"}
        payload = {"script": gcode}
        try:
            url = f"http://{self.ip}/api/laser/gcode/script"
            res = requests.post(url, json=payload, headers=headers, timeout=15)
            status = "成功" if res.status_code == 200 else f"失败({res.status_code})"
            log = f"[{self.ip}] JSON发送指令 → {status}\n"
            data = res.json()
            return data.get('result')
        except Exception as e:
            print(f"[{self.ip}] 发送失败：{str(e)}\n")
        print(log)

    async def G28_test(self, index, gcode:str):
        print(f'{self.ip}: test g28')
        await asyncio.sleep(1)
        print(f'{self.ip}: test complete')
        if self.ip == '172.16.22.126':
            return [index, True, 'ok']
        else:
            return [index, False, 'ok']
        # self.send_gcode(gcode)

    async def dummy_test(self, index, gcode:str):
        print(f'{self.ip}: dummy_test')
        await asyncio.sleep(0.5)
        print(f'{self.ip}: test complete')
        return [index, True, 'ok']

    async def test(self, test_items:Dict[str, Dict[str, str]], callback):
        for i, test in enumerate(test_items.values()):
            gcode = test.get('gcode')
            if not gcode:
                func = self.dummy_test
            else:
                print(gcode)
                gcode_cmd = gcode.split(' ')[0]
                if gcode_cmd in self.test_handle:
                    func = self.test_handle.get(gcode_cmd)
            result = await func(i, gcode)
            callback(self.ip, result)
        return True
