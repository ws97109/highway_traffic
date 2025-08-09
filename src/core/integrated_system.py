#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import threading
import signal
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import argparse

# 導入所有系統模組
try:
    from ..data.tisc_api_tester import ProductionRealtimeSystem
    from ..prediction.realtime_shock_predictor import RealtimeShockPredictor
    from ..systems.shock_warning_system import ShockWarningSystem
    from ..prediction.location_based_predictor import LocationBasedShockPredictor
    
    # 確保所有依賴模組也能正確導入
    from .. import detection
    from .. import prediction
    
except ImportError as e:
    print(f"❌ 模組導入失敗: {e}")
    print("請確保以下檔案都在相同目錄下：")
    required_files = [
        "data/tisc_api_tester.py",
        "prediction/realtime_shock_predictor.py", 
        "systems/shock_warning_system.py",
        "prediction/location_based_predictor.py",
        "detection/final_optimized_detector.py",
        "prediction/propagation_system.py"
    ]
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - 檔案缺失")
    sys.exit(1)

class IntegratedShockPredictionSystem:
    """
    整合衝擊波預測系統
    
    統一管理所有子系統：
    1. 即時資料收集系統
    2. 衝擊波預測系統  
    3. 預警通知系統
    4. 位置服務系統
    """
    
    def __init__(self, config_dir: str = None):
        """初始化整合系統"""
        
        # 設定基本路徑
        self.base_dir = "../data"
        self.config_dir = config_dir or os.path.join(self.base_dir, "config")
        
        # 建立目錄
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 設定日誌
        self._setup_logging()
        
        # 載入配置
        self.config = self._load_system_config()
        
        # 系統狀態
        self.is_running = False
        self.subsystems = {}
        self.threads = {}
        self.start_time = None
        
        # 健康檢查
        self.health_check_interval = 60  # 秒
        self.last_health_check = None
        
        # 系統組件初始化狀態
        self.components_status = {
            'data_collector': {'status': 'stopped', 'last_update': None, 'error_count': 0},
            'shock_predictor': {'status': 'stopped', 'last_update': None, 'error_count': 0},
            'warning_system': {'status': 'stopped', 'last_update': None, 'error_count': 0},
            'location_service': {'status': 'stopped', 'last_update': None, 'error_count': 0}
        }
        
        # 註冊信號處理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("🚀 整合衝擊波預測系統初始化完成")
        self.logger.info(f"📂 基礎目錄: {self.base_dir}")
        self.logger.info(f"⚙️ 配置目錄: {self.config_dir}")

    def _setup_logging(self):
        """設定系統日誌"""
        log_dir = os.path.join(self.base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"integrated_system_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('IntegratedSystem')

    def _load_system_config(self):
        """載入系統配置"""
        default_config = {
            'system': {
                'auto_start_all': True,
                'health_check_enabled': True,
                'auto_restart_on_failure': True,
                'max_restart_attempts': 3
            },
            'google_api_key': '',
            'components': {
                'data_collector': {'enabled': True, 'auto_start': True},
                'shock_predictor': {'enabled': True, 'auto_start': True},
                'warning_system': {'enabled': True, 'auto_start': True},
                'location_service': {'enabled': True, 'auto_start': True}
            }
        }
        
        config_file = os.path.join(self.config_dir, "system_config.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 深度合併配置
                    self._deep_merge_config(default_config, user_config)
            except Exception as e:
                self.logger.warning(f"載入配置失敗，使用預設配置: {e}")
        else:
            # 創建預設配置檔案
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已創建預設配置檔案: {config_file}")
        
        return default_config

    def _deep_merge_config(self, default, user):
        """深度合併配置"""
        for key, value in user.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._deep_merge_config(default[key], value)
            else:
                default[key] = value

    def _load_location_config(self):
        """載入位置服務配置"""
        location_config_file = os.path.join(self.config_dir, "location_config.json")
        default_location_config = {
            'max_distance_km': 20,
            'location_cache_minutes': 30,
            'prediction_radius_km': 50,
            'route_analysis': True,
            'traffic_consideration': True
        }
        
        if os.path.exists(location_config_file):
            try:
                with open(location_config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_location_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"載入位置配置失敗，使用預設配置: {e}")
        
        return default_location_config

    def _signal_handler(self, signum, frame):
        """信號處理器"""
        self.logger.info(f"收到信號 {signum}，準備優雅關閉...")
        self.stop_all_systems()

    def initialize_subsystems(self):
        """初始化所有子系統"""
        try:
            self.logger.info("🔧 初始化子系統...")
            
            # 1. 即時資料收集系統
            if self.config['components']['data_collector']['enabled']:
                try:
                    self.subsystems['data_collector'] = ProductionRealtimeSystem(self.base_dir)
                    self.components_status['data_collector']['status'] = 'initialized'
                    self.logger.info("✅ 資料收集系統初始化成功")
                except Exception as e:
                    self.logger.error(f"❌ 資料收集系統初始化失敗: {e}")
                    self.components_status['data_collector']['status'] = 'error'
            
            # 2. 衝擊波預測系統
            if self.config['components']['shock_predictor']['enabled']:
                try:
                    self.subsystems['shock_predictor'] = RealtimeShockPredictor(self.base_dir)
                    self.components_status['shock_predictor']['status'] = 'initialized'
                    self.logger.info("✅ 衝擊波預測系統初始化成功")
                except Exception as e:
                    self.logger.error(f"❌ 衝擊波預測系統初始化失敗: {e}")
                    self.components_status['shock_predictor']['status'] = 'error'
            
            # 3. 預警系統
            if self.config['components']['warning_system']['enabled']:
                try:
                    warning_config = os.path.join(self.config_dir, "warning_config.json")
                    self.subsystems['warning_system'] = ShockWarningSystem(self.base_dir, warning_config)
                    self.components_status['warning_system']['status'] = 'initialized'
                    self.logger.info("✅ 預警系統初始化成功")
                except Exception as e:
                    self.logger.error(f"❌ 預警系統初始化失敗: {e}")
                    self.components_status['warning_system']['status'] = 'error'
            
            # 4. 位置服務系統
            if self.config['components']['location_service']['enabled']:
                try:
                    google_api_key = self.config.get('google_api_key', '')
                    if google_api_key:
                        location_config = self._load_location_config()
                        self.subsystems['location_service'] = LocationBasedShockPredictor(
                            self.base_dir, google_api_key, location_config
                        )
                        self.components_status['location_service']['status'] = 'initialized'
                        self.logger.info("✅ 位置服務系統初始化成功")
                    else:
                        # 即使沒有API Key也要初始化基本功能
                        self.logger.warning("⚠️ Google API Key未設定，位置服務將受限")
                        location_config = self._load_location_config()
                        self.subsystems['location_service'] = LocationBasedShockPredictor(
                            self.base_dir, '', location_config
                        )
                        self.components_status['location_service']['status'] = 'warning'
                except Exception as e:
                    self.logger.error(f"❌ 位置服務系統初始化失敗: {e}")
                    self.components_status['location_service']['status'] = 'error'
            
            initialized_count = sum(1 for status in self.components_status.values() 
                                  if status['status'] in ['initialized', 'warning'])
            
            self.logger.info(f"🎯 子系統初始化完成: {initialized_count}/{len(self.components_status)} 個系統就緒")
            
            return initialized_count > 0
            
        except Exception as e:
            self.logger.error(f"❌ 子系統初始化失敗: {e}")
            return False

    def start_subsystem(self, system_name: str):
        """啟動指定子系統"""
        if system_name not in self.subsystems:
            self.logger.error(f"❌ 子系統不存在: {system_name}")
            return False
        
        try:
            self.logger.info(f"🚀 啟動 {system_name}...")
            
            if system_name == 'data_collector':
                # 資料收集系統在獨立執行緒中運行
                thread = threading.Thread(
                    target=self.subsystems[system_name].start_continuous_monitoring,
                    name=f"Thread-{system_name}",
                    daemon=True
                )
                thread.start()
                self.threads[system_name] = thread
                
            elif system_name == 'shock_predictor':
                # 衝擊波預測系統在獨立執行緒中運行
                thread = threading.Thread(
                    target=self.subsystems[system_name].start_continuous_prediction,
                    name=f"Thread-{system_name}",
                    daemon=True
                )
                thread.start()
                self.threads[system_name] = thread
                
            elif system_name == 'warning_system':
                # 預警系統在獨立執行緒中運行
                thread = threading.Thread(
                    target=self.subsystems[system_name].start_monitoring,
                    name=f"Thread-{system_name}",
                    daemon=True
                )
                thread.start()
                self.threads[system_name] = thread
                
            elif system_name == 'location_service':
                # 位置服務系統通常是按需調用，不需要持續運行
                self.components_status[system_name]['status'] = 'running'
                self.components_status[system_name]['last_update'] = datetime.now()
                self.logger.info(f"✅ {system_name} 已就緒（按需服務）")
                return True
            
            # 等待系統啟動
            time.sleep(2)
            
            # 檢查執行緒狀態
            if system_name in self.threads and self.threads[system_name].is_alive():
                self.components_status[system_name]['status'] = 'running'
                self.components_status[system_name]['last_update'] = datetime.now()
                self.logger.info(f"✅ {system_name} 啟動成功")
                return True
            else:
                self.logger.error(f"❌ {system_name} 啟動失敗")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 啟動 {system_name} 時發生錯誤: {e}")
            self.components_status[system_name]['status'] = 'error'
            self.components_status[system_name]['error_count'] += 1
            return False

    def stop_subsystem(self, system_name: str):
        """停止指定子系統"""
        try:
            if system_name in self.subsystems:
                # 調用子系統的停止方法
                if hasattr(self.subsystems[system_name], 'stop'):
                    self.subsystems[system_name].stop()
                elif hasattr(self.subsystems[system_name], 'is_running'):
                    self.subsystems[system_name].is_running = False
            
            # 等待執行緒結束
            if system_name in self.threads:
                thread = self.threads[system_name]
                if thread.is_alive():
                    thread.join(timeout=10)  # 等待最多10秒
                del self.threads[system_name]
            
            self.components_status[system_name]['status'] = 'stopped'
            self.logger.info(f"🛑 {system_name} 已停止")
            
        except Exception as e:
            self.logger.error(f"❌ 停止 {system_name} 時發生錯誤: {e}")

    def start_all_systems(self):
        """啟動所有系統"""
        self.logger.info("🚀 啟動所有子系統...")
        self.is_running = True
        self.start_time = datetime.now()
        
        # 按順序啟動系統
        startup_order = ['data_collector', 'shock_predictor', 'warning_system', 'location_service']
        
        for system_name in startup_order:
            if (self.config['components'][system_name]['enabled'] and 
                self.config['components'][system_name]['auto_start']):
                
                success = self.start_subsystem(system_name)
                if not success:
                    self.logger.warning(f"⚠️ {system_name} 啟動失敗，但繼續啟動其他系統")
                
                # 系統間啟動延遲
                time.sleep(3)
        
        # 啟動健康檢查
        if self.config['system']['health_check_enabled']:
            health_thread = threading.Thread(
                target=self._health_check_loop,
                name="Thread-HealthCheck",
                daemon=True
            )
            health_thread.start()
            self.threads['health_check'] = health_thread
        
        running_count = sum(1 for status in self.components_status.values() 
                           if status['status'] == 'running')
        
        self.logger.info(f"🎯 系統啟動完成: {running_count} 個系統運行中")

    def stop_all_systems(self):
        """停止所有系統"""
        self.logger.info("🛑 停止所有子系統...")
        self.is_running = False
        
        # 按相反順序停止系統
        shutdown_order = ['location_service', 'warning_system', 'shock_predictor', 'data_collector']
        
        for system_name in shutdown_order:
            if system_name in self.subsystems:
                self.stop_subsystem(system_name)
                time.sleep(1)
        
        # 停止健康檢查
        if 'health_check' in self.threads:
            del self.threads['health_check']
        
        self.logger.info("✅ 所有系統已停止")

    def _health_check_loop(self):
        """健康檢查循環"""
        while self.is_running:
            try:
                self._perform_health_check()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"❌ 健康檢查失敗: {e}")
                time.sleep(30)  # 錯誤時延長檢查間隔

    def _perform_health_check(self):
        """執行健康檢查"""
        self.last_health_check = datetime.now()
        
        for system_name, status in self.components_status.items():
            if status['status'] == 'running':
                # 檢查執行緒是否還活著
                if system_name in self.threads:
                    thread = self.threads[system_name]
                    if not thread.is_alive():
                        self.logger.warning(f"⚠️ {system_name} 執行緒已終止")
                        status['status'] = 'error'
                        status['error_count'] += 1
                        
                        # 自動重啟（如果啟用）
                        if (self.config['system']['auto_restart_on_failure'] and 
                            status['error_count'] < self.config['system']['max_restart_attempts']):
                            self.logger.info(f"🔄 嘗試重啟 {system_name}")
                            self.start_subsystem(system_name)
                
                # 檢查資料更新時間
                if status['last_update']:
                    time_since_update = datetime.now() - status['last_update']
                    if time_since_update > timedelta(minutes=10):
                        self.logger.warning(f"⚠️ {system_name} 長時間無更新")

    def get_system_status(self):
        """獲取系統狀態"""
        status = {
            'overall_status': 'running' if self.is_running else 'stopped',
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_minutes': int((datetime.now() - self.start_time).total_seconds() / 60) if self.start_time else 0,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'components': self.components_status.copy(),
            'system_resources': self._get_system_resources()
        }
        
        # 轉換時間格式
        for component in status['components'].values():
            if component['last_update']:
                component['last_update'] = component['last_update'].isoformat()
        
        return status

    def _get_system_resources(self):
        """獲取系統資源使用情況"""
        try:
            process = psutil.Process()
            
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'memory_percent': process.memory_percent(),
                'threads_count': process.num_threads(),
                'files_open': process.num_fds() if hasattr(process, 'num_fds') else 0
            }
        except:
            return {'error': 'Unable to get system resources'}

    def run_interactive_mode(self):
        """交互模式運行"""
        print("=" * 70)
        print("🚀 整合衝擊波預測系統 - 交互模式")
        print("=" * 70)
        
        while True:
            print("\n選擇操作:")
            print("1. 啟動所有系統")
            print("2. 停止所有系統") 
            print("3. 查看系統狀態")
            print("4. 重啟指定系統")
            print("5. 測試位置預測")
            print("6. 查看最新預警")
            print("7. 系統配置")
            print("0. 退出")
            
            try:
                choice = input("\n請選擇 (0-7): ").strip()
                
                if choice == "1":
                    if not self.is_running:
                        if self.initialize_subsystems():
                            self.start_all_systems()
                        else:
                            print("❌ 子系統初始化失敗")
                    else:
                        print("ℹ️ 系統已在運行中")
                
                elif choice == "2":
                    if self.is_running:
                        self.stop_all_systems()
                    else:
                        print("ℹ️ 系統未運行")
                
                elif choice == "3":
                    status = self.get_system_status()
                    self._print_system_status(status)
                
                elif choice == "4":
                    self._interactive_restart_system()
                
                elif choice == "5":
                    self._interactive_location_test()
                
                elif choice == "6":
                    self._show_latest_warnings()
                
                elif choice == "7":
                    self._interactive_config()
                
                elif choice == "0":
                    if self.is_running:
                        print("正在停止系統...")
                        self.stop_all_systems()
                    print("👋 再見！")
                    break
                
                else:
                    print("❌ 無效選擇")
                    
            except KeyboardInterrupt:
                print("\n\n正在停止系統...")
                if self.is_running:
                    self.stop_all_systems()
                break
            except Exception as e:
                print(f"❌ 操作失敗: {e}")

    def _print_system_status(self, status):
        """列印系統狀態"""
        print(f"\n📊 系統狀態報告")
        print(f"={'='*50}")
        print(f"整體狀態: {status['overall_status']}")
        if status['start_time']:
            print(f"啟動時間: {status['start_time']}")
            print(f"運行時間: {status['uptime_minutes']} 分鐘")
        
        print(f"\n🔧 子系統狀態:")
        for name, info in status['components'].items():
            status_emoji = {
                'running': '✅',
                'stopped': '⏹️',
                'error': '❌',
                'initialized': '🔧',
                'warning': '⚠️'
            }
            emoji = status_emoji.get(info['status'], '❓')
            print(f"  {emoji} {name}: {info['status']}")
            if info['error_count'] > 0:
                print(f"    錯誤次數: {info['error_count']}")
        
        print(f"\n💻 系統資源:")
        resources = status['system_resources']
        if 'error' not in resources:
            print(f"  CPU: {resources['cpu_percent']:.1f}%")
            print(f"  記憶體: {resources['memory_mb']:.1f} MB ({resources['memory_percent']:.1f}%)")
            print(f"  執行緒: {resources['threads_count']}")

    def _interactive_restart_system(self):
        """交互式重啟系統"""
        print("\n可重啟的系統:")
        systems = list(self.components_status.keys())
        for i, name in enumerate(systems, 1):
            status = self.components_status[name]['status']
            print(f"  {i}. {name} ({status})")
        
        try:
            choice = int(input("選擇要重啟的系統 (數字): ")) - 1
            if 0 <= choice < len(systems):
                system_name = systems[choice]
                print(f"重啟 {system_name}...")
                self.stop_subsystem(system_name)
                time.sleep(2)
                self.start_subsystem(system_name)
            else:
                print("❌ 無效選擇")
        except ValueError:
            print("❌ 請輸入有效數字")

    def _interactive_location_test(self):
        """交互式位置測試"""
        if 'location_service' not in self.subsystems:
            print("❌ 位置服務未啟用")
            return
        
        print("\n📍 位置預測測試")
        try:
            lat = float(input("請輸入緯度: "))
            lng = float(input("請輸入經度: "))
            
            result = self.subsystems['location_service'].predict_for_coordinates(lat, lng)
            
            if result['success']:
                print(f"\n✅ 預測成功!")
                print(f"📍 位置: {result['user_location']['address']}")
                print(f"🎯 風險等級: {result['risk_assessment']['overall_risk']}")
                print(f"📊 風險分數: {result['risk_assessment']['risk_score']}")
                print(f"🚨 相關預測: {len(result['relevant_predictions'])} 個")
                
                if result['recommendations']:
                    print(f"\n💡 建議:")
                    for rec in result['recommendations'][:3]:
                        print(f"  - {rec}")
            else:
                print(f"❌ 預測失敗: {result['error']}")
                
        except ValueError:
            print("❌ 請輸入有效的數字")
        except Exception as e:
            print(f"❌ 測試失敗: {e}")

    def _show_latest_warnings(self):
        """顯示最新預警"""
        if 'warning_system' not in self.subsystems:
            print("❌ 預警系統未啟用")
            return
        
        try:
            warnings = self.subsystems['warning_system'].get_active_warnings()
            
            if warnings:
                print(f"\n🚨 活躍預警 ({len(warnings)} 個):")
                for i, warning in enumerate(warnings[:5], 1):
                    print(f"\n{i}. {warning['level']} - {warning['title']}")
                    print(f"   站點: {warning['target_station']}")
                    print(f"   時間: {warning['created_time']}")
                    print(f"   信心度: {warning['confidence']*100:.1f}%")
            else:
                print("ℹ️ 目前無活躍預警")
                
        except Exception as e:
            print(f"❌ 獲取預警失敗: {e}")

    def _interactive_config(self):
        """交互式配置"""
        print("\n⚙️ 系統配置選項:")
        print("1. 顯示當前配置")
        print("2. 設定Google API Key")
        print("3. 配置通知設定")
        print("4. 返回主選單")
        
        try:
            choice = input("請選擇 (1-4): ").strip()
            
            if choice == "1":
                print(json.dumps(self.config, ensure_ascii=False, indent=2))
            
            elif choice == "2":
                api_key = input("請輸入Google Maps API Key: ").strip()
                if api_key:
                    self.config['google_api_key'] = api_key
                    self._save_config()
                    print("✅ API Key已更新")
            
            elif choice == "3":
                print("通知配置功能開發中...")
            
            elif choice == "4":
                return
            
        except Exception as e:
            print(f"❌ 配置操作失敗: {e}")

    def _save_config(self):
        """儲存配置"""
        config_file = os.path.join(self.config_dir, "system_config.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='整合衝擊波預測系統')
    parser.add_argument('--config-dir', help='配置檔案目錄')
    parser.add_argument('--mode', choices=['interactive', 'daemon'], 
                       default='interactive', help='運行模式')
    parser.add_argument('--auto-start', action='store_true', 
                       help='自動啟動所有系統')
    
    args = parser.parse_args()
    
    try:
        # 建立整合系統
        system = IntegratedShockPredictionSystem(args.config_dir)
        
        if args.mode == 'daemon':
            # 守護程序模式
            if system.initialize_subsystems():
                system.start_all_systems()
                
                # 保持運行
                try:
                    while system.is_running:
                        time.sleep(60)
                except KeyboardInterrupt:
                    pass
                finally:
                    system.stop_all_systems()
            else:
                print("❌ 系統初始化失敗")
                sys.exit(1)
        
        else:
            # 交互模式
            if args.auto_start:
                if system.initialize_subsystems():
                    system.start_all_systems()
            
            system.run_interactive_mode()
    
    except KeyboardInterrupt:
        print("\n👋 系統已停止")
    except Exception as e:
        print(f"❌ 系統錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()