from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import json
import os
from typing import Optional, Dict, Any

router = APIRouter()

# Ollama 設定
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')

class ChatRequest(BaseModel):
    message: str
    traffic_data: Optional[Dict[str, Any]] = None
    shockwave_data: Optional[Dict[str, Any]] = None
    user_location: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    model: str
    timestamp: str

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ollama(request: ChatRequest):
    """直接與 Ollama 對話，分析交通數據並提供建議"""
    try:
        # 構建包含交通數據的提示
        system_prompt = """你是一個專業的交通分析助手，專門為台灣的駕駛者提供智能建議。
你會根據即時交通數據、震波預警和路況信息，提供實用的駕駛建議。
請用繁體中文回答，語氣要親切且專業。"""

        # 準備交通數據摘要
        traffic_summary = ""
        if request.traffic_data and request.traffic_data.get('stations'):
            stations = request.traffic_data['stations']
            total_stations = len(stations)
            avg_speed = sum(s.get('speed', 0) for s in stations) / total_stations if total_stations > 0 else 0
            traffic_summary += f"\n目前監測到 {total_stations} 個交通站點，平均車速 {avg_speed:.1f} km/h。"
            
            # 找出壅塞站點
            congested = [s for s in stations if s.get('speed', 100) < 50]
            if congested:
                traffic_summary += f"\n有 {len(congested)} 個站點出現壅塞（車速低於50km/h）。"

        if request.shockwave_data and request.shockwave_data.get('shockwaves'):
            shockwaves = request.shockwave_data['shockwaves']
            if shockwaves:
                traffic_summary += f"\n⚠️ 偵測到 {len(shockwaves)} 個交通震波事件。"

        # 用戶位置信息
        location_info = ""
        if request.user_location:
            location_info = f"\n用戶位置：緯度 {request.user_location.get('lat', '未知')}, 經度 {request.user_location.get('lng', '未知')}"

        # 完整提示
        full_prompt = f"""{system_prompt}

當前交通狀況：{traffic_summary}
{location_info}

用戶問題：{request.message}

請根據以上交通數據分析並提供建議。"""

        # 調用 Ollama API
        ollama_response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 500
                }
            },
            timeout=30
        )

        if not ollama_response.ok:
            raise HTTPException(status_code=500, detail=f"Ollama API 錯誤: {ollama_response.status_code}")

        ollama_data = ollama_response.json()
        ai_response = ollama_data.get('response', '抱歉，AI 助手暫時無法回應。')

        return ChatResponse(
            response=ai_response,
            model=OLLAMA_MODEL,
            timestamp=ollama_data.get('created_at', '')
        )

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="AI 回應超時，請稍後再試")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="無法連接到 AI 服務")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 對話失敗: {str(e)}")

@router.get("/advice")
async def get_traffic_advice(
    user_lat: float,
    user_lng: float,
    destination_lat: Optional[float] = None,
    destination_lng: Optional[float] = None
):
    """根據當前位置獲取交通建議"""
    try:
        # 獲取當前交通數據
        traffic_response = requests.get('http://localhost:8000/api/traffic/current', timeout=10)
        shockwave_response = requests.get('http://localhost:8000/api/shockwave/active', timeout=10)
        
        traffic_data = traffic_response.json() if traffic_response.ok else None
        shockwave_data = shockwave_response.json() if shockwave_response.ok else None

        # 構建分析請求
        if destination_lat and destination_lng:
            message = f"我要從目前位置（{user_lat}, {user_lng}）開車到目的地（{destination_lat}, {destination_lng}），請分析當前路況並提供最佳的駕駛建議。"
        else:
            message = f"我目前在（{user_lat}, {user_lng}）位置，請分析周邊的交通狀況並提供駕駛建議。"

        # 調用聊天 API
        chat_request = ChatRequest(
            message=message,
            traffic_data=traffic_data,
            shockwave_data=shockwave_data,
            user_location={"lat": user_lat, "lng": user_lng}
        )

        return await chat_with_ollama(chat_request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取交通建議失敗: {str(e)}")

@router.get("/status")
async def check_ollama_status():
    """檢查 Ollama 服務狀態"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.ok:
            models = response.json().get('models', [])
            available_models = [model['name'] for model in models]
            return {
                "status": "healthy",
                "ollama_url": OLLAMA_BASE_URL,
                "current_model": OLLAMA_MODEL,
                "available_models": available_models
            }
        else:
            return {"status": "error", "message": "Ollama 服務無回應"}
    except Exception as e:
        return {"status": "error", "message": f"無法連接 Ollama: {str(e)}"}