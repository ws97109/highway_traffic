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

# 載入環境變數
load_dotenv()

class TDXRealtimeSystem:
    """
    TDX ETag 即時交通監控系統 (修復中斷問題版本)
    
    特點：
    1. 使用 TDX API 取得即時 ETag 資料
    2. OAuth2 認證機制
    3. 自動資料處理和保存
    4. 完整日誌記錄
    5. 錯誤恢復機制
    6. 與現有系統相容的資料格式
    7. 修復 Ctrl+C 中斷問題
    """

    def __init__(self, base_dir="/Users/weiqihong/Desktop/碩士班/碩一下/highway-traffic/data"):
        """初始化 TDX 系統"""
        
        # 基本設定
        self.base_dir = base_dir
        self.realtime_dir = os.path.join(self.base_dir, "realtime_data")
        self.log_dir = os.path.join(self.base_dir, "logs")
        
        # 建立目錄
        os.makedirs(self.realtime_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 設定日誌
        self._setup_logging()
        
        # TDX API 設定
        self.client_id = "613890176-1884e50b-52b1-44cb"
        self.client_secret = "ef5e1d00-4855-4214-b300-475309d88525"
        self.base_url = "https://tdx.transportdata.tw/api/basic"
        self.auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        
        # 認證相關
        self.access_token = None
        self.token_expires_at = None
        
        # 監控配置 - 修改為更合理的間隔
        self.collection_interval = 1    # 5分鐘間隔 (更即時)
        self.cleanup_frequency = 12     # 每12次收集後清理一次
        self.max_file_age_hours = 24    # 保留24小時的檔案
        
        # 系統狀態
        self.is_running = False
        self.collection_count = 0
        self.last_successful_collection = None
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        
        # 中斷處理標誌
        self.interrupt_requested = False
        
        # 車種對應表 (TDX 使用數字代碼)
        self.vehicle_types = {
            1: '小客車',
            2: '小貨車', 
            3: '大客車',
            4: '大貨車',
            5: '聯結車'
        }
        
        # 目標路段篩選
        self.target_highways = ['1', '2', '3', '4', '5', '6']
        self.target_directions = ['0', '1']
        
        # 載入目標站點清單
        self.target_stations = self._load_target_stations()
        
        # 註冊信號處理器 - 修改處理方式
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("🚀 TDX 即時監控系統初始化完成")
        self.logger.info(f"🔑 Client ID: {self.client_id}")
        self.logger.info(f"💾 資料目錄: {self.realtime_dir}")
        self.logger.info(f"⏱️ 收集間隔: {self.collection_interval} 分鐘")

    def _setup_logging(self):
        """設定日誌系統"""
        log_file = os.path.join(self.log_dir, f"tdx_system_{datetime.now().strftime('%Y%m%d')}.log")
        
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
        """信號處理器 - 立即響應中斷"""
        self.logger.info(f"\n🛑 收到中斷信號 {signum}，正在停止系統...")
        self.interrupt_requested = True
        self.is_running = False
        
        # 強制退出選項
        if hasattr(self, '_interrupt_count'):
            self._interrupt_count += 1
        else:
            self._interrupt_count = 1
            
        if self._interrupt_count >= 2:
            self.logger.info("🚨 收到多次中斷信號，強制退出")
            sys.exit(1)
        else:
            self.logger.info("💡 再按一次 Ctrl+C 強制退出")

    def _load_target_stations(self):
        """載入目標站點清單"""
        target_stations = set()
        etag_file = os.path.join(os.path.dirname(self.base_dir), 'data', 'Taiwan', 'Etag.csv')
        
        try:
            import pandas as pd
            df = pd.read_csv(etag_file, encoding='utf-8')
            
            for station_code in df['編號'].values:
                if pd.notna(station_code):
                    converted = station_code.replace('-', '').replace('.', '')
                    target_stations.add(converted)
            
            self.logger.info(f"✅ 載入 {len(target_stations)} 個目標站點")
            return target_stations
            
        except Exception as e:
            self.logger.warning(f"⚠️ 無法載入目標站點清單: {e}")
            self.logger.info("🔄 將使用所有可用站點")
            return set()

    def get_access_token(self):
        """取得 OAuth2 存取權杖"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        self.logger.info("🔑 取得新的存取權杖...")
        
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = requests.post(
                self.auth_url,
                data=auth_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            self.logger.info("✅ 存取權杖取得成功")
            return self.access_token
            
        except Exception as e:
            self.logger.error(f"❌ 取得存取權杖失敗: {e}")
            raise

    def make_api_request(self, endpoint, params=None, retries=3):
        """發送 API 請求"""
        for attempt in range(retries):
            try:
                token = self.get_access_token()
                
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'HighwayTrafficSystem/1.0'
                }
                
                url = f"{self.base_url}{endpoint}"
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                return response.json()
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"API 請求超時 (嘗試 {attempt + 1}/{retries}): {endpoint}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    self.logger.info("Token 可能過期，重新取得...")
                    self.access_token = None
                    if attempt < retries - 1:
                        continue
                self.logger.error(f"HTTP 錯誤: {e.response.status_code} - {endpoint}")
                raise
                
            except Exception as e:
                self.logger.error(f"API 請求失敗 (嘗試 {attempt + 1}/{retries}): {endpoint} - {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise

    def get_live_etag_data(self):
        """取得即時 ETag 資料"""
        self.logger.info("📡 取得即時 ETag 路況資料...")
        
        try:
            params = {
                '$format': 'JSON'
            }
            
            data = self.make_api_request("/v2/Road/Traffic/Live/ETag/Freeway", params)
            
            if isinstance(data, dict) and 'ETagPairLives' in data:
                live_data = data['ETagPairLives']
                self.logger.info(f"📋 從 ETagPairLives 取得 {len(live_data)} 筆原始資料")
            elif isinstance(data, list):
                live_data = data
                self.logger.info(f"📋 直接取得 {len(live_data)} 筆原始資料")
            else:
                self.logger.warning("❌ 無法解析資料結構")
                return []
            
            current_time = datetime.now()
            valid_data = []
            highway_stats = {}
            
            for record in live_data:
                if not isinstance(record, dict):
                    continue
                
                pair_id = record.get('ETagPairID', '')
                highway_id = ''
                
                if pair_id.startswith('01F'):
                    highway_id = '1'
                elif pair_id.startswith('03F'):
                    highway_id = '3'
                elif pair_id.startswith('02F'):
                    highway_id = '2'
                elif pair_id.startswith('04F'):
                    highway_id = '4'
                elif pair_id.startswith('05F'):
                    highway_id = '5'
                elif pair_id.startswith('06F'):
                    highway_id = '6'
                
                highway_stats[highway_id] = highway_stats.get(highway_id, 0) + 1
                
                data_time_str = record.get('DataCollectTime', '')
                data_is_fresh = True
                
                if data_time_str:
                    try:
                        if '+' in data_time_str or 'Z' in data_time_str:
                            data_time = datetime.fromisoformat(data_time_str.replace('Z', '+00:00'))
                            data_time = data_time.replace(tzinfo=None)
                        else:
                            data_time = datetime.fromisoformat(data_time_str)
                        
                        time_diff = (current_time - data_time).total_seconds() / 60
                        
                        if time_diff > 60:
                            data_is_fresh = False
                            continue
                    except Exception as e:
                        pass
                
                record['ParsedHighwayID'] = highway_id
                valid_data.append(record)
            
            self.logger.info(f"📊 國道資料分布: {highway_stats}")
            self.logger.info(f"✅ 篩選出 {len(valid_data)} 筆有效即時資料")
            return valid_data
            
        except Exception as e:
            self.logger.error(f"❌ 取得即時資料失敗: {e}")
            return []

    def process_live_data(self, live_data):
        """處理即時資料"""
        if not live_data:
            return pd.DataFrame()
        
        self.logger.info(f"🔄 處理 {len(live_data)} 筆即時資料...")
        
        processed_records = []
        current_time = datetime.now()
        
        for record in live_data:
            try:
                pair_id = record.get('ETagPairID', '')
                if not pair_id:
                    continue
                
                highway_id = record.get('ParsedHighwayID', '')
                direction = 'N' if pair_id.endswith('N') else 'S' if pair_id.endswith('S') else ''
                
                if highway_id not in self.target_highways:
                    continue
                
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
                        'date': current_time.strftime('%Y/%m/%d'),
                        'hour': current_time.hour,
                        'minute': (current_time.minute // 5) * 5,
                        'flow': volume * equivalent,
                        'median_speed': speed,
                        'avg_travel_time': travel_time,
                        'pair_id': pair_id,
                        'highway_id': highway_id,
                        'direction': direction,
                        'vehicle_type': vehicle_type,
                        'raw_volume': volume,
                        'data_collect_time': record.get('DataCollectTime', current_time.isoformat())
                    }
                    
                    processed_records.append(processed_record)
                    
            except Exception as e:
                self.logger.warning(f"處理單筆資料時發生錯誤: {e}")
                continue
        
        if processed_records:
            df = pd.DataFrame(processed_records)
            
            aggregated_df = df.groupby(['station', 'date', 'hour', 'minute']).agg({
                'flow': 'sum',
                'median_speed': lambda x: np.average(x, weights=df.loc[x.index, 'raw_volume']) if len(x) > 0 else 0,
                'avg_travel_time': lambda x: np.average(x, weights=df.loc[x.index, 'raw_volume']) if len(x) > 0 else 0,
                'pair_id': 'first',
                'highway_id': 'first', 
                'direction': 'first'
            }).reset_index()
            
            self.logger.info(f"✅ 處理完成: {len(aggregated_df)} 個站點的聚合資料")
            return aggregated_df
        
        return pd.DataFrame()

    def _generate_station_id(self, pair_id, highway_id, direction):
        """生成與原系統相容的站點ID"""
        import re
        
        if '-' in pair_id:
            end_station = pair_id.split('-')[1]
            return end_station
        else:
            direction_suffix = 'S' if direction == '0' else 'N'
            highway_prefix = f"{highway_id.zfill(2)}F"
            
            numbers = re.findall(r'\d+', pair_id)
            if numbers:
                number_part = numbers[0].zfill(4)
            else:
                number_part = str(abs(hash(pair_id)) % 9999).zfill(4)
            
            return f"{highway_prefix}{number_part}{direction_suffix}"

    def _calculate_vehicle_equivalent(self, vehicle_type, speed):
        """計算車種當量"""
        if vehicle_type in [1, 2]:
            return 1.0
        elif vehicle_type == 3:
            if speed < 70:
                return 1.13 + 1.66 * exp(-speed / 34.93)
            elif 70 <= speed <= 87:
                return 2.79 - 0.0206 * speed
            else:
                return 1.0
        elif vehicle_type == 4:
            if speed <= 105:
                return 1.9 - 0.00857 * speed
            else:
                return 1.0
        elif vehicle_type == 5:
            if speed <= 108:
                return 2.7 - 0.0157 * speed
            else:
                return 1.0
        else:
            return 1.0

    def save_data(self, processed_data):
        """保存處理後的資料"""
        if processed_data.empty:
            return None
        
        current_time = datetime.now()
        
        date_str = current_time.strftime('%Y%m%d')
        time_str = current_time.strftime('%H%M')
        
        output_file = os.path.join(self.realtime_dir, f"realtime_shock_data_{date_str}_{time_str}.csv")
        
        output_columns = ['station', 'date', 'hour', 'minute', 'flow', 'median_speed', 'avg_travel_time']
        compatible_data = processed_data[output_columns].copy()
        
        if self.target_stations:
            before_filter = len(compatible_data)
            compatible_data = compatible_data[compatible_data['station'].isin(self.target_stations)]
            after_filter = len(compatible_data)
            self.logger.info(f"🎯 站點過濾: {before_filter} → {after_filter} 筆記錄")
        
        compatible_data.to_csv(output_file, index=False, encoding='utf-8')
        
        self.logger.info(f"💾 資料已保存: {output_file}")
        self.logger.info(f"📊 記錄數: {len(compatible_data)}, 站點數: {compatible_data['station'].nunique()}")
        
        return output_file

    def cleanup_old_files(self):
        """清理舊檔案"""
        self.logger.info("🧹 執行檔案清理...")
        
        cutoff_time = datetime.now() - timedelta(hours=self.max_file_age_hours)
        csv_pattern = os.path.join(self.realtime_dir, "realtime_shock_data_*.csv")
        
        deleted_count = 0
        for file_path in glob.glob(csv_pattern):
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
            except:
                pass
        
        if deleted_count > 0:
            self.logger.info(f"✅ 清理完成: 刪除 {deleted_count} 個檔案")

    def single_collection(self):
        """執行單次資料收集"""
        try:
            start_time = datetime.now()
            self.logger.info(f"📊 開始 TDX 即時資料收集 - {start_time.strftime('%H:%M:%S')}")
            
            live_data = self.get_live_etag_data()
            processed_data = self.process_live_data(live_data)
            output_file = self.save_data(processed_data)
            
            self.last_successful_collection = datetime.now()
            self.consecutive_failures = 0
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ 收集完成，耗時 {duration:.1f} 秒")
            
            return processed_data, output_file
            
        except Exception as e:
            self.logger.error(f"❌ 資料收集失敗: {e}")
            self.consecutive_failures += 1
            return pd.DataFrame(), None

    def interruptible_sleep(self, seconds):
        """可中斷的休眠函數"""
        end_time = time.time() + seconds
        
        while time.time() < end_time and not self.interrupt_requested:
            # 每秒檢查一次中斷信號
            remaining = min(1.0, end_time - time.time())
            if remaining <= 0:
                break
            time.sleep(remaining)
        
        return self.interrupt_requested

    def start_continuous_monitoring(self):
        """啟動持續監控 - 修復中斷問題"""
        self.logger.info("🚀 啟動 TDX 持續監控模式")
        self.logger.info(f"⏱️ 收集間隔: {self.collection_interval} 分鐘")
        self.logger.info(f"🧹 清理頻率: 每 {self.cleanup_frequency} 次收集")
        self.logger.info("💡 按 Ctrl+C 可隨時停止")
        
        self.is_running = True
        self.interrupt_requested = False
        
        try:
            while self.is_running and not self.interrupt_requested:
                self.collection_count += 1
                
                self.logger.info(f"=== 第 {self.collection_count} 次收集 ===")
                
                # 檢查連續失敗次數
                if self.consecutive_failures >= self.max_consecutive_failures:
                    self.logger.error(f"連續失敗 {self.consecutive_failures} 次，暫停10分鐘")
                    if self.interruptible_sleep(600):  # 10分鐘，但可中斷
                        break
                    self.consecutive_failures = 0
                
                # 執行資料收集
                processed_data, output_file = self.single_collection()
                
                # 定期清理
                if self.collection_count % self.cleanup_frequency == 0:
                    self.cleanup_old_files()
                
                # 結果報告
                if not processed_data.empty:
                    unique_stations = processed_data['station'].nunique() if 'station' in processed_data.columns else 0
                    self.logger.info(f"✅ 收集成功: {len(processed_data)} 筆記錄, {unique_stations} 個站點")
                else:
                    self.logger.warning("⚠️ 本次收集無有效資料")
                
                # 可中斷的等待
                if self.is_running and not self.interrupt_requested:
                    self.logger.info(f"⏳ 等待 {self.collection_interval} 分鐘...")
                    if self.interruptible_sleep(self.collection_interval * 60):
                        break
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 收到鍵盤中斷")
        except Exception as e:
            self.logger.error(f"❌ 監控過程中發生錯誤: {e}")
        finally:
            self.logger.info("🏁 監控已停止")
            self.is_running = False

    def test_api_connection(self):
        """測試 API 連接"""
        self.logger.info("🔍 測試 TDX API 連接...")
        
        try:
            token = self.get_access_token()
            self.logger.info("✅ OAuth2 認證成功")
            
            live_data = self.get_live_etag_data()
            self.logger.info(f"✅ 即時資料: {len(live_data)} 筆")
            
            if live_data:
                processed = self.process_live_data(live_data[:5])
                self.logger.info(f"✅ 資料處理: 生成 {len(processed)} 筆處理後資料")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ API 測試失敗: {e}")
            return False


def run_tdx_system():
    """執行 TDX 系統"""
    
    print("=" * 60)
    print("🚀 TDX ETag 即時交通監控系統 (修復中斷問題版)")
    print("=" * 60)
    
    system = TDXRealtimeSystem()
    
    print("\n選擇運行模式:")
    print("1. API 連接測試")
    print("2. 單次資料收集測試")
    print("3. 持續監控模式 (可正常中斷)")
    print("4. 自定義間隔監控 (可正常中斷)")
    
    try:
        choice = input("\n請選擇 (1/2/3/4): ").strip()
        
        if choice == "1":
            print("\n🔍 執行 API 連接測試...")
            if system.test_api_connection():
                print("✅ API 連接測試成功!")
            else:
                print("❌ API 連接測試失敗，請檢查憑證設定")
        
        elif choice == "2":
            print("\n🧪 執行單次收集測試...")
            processed_data, output_file = system.single_collection()
            
            if not processed_data.empty:
                print(f"✅ 測試成功!")
                print(f"📊 收集到 {len(processed_data)} 筆記錄")
                if 'station' in processed_data.columns:
                    print(f"📍 涵蓋 {processed_data['station'].nunique()} 個站點")
                print(f"💾 檔案: {output_file}")
                
                print("\n前5筆資料預覽:")
                display_columns = ['station', 'hour', 'minute', 'flow', 'median_speed', 'avg_travel_time']
                available_columns = [col for col in display_columns if col in processed_data.columns]
                print(processed_data[available_columns].head().to_string())
            else:
                print("❌ 測試失敗，請檢查 API 設定")
        
        elif choice == "3":
            print(f"\n🚀 啟動持續監控模式 (每{system.collection_interval}分鐘收集一次)...")
            print("💡 現在可以隨時按 Ctrl+C 停止！")
            system.start_continuous_monitoring()
        
        elif choice == "4":
            interval = int(input("請輸入收集間隔(分鐘): "))
            system.collection_interval = interval
            print(f"\n🚀 啟動自定義監控 (每{interval}分鐘收集一次)...")
            print("💡 現在可以隨時按 Ctrl+C 停止！")
            system.start_continuous_monitoring()
        
        else:
            print("無效選擇")
    
    except KeyboardInterrupt:
        print("\n👋 系統已正常停止")
    except Exception as e:
        print(f"\n❌ 系統錯誤: {e}")


if __name__ == "__main__":
    run_tdx_system()