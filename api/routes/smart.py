from fastapi import APIRouter, HTTPException, Depends, Form
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sys
import os
import asyncio

# 導入後端模組
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

# 導入RAG智能駕駛建議系統
try:
    from train_model.models.driver_advisor import IntelligentDriverAdvisor, TrafficCondition, ShockwaveAlert
    from src.data.tdx_tisc_mix_system import OptimizedIntegratedDataCollectionSystem
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"RAG系統導入失敗: {e}")
    RAG_AVAILABLE = False

router = APIRouter()

# 全域RAG系統實例
rag_advisor = None
data_system = None

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

# RAG 智能建議相關模型
class DriverAdviceRequest(BaseModel):
    current_location: Dict[str, Any]
    destination: Dict[str, Any] 
    current_traffic: Optional[Dict[str, Any]] = None
    shockwave_alert: Optional[Dict[str, Any]] = None

class DriverAdviceResponse(BaseModel):
    priority: str
    action_type: str
    title: str
    description: str
    reasoning: str
    time_saving_min: Optional[int]
    safety_impact: str
    alternatives: List[Dict[str, Any]]
    rest_areas: List[Dict[str, Any]]
    estimated_cost: Optional[str]
    confidence: float

# RAG系統初始化
async def initialize_rag_system():
    """初始化RAG智能駕駛建議系統"""
    global rag_advisor, data_system
    
    if not RAG_AVAILABLE:
        return False
        
    try:
        if rag_advisor is None:
            rag_advisor = IntelligentDriverAdvisor()
            await rag_advisor.initialize()
            print("✅ RAG智能駕駛建議系統初始化完成")
            
        if data_system is None:
            data_system = OptimizedIntegratedDataCollectionSystem()
            print("✅ 交通資料收集系統初始化完成")
            
        return True
    except Exception as e:
        print(f"❌ RAG系統初始化失敗: {e}")
        return False

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

# ==================== RAG 智能駕駛建議API ====================

@router.post("/rag-advice", response_model=DriverAdviceResponse)
async def get_rag_driver_advice(request: DriverAdviceRequest):
    """RAG智能駕駛建議 - 核心功能"""
    try:
        # 初始化RAG系統
        if not await initialize_rag_system():
            raise HTTPException(status_code=503, detail="RAG系統不可用")
            
        # 獲取當前交通資料
        current_traffic_data = None
        if data_system:
            try:
                # 獲取實時交通資料
                latest_data = data_system.get_latest_data_for_shockwave()
                if not latest_data.empty:
                    # 根據位置找到最近的站點資料
                    current_station = find_nearest_station(
                        request.current_location, latest_data
                    )
                    if current_station is not None:
                        current_traffic_data = TrafficCondition(
                            station_id=current_station['station'],
                            speed=current_station['median_speed'],
                            flow=current_station['flow'],
                            travel_time=current_station['avg_travel_time'],
                            congestion_level=determine_congestion_level(current_station['median_speed']),
                            timestamp=datetime.now()
                        )
            except Exception as e:
                print(f"獲取交通資料失敗: {e}")
        
        # 處理震波警報
        shockwave_alert = None
        if request.shockwave_alert:
            shockwave_alert = ShockwaveAlert(
                intensity=request.shockwave_alert.get('intensity', 0),
                propagation_speed=request.shockwave_alert.get('propagation_speed', 0),
                estimated_arrival=datetime.fromisoformat(request.shockwave_alert.get('estimated_arrival')) if request.shockwave_alert.get('estimated_arrival') else None,
                affected_area=request.shockwave_alert.get('affected_area', ''),
                warning_level=request.shockwave_alert.get('warning_level', 'low')
            )
        
        # 如果沒有實際交通資料，創建模擬資料
        if current_traffic_data is None:
            current_traffic_data = TrafficCondition(
                station_id='unknown',
                speed=80.0,  # 預設速度
                flow=1000.0,  # 預設流量
                travel_time=5.0,  # 預設旅行時間
                congestion_level='normal',
                timestamp=datetime.now()
            )
        
        # 使用RAG系統獲取建議
        advice = await rag_advisor.analyze_current_situation(
            current_location=request.current_location,
            destination=request.destination,
            traffic_data=current_traffic_data,
            shockwave_alert=shockwave_alert
        )
        
        # 轉換為API回應格式
        response = DriverAdviceResponse(
            priority=advice.priority,
            action_type=advice.action_type,
            title=advice.title,
            description=advice.description,
            reasoning=advice.reasoning,
            time_saving_min=advice.time_saving_min,
            safety_impact=advice.safety_impact,
            alternatives=[{
                'route_name': alt.route_name,
                'description': alt.description,
                'extra_distance_km': alt.extra_distance_km,
                'time_difference_min': alt.time_difference_min,
                'congestion_avoidance': alt.congestion_avoidance,
                'recommended_conditions': alt.recommended_conditions
            } for alt in advice.alternatives],
            rest_areas=[{
                'name': area.name,
                'distance_km': area.distance_km,
                'direction': area.direction,
                'facilities': area.facilities,
                'estimated_travel_time': area.estimated_travel_time
            } for area in advice.rest_areas],
            estimated_cost=advice.estimated_cost,
            confidence=calculate_advice_confidence(advice)
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"RAG建議生成錯誤: {e}")
        # 返回備用建議
        return DriverAdviceResponse(
            priority='medium',
            action_type='continue',
            title='基本交通建議',
            description='RAG系統暫時不可用，建議依據實際路況小心駕駛，保持安全車距。',
            reasoning='AI系統暫時無法提供詳細分析，請駕駛人依據實際情況判斷。',
            time_saving_min=None,
            safety_impact='請保持警覺',
            alternatives=[],
            rest_areas=[],
            estimated_cost=None,
            confidence=0.3
        )

@router.get("/rag-status")
async def get_rag_status():
    """檢查RAG系統狀態"""
    try:
        status = {
            "rag_available": RAG_AVAILABLE,
            "advisor_initialized": rag_advisor is not None,
            "data_system_initialized": data_system is not None,
            "last_check": datetime.now().isoformat()
        }
        
        if RAG_AVAILABLE and rag_advisor:
            try:
                # 測試RAG系統連接
                await initialize_rag_system()
                status["ollama_connected"] = True
                status["system_health"] = "healthy"
            except Exception as e:
                status["ollama_connected"] = False
                status["system_health"] = "degraded"
                status["error"] = str(e)
        else:
            status["system_health"] = "unavailable"
            
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG狀態檢查失敗: {str(e)}")

@router.post("/rag-chat")
async def rag_chat_endpoint(message: str = Form(...)):
    """RAG對話端點 - 供駕駛者諮詢使用"""
    try:
        if not await initialize_rag_system():
            raise HTTPException(status_code=503, detail="RAG系統不可用")
            
        if not rag_advisor or not rag_advisor.rag_chat:
            raise HTTPException(status_code=503, detail="RAG對話系統未初始化")
            
        # 使用RAG對話系統回應
        response = await rag_advisor.rag_chat.chat(
            user_message=message,
            use_rag=True,
            max_history=3
        )
        
        return {
            "message": message,
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "source": "RAG+Ollama"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG對話失敗: {str(e)}")

# 輔助函數
def find_nearest_station(location: Dict[str, Any], traffic_data) -> Optional[Dict]:
    """找到最近的交通監測站點"""
    try:
        if traffic_data.empty:
            return None
            
        # 簡化版本：返回第一個可用的站點資料
        # 實際實作應該根據地理位置計算最近站點
        return traffic_data.iloc[0].to_dict()
    except:
        return None

def determine_congestion_level(speed: float) -> str:
    """根據速度判斷壅塞程度"""
    if speed >= 80:
        return 'smooth'
    elif speed >= 60:
        return 'normal'
    elif speed >= 40:
        return 'congested'
    else:
        return 'severe'

def calculate_advice_confidence(advice) -> float:
    """計算建議的可信度"""
    # 基於建議類型和資料完整性計算信心度
    base_confidence = 0.8
    
    if advice.priority == 'urgent':
        base_confidence += 0.1
    elif advice.priority == 'high':
        base_confidence += 0.05
        
    if len(advice.alternatives) > 0:
        base_confidence += 0.05
        
    if len(advice.rest_areas) > 0:
        base_confidence += 0.05
        
    return min(base_confidence, 1.0)
