from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os

# 導入後端模組
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

from src.detection.final_optimized_detector import FinalOptimizedShockDetector
from src.prediction.realtime_shock_predictor import RealtimeShockPredictor

router = APIRouter()

# 資料模型
from pydantic import BaseModel

class ShockwaveData(BaseModel):
    id: str
    location_name: str
    latitude: float
    longitude: float
    intensity: float
    propagation_speed: float
    estimated_arrival: datetime
    affected_area: float
    description: Optional[str] = None
    alternative_routes: Optional[List[dict]] = None

class ShockwaveAlert(BaseModel):
    id: str
    severity: str
    title: str
    description: str
    timestamp: datetime
    location: dict
    recommendations: List[str]

@router.get("/active", response_model=dict)
async def get_active_shockwaves():
    """獲取當前活躍的震波"""
    try:
        # 這裡應該調用你的震波檢測系統
        # detector = FinalOptimizedShockDetector()
        # active_shockwaves = detector.get_active_shockwaves()
        
        # 模擬資料
        current_time = datetime.now()
        mock_shockwaves = [
            {
                "id": "sw_001",
                "location_name": "國道1號 台北-桃園",
                "latitude": 25.0330,
                "longitude": 121.5654,
                "intensity": 7.2,
                "propagation_speed": 22.5,
                "estimated_arrival": (current_time + timedelta(minutes=15)).isoformat(),
                "affected_area": 5.8,
                "description": "前方發生交通事故，形成震波向後傳播",
                "alternative_routes": [
                    {
                        "id": "alt_001",
                        "name": "國道3號替代路線",
                        "additional_time": 12,
                        "avoidance_success": 85
                    }
                ]
            },
            {
                "id": "sw_002", 
                "location_name": "國道3號 新店-土城",
                "latitude": 24.9598,
                "longitude": 121.5426,
                "intensity": 5.1,
                "propagation_speed": 18.3,
                "estimated_arrival": (current_time + timedelta(minutes=25)).isoformat(),
                "affected_area": 3.2,
                "description": "車流量突增導致的震波",
                "alternative_routes": []
            }
        ]
        
        return {
            "shockwaves": mock_shockwaves,
            "total_count": len(mock_shockwaves),
            "last_updated": current_time.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取震波資料失敗: {str(e)}")

@router.get("/predict")
async def predict_shockwave_propagation(
    shockwave_id: str,
    time_horizon: int = 60  # 預測時間範圍（分鐘）
):
    """預測震波傳播路徑和到達時間"""
    try:
        # 這裡調用震波預測系統
        # predictor = RealtimeShockPredictor()
        # prediction = predictor.predict_propagation(shockwave_id, time_horizon)
        
        # 模擬預測結果
        current_time = datetime.now()
        prediction_data = {
            "shockwave_id": shockwave_id,
            "propagation_path": [
                {
                    "station_id": "001",
                    "estimated_arrival": (current_time + timedelta(minutes=5)).isoformat(),
                    "intensity": 7.0,
                    "confidence": 0.92
                },
                {
                    "station_id": "002", 
                    "estimated_arrival": (current_time + timedelta(minutes=15)).isoformat(),
                    "intensity": 6.5,
                    "confidence": 0.87
                },
                {
                    "station_id": "003",
                    "estimated_arrival": (current_time + timedelta(minutes=25)).isoformat(), 
                    "intensity": 5.8,
                    "confidence": 0.78
                }
            ],
            "total_affected_distance": 15.2,
            "prediction_confidence": 0.85,
            "generated_at": current_time.isoformat()
        }
        
        return prediction_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"震波預測失敗: {str(e)}")

@router.get("/history")
async def get_shockwave_history(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 50
):
    """獲取歷史震波記錄"""
    try:
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=7)
            
        # 這裡實作歷史震波查詢
        return {
            "history": [],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_count": 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取歷史震波失敗: {str(e)}")

@router.post("/alert/dismiss")
async def dismiss_shockwave_alert(alert_id: str):
    """關閉震波警報"""
    try:
        # 實作警報關閉邏輯
        return {
            "message": f"警報 {alert_id} 已關閉",
            "dismissed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"關閉警報失敗: {str(e)}")

@router.get("/statistics")
async def get_shockwave_statistics():
    """獲取震波統計資料"""
    try:
        # 計算震波統計
        stats = {
            "today_total": 12,
            "active_count": 2,
            "average_intensity": 5.8,
            "most_affected_highway": "國道1號",
            "prediction_accuracy": 0.87,
            "last_24h_trend": "increasing"
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取統計資料失敗: {str(e)}")
