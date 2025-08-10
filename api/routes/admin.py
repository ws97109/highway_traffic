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

class SystemStatus(BaseModel):
    overall_health: str
    active_shockwaves: int
    monitoring_stations: int
    predictions_accuracy: float
    system_load: float
    last_update: datetime

class TrafficMetrics(BaseModel):
    total_flow: int
    average_speed: float
    congestion_level: float
    incident_count: int
    prediction_confidence: float

class RecommendedAction(BaseModel):
    id: str
    priority: str
    type: str
    title: str
    description: str
    expected_impact: str
    estimated_cost: float
    implementation_time: int
    confidence: float

class ActionRequest(BaseModel):
    action_id: str
    parameters: Optional[Dict[str, Any]] = None

@router.get("/system-status")
async def get_system_status():
    """獲取系統整體狀態"""
    try:
        # 這裡應該從各個子系統收集狀態資訊
        current_time = datetime.now()
        
        # 模擬系統狀態
        status = {
            "overall_health": "healthy",  # healthy, warning, critical
            "active_shockwaves": 3,
            "monitoring_stations": 62,
            "predictions_accuracy": 0.87,
            "system_load": 45.2,
            "last_update": current_time.isoformat(),
            "subsystems": {
                "data_collection": "healthy",
                "prediction_engine": "healthy", 
                "shockwave_detector": "warning",
                "alert_system": "healthy",
                "database": "healthy"
            },
            "uptime": "99.8%",
            "response_time": "120ms"
        }
        
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取系統狀態失敗: {str(e)}")

@router.get("/traffic-metrics")
async def get_traffic_metrics():
    """獲取即時交通指標"""
    try:
        # 計算即時交通指標
        current_time = datetime.now()
        
        metrics = {
            "total_flow": 45280,  # 車/小時
            "average_speed": 78.5,  # km/h
            "congestion_level": 32.8,  # %
            "incident_count": 5,
            "prediction_confidence": 0.89,
            "timestamp": current_time.isoformat(),
            "by_highway": {
                "國道1號": {
                    "flow": 28500,
                    "speed": 75.2,
                    "congestion": 38.5
                },
                "國道3號": {
                    "flow": 16780,
                    "speed": 82.1,
                    "congestion": 25.3
                }
            },
            "trends": {
                "flow_change_1h": "+5.2%",
                "speed_change_1h": "-3.1%",
                "congestion_trend": "increasing"
            }
        }
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取交通指標失敗: {str(e)}")

@router.get("/recommended-actions")
async def get_recommended_actions():
    """獲取AI推薦的管制行動"""
    try:
        current_time = datetime.now()
        
        # 模擬AI決策建議
        actions = [
            {
                "id": "action_001",
                "priority": "high",
                "type": "traffic_control",
                "title": "國道1號匝道管制",
                "description": "建議在台北系統交流道實施匝道管制，預計可減少主線車流15%",
                "expected_impact": "減少壅塞時間20分鐘",
                "estimated_cost": 5000,
                "implementation_time": 10,  # 分鐘
                "confidence": 0.92,
                "affected_area": "台北系統-桃園系統",
                "estimated_duration": 45  # 分鐘
            },
            {
                "id": "action_002", 
                "priority": "medium",
                "type": "route_guidance",
                "title": "替代路線引導",
                "description": "透過CMS看板引導車輛使用國道3號替代路線",
                "expected_impact": "分散車流25%",
                "estimated_cost": 2000,
                "implementation_time": 5,
                "confidence": 0.78,
                "affected_area": "國道1號中山高全線",
                "estimated_duration": 30
            },
            {
                "id": "action_003",
                "priority": "low", 
                "type": "emergency_response",
                "title": "增派巡邏車輛",
                "description": "在易壅塞路段增派巡邏車輛，提升事故處理效率",
                "expected_impact": "減少事故處理時間30%",
                "estimated_cost": 8000,
                "implementation_time": 20,
                "confidence": 0.85,
                "affected_area": "國道1號南向",
                "estimated_duration": 120
            }
        ]
        
        return {
            "actions": actions,
            "total_count": len(actions),
            "generated_at": current_time.isoformat(),
            "model_version": "DecisionAI-v2.1"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取推薦行動失敗: {str(e)}")

@router.post("/execute-action")
async def execute_action(request: ActionRequest):
    """執行推薦的管制行動"""
    try:
        action_id = request.action_id
        parameters = request.parameters or {}
        
        # 這裡實作具體的行動執行邏輯
        # 例如：發送管制指令、更新CMS看板、調度資源等
        
        execution_result = {
            "action_id": action_id,
            "status": "executed",
            "executed_at": datetime.now().isoformat(),
            "execution_time": "2.3s",
            "parameters_used": parameters,
            "result": {
                "success": True,
                "message": f"行動 {action_id} 已成功執行",
                "affected_systems": ["CMS看板系統", "匝道管制系統"],
                "estimated_effect_time": "5-10分鐘"
            }
        }
        
        return execution_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"執行行動失敗: {str(e)}")

@router.get("/dashboard-data")
async def get_dashboard_data():
    """獲取管理者儀表板完整資料"""
    try:
        current_time = datetime.now()
        
        # 整合所有儀表板需要的資料
        dashboard_data = {
            "system_overview": {
                "status": "operational",
                "active_alerts": 3,
                "system_load": 45.2,
                "data_freshness": "30s ago"
            },
            "traffic_summary": {
                "total_vehicles": 45280,
                "average_speed": 78.5,
                "congestion_hotspots": 5,
                "incident_count": 2
            },
            "shockwave_status": {
                "active_shockwaves": 3,
                "high_risk_areas": ["國道1號北向", "國道3號南向"],
                "prediction_accuracy": 0.87
            },
            "recent_actions": [
                {
                    "time": "10:30",
                    "action": "匝道管制啟動",
                    "location": "台北系統",
                    "status": "active"
                },
                {
                    "time": "10:15", 
                    "action": "CMS訊息更新",
                    "location": "全線",
                    "status": "completed"
                }
            ],
            "performance_metrics": {
                "prediction_accuracy": 0.87,
                "alert_response_time": "45s",
                "system_availability": "99.8%"
            },
            "timestamp": current_time.isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取儀表板資料失敗: {str(e)}")

@router.get("/alerts/active")
async def get_active_alerts():
    """獲取當前活躍警報 - 基於真實檢測結果"""
    try:
        from .shockwave import get_active_shockwaves
        
        # 獲取真實的衝擊波檢測結果
        shockwave_data = await get_active_shockwaves()
        active_alerts = []
        
        # 將衝擊波檢測轉換為警報格式
        if shockwave_data.get("shockwaves"):
            for shock in shockwave_data["shockwaves"][:3]:  # 只顯示前3個最重要的
                severity = "high" if shock.get("intensity", 0) >= 6.0 else "medium"
                
                alert = {
                    "id": f"shock_{shock.get('station_id', 'unknown')}_{shock.get('shock_start_time', '').replace(':', '')}",
                    "type": "shockwave",
                    "severity": severity,
                    "title": f"{shock.get('location_name', '未知測站')} 震波警報",
                    "description": f"檢測到真實交通衝擊波，強度: {shock.get('intensity', 0):.1f}，速度下降: {shock.get('speed_drop', 0):.0f} km/h",
                    "location": {
                        "lat": float(shock.get("latitude", 0)), 
                        "lng": float(shock.get("longitude", 0))
                    },
                    "created_at": shock.get("shock_occurrence_time", datetime.now().isoformat()),
                    "estimated_duration": int(shock.get("shock_duration", 30))
                }
                active_alerts.append(alert)
        
        # 如果沒有真實檢測結果，添加一個系統狀態警告
        if not active_alerts:
            current_time = datetime.now()
            active_alerts.append({
                "id": "system_001",
                "type": "system",
                "severity": "low",
                "title": "系統正常運行",
                "description": "目前未檢測到衝擊波，系統運行正常",
                "location": None,
                "created_at": current_time.isoformat(),
                "estimated_duration": None
            })
        
        return {
            "alerts": active_alerts,
            "total_count": len(active_alerts),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取活躍警報失敗: {str(e)}")

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """確認警報"""
    try:
        return {
            "alert_id": alert_id,
            "status": "acknowledged",
            "acknowledged_at": datetime.now().isoformat(),
            "acknowledged_by": "admin_user"  # 實際應該從認證中獲取
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"確認警報失敗: {str(e)}")

@router.get("/statistics/daily")
async def get_daily_statistics():
    """獲取每日統計資料"""
    try:
        # 計算每日統計
        stats = {
            "date": datetime.now().date().isoformat(),
            "traffic_volume": 1250000,  # 總車流量
            "average_speed": 76.8,
            "total_incidents": 23,
            "shockwaves_detected": 45,
            "prediction_accuracy": 0.86,
            "system_uptime": "99.9%",
            "alerts_generated": 67,
            "actions_executed": 12,
            "fuel_saved_estimate": "15,000L",  # 預估節省燃油
            "time_saved_estimate": "2,500 hours"  # 預估節省時間
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取每日統計失敗: {str(e)}")
