from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import math
from datetime import datetime, timedelta

router = APIRouter()

class ShockwaveAnalysisRequest(BaseModel):
    user_location: Dict[str, float]  # {lat, lng}
    shockwaves: List[Dict[str, Any]]
    user_message: Optional[str] = "請分析當前的交通震波情況並給予建議"

class ShockwaveRecommendation(BaseModel):
    type: str
    priority: str
    title: str
    description: str
    action_time: Optional[str] = None

class ShockwaveAnalysisResponse(BaseModel):
    recommendations: List[ShockwaveRecommendation]
    risk_level: str
    summary: str
    ai_analysis: str

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """計算兩點之間的距離 (Haversine公式)"""
    R = 6371  # 地球半徑 (公里)
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat/2) * math.sin(dLat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dLon/2) * math.sin(dLon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@router.post("/shockwave-analysis", response_model=ShockwaveAnalysisResponse)
async def analyze_shockwave_impact(request: ShockwaveAnalysisRequest):
    """分析交通震波對駕駛者的影響並提供具體建議"""
    try:
        if not request.shockwaves:
            return ShockwaveAnalysisResponse(
                recommendations=[],
                risk_level="low",
                summary="目前沒有檢測到震波事件",
                ai_analysis="路況良好，請安全駕駛。"
            )
        
        # 計算距離和風險
        nearest_distance = float('inf')
        max_intensity = 0
        
        for shock in request.shockwaves:
            distance = calculate_distance(
                request.user_location['lat'], request.user_location['lng'],
                shock.get('latitude', 0), shock.get('longitude', 0)
            )
            shock['distance_to_user'] = distance
            
            if distance < nearest_distance:
                nearest_distance = distance
            
            if shock.get('intensity', 0) > max_intensity:
                max_intensity = shock.get('intensity', 0)
        
        # 評估風險等級
        if nearest_distance < 5 and max_intensity >= 7:
            risk_level = "high"
        elif nearest_distance < 10 and max_intensity >= 5:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 生成建議
        recommendations = []
        
        # 基本建議
        if risk_level == "high":
            recommendations.append(ShockwaveRecommendation(
                type="emergency",
                priority="urgent",
                title="⚠️ 緊急注意",
                description=f"前方{nearest_distance:.1f}公里處有高強度震波，建議立即減速或尋找替代路線",
                action_time="立即"
            ))
        elif risk_level == "medium":
            recommendations.append(ShockwaveRecommendation(
                type="alternative_route",
                priority="medium",
                title="建議使用替代路線",
                description=f"前方{nearest_distance:.1f}公里處有震波影響，建議考慮其他路線",
                action_time="盡快"
            ))
        
        recommendations.append(ShockwaveRecommendation(
            type="speed_warning",
            priority="medium",
            title="注意行車速度",
            description=f"建議將車速降至60km/h以下，保持安全跟車距離",
            action_time=f"{nearest_distance:.1f}公里後"
        ))
        
        # 生成摘要
        if risk_level == "high":
            summary = f"⚠️ 高風險：距離您{nearest_distance:.1f}公里處有強度{max_intensity}/10的震波，請立即採取避險措施"
        elif risk_level == "medium":
            summary = f"⚡ 中等風險：距離您{nearest_distance:.1f}公里處有強度{max_intensity}/10的震波，建議調整行駛計畫"
        else:
            summary = f"ℹ️ 低風險：震波距離較遠，請持續關注路況變化"
        
        # 簡單的AI分析（不調用Ollama避免超時）
        ai_analysis = f"""根據震波分析結果：
        
📍 最近震波距離：{nearest_distance:.1f}公里
📊 最高震波強度：{max_intensity}/10
⚠️ 風險等級：{risk_level.upper()}

建議採取以下措施：
1. 🚗 降低行車速度至安全範圍
2. 📱 持續關注即時路況資訊  
3. 🛣️ 如情況嚴重，考慮替代路線
4. ⏰ 必要時延後出發時間

請根據實際路況謹慎駕駛，安全第一！"""
        
        return ShockwaveAnalysisResponse(
            recommendations=recommendations,
            risk_level=risk_level,
            summary=summary,
            ai_analysis=ai_analysis
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"震波分析失敗: {str(e)}")

@router.get("/shockwave-status")
async def get_shockwave_status():
    """獲取震波分析系統狀態"""
    return {
        "status": "operational",
        "ollama_status": "bypassed",  # 暫時繞過Ollama
        "features": {
            "distance_calculation": True,
            "risk_assessment": True,
            "recommendation_engine": True,
            "ai_analysis": True
        }
    }