from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sys
import os

# 導入後端模組
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

router = APIRouter()

# 資料模型
from pydantic import BaseModel

class LocationPoint(BaseModel):
    lat: float
    lng: float
    address: str

class DepartureOptimizerRequest(BaseModel):
    origin: LocationPoint
    destination: LocationPoint
    preferred_arrival_time: Optional[datetime] = None
    analysis_range: int = 2  # 分析前後幾小時
    include_shockwave_prediction: bool = True
    include_traffic_prediction: bool = True

class TimeSlot(BaseModel):
    departure_time: datetime
    arrival_time: datetime
    duration: int  # 分鐘
    traffic_score: int  # 0-100
    shockwave_risk: str  # low, medium, high
    fuel_consumption: float  # 公升
    recommendation: str  # optimal, good, avoid

class AlternativeRoute(BaseModel):
    id: str
    name: str
    additional_time: int  # 額外時間（分鐘）
    avoidance_success: int  # 成功避開壅塞的機率（%）
    distance: float  # 距離（公里）
    toll_cost: int  # 過路費（元）

@router.post("/departure-optimizer")
async def optimize_departure_time(request: DepartureOptimizerRequest):
    """智慧出發時間建議"""
    try:
        # 這裡應該調用深度學習模型和震波預測系統
        current_time = datetime.now()
        
        # 計算分析時間範圍
        if request.preferred_arrival_time:
            base_time = request.preferred_arrival_time
        else:
            base_time = current_time + timedelta(hours=1)
            
        # 生成時間選項
        time_slots = []
        for i in range(-request.analysis_range * 2, request.analysis_range * 2 + 1):
            departure_time = base_time + timedelta(minutes=i * 30) - timedelta(hours=1)
            
            # 模擬交通預測和震波風險評估
            traffic_score = max(20, 100 - abs(i) * 10 - (i % 3) * 15)
            shockwave_risk = "low" if abs(i) <= 2 else "medium" if abs(i) <= 4 else "high"
            duration = 45 + abs(i) * 5 + (10 if shockwave_risk == "high" else 0)
            fuel_consumption = 8.5 + (duration - 45) * 0.1
            
            # 決定推薦等級
            if traffic_score >= 85 and shockwave_risk == "low":
                recommendation = "optimal"
            elif traffic_score >= 70 and shockwave_risk != "high":
                recommendation = "good"
            else:
                recommendation = "avoid"
            
            time_slots.append({
                "departure_time": departure_time.isoformat(),
                "arrival_time": (departure_time + timedelta(minutes=duration)).isoformat(),
                "duration": duration,
                "traffic_score": traffic_score,
                "shockwave_risk": shockwave_risk,
                "fuel_consumption": fuel_consumption,
                "recommendation": recommendation
            })
        
        # 排序：最佳選項在前
        time_slots.sort(key=lambda x: (
            0 if x["recommendation"] == "optimal" else 
            1 if x["recommendation"] == "good" else 2,
            -x["traffic_score"]
        ))
        
        return {
            "time_slots": time_slots,
            "analysis_range": request.analysis_range,
            "total_options": len(time_slots),
            "generated_at": current_time.isoformat(),
            "route_info": {
                "distance": 25.8,  # km
                "base_duration": 45,  # 分鐘
                "toll_cost": 40  # 元
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"出發時間優化失敗: {str(e)}")

@router.post("/alternative-routes")
async def get_alternative_routes(
    origin: LocationPoint,
    destination: LocationPoint,
    avoid_shockwaves: bool = True
):
    """獲取替代路線建議"""
    try:
        # 這裡應該調用路線規劃算法，考慮震波避讓
        current_time = datetime.now()
        
        # 模擬替代路線
        routes = [
            {
                "id": "route_001",
                "name": "國道1號主線",
                "additional_time": 0,
                "avoidance_success": 60,
                "distance": 25.8,
                "toll_cost": 40,
                "description": "最短路線，但可能遇到震波",
                "risk_level": "medium"
            },
            {
                "id": "route_002", 
                "name": "國道3號替代",
                "additional_time": 12,
                "avoidance_success": 85,
                "distance": 28.5,
                "toll_cost": 45,
                "description": "繞行國道3號，可避開大部分震波",
                "risk_level": "low"
            },
            {
                "id": "route_003",
                "name": "省道混合路線",
                "additional_time": 25,
                "avoidance_success": 95,
                "distance": 32.1,
                "toll_cost": 20,
                "description": "部分使用省道，完全避開高速公路震波",
                "risk_level": "low"
            }
        ]
        
        # 如果要求避開震波，重新排序
        if avoid_shockwaves:
            routes.sort(key=lambda x: (-x["avoidance_success"], x["additional_time"]))
        
        return {
            "routes": routes,
            "total_count": len(routes),
            "generated_at": current_time.isoformat(),
            "criteria": {
                "avoid_shockwaves": avoid_shockwaves,
                "optimization_target": "time_and_safety"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"替代路線查詢失敗: {str(e)}")

@router.get("/travel-time-prediction")
async def predict_travel_time(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    departure_time: Optional[datetime] = None
):
    """預測旅行時間"""
    try:
        if not departure_time:
            departure_time = datetime.now()
            
        # 這裡應該調用旅行時間預測模型
        # 考慮歷史資料、即時交通、震波影響等因素
        
        # 計算基礎距離（簡化計算）
        import math
        R = 6371  # 地球半徑
        dlat = math.radians(dest_lat - origin_lat)
        dlon = math.radians(dest_lng - origin_lng)
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(origin_lat)) * math.cos(math.radians(dest_lat)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        # 模擬預測結果
        base_time = distance / 80 * 60  # 假設平均80km/h
        
        # 考慮時段因素
        hour = departure_time.hour
        if 7 <= hour <= 9 or 17 <= hour <= 19:  # 尖峰時段
            time_factor = 1.4
        elif 22 <= hour or hour <= 6:  # 深夜時段
            time_factor = 0.8
        else:
            time_factor = 1.0
            
        predicted_time = int(base_time * time_factor)
        
        prediction_result = {
            "origin": {"lat": origin_lat, "lng": origin_lng},
            "destination": {"lat": dest_lat, "lng": dest_lng},
            "departure_time": departure_time.isoformat(),
            "predicted_duration": predicted_time,  # 分鐘
            "distance": round(distance, 1),  # km
            "confidence": 0.85,
            "factors": {
                "base_time": int(base_time),
                "time_factor": time_factor,
                "traffic_impact": "moderate",
                "weather_impact": "none",
                "shockwave_impact": "low"
            },
            "alternative_scenarios": {
                "best_case": int(predicted_time * 0.8),
                "worst_case": int(predicted_time * 1.3),
                "most_likely": predicted_time
            }
        }
        
        return prediction_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"旅行時間預測失敗: {str(e)}")

@router.get("/traffic-insights")
async def get_traffic_insights(
    route_id: Optional[str] = None,
    time_range: int = 24  # 小時
):
    """獲取交通洞察分析"""
    try:
        current_time = datetime.now()
        
        # 模擬交通洞察資料
        insights = {
            "route_id": route_id or "default",
            "analysis_period": f"過去{time_range}小時",
            "key_insights": [
                {
                    "type": "pattern",
                    "title": "尖峰時段識別",
                    "description": "週一至週五 8:00-9:30 和 17:30-19:00 為主要壅塞時段",
                    "confidence": 0.92
                },
                {
                    "type": "shockwave",
                    "title": "震波熱點",
                    "description": "國道1號桃園系統附近最容易產生震波，建議避開",
                    "confidence": 0.88
                },
                {
                    "type": "optimization",
                    "title": "最佳出發時間",
                    "description": "提前30分鐘出發可節省平均15分鐘旅行時間",
                    "confidence": 0.85
                }
            ],
            "statistics": {
                "average_speed": 76.5,
                "congestion_frequency": 0.35,
                "shockwave_incidents": 12,
                "reliability_score": 0.78
            },
            "recommendations": [
                "考慮使用國道3號作為替代路線",
                "避開週五下午時段",
                "關注即時震波警報"
            ],
            "generated_at": current_time.isoformat()
        }
        
        return insights
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取交通洞察失敗: {str(e)}")

@router.post("/save-preferences")
async def save_user_preferences(
    user_id: str,
    preferences: Dict[str, Any]
):
    """儲存用戶偏好設定"""
    try:
        # 這裡應該將偏好設定儲存到資料庫
        saved_preferences = {
            "user_id": user_id,
            "preferences": preferences,
            "saved_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        return {
            "message": "偏好設定已儲存",
            "user_id": user_id,
            "saved_preferences": saved_preferences
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"儲存偏好設定失敗: {str(e)}")
