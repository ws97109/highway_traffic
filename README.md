# 交通衝擊波檢測與預測系統
Highway Traffic Shock Wave Detection and Prediction System

## 📋 專案概述

本專案是一個完整的交通衝擊波檢測與預測系統，能夠即時分析高速公路交通資料，檢測衝擊波並進行傳播預測，提供預警服務。

## 🏗️ 系統架構

### 模組化結構

```
src/
├── __init__.py
├── core/                    # 核心系統
│   ├── __init__.py
│   └── integrated_system.py
├── detection/               # 衝擊波檢測
│   ├── __init__.py
│   ├── final_optimized_detector.py
│   └── trafficWave.py
├── prediction/              # 衝擊波預測
│   ├── __init__.py
│   ├── location_based_predictor.py
│   ├── propagation_system.py
│   └── realtime_shock_predictor.py
├── data/                    # 資料處理
│   ├── __init__.py
│   ├── dataLoad.py
│   └── tisc_api_tester.py
├── utils/                   # 工具函數
│   ├── __init__.py
│   └── config_loader.py
└── systems/                 # 系統功能
    ├── __init__.py
    └── shock_warning_system.py
```

### 主要功能模組

- **🔍 detection**: 交通衝擊波檢測演算法
- **📈 prediction**: 衝擊波傳播預測與位置預測
- **📊 data**: 資料載入、處理與 API 介面
- **⚙️ utils**: 配置管理與工具函數
- **🚨 systems**: 警告系統與通知服務
- **🎯 core**: 系統整合與核心邏輯

## 🚀 快速開始

### 1. 環境設定

```bash
# 複製環境變數範例檔案
cp .env.example .env

# 編輯 .env 檔案，填入您的 API 憑證
# - TDX API 憑證
# - 電子郵件設定
# - Google Maps API 金鑰
```

### 2. 測試系統

```bash
# 測試程式碼結構
python test_structure.py

# 測試配置載入
python src/utils/config_loader.py
```

### 3. 基本使用

```python
# 匯入主要模組
from src.detection.final_optimized_detector import FinalOptimizedShockDetector
from src.prediction.realtime_shock_predictor import RealtimeShockPredictor
from src.core.integrated_system import IntegratedShockPredictionSystem

# 創建檢測器
detector = FinalOptimizedShockDetector()

# 創建預測器
predictor = RealtimeShockPredictor()

# 創建整合系統
system = IntegratedShockPredictionSystem()
```

## 🔧 配置管理

### 環境變數

系統使用環境變數來保護敏感資訊：

```bash
# TDX API 憑證
TDX_CLIENT_ID=your_client_id
TDX_CLIENT_SECRET=your_client_secret

# 電子郵件設定
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM_ADDRESS=your_email@gmail.com

# Google Maps API
GOOGLE_MAPS_API_KEY=your_api_key
```

### 配置載入

```python
from src.utils.config_loader import load_config_with_env

# 載入配置（自動替換環境變數）
config = load_config_with_env('data/config/system_config.json')

# 獲取配置值
email_config = config['warning_config.json']['email']
api_key = config['location_config.json']['google_maps']['api_key']
```

## 📊 核心功能

### 1. 衝擊波檢測
- 多層級檢測演算法
- 適應性閾值調整
- 即時檢測能力

### 2. 傳播預測
- 基於歷史資料的傳播模型
- 路網拓撲分析
- 到達時間預測

### 3. 位置服務
- Google Maps 整合
- 地理位置風險評估
- 路徑分析

### 4. 警告系統
- 電子郵件通知
- 風險等級分類
- 智慧降噪機制

## 🗂️ 資料結構

### 輸入資料
- 交通流量資料 (flow)
- 車速資料 (median_speed)
- 旅行時間資料 (avg_travel_time)
- 站點位置資訊

### 輸出資料
- 衝擊波事件清單
- 傳播預測結果
- 風險評估報告
- 警告通知紀錄

## 📈 系統監控

### 日誌管理
- 分模組日誌記錄
- 可設定日誌等級
- 自動備份機制

### 效能監控
- 處理時間統計
- 記憶體使用監控
- API 呼叫追蹤

## 🔒 安全性

- 敏感資訊環境變數化
- API 憑證加密存儲
- 存取權限控制
- 資料備份策略

## 🧪 測試

```bash
# 執行完整測試
python test_structure.py

# 測試個別模組
python -c "from src.detection import *; print('檢測模組測試通過')"
python -c "from src.prediction import *; print('預測模組測試通過')"
```

## 📝 開發指南

### 添加新模組
1. 在對應目錄創建新檔案
2. 更新 `__init__.py` 檔案
3. 添加必要的測試
4. 更新文件

### 修改配置
1. 更新 `system_config.json`
2. 添加環境變數到 `.env.example`
3. 更新配置載入邏輯

## 🤝 貢獻

歡迎提交問題和改進建議！

## 📄 授權

本專案採用 MIT 授權條款。

## 👨‍💻 作者

- **timwei0801** - *初始開發* - [GitHub](https://github.com/timwei0801)

---

更多詳細資訊請參考 `CONFIG_SETUP.md` 檔案。
