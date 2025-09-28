from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import requests
import math
from datetime import datetime, timedelta
import os

router = APIRouter()

# Ollama 設定
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')

class ShockwaveAnalysisRequest(BaseModel):
    user_location: Dict[str, float]  # {lat, lng}
    shockwaves: List[Dict[str, Any]]
    user_message: Optional[str] = "請分析當前的交通震波情況並給予建議"
    destination: Optional[Dict[str, float]] = None

class ShockwaveRecommendation(BaseModel):
    type: str  # "alternative_route", "timing_adjustment", "rest_area", "speed_warning", "emergency"
    priority: str  # "urgent", "high", "medium", "low"
    title: str
    description: str
    action_time: Optional[str] = None
    location: Optional[Dict[str, Any]] = None

class ShockwaveAnalysisResponse(BaseModel):
    recommendations: List[ShockwaveRecommendation]
    risk_level: str  # "high", "medium", "low"
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

def analyze_shockwave_risk(user_location: Dict[str, float], shockwaves: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析震波風險等級和基本建議"""
    if not shockwaves:
        return {"risk_level": "low", "nearest_shock": None, "recommendations": []}
    
    nearest_shock = None
    min_distance = float('inf')
    max_intensity = 0
    
    for shock in shockwaves:
        distance = calculate_distance(
            user_location['lat'], user_location['lng'],
            shock.get('latitude', 0), shock.get('longitude', 0)
        )
        shock['distance_to_user'] = distance
        
        if distance < min_distance:
            min_distance = distance
            nearest_shock = shock
        
        if shock.get('intensity', 0) > max_intensity:
            max_intensity = shock.get('intensity', 0)
    
    # 風險等級評估
    if min_distance < 5 and max_intensity >= 7:
        risk_level = "high"
    elif min_distance < 10 and max_intensity >= 5:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return {
        "risk_level": risk_level,
        "nearest_shock": nearest_shock,
        "min_distance": min_distance,
        "max_intensity": max_intensity
    }

def generate_recommendations(analysis: Dict[str, Any], shockwaves: List[Dict[str, Any]]) -> List[ShockwaveRecommendation]:
    """根據分析結果生成具體建議"""
    recommendations = []
    nearest_shock = analysis['nearest_shock']
    
    if not nearest_shock:
        return recommendations
    
    distance = analysis['min_distance']
    intensity = analysis['max_intensity']
    risk_level = analysis['risk_level']
    
    # 1. 替代路線建議
    if distance < 15 and intensity >= 6:
        recommendations.append(ShockwaveRecommendation(
            type="alternative_route",
            priority="high" if risk_level == "high" else "medium",
            title="建議使用替代路線",
            description=f"前方{distance:.1f}公里處有強度{intensity}/10的交通震波，建議改走省道或其他國道避開壅塞區域",
            location={"lat": nearest_shock.get('latitude'), "lng": nearest_shock.get('longitude')}
        ))
    
    # 2. 時間調整建議
    duration = nearest_shock.get('shock_duration', 30)
    if distance < 20 and intensity >= 5:
        delay_minutes = max(duration + 10, 20)  # 震波持續時間 + 緩衝時間
        recommendations.append(ShockwaveRecommendation(
            type="timing_adjustment",
            priority="medium",
            title="建議延後出發",
            description=f"震波預計持續{duration}分鐘，建議延後{delay_minutes}分鐘出發，讓震波通過後再行駛",
            action_time=(datetime.now() + timedelta(minutes=delay_minutes)).strftime('%H:%M')
        ))
    
    # 3. 休息站建議
    if distance < 10 and intensity >= 6:
        recommendations.append(ShockwaveRecommendation(
            type="rest_area",
            priority="high" if risk_level == "high" else "medium",
            title="建議前往休息站等待",
            description=f"前方{distance:.1f}公里即將遭受震波影響，建議就近尋找休息站或安全區域等待{duration}分鐘",
            action_time=f"等待約{duration}分鐘"
        ))
    
    # 4. 速度警告
    if distance < 25:
        safe_speed = max(50, 80 - intensity * 5)  # 根據強度調整建議速度
        recommendations.append(ShockwaveRecommendation(
            type="speed_warning",
            priority="medium",
            title="前方需要降速",
            description=f"前方{distance:.1f}公里後車流將受震波影響，建議將車速降至{safe_speed}km/h以下，保持安全跟車距離",
            action_time=f"{distance:.1f}公里後"
        ))
    
    # 5. 緊急措施
    if distance < 3 and intensity >= 8:
        recommendations.append(ShockwaveRecommendation(
            type="emergency",
            priority="urgent",
            title="⚠️ 緊急注意",
            description="您即將進入高強度震波影響區域，請立即減速並尋找安全地點停車，避免追撞風險",
            action_time="立即"
        ))
    
    return recommendations

class SingleShockwaveAnalysisRequest(BaseModel):
    user_location: Dict[str, float]  # {lat, lng}
    shockwave: Dict[str, Any]  # 單個震波資訊
    
@router.post("/shockwave-analysis", response_model=ShockwaveAnalysisResponse)
async def analyze_shockwave_impact(request: ShockwaveAnalysisRequest):
    """分析交通震波對駕駛者的影響並提供具體建議"""
    try:
        # 1. 基本風險分析
        analysis = analyze_shockwave_risk(request.user_location, request.shockwaves)
        
        # 2. 生成具體建議
        recommendations = generate_recommendations(analysis, request.shockwaves)
        
        # 3. 構建簡化的AI分析提示
        nearest_shock = analysis['nearest_shock']
        distance = analysis['min_distance']
        intensity = analysis['max_intensity']
        
        detailed_prompt = f"""你是台灣的專業交通專家，請用繁體中文進行分析：

【台灣交通震波分析】
位置：距離您{distance:.1f}公里處有強度{intensity}/10的震波
風險：{analysis['risk_level']}風險等級

請用繁體中文提供：
1. 路線建議（國道/省道替代方案）
2. 時間調整（建議延後多久出發）
3. 休息站建議（就近等待地點）
4. 速度建議（行車注意事項）

請務必使用繁體中文，簡潔回答，150字內："""

        # 4. 使用真實Ollama AI進行分析
        try:
            ollama_response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": "qwen2.5:7b",
                    "prompt": detailed_prompt,
                    "stream": False
                },
                timeout=30  # 30秒超時
            )
            
            if ollama_response.ok:
                ai_data = ollama_response.json()
                ai_analysis = f"""🤖 AI智能分析報告

📍 震波位置：{nearest_shock.get('location_name', '未知位置')}
📏 距離您的位置：{distance:.1f}公里  
📊 震波強度：{intensity}/10
⏱️ 預估持續時間：{nearest_shock.get('shock_duration', '未知')}分鐘
🌊 影響範圍：{nearest_shock.get('affected_area', '未知')}公里

🧠 AI專家建議：
{ai_data.get('response', '分析中...')}

⚠️ 此分析基於即時AI運算，請結合實際路況謹慎駕駛！"""
            else:
                ai_analysis = f"""⚠️ AI服務暫時不可用

📍 基礎分析報告：
• 震波位置：{nearest_shock.get('location_name', '未知位置')}
• 距離：{distance:.1f}公里
• 強度：{intensity}/10
• 風險等級：{analysis['risk_level'].upper()}

請根據基礎分析謹慎駕駛，安全第一！"""
                
        except Exception as e:
            print(f"Ollama AI 調用失敗: {str(e)}")
            ai_analysis = f"""⚠️ AI分析服務連線異常

📍 緊急基礎分析：
• 檢測到震波距離您{distance:.1f}公里
• 強度等級：{intensity}/10 
• 風險評估：{analysis['risk_level'].upper()}

建議立即關注路況，必要時尋找替代路線！"""
        
        # 5. 生成摘要
        risk_level = analysis['risk_level']
        shock_count = len(request.shockwaves)
        min_distance = analysis['min_distance']
        
        if risk_level == "high":
            summary = f"⚠️ 高風險：檢測到{shock_count}個震波，最近距離{min_distance:.1f}公里，建議立即採取避險措施"
        elif risk_level == "medium":
            summary = f"⚡ 中等風險：檢測到{shock_count}個震波，最近距離{min_distance:.1f}公里，建議調整行駛計畫"
        else:
            summary = f"ℹ️ 低風險：檢測到{shock_count}個震波，距離較遠，請持續關注路況變化"
        
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
    try:
        # 檢查Ollama服務
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        ollama_status = "healthy" if response.ok else "unavailable"
        
        return {
            "status": "operational",
            "ollama_status": ollama_status,
            "features": {
                "distance_calculation": True,
                "risk_assessment": True,
                "recommendation_engine": True,
                "ai_analysis": ollama_status == "healthy"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/single-shockwave-analysis")
async def analyze_single_shockwave(request: SingleShockwaveAnalysisRequest):
    """針對特定震波進行詳細AI分析"""
    try:
        # 計算距離
        user_lat = request.user_location['lat']
        user_lng = request.user_location['lng']
        shock_lat = request.shockwave['latitude']
        shock_lng = request.shockwave['longitude']
        
        distance = calculate_distance(user_lat, user_lng, shock_lat, shock_lng)
        intensity = request.shockwave.get('intensity', 0)
        
        # 風險評估
        if distance < 5 and intensity > 8:
            risk_level = "high"
        elif distance < 15 and intensity > 6:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 構建詳細的AI分析提示
        shock_info = request.shockwave
        ai_prompt = f"""你是台灣的專業交通專家，請用繁體中文分析以下震波情況並提供專業建議：

【震波詳細資訊】
• 位置：{shock_info.get('location_name', '未知')}
• 座標：緯度{shock_lat}，經度{shock_lng}
• 距離用戶：{distance:.1f}公里
• 強度等級：{intensity}/10
• 持續時間：{shock_info.get('shock_duration', '未知')}分鐘
• 影響範圍：{shock_info.get('affected_area', '未知')}公里
• 傳播速度：{shock_info.get('propagation_speed', '未知')}km/h
• 預估降速：{shock_info.get('speed_drop', '未知')}%

【使用者位置】
緯度：{user_lat}，經度：{user_lng}

請用繁體中文提供：
1. 🛣️ 具體的替代路線建議（國道/省道）
2. ⏰ 精確的時間調整建議（何時出發最佳）
3. � 附近休息站或安全停靠點
4. 🚗 行車速度和安全距離建議
5. 📱 其他注意事項

請務必使用繁體中文，以專業、簡潔的方式回答，控制在200字內："""

        # 調用真實AI分析
        try:
            ollama_response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": "qwen2.5:7b",
                    "prompt": ai_prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if ollama_response.ok:
                ai_data = ollama_response.json()
                ai_analysis = ai_data.get('response', '分析中...')
            else:
                raise Exception("Ollama API 請求失敗")
                
        except Exception as e:
            print(f"AI分析失敗: {str(e)}")
            ai_analysis = f"""⚠️ AI服務暫時無法使用，提供基礎分析：

基於震波資料分析：
• 距離{distance:.1f}公里的{shock_info.get('location_name', '震波區域')}
• 強度{intensity}/10，風險等級：{risk_level.upper()}
• 建議採取相應的預防措施

請根據實際路況謹慎駕駛！"""

        # 生成針對性建議
        recommendations = []
        if distance < 15 and intensity >= 6:
            recommendations.append({
                "type": "alternative_route",
                "priority": "high" if risk_level == "high" else "medium",
                "title": "替代路線建議",
                "description": f"前方{distance:.1f}公里處的{shock_info.get('location_name', '震波區域')}強度達{intensity}/10，建議改走替代路線"
            })
        
        if distance < 20:
            delay_time = shock_info.get('shock_duration', 30) + 15
            recommendations.append({
                "type": "timing_adjustment", 
                "priority": "medium",
                "title": "出行時間調整",
                "description": f"建議延後{delay_time}分鐘出發，避開震波高峰期"
            })
        
        return {
            "shockwave_info": shock_info,
            "distance": round(distance, 1),
            "risk_level": risk_level,
            "ai_analysis": ai_analysis,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"單震波分析失敗: {str(e)}")