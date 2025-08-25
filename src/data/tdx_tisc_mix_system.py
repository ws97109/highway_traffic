#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import signal
import sys
import glob
from pathlib import Path
from math import exp
from dotenv import load_dotenv
from io import StringIO
import threading
from collections import deque, defaultdict

# 載入環境變數
load_dotenv()

class OptimizedIntegratedDataCollectionSystem:
    """
    優化的整合式交通資料收集系統 - 含資料緩存機制
    
    特點：
    1. 初始啟動時載入60分鐘歷史資料
    2. 之後每分鐘只添加即時資料
    3. 智慧資料緩存與滑動視窗
    4. 高效率資料融合
    5. 與衝擊波系統相容的輸出格式
    """

    def __init__(self, base_dir="data"):
        """初始化優化的整合資料收集系統"""
        
        # 智慧路徑偵測
        current_dir = os.getcwd()
        if current_dir.endswith('/src/data'):
            self.base_dir = os.path.join('..', '..', base_dir)
        elif current_dir.endswith('/src'):
            self.base_dir = os.path.join('..', base_dir)
        else:
            self.base_dir = base_dir
            
        self.realtime_dir = os.path.join(self.base_dir, "realtime_data")
        self.log_dir = os.path.join(self.base_dir, "logs")
        
        # 建立目錄
        for directory in [self.realtime_dir, self.log_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # 設定日誌
        self._setup_logging()
        
        # TDX API 設定
        self.tdx_client_id = os.getenv('TDX_CLIENT_ID')
        self.tdx_client_secret = os.getenv('TDX_CLIENT_SECRET')
        
        if not self.tdx_client_id or not self.tdx_client_secret:
            self.logger.warning("⚠️ TDX 憑證未設定，將僅使用 TISC 資料")
            self.tdx_available = False
        else:
            self.tdx_available = True
            
        self.tdx_base_url = "https://tdx.transportdata.tw/api/basic"
        self.tdx_auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        self.tdx_access_token = None
        self.tdx_token_expires_at = None
        
        # TISC 設定
        self.tisc_codes = ["M04A", "M05A"]
        self.tisc_base_url = "https://tisvcloud.freeway.gov.tw"
        self.tisc_headers = {'User-Agent': 'Mozilla/5.0'}
        
        # 📊 資料緩存設定 - 核心改進
        self.data_cache = defaultdict(lambda: deque(maxlen=120))  # 每站點保持120個時間點（2小時）
        self.cache_window_minutes = 60                           # 緩存視窗60分鐘
        self.historical_loaded = False                           # 歷史資料載入狀態
        self.cache_lock = threading.Lock()                      # 緩存線程安全
        
        # 監控參數
        self.collection_interval = 1        # 1分鐘間隔
        self.cleanup_frequency = 12         # 每12次收集後清理一次
        self.max_file_age_hours = 24        # 保留24小時的檔案
        
        # 系統狀態
        self.is_running = False
        self.collection_count = 0
        self.last_successful_collection = None
        self.data_source_stats = {
            'tdx_success': 0,
            'tdx_failure': 0,
            'tisc_success': 0, 
            'tisc_failure': 0,
            'fusion_success': 0,
            'cache_hits': 0
        }
        
        # 錯誤處理
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.failover_mode = False
        
        # 目標站點
        self.target_stations = self._load_target_stations()
        
        # 車種對應表
        self.vehicle_types = {
            1: '小客車', 2: '小貨車', 3: '大客車', 4: '大貨車', 5: '聯結車',
            31: '小客車', 32: '小貨車', 41: '大客車', 42: '單體貨車'
        }
        
        # 信號處理
        self.interrupt_requested = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("🚀 優化整合式資料收集系統初始化完成")
        self.logger.info(f"📡 TDX 可用: {self.tdx_available}")
        self.logger.info(f"📊 TISC 代碼: {self.tisc_codes}")
        self.logger.info(f"🎯 目標站點: {len(self.target_stations)}")
        self.logger.info(f"💾 緩存視窗: {self.cache_window_minutes} 分鐘")
        self.logger.info(f"⏱️ 收集間隔: {self.collection_interval} 分鐘")

    def _setup_logging(self):
        """設定日誌系統"""
        log_file = os.path.join(self.log_dir, f"optimized_data_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _signal_handler(self, signum, frame):
        """信號處理器"""
        self.logger.info(f"\n🛑 收到中斷信號 {signum}，正在停止系統...")
        self.interrupt_requested = True
        self.is_running = False
        
        if hasattr(self, '_interrupt_count'):
            self._interrupt_count += 1
        else:
            self._interrupt_count = 1
            
        if self._interrupt_count >= 2:
            self.logger.info("🚨 收到多次中斷信號，強制退出")
            import threading
            if threading.current_thread() is threading.main_thread():
                os._exit(0)
            else:
                sys.exit(1)
        else:
            self.logger.info("💡 再按一次 Ctrl+C 強制退出")

    def _load_target_stations(self):
        """載入目標站點清單"""
        target_stations = set()
        
        # 從 Etag.csv 載入
        etag_file = os.path.join(self.base_dir, 'Taiwan', 'Etag.csv')
        try:
            df = pd.read_csv(etag_file, encoding='utf-8')
            for station_code in df['編號'].values:
                if pd.notna(station_code):
                    converted = station_code.replace('-', '').replace('.', '')
                    target_stations.add(converted)
            self.logger.info(f"✅ 從 Etag.csv 載入 {len(target_stations)} 個站點")
        except Exception as e:
            self.logger.warning(f"⚠️ 無法載入 Etag.csv: {e}")
        
        # 添加重要站點
        important_stations = [
            # 國道1號北向
            '01F0340N', '01F0376N', '01F0413N', '01F0467N', '01F0492N',
            '01F0511N', '01F0532N', '01F0557N', '01F0584N', '01F0633N',
            '01F0664N', '01F0681N', '01F0699N', '01F0750N', '01F0880N',
            '01F0928N', '01F0956N', '01F0980N', '01F1045N',
            # 國道1號南向  
            '01F0339S', '01F0376S', '01F0413S', '01F0467S', '01F0492S',
            '01F0511S', '01F0532S', '01F0557S', '01F0578S', '01F0633S',
            '01F0664S', '01F0681S', '01F0699S', '01F0750S', '01F0880S',
            '01F0928S', '01F0950S', '01F0980S', '01F1045S',
            # 國道3號北向
            '03F0447N', '03F0498N', '03F0525N', '03F0559N', '03F0648N',
            '03F0698N', '03F0746N', '03F0783N', '03F0846N', '03F0961N',
            '03F0996N', '03F1022N',
            # 國道3號南向
            '03F0447S', '03F0498S', '03F0525S', '03F0559S', '03F0648S', 
            '03F0698S', '03F0746S', '03F0783S', '03F0846S', '03F0961S',
            '03F0996S', '03F1022S'
        ]
        
        target_stations.update(important_stations)
        self.logger.info(f"✅ 總計 {len(target_stations)} 個目標站點")
        
        return target_stations

    # ==================== 🆕 資料緩存核心方法 ====================
    
    def load_initial_historical_data(self):
        """🔄 初始載入歷史資料 - 只在系統啟動時執行一次"""
        if self.historical_loaded:
            self.logger.info("📋 歷史資料已載入，跳過重複載入")
            return
        
        self.logger.info("📥 開始載入初始歷史資料（60分鐘）...")
        start_time = datetime.now()
        
        try:
            # 取得60分鐘的歷史資料
            historical_data = self.fetch_tisc_historical_data(window_minutes=60)
            processed_data = self.process_tisc_data(historical_data)
            
            if not processed_data.empty:
                # 將歷史資料載入緩存
                self._add_to_cache(processed_data, is_historical=True)
                self.historical_loaded = True
                
                duration = (datetime.now() - start_time).total_seconds()
                self.logger.info(f"✅ 歷史資料載入完成")
                self.logger.info(f"   📊 載入 {len(processed_data)} 筆記錄")
                self.logger.info(f"   📍 涵蓋 {processed_data['station'].nunique()} 個站點")
                self.logger.info(f"   ⏱️ 載入時間: {duration:.1f} 秒")
                self.logger.info(f"   💾 緩存站點數: {len(self.data_cache)}")
            else:
                self.logger.warning("⚠️ 歷史資料載入失敗，將從即時資料開始")
                
        except Exception as e:
            self.logger.error(f"❌ 歷史資料載入錯誤: {e}")

    def _add_to_cache(self, new_data, is_historical=False):
        """📝 將資料加入緩存"""
        if new_data.empty:
            return
        
        with self.cache_lock:
            current_time = datetime.now()
            
            # 按站點分組加入緩存
            for station, station_data in new_data.groupby('station'):
                if station not in self.target_stations:
                    continue
                
                for _, row in station_data.iterrows():
                    # 建立時間戳記
                    if 'timestamp' in row and pd.notna(row['timestamp']):
                        timestamp = pd.to_datetime(row['timestamp'])
                    else:
                        # 使用hour, minute建立時間戳記
                        timestamp = current_time.replace(
                            hour=int(row['hour']), 
                            minute=int(row['minute']), 
                            second=0, 
                            microsecond=0
                        )
                    
                    # 加入緩存（deque自動管理大小）
                    cache_record = {
                        'timestamp': timestamp,
                        'station': station,
                        'flow': row['flow'],
                        'median_speed': row['median_speed'],
                        'avg_travel_time': row['avg_travel_time'],
                        'data_source': row.get('data_source', 'UNKNOWN'),
                        'hour': int(row['hour']),
                        'minute': int(row['minute']),
                        'date': row['date']
                    }
                    
                    self.data_cache[station].append(cache_record)
            
            self.data_source_stats['cache_hits'] += 1
            
            if is_historical:
                self.logger.info(f"💾 歷史資料已加入緩存: {new_data['station'].nunique()} 個站點")
            else:
                self.logger.info(f"➕ 即時資料已加入緩存: {new_data['station'].nunique()} 個站點")

    def get_cached_data_for_output(self, time_window_minutes=60):
        """📤 從緩存取得輸出資料"""
        with self.cache_lock:
            if not self.data_cache:
                return pd.DataFrame()
            
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(minutes=time_window_minutes)
            
            output_records = []
            
            for station, cache_deque in self.data_cache.items():
                if station not in self.target_stations:
                    continue
                
                # 取得時間窗口內的資料
                for record in cache_deque:
                    if record['timestamp'] >= cutoff_time:
                        output_records.append(record)
            
            if output_records:
                df = pd.DataFrame(output_records)
                # 按時間排序
                df = df.sort_values(['station', 'timestamp'])
                self.logger.info(f"📋 緩存資料擷取: {len(df)} 筆記錄，{df['station'].nunique()} 個站點")
                return df
            
            return pd.DataFrame()

    def cleanup_cache(self):
        """🧹 清理過舊的緩存資料"""
        with self.cache_lock:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(minutes=self.cache_window_minutes * 2)
            
            cleaned_count = 0
            for station, cache_deque in self.data_cache.items():
                original_length = len(cache_deque)
                
                # 移除過舊的記錄
                while cache_deque and cache_deque[0]['timestamp'] < cutoff_time:
                    cache_deque.popleft()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"🧹 緩存清理: 移除 {cleaned_count} 筆過舊記錄")

    # ==================== TDX 相關方法 ====================
    
    def get_tdx_access_token(self):
        """取得 TDX OAuth2 權杖"""
        if not self.tdx_available:
            return None
            
        if self.tdx_access_token and self.tdx_token_expires_at and datetime.now() < self.tdx_token_expires_at:
            return self.tdx_access_token
        
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': self.tdx_client_id,
            'client_secret': self.tdx_client_secret
        }
        
        try:
            response = requests.post(
                self.tdx_auth_url,
                data=auth_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.tdx_access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.tdx_token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            return self.tdx_access_token
            
        except Exception as e:
            self.logger.error(f"❌ TDX 權杖取得失敗: {e}")
            return None

    def fetch_tdx_realtime_data(self):
        """取得 TDX 即時資料 - 僅最新資料"""
        if not self.tdx_available:
            return []
        
        try:
            token = self.get_tdx_access_token()
            if not token:
                return []
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.tdx_base_url}/v2/Road/Traffic/Live/ETag/Freeway"
            params = {'$format': 'JSON'}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, dict) and 'ETagPairLives' in data:
                live_data = data['ETagPairLives']
            elif isinstance(data, list):
                live_data = data
            else:
                return []
            
            self.data_source_stats['tdx_success'] += 1
            self.logger.info(f"📡 TDX 即時資料: {len(live_data)} 筆")
            return live_data
            
        except Exception as e:
            self.data_source_stats['tdx_failure'] += 1
            self.logger.warning(f"⚠️ TDX 即時資料失敗: {e}")
            return []

    def process_tdx_data(self, raw_data):
        """處理 TDX 資料"""
        if not raw_data:
            return pd.DataFrame()
        
        processed_records = []
        current_time = datetime.now()
        
        for record in raw_data:
            try:
                pair_id = record.get('ETagPairID', '')
                if not pair_id:
                    continue
                
                # 解析國道編號
                highway_id = ''
                if pair_id.startswith('01F'): highway_id = '1'
                elif pair_id.startswith('02F'): highway_id = '2'
                elif pair_id.startswith('03F'): highway_id = '3'
                elif pair_id.startswith('04F'): highway_id = '4'
                elif pair_id.startswith('05F'): highway_id = '5'
                elif pair_id.startswith('06F'): highway_id = '6'
                
                direction = 'N' if pair_id.endswith('N') else 'S'
                
                flows = record.get('Flows', [])
                if not flows:
                    travel_time = record.get('TravelTime', 0)
                    speed = record.get('SpaceMeanSpeed', 0)
                    volume = record.get('Volume', 0) or record.get('VehicleCount', 0)
                    
                    if volume > 0:
                        flows = [{
                            'VehicleType': 1,
                            'TravelTime': travel_time,
                            'SpaceMeanSpeed': speed,
                            'VehicleCount': volume
                        }]
                
                for flow in flows:
                    vehicle_type = flow.get('VehicleType', 1)
                    travel_time = flow.get('TravelTime', 0)
                    speed = flow.get('SpaceMeanSpeed', 0) or flow.get('Speed', 0)
                    volume = flow.get('VehicleCount', 0) or flow.get('Volume', 0)
                    
                    if volume <= 0:
                        continue
                    
                    equivalent = self._calculate_vehicle_equivalent(vehicle_type, speed)
                    station_id = self._generate_station_id(pair_id, highway_id, direction)
                    
                    processed_record = {
                        'station': station_id,
                        'timestamp': current_time,
                        'date': current_time.strftime('%Y/%m/%d'),
                        'hour': current_time.hour,
                        'minute': current_time.minute,
                        'flow': volume * equivalent,
                        'median_speed': speed,
                        'avg_travel_time': travel_time,
                        'data_source': 'TDX_REALTIME',
                        'vehicle_type': vehicle_type,
                        'raw_volume': volume
                    }
                    
                    processed_records.append(processed_record)
                    
            except Exception as e:
                continue
        
        if processed_records:
            df = pd.DataFrame(processed_records)
            return df
        
        return pd.DataFrame()

    def _generate_station_id(self, pair_id, highway_id, direction):
        """生成站點ID"""
        import re
        
        if '-' in pair_id:
            return pair_id.split('-')[1]
        else:
            direction_suffix = 'S' if direction == '0' else 'N'
            highway_prefix = f"{highway_id.zfill(2)}F"
            
            numbers = re.findall(r'\d+', pair_id)
            if numbers:
                number_part = numbers[0].zfill(4)
            else:
                number_part = str(abs(hash(pair_id)) % 9999).zfill(4)
            
            return f"{highway_prefix}{number_part}{direction_suffix}"

    # ==================== TISC 相關方法 ====================
    
    def download_tisc_csv(self, url, retries=2):
        """下載 TISC CSV 資料"""
        for i in range(retries):
            try:
                response = requests.get(url, headers=self.tisc_headers, timeout=20)
                response.raise_for_status()
                
                csv_content = response.text
                if csv_content.startswith('\ufeff'):
                    csv_content = csv_content[1:]
                
                df = pd.read_csv(StringIO(csv_content), encoding='utf-8')
                
                if len(df.columns) >= 6:
                    if 'M05A' in url:
                        expected_cols = ['TimeStamp', 'GantryFrom', 'GantryTo', 'VehicleType', 'Speed', 'Volume']
                    else:
                        expected_cols = ['TimeStamp', 'GantryFrom', 'GantryTo', 'VehicleType', 'TravelTime', 'VehicleCount']
                    
                    df.columns = expected_cols[:len(df.columns)]
                
                return df
                
            except Exception as e:
                if i < retries - 1:
                    time.sleep(1)
                else:
                    self.logger.debug(f"TISC 下載失敗: {url}")
        
        return pd.DataFrame()

    def get_tisc_latest_time(self):
        """取得 TISC 最新可用時間"""
        current = datetime.now()
        
        for minutes_back in range(0, 121, 5):
            test_time = current - timedelta(minutes=minutes_back)
            test_time = test_time.replace(minute=(test_time.minute // 5) * 5, second=0, microsecond=0)
            
            date_str = test_time.strftime('%Y%m%d')
            hour_str = test_time.strftime('%H')
            minute_str = test_time.strftime('%M')
            ts = f"{hour_str}{minute_str}00"
            
            test_url = f"{self.tisc_base_url}/history/TDCS/M05A/{date_str}/{hour_str}/TDCS_M05A_{date_str}_{ts}.csv"
            
            try:
                response = requests.head(test_url, headers=self.tisc_headers, timeout=5)
                if response.status_code == 200:
                    return test_time
            except:
                continue
        
        return current - timedelta(hours=2)

    def fetch_tisc_historical_data(self, target_time=None, window_minutes=30):
        """取得 TISC 歷史資料（僅用於初始載入）"""
        if target_time is None:
            target_time = self.get_tisc_latest_time()
        
        all_results = {}
        time_points_needed = window_minutes // 5
        
        for code in self.tisc_codes:
            code_data = []
            
            for i in range(time_points_needed):
                point_time = target_time - timedelta(minutes=i*5)
                point_data = self._fetch_tisc_single_timepoint(code, point_time)
                
                if not point_data.empty:
                    code_data.append(point_data)
                
                if len(code_data) >= 6:  # 至少6個時間點（30分鐘）
                    break
            
            if code_data:
                all_results[code] = pd.concat(code_data, ignore_index=True)
        
        self.data_source_stats['tisc_success'] += 1
        return all_results

    def fetch_tisc_current_data(self):
        """取得 TISC 當前時間點資料 - 用於持續更新"""
        current_time = self.get_tisc_latest_time()
        
        all_results = {}
        for code in self.tisc_codes:
            point_data = self._fetch_tisc_single_timepoint(code, current_time)
            if not point_data.empty:
                all_results[code] = point_data
        
        return all_results

    def _fetch_tisc_single_timepoint(self, code, point_time):
        """取得 TISC 單一時間點資料"""
        date_str = point_time.strftime('%Y%m%d')
        hour_str = point_time.strftime('%H')
        minute_str = point_time.strftime('%M')
        
        minute_int = (int(minute_str) // 5) * 5
        ts = f"{hour_str}{minute_int:02d}00"
        
        url = f"{self.tisc_base_url}/history/TDCS/{code}/{date_str}/{hour_str}/TDCS_{code}_{date_str}_{ts}.csv"
        
        df = self.download_tisc_csv(url)
        if not df.empty:
            df['download_time'] = point_time.replace(minute=minute_int, second=0, microsecond=0)
            df['data_hour'] = int(hour_str)
            df['data_minute'] = minute_int
        
        return df

    def process_tisc_data(self, raw_data):
        """處理 TISC 資料"""
        if not raw_data:
            return pd.DataFrame()
        
        processed_records = []
        
        m05a_data = raw_data.get('M05A', pd.DataFrame())
        m04a_data = raw_data.get('M04A', pd.DataFrame())
        
        # 處理 M05A (速度/流量)
        if not m05a_data.empty:
            target_data = m05a_data[
                m05a_data['GantryFrom'].isin(self.target_stations) | 
                m05a_data['GantryTo'].isin(self.target_stations)
            ].copy()
            
            target_data['station'] = target_data.apply(
                lambda row: row['GantryFrom'] if row['GantryFrom'] in self.target_stations else row['GantryTo'], 
                axis=1
            )
            
            for (gantry, hour, minute), group in target_data.groupby(['station', 'data_hour', 'data_minute']):
                total_weighted_flow = 0
                speeds = []
                
                for _, row in group.iterrows():
                    if row['VehicleType'] in self.vehicle_types and row['Speed'] > 0 and row['Volume'] > 0:
                        equivalent = self._calculate_vehicle_equivalent(row['VehicleType'], row['Speed'])
                        total_weighted_flow += row['Volume'] * equivalent
                        speeds.extend([row['Speed']] * int(row['Volume']))
                
                if total_weighted_flow > 0:
                    historical_time = group.iloc[0]['download_time']
                    
                    record = {
                        'station': gantry,
                        'timestamp': historical_time,
                        'date': historical_time.strftime('%Y/%m/%d'),
                        'hour': hour,
                        'minute': minute,
                        'flow': total_weighted_flow,
                        'median_speed': np.median(speeds) if speeds else 0,
                        'avg_travel_time': 0,
                        'data_source': 'TISC_M05A'
                    }
                    processed_records.append(record)
        
        # 處理 M04A (旅行時間)
        if not m04a_data.empty:
            target_data = m04a_data[
                m04a_data['GantryFrom'].isin(self.target_stations) | 
                m04a_data['GantryTo'].isin(self.target_stations)
            ].copy()
            
            target_data['station'] = target_data.apply(
                lambda row: row['GantryFrom'] if row['GantryFrom'] in self.target_stations else row['GantryTo'], 
                axis=1
            )
            
            travel_time_dict = {}
            
            for (gantry, hour, minute), group in target_data.groupby(['station', 'data_hour', 'data_minute']):
                valid_data = group[
                    (group['VehicleType'].isin(self.vehicle_types)) &
                    (group['TravelTime'] > 0) & 
                    (group['VehicleCount'] > 0)
                ]
                
                if not valid_data.empty:
                    total_travel_time = (valid_data['TravelTime'] * valid_data['VehicleCount']).sum()
                    total_count = valid_data['VehicleCount'].sum()
                    avg_travel_time = total_travel_time / total_count if total_count > 0 else 0
                    
                    key = (gantry, hour, minute)
                    travel_time_dict[key] = avg_travel_time
            
            # 更新已有記錄的旅行時間
            for record in processed_records:
                if record['data_source'] == 'TISC_M05A':
                    key = (record['station'], record['hour'], record['minute'])
                    if key in travel_time_dict:
                        record['avg_travel_time'] = travel_time_dict[key]
            
            # 添加只有旅行時間的記錄
            for (gantry, hour, minute), avg_travel_time in travel_time_dict.items():
                existing = any(
                    r['station'] == gantry and r['hour'] == hour and r['minute'] == minute 
                    for r in processed_records
                )
                
                if not existing:
                    matching_data = target_data[
                        (target_data['station'] == gantry) &
                        (target_data['data_hour'] == hour) & 
                        (target_data['data_minute'] == minute)
                    ]
                    
                    if not matching_data.empty:
                        historical_time = matching_data.iloc[0]['download_time']
                        
                        record = {
                            'station': gantry,
                            'timestamp': historical_time,
                            'date': historical_time.strftime('%Y/%m/%d'),
                            'hour': hour,
                            'minute': minute,
                            'flow': 0,
                            'median_speed': 0,
                            'avg_travel_time': avg_travel_time,
                            'data_source': 'TISC_M04A'
                        }
                        processed_records.append(record)
        
        if processed_records:
            df = pd.DataFrame(processed_records)
            df = df.sort_values(['station', 'timestamp'])
            return df
        
        return pd.DataFrame()

    def _calculate_vehicle_equivalent(self, vehicle_type, speed):
        """計算車種當量"""
        if vehicle_type in [1, 2, 31, 32]:  # 小客車/小貨車
            return 1.0
        elif vehicle_type in [3, 41]:  # 大客車
            if speed < 70:
                return 1.13 + 1.66 * exp(-speed / 34.93)
            elif 70 <= speed <= 87:
                return 2.79 - 0.0206 * speed
            else:
                return 1.0
        elif vehicle_type in [4, 42]:  # 大貨車
            if speed <= 105:
                return 1.9 - 0.00857 * speed
            else:
                return 1.0
        elif vehicle_type == 5:  # 聯結車
            if speed <= 108:
                return 2.7 - 0.0157 * speed
            else:
                return 1.0
        else:
            return 1.0

    # ==================== 🆕 優化的主要資料收集方法 ====================
    
    def single_optimized_collection(self):
        """執行單次優化資料收集 - 核心改進"""
        try:
            start_time = datetime.now()
            self.logger.info(f"📊 開始優化資料收集 - {start_time.strftime('%H:%M:%S')}")
            
            # 🔄 如果是第一次收集，載入歷史資料
            if not self.historical_loaded:
                self.load_initial_historical_data()
            
            # 📡 收集即時資料（TDX + TISC最新）
            new_data_records = []
            
            # TDX 即時資料
            if self.tdx_available and not self.failover_mode:
                try:
                    tdx_raw = self.fetch_tdx_realtime_data()
                    tdx_data = self.process_tdx_data(tdx_raw)
                    if not tdx_data.empty:
                        new_data_records.append(tdx_data)
                        self.logger.info(f"📡 TDX 即時資料: {len(tdx_data)} 筆")
                except Exception as e:
                    self.logger.warning(f"⚠️ TDX 收集失敗: {e}")
                    self.failover_mode = True
            
            # TISC 最新資料點（不再下載60分鐘）
            try:
                tisc_current = self.fetch_tisc_current_data()
                tisc_data = self.process_tisc_data(tisc_current)
                if not tisc_data.empty:
                    new_data_records.append(tisc_data)
                    self.logger.info(f"📊 TISC 即時資料: {len(tisc_data)} 筆")
            except Exception as e:
                self.logger.warning(f"⚠️ TISC 收集失敗: {e}")
                self.data_source_stats['tisc_failure'] += 1
            
            # 💾 將新資料加入緩存
            if new_data_records:
                combined_new_data = pd.concat(new_data_records, ignore_index=True)
                self._add_to_cache(combined_new_data, is_historical=False)
            
            # 📤 從緩存取得完整輸出資料
            output_data = self.get_cached_data_for_output(time_window_minutes=60)
            
            # 💾 保存資料
            output_file = self.save_cached_data(output_data)
            
            # 🧹 定期清理緩存
            if self.collection_count % 10 == 0:
                self.cleanup_cache()
            
            # ✅ 更新狀態
            if not output_data.empty:
                self.failover_mode = False
                self.consecutive_failures = 0
                self.last_successful_collection = datetime.now()
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ 優化收集完成，耗時 {duration:.1f} 秒")
            
            return output_data, output_file
            
        except Exception as e:
            self.logger.error(f"❌ 優化資料收集失敗: {e}")
            self.consecutive_failures += 1
            return pd.DataFrame(), None

    def save_cached_data(self, cached_data):
        """保存緩存資料 - 輸出衝擊波系統相容格式"""
        if cached_data.empty:
            return None
        
        current_time = datetime.now()
        date_str = current_time.strftime('%Y%m%d')
        time_str = current_time.strftime('%H%M')
        
        # 主要輸出檔案
        output_file = os.path.join(self.realtime_dir, f"realtime_shock_data_{date_str}_{time_str}.csv")
        
        # 準備標準輸出格式
        output_columns = ['station', 'date', 'hour', 'minute', 'flow', 'median_speed', 'avg_travel_time']
        output_data = cached_data[output_columns].copy()
        
        # 只保留目標站點
        if self.target_stations:
            before_filter = len(output_data)
            output_data = output_data[output_data['station'].isin(self.target_stations)]
            after_filter = len(output_data)
            
            if before_filter != after_filter:
                self.logger.info(f"🎯 站點過濾: {before_filter} → {after_filter} 筆記錄")
        
        # 移除重複記錄（同站點同時間）
        output_data = output_data.drop_duplicates(subset=['station', 'hour', 'minute'])
        
        # 保存主要檔案
        output_data.to_csv(output_file, index=False, encoding='utf-8')
        
        # 保存詳細版本檔案
        if 'data_source' in cached_data.columns and 'timestamp' in cached_data.columns:
            detail_columns = ['station', 'timestamp', 'date', 'hour', 'minute', 'flow', 'median_speed', 'avg_travel_time', 'data_source']
            detail_data = cached_data[detail_columns].copy()
            if self.target_stations:
                detail_data = detail_data[detail_data['station'].isin(self.target_stations)]
            detail_data = detail_data.drop_duplicates(subset=['station', 'hour', 'minute'])
            detail_file = os.path.join(self.realtime_dir, f"detailed_cached_data_{date_str}_{time_str}.csv")
            detail_data.to_csv(detail_file, index=False, encoding='utf-8')
        
        # 報告資料源統計
        if 'data_source' in cached_data.columns:
            source_stats = cached_data['data_source'].value_counts().to_dict()
            self.logger.info(f"📊 緩存資料源分布: {source_stats}")
        
        self.logger.info(f"💾 緩存資料已保存: {output_file}")
        self.logger.info(f"📊 記錄數: {len(output_data)}, 站點數: {output_data['station'].nunique()}")
        
        return output_file

    def cleanup_old_files(self):
        """清理舊檔案"""
        self.logger.info("🧹 執行檔案清理...")
        
        cutoff_time = datetime.now() - timedelta(hours=self.max_file_age_hours)
        deleted_count = 0
        
        patterns = ["realtime_shock_data_*.csv", "detailed_cached_data_*.csv"]
        for pattern in patterns:
            for file_path in glob.glob(os.path.join(self.realtime_dir, pattern)):
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                except:
                    pass
        
        if deleted_count > 0:
            self.logger.info(f"✅ 檔案清理完成: 刪除 {deleted_count} 個檔案")

    def interruptible_sleep(self, seconds):
        """可中斷的休眠函數"""
        sleep_interval = 0.5
        elapsed = 0
        
        while elapsed < seconds and not self.interrupt_requested:
            remaining = seconds - elapsed
            current_sleep = min(sleep_interval, remaining)
            
            time.sleep(current_sleep)
            elapsed += current_sleep
            
            if self.interrupt_requested:
                self.logger.info("💡 檢測到中斷信號，停止等待")
                return True
        
        return self.interrupt_requested

    def start_optimized_monitoring(self):
        """🚀 啟動優化的持續監控"""
        self.logger.info("🚀 啟動優化整合式資料收集監控")
        self.logger.info(f"⏱️ 收集間隔: {self.collection_interval} 分鐘")
        self.logger.info(f"💾 緩存視窗: {self.cache_window_minutes} 分鐘")
        self.logger.info(f"🎯 輸出格式: 衝擊波系統相容")
        self.logger.info("💡 按 Ctrl+C 可隨時停止")
        
        self.is_running = True
        self.interrupt_requested = False
        
        try:
            while self.is_running and not self.interrupt_requested:
                self.collection_count += 1
                
                self.logger.info(f"=== 第 {self.collection_count} 次優化收集 ===")
                
                # 檢查連續失敗次數
                if self.consecutive_failures >= self.max_consecutive_failures:
                    self.logger.error(f"連續失敗 {self.consecutive_failures} 次，暫停10分鐘")
                    if self.interruptible_sleep(600):
                        break
                    self.consecutive_failures = 0
                
                # 執行優化資料收集
                output_data, output_file = self.single_optimized_collection()
                
                # 定期清理
                if self.collection_count % self.cleanup_frequency == 0:
                    self.cleanup_old_files()
                
                # 系統狀態報告
                if self.collection_count % 10 == 0:
                    self._report_optimized_status()
                
                # 結果報告
                if not output_data.empty:
                    unique_stations = output_data['station'].nunique()
                    total_cache_records = sum(len(cache) for cache in self.data_cache.values())
                    
                    self.logger.info(f"✅ 收集成功: {len(output_data)} 筆記錄, {unique_stations} 個站點")
                    self.logger.info(f"💾 緩存狀態: {len(self.data_cache)} 個站點, {total_cache_records} 筆記錄")
                    
                    if 'data_source' in output_data.columns:
                        source_stats = output_data['data_source'].value_counts().to_dict()
                        self.logger.info(f"📊 資料源分布: {source_stats}")
                else:
                    self.logger.warning("⚠️ 本次收集無有效資料")
                
                # 可中斷的等待
                if self.is_running and not self.interrupt_requested:
                    self.logger.info(f"⏳ 等待 {self.collection_interval} 分鐘...")
                    if self.interruptible_sleep(self.collection_interval * 60):
                        break
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 收到鍵盤中斷")
            self.interrupt_requested = True
            self.is_running = False
        except Exception as e:
            self.logger.error(f"❌ 監控過程中發生錯誤: {e}")
        finally:
            self.logger.info("🏁 優化監控已停止")
            self.is_running = False

    def _report_optimized_status(self):
        """報告優化系統狀態"""
        success_rate_tdx = 0
        success_rate_tisc = 0
        
        if self.data_source_stats['tdx_success'] + self.data_source_stats['tdx_failure'] > 0:
            success_rate_tdx = (self.data_source_stats['tdx_success'] / 
                               (self.data_source_stats['tdx_success'] + self.data_source_stats['tdx_failure'])) * 100
        
        if self.data_source_stats['tisc_success'] + self.data_source_stats['tisc_failure'] > 0:
            success_rate_tisc = (self.data_source_stats['tisc_success'] / 
                                (self.data_source_stats['tisc_success'] + self.data_source_stats['tisc_failure'])) * 100
        
        total_cache_records = sum(len(cache) for cache in self.data_cache.values())
        
        self.logger.info("=" * 50)
        self.logger.info("📈 優化系統狀態報告")
        self.logger.info(f"📊 資料源統計:")
        self.logger.info(f"   TDX: 成功 {self.data_source_stats['tdx_success']}, 失敗 {self.data_source_stats['tdx_failure']} (成功率: {success_rate_tdx:.1f}%)")
        self.logger.info(f"   TISC: 成功 {self.data_source_stats['tisc_success']}, 失敗 {self.data_source_stats['tisc_failure']} (成功率: {success_rate_tisc:.1f}%)")
        self.logger.info(f"💾 緩存統計:")
        self.logger.info(f"   站點數: {len(self.data_cache)}")
        self.logger.info(f"   總記錄數: {total_cache_records}")
        self.logger.info(f"   緩存命中: {self.data_source_stats['cache_hits']} 次")
        self.logger.info(f"   歷史載入: {'✅' if self.historical_loaded else '❌'}")
        self.logger.info(f"🔄 故障轉移模式: {'啟用' if self.failover_mode else '停用'}")
        
        if self.last_successful_collection:
            time_since_success = (datetime.now() - self.last_successful_collection).total_seconds() / 60
            self.logger.info(f"🕒 上次成功收集: {time_since_success:.1f} 分鐘前")
        
        self.logger.info("=" * 50)

    def test_optimized_system(self):
        """測試優化系統"""
        self.logger.info("🔍 測試優化整合資料收集系統...")
        
        success_count = 0
        total_tests = 0
        
        # 測試 TDX 連接
        if self.tdx_available:
            total_tests += 1
            try:
                token = self.get_tdx_access_token()
                if token:
                    self.logger.info("✅ TDX 認證成功")
                    success_count += 1
                else:
                    self.logger.warning("⚠️ TDX 認證失敗")
            except Exception as e:
                self.logger.error(f"❌ TDX 測試失敗: {e}")
        else:
            self.logger.info("ℹ️ TDX 未配置，將僅使用 TISC 資料")
        
        # 測試 TISC 連接
        total_tests += 1
        try:
            latest_time = self.get_tisc_latest_time()
            delay_minutes = (datetime.now() - latest_time).total_seconds() / 60
            self.logger.info(f"✅ TISC 最新時間: {latest_time.strftime('%Y-%m-%d %H:%M')} (延遲 {delay_minutes:.0f} 分鐘)")
            success_count += 1
        except Exception as e:
            self.logger.error(f"❌ TISC 測試失敗: {e}")
        
        # 測試歷史資料載入
        total_tests += 1
        try:
            self.load_initial_historical_data()
            if self.historical_loaded:
                total_cache_records = sum(len(cache) for cache in self.data_cache.values())
                self.logger.info(f"✅ 歷史資料載入成功:")
                self.logger.info(f"   💾 緩存站點: {len(self.data_cache)}")
                self.logger.info(f"   📊 總記錄數: {total_cache_records}")
                success_count += 1
            else:
                self.logger.warning("⚠️ 歷史資料載入失敗")
        except Exception as e:
            self.logger.error(f"❌ 歷史資料載入測試失敗: {e}")
        
        # 測試優化資料收集
        total_tests += 1
        try:
            output_data, output_file = self.single_optimized_collection()
            if not output_data.empty:
                self.logger.info(f"✅ 優化收集測試成功:")
                self.logger.info(f"   📊 記錄數: {len(output_data)}")
                self.logger.info(f"   📍 站點數: {output_data['station'].nunique()}")
                
                if 'data_source' in output_data.columns:
                    source_dist = output_data['data_source'].value_counts()
                    self.logger.info(f"   📊 資料源: {dict(source_dist)}")
                
                self.logger.info(f"   💾 輸出檔案: {output_file}")
                success_count += 1
            else:
                self.logger.warning("⚠️ 優化收集測試無資料返回")
        except Exception as e:
            self.logger.error(f"❌ 優化收集測試失敗: {e}")
        
        success_rate = (success_count / total_tests) * 100 if total_tests > 0 else 0
        self.logger.info(f"📊 測試完成: {success_count}/{total_tests} 成功 ({success_rate:.1f}%)")
        
        return success_rate >= 50

    def get_latest_data_for_shockwave(self):
        """為衝擊波系統提供最新資料"""
        try:
            output_data = self.get_cached_data_for_output(time_window_minutes=60)
            
            if not output_data.empty:
                output_columns = ['station', 'date', 'hour', 'minute', 'flow', 'median_speed', 'avg_travel_time']
                return output_data[output_columns]
            
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"❌ 為衝擊波系統取得資料失敗: {e}")
            return pd.DataFrame()


def run_optimized_integrated_system():
    """執行優化的整合資料收集系統"""
    
    print("=" * 80)
    print("🚀 優化的整合式交通資料收集系統 v2.0")
    print("💾 資料緩存機制 - 只載入一次歷史資料")
    print("⚡ 持續累積即時資料 - 高效能監控")
    print("🌊 專為衝擊波檢測系統設計")
    print("=" * 80)
    
    system = OptimizedIntegratedDataCollectionSystem(base_dir="data")
    
    print("\n💡 核心改進:")
    print("✨ 初始啟動時載入60分鐘歷史資料")
    print("⚡ 之後每分鐘只下載即時資料")
    print("💾 智慧緩存管理，滑動視窗機制")
    print("🔄 自動資料融合與品質控制")
    
    print("\n📁 資料將儲存至: data/realtime_data/")
    
    print("\n選擇運行模式:")
    print("1. 系統完整測試 (測試所有功能)")
    print("2. 優化持續監控 (每1分鐘更新，推薦)")
    print("3. 自定義間隔監控")
    print("4. 單次優化收集測試")
    print("5. 查看緩存狀態")
    
    try:
        choice = input("\n請選擇 (1/2/3/4/5): ").strip()
        
        if choice == "1":
            print("\n🔍 執行系統完整測試...")
            if system.test_optimized_system():
                print("✅ 優化系統測試通過!")
                print("🎯 系統已準備好為衝擊波檢測提供高效資料流")
            else:
                print("❌ 系統測試失敗，請檢查設定")
        
        elif choice == "2":
            print("\n🚀 啟動優化持續監控模式...")
            print("💾 初始載入60分鐘歷史資料（僅首次）")
            print("⚡ 每1分鐘添加即時資料到緩存")
            print("📤 持續輸出完整時間序列資料")
            print("💡 按 Ctrl+C 可隨時停止 (可能需要按兩次)")
            
            try:
                system.start_optimized_monitoring()
            except KeyboardInterrupt:
                print("\n🛑 接收到中斷信號，正在停止...")
                system.interrupt_requested = True
                system.is_running = False
                time.sleep(1)
                print("✅ 優化系統已安全停止")
        
        elif choice == "3":
            interval = int(input("請輸入收集間隔(分鐘，建議1-3分鐘): "))
            if interval < 1:
                print("⚠️ 間隔過短，調整為1分鐘")
                interval = 1
            elif interval > 5:
                print("⚠️ 間隔過長可能影響即時性")
            
            system.collection_interval = interval
            print(f"\n🚀 啟動自定義監控 (每{interval}分鐘收集一次)...")
            print("💡 按 Ctrl+C 可隨時停止")
            
            try:
                system.start_optimized_monitoring()
            except KeyboardInterrupt:
                print("\n🛑 接收到中斷信號，正在停止...")
                system.interrupt_requested = True
                system.is_running = False
                time.sleep(1)
                print("✅ 優化系統已安全停止")
        
        elif choice == "4":
            print("\n🧪 執行單次優化收集測試...")
            
            # 先載入歷史資料
            if not system.historical_loaded:
                print("📥 首次執行，載入歷史資料...")
                system.load_initial_historical_data()
            
            output_data, output_file = system.single_optimized_collection()
            
            if not output_data.empty:
                print(f"✅ 優化收集測試成功!")
                print(f"📊 輸出記錄數: {len(output_data)}")
                print(f"📍 涵蓋站點數: {output_data['station'].nunique()}")
                
                total_cache_records = sum(len(cache) for cache in system.data_cache.values())
                print(f"💾 緩存狀態: {len(system.data_cache)} 個站點, {total_cache_records} 筆記錄")
                
                if 'data_source' in output_data.columns:
                    source_dist = output_data['data_source'].value_counts()
                    print(f"📊 資料源分布:")
                    for source, count in source_dist.items():
                        print(f"   {source}: {count} 筆")
                
                print(f"💾 輸出檔案: {output_file}")
                
                # 顯示前5筆資料預覽
                print("\n📋 前5筆資料預覽:")
                display_cols = ['station', 'hour', 'minute', 'flow', 'median_speed', 'avg_travel_time']
                available_cols = [col for col in display_cols if col in output_data.columns]
                print(output_data[available_cols].head().to_string(index=False))
            else:
                print("❌ 測試失敗，請檢查網路連接")
        
        elif choice == "5":
            print("\n📋 查看緩存狀態...")
            
            if not system.historical_loaded:
                print("⚠️ 歷史資料尚未載入")
                load_choice = input("是否載入歷史資料? (y/n): ").strip().lower()
                if load_choice == 'y':
                    system.load_initial_historical_data()
            
            if system.data_cache:
                total_records = sum(len(cache) for cache in system.data_cache.values())
                print(f"💾 緩存統計:")
                print(f"   站點數: {len(system.data_cache)}")
                print(f"   總記錄數: {total_records}")
                print(f"   歷史載入狀態: {'✅' if system.historical_loaded else '❌'}")
                
                # 顯示前10個站點的記錄數
                print(f"\n📊 前10個站點記錄數:")
                station_counts = [(station, len(cache)) for station, cache in system.data_cache.items()]
                station_counts.sort(key=lambda x: x[1], reverse=True)
                for station, count in station_counts[:10]:
                    print(f"   {station}: {count} 筆")
                
                # 取得最新資料樣本
                latest_data = system.get_cached_data_for_output(time_window_minutes=30)
                if not latest_data.empty:
                    print(f"\n📋 最近30分鐘資料預覽:")
                    display_cols = ['station', 'hour', 'minute', 'flow', 'median_speed']
                    available_cols = [col for col in display_cols if col in latest_data.columns]
                    print(latest_data[available_cols].tail().to_string(index=False))
            else:
                print("📭 緩存為空")
        
        else:
            print("無效選擇")
    
    except KeyboardInterrupt:
        print("\n🛑 程序被中斷")
        if hasattr(system, 'is_running'):
            system.is_running = False
            system.interrupt_requested = True
        print("✅ 優化系統已停止")
    except Exception as e:
        print(f"\n❌ 系統錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n👋 感謝使用優化的整合式資料收集系統！")


if __name__ == "__main__":
    run_optimized_integrated_system()