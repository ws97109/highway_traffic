#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import os
import glob
import pickle
import time
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
import warnings
warnings.filterwarnings('ignore')

# 導入現有的檢測器
from ..detection.final_optimized_detector import FinalOptimizedShockDetector
from .propagation_system import RealDataShockWavePropagationAnalyzer

class RealtimeShockPredictor:
    """
    即時衝擊波預測系統
    
    功能：
    1. 監控即時資料檔案
    2. 使用訓練好的模型進行衝擊波檢測
    3. 預測衝擊波傳播軌跡
    4. 提供即時預警資訊
    """
    
    def __init__(self, data_dir, config=None):
        """初始化即時預測系統"""
        
        # 基本設定
        self.data_dir = data_dir
        self.realtime_dir = os.path.join(data_dir, "realtime_data")
        self.model_dir = os.path.join(data_dir, "models")
        self.prediction_dir = os.path.join(data_dir, "predictions")
        
        # 建立目錄
        os.makedirs(self.prediction_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        
        # 設定日誌
        self._setup_logging()
        
        # 載入檢測器和分析器
        self.detector = FinalOptimizedShockDetector()
        
        # 初始化傳播分析器（需要站點資訊）
        etag_file = os.path.join(data_dir, "Taiwan", "Etag.csv")
        distance_file = os.path.join(data_dir, "Taiwan", "dis.csv")
        
        # 檢查多個可能的路徑
        possible_paths = [
            data_dir,
            os.path.join(os.path.dirname(data_dir), "國道", "data"),
            os.path.join(os.path.dirname(data_dir), "data"),
            "/Users/weiqihong/Desktop/碩士班/碩一下/highway-traffic/data"
        ]
        
        found_etag = False
        found_distance = False
        
        for path in possible_paths:
            test_etag = os.path.join(path, "Taiwan", "Etag.csv")
            test_distance = os.path.join(path, "Taiwan", "dis.csv")
            
            if os.path.exists(test_etag) and os.path.exists(test_distance):
                etag_file = test_etag
                distance_file = test_distance
                found_etag = True
                found_distance = True
                self.logger.info(f"✅ 找到站點資訊檔案: {path}")
                break
        
        if found_etag and found_distance:
            try:
                self.propagation_analyzer = RealDataShockWavePropagationAnalyzer(etag_file, distance_file)
                self.logger.info("✅ 傳播分析器初始化成功")
            except Exception as e:
                self.propagation_analyzer = None
                self.logger.warning(f"⚠️ 傳播分析器初始化失敗: {e}")
        else:
            self.propagation_analyzer = None
            self.logger.warning("⚠️ 站點資訊檔案未找到，傳播分析功能將受限")
            self.logger.info(f"尋找的檔案路徑: {etag_file}, {distance_file}")
        
        # 配置參數
        default_config = {
            'data_window_minutes': 60,      # 分析視窗：60分鐘
            'min_data_points': 12,          # 最少資料點：12個（1小時）
            'prediction_horizon': 30,       # 預測時間範圍：30分鐘
            'monitoring_interval': 60,      # 監控間隔：1分鐘
            'file_scan_interval': 30,       # 檔案掃描間隔：30秒
            'max_prediction_distance': 50,  # 最大預測距離：50公里
        }
        
        self.config = {**default_config, **(config or {})}
        
        # 資料緩衝區
        self.data_buffer = defaultdict(lambda: deque(maxlen=100))  # 每站點保留100個資料點
        self.last_processed_files = set()
        self.active_shocks = {}  # 活躍的衝擊波事件
        self.prediction_history = deque(maxlen=1000)  # 預測歷史
        
        # 系統狀態
        self.is_running = False
        self.last_prediction_time = None
        
        # 站點分組（按國道和方向）
        self.station_groups = self._build_station_groups()
        
        self.logger.info("🚀 即時衝擊波預測系統初始化完成")
        self.logger.info(f"📊 配置參數: {self.config}")
        self.logger.info(f"📍 站點分組: {len(self.station_groups)} 個群組")

    def _setup_logging(self):
        """設定日誌"""
        log_file = os.path.join(self.data_dir, "logs", f"shock_predictor_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ShockPredictor')

    def _build_station_groups(self):
        """建立站點分組"""
        groups = {
            '01F_N': [],  # 國道1號北向
            '01F_S': [],  # 國道1號南向
            '03F_N': [],  # 國道3號北向
            '03F_S': [],  # 國道3號南向
        }
        
        # 基於現有的目標門架清單
        target_stations = [
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
        
        for station in target_stations:
            if station.startswith('01F') and station.endswith('N'):
                groups['01F_N'].append(station)
            elif station.startswith('01F') and station.endswith('S'):
                groups['01F_S'].append(station)
            elif station.startswith('03F') and station.endswith('N'):
                groups['03F_N'].append(station)
            elif station.startswith('03F') and station.endswith('S'):
                groups['03F_S'].append(station)
        
        # 按里程排序
        for group_name in groups:
            groups[group_name].sort(key=self._extract_mileage)
        
        return groups

    def _extract_mileage(self, station):
        """從站點編號提取里程"""
        try:
            # 從 01F0340N 提取 034.0
            mileage_str = station[3:7]  # 0340
            return float(mileage_str[:-1] + '.' + mileage_str[-1])
        except:
            return 0

    def scan_new_data_files(self):
        """掃描新的資料檔案"""
        pattern = os.path.join(self.realtime_dir, "realtime_shock_data_*.csv")
        all_files = glob.glob(pattern)
        
        new_files = []
        for file_path in all_files:
            if file_path not in self.last_processed_files:
                # 檢查檔案是否在合理時間範圍內
                try:
                    filename = os.path.basename(file_path)
                    timestamp_str = filename.replace('realtime_shock_data_', '').replace('.csv', '')
                    file_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M')
                    
                    # 只處理最近2小時的檔案
                    if datetime.now() - file_time < timedelta(hours=2):
                        new_files.append(file_path)
                except:
                    continue
        
        return new_files

    def load_and_process_file(self, file_path):
        """載入並處理單個檔案"""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            
            if df.empty:
                return
            
            # 為每個站點更新緩衝區
            for station in df['station'].unique():
                station_data = df[df['station'] == station].sort_values(['hour', 'minute'])
                
                for _, row in station_data.iterrows():
                    data_point = {
                        'timestamp': datetime.now(),
                        'date': row['date'],
                        'hour': row['hour'],
                        'minute': row['minute'],
                        'flow': row['flow'],
                        'median_speed': row['median_speed'],
                        'avg_travel_time': row['avg_travel_time']
                    }
                    
                    self.data_buffer[station].append(data_point)
            
            self.last_processed_files.add(file_path)
            self.logger.info(f"✅ 處理檔案: {os.path.basename(file_path)} ({len(df)} 筆記錄)")
            
        except Exception as e:
            self.logger.error(f"❌ 檔案處理失敗: {file_path} - {e}")

    def detect_shocks_for_station(self, station):
        """為特定站點檢測衝擊波"""
        if station not in self.data_buffer or len(self.data_buffer[station]) < self.config['min_data_points']:
            return []
        
        # 轉換緩衝區資料為DataFrame
        buffer_data = list(self.data_buffer[station])
        df = pd.DataFrame([point for point in buffer_data])
        
        # 確保資料格式正確
        if 'median_speed' not in df.columns or 'flow' not in df.columns:
            return []
        
        # 使用檢測器分析
        try:
            shocks = self.detector.detect_significant_shocks(df)
            
            # 添加預測時間戳和站點資訊
            for shock in shocks:
                shock['detection_time'] = datetime.now()
                shock['station'] = station
                shock['prediction_id'] = f"{station}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return shocks
            
        except Exception as e:
            self.logger.error(f"❌ 站點 {station} 衝擊波檢測失敗: {e}")
            return []

    def predict_shock_propagation(self, shock, group_stations):
        """預測衝擊波傳播"""
        if not self.propagation_analyzer:
            return {}
        
        source_station = shock['station']
        
        # 找到源站點在群組中的位置
        if source_station not in group_stations:
            return {}
        
        source_idx = group_stations.index(source_station)
        predictions = {}
        
        # 預測下游站點
        for i in range(source_idx + 1, min(source_idx + 6, len(group_stations))):  # 預測最多5個下游站點
            target_station = group_stations[i]
            
            # 計算距離
            distance = self.propagation_analyzer.get_station_distance(source_station, target_station)
            if not distance:
                continue
            
            # 預測到達時間（使用歷史平均傳播速度）
            avg_propagation_speed = 25  # km/h，可以從歷史資料中計算
            travel_time_minutes = (distance / avg_propagation_speed) * 60
            
            predicted_arrival = datetime.now() + timedelta(minutes=travel_time_minutes)
            
            prediction = {
                'target_station': target_station,
                'source_shock': shock,
                'distance': distance,
                'predicted_arrival': predicted_arrival,
                'travel_time_minutes': travel_time_minutes,
                'propagation_speed': avg_propagation_speed,
                'confidence': self._calculate_confidence(shock, distance),
                'prediction_time': datetime.now()
            }
            
            predictions[target_station] = prediction
        
        return predictions

    def _calculate_confidence(self, shock, distance):
        """計算預測信心度"""
        # 基於衝擊波強度和距離計算信心度
        base_confidence = 0.7
        
        # 衝擊波等級影響
        level_weights = {'mild': 0.6, 'moderate': 0.8, 'severe': 0.9}
        level_factor = level_weights.get(shock['level'], 0.7)
        
        # 距離影響（距離越遠信心度越低）
        distance_factor = max(0.3, 1 - (distance / 100))  # 100km以上信心度最低0.3
        
        # 衝擊波強度影響
        strength_factor = min(1.0, shock['shock_strength'] / 50)  # 強度50%以上信心度最高
        
        confidence = base_confidence * level_factor * distance_factor * strength_factor
        return min(0.95, max(0.2, confidence))

    def run_single_prediction_cycle(self):
        """執行單次預測循環"""
        try:
            self.logger.info("🔍 開始預測循環...")
            
            # 1. 掃描新檔案
            new_files = self.scan_new_data_files()
            
            # 2. 處理新檔案
            for file_path in new_files:
                self.load_and_process_file(file_path)
            
            # 3. 為每個群組檢測衝擊波
            all_predictions = {}
            total_shocks = 0
            
            for group_name, stations in self.station_groups.items():
                group_shocks = []
                group_predictions = {}
                
                # 檢測每個站點的衝擊波
                for station in stations:
                    station_shocks = self.detect_shocks_for_station(station)
                    group_shocks.extend(station_shocks)
                    total_shocks += len(station_shocks)
                    
                    # 為每個衝擊波預測傳播
                    for shock in station_shocks:
                        propagation_predictions = self.predict_shock_propagation(shock, stations)
                        group_predictions.update(propagation_predictions)
                
                if group_shocks or group_predictions:
                    all_predictions[group_name] = {
                        'shocks': group_shocks,
                        'propagation_predictions': group_predictions
                    }
            
            # 4. 保存預測結果
            if all_predictions:
                self.save_predictions(all_predictions)
                self.logger.info(f"✅ 預測完成: 檢測到 {total_shocks} 個衝擊波，生成 {sum(len(p['propagation_predictions']) for p in all_predictions.values())} 個傳播預測")
            else:
                self.logger.info("ℹ️ 本次循環無衝擊波檢測結果")
            
            self.last_prediction_time = datetime.now()
            return all_predictions
            
        except Exception as e:
            self.logger.error(f"❌ 預測循環失敗: {e}")
            return {}

    def save_predictions(self, predictions):
        """保存預測結果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # 保存詳細預測結果
        prediction_file = os.path.join(self.prediction_dir, f"shock_predictions_{timestamp}.json")
        
        # 轉換為可序列化的格式
        serializable_predictions = {}
        for group_name, group_data in predictions.items():
            serializable_predictions[group_name] = {
                'shocks': [],
                'propagation_predictions': {}
            }
            
            # 處理衝擊波資料
            for shock in group_data['shocks']:
                shock_data = shock.copy()
                # 轉換時間為字串
                for time_field in ['detection_time', 'start_time', 'end_time']:
                    if time_field in shock_data and hasattr(shock_data[time_field], 'isoformat'):
                        shock_data[time_field] = shock_data[time_field].isoformat()
                    elif time_field in shock_data and isinstance(shock_data[time_field], str):
                        # 已經是字串，保持不變
                        pass
                serializable_predictions[group_name]['shocks'].append(shock_data)
            
            # 處理傳播預測
            for station, prediction in group_data['propagation_predictions'].items():
                pred_data = prediction.copy()
                # 轉換時間為字串
                for time_field in ['predicted_arrival', 'prediction_time']:
                    if time_field in pred_data and hasattr(pred_data[time_field], 'isoformat'):
                        pred_data[time_field] = pred_data[time_field].isoformat()
                    elif time_field in pred_data and isinstance(pred_data[time_field], str):
                        # 已經是字串，保持不變
                        pass
                
                # 處理source_shock中的時間欄位
                if 'source_shock' in pred_data and isinstance(pred_data['source_shock'], dict):
                    source_shock = pred_data['source_shock'].copy()
                    for time_field in ['detection_time', 'start_time', 'end_time']:
                        if time_field in source_shock and hasattr(source_shock[time_field], 'isoformat'):
                            source_shock[time_field] = source_shock[time_field].isoformat()
                    pred_data['source_shock'] = source_shock
                
                serializable_predictions[group_name]['propagation_predictions'][station] = pred_data
        
        # 寫入JSON檔案
        import json
        try:
            with open(prediction_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_predictions, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"❌ JSON儲存失敗: {e}")
            return
        
        # 保存簡化的CSV格式用於快速查詢
        csv_records = []
        for group_name, group_data in predictions.items():
            for prediction in group_data['propagation_predictions'].values():
                try:
                    # 安全地獲取時間字串
                    predicted_arrival = prediction.get('predicted_arrival', '')
                    if hasattr(predicted_arrival, 'strftime'):
                        arrival_str = predicted_arrival.strftime('%Y-%m-%d %H:%M')
                    elif isinstance(predicted_arrival, str):
                        arrival_str = predicted_arrival[:16] if len(predicted_arrival) >= 16 else predicted_arrival
                    else:
                        arrival_str = str(predicted_arrival)
                    
                    record = {
                        'group': group_name,
                        'source_station': prediction['source_shock']['station'],
                        'target_station': prediction['target_station'],
                        'shock_level': prediction['source_shock']['level'],
                        'shock_strength': prediction['source_shock']['shock_strength'],
                        'predicted_arrival': arrival_str,
                        'travel_time_minutes': prediction['travel_time_minutes'],
                        'distance_km': prediction['distance'],
                        'confidence': prediction['confidence']
                    }
                    csv_records.append(record)
                except Exception as e:
                    self.logger.warning(f"⚠️ 處理預測記錄時發生錯誤: {e}")
                    continue
        
        if csv_records:
            csv_file = os.path.join(self.prediction_dir, f"shock_predictions_summary_{timestamp}.csv")
            try:
                pd.DataFrame(csv_records).to_csv(csv_file, index=False, encoding='utf-8')
                self.logger.info(f"💾 預測結果已保存: {prediction_file}")
                self.logger.info(f"📊 預測摘要已保存: {csv_file}")
            except Exception as e:
                self.logger.error(f"❌ CSV儲存失敗: {e}")
        else:
            self.logger.info(f"💾 預測結果已保存: {prediction_file} (無傳播預測)")

    def start_continuous_prediction(self):
        """啟動持續預測"""
        self.logger.info("🚀 啟動持續預測模式")
        self.logger.info(f"⏱️ 監控間隔: {self.config['monitoring_interval']} 秒")
        
        self.is_running = True
        
        try:
            while self.is_running:
                predictions = self.run_single_prediction_cycle()
                
                # 等待下次預測
                if self.is_running:
                    time.sleep(self.config['monitoring_interval'])
                    
        except KeyboardInterrupt:
            self.logger.info("收到中斷信號")
        finally:
            self.logger.info("預測系統已停止")
            self.is_running = False

    def get_latest_predictions(self, max_age_minutes=30):
        """獲取最新的預測結果"""
        pattern = os.path.join(self.prediction_dir, "shock_predictions_summary_*.csv")
        files = glob.glob(pattern)
        
        recent_files = []
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        
        for file_path in files:
            try:
                filename = os.path.basename(file_path)
                timestamp_str = filename.replace('shock_predictions_summary_', '').replace('.csv', '')
                file_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M')
                
                if file_time >= cutoff_time:
                    recent_files.append((file_time, file_path))
            except:
                continue
        
        if not recent_files:
            return pd.DataFrame()
        
        # 載入最新的檔案
        recent_files.sort(reverse=True)
        latest_file = recent_files[0][1]
        
        try:
            return pd.read_csv(latest_file, encoding='utf-8')
        except:
            return pd.DataFrame()

    def stop(self):
        """停止預測系統"""
        self.is_running = False
        self.logger.info("🛑 預測系統停止指令已發出")


def main():
    """主函數"""
    # 設定路徑
    base_dir = "/Users/weiqihong/Desktop/碩士班/碩一下/highway-traffic/data"
    
    # 建立預測系統
    predictor = RealtimeShockPredictor(base_dir)
    
    print("=" * 60)
    print("🚀 即時衝擊波預測系統")
    print("=" * 60)
    print("\n選擇運行模式:")
    print("1. 測試模式 (單次預測)")
    print("2. 持續預測模式")
    print("3. 查看最新預測結果")
    
    try:
        choice = input("\n請選擇 (1/2/3): ").strip()
        
        if choice == "1":
            print("\n🧪 執行測試預測...")
            predictions = predictor.run_single_prediction_cycle()
            
            if predictions:
                print(f"✅ 測試成功!")
                for group_name, group_data in predictions.items():
                    print(f"📊 {group_name}: {len(group_data['shocks'])} 個衝擊波, {len(group_data['propagation_predictions'])} 個傳播預測")
            else:
                print("ℹ️ 目前無衝擊波檢測結果")
        
        elif choice == "2":
            print("\n🚀 啟動持續預測模式...")
            print("按 Ctrl+C 可以停止")
            predictor.start_continuous_prediction()
        
        elif choice == "3":
            print("\n📊 載入最新預測結果...")
            latest_predictions = predictor.get_latest_predictions()
            
            if not latest_predictions.empty:
                print(f"✅ 找到 {len(latest_predictions)} 個預測:")
                print(latest_predictions.to_string(index=False))
            else:
                print("ℹ️ 目前無可用的預測結果")
        
        else:
            print("無效選擇")
    
    except KeyboardInterrupt:
        print("\n👋 系統已停止")
    except Exception as e:
        print(f"\n❌ 系統錯誤: {e}")


if __name__ == "__main__":
    main()