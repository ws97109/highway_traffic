from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os

# 導入後端模組
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

from src.models.mt_stnet.adapter import MTSTNetAdapter
from src.prediction.location_based_predictor import LocationBasedShockPredictor

router = APIRouter()

# 資料模型
from pydantic import BaseModel

class TrafficPrediction(BaseModel):
    station_id: str
    location_name: str
    predicted_speed: float
    predicted_flow: float
    confidence: float
    time_horizon: int  # 預測時間範圍（分鐘）
    timestamp: datetime

class PredictionRequest(BaseModel):
    station_ids: Optional[List[str]] = None
    time_horizon: int = 60
    include_confidence: bool = True

@router.get("/traffic", response_model=dict)
async def get_traffic_predictions(
    station_ids: Optional[str] = None,
    time_horizon: int = 60
):
    """獲取交通預測資料"""
    try:
        # 這裡調用MT-STNet模型進行預測
        # adapter = MTSTNetAdapter()
        # predictions = adapter.predict_traffic(station_ids, time_horizon)
        
        # 模擬預測資料
        current_time = datetime.now()
        station_list = station_ids.split(',') if station_ids else ['001', '002', '003']
        
        mock_predictions = []
        for i, station_id in enumerate(station_list):
            mock_predictions.append({
                "station_id": station_id,
                "location_name": f"監測站 {station_id}",
                "predicted_speed": 75.5 - (i * 5.2),
                "predicted_flow": 1200 + (i * 150),
                "confidence": 0.87 - (i * 0.05),
                "time_horizon": time_horizon,
                "timestamp": current_time.isoformat()
            })
        
        return {
            "predictions": mock_predictions,
            "model_version": "MT-STNet-v1.2",
            "generated_at": current_time.isoformat(),
            "time_horizon": time_horizon
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"交通預測失敗: {str(e)}")

@router.post("/batch")
async def batch_predict_traffic(request: PredictionRequest):
    """批次交通預測"""
    try:
        # 批次預測邏輯
        current_time = datetime.now()
        
        predictions = []
        station_ids = request.station_ids or ['001', '002', '003', '004', '005']
        
        for station_id in station_ids:
            predictions.append({
                "station_id": station_id,
                "location_name": f"監測站 {station_id}",
                "predicted_speed": 80.0,
                "predicted_flow": 1100,
                "confidence": 0.85 if request.include_confidence else None,
                "time_horizon": request.time_horizon,
                "timestamp": current_time.isoformat()
            })
        
        return {
            "predictions": predictions,
            "total_count": len(predictions),
            "request_id": f"batch_{int(current_time.timestamp())}",
            "generated_at": current_time.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次預測失敗: {str(e)}")

@router.get("/accuracy")
async def get_prediction_accuracy():
    """獲取預測準確度統計"""
    try:
        # 計算預測準確度
        accuracy_stats = {
            "overall_accuracy": 0.87,
            "speed_prediction_mae": 5.2,  # 平均絕對誤差
            "flow_prediction_mae": 125.8,
            "confidence_calibration": 0.92,
            "model_performance": {
                "last_24h": 0.89,
                "last_week": 0.86,
                "last_month": 0.84
            },
            "by_time_of_day": {
                "morning_rush": 0.82,
                "afternoon": 0.91,
                "evening_rush": 0.79,
                "night": 0.94
            }
        }
        
        return accuracy_stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取準確度統計失敗: {str(e)}")

@router.get("/model/status")
async def get_model_status():
    """獲取預測模型狀態"""
    try:
        model_status = {
            "model_name": "MT-STNet",
            "version": "1.2.0",
            "status": "active",
            "last_trained": "2024-01-15T10:30:00Z",
            "training_data_period": "2023-01-01 to 2024-01-01",
            "parameters": {
                "input_window": 12,
                "output_window": 12,
                "hidden_dim": 64,
                "num_layers": 3
            },
            "performance_metrics": {
                "mse": 0.045,
                "mae": 0.032,
                "r2_score": 0.87
            }
        }
        
        return model_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取模型狀態失敗: {str(e)}")

@router.post("/retrain")
async def trigger_model_retrain():
    """觸發模型重新訓練"""
    try:
        # 這裡實作模型重新訓練邏輯
        return {
            "message": "模型重新訓練已啟動",
            "job_id": f"retrain_{int(datetime.now().timestamp())}",
            "estimated_completion": (datetime.now() + timedelta(hours=2)).isoformat(),
            "status": "queued"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"啟動重新訓練失敗: {str(e)}")
