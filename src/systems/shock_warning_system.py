#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import os
import json
import smtplib
import requests
import time
import threading
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from collections import defaultdict, deque
import glob
import sqlite3

class ShockWarningSystem:
    """
    衝擊波預警系統
    
    功能：
    1. 監控衝擊波預測結果
    2. 分級預警（輕微、中等、嚴重、緊急）
    3. 多通道通知（Email、LINE、Slack、Push）
    4. 用戶訂閱管理
    5. 預警歷史記錄
    """
    
    def __init__(self, data_dir, config_file=None):
        """初始化預警系統"""
        
        self.data_dir = data_dir
        self.prediction_dir = os.path.join(data_dir, "predictions")
        self.warning_dir = os.path.join(data_dir, "warnings")
        self.log_dir = os.path.join(data_dir, "logs")
        
        # 建立目錄
        os.makedirs(self.warning_dir, exist_ok=True)
        
        # 設定日誌
        self._setup_logging()
        
        # 載入配置
        self.config = self._load_config(config_file)
        
        # 初始化資料庫
        self._init_database()
        
        # 預警等級定義
        self.warning_levels = {
            'INFO': {
                'name': '資訊',
                'color': '#17a2b8',
                'priority': 1,
                'criteria': {
                    'shock_strength_min': 0,
                    'shock_strength_max': 20,
                    'speed_drop_min': 0,
                    'speed_drop_max': 15
                }
            },
            'MINOR': {
                'name': '輕微',
                'color': '#ffc107',
                'priority': 2,
                'criteria': {
                    'shock_strength_min': 20,
                    'shock_strength_max': 35,
                    'speed_drop_min': 15,
                    'speed_drop_max': 25
                }
            },
            'MODERATE': {
                'name': '中等',
                'color': '#fd7e14',
                'priority': 3,
                'criteria': {
                    'shock_strength_min': 35,
                    'shock_strength_max': 50,
                    'speed_drop_min': 25,
                    'speed_drop_max': 40
                }
            },
            'SEVERE': {
                'name': '嚴重',
                'color': '#dc3545',
                'priority': 4,
                'criteria': {
                    'shock_strength_min': 50,
                    'shock_strength_max': 70,
                    'speed_drop_min': 40,
                    'speed_drop_max': 60
                }
            },
            'CRITICAL': {
                'name': '緊急',
                'color': '#721c24',
                'priority': 5,
                'criteria': {
                    'shock_strength_min': 70,
                    'shock_strength_max': 100,
                    'speed_drop_min': 60,
                    'speed_drop_max': 100
                }
            }
        }
        
        # 系統狀態
        self.is_running = False
        self.last_check_time = None
        self.active_warnings = {}
        self.notification_queue = deque()
        
        # 通知限制（防止垃圾訊息）
        self.notification_cooldown = {}  # 每個用戶的冷卻時間
        self.cooldown_minutes = 5  # 相同類型預警5分鐘內不重複發送
        
        self.logger.info("🚨 衝擊波預警系統初始化完成")
        self.logger.info(f"📊 預警等級: {len(self.warning_levels)} 個")
        self.logger.info(f"💾 資料庫: {self.db_path}")

    def _setup_logging(self):
        """設定日誌"""
        log_file = os.path.join(self.log_dir, f"warning_system_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('WarningSystem')

    def _load_config(self, config_file):
        """載入配置檔案"""
        default_config = {
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_address': ''
            },
            'line': {
                'enabled': False,
                'access_token': ''
            },
            'slack': {
                'enabled': False,
                'webhook_url': ''
            },
            'monitoring': {
                'check_interval': 30,  # 秒
                'max_warning_age': 60,  # 分鐘
                'auto_cleanup': True
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 合併配置
                    for key, value in user_config.items():
                        if key in default_config and isinstance(value, dict):
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
            except Exception as e:
                self.logger.warning(f"配置檔案載入失敗，使用預設配置: {e}")
        
        return default_config

    def _init_database(self):
        """初始化SQLite資料庫"""
        self.db_path = os.path.join(self.warning_dir, "warnings.db")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 創建預警記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    warning_id TEXT UNIQUE,
                    level TEXT,
                    title TEXT,
                    message TEXT,
                    source_station TEXT,
                    target_station TEXT,
                    shock_strength REAL,
                    predicted_arrival TEXT,
                    confidence REAL,
                    created_time TEXT,
                    status TEXT DEFAULT 'ACTIVE'
                )
            ''')
            
            # 創建用戶訂閱表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscribers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    contact_method TEXT,
                    contact_info TEXT,
                    subscribed_levels TEXT,
                    subscribed_stations TEXT,
                    created_time TEXT,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # 創建通知記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    warning_id TEXT,
                    user_id TEXT,
                    contact_method TEXT,
                    status TEXT,
                    sent_time TEXT,
                    error_message TEXT
                )
            ''')
            
            conn.commit()

    def classify_warning_level(self, prediction):
        """根據預測結果分類預警等級"""
        shock_strength = prediction.get('shock_strength', 0)
        if isinstance(shock_strength, str):
            try:
                shock_strength = float(shock_strength)
            except:
                shock_strength = 0
        
        # 安全地獲取source_shock資訊
        source_shock = prediction.get('source_shock', {})
        if isinstance(source_shock, str):
            speed_drop = 0
        else:
            speed_drop = source_shock.get('speed_drop', 0)
            if isinstance(speed_drop, str):
                try:
                    speed_drop = float(speed_drop)
                except:
                    speed_drop = 0
        
        confidence = prediction.get('confidence', 0)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except:
                confidence = 0
        
        # 基於衝擊波強度和速度下降程度分類
        for level, config in self.warning_levels.items():
            criteria = config['criteria']
            
            if (criteria['shock_strength_min'] <= shock_strength <= criteria['shock_strength_max'] and
                criteria['speed_drop_min'] <= speed_drop <= criteria['speed_drop_max']):
                
                # 考慮信心度調整等級
                if confidence < 0.5 and level in ['SEVERE', 'CRITICAL']:
                    # 低信心度的嚴重預警降級
                    level_priorities = list(self.warning_levels.keys())
                    current_idx = level_priorities.index(level)
                    if current_idx > 0:
                        level = level_priorities[current_idx - 1]
                
                return level
        
        # 預設為INFO等級
        return 'INFO'

    def create_warning(self, prediction):
        """創建預警"""
        level = self.classify_warning_level(prediction)
        level_config = self.warning_levels[level]
        
        # 生成預警ID
        warning_id = f"{prediction['target_station']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 安全地獲取source_shock資訊
        source_shock = prediction.get('source_shock', {})
        if isinstance(source_shock, str):
            # 如果source_shock是字串，嘗試解析或使用預設值
            source_shock = {
                'station': prediction.get('source_station', 'Unknown'),
                'level': 'moderate',
                'speed_drop': prediction.get('speed_drop', 0)
            }
        
        # 計算預計到達時間
        predicted_arrival = prediction.get('predicted_arrival', datetime.now().isoformat())
        if isinstance(predicted_arrival, str):
            try:
                predicted_arrival = datetime.fromisoformat(predicted_arrival)
            except:
                predicted_arrival = datetime.now()
        
        time_to_arrival = predicted_arrival - datetime.now()
        minutes_to_arrival = int(time_to_arrival.total_seconds() / 60)
        
        # 生成預警訊息
        title = f"🚨 {level_config['name']}交通衝擊波預警"
        
        source_info = self._get_station_readable_name(source_shock.get('station', prediction.get('source_station', '')))
        target_info = self._get_station_readable_name(prediction['target_station'])
        
        shock_strength = prediction.get('shock_strength', 0)
        if isinstance(shock_strength, str):
            try:
                shock_strength = float(shock_strength)
            except:
                shock_strength = 0
        
        speed_drop = source_shock.get('speed_drop', 0)
        if isinstance(speed_drop, str):
            try:
                speed_drop = float(speed_drop)
            except:
                speed_drop = 0
        
        distance = prediction.get('distance', prediction.get('distance_km', 0))
        confidence = prediction.get('confidence', 0)
        
        message = f"""
📍 影響路段: {target_info}
🌊 衝擊波來源: {source_info}
⏰ 預計到達: {predicted_arrival.strftime('%H:%M')} ({minutes_to_arrival}分鐘後)
📊 衝擊強度: {shock_strength:.1f}%
🚗 速度影響: 下降 {speed_drop:.1f} km/h
📏 傳播距離: {distance:.1f} km
🎯 預測信心度: {confidence*100:.1f}%

💡 建議: {"立即改道避開該路段" if level in ['SEVERE', 'CRITICAL'] else "注意減速慢行，保持安全距離"}
        """.strip()
        
        warning = {
            'warning_id': warning_id,
            'level': level,
            'title': title,
            'message': message,
            'source_station': source_shock.get('station', prediction.get('source_station', '')),
            'target_station': prediction['target_station'],
            'shock_strength': shock_strength,
            'predicted_arrival': predicted_arrival.isoformat(),
            'confidence': confidence,
            'created_time': datetime.now().isoformat(),
            'raw_prediction': prediction
        }
        
        # 儲存到資料庫
        self._save_warning_to_db(warning)
        
        # 加入活躍預警
        self.active_warnings[warning_id] = warning
        
        self.logger.info(f"🚨 創建 {level_config['name']} 預警: {target_info} (ID: {warning_id})")
        
        return warning

    def _get_station_readable_name(self, station_code):
        """將站點代碼轉換為可讀名稱"""
        # 簡化的站點名稱映射
        name_mapping = {
            '01F0340': '高公局-五股',
            '01F0376': '林口(文化一路)',
            '01F0413': '林口(文化北路)',
            '01F0467': '桃園',
            '01F0492': '桃園南',
            '01F0511': '機場系統',
            '01F0532': '中壢服務區',
            '01F0557': '內壢',
            '01F0584': '中壢',
            '01F0633': '平鎮系統',
            '01F0664': '幼獅',
            '01F0681': '楊梅',
            '01F0699': '校前路',
            '01F0750': '湖口',
            '01F0880': '竹北',
            '01F0928': '新竹',
            '01F0956': '新竹科學園區',
            '01F0980': '新竹系統',
            '01F1045': '頭份',
            '03F0447': '樹林-土城',
            '03F0498': '三鶯',
            '03F0525': '鶯歌系統',
            '03F0559': '大溪',
            '03F0648': '龍潭',
            '03F0698': '高原',
            '03F0746': '關西服務區',
            '03F0783': '關西',
            '03F0846': '竹林',
            '03F0961': '寶山',
            '03F0996': '新竹系統',
            '03F1022': '茄苳'
        }
        
        # 提取站點基礎代碼
        base_code = station_code[:7] if len(station_code) >= 7 else station_code
        name = name_mapping.get(base_code, station_code)
        
        # 添加方向資訊
        if station_code.endswith('N'):
            direction = '北向'
        elif station_code.endswith('S'):
            direction = '南向'
        else:
            direction = ''
        
        return f"{name} {direction}".strip()

    def _save_warning_to_db(self, warning):
        """儲存預警到資料庫"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO warnings 
                (warning_id, level, title, message, source_station, target_station, 
                 shock_strength, predicted_arrival, confidence, created_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                warning['warning_id'],
                warning['level'],
                warning['title'],
                warning['message'],
                warning['source_station'],
                warning['target_station'],
                warning['shock_strength'],
                warning['predicted_arrival'],
                warning['confidence'],
                warning['created_time']
            ))
            conn.commit()

    def scan_new_predictions(self):
        """掃描新的預測結果"""
        pattern = os.path.join(self.prediction_dir, "shock_predictions_summary_*.csv")
        files = glob.glob(pattern)
        
        # 只處理最近30分鐘的檔案
        recent_files = []
        cutoff_time = datetime.now() - timedelta(minutes=30)
        
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
            return []
        
        # 載入最新的檔案
        recent_files.sort(reverse=True)
        latest_file = recent_files[0][1]
        
        try:
            df = pd.read_csv(latest_file, encoding='utf-8')
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"載入預測檔案失敗: {e}")
            return []

    def process_predictions(self, predictions):
        """處理預測結果並生成預警"""
        new_warnings = []
        
        for prediction in predictions:
            # 檢查是否已經存在相似的預警
            if self._is_duplicate_warning(prediction):
                continue
            
            # 創建預警
            warning = self.create_warning(prediction)
            new_warnings.append(warning)
            
            # 發送通知
            self._queue_notifications(warning)
        
        return new_warnings

    def _is_duplicate_warning(self, prediction):
        """檢查是否為重複預警"""
        target_station = prediction['target_station']
        
        # 檢查最近30分鐘內是否有相同站點的預警
        cutoff_time = datetime.now() - timedelta(minutes=30)
        
        for warning_id, warning in self.active_warnings.items():
            warning_time = datetime.fromisoformat(warning['created_time'])
            
            if (warning['target_station'] == target_station and 
                warning_time >= cutoff_time):
                return True
        
        return False

    def _queue_notifications(self, warning):
        """將通知加入佇列"""
        # 獲取訂閱該站點和等級的用戶
        subscribers = self._get_relevant_subscribers(warning)
        
        for subscriber in subscribers:
            # 檢查冷卻時間
            cooldown_key = f"{subscriber['user_id']}_{warning['target_station']}_{warning['level']}"
            
            if cooldown_key in self.notification_cooldown:
                last_sent = self.notification_cooldown[cooldown_key]
                if datetime.now() - last_sent < timedelta(minutes=self.cooldown_minutes):
                    continue
            
            # 加入通知佇列
            notification = {
                'warning': warning,
                'subscriber': subscriber,
                'cooldown_key': cooldown_key
            }
            
            self.notification_queue.append(notification)

    def _get_relevant_subscribers(self, warning):
        """獲取相關訂閱者"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM subscribers 
                WHERE is_active = 1
            ''')
            
            subscribers = []
            for row in cursor.fetchall():
                # 轉換為字典
                subscriber = {
                    'id': row[0],
                    'user_id': row[1],
                    'contact_method': row[2],
                    'contact_info': row[3],
                    'subscribed_levels': row[4].split(',') if row[4] else [],
                    'subscribed_stations': row[5].split(',') if row[5] else [],
                    'created_time': row[6],
                    'is_active': row[7]
                }
                
                # 檢查是否符合訂閱條件
                if (warning['level'] in subscriber['subscribed_levels'] and
                    (not subscriber['subscribed_stations'] or 
                     warning['target_station'] in subscriber['subscribed_stations'])):
                    subscribers.append(subscriber)
            
            return subscribers

    def send_notifications(self):
        """發送通知"""
        while self.notification_queue:
            notification = self.notification_queue.popleft()
            
            try:
                self._send_single_notification(notification)
                
                # 更新冷卻時間
                self.notification_cooldown[notification['cooldown_key']] = datetime.now()
                
            except Exception as e:
                self.logger.error(f"通知發送失敗: {e}")
                
                # 記錄失敗
                self._log_notification_failure(notification, str(e))

    def _send_single_notification(self, notification):
        """發送單個通知"""
        warning = notification['warning']
        subscriber = notification['subscriber']
        contact_method = subscriber['contact_method']
        
        if contact_method == 'email' and self.config['email']['enabled']:
            self._send_email_notification(warning, subscriber)
        elif contact_method == 'line' and self.config['line']['enabled']:
            self._send_line_notification(warning, subscriber)
        elif contact_method == 'slack' and self.config['slack']['enabled']:
            self._send_slack_notification(warning, subscriber)
        else:
            self.logger.warning(f"不支援的通知方式: {contact_method}")

    def _send_email_notification(self, warning, subscriber):
        """發送Email通知"""
        config = self.config['email']
        
        msg = MIMEMultipart()
        msg['From'] = config['from_address']
        msg['To'] = subscriber['contact_info']
        msg['Subject'] = warning['title']
        
        # HTML內容
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: {self.warning_levels[warning['level']]['color']}; color: white; padding: 10px; border-radius: 5px;">
                <h2>{warning['title']}</h2>
            </div>
            <div style="padding: 20px;">
                <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{warning['message']}</pre>
            </div>
            <hr>
            <p style="color: #666; font-size: 12px;">
                此通知由高速公路衝擊波預警系統自動發送<br>
                發送時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # 發送郵件
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['username'], config['password'])
            server.send_message(msg)
        
        self.logger.info(f"📧 Email通知已發送: {subscriber['contact_info']}")

    def _send_line_notification(self, warning, subscriber):
        """發送LINE通知"""
        config = self.config['line']
        
        headers = {
            'Authorization': f'Bearer {config["access_token"]}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        message = f"{warning['title']}\n\n{warning['message']}"
        
        data = {'message': message}
        
        response = requests.post(
            'https://notify-api.line.me/api/notify',
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            self.logger.info(f"📱 LINE通知已發送: {subscriber['user_id']}")
        else:
            raise Exception(f"LINE通知失敗: {response.status_code}")

    def _send_slack_notification(self, warning, subscriber):
        """發送Slack通知"""
        config = self.config['slack']
        
        color_map = {
            'INFO': '#17a2b8',
            'MINOR': '#ffc107',
            'MODERATE': '#fd7e14',
            'SEVERE': '#dc3545',
            'CRITICAL': '#721c24'
        }
        
        payload = {
            "attachments": [
                {
                    "color": color_map.get(warning['level'], '#17a2b8'),
                    "title": warning['title'],
                    "text": warning['message'],
                    "footer": "高速公路衝擊波預警系統",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        response = requests.post(config['webhook_url'], json=payload)
        
        if response.status_code == 200:
            self.logger.info(f"💬 Slack通知已發送: {subscriber['user_id']}")
        else:
            raise Exception(f"Slack通知失敗: {response.status_code}")

    def _log_notification_failure(self, notification, error_message):
        """記錄通知失敗"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications 
                (warning_id, user_id, contact_method, status, sent_time, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                notification['warning']['warning_id'],
                notification['subscriber']['user_id'],
                notification['subscriber']['contact_method'],
                'FAILED',
                datetime.now().isoformat(),
                error_message
            ))
            conn.commit()

    def run_single_check_cycle(self):
        """執行單次檢查循環"""
        try:
            self.logger.info("🔍 開始預警檢查...")
            
            # 1. 掃描新的預測結果
            predictions = self.scan_new_predictions()
            
            if not predictions:
                self.logger.info("ℹ️ 無新的預測結果")
                return
            
            # 2. 處理預測並生成預警
            new_warnings = self.process_predictions(predictions)
            
            # 3. 發送通知
            if self.notification_queue:
                self.send_notifications()
            
            # 4. 清理過期預警
            self._cleanup_expired_warnings()
            
            self.logger.info(f"✅ 檢查完成: 新增 {len(new_warnings)} 個預警")
            self.last_check_time = datetime.now()
            
        except Exception as e:
            self.logger.error(f"❌ 預警檢查失敗: {e}")

    def _cleanup_expired_warnings(self):
        """清理過期預警"""
        if not self.config['monitoring']['auto_cleanup']:
            return
        
        max_age = self.config['monitoring']['max_warning_age']
        cutoff_time = datetime.now() - timedelta(minutes=max_age)
        
        expired_warnings = []
        for warning_id, warning in list(self.active_warnings.items()):
            warning_time = datetime.fromisoformat(warning['created_time'])
            
            if warning_time < cutoff_time:
                expired_warnings.append(warning_id)
                del self.active_warnings[warning_id]
        
        if expired_warnings:
            self.logger.info(f"🧹 清理過期預警: {len(expired_warnings)} 個")

    def start_monitoring(self):
        """啟動預警監控"""
        self.logger.info("🚀 啟動預警監控模式")
        self.logger.info(f"⏱️ 檢查間隔: {self.config['monitoring']['check_interval']} 秒")
        
        self.is_running = True
        
        try:
            while self.is_running:
                self.run_single_check_cycle()
                
                # 等待下次檢查
                if self.is_running:
                    time.sleep(self.config['monitoring']['check_interval'])
                    
        except KeyboardInterrupt:
            self.logger.info("收到中斷信號")
        finally:
            self.logger.info("預警監控已停止")
            self.is_running = False

    def add_subscriber(self, user_id, contact_method, contact_info, levels=None, stations=None):
        """新增訂閱者"""
        if levels is None:
            levels = ['MODERATE', 'SEVERE', 'CRITICAL']
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO subscribers 
                (user_id, contact_method, contact_info, subscribed_levels, subscribed_stations, created_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                contact_method,
                contact_info,
                ','.join(levels),
                ','.join(stations) if stations else '',
                datetime.now().isoformat()
            ))
            conn.commit()
        
        self.logger.info(f"➕ 新增訂閱者: {user_id} ({contact_method})")

    def get_active_warnings(self, level_filter=None):
        """獲取活躍預警"""
        warnings = list(self.active_warnings.values())
        
        if level_filter:
            warnings = [w for w in warnings if w['level'] == level_filter]
        
        # 按創建時間排序
        warnings.sort(key=lambda x: x['created_time'], reverse=True)
        
        return warnings

    def stop(self):
        """停止預警系統"""
        self.is_running = False
        self.logger.info("🛑 預警系統停止指令已發出")


def main():
    """主函數"""
    base_dir = "/Users/weiqihong/Desktop/碩士班/碩一下/highway-traffic/data"
    config_file = os.path.join(base_dir, "warning_config.json")
    
    # 建立預警系統
    warning_system = ShockWarningSystem(base_dir, config_file)
    
    print("=" * 60)
    print("🚨 衝擊波預警系統")
    print("=" * 60)
    print("\n選擇運行模式:")
    print("1. 測試模式 (單次檢查)")
    print("2. 持續監控模式")
    print("3. 查看活躍預警")
    print("4. 管理訂閱者")
    
    try:
        choice = input("\n請選擇 (1/2/3/4): ").strip()
        
        if choice == "1":
            print("\n🧪 執行測試檢查...")
            warning_system.run_single_check_cycle()
            
            active_warnings = warning_system.get_active_warnings()
            if active_warnings:
                print(f"✅ 測試成功! 發現 {len(active_warnings)} 個活躍預警")
                for warning in active_warnings[:3]:
                    print(f"  - {warning['level']}: {warning['target_station']}")
            else:
                print("ℹ️ 目前無活躍預警")
        
        elif choice == "2":
            print("\n🚀 啟動持續監控模式...")
            print("按 Ctrl+C 可以停止")
            warning_system.start_monitoring()
        
        elif choice == "3":
            print("\n📊 載入活躍預警...")
            active_warnings = warning_system.get_active_warnings()
            
            if active_warnings:
                print(f"✅ 找到 {len(active_warnings)} 個活躍預警:")
                for warning in active_warnings:
                    print(f"\n🚨 {warning['level']} - {warning['title']}")
                    print(f"   站點: {warning['target_station']}")
                    print(f"   時間: {warning['created_time']}")
            else:
                print("ℹ️ 目前無活躍預警")
        
        elif choice == "4":
            print("\n👥 管理訂閱者...")
            user_id = input("用戶ID: ")
            contact_method = input("聯絡方式 (email/line/slack): ")
            contact_info = input("聯絡資訊: ")
            
            warning_system.add_subscriber(user_id, contact_method, contact_info)
            print("✅ 訂閱者新增成功!")
        
        else:
            print("無效選擇")
    
    except KeyboardInterrupt:
        print("\n👋 系統已停止")
    except Exception as e:
        print(f"\n❌ 系統錯誤: {e}")


if __name__ == "__main__":
    main()