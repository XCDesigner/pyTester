import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed

class WebSocketJsonClient:
    def __init__(self, ip):
        """
        构造函数
        :param ip: 服务器IP
        :param port: 端口，默认8765
        """
        self.uri = f"ws://{ip}/websocket"
        self.websocket = None

    async def connect(self):
        """建立连接"""
        self.websocket = await websockets.connect(self.uri)
        print(f"✅ 已连接到: {self.uri}")

    async def send(self, data: dict):
        """
        发送JSON数据
        :param data: 字典（会自动转JSON）
        """
        if not self.websocket:
            print("❌ 未连接，请先调用 connect()")
            return

        try:
            # 字典 → JSON字符串
            json_str = json.dumps(data, ensure_ascii=False)
            await self.websocket.send(json_str)
            print(f"📤 发送成功: {data}")
        except ConnectionClosed:
            print("❌ 连接已断开")
        except Exception as e:
            print(f"❌ 发送失败: {e}")

    async def receive(self):
        """阻塞等待接收消息"""
        if not self.websocket:
            return None
        try:
            msg = await self.websocket.recv()
            return json.loads(msg)
        except:
            return None

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 连接已关闭")