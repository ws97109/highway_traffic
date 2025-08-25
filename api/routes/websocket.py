from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio
from datetime import datetime

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # 如果連接已斷開，從列表中移除
                self.active_connections.remove(connection)

manager = ConnectionManager()

@router.websocket("/traffic")
async def websocket_traffic_updates(websocket: WebSocket):
    """提供即時交通資料更新的 WebSocket 端點"""
    await manager.connect(websocket)
    try:
        while True:
            # 模擬發送即時交通資料
            traffic_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "traffic_update",
                "data": {
                    "location": "國道1號 台北-桃園",
                    "speed": 45,
                    "density": 85,
                    "flow": 1200,
                    "status": "壅塞"
                }
            }
            await manager.send_personal_message(json.dumps(traffic_data), websocket)
            await asyncio.sleep(30)  # 每30秒更新一次
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.websocket("/shockwave")
async def websocket_shockwave_alerts(websocket: WebSocket):
    """提供即時震波警報的 WebSocket 端點"""
    await manager.connect(websocket)
    try:
        while True:
            # 模擬發送震波警報
            shockwave_alert = {
                "timestamp": datetime.now().isoformat(),
                "type": "shockwave_alert",
                "data": {
                    "id": "sw_001",
                    "location": "國道1號 台北-桃園",
                    "intensity": 7.2,
                    "propagation_speed": 22.5,
                    "estimated_arrival": "2025-01-27T15:30:00Z",
                    "severity": "moderate"
                }
            }
            await manager.send_personal_message(json.dumps(shockwave_alert), websocket)
            await asyncio.sleep(60)  # 每分鐘檢查一次
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.websocket("/system")
async def websocket_system_status(websocket: WebSocket):
    """提供系統狀態更新的 WebSocket 端點"""
    await manager.connect(websocket)
    try:
        while True:
            # 模擬發送系統狀態
            system_status = {
                "timestamp": datetime.now().isoformat(),
                "type": "system_status",
                "data": {
                    "api_status": "healthy",
                    "active_connections": len(manager.active_connections),
                    "processed_requests": 12580,
                    "uptime": "99.8%",
                    "response_time": "120ms"
                }
            }
            await manager.send_personal_message(json.dumps(system_status), websocket)
            await asyncio.sleep(10)  # 每10秒更新系統狀態
    except WebSocketDisconnect:
        manager.disconnect(websocket)
