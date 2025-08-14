from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd

# 導入你的資料處理模組
import sys
import os
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

from src.data.dataLoad import load_traffic_data
from src.utils.config_loader import load_config_with_env

router = APIRouter()

# 資料模型
from pydantic import BaseModel

class TrafficData(BaseModel):
    timestamp: datetime
    station_id: str
    flow: float
    median_speed: float
    avg_travel_time: float
    location: Optional[dict] = None

class StationInfo(BaseModel):
    station_id: str
    name: str
    location: dict
    highway: str
    direction: str

@router.get("/current")
async def get_current_traffic():
    """獲取當前交通狀況"""
    try:
        # 使用真實的 TDX 交通資料系統
        from src.data.tdx_tisc_mix_system import OptimizedIntegratedDataCollectionSystem
        
        # 初始化資料收集系統
        data_system = OptimizedIntegratedDataCollectionSystem()
        
        # 獲取最新的即時資料
        latest_data = data_system.get_latest_data_for_shockwave()
        
        current_time = datetime.now()
        stations = []
        
        if latest_data is not None and not latest_data.empty:
            # 轉換真實資料為 API 格式
            for idx, row in latest_data.iterrows():
                try:
                    station_data = {
                        "id": str(row.get('station_id', idx)),
                        "name": row.get('station_name', f"監測站 {idx}"),
                        "latitude": float(row.get('latitude', 25.0)),
                        "longitude": float(row.get('longitude', 121.0)),
                        "flow": float(row.get('volume', 0)) if row.get('volume') else 0,
                        "speed": float(row.get('speed', 0)) if row.get('speed') else 0,
                        "timestamp": current_time.isoformat()
                    }
                    stations.append(station_data)
                except Exception as e:
                    continue  # 跳過有問題的資料行
        
        # 如果沒有真實資料，提供詳細信息
        if not stations:
            return {
                "stations": [],
                "total_count": 0,
                "last_updated": current_time.isoformat(),
                "message": "正在等待 TDX 即時交通資料...",
                "data_source": "TDX_realtime",
                "status": "waiting_for_data",
                "note": "台北站和桃園站的虛擬資料已移除，系統正在收集真實交通數據"
            }
        
        return {
            "stations": stations,
            "total_count": len(stations),
            "last_updated": current_time.isoformat(),
            "data_source": "TDX_realtime"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取交通資料失敗: {str(e)}")

@router.get("/history")
async def get_traffic_history(
    station_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100
):
    """獲取歷史交通資料"""
    try:
        # 設定預設時間範圍
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(hours=24)
            
        # 這裡實作歷史資料查詢邏輯
        # 實際實作需要連接到你的資料儲存系統
        
        return {
            "message": "歷史資料查詢",
            "station_id": station_id,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
            "data": []  # 實際資料
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取歷史資料失敗: {str(e)}")

@router.get("/stations", response_model=List[StationInfo])
async def get_stations():
    """獲取所有監測站點資訊"""
    try:
        # 從真實的交通資料系統獲取站點資訊
        from src.data.tdx_tisc_mix_system import OptimizedIntegratedDataCollectionSystem
        
        data_system = OptimizedIntegratedDataCollectionSystem()
        latest_data = data_system.get_latest_data_for_shockwave()
        
        stations = []
        
        if latest_data is not None and not latest_data.empty:
            # 從真實資料中提取站點資訊
            for idx, row in latest_data.iterrows():
                try:
                    station = StationInfo(
                        station_id=str(row.get('station_id', idx)),
                        name=row.get('station_name', f"監測站 {idx}"),
                        location={
                            "lat": float(row.get('latitude', 25.0)),
                            "lng": float(row.get('longitude', 121.0))
                        },
                        highway=row.get('highway', '國道1號'),
                        direction=row.get('direction', '未知')
                    )
                    stations.append(station)
                except Exception as e:
                    continue  # 跳過有問題的資料行
        
        # 如果沒有真實資料，返回空列表
        return stations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取站點資訊失敗: {str(e)}")

@router.get("/station/{station_id}")
async def get_station_detail(station_id: str):
    """獲取特定站點詳細資訊"""
    try:
        # 實作特定站點查詢邏輯
        return {
            "station_id": station_id,
            "current_traffic": {},
            "recent_trends": {},
            "alerts": []
        }
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"站點 {station_id} 不存在")
