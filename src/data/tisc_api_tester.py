#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from io import StringIO
from math import exp
import glob
import threading
import logging
import signal
import sys
from pathlib import Path

class ProductionRealtimeSystem:
    """
    生產版即時交通監控系統
    
    特點：
    1. 持續自動監控
    2. 自動清理機制
    3. 完整日誌記錄
    4. 錯誤恢復機制
    5. 優雅關閉
    """

    def __init__(self, base_dir="../data"):
        """初始化生產版系統"""
        
        # 基本設定
        self.base_dir = base_dir
        self.realtime_dir = os.path.join(self.base_dir, "realtime_data")
        self.log_dir = os.path.join(self.base_dir, "logs")
        
        # 建立目錄
        os.makedirs(self.realtime_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 設定日誌
        self._setup_logging()
        
        # 系統參數
        self.codes = ["M04A", "M05A"]
        self.base_url = "https://tisvcloud.freeway.gov.tw"
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        
        # 監控參數
        self.collection_interval = 5      # 每5分鐘收集一次
        self.data_window_minutes = 30     # 資料視窗30分鐘
        self.min_data_points = 6          # 最少需要6個資料點
        
        # 清理參數
        self.cleanup_frequency = 12       # 每12次收集後清理一次（每小時）
        self.max_file_age_hours = 24      # 保留24小時的檔案
        self.max_log_age_days = 1         # 保留7天的日誌
        
        # 記憶體管理
        self.data_buffer = {}
        self.buffer_max_points = 24       # 記憶體中保留2小時資料
        
        # 系統狀態
        self.is_running = False
        self.collection_count = 0
        self.last_successful_collection = None
        
        # 錯誤處理
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        
        # 目標門架
        self.target_gantries = [
            # 國道1號北向 (19個)
            '01F0340N', '01F0376N', '01F0413N', '01F0467N', '01F0492N',
            '01F0511N', '01F0532N', '01F0557N', '01F0584N', '01F0633N',
            '01F0664N', '01F0681N', '01F0699N', '01F0750N', '01F0880N',
            '01F0928N', '01F0956N', '01F0980N', '01F1045N',
            # 國道1號南向 (19個)
            '01F0339S', '01F0376S', '01F0413S', '01F0467S', '01F0492S',
            '01F0511S', '01F0532S', '01F0557S', '01F0578S', '01F0633S',
            '01F0664S', '01F0681S', '01F0699S', '01F0750S', '01F0880S',
            '01F0928S', '01F0950S', '01F0980S', '01F1045S',
            # 國道3號北向 (12個)
            '03F0447N', '03F0498N', '03F0525N', '03F0559N', '03F0648N',
            '03F0698N', '03F0746N', '03F0783N', '03F0846N', '03F0961N',
            '03F0996N', '03F1022N',
            # 國道3號南向 (12個)
            '03F0447S', '03F0498S', '03F0525S', '03F0559S', '03F0648S',
            '03F0698S', '03F0746S', '03F0783S', '03F0846S', '03F0961S',
            '03F0996S', '03F1022S'
        ]
        
        # 車種分類
        self.vehicle_types = {31: '小客車', 32: '小貨車', 41: '大客車', 42: '單體貨車', 5: '5軸聯結車'}
        
        # 註冊信號處理器（優雅關閉）
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("🚀 生產版即時監控系統初始化完成")
        self.logger.info(f"📡 監控代碼: {self.codes}")
        self.logger.info(f"📍 目標門架: {len(self.target_gantries)} 個")
        self.logger.info(f"💾 資料目錄: {self.realtime_dir}")
        self.logger.info(f"⏱️ 收集間隔: {self.collection_interval} 分鐘")

    def _setup_logging(self):
        """設定日誌系統"""
        log_file = os.path.join(self.log_dir, f"realtime_system_{datetime.now().strftime('%Y%m%d')}.log")
        
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
        """信號處理器 - 優雅關閉"""
        self.logger.info(f"收到信號 {signum}，準備優雅關閉...")
        self.is_running = False

    def download_csv_data(self, url, retries=2, wait=1):
        """下載CSV資料"""
        for i in range(1, retries + 1):
            try:
                response = requests.get(url, headers=self.headers, timeout=20)
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
                if i < retries:
                    time.sleep(wait)
                else:
                    self.logger.warning(f"下載失敗: {url} - {e}")
        
        return pd.DataFrame()

    def get_latest_available_time(self):
        """動態尋找最新可用的資料時間 - 從最近時間開始搜尋"""
        current = datetime.now()
        
        # 首先嘗試當前時間和最近的幾個5分鐘間隔
        search_times = []
        
        # 當前時間調整到5分鐘間隔
        current_minute = (current.minute // 5) * 5
        current_adjusted = current.replace(minute=current_minute, second=0, microsecond=0)
        
        # 生成搜尋時間列表：當前時間往前每5分鐘一次，搜尋2小時
        for minutes_back in range(0, 121, 5):
            search_time = current_adjusted - timedelta(minutes=minutes_back)
            search_times.append(search_time)
        
        self.logger.info(f"開始搜尋最新可用資料，從 {current_adjusted.strftime('%H:%M')} 開始往前找...")
        
        for i, test_time in enumerate(search_times):
            test_url = self._build_test_url(test_time)
            
            try:
                response = requests.head(test_url, headers=self.headers, timeout=5)
                if response.status_code == 200:
                    delay_minutes = (current - test_time).total_seconds() / 60
                    if delay_minutes < 10:
                        self.logger.info(f"✅ 發現即時資料: {test_time.strftime('%Y-%m-%d %H:%M')} (延遲 {delay_minutes:.0f} 分鐘)")
                    else:
                        self.logger.info(f"✅ 發現可用資料: {test_time.strftime('%Y-%m-%d %H:%M')} (延遲 {delay_minutes:.0f} 分鐘)")
                    return test_time
            except Exception as e:
                if i < 5:  # 只在前5次失敗時記錄詳細錯誤
                    self.logger.debug(f"測試 {test_time.strftime('%H:%M')} 失敗: {e}")
                continue
        
        self.logger.warning("⚠️ 未找到任何可用資料，使用預設時間")
        return current - timedelta(hours=2)

    def _build_test_url(self, target_time):
        """建立測試URL - 調整到5分鐘間隔"""
        # 將時間調整到最接近的5分鐘間隔
        minute = target_time.minute
        rounded_minute = (minute // 5) * 5  # 取5的倍數
        adjusted_time = target_time.replace(minute=rounded_minute, second=0, microsecond=0)
        
        date_str = adjusted_time.strftime('%Y%m%d')
        hour_str = adjusted_time.strftime('%H')
        minute_str = adjusted_time.strftime('%M')
        ts = f"{hour_str}{minute_str}00"
        
        return f"{self.base_url}/history/TDCS/M05A/{date_str}/{hour_str}/TDCS_M05A_{date_str}_{ts}.csv"

    def fetch_recent_data(self, target_time=None):
        """收集最近資料"""
        if target_time is None:
            target_time = self.get_latest_available_time()
        
        self.logger.info(f"收集 {target_time.strftime('%Y-%m-%d %H:xx')} 最近 {self.data_window_minutes} 分鐘資料")
        
        all_results = {}
        time_points_needed = self.data_window_minutes // 5
        
        for code in self.codes:
            code_data = []
            
            for i in range(time_points_needed):
                point_time = target_time - timedelta(minutes=i*5)
                point_data = self._fetch_single_timepoint(code, point_time)
                
                if not point_data.empty:
                    point_data['data_sequence'] = i
                    code_data.append(point_data)
                
                if len(code_data) >= self.min_data_points:
                    break
            
            if code_data:
                all_results[code] = pd.concat(code_data, ignore_index=True)
                self.logger.info(f"{code} 收集: {len(all_results[code])} 筆")
        
        return all_results

    def _fetch_single_timepoint(self, code, point_time):
        """獲取單一時間點資料"""
        date_str = point_time.strftime('%Y%m%d')
        hour_str = point_time.strftime('%H')
        minute_str = point_time.strftime('%M')
        
        minute_int = (int(minute_str) // 5) * 5
        ts = f"{hour_str}{minute_int:02d}00"
        
        url = f"{self.base_url}/history/TDCS/{code}/{date_str}/{hour_str}/TDCS_{code}_{date_str}_{ts}.csv"
        
        df = self.download_csv_data(url)
        if not df.empty:
            df['download_time'] = point_time.replace(minute=minute_int, second=0, microsecond=0)
            df['data_hour'] = int(hour_str)
            df['data_minute'] = minute_int
        
        return df

    def process_data(self, raw_data):
        """處理原始資料"""
        if not raw_data:
            return pd.DataFrame()
        
        self.logger.info("處理原始資料...")
        
        m05a_data = raw_data.get('M05A', pd.DataFrame())
        m04a_data = raw_data.get('M04A', pd.DataFrame())
        
        processed_records = []
        
        # 處理M05A和M04A資料
        for data, data_type in [(m05a_data, 'M05A'), (m04a_data, 'M04A')]:
            if data.empty:
                continue
            
            # 只保留目標門架
            target_data = data[
                data['GantryFrom'].isin(self.target_gantries) | 
                data['GantryTo'].isin(self.target_gantries)
            ]
            
            if target_data.empty:
                continue
            
            # 按門架和時間分組處理
            for gantry_col in ['GantryFrom', 'GantryTo']:
                gantry_data = target_data[target_data[gantry_col].isin(self.target_gantries)]
                
                for (gantry, hour, minute), group in gantry_data.groupby([gantry_col, 'data_hour', 'data_minute']):
                    
                    if data_type == 'M05A':
                        total_weighted_flow = 0
                        speeds = []
                        
                        for _, row in group.iterrows():
                            if row['VehicleType'] in self.vehicle_types and row['Speed'] > 0 and row['Volume'] > 0:
                                equivalent = self._calculate_vehicle_equivalent(row['VehicleType'], row['Speed'])
                                total_weighted_flow += row['Volume'] * equivalent
                                speeds.extend([row['Speed']] * int(row['Volume']))
                        
                        median_speed = np.median(speeds) if speeds else 0
                        
                        record = {
                            'station': gantry,
                            'date': datetime.now().strftime('%Y/%m/%d'),
                            'hour': hour,
                            'minute': minute,
                            'flow': total_weighted_flow,
                            'median_speed': median_speed,
                            'avg_travel_time': 0
                        }
                        
                    else:  # M04A
                        valid_data = group[
                            (group['VehicleType'].isin(self.vehicle_types)) &
                            (group['TravelTime'] > 0) & 
                            (group['VehicleCount'] > 0)
                        ]
                        
                        if not valid_data.empty:
                            total_travel_time = (valid_data['TravelTime'] * valid_data['VehicleCount']).sum()
                            total_count = valid_data['VehicleCount'].sum()
                            avg_travel_time = total_travel_time / total_count if total_count > 0 else 0
                            
                            record = {
                                'station': gantry,
                                'date': datetime.now().strftime('%Y/%m/%d'),
                                'hour': hour,
                                'minute': minute,
                                'flow': 0,
                                'median_speed': 0,
                                'avg_travel_time': avg_travel_time
                            }
                        else:
                            continue
                    
                    processed_records.append(record)
        
        if processed_records:
            df = pd.DataFrame(processed_records)
            
            # 合併同一站點同一時間的資料
            final_df = df.groupby(['station', 'date', 'hour', 'minute']).agg({
                'flow': 'max',
                'median_speed': 'max', 
                'avg_travel_time': 'max'
            }).reset_index()
            
            self.logger.info(f"處理完成: {len(final_df)} 筆記錄")
            return final_df
        
        return pd.DataFrame()

    def _calculate_vehicle_equivalent(self, vehicle_type, speed):
        """計算車種當量"""
        if vehicle_type in [31, 32]:
            return 1.0
        elif vehicle_type == 41:
            if speed < 70:
                return 1.13 + 1.66 * exp(-speed / 34.93)
            elif 70 <= speed <= 87:
                return 2.79 - 0.0206 * speed
            else:
                return 1.0
        elif vehicle_type == 42:
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
        
        # 使用資料的實際時間範圍作為檔案名稱
        if not processed_data.empty:
            min_hour = processed_data['hour'].min()
            max_hour = processed_data['hour'].max()
            min_minute = processed_data['minute'].min()
            max_minute = processed_data['minute'].max()
            data_date = processed_data['date'].iloc[0].replace('/', '')  # 2025/08/02 -> 20250802
            
            # 如果跨小時，使用時間範圍；否則使用單一時間
            if min_hour != max_hour:
                timestamp = f"{data_date}_{min_hour:02d}{min_minute:02d}-{max_hour:02d}{max_minute:02d}"
            else:
                timestamp = f"{data_date}_{min_hour:02d}{min_minute:02d}-{max_minute:02d}"
        else:
            # 備用方案：使用執行時間
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
        output_file = os.path.join(self.realtime_dir, f"realtime_shock_data_{timestamp}.csv")
        
        processed_data.to_csv(output_file, index=False, encoding='utf-8')
        
        self.logger.info(f"資料已保存: {output_file}")
        self.logger.info(f"記錄數: {len(processed_data)}, 站點數: {processed_data['station'].nunique()}")
        
        return output_file

    def update_buffer(self, new_data):
        """更新記憶體緩衝"""
        if new_data.empty:
            return
        
        current_time = datetime.now()
        
        for station in new_data['station'].unique():
            if station not in self.data_buffer:
                self.data_buffer[station] = []
            
            station_new_data = new_data[new_data['station'] == station]
            for _, row in station_new_data.iterrows():
                self.data_buffer[station].append({
                    'timestamp': current_time,
                    'data': row.to_dict()
                })
            
            # 限制緩衝大小
            if len(self.data_buffer[station]) > self.buffer_max_points:
                self.data_buffer[station] = self.data_buffer[station][-self.buffer_max_points:]

    def cleanup_old_files(self):
        """清理舊檔案"""
        self.logger.info("執行檔案清理...")
        
        # 清理CSV檔案
        cutoff_time = datetime.now() - timedelta(hours=self.max_file_age_hours)
        csv_pattern = os.path.join(self.realtime_dir, "realtime_shock_data_*.csv")
        
        deleted_csv = 0
        for file_path in glob.glob(csv_pattern):
            try:
                filename = os.path.basename(file_path)
                timestamp_str = filename.replace('realtime_shock_data_', '').replace('.csv', '')
                file_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M')
                
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted_csv += 1
            except:
                pass
        
        # 清理日誌檔案
        log_cutoff = datetime.now() - timedelta(days=self.max_log_age_days)
        log_pattern = os.path.join(self.log_dir, "realtime_system_*.log")
        
        deleted_logs = 0
        for file_path in glob.glob(log_pattern):
            try:
                filename = os.path.basename(file_path)
                date_str = filename.replace('realtime_system_', '').replace('.log', '')
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if file_date < log_cutoff:
                    os.remove(file_path)
                    deleted_logs += 1
            except:
                pass
        
        if deleted_csv > 0 or deleted_logs > 0:
            self.logger.info(f"清理完成: 刪除 {deleted_csv} 個CSV檔案, {deleted_logs} 個日誌檔案")

    def single_collection(self):
        """執行單次資料收集"""
        try:
            # 1. 尋找並收集最新資料
            latest_time = self.get_latest_available_time()
            current_time = datetime.now()
            delay_minutes = (current_time - latest_time).total_seconds() / 60
            
            self.logger.info(f"📊 準備收集資料 - 最新可用時間: {latest_time.strftime('%H:%M')}, 延遲: {delay_minutes:.0f}分鐘")
            
            raw_data = self.fetch_recent_data(latest_time)
            
            # 2. 處理資料
            processed_data = self.process_data(raw_data)
            
            # 3. 保存資料
            output_file = self.save_data(processed_data)
            
            # 4. 更新緩衝
            self.update_buffer(processed_data)
            
            # 5. 記錄成功
            self.last_successful_collection = datetime.now()
            self.consecutive_failures = 0
            
            return processed_data, output_file
            
        except Exception as e:
            self.logger.error(f"資料收集失敗: {e}")
            self.consecutive_failures += 1
            return pd.DataFrame(), None

    def start_continuous_monitoring(self):
        """啟動持續監控"""
        self.logger.info("🚀 啟動持續監控模式")
        self.logger.info(f"收集間隔: {self.collection_interval} 分鐘")
        self.logger.info(f"清理頻率: 每 {self.cleanup_frequency} 次收集")
        
        self.is_running = True
        
        try:
            while self.is_running:
                self.collection_count += 1
                
                self.logger.info(f"=== 第 {self.collection_count} 次收集 ===")
                
                # 檢查連續失敗次數
                if self.consecutive_failures >= self.max_consecutive_failures:
                    self.logger.error(f"連續失敗 {self.consecutive_failures} 次，暫停10分鐘")
                    time.sleep(600)  # 暫停10分鐘
                    self.consecutive_failures = 0
                
                # 執行資料收集
                processed_data, output_file = self.single_collection()
                
                # 定期清理
                if self.collection_count % self.cleanup_frequency == 0:
                    self.cleanup_old_files()
                
                # 系統狀態報告
                buffer_size = sum(len(buffer) for buffer in self.data_buffer.values())
                self.logger.info(f"系統狀態: 緩衝區 {len(self.data_buffer)} 站點, {buffer_size} 記錄")
                
                if not processed_data.empty:
                    self.logger.info(f"✅ 收集成功: {len(processed_data)} 筆記錄")
                else:
                    self.logger.warning("❌ 本次收集無有效資料")
                
                # 等待下次收集
                if self.is_running:
                    self.logger.info(f"等待 {self.collection_interval} 分鐘...")
                    time.sleep(self.collection_interval * 60)
                    
        except KeyboardInterrupt:
            self.logger.info("收到中斷信號")
        finally:
            self.logger.info("監控已停止")
            self.is_running = False

    def get_shock_detection_data(self, station, min_points=6):
        """為震波檢測提供資料"""
        if station not in self.data_buffer:
            return pd.DataFrame()
        
        buffer_records = []
        for item in self.data_buffer[station]:
            record = item['data'].copy()
            record['buffer_timestamp'] = item['timestamp']
            buffer_records.append(record)
        
        if len(buffer_records) >= min_points:
            df = pd.DataFrame(buffer_records)
            return df.sort_values(['hour', 'minute'])
        
        return pd.DataFrame()


def run_production_system():
    """執行生產版系統"""
    
    print("=" * 60)
    print("🚀 生產版即時交通監控系統")
    print("=" * 60)
    
    # 建立系統
    system = ProductionRealtimeSystem()
    
    print("\n選擇運行模式:")
    print("1. 測試模式 (單次收集)")
    print("2. 生產模式 (持續監控)")
    print("3. 自定義間隔監控")
    
    try:
        choice = input("\n請選擇 (1/2/3): ").strip()
        
        if choice == "1":
            print("\n🧪 執行測試模式...")
            processed_data, output_file = system.single_collection()
            
            if not processed_data.empty:
                print(f"✅ 測試成功!")
                print(f"📊 收集到 {len(processed_data)} 筆記錄")
                print(f"📍 涵蓋 {processed_data['station'].nunique()} 個站點")
                print(f"💾 檔案: {output_file}")
            else:
                print("❌ 測試失敗，請檢查網路連接")
        
        elif choice == "2":
            print("\n🚀 啟動生產模式 (每5分鐘收集一次)...")
            print("按 Ctrl+C 可以優雅停止")
            system.start_continuous_monitoring()
        
        elif choice == "3":
            interval = int(input("請輸入收集間隔(分鐘): "))
            system.collection_interval = interval
            print(f"\n🚀 啟動自定義監控 (每{interval}分鐘收集一次)...")
            print("按 Ctrl+C 可以優雅停止")
            system.start_continuous_monitoring()
        
        else:
            print("無效選擇")
    
    except KeyboardInterrupt:
        print("\n👋 系統已停止")
    except Exception as e:
        print(f"\n❌ 系統錯誤: {e}")


if __name__ == "__main__":
    run_production_system()