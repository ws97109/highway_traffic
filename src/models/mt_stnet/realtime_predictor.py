#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json
from typing import Dict, List, Optional, Tuple
import threading
import time
from collections import deque

# 添加專案路徑
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.append(str(project_root))

from src.data.tdx_tisc_mix_system import OptimizedIntegratedDataCollectionSystem

class MTSTNetRealtimePredictor:
    """
    MT-STNet 即時預測系統
    
    功能：
    1. 載入預訓練的MT-STNet模型
    2. 接收即時交通資料
    3. 執行即時預測
    4. 輸出預測結果給前端
    """
    
    def __init__(self, model_path=None, config_path=None):
        """初始化即時預測系統"""
        
        # 設定路徑
        self.model_dir = current_dir
        self.weights_dir = self.model_dir / "weights"
        self.data_dir = project_root / "data"
        self.output_dir = self.data_dir / "predictions"
        
        # 建立輸出目錄
        self.output_dir.mkdir(exist_ok=True)
        
        # 設定日誌
        self._setup_logging()
        
        # 模型參數（從config.py載入）
        self.model_params = {
            'input_length': 12,      # 輸入時間步長
            'output_length': 12,     # 預測時間步長
            'site_num': 62,          # 站點數量
            'emb_size': 64,          # 嵌入維度
            'num_heads': 8,          # 注意力頭數
            'num_blocks': 1,         # 注意力層數
            'batch_size': 32,        # 批次大小
        }
        
        # 資料處理參數
        self.data_window_minutes = 60    # 資料視窗（分鐘）
        self.prediction_interval = 5     # 預測間隔（分鐘）
        self.min_data_points = 6         # 最少資料點數
        
        # 站點映射
        self.station_mapping = self._load_station_mapping()
        self.target_stations = list(self.station_mapping.keys())
        
        # 資料緩存
        self.data_cache = deque(maxlen=120)  # 保存2小時資料
        self.prediction_cache = deque(maxlen=50)  # 保存預測結果
        
        # 模型相關
        self.model = None
        self.sess = None
        self.is_model_loaded = False
        self.normalization_params = {'mean': 0, 'std': 1}
        
        # 資料收集系統
        self.data_collector = None
        
        # 執行狀態
        self.is_running = False
        self.prediction_thread = None
        self.last_prediction_time = None
        
        self.logger.info("🚀 MT-STNet 即時預測系統初始化完成")
        self.logger.info(f"📊 目標站點數: {len(self.target_stations)}")
        self.logger.info(f"⏱️ 預測間隔: {self.prediction_interval} 分鐘")

    def set_data_collector(self, data_collector):
        """設定外部資料收集器"""
        self.data_collector = data_collector
        self.logger.info("✅ 已設定外部資料收集器")

    def _setup_logging(self):
        """設定日誌系統"""
        log_dir = self.data_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"mt_stnet_predictor_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('MTSTNetPredictor')

    def _load_station_mapping(self):
        """載入站點映射"""
        station_mapping = {}
        
        # 從Etag.csv載入站點資訊
        etag_file = self.data_dir / 'Taiwan' / 'Etag.csv'
        try:
            if etag_file.exists():
                df = pd.read_csv(etag_file, encoding='utf-8')
                for idx, row in df.iterrows():
                    if pd.notna(row['編號']):
                        station_id = str(row['編號']).replace('-', '').replace('.', '')
                        station_name = row.get('名稱', f'站點_{station_id}')
                        station_mapping[station_id] = {
                            'name': station_name,
                            'index': idx,
                            'highway': row.get('國道', ''),
                            'direction': row.get('方向', '')
                        }
                
                self.logger.info(f"✅ 載入 {len(station_mapping)} 個站點映射")
            else:
                self.logger.warning("⚠️ Etag.csv 不存在，使用預設站點")
                # 使用預設站點
                default_stations = [
                    '01F0340N', '01F0376N', '01F0413N', '01F0467N', '01F0492N',
                    '01F0511N', '01F0532N', '01F0557N', '01F0584N', '01F0633N'
                ]
                for i, station in enumerate(default_stations):
                    station_mapping[station] = {
                        'name': f'站點_{station}',
                        'index': i,
                        'highway': '1',
                        'direction': 'N'
                    }
        except Exception as e:
            self.logger.error(f"❌ 載入站點映射失敗: {e}")
        
        return station_mapping

    def load_model(self, model_path=None):
        """載入預訓練模型"""
        try:
            # 載入正規化參數
            self._load_normalization_params()

            if model_path is None:
                # 尋找最新的模型檔案
                model_path = self._find_latest_model()

            if model_path and os.path.exists(model_path):
                self.logger.info(f"📥 找到模型檔案: {model_path}")

                # 檢查是否為TensorFlow checkpoint目錄
                if os.path.isdir(model_path):
                    checkpoint_file = os.path.join(model_path, "checkpoint")
                    if os.path.exists(checkpoint_file):
                        self.logger.info("📁 檢測到TensorFlow checkpoint格式")

                        # 載入真正的MT-STNet模型
                        try:
                            # 確保 TensorFlow 1.x 相容模式 (必須在導入 Model 之前)
                            try:
                                import tensorflow.compat.v1 as tf_v1
                                tf_v1.disable_v2_behavior()
                                self.logger.info("✅ 啟用 TensorFlow 1.x 相容模式")
                            except Exception as e:
                                self.logger.warning(f"⚠️ 無法啟用 TF1 相容模式: {e}")

                            # 導入必要模組
                            sys.path.insert(0, str(self.model_dir))
                            from config.config import parameter
                            from run_train import Model
                            import argparse

                            # 載入模型配置
                            para = parameter(argparse.ArgumentParser())
                            hp = para.get_para()
                            hp.is_training = False
                            hp.batch_size = 1

                            # 修正檔案路徑為絕對路徑
                            data_taiwan = self.data_dir / 'Taiwan'
                            hp.file_train_f = str(data_taiwan / 'train.csv')
                            hp.file_sp = str(data_taiwan / 'sp.csv')
                            hp.file_dis = str(data_taiwan / 'dis.csv')
                            hp.file_in_deg = str(data_taiwan / 'in_deg.csv')
                            hp.file_out_deg = str(data_taiwan / 'out_deg.csv')
                            hp.file_adj = str(data_taiwan / 'adjacent_fully.csv')

                            # 建立 TensorFlow session (使用 TF 1.x 相容 API)
                            import tensorflow.compat.v1 as tf_v1
                            config = tf_v1.ConfigProto()
                            config.gpu_options.allow_growth = True
                            self.sess = tf_v1.Session(config=config)

                            # 建立模型
                            self.logger.info("🔨 建立 MT-STNet 模型架構...")
                            self.model = Model(
                                hp=hp,
                                mean=self.normalization_params['mean'],
                                std=self.normalization_params['std']
                            )
                            self.model.initialize_session(self.sess)

                            # 載入模型權重
                            self.logger.info(f"📥 載入模型權重: {model_path}")
                            checkpoint_path = os.path.join(model_path, "MT_STNet-7")

                            # 使用 TF 1.x 相容 API
                            saver = tf_v1.train.Saver()
                            saver.restore(self.sess, checkpoint_path)

                            self.is_model_loaded = True
                            self.logger.info("✅ MT-STNet 模型載入成功")
                            return True

                        except Exception as e:
                            self.logger.error(f"❌ TensorFlow模型載入失敗: {e}")
                            import traceback
                            self.logger.error(traceback.format_exc())
                            self.is_model_loaded = False
                            if self.sess:
                                self.sess.close()
                                self.sess = None
                            return False
                    else:
                        self.logger.warning("⚠️ checkpoint檔案不存在")
                        return False
                else:
                    # 其他格式的模型檔案
                    self.logger.info("📄 檢測到其他格式模型檔案")
                    self.is_model_loaded = False
                    return False
            else:
                self.logger.warning("⚠️ 未找到預訓練模型")
                self.is_model_loaded = False
                return False

        except Exception as e:
            self.logger.error(f"❌ 模型載入失敗: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.is_model_loaded = False
            if self.sess:
                self.sess.close()
                self.sess = None
            return False

    def _find_latest_model(self):
        """尋找最新的模型檔案"""
        try:
            # 檢查TensorFlow checkpoint檔案
            checkpoint_dir = self.weights_dir / "MT_STNet-7"
            if checkpoint_dir.exists():
                checkpoint_file = checkpoint_dir / "checkpoint"
                if checkpoint_file.exists():
                    self.logger.info(f"📁 找到TensorFlow checkpoint: {checkpoint_file}")
                    return str(checkpoint_dir)
            
            # 檢查其他模型格式
            model_patterns = [
                self.weights_dir / "MT_STNet-7" / "*.h5",
                self.weights_dir / "MT_STNet-7" / "*.pb",
                self.weights_dir / "*.h5",
                self.weights_dir / "*.pb"
            ]
            
            for pattern in model_patterns:
                if pattern.parent.exists():
                    model_files = list(pattern.parent.glob(pattern.name))
                    if model_files:
                        # 返回最新的檔案
                        latest_file = max(model_files, key=lambda x: x.stat().st_mtime)
                        return str(latest_file)
            
            return None
        except Exception as e:
            self.logger.error(f"❌ 尋找模型檔案失敗: {e}")
            return None

    def _load_normalization_params(self):
        """載入資料正規化參數"""
        try:
            # 嘗試從訓練資料計算正規化參數
            train_file = self.data_dir / 'Taiwan' / 'train.csv'
            if train_file.exists():
                df = pd.read_csv(train_file)
                if 'flow' in df.columns:
                    self.normalization_params['mean'] = df['flow'].mean()
                    self.normalization_params['std'] = df['flow'].std()
                    self.logger.info(f"📊 正規化參數: mean={self.normalization_params['mean']:.2f}, std={self.normalization_params['std']:.2f}")
            else:
                # 使用預設值
                self.normalization_params = {'mean': 1000, 'std': 500}
                self.logger.info("📊 使用預設正規化參數")

        except Exception as e:
            self.logger.error(f"❌ 載入正規化參數失敗: {e}")
            self.normalization_params = {'mean': 1000, 'std': 500}

    def _load_auxiliary_data(self, filename: str) -> np.ndarray:
        """載入輔助資料（sp, dis, in_deg, out_deg）"""
        try:
            file_path = self.data_dir / 'Taiwan' / filename
            if file_path.exists():
                # in_deg.csv 和 out_deg.csv 有表頭，需要跳過
                if filename in ['in_deg.csv', 'out_deg.csv']:
                    data = pd.read_csv(file_path)
                    # 只取第二列（degree 列），轉換為 [1, site_num] 的形狀
                    deg_values = data.iloc[:, 1].values
                    # 確保有足夠的站點
                    if len(deg_values) < self.model_params['site_num']:
                        # 補零到正確大小
                        deg_values = np.pad(deg_values, (0, self.model_params['site_num'] - len(deg_values)),
                                          mode='constant', constant_values=0)
                    return deg_values[:self.model_params['site_num']].reshape(1, -1).astype(np.int32)
                else:
                    # sp.csv 和 dis.csv 沒有表頭
                    data = pd.read_csv(file_path, header=None)
                    return data.values
            else:
                self.logger.warning(f"⚠️ {filename} 不存在")
                # 返回預設值
                if filename == 'sp.csv':
                    return np.zeros((self.model_params['site_num'] * self.model_params['site_num'], 15), dtype=np.int32)
                elif filename == 'dis.csv':
                    return np.eye(self.model_params['site_num'], dtype=np.float32)
                elif filename in ['in_deg.csv', 'out_deg.csv']:
                    return np.zeros((1, self.model_params['site_num']), dtype=np.int32)
        except Exception as e:
            self.logger.error(f"❌ 載入 {filename} 失敗: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            if filename == 'sp.csv':
                return np.zeros((self.model_params['site_num'] * self.model_params['site_num'], 15), dtype=np.int32)
            elif filename == 'dis.csv':
                return np.eye(self.model_params['site_num'], dtype=np.float32)
            elif filename in ['in_deg.csv', 'out_deg.csv']:
                return np.zeros((1, self.model_params['site_num']), dtype=np.int32)

    def initialize_data_collector(self):
        """初始化資料收集系統"""
        try:
            # 使用絕對路徑
            data_path = str(self.data_dir)
            self.data_collector = OptimizedIntegratedDataCollectionSystem(base_dir=data_path)
            
            # 載入歷史資料到緩存
            if not self.data_collector.historical_loaded:
                self.data_collector.load_initial_historical_data()
            
            self.logger.info("✅ 資料收集系統初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 資料收集系統初始化失敗: {e}")
            return False

    def get_realtime_data(self) -> pd.DataFrame:
        """取得即時交通資料"""
        try:
            if self.data_collector is None:
                if not self.initialize_data_collector():
                    return pd.DataFrame()
            
            # 從資料收集系統取得最新資料
            latest_data = self.data_collector.get_cached_data_for_output(
                time_window_minutes=self.data_window_minutes
            )
            
            if not latest_data.empty:
                # 過濾目標站點
                target_data = latest_data[
                    latest_data['station'].isin(self.target_stations)
                ].copy()
                
                self.logger.info(f"📊 取得即時資料: {len(target_data)} 筆記錄，{target_data['station'].nunique()} 個站點")
                return target_data
            else:
                self.logger.warning("⚠️ 無可用的即時資料")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"❌ 取得即時資料失敗: {e}")
            return pd.DataFrame()

    def preprocess_data_for_prediction(self, data: pd.DataFrame) -> Optional[Tuple]:
        """預處理資料用於預測"""
        try:
            if data.empty:
                return None

            # 確保timestamp為datetime類型
            if 'timestamp' in data.columns and not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
                data['timestamp'] = pd.to_datetime(data['timestamp'])

            # 確保有足夠的時間步長
            required_timesteps = self.model_params['input_length']
            total_timesteps = self.model_params['input_length'] + self.model_params['output_length']

            # 按站點和時間排序
            data = data.sort_values(['station', 'timestamp'])

            # 建立時間序列矩陣和時間特徵
            station_sequences = {}
            timestamps_list = []

            for station in self.target_stations:
                station_data = data[data['station'] == station].copy()

                if len(station_data) >= self.min_data_points:
                    # 取最近的資料點
                    recent_data = station_data.tail(required_timesteps)

                    # 提取流量特徵（只使用flow，因為features=1）
                    features = []
                    for _, row in recent_data.iterrows():
                        feature_vector = [row.get('flow', 0)]
                        features.append(feature_vector)

                    # 如果資料不足，用最後一個值填充
                    while len(features) < required_timesteps:
                        if features:
                            features.insert(0, features[0])
                        else:
                            features.append([0])

                    station_sequences[station] = np.array(features[-required_timesteps:])

                    # 保存最後一個時間戳記
                    if len(recent_data) > 0:
                        timestamps_list.append(recent_data.iloc[-1]['timestamp'])

            if not station_sequences:
                self.logger.warning("⚠️ 無足夠資料進行預測")
                return None

            # 組合成批次格式
            batch_data = []
            station_list = []

            for station in self.target_stations:
                if station in station_sequences:
                    batch_data.append(station_sequences[station])
                    station_list.append(station)
                else:
                    # 用零填充缺失的站點
                    batch_data.append(np.zeros((required_timesteps, 1)))
                    station_list.append(station)

            if batch_data:
                # 轉換為numpy陣列
                batch_array = np.array(batch_data)  # [stations, timesteps, features]
                batch_array = np.transpose(batch_array, (1, 0, 2))  # [timesteps, stations, features]
                batch_array = np.expand_dims(batch_array, axis=0)  # [1, timesteps, stations, features]

                # 正規化流量資料
                batch_array = (batch_array - self.normalization_params['mean']) / self.normalization_params['std']

                # 生成時間特徵
                base_time = timestamps_list[0] if timestamps_list else datetime.now()

                # day_of_week 和 minute_of_day: [total_timesteps, site_num]
                # 模型期望的形狀是 [?, site_num]，其中 ? 是 batch_size * total_timesteps
                day_of_week = []
                minute_of_day = []

                for t in range(total_timesteps):
                    current_time = base_time + timedelta(minutes=t * self.model_params.get('granularity', 5))
                    dow = current_time.weekday()
                    mod = (current_time.hour * 60 + current_time.minute) // self.model_params.get('granularity', 5)

                    # 每個時間步一行，每行有 site_num 個相同的值
                    day_of_week.append([dow] * self.model_params['site_num'])
                    minute_of_day.append([mod] * self.model_params['site_num'])

                # 轉換為 [total_timesteps, site_num]
                day_of_week = np.array(day_of_week, dtype=np.int32)  # [24, 62]
                minute_of_day = np.array(minute_of_day, dtype=np.int32)  # [24, 62]

                # 生成 x_all (input + output長度)
                # 對於預測，output部分用input最後的值填充
                x_all = np.zeros((1, total_timesteps, self.model_params['site_num'], 1))
                x_all[:, :required_timesteps, :, :] = batch_array
                # 用最後一個時間步填充未來
                x_all[:, required_timesteps:, :, :] = batch_array[:, -1:, :, :]

                self.logger.info(f"📊 預處理完成: features={batch_array.shape}, x_all={x_all.shape}")

                return {
                    'features': batch_array,
                    'x_all': x_all,
                    'day_of_week': day_of_week,
                    'minute_of_day': minute_of_day,
                    'station_list': station_list
                }

            return None

        except Exception as e:
            self.logger.error(f"❌ 資料預處理失敗: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

    def predict_traffic(self, input_data: Dict, station_list: List[str]) -> Dict:
        """執行交通預測"""
        try:
            current_time = datetime.now()

            if self.is_model_loaded and self.model is not None and self.sess is not None:
                # 使用真實模型預測
                try:
                    # 載入輔助資料
                    sys.path.insert(0, str(self.model_dir))
                    from utils.utils import construct_feed_dict

                    # 載入圖結構資料
                    sp_data = self._load_auxiliary_data('sp.csv')
                    dis_data = self._load_auxiliary_data('dis.csv')
                    in_deg_data = self._load_auxiliary_data('in_deg.csv')
                    out_deg_data = self._load_auxiliary_data('out_deg.csv')

                    # 建立 feed_dict
                    feed_dict = construct_feed_dict(
                        features=input_data['features'],
                        x_all=input_data['x_all'],
                        adj=self.model.adj,
                        labels=np.zeros((1, self.model_params['site_num'], self.model_params['output_length'])),  # dummy labels
                        day_of_week=input_data['day_of_week'],
                        minute_of_day=input_data['minute_of_day'],
                        placeholders=self.model.placeholders,
                        site_num=self.model_params['site_num'],
                        sp=sp_data,
                        dis=dis_data,
                        in_deg=in_deg_data,
                        out_deg=out_deg_data,
                        is_training=False
                    )

                    # 執行預測
                    predictions = self.sess.run(self.model.pre, feed_dict=feed_dict)
                    self.logger.info(f"🤖 使用MT-STNet模型預測，輸出shape: {predictions.shape}")

                except Exception as e:
                    self.logger.error(f"❌ 模型預測失敗: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    # 回退到簡化預測
                    predictions = self._simple_prediction(input_data['features'], station_list)
                    self.logger.info("📊 回退使用簡化預測邏輯")
            else:
                # 使用簡化預測邏輯
                predictions = self._simple_prediction(input_data.get('features', input_data) if isinstance(input_data, dict) else input_data, station_list)
                self.logger.info("📊 使用簡化預測邏輯")
            
            # 處理預測結果
            prediction_results = []

            for i, station in enumerate(station_list):
                station_info = self.station_mapping.get(station, {})

                # 計算預測值
                # MT-STNet 輸出: [batch, site_num, output_length]
                if isinstance(predictions, np.ndarray) and len(predictions.shape) >= 2:
                    if i < predictions.shape[1]:
                        # 取第一個預測時間步的值
                        predicted_flow = float(predictions[0, i, 0] if len(predictions.shape) > 2 else predictions[0, i])
                    else:
                        predicted_flow = 0
                else:
                    # 簡化預測返回dict
                    predicted_flow = predictions.get(station, 0)
                    # 反正規化（簡化預測已經是正規化的值）
                    if isinstance(predicted_flow, (int, float)):
                        predicted_flow = predicted_flow * self.normalization_params['std'] + self.normalization_params['mean']

                # 確保非負值
                predicted_flow = max(0, predicted_flow)
                
                # 估算速度（基於流量的簡化模型）
                predicted_speed = self._estimate_speed_from_flow(predicted_flow)
                
                # 計算信心度
                confidence = self._calculate_confidence(station, predicted_flow)
                
                prediction_result = {
                    'station_id': station,
                    'location_name': station_info.get('name', f'站點_{station}'),
                    'predicted_flow': round(predicted_flow, 1),
                    'predicted_speed': round(predicted_speed, 1),
                    'confidence': round(confidence, 3),
                    'time_horizon': self.model_params['output_length'] * 5,  # 分鐘
                    'timestamp': current_time.isoformat(),
                    'highway': station_info.get('highway', ''),
                    'direction': station_info.get('direction', '')
                }
                
                prediction_results.append(prediction_result)
            
            # 組合最終結果
            result = {
                'predictions': prediction_results,
                'model_version': 'MT-STNet-v1.0',
                'prediction_time': current_time.isoformat(),
                'time_horizon_minutes': self.model_params['output_length'] * 5,
                'total_stations': len(prediction_results),
                'data_source': 'REALTIME'
            }
            
            # 快取預測結果
            self.prediction_cache.append(result)
            
            self.logger.info(f"✅ 預測完成: {len(prediction_results)} 個站點")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 預測失敗: {e}")
            return {'predictions': [], 'error': str(e)}

    def _simple_prediction(self, input_data: np.ndarray, station_list: List[str]) -> Dict:
        """簡化預測邏輯（當模型未載入時使用）"""
        predictions = {}
        
        try:
            # 基於歷史趨勢的簡單預測
            for i, station in enumerate(station_list):
                if i < input_data.shape[2]:  # 確保索引有效
                    # 取最近幾個時間點的流量
                    recent_flows = input_data[0, -3:, i, 0]  # 最近3個時間點的流量
                    
                    if len(recent_flows) > 0:
                        # 計算趨勢
                        if len(recent_flows) >= 2:
                            trend = recent_flows[-1] - recent_flows[-2]
                        else:
                            trend = 0
                        
                        # 預測下一個時間點（加上趨勢和一些隨機性）
                        base_prediction = recent_flows[-1] + trend * 0.5
                        
                        # 添加時間因子（考慮交通模式）
                        current_hour = datetime.now().hour
                        time_factor = self._get_time_factor(current_hour)
                        
                        predicted_flow = base_prediction * time_factor
                        predictions[station] = float(predicted_flow)
                    else:
                        predictions[station] = 0
                else:
                    predictions[station] = 0
            
        except Exception as e:
            self.logger.error(f"❌ 簡化預測失敗: {e}")
            for station in station_list:
                predictions[station] = 0
        
        return predictions

    def _get_time_factor(self, hour: int) -> float:
        """根據時間取得交通流量因子"""
        # 簡化的時間因子（基於一般交通模式）
        if 7 <= hour <= 9:  # 早高峰
            return 1.3
        elif 17 <= hour <= 19:  # 晚高峰
            return 1.4
        elif 22 <= hour or hour <= 5:  # 深夜
            return 0.3
        else:  # 其他時間
            return 1.0

    def _estimate_speed_from_flow(self, flow: float) -> float:
        """根據流量估算速度"""
        # 簡化的流量-速度關係模型
        if flow <= 0:
            return 90  # 自由流速度
        elif flow <= 1000:
            return 90 - (flow / 1000) * 20  # 線性下降
        elif flow <= 2000:
            return 70 - ((flow - 1000) / 1000) * 30
        else:
            return max(20, 40 - ((flow - 2000) / 1000) * 15)  # 擁塞狀態

    def _calculate_confidence(self, station: str, predicted_flow: float) -> float:
        """計算預測信心度"""
        base_confidence = 0.75
        
        # 根據資料品質調整
        if predicted_flow > 0:
            base_confidence += 0.1
        
        # 根據站點重要性調整
        if station in self.target_stations[:20]:  # 前20個重要站點
            base_confidence += 0.05
        
        # 根據時間調整（白天信心度較高）
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 22:
            base_confidence += 0.05
        
        return min(0.95, max(0.5, base_confidence))

    def save_predictions(self, predictions: Dict) -> str:
        """保存預測結果"""
        try:
            current_time = datetime.now()
            filename = f"mt_stnet_predictions_{current_time.strftime('%Y%m%d_%H%M')}.json"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(predictions, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 預測結果已保存: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"❌ 保存預測結果失敗: {e}")
            return ""

    def get_latest_predictions(self) -> Dict:
        """取得最新預測結果"""
        if self.prediction_cache:
            return self.prediction_cache[-1]
        else:
            return {'predictions': [], 'message': '暫無預測資料'}

    def run_single_prediction(self) -> Dict:
        """執行單次預測"""
        try:
            self.logger.info("🔮 開始執行單次預測...")

            # 取得即時資料
            realtime_data = self.get_realtime_data()
            if realtime_data.empty:
                return {'predictions': [], 'error': '無可用的即時資料'}

            # 預處理資料
            processed_result = self.preprocess_data_for_prediction(realtime_data)
            if processed_result is None:
                return {'predictions': [], 'error': '資料預處理失敗'}

            # 新格式：processed_result 是 dict
            if isinstance(processed_result, dict):
                input_data = processed_result
                station_list = processed_result['station_list']
            else:
                # 舊格式兼容
                input_data, station_list = processed_result

            # 執行預測
            predictions = self.predict_traffic(input_data, station_list)
            
            # 保存結果
            if predictions.get('predictions'):
                self.save_predictions(predictions)
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"❌ 單次預測失敗: {e}")
            return {'predictions': [], 'error': str(e)}

    def start_continuous_prediction(self):
        """啟動持續預測"""
        self.logger.info("🚀 啟動MT-STNet持續預測模式")
        self.is_running = True
        
        def prediction_loop():
            while self.is_running:
                try:
                    # 檢查是否需要執行預測
                    current_time = datetime.now()
                    
                    if (self.last_prediction_time is None or 
                        (current_time - self.last_prediction_time).total_seconds() >= self.prediction_interval * 60):
                        
                        self.logger.info(f"⏰ 執行定時預測 - {current_time.strftime('%H:%M:%S')}")
                        
                        # 執行預測
                        result = self.run_single_prediction()
                        
                        if result.get('predictions'):
                            self.last_prediction_time = current_time
                            self.logger.info(f"✅ 預測完成: {len(result['predictions'])} 個站點")
                        else:
                            self.logger.warning("⚠️ 預測無結果")
                    
                    # 等待30秒後再檢查
                    time.sleep(30)
                    
                except Exception as e:
                    self.logger.error(f"❌ 預測循環錯誤: {e}")
                    time.sleep(60)  # 錯誤時等待更長時間
        
        # 啟動預測線程
        self.prediction_thread = threading.Thread(target=prediction_loop, daemon=True)
        self.prediction_thread.start()
        
        self.logger.info(f"✅ 持續預測已啟動，間隔: {self.prediction_interval} 分鐘")

    def stop_continuous_prediction(self):
        """停止持續預測"""
        self.is_running = False
        if self.prediction_thread and self.prediction_thread.is_alive():
            self.prediction_thread.join(timeout=5)
        # 清理 TensorFlow session
        if self.sess is not None:
            try:
                self.sess.close()
                self.logger.info("✅ TensorFlow session 已關閉")
            except Exception as e:
                self.logger.error(f"❌ 關閉 session 失敗: {e}")
            finally:
                self.sess = None
        self.logger.info("🛑 持續預測已停止")

    def get_system_status(self) -> Dict:
        """取得系統狀態"""
        return {
            'model_loaded': self.is_model_loaded,
            'is_running': self.is_running,
            'last_prediction_time': self.last_prediction_time.isoformat() if self.last_prediction_time else None,
            'prediction_interval_minutes': self.prediction_interval,
            'target_stations_count': len(self.target_stations),
            'cached_predictions_count': len(self.prediction_cache),
            'data_collector_available': self.data_collector is not None
        }


def main():
    """主函數 - 用於測試"""
    print("🚀 MT-STNet 即時預測系統測試")
    
    predictor = MTSTNetRealtimePredictor()
    
    print("\n選擇測試模式:")
    print("1. 載入模型測試")
    print("2. 單次預測測試")
    print("3. 持續預測模式")
    print("4. 系統狀態檢查")
    
    choice = input("請選擇 (1-4): ").strip()
    
    if choice == "1":
        print("\n🔍 測試模型載入...")
        success = predictor.load_model()
        if success:
            print("✅ 模型載入成功")
        else:
            print("⚠️ 模型載入失敗，將使用簡化預測")
    
    elif choice == "2":
        print("\n🔮 執行單次預測測試...")
        predictor.load_model()
        result = predictor.run_single_prediction()
        
        if result.get('predictions'):
            print(f"✅ 預測成功: {len(result['predictions'])} 個站點")
            print("\n📊 預測結果預覽:")
            for pred in result['predictions'][:5]:  # 顯示前5個
                print(f"  {pred['location_name']}: 流量={pred['predicted_flow']:.1f}, 速度={pred['predicted_speed']:.1f}km/h, 信心度={pred['confidence']:.2f}")
        else:
            print(f"❌ 預測失敗: {result.get('error', '未知錯誤')}")
    
    elif choice == "3":
        print("\n🚀 啟動持續預測模式...")
        predictor.load_model()
        predictor.start_continuous_prediction()
        
        try:
            print("💡 按 Ctrl+C 停止預測")
            while predictor.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 停止持續預測...")
            predictor.stop_continuous_prediction()
    
    elif choice == "4":
        print("\n📊 系統狀態檢查...")
        status = predictor.get_system_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
    
    print("\n👋 測試完成")


if __name__ == "__main__":
    main()
