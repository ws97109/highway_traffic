#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import os
import json
import requests
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# 導入現有的系統
from .realtime_shock_predictor import RealtimeShockPredictor
from ..systems.shock_warning_system import ShockWarningSystem

class LocationBasedShockPredictor:
    """
    基於地理位置的衝擊波預測系統
    
    功能：
    1. Google Maps API整合
    2. 用戶位置獲取與管理
    3. 最近站點計算
    4. 個人化衝擊波預測
    5. 基於位置的智能預警
    """
    
    def __init__(self, data_dir: str, google_api_key: str, config: Dict = None):
        """初始化基於位置的預測系統"""
        
        self.data_dir = data_dir
        self.google_api_key = google_api_key
        self.location_dir = os.path.join(data_dir, "locations")
        self.user_dir = os.path.join(data_dir, "users")
        
        # 建立目錄
        os.makedirs(self.location_dir, exist_ok=True)
        os.makedirs(self.user_dir, exist_ok=True)
        
        # 設定日誌
        self._setup_logging()
        
        # 配置參數
        default_config = {
            'max_distance_km': 20,          # 最大搜尋距離：20公里
            'location_cache_minutes': 30,   # 位置快取：30分鐘
            'prediction_radius_km': 50,     # 預測範圍：50公里
            'route_analysis': True,         # 路線分析功能
            'traffic_consideration': True,  # 考慮交通狀況
        }
        
        self.config = {**default_config, **(config or {})}
        
        # 初始化系統組件
        self.shock_predictor = RealtimeShockPredictor(data_dir)
        self.warning_system = ShockWarningSystem(data_dir)
        
        # 初始化資料庫
        self._init_location_database()
        
        # 載入站點資訊
        self.station_locations = self._load_station_locations()
        
        # 快取
        self.location_cache = {}
        self.geocoding_cache = {}
        self.route_cache = {}
        
        self.logger.info("📍 基於位置的衝擊波預測系統初始化完成")
        self.logger.info(f"🗺️ Google Maps API: {'已配置' if google_api_key else '未配置'}")
        self.logger.info(f"📊 站點數量: {len(self.station_locations)}")
        self.logger.info(f"📏 搜尋範圍: {self.config['max_distance_km']} 公里")

    def _setup_logging(self):
        """設定日誌"""
        log_file = os.path.join(self.data_dir, "logs", f"location_predictor_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('LocationPredictor')

    def _init_location_database(self):
        """初始化位置資料庫"""
        self.db_path = os.path.join(self.location_dir, "locations.db")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 用戶位置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    latitude REAL,
                    longitude REAL,
                    address TEXT,
                    update_time TEXT,
                    source TEXT DEFAULT 'gps'
                )
            ''')
            
            # 位置預測記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS location_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    user_latitude REAL,
                    user_longitude REAL,
                    nearest_station TEXT,
                    distance_km REAL,
                    prediction_count INTEGER,
                    max_warning_level TEXT,
                    created_time TEXT
                )
            ''')
            
            # 路線分析表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS route_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    origin_lat REAL,
                    origin_lng REAL,
                    destination_lat REAL,
                    destination_lng REAL,
                    route_stations TEXT,
                    total_distance_km REAL,
                    estimated_duration_minutes INTEGER,
                    affected_stations TEXT,
                    warning_summary TEXT,
                    created_time TEXT
                )
            ''')
            
            conn.commit()

    def _load_station_locations(self):
        """載入站點位置資訊"""
        # 檢查多個可能的路徑
        possible_paths = [
            os.path.join(self.data_dir, "Taiwan", "Etag.csv"),
            os.path.join(os.path.dirname(self.data_dir), "國道", "data", "Taiwan", "Etag.csv"),
            os.path.join(os.path.dirname(self.data_dir), "data", "Taiwan", "Etag.csv"),
            "/Users/weiqihong/Desktop/碩士班/碩一下/highway-traffic/data/Taiwan/Etag.csv",
            "/Users/weiqihong/Desktop/碩士班/碩一下/highway-traffic/data/Taiwan/Etag.csv"
        ]
        
        etag_file = None
        for path in possible_paths:
            if os.path.exists(path):
                etag_file = path
                self.logger.info(f"✅ 找到站點位置檔案: {path}")
                break
        
        if not etag_file:
            self.logger.warning("⚠️ 站點位置檔案未找到")
            self.logger.info(f"嘗試的路徑:")
            for path in possible_paths:
                self.logger.info(f"  - {path}")
            return {}

        try:
            df = pd.read_csv(etag_file, encoding='utf-8')
            
            stations = {}
            for _, row in df.iterrows():
                station_code = row['編號']
                if pd.isna(station_code):
                    continue
                
                # 轉換為標準格式
                clean_code = station_code.replace('-', '').replace('.', '')
                
                stations[clean_code] = {
                    'id': row['ID'],
                    'code': clean_code,
                    'original_code': station_code,
                    'direction': row['方向'],
                    'start_ic': row['交流道(起)'],
                    'end_ic': row['交流道(迄)'],
                    'latitude': float(row['緯度(北緯)']),
                    'longitude': float(row['經度(東經)']),
                    'readable_name': f"{row['交流道(起)']} → {row['交流道(迄)']} ({row['方向']}向)"
                }
            
            self.logger.info(f"✅ 載入 {len(stations)} 個站點位置")
            return stations
            
        except Exception as e:
            self.logger.error(f"❌ 載入站點位置失敗: {e}")
            return {}

    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """計算兩點間距離（公里）"""
        # 使用Haversine公式
        R = 6371  # 地球半徑（公里）
        
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """地址轉座標"""
        if address in self.geocoding_cache:
            return self.geocoding_cache[address]
        
        if not self.google_api_key:
            self.logger.warning("Google API Key未設定，無法進行地址轉座標")
            return None
        
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': self.google_api_key,
                'region': 'tw'  # 台灣區域偏好
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                coordinates = (location['lat'], location['lng'])
                
                # 快取結果
                self.geocoding_cache[address] = coordinates
                
                self.logger.info(f"📍 地址轉座標成功: {address} → {coordinates}")
                return coordinates
            else:
                self.logger.warning(f"地址轉座標失敗: {address} - {data.get('status', 'Unknown error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 地址轉座標錯誤: {e}")
            return None

    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """座標轉地址"""
        cache_key = f"{latitude:.6f},{longitude:.6f}"
        if cache_key in self.geocoding_cache:
            return self.geocoding_cache[cache_key]
        
        if not self.google_api_key:
            return f"位置: {latitude:.6f}, {longitude:.6f}"
        
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'latlng': f"{latitude},{longitude}",
                'key': self.google_api_key,
                'language': 'zh-TW'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                address = data['results'][0]['formatted_address']
                
                # 快取結果
                self.geocoding_cache[cache_key] = address
                
                return address
            else:
                return f"位置: {latitude:.6f}, {longitude:.6f}"
                
        except Exception as e:
            self.logger.error(f"❌ 座標轉地址錯誤: {e}")
            return f"位置: {latitude:.6f}, {longitude:.6f}"

    def find_nearest_stations(self, latitude: float, longitude: float, max_count: int = 5) -> List[Dict]:
        """找到最近的站點"""
        if not self.station_locations:
            return []
        
        distances = []
        
        for station_code, station_info in self.station_locations.items():
            distance = self.calculate_distance(
                latitude, longitude,
                station_info['latitude'], station_info['longitude']
            )
            
            if distance <= self.config['max_distance_km']:
                station_with_distance = station_info.copy()
                station_with_distance['distance_km'] = distance
                distances.append(station_with_distance)
        
        # 按距離排序
        distances.sort(key=lambda x: x['distance_km'])
        
        return distances[:max_count]

    def update_user_location(self, user_id: str, latitude: float, longitude: float, source: str = 'gps') -> bool:
        """更新用戶位置"""
        try:
            # 獲取地址
            address = self.reverse_geocode(latitude, longitude)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_locations 
                    (user_id, latitude, longitude, address, update_time, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    latitude,
                    longitude,
                    address,
                    datetime.now().isoformat(),
                    source
                ))
                conn.commit()
            
            # 更新快取
            self.location_cache[user_id] = {
                'latitude': latitude,
                'longitude': longitude,
                'address': address,
                'update_time': datetime.now(),
                'source': source
            }
            
            self.logger.info(f"📍 用戶位置已更新: {user_id} - {address}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 更新用戶位置失敗: {e}")
            return False

    def get_user_location(self, user_id: str) -> Optional[Dict]:
        """獲取用戶位置"""
        # 檢查快取
        if user_id in self.location_cache:
            cached = self.location_cache[user_id]
            if datetime.now() - cached['update_time'] < timedelta(minutes=self.config['location_cache_minutes']):
                return cached
        
        # 從資料庫載入
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT latitude, longitude, address, update_time, source
                    FROM user_locations 
                    WHERE user_id = ? 
                    ORDER BY update_time DESC 
                    LIMIT 1
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    location = {
                        'latitude': row[0],
                        'longitude': row[1],
                        'address': row[2],
                        'update_time': datetime.fromisoformat(row[3]),
                        'source': row[4]
                    }
                    
                    # 更新快取
                    self.location_cache[user_id] = location
                    return location
                
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 獲取用戶位置失敗: {e}")
            return None

    def predict_for_user_location(self, user_id: str, include_route_analysis: bool = True) -> Dict:
        """為用戶位置進行衝擊波預測"""
        # 獲取用戶位置
        user_location = self.get_user_location(user_id)
        if not user_location:
            return {
                'success': False,
                'error': '用戶位置未找到',
                'user_id': user_id
            }
        
        return self.predict_for_coordinates(
            user_location['latitude'], 
            user_location['longitude'],
            user_id=user_id,
            include_route_analysis=include_route_analysis
        )

    def predict_for_coordinates(self, latitude: float, longitude: float, user_id: str = None, 
                              include_route_analysis: bool = True) -> Dict:
        """為指定座標進行衝擊波預測"""
        try:
            # 1. 找到最近的站點
            nearest_stations = self.find_nearest_stations(latitude, longitude)
            
            if not nearest_stations:
                return {
                    'success': False,
                    'error': f'附近{self.config["max_distance_km"]}公里內無高速公路站點',
                    'user_location': {'latitude': latitude, 'longitude': longitude}
                }
            
            # 2. 獲取最新的衝擊波預測
            latest_predictions = self.shock_predictor.get_latest_predictions()
            
            # 3. 過濾與用戶位置相關的預測
            relevant_predictions = []
            for _, prediction in latest_predictions.iterrows():
                target_station = prediction['target_station']
                
                # 檢查目標站點是否在用戶附近
                for station in nearest_stations:
                    if station['code'] == target_station:
                        pred_dict = prediction.to_dict()
                        pred_dict['station_info'] = station
                        relevant_predictions.append(pred_dict)
                        break
            
            # 4. 計算風險等級
            risk_assessment = self._assess_location_risk(nearest_stations, relevant_predictions)
            
            # 5. 生成建議
            recommendations = self._generate_recommendations(nearest_stations, relevant_predictions, risk_assessment)
            
            # 6. 路線分析（如果啟用）
            route_analysis = None
            if include_route_analysis and self.config['route_analysis']:
                route_analysis = self._analyze_potential_routes(latitude, longitude, relevant_predictions)
            
            result = {
                'success': True,
                'user_location': {
                    'latitude': latitude,
                    'longitude': longitude,
                    'address': self.reverse_geocode(latitude, longitude)
                },
                'nearest_stations': nearest_stations,
                'relevant_predictions': relevant_predictions,
                'risk_assessment': risk_assessment,
                'recommendations': recommendations,
                'route_analysis': route_analysis,
                'analysis_time': datetime.now().isoformat()
            }
            
            # 7. 記錄預測結果
            if user_id:
                self._save_location_prediction(user_id, result)
            
            self.logger.info(f"✅ 位置預測完成: {len(relevant_predictions)} 個相關預測")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 位置預測失敗: {e}")
            return {
                'success': False,
                'error': f'預測過程發生錯誤: {str(e)}',
                'user_location': {'latitude': latitude, 'longitude': longitude}
            }

    def _assess_location_risk(self, nearest_stations: List[Dict], predictions: List[Dict]) -> Dict:
        """評估位置風險"""
        if not predictions:
            return {
                'overall_risk': 'LOW',
                'risk_score': 0,
                'affected_stations_count': 0,
                'max_warning_level': 'INFO',
                'summary': '目前附近路段無衝擊波預警'
            }
        
        # 計算風險分數
        risk_scores = []
        warning_levels = []
        
        for prediction in predictions:
            # 基於距離的風險衰減
            distance = prediction['station_info']['distance_km']
            distance_factor = max(0.1, 1 - (distance / 20))  # 20公里外風險降到10%
            
            # 基於衝擊波強度的風險
            strength = prediction.get('shock_strength', 0)
            strength_score = min(100, strength) / 100
            
            # 基於信心度的調整
            confidence = prediction.get('confidence', 0)
            confidence_factor = confidence
            
            # 基於預計到達時間的緊急度
            arrival_time = datetime.fromisoformat(prediction['predicted_arrival'])
            time_to_arrival = (arrival_time - datetime.now()).total_seconds() / 3600  # 小時
            urgency_factor = max(0.2, 1 - (time_to_arrival / 2))  # 2小時後緊急度降到20%
            
            # 綜合風險分數
            risk_score = strength_score * distance_factor * confidence_factor * urgency_factor * 100
            risk_scores.append(risk_score)
            
            # 收集預警等級
            warning_levels.append(prediction.get('shock_level', 'INFO'))
        
        # 計算總體風險
        max_risk_score = max(risk_scores) if risk_scores else 0
        avg_risk_score = np.mean(risk_scores) if risk_scores else 0
        
        # 總體風險等級
        if max_risk_score >= 80:
            overall_risk = 'CRITICAL'
        elif max_risk_score >= 60:
            overall_risk = 'HIGH'
        elif max_risk_score >= 40:
            overall_risk = 'MODERATE'
        elif max_risk_score >= 20:
            overall_risk = 'LOW'
        else:
            overall_risk = 'MINIMAL'
        
        # 最高預警等級
        level_priority = {'mild': 1, 'moderate': 2, 'severe': 3, 'INFO': 0, 'MINOR': 1, 'MODERATE': 2, 'SEVERE': 3, 'CRITICAL': 4}
        max_level = max(warning_levels, key=lambda x: level_priority.get(x, 0)) if warning_levels else 'INFO'
        
        return {
            'overall_risk': overall_risk,
            'risk_score': round(max_risk_score, 1),
            'average_risk_score': round(avg_risk_score, 1),
            'affected_stations_count': len(predictions),
            'max_warning_level': max_level,
            'summary': self._generate_risk_summary(overall_risk, len(predictions), max_level)
        }

    def _generate_risk_summary(self, risk_level: str, affected_count: int, max_warning: str) -> str:
        """生成風險摘要"""
        risk_descriptions = {
            'CRITICAL': '極高風險，建議立即改道',
            'HIGH': '高風險，建議避開相關路段',
            'MODERATE': '中等風險，建議謹慎行駛',
            'LOW': '低風險，注意交通狀況',
            'MINIMAL': '風險極小，正常行駛'
        }
        
        base_description = risk_descriptions.get(risk_level, '風險狀況未明')
        
        if affected_count > 0:
            return f"{base_description}，{affected_count} 個附近站點受到 {max_warning} 等級衝擊波影響"
        else:
            return base_description

    def _generate_recommendations(self, nearest_stations: List[Dict], predictions: List[Dict], 
                                risk_assessment: Dict) -> List[str]:
        """生成建議"""
        recommendations = []
        
        risk_level = risk_assessment['overall_risk']
        affected_count = risk_assessment['affected_stations_count']
        
        if risk_level in ['CRITICAL', 'HIGH']:
            recommendations.append("🚨 強烈建議改道避開高速公路")
            recommendations.append("📱 使用導航軟體尋找替代路線")
            recommendations.append("⏰ 延後出發時間至衝擊波通過後")
        
        elif risk_level == 'MODERATE':
            recommendations.append("⚠️ 建議謹慎駕駛，保持安全距離")
            recommendations.append("🐌 降低行車速度，注意前方車況")
            recommendations.append("📻 關注即時交通資訊")
        
        elif risk_level == 'LOW':
            recommendations.append("ℹ️ 正常行駛，注意交通狀況")
            recommendations.append("👀 留意前方車流變化")
        
        else:
            recommendations.append("✅ 交通狀況良好，可正常行駛")
        
        # 特定站點建議
        if predictions:
            high_impact_stations = [p for p in predictions if p.get('shock_strength', 0) > 50]
            if high_impact_stations:
                station_names = [p['station_info']['readable_name'] for p in high_impact_stations]
                recommendations.append(f"🚫 特別避開：{', '.join(station_names[:3])}")
        
        # 時間建議
        if predictions:
            earliest_arrival = min(datetime.fromisoformat(p['predicted_arrival']) for p in predictions)
            time_to_earliest = (earliest_arrival - datetime.now()).total_seconds() / 60
            
            if time_to_earliest > 0:
                recommendations.append(f"⏱️ 最早衝擊波將在 {int(time_to_earliest)} 分鐘後到達")
        
        return recommendations

    def _analyze_potential_routes(self, latitude: float, longitude: float, predictions: List[Dict]) -> Dict:
        """分析潛在路線（簡化版）"""
        # 這裡實作簡化的路線分析
        # 在實際應用中，可以使用Google Maps Directions API進行更詳細的路線分析
        
        if not predictions:
            return {
                'analysis_available': False,
                'message': '無相關衝擊波預測，無需路線分析'
            }
        
        affected_stations = [p['station_info'] for p in predictions]
        
        # 分析影響的路段
        highways = set()
        directions = set()
        
        for station in affected_stations:
            highway = station['code'][:3]  # 01F or 03F
            direction = station['direction']
            highways.add(highway)
            directions.add(direction)
        
        analysis = {
            'analysis_available': True,
            'affected_highways': list(highways),
            'affected_directions': list(directions),
            'total_affected_stations': len(affected_stations),
            'recommendations': []
        }
        
        # 生成路線建議
        if '01F' in highways and '03F' in highways:
            analysis['recommendations'].append("兩條主要高速公路都受影響，建議使用平面道路")
        elif '01F' in highways:
            analysis['recommendations'].append("國道1號受影響，建議改用國道3號")
        elif '03F' in highways:
            analysis['recommendations'].append("國道3號受影響，建議改用國道1號")
        
        if 'N' in directions and 'S' in directions:
            analysis['recommendations'].append("雙向車道都有影響，特別注意交通狀況")
        
        return analysis

    def _save_location_prediction(self, user_id: str, prediction_result: Dict):
        """儲存位置預測結果"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                user_loc = prediction_result['user_location']
                risk = prediction_result['risk_assessment']
                nearest = prediction_result['nearest_stations'][0] if prediction_result['nearest_stations'] else None
                
                cursor.execute('''
                    INSERT INTO location_predictions 
                    (user_id, user_latitude, user_longitude, nearest_station, distance_km, 
                     prediction_count, max_warning_level, created_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    user_loc['latitude'],
                    user_loc['longitude'],
                    nearest['code'] if nearest else None,
                    nearest['distance_km'] if nearest else None,
                    len(prediction_result['relevant_predictions']),
                    risk['max_warning_level'],
                    datetime.now().isoformat()
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"❌ 儲存預測結果失敗: {e}")

    def analyze_route_with_coordinates(self, origin_lat: float, origin_lng: float, 
                                     dest_lat: float, dest_lng: float, user_id: str = None) -> Dict:
        """分析指定起終點的路線"""
        try:
            # 1. 獲取起點和終點的預測
            origin_prediction = self.predict_for_coordinates(origin_lat, origin_lng, include_route_analysis=False)
            dest_prediction = self.predict_for_coordinates(dest_lat, dest_lng, include_route_analysis=False)
            
            # 2. 路線沿途站點分析（簡化版）
            route_stations = self._find_route_stations(origin_lat, origin_lng, dest_lat, dest_lng)
            
            # 3. 合併預測結果
            all_predictions = []
            if origin_prediction['success']:
                all_predictions.extend(origin_prediction['relevant_predictions'])
            if dest_prediction['success']:
                all_predictions.extend(dest_prediction['relevant_predictions'])
            
            # 去重
            seen_stations = set()
            unique_predictions = []
            for pred in all_predictions:
                station = pred['target_station']
                if station not in seen_stations:
                    unique_predictions.append(pred)
                    seen_stations.add(station)
            
            # 4. 路線風險評估
            route_risk = self._assess_route_risk(unique_predictions)
            
            # 5. 路線建議
            route_recommendations = self._generate_route_recommendations(route_risk, unique_predictions)
            
            result = {
                'success': True,
                'origin': {
                    'latitude': origin_lat,
                    'longitude': origin_lng,
                    'address': self.reverse_geocode(origin_lat, origin_lng)
                },
                'destination': {
                    'latitude': dest_lat,
                    'longitude': dest_lng,
                    'address': self.reverse_geocode(dest_lat, dest_lng)
                },
                'route_stations': route_stations,
                'route_predictions': unique_predictions,
                'route_risk': route_risk,
                'recommendations': route_recommendations,
                'analysis_time': datetime.now().isoformat()
            }
            
            # 6. 儲存路線分析
            if user_id:
                self._save_route_analysis(user_id, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 路線分析失敗: {e}")
            return {
                'success': False,
                'error': f'路線分析發生錯誤: {str(e)}'
            }

    def _find_route_stations(self, origin_lat: float, origin_lng: float, 
                           dest_lat: float, dest_lng: float) -> List[Dict]:
        """找出路線沿途的站點（簡化版）"""
        # 簡化的實作：找出起終點附近的所有站點
        # 在實際應用中，可以使用Google Maps Roads API獲取精確的路線站點
        
        origin_stations = self.find_nearest_stations(origin_lat, origin_lng, max_count=10)
        dest_stations = self.find_nearest_stations(dest_lat, dest_lng, max_count=10)
        
        # 合併並去重
        all_stations = origin_stations + dest_stations
        seen_codes = set()
        unique_stations = []
        
        for station in all_stations:
            if station['code'] not in seen_codes:
                unique_stations.append(station)
                seen_codes.add(station['code'])
        
        # 按距離起點的遠近排序
        for station in unique_stations:
            station['distance_from_origin'] = self.calculate_distance(
                origin_lat, origin_lng,
                station['latitude'], station['longitude']
            )
        
        unique_stations.sort(key=lambda x: x['distance_from_origin'])
        
        return unique_stations

    def _assess_route_risk(self, predictions: List[Dict]) -> Dict:
        """評估路線風險"""
        if not predictions:
            return {
                'overall_risk': 'LOW',
                'risk_score': 0,
                'affected_segments': 0,
                'summary': '路線上無衝擊波預警'
            }
        
        # 計算路線總風險
        risk_scores = []
        severe_count = 0
        
        for prediction in predictions:
            strength = prediction.get('shock_strength', 0)
            confidence = prediction.get('confidence', 0)
            
            risk_score = strength * confidence
            risk_scores.append(risk_score)
            
            if prediction.get('shock_level') in ['severe', 'SEVERE', 'CRITICAL']:
                severe_count += 1
        
        avg_risk = np.mean(risk_scores) if risk_scores else 0
        max_risk = max(risk_scores) if risk_scores else 0
        
        # 路線風險等級
        if max_risk >= 70 or severe_count >= 2:
            overall_risk = 'HIGH'
        elif max_risk >= 50 or severe_count >= 1:
            overall_risk = 'MODERATE'
        elif max_risk >= 30:
            overall_risk = 'LOW'
        else:
            overall_risk = 'MINIMAL'
        
        return {
            'overall_risk': overall_risk,
            'risk_score': round(max_risk, 1),
            'average_risk_score': round(avg_risk, 1),
            'affected_segments': len(predictions),
            'severe_segments': severe_count,
            'summary': f'路線上有 {len(predictions)} 個受影響路段，{severe_count} 個嚴重影響'
        }

    def _generate_route_recommendations(self, route_risk: Dict, predictions: List[Dict]) -> List[str]:
        """生成路線建議"""
        recommendations = []
        
        risk_level = route_risk['overall_risk']
        
        if risk_level == 'HIGH':
            recommendations.append("🚨 強烈建議延後出發或改用替代路線")
            recommendations.append("🛣️ 考慮使用平面道路或大眾運輸")
        elif risk_level == 'MODERATE':
            recommendations.append("⚠️ 建議謹慎駕駛，預留額外時間")
            recommendations.append("🕐 考慮調整出發時間")
        elif risk_level == 'LOW':
            recommendations.append("ℹ️ 可正常通行，注意交通狀況")
        else:
            recommendations.append("✅ 路線暢通，可正常通行")
        
        # 時間建議
        if predictions:
            earliest_impact = min(datetime.fromisoformat(p['predicted_arrival']) for p in predictions)
            time_to_impact = (earliest_impact - datetime.now()).total_seconds() / 60
            
            if time_to_impact > 0:
                recommendations.append(f"⏰ 建議在 {int(time_to_impact)} 分鐘內完成通行")
        
        return recommendations

    def _save_route_analysis(self, user_id: str, analysis_result: Dict):
        """儲存路線分析結果"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                origin = analysis_result['origin']
                dest = analysis_result['destination']
                risk = analysis_result['route_risk']
                
                affected_stations = [p['target_station'] for p in analysis_result['route_predictions']]
                
                cursor.execute('''
                    INSERT INTO route_analysis 
                    (user_id, origin_lat, origin_lng, destination_lat, destination_lng,
                     route_stations, total_distance_km, estimated_duration_minutes,
                     affected_stations, warning_summary, created_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    origin['latitude'],
                    origin['longitude'],
                    dest['latitude'],
                    dest['longitude'],
                    json.dumps([s['code'] for s in analysis_result['route_stations']]),
                    0,  # 簡化版暫不計算距離
                    0,  # 簡化版暫不計算時間
                    json.dumps(affected_stations),
                    risk['summary'],
                    datetime.now().isoformat()
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"❌ 儲存路線分析失敗: {e}")


def main():
    """主函數"""
    # 設定參數（請替換為您的實際API Key）
    base_dir = "/Users/weiqihong/Desktop/碩士班/碩一下/highway-traffic/data"
    google_api_key = "YOUR_GOOGLE_MAPS_API_KEY"  # 請替換為實際的API Key
    
    # 建立位置預測系統
    location_predictor = LocationBasedShockPredictor(base_dir, google_api_key)
    
    print("=" * 60)
    print("📍 基於位置的衝擊波預測系統")
    print("=" * 60)
    print("\n選擇功能:")
    print("1. 地址查詢預測")
    print("2. 座標查詢預測")
    print("3. 用戶位置管理")
    print("4. 路線分析")
    print("5. 測試最近站點搜尋")
    
    try:
        choice = input("\n請選擇 (1/2/3/4/5): ").strip()
        
        if choice == "1":
            address = input("請輸入地址: ")
            coordinates = location_predictor.geocode_address(address)
            
            if coordinates:
                print(f"📍 座標: {coordinates}")
                result = location_predictor.predict_for_coordinates(coordinates[0], coordinates[1])
                
                if result['success']:
                    print(f"\n✅ 預測成功!")
                    print(f"📍 位置: {result['user_location']['address']}")
                    print(f"🎯 風險等級: {result['risk_assessment']['overall_risk']}")
                    print(f"📊 風險分數: {result['risk_assessment']['risk_score']}")
                    print(f"🚨 相關預測: {len(result['relevant_predictions'])} 個")
                    
                    print(f"\n💡 建議:")
                    for rec in result['recommendations']:
                        print(f"  - {rec}")
                else:
                    print(f"❌ 預測失敗: {result['error']}")
            else:
                print("❌ 地址轉座標失敗")
        
        elif choice == "2":
            lat = float(input("請輸入緯度: "))
            lng = float(input("請輸入經度: "))
            
            result = location_predictor.predict_for_coordinates(lat, lng)
            
            if result['success']:
                print(f"\n✅ 預測成功!")
                print(f"📍 位置: {result['user_location']['address']}")
                print(f"🎯 風險等級: {result['risk_assessment']['overall_risk']}")
                print(f"📊 風險分數: {result['risk_assessment']['risk_score']}")
                print(f"🚨 相關預測: {len(result['relevant_predictions'])} 個")
                
                print(f"\n💡 建議:")
                for rec in result['recommendations']:
                    print(f"  - {rec}")
            else:
                print(f"❌ 預測失敗: {result['error']}")
        
        elif choice == "3":
            user_id = input("請輸入用戶ID: ")
            lat = float(input("請輸入緯度: "))
            lng = float(input("請輸入經度: "))
            
            success = location_predictor.update_user_location(user_id, lat, lng)
            
            if success:
                print("✅ 用戶位置更新成功!")
                
                # 進行預測
                result = location_predictor.predict_for_user_location(user_id)
                if result['success']:
                    print(f"🎯 風險等級: {result['risk_assessment']['overall_risk']}")
                    print(f"📊 風險分數: {result['risk_assessment']['risk_score']}")
            else:
                print("❌ 用戶位置更新失敗")
        
        elif choice == "4":
            print("路線分析功能:")
            origin_lat = float(input("起點緯度: "))
            origin_lng = float(input("起點經度: "))
            dest_lat = float(input("終點緯度: "))
            dest_lng = float(input("終點經度: "))
            
            result = location_predictor.analyze_route_with_coordinates(
                origin_lat, origin_lng, dest_lat, dest_lng
            )
            
            if result['success']:
                print(f"\n✅ 路線分析成功!")
                print(f"📍 起點: {result['origin']['address']}")
                print(f"📍 終點: {result['destination']['address']}")
                print(f"🎯 路線風險: {result['route_risk']['overall_risk']}")
                print(f"📊 風險分數: {result['route_risk']['risk_score']}")
                print(f"🚨 影響路段: {result['route_risk']['affected_segments']} 個")
                
                print(f"\n💡 建議:")
                for rec in result['recommendations']:
                    print(f"  - {rec}")
            else:
                print(f"❌ 路線分析失敗: {result['error']}")
        
        elif choice == "5":
            lat = float(input("請輸入緯度: "))
            lng = float(input("請輸入經度: "))
            
            stations = location_predictor.find_nearest_stations(lat, lng)
            
            print(f"\n✅ 找到 {len(stations)} 個附近站點:")
            for i, station in enumerate(stations):
                print(f"{i+1}. {station['readable_name']}")
                print(f"   距離: {station['distance_km']:.2f} 公里")
                print(f"   座標: ({station['latitude']:.6f}, {station['longitude']:.6f})")
                print()
        
        else:
            print("無效選擇")
    
    except KeyboardInterrupt:
        print("\n👋 系統已停止")
    except Exception as e:
        print(f"\n❌ 系統錯誤: {e}")


if __name__ == "__main__":
    main()