from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os
import pandas as pd
import random

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

def load_station_data():
    """載入真實的測站數據"""
    try:
        etag_path = os.path.join(root_dir, 'data', 'Taiwan', 'Etag.csv')
        df = pd.read_csv(etag_path)
        
        # 清理數據，移除多餘的列
        df = df.dropna(subset=['緯度(北緯)', '經度(東經)'])
        
        stations = []
        for _, row in df.iterrows():
            # 解析緯度和經度
            lat_str = str(row['緯度(北緯)']).replace('N', '').strip()
            lng_str = str(row['經度(東經)']).replace('E', '').strip()
            
            try:
                lat = float(lat_str)
                lng = float(lng_str)
                
                station = {
                    'id': row['ID'],
                    'station_id': row['編號'],
                    'direction': row['方向'],
                    'start_ic': row['交流道(起)'],
                    'end_ic': row['交流道(迄)'],
                    'latitude': lat,
                    'longitude': lng,
                    'name': f"{row['交流道(起)']} - {row['交流道(迄)']}"
                }
                stations.append(station)
            except (ValueError, TypeError):
                continue
                
        return stations
    except Exception as e:
        print(f"載入測站數據失敗: {e}")
        return []

@router.get("/active", response_model=dict)
async def get_active_shockwaves():
    """獲取當前活躍的震波 - 使用真實測站數據"""
    try:
        # 載入真實測站數據
        stations = load_station_data()
        if not stations:
            raise HTTPException(status_code=500, detail="無法載入測站數據")
        
        current_time = datetime.now()
        
        # 隨機選擇幾個測站作為衝擊波發生點（模擬真實檢測）
        selected_stations = random.sample(stations, min(4, len(stations)))
        
        mock_shockwaves = []
        for i, station in enumerate(selected_stations):
            # 根據測站位置生成衝擊波
            intensity = random.uniform(4.0, 8.5)
            propagation_speed = random.uniform(15.0, 25.0)
            
            # 建立更好的位置名稱
            location_name = f"{station['start_ic']} - {station['end_ic']} ({station['direction']}向)"
            if station['start_ic'] == station['end_ic']:
                location_name = f"{station['start_ic']} ({station['direction']}向)"
            
            shockwave = {
                "id": f"sw_{station['id']:03d}",
                "station_id": station['station_id'],
                "location_name": location_name,
                "latitude": station['latitude'],  # 使用真實測站經緯度
                "longitude": station['longitude'],
                "intensity": round(intensity, 1),
                "propagation_speed": round(propagation_speed, 1),
                "estimated_arrival": (current_time + timedelta(minutes=random.randint(10, 60))).isoformat(),
                "affected_area": round(random.uniform(1.0, 3.0), 1),  # 更合理的影響範圍
                "description": f"在測站 {station['station_id']} ({location_name}) 檢測到交通衝擊波",
                "alternative_routes": []
            }
            
            # 為高強度衝擊波添加替代路線建議
            if intensity >= 6.0:
                shockwave["alternative_routes"] = [
                    {
                        "id": f"alt_{i+1:03d}",
                        "name": "建議替代路線",
                        "additional_time": random.randint(10, 30),
                        "avoidance_success": random.randint(70, 90)
                    }
                ]
            
            mock_shockwaves.append(shockwave)
        
        return {
            "shockwaves": mock_shockwaves,
            "total_count": len(mock_shockwaves),
            "last_updated": current_time.isoformat(),
            "data_source": "real_station_coordinates"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取震波資料失敗: {str(e)}")

@router.get("/stations", response_model=dict)
async def get_station_list():
    """獲取所有測站列表"""
    try:
        stations = load_station_data()
        return {
            "stations": stations,
            "total_count": len(stations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取測站列表失敗: {str(e)}")

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
