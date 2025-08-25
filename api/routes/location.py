from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
import sys
import os

# 導入你的後端模組
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

from src.prediction.location_based_predictor import LocationBasedShockPredictor
from src.utils.config_loader import load_config_with_env

router = APIRouter()

# 資料模型
from pydantic import BaseModel

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None

class NearbyStationsResponse(BaseModel):
    station_id: str
    name: str
    latitude: float
    longitude: float
    distance_km: float
    current_flow: Optional[float] = None
    current_speed: Optional[float] = None
    status: str

class LocationPredictionResponse(BaseModel):
    location: LocationRequest
    nearby_stations: List[NearbyStationsResponse]
    risk_assessment: dict
    recommendations: List[str]
    estimated_impact: dict

class RouteAnalysisRequest(BaseModel):
    origin: LocationRequest
    destination: LocationRequest
    departure_time: Optional[datetime] = None

class RouteAnalysisResponse(BaseModel):
    route_info: dict
    traffic_predictions: List[dict]
    shock_wave_risks: List[dict]
    alternative_routes: List[dict]
    recommendations: dict

# 全域變數 (實際使用時應該從依賴注入取得)
location_predictor = None

def get_location_predictor():
    """取得位置預測器實例"""
    global location_predictor
    if location_predictor is None:
        try:
            # 載入配置
            config = load_config_with_env('data/config/system_config.json')
            google_api_key = config['location_config.json']['google_maps']['api_key']
            location_config = config['location_config.json']['location_settings']
            
            # 初始化預測器
            location_predictor = LocationBasedShockPredictor(
                data_dir='data',
                google_api_key=google_api_key,
                config=location_config
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"位置預測器初始化失敗: {str(e)}")
    
    return location_predictor

@router.post("/analyze", response_model=LocationPredictionResponse)
async def analyze_location(
    location_request: LocationRequest,
    max_distance_km: float = Query(20, description="最大搜尋距離(公里)")
):
    """分析指定位置的交通衝擊波風險"""
    try:
        predictor = get_location_predictor()
        
        # 獲取附近站點
        nearby_stations = predictor.find_nearby_stations(
            latitude=location_request.latitude,
            longitude=location_request.longitude,
            max_distance_km=max_distance_km
        )
        
        # 轉換為回應格式
        station_responses = []
        for station in nearby_stations:
            station_responses.append(NearbyStationsResponse(
                station_id=station['station_id'],
                name=station['name'],
                latitude=station['latitude'],
                longitude=station['longitude'],
                distance_km=station['distance_km'],
                current_flow=station.get('current_flow'),
                current_speed=station.get('current_speed'),
                status=station.get('status', 'unknown')
            ))
        
        # 風險評估
        risk_assessment = predictor.assess_location_risk(
            latitude=location_request.latitude,
            longitude=location_request.longitude,
            nearby_stations=nearby_stations
        )
        
        # 產生建議
        recommendations = predictor.generate_recommendations(
            location_request.latitude,
            location_request.longitude,
            risk_assessment
        )
        
        # 預估影響
        estimated_impact = predictor.estimate_impact(
            location_request.latitude,
            location_request.longitude,
            nearby_stations
        )
        
        return LocationPredictionResponse(
            location=location_request,
            nearby_stations=station_responses,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
            estimated_impact=estimated_impact
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"位置分析失敗: {str(e)}")

@router.post("/route-analysis", response_model=RouteAnalysisResponse)
async def analyze_route(route_request: RouteAnalysisRequest):
    """分析路線的交通衝擊波風險"""
    try:
        predictor = get_location_predictor()
        
        # 路線分析
        route_analysis = predictor.analyze_route(
            origin_lat=route_request.origin.latitude,
            origin_lng=route_request.origin.longitude,
            dest_lat=route_request.destination.latitude,
            dest_lng=route_request.destination.longitude,
            departure_time=route_request.departure_time
        )
        
        return RouteAnalysisResponse(
            route_info=route_analysis['route_info'],
            traffic_predictions=route_analysis['traffic_predictions'],
            shock_wave_risks=route_analysis['shock_wave_risks'],
            alternative_routes=route_analysis['alternative_routes'],
            recommendations=route_analysis['recommendations']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"路線分析失敗: {str(e)}")

@router.get("/stations/nearby")
async def get_nearby_stations(
    lat: float = Query(..., description="緯度"),
    lng: float = Query(..., description="經度"),
    radius: float = Query(10, description="搜尋半徑(公里)")
):
    """取得附近的監測站點"""
    try:
        predictor = get_location_predictor()
        
        stations = predictor.find_nearby_stations(
            latitude=lat,
            longitude=lng,
            max_distance_km=radius
        )
        
        return {
            "total": len(stations),
            "stations": stations,
            "search_center": {"lat": lat, "lng": lng},
            "search_radius_km": radius
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得附近站點失敗: {str(e)}")

@router.post("/geocode")
async def geocode_address(address: str):
    """地址轉座標"""
    try:
        predictor = get_location_predictor()
        
        coordinates = predictor.geocode_address(address)
        
        if coordinates:
            return {
                "address": address,
                "latitude": coordinates[0],
                "longitude": coordinates[1],
                "success": True
            }
        else:
            return {
                "address": address,
                "error": "無法找到該地址",
                "success": False
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"地址轉座標失敗: {str(e)}")

@router.post("/reverse-geocode")
async def reverse_geocode(lat: float, lng: float):
    """座標轉地址"""
    try:
        predictor = get_location_predictor()
        
        address = predictor.reverse_geocode(lat, lng)
        
        return {
            "latitude": lat,
            "longitude": lng,
            "address": address,
            "success": address is not None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"座標轉地址失敗: {str(e)}")

@router.get("/traffic-forecast")
async def get_traffic_forecast(
    lat: float = Query(..., description="緯度"),
    lng: float = Query(..., description="經度"),
    horizon_minutes: int = Query(60, description="預測時間範圍(分鐘)")
):
    """取得指定位置的交通預測"""
    try:
        predictor = get_location_predictor()
        
        # 找到最近的站點
        nearby_stations = predictor.find_nearby_stations(lat, lng, max_distance_km=5)
        
        if not nearby_stations:
            raise HTTPException(status_code=404, detail="附近沒有監測站點")
        
        # 取得最近站點的預測
        closest_station = nearby_stations[0]
        
        # 這裡應該調用你的交通預測模型
        forecast = {
            "station_id": closest_station['station_id'],
            "station_name": closest_station['name'],
            "distance_km": closest_station['distance_km'],
            "forecast_horizon_minutes": horizon_minutes,
            "predictions": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "predicted_flow": 1200,
                    "predicted_speed": 85,
                    "confidence": 0.85,
                    "shock_wave_probability": 0.15
                }
                # 這裡應該是實際的預測資料
            ]
        }
        
        return forecast
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"交通預測失敗: {str(e)}")

@router.get("/risk-map")
async def get_risk_map(
    north: float = Query(..., description="北邊界緯度"),
    south: float = Query(..., description="南邊界緯度"),  
    east: float = Query(..., description="東邊界經度"),
    west: float = Query(..., description="西邊界經度")
):
    """取得區域風險地圖資料"""
    try:
        predictor = get_location_predictor()
        
        # 產生風險地圖網格
        risk_grid = predictor.generate_risk_grid(
            north_lat=north,
            south_lat=south,
            east_lng=east,
            west_lng=west,
            grid_size=50  # 50x50 網格
        )
        
        return {
            "bounds": {
                "north": north,
                "south": south,
                "east": east,
                "west": west
            },
            "grid_size": 50,
            "risk_data": risk_grid,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"風險地圖產生失敗: {str(e)}")

@router.post("/user-location")
async def update_user_location(
    user_id: str,
    location: LocationRequest,
    enable_notifications: bool = True
):
    """更新使用者位置並設定通知"""
    try:
        predictor = get_location_predictor()
        
        # 儲存使用者位置
        result = predictor.update_user_location(
            user_id=user_id,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address,
            enable_notifications=enable_notifications
        )
        
        return {
            "user_id": user_id,
            "location": location,
            "notifications_enabled": enable_notifications,
            "nearby_risks": result.get('nearby_risks', []),
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新使用者位置失敗: {str(e)}")