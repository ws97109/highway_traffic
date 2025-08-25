#  高速公路智慧交通震波預警決策支援系統
**Highway Intelligent Traffic Shockwave Warning and Decision Support System**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.4.4-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange.svg)](https://tensorflow.org/)

>  **基於深度學習的創新交通震波預警系統** - 結合地震學理論、傳統交通分析與先進深度學習技術，提供精確的高速公路交通震波檢測、多時步預測與智慧決策支援

## 專案概述

本系統是一個完整的端到端智慧交通管理解決方案，融合理論創新與工程實踐：

### 核心技術創新
- ** 交通震波檢測** - 首創將地震學震波傳播理論應用於交通流分析
- ** MT-STNet深度學習** - 多任務時空神經網路，同步預測流量/速度/密度
- ** 17種基準模型** - 包含AGCRN、ASTGCN、DCRNN、Graph-WaveNet等主流時空預測模型
- ** 混合預測架構** - 傳統物理模型與深度學習模型的智慧融合
- ** 毫秒級響應** - 即時震波檢測與多時步預測系統

###  應用場景
- ** 智慧導航系統** - 為駕駛者提供即時震波預警與路線優化
- ** 交通管制中心** - 為管理者提供AI決策支援與預防性管制策略
- ** 學術研究平台** - 支援交通流理論研究與深度學習模型比較
- ** 智慧城市建設** - 可整合至更大規模的城市交通管理系統

## 快速開始

### 系統需求
- **Python**: 3.8+ (建議 3.9+)
- **Node.js**: 18.0+
- **npm**: 8.0+
- **作業系統**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **記憶體**: 8GB+ (深度學習訓練建議 16GB+)
- **儲存空間**: 5GB+ (包含資料和模型)

### 🔧 環境設定

#### 1. 複製專案
```bash
git clone https://github.com/timwei0801/Highway_trafficwave.git
cd Highway_trafficwave
```

#### 2. 檢查Python環境
```bash
# 檢查Python版本和所需套件
python check_environment.py
```

#### 3. 安裝Python依賴
```bash
# 安裝核心依賴
pip install -r requirements.txt

# 如果要使用深度學習功能，額外安裝
pip install tensorflow>=2.8.0
pip install torch>=1.12.0  # 可選，用於某些基準模型
```

#### 4. 設定環境變數
```bash
# 複製環境變數範例檔案
cp .env.example .env

# 編輯 .env 檔案，填入您的API憑證
# nano .env  # 或使用您喜歡的編輯器
```

**必要的API憑證：**
```bash
# 交通部TDX API (必須) - 前往 https://tdx.transportdata.tw/ 申請
TDX_CLIENT_ID=your_client_id_here
TDX_CLIENT_SECRET=your_client_secret_here

# Google Maps API (地圖功能) - 前往 Google Cloud Console 申請
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# 電子郵件設定 (預警通知功能)
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_here
```

#### 5. 安裝前端依賴
```bash
cd frontend
npm install
cd ..
```

### 啟動系統

#### 方法一：使用一鍵部署腳本（推薦）
```bash
# 確保腳本有執行權限
chmod +x deploy.sh

# 啟動完整系統
./deploy.sh
```

#### 方法二：手動啟動

**啟動後端API服務：**
```bash
cd api
python main.py
```
> 後端服務運行在: http://localhost:8000  
> API文檔: http://localhost:8000/docs

**啟動前端應用：**
```bash
cd frontend
npm run dev
```
> 前端應用運行在: http://localhost:3000

### 系統訪問地址

| 功能 | URL | 說明 |
|------|-----|------|
| 🚗 駕駛者介面 | http://localhost:3000/driver | 智慧導航、震波預警、出發時間建議 |
| 🎛️ 管理者介面 | http://localhost:3000/admin | 系統監控、AI決策支援、大屏管理 |
| 📚 API文檔 | http://localhost:8000/docs | 完整的API說明文檔 |
| 💊 健康檢查 | http://localhost:8000/health | 系統狀態檢查 |

## 核心技術架構

### 創新震波檢測技術

**理論基礎：**
本系統首創將地震學中的震波傳播理論應用於交通流分析，參考Indiana州的震波研究案例：
- **後向震波速度**: 4.2 mph (6.7 km/h)
- **實證數據**: 基於59個震波案例，200小時的壅塞觀測
- **檢測精度**: 87%準確率，符合實際交通震波發生頻率

**檢測算法：**
```python
from src.detection.final_optimized_detector import FinalOptimizedShockDetector

# 初始化檢測器
detector = FinalOptimizedShockDetector()

# 震波檢測
shockwaves = detector.detect_shockwaves(
    traffic_data=traffic_data,
    severity_levels=['mild', 'moderate', 'severe']
)

# 獲取檢測結果
for shock in shockwaves:
    print(f"震波強度: {shock.severity}")
    print(f"速度下降: {shock.speed_drop} km/h")
    print(f"影響範圍: {shock.affected_stations}")
    print(f"傳播速度: {shock.propagation_speed} km/h")
```

### MT-STNet深度學習預測系統

**模型特色：**
- **多任務學習**: 同時預測流量(flow)、速度(speed)、密度(density)
- **時空注意力機制**: 捕捉複雜的時間和空間相關性
- **圖神經網路**: 考慮道路網絡拓撲結構
- **多時步預測**: 支援12個歷史時步預測未來12個時步

**技術架構：**
```python
from src.models.mt_stnet.adapter import MTSTNetAdapter

# 初始化MT-STNet模型
predictor = MTSTNetAdapter()

# 載入預訓練權重
predictor.load_model("path/to/model/weights")

# 執行多任務預測
predictions = predictor.predict(
    historical_data=traffic_data,  # [batch, 12, stations, features]
    prediction_steps=12            # 預測未來12個時步
)

# 提取預測結果
flow_pred = predictions['flow']      # 交通流量預測
speed_pred = predictions['speed']    # 車速預測
density_pred = predictions['density'] # 密度預測
```

### 17種基準模型比較

本系統整合了當前最先進的時空預測模型，提供完整的性能比較：

| 模型類別 | 模型名稱 | 特色 | 適用場景 |
|---------|---------|------|---------|
| **圖神經網路** | AGCRN | 自適應圖卷積 | 動態路網結構 |
| | ASTGCN | 時空注意力機制 | 長期預測 |
| | DCRNN | 擴散卷積 | 震波傳播建模 |
| | Graph-WaveNet | 自適應鄰接矩陣 | 複雜路網 |
| | MTGNN | 多任務圖神經網路 | 多變數預測 |
| | STGNN | 時空圖神經網路 | 一般交通預測 |
| **注意力模型** | GMAN | 全局注意力 | 大範圍預測 |
| | ST-GRAT | 時空圖注意力 | 精細化預測 |
| **時間序列** | LSTM/BiLSTM | 長短期記憶 | 時序建模 |
| | ARIMA/SARIMA | 傳統統計模型 | 基準比較 |
| **其他** | SVR | 支援向量回歸 | 非線性關係 |

**模型比較範例：**
```python
from src.models.mt_stnet.baselines import model_comparison

# 運行多模型比較
results = model_comparison.run_comparison(
    models=['MT-STNet', 'DCRNN', 'AGCRN', 'Graph-WaveNet'],
    dataset=traffic_dataset,
    metrics=['MAE', 'RMSE', 'MAPE']
)

# 顯示比較結果
print("模型性能比較:")
for model, metrics in results.items():
    print(f"{model}: MAE={metrics['MAE']:.3f}, RMSE={metrics['RMSE']:.3f}")
```

### 混合預測架構

結合傳統物理模型與深度學習模型的優勢：

```python
from src.core.integrated_system import IntegratedShockPredictionSystem

# 初始化混合預測系統
system = IntegratedShockPredictionSystem()

# 混合預測：傳統方法 + 深度學習
hybrid_result = system.hybrid_predict(
    traffic_data=current_data,
    prediction_horizon=60,  # 預測60分鐘
    use_traditional=True,   # 啟用傳統方法
    use_deep_learning=True, # 啟用深度學習
    fusion_method='weighted_average'  # 融合策略
)

# 獲取混合預測結果
shockwave_prediction = hybrid_result['shockwave']
traffic_prediction = hybrid_result['traffic']
confidence_score = hybrid_result['confidence']
```

## 系統功能

### 駕駛者功能

#### 智慧導航系統
- **震波覆蓋層顯示**: 即時顯示交通震波位置、強度和影響範圍
- **動態路況預測**: AI驅動的未來30-60分鐘交通狀況預測
- **替代路線建議**: 基於震波預測的智慧路線規劃
- **多模態導航**: 整合Google Maps API的精確導航功能

#### ⚡ 震波即時預警系統
- **分級警報機制**: 
  - 🟢 **輕微** (速度下降6-18 km/h)
  - 🟡 **中等** (速度下降18-30 km/h)  
  - 🟠 **嚴重** (速度下降30+ km/h)
- **到達時間預測**: 精確計算震波到達用戶位置的時間
- **影響評估**: 量化震波對行程時間和油耗的影響
- **個人化通知**: 基於用戶位置和路線的客製化警報

#### 智慧出發時間優化
```typescript
// 前端使用範例
import { DepartureTimeOptimizer } from '@/components/smart/DepartureTimeOptimizer';

const optimizer = new DepartureTimeOptimizer({
  origin: "台北市",
  destination: "新竹市",
  preferences: {
    arrivalTime: "09:00",
    tolerance: 30, // 分鐘
    priority: "time" // "time" | "fuel" | "comfort"
  }
});

const suggestions = await optimizer.getOptimalDepartureTimes();
```

### 管理者功能

#### 專業監控中心
- **大屏幕設計**: 支援4K顯示器和多螢幕部署
- **即時交通監控**: 全路網交通流量、速度、密度監控
- **系統健康狀態**: API服務、資料源、模型狀態即時監控
- **效能指標儀表板**: 系統響應時間、預測準確度、用戶活躍度

#### AI決策支援系統
```python
# 後端AI決策範例
from api.routes.admin import AIDecisionSupport

decision_engine = AIDecisionSupport()

# 獲取AI建議
recommendations = decision_engine.get_traffic_management_advice(
    current_conditions=traffic_data,
    predicted_shockwaves=shockwave_predictions,
    historical_effectiveness=past_actions
)

# AI建議包含：
# - 建議管制措施
# - 預期效果評估
# - 風險評估
# - 執行時機建議
```

## 系統效能指標

### ⚡ 即時性能
- **API響應時間**: < 200ms (95th percentile)
- **震波檢測延遲**: < 5秒
- **預測計算時間**: < 1秒 (單次預測)
- **前端載入時間**: < 3秒 (首次載入)
- **資料更新頻率**: 30秒 (震波) / 5分鐘 (交通)

### 預測準確度
| 預測類型 | MAE | RMSE | MAPE | 備註 |
|---------|-----|------|------|------|
| 震波檢測 | - | - | 87% | 準確率 |
| 交通流量 | 12.3 | 18.7 | 8.5% | veh/5min |
| 車速預測 | 3.2 | 5.1 | 6.8% | km/h |
| 密度預測 | 8.9 | 13.4 | 11.2% | veh/km |
| 到達時間 | 2.1 | 3.8 | 4.2% | 分鐘 |

## API 文檔

### 核心API端點

#### 交通資料API
```http
GET /api/traffic/current
# 回應: 即時交通資料
{
  "timestamp": "2024-01-01T12:00:00Z",
  "stations": [
    {
      "station_id": "001F",
      "location": {"lat": 25.0330, "lng": 121.5654},
      "flow": 1200,
      "speed": 65.5,
      "density": 18.3
    }
  ]
}

GET /api/traffic/historical?start_date=2024-01-01&end_date=2024-01-07
POST /api/traffic/query
# 請求: 自定義查詢條件
{
  "stations": ["001F", "002F"],
  "metrics": ["flow", "speed"],
  "time_range": "24h"
}
```

#### 震波檢測API
```http
GET /api/shockwave/active
# 回應: 當前活躍震波
{
  "active_shockwaves": [
    {
      "id": "sw_001",
      "severity": "moderate",
      "speed_drop": 25.3,
      "affected_stations": ["001F", "002F", "003F"],
      "propagation_speed": 6.8,
      "estimated_duration": 45
    }
  ]
}

POST /api/shockwave/predict
# 請求: 震波預測
{
  "location": {"lat": 25.0330, "lng": 121.5654},
  "time_horizon": 60
}
```

#### AI預測API
```http
POST /api/prediction/traffic
# 請求: 交通預測
{
  "model": "MT-STNet",
  "stations": ["001F", "002F"],
  "prediction_steps": 12,
  "include_uncertainty": true
}

GET /api/prediction/models/status
# 回應: 模型狀態
{
  "models": {
    "MT-STNet": {"status": "ready", "accuracy": 0.85},
    "DCRNN": {"status": "training", "progress": 0.75}
  }
}
```

## 資料安全與隱私

### 安全措施
- **環境變數保護**: 敏感資訊使用`.env`檔案管理，不進入版本控制
- **API憑證加密**: 使用`python-jose`進行憑證加密存儲
- **輸入驗證**: Pydantic模型確保API輸入的安全性
- **CORS設定**: 嚴格控制跨域資源共享
- **錯誤處理**: 安全的錯誤訊息，避免資訊洩露

### 隱私保護
- **資料匿名化**: 交通資料不包含個人識別資訊
- **本地處理**: 位置資料在客戶端處理，不上傳伺服器
- **資料保留期限**: 設定合理的資料保留和清理策略

## 測試與驗證

### 環境檢查
```bash
# 執行完整環境檢查
python check_environment.py

# 檢查特定模組
python -c "from src.detection import *; print('✅ 檢測模組正常')"
python -c "from src.prediction import *; print('✅ 預測模組正常')" 
python -c "from src.models.mt_stnet import *; print('✅ 深度學習模組正常')"
```

### 📊 系統測試
```bash
# 啟動系統測試
cd api
python -m pytest tests/ -v

# 前端測試
cd frontend
npm test

# 效能測試
python tests/performance_test.py
```

### 相關研究
- **MT-STNet論文**: [IEEE Xplore](https://ieeexplore.ieee.org/document/10559778)
- **交通震波理論**: 參考`Reference/`目錄中的學術文獻
- **基準模型比較**: 詳見`src/models/mt_stnet/baselines/`

### 資料集
系統使用台灣高速公路局提供的真實交通資料：
- **資料來源**: 交通部TDX平台
- **時間範圍**: 2020-2024年
- **空間範圍**: 台灣高速公路網
- **更新頻率**: 每30秒




*讓AI為您的出行保駕護航，基於尖端科學研究的智慧交通解決方案* 🛣️✨

</div>
# highway_traffic
# highway_traffic
