import requests
import json

class HttpClient:
    def __init__(self, ip):
        ''''''
        self.ip = ip
    
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

    async def test(self, test_items):
        return True
