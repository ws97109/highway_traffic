from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os
import pandas as pd
import numpy as np
import glob
import logging

# 導入後端模組
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

from src.detection.final_optimized_detector import FinalOptimizedShockDetector
from src.detection.realtime_adaptive_detector import RealtimeAdaptiveShockDetector
from src.prediction.realtime_shock_predictor import RealtimeShockPredictor
from src.core.shockwave_calculator import ShockwaveCalculator

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
                    'id': int(row['ID']),  # 確保轉換為Python int
                    'station_id': str(row['編號']),
                    'direction': str(row['方向']),
                    'start_ic': str(row['交流道(起)']),
                    'end_ic': str(row['交流道(迄)']),
                    'latitude': float(lat),
                    'longitude': float(lng),
                    'name': f"{row['交流道(起)']} - {row['交流道(迄)']}"
                }
                stations.append(station)
            except (ValueError, TypeError):
                continue
                
        return stations
    except Exception as e:
        print(f"載入測站數據失敗: {e}")
        return []

def find_station_info(station_id, stations_info):
    """精確匹配站點資訊"""
    # 直接匹配
    for info in stations_info:
        if info['station_id'] == station_id:
            return info
    
    # 處理格式差異：01F0339S -> 01F-033.9S
    try:
        # 解析站點ID：01F0339S
        if len(station_id) >= 8 and station_id.startswith(('01F', '03F')):
            highway = station_id[:3]  # 01F 或 03F
            km_part = station_id[3:7]  # 0339
            direction = station_id[-1]  # S 或 N
            
            # 轉換為標準格式：01F-033.9S
            km_major = km_part[:3].lstrip('0') or '0'  # 033 -> 33
            km_minor = km_part[3]  # 9
            
            standard_format = f"{highway}-{km_major}.{km_minor}{direction}"
            
            # 尋找匹配
            for info in stations_info:
                if info['station_id'] == standard_format:
                    return info
                    
            # 嘗試其他可能的格式
            alt_formats = [
                f"{highway}-0{km_major}.{km_minor}{direction}",  # 01F-033.9S
                f"{highway}-{km_major}{direction}",              # 01F-33S
                f"{highway}0{km_major}.{km_minor}{direction}",   # 01F033.9S
            ]
            
            for alt_format in alt_formats:
                for info in stations_info:
                    if info['station_id'] == alt_format:
                        return info
    except:
        pass
    
    return None

# shockwave.py 的關鍵修改部分
# 在原有的 get_active_shockwaves 函數中替換計算邏輯

@router.get("/active", response_model=dict)
async def get_active_shockwaves():
    """獲取當前活躍的衝擊波 - 使用真實檢測系統（含熵條件驗證）"""
    try:
        current_time = datetime.now()
        
        try:
            # 1. 初始化檢測器、預測器和計算器
            detector = RealtimeAdaptiveShockDetector()
            calculator = ShockwaveCalculator()  # 使用改進的計算器
            predictor = RealtimeShockPredictor(
                data_dir=os.path.join(root_dir, 'data')
            )
            
            # 2. 獲取最新的即時資料檔案
            realtime_dir = os.path.join(root_dir, 'data', 'realtime_data')
            if not os.path.exists(realtime_dir):
                raise Exception("即時資料目錄不存在，請確保 TDX 系統正在運行")
            
            pattern = os.path.join(realtime_dir, "realtime_shock_data_*.csv")
            data_files = sorted(glob.glob(pattern), reverse=True)
            
            if not data_files:
                raise Exception("沒有找到即時資料檔案，請確保 TDX 資料收集器正在運行")
            
            latest_file = data_files[0]
            file_age_minutes = (current_time - datetime.fromtimestamp(os.path.getmtime(latest_file))).total_seconds() / 60
            
            if file_age_minutes > 10:
                raise Exception(f"最新資料檔案過時 ({file_age_minutes:.1f} 分鐘前)，請檢查 TDX 收集器狀態")
            
            # 3. 讀取並處理資料
            df = pd.read_csv(latest_file)
            if df.empty:
                raise Exception("資料檔案為空")
            
            # 4. 使用檢測器進行衝擊波分析
            detected_shocks = []
            stations = df['station'].unique()

            print(f"🔍 開始檢測 {len(stations)} 個測站...")

            for station in stations:
                station_data = df[df['station'] == station].sort_values(['hour', 'minute'])

                if len(station_data) >= 3:
                    try:
                        shocks = detector.detect_realtime_shocks(station_data)

                        if shocks:
                            print(f"✅ 測站 {station}: 檢測到 {len(shocks)} 個衝擊波")

                        for shock in shocks:
                            shock['station'] = station
                            shock['detection_time'] = current_time
                            detected_shocks.append(shock)
                    except Exception as e:
                        print(f"❌ 測站 {station} 檢測失敗: {e}")
                        continue

            print(f"📊 總共檢測到 {len(detected_shocks)} 個衝擊波")
            
            # 5. 載入測站位置資訊
            stations_info = load_station_data()
            print(f"📍 載入了 {len(stations_info)} 個測站")
            
            # 6. 轉換為API格式（含熵條件驗證和稀疏波標記）
            active_shockwaves_data = []
            filtered_count = 0  # 被過濾掉的數量
            rarefaction_count = 0  # 稀疏波數量
            
            for i, shock in enumerate(detected_shocks):
                station = shock.get('station', '')
                print(f"🔍 處理衝擊波 {i+1}: 測站 {station}")
                
                # 查找測站資訊
                station_info = find_station_info(station, stations_info)
                
                # === 使用改進的文獻公式計算衝擊波參數 ===
                
                speed_drop = float(shock.get('speed_drop', 0))
                initial_speed = float(shock.get('initial_speed', 70))
                final_speed = float(shock.get('final_speed', 30))
                initial_flow = float(shock.get('max_flow', 1000))
                final_flow = float(shock.get('min_flow', 200))
                
                # 計算密度
                initial_density = calculator.calculate_density_from_flow_speed(initial_flow, initial_speed)
                final_density = calculator.calculate_density_from_flow_speed(final_flow, final_speed)

                if initial_density is None or final_density is None:
                    print(f"⚠️ 無法計算密度 - 測站 {station}")
                    continue

                # 🔥 關鍵：計算衝擊波速度並驗證 Lax 熵條件
                wave_result = calculator.calculate_shockwave_speed(
                    initial_flow, initial_density,
                    final_flow, final_density,
                    verify_entropy=True  # 啟用熵條件驗證
                )

                # 🚫 過濾：不符合熵條件的不顯示
                if not wave_result.get('valid', False):
                    print(f"❌ 過濾掉不符合熵條件的衝擊波 - 測站 {station}: {wave_result.get('reason', 'Unknown')}")
                    filtered_count += 1
                    continue

                wave_speed = wave_result['speed']
                wave_type = wave_result['type']  # 'shock' 或 'rarefaction'
                
                # 🎨 稀疏波標記
                is_rarefaction = (wave_type == 'rarefaction')
                if is_rarefaction:
                    rarefaction_count += 1
                
                # 計算隊列增長率
                growth_rate = calculator.calculate_queue_growth_rate(initial_flow, final_flow)
                
                # 使用改進的強度計算
                density_increase = final_density - initial_density
                flow_drop = initial_flow - final_flow
                
                intensity_result = calculator.calculate_shock_intensity(
                    speed_drop, 
                    density_increase, 
                    flow_drop
                )
                intensity = intensity_result['intensity']
                
                # 信心度
                confidence = 0.9 if shock.get('level') == 'severe' else 0.8 if shock.get('level') == 'moderate' else 0.7
                
                # 位置資訊
                if station_info:
                    latitude = station_info['latitude']
                    longitude = station_info['longitude']
                    location_name = station_info['name']
                else:
                    latitude = 25.0330 + (i * 0.01)
                    longitude = 121.5654 + (i * 0.01)
                    location_name = f"測站 {station}"
                
                # 構建衝擊波時間
                shock_start_time = shock.get('start_time', '00:00')
                shock_end_time = shock.get('end_time', '00:00')
                shock_date = df.iloc[0]['date'] if not df.empty else current_time.strftime('%Y/%m/%d')
                
                try:
                    start_hour, start_minute = map(int, shock_start_time.split(':'))
                    shock_datetime = datetime.strptime(f"{shock_date} {start_hour:02d}:{start_minute:02d}", '%Y/%m/%d %H:%M')
                    
                    end_hour, end_minute = map(int, shock_end_time.split(':'))
                    shock_end_datetime = datetime.strptime(f"{shock_date} {end_hour:02d}:{end_minute:02d}", '%Y/%m/%d %H:%M')
                    
                    shock_duration = calculator.calculate_shock_duration_from_times(shock_datetime, shock_end_datetime)
                except:
                    shock_datetime = current_time
                    shock_duration = float(shock.get('duration', 0))
                
                # 使用改進的影響範圍計算
                affected_area_result = calculator.calculate_affected_area(
                    wave_speed=wave_speed,
                    duration_minutes=shock_duration,
                    num_lanes=4
                )
                affected_area = affected_area_result['longitudinal_km']
                
                # 使用考慮衰減的到達時間估算
                arrival_result = calculator.estimate_arrival_time_with_decay(
                    distance_km=5.0,
                    initial_wave_speed=wave_speed,
                    decay_rate=0.95,
                    current_time=shock_datetime
                )
                
                if not arrival_result['dissipated']:
                    estimated_arrival_time = arrival_result['arrival_time']
                    arrival_minutes = arrival_result['travel_minutes']
                else:
                    estimated_arrival_time = shock_datetime
                    arrival_minutes = 0
                
                # 🎨 構建 API 回應（含稀疏波標記）
                shockwave_data = {
                    "id": f"real_sw_{station}_{shock_start_time.replace(':', '')}",
                    "station_id": station,
                    "location_name": location_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    
                    # === 波類型與熵條件資訊 ===
                    "wave_type": wave_type,  # 'shock' 或 'rarefaction'
                    "is_rarefaction": is_rarefaction,
                    "satisfies_entropy": wave_result['satisfies_entropy'],
                    "entropy_validation": wave_result.get('reason', ''),
                    
                    # 🎨 稀疏波視覺標記
                    "display_color": "#FF6B6B" if not is_rarefaction else "#4ECDC4",  # 紅色=衝擊波，青色=稀疏波
                    "display_icon": "⚠️" if not is_rarefaction else "📈",
                    "display_label": "衝擊波" if not is_rarefaction else "稀疏波",
                    "border_style": "solid" if not is_rarefaction else "dashed",  # 實線=衝擊波，虛線=稀疏波
                    
                    # === 使用改進公式計算的參數 ===
                    "intensity": round(float(intensity), 2),
                    "intensity_breakdown": {
                        "speed_factor": round(intensity_result['speed_factor'], 3),
                        "density_factor": round(intensity_result['density_factor'], 3),
                        "flow_factor": round(intensity_result['flow_factor'], 3),
                        "dominant_factor": intensity_result['dominant_factor']
                    },
                    "propagation_speed": round(abs(wave_speed), 2),
                    "wave_speed": round(float(wave_speed), 2),
                    "wave_direction": "upstream" if wave_speed < 0 else "downstream",
                    "estimated_arrival": estimated_arrival_time.isoformat(),
                    "estimated_arrival_minutes": round(arrival_minutes, 1),
                    "effective_wave_speed": round(arrival_result.get('effective_speed', wave_speed), 2),
                    "decay_factor": round(arrival_result.get('decay_factor', 1.0), 3),
                    
                    # === 影響範圍（基於物理）===
                    "affected_area": round(float(affected_area), 2),
                    "affected_area_details": {
                        "longitudinal_km": round(affected_area_result['longitudinal_km'], 2),
                        "lateral_km": round(affected_area_result['lateral_km'], 3),
                        "area_km2": round(affected_area_result['area_km2'], 3),
                        "num_lanes": affected_area_result['num_lanes_affected']
                    },
                    "shock_duration": round(float(shock_duration), 1),
                    
                    # === 流量和密度資訊 ===
                    "speed_drop": round(float(speed_drop), 1),
                    "initial_speed": round(float(initial_speed), 1),
                    "final_speed": round(float(final_speed), 1),
                    "initial_flow": round(float(initial_flow), 1),
                    "final_flow": round(float(final_flow), 1),
                    "initial_density": round(float(initial_density), 2),
                    "final_density": round(float(final_density), 2),
                    "density_change": round(float(density_increase), 2),
                    "queue_growth_rate": round(float(growth_rate), 1),
                    
                    # === 其他資訊 ===
                    "description": _generate_description(
                        station, location_name, intensity, wave_speed, wave_type
                    ),
                    "confidence": round(float(confidence), 3),
                    "detection_method": "RealtimeAdaptiveDetector + EntropyValidation",
                    "shock_occurrence_time": shock_datetime.isoformat(),
                    "shock_start_time": shock_start_time,
                    "shock_end_time": shock_end_time,
                    "data_source_time": datetime.fromtimestamp(os.path.getmtime(latest_file)).isoformat(),
                    "alternative_routes": []
                }
                
                # 為高強度衝擊波（非稀疏波）添加替代路線建議
                if intensity >= 6.0 and not is_rarefaction:
                    shockwave_data["alternative_routes"] = [
                        {
                            "id": f"alt_real_{station}",
                            "name": "建議使用替代路線",
                            "additional_time": max(10, int(intensity * 3)),
                            "avoidance_success": min(90, int(confidence * 100))
                        }
                    ]
                
                active_shockwaves_data.append(shockwave_data)
            
            # 7. 回傳結果
            response_data = {
                "shockwaves": active_shockwaves_data,
                "count": len(active_shockwaves_data),
                "last_updated": current_time.isoformat(),
                "data_source": "real_time_detector_with_entropy_validation",
                "data_file_used": os.path.basename(latest_file),
                "data_file_age_minutes": round(file_age_minutes, 1),
                "total_stations_analyzed": len(stations),
                "detection_summary": {
                    "files_checked": len(data_files),
                    "latest_file": os.path.basename(latest_file),
                    "stations_with_data": len(stations),
                    "total_detected": len(detected_shocks),
                    "valid_shocks": len([s for s in active_shockwaves_data if not s['is_rarefaction']]),
                    "rarefaction_waves": rarefaction_count,
                    "filtered_invalid": filtered_count
                },
                "legend": {
                    "shock_wave": {
                        "color": "#FF6B6B",
                        "icon": "⚠️",
                        "label": "衝擊波",
                        "description": "密度增加，向上游傳播"
                    },
                    "rarefaction_wave": {
                        "color": "#4ECDC4",
                        "icon": "📈",
                        "label": "稀疏波",
                        "description": "密度降低，車流加速"
                    }
                }
            }
            
            return response_data
            
        except Exception as detection_error:
            logger = logging.getLogger(__name__)
            logger.error(f"真實衝擊波檢測失敗: {detection_error}")
            
            stations = load_station_data()
            
            return {
                "shockwaves": [],
                "count": 0,
                "last_updated": current_time.isoformat(),
                "data_source": "detector_failed",
                "error": str(detection_error),
                "available_stations": len(stations),
                "status": "檢測系統暫時無法使用，請檢查資料收集狀態"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取衝擊波資料失敗: {str(e)}")


def _generate_description(station, location_name, intensity, wave_speed, wave_type):
    """生成衝擊波描述"""
    if wave_type == 'rarefaction':
        return (f"在測站 {station} ({location_name}) 檢測到交通稀疏波 "
                f"(車流加速, 波速: {wave_speed:.1f} km/h)")
    else:
        return (f"在測站 {station} ({location_name}) 檢測到交通衝擊波 "
                f"(強度: {intensity:.1f}/10, 波速: {wave_speed:.1f} km/h)")