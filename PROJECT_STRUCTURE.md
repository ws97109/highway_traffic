# 高速公路交通衝擊波預測系統 - 項目結構

## 🏗️ 整體架構

本系統整合了傳統交通分析方法與最先進的深度學習技術，用於高速公路交通衝擊波的檢測與預測。

### 📁 主要目錄結構

```
highway-traffic/
├── 📂 src/                          # 源代碼目錄（模組化架構）
│   ├── 📂 core/                     # 核心系統模組
│   │   ├── __init__.py
│   │   └── integrated_system.py    # 主整合系統
│   │
│   ├── 📂 detection/                # 衝擊波檢測模組
│   │   ├── __init__.py
│   │   ├── trafficWave.py          # 基礎交通波動分析
│   │   └── final_optimized_detector.py  # 優化檢測器
│   │
│   ├── 📂 prediction/               # 傳統預測模組
│   │   ├── __init__.py
│   │   ├── realtime_shock_predictor.py    # 即時衝擊波預測
│   │   ├── location_based_predictor.py   # 基於位置的預測
│   │   └── propagation_system.py         # 傳播系統
│   │
│   ├── 📂 data/                     # 資料處理模組
│   │   ├── __init__.py
│   │   ├── dataLoad.py             # 資料載入器
│   │   ├── dataLoad_new.py         # 新版資料載入器
│   │   └── tisc_api_tester.py      # API 測試工具
│   │
│   ├── 📂 systems/                  # 整合系統模組
│   │   ├── __init__.py
│   │   └── shock_warning_system.py # 衝擊波警告系統
│   │
│   ├── 📂 utils/                    # 工具函數模組
│   │   ├── __init__.py
│   │   └── config_loader.py        # 配置載入器
│   │
│   └── 📂 models/                   # 🆕 深度學習模型模組
│       └── 📂 mt_stnet/             # MT-STNet 深度學習套件
│           ├── 📂 core/             # 核心模型組件
│           │   ├── models.py        # 主要模型定義
│           │   ├── st_block.py      # 時空注意力區塊
│           │   ├── layers.py        # 神經網路層
│           │   ├── embedding.py     # 嵌入層
│           │   └── gate_fusion.py   # 門控融合機制
│           │
│           ├── 📂 data/             # 資料處理
│           │   ├── data_loader.py   # 深度學習資料載入
│           │   ├── short_path.py    # 路徑計算
│           │   └── train.py         # 訓練資料處理
│           │
│           ├── 📂 utils/            # 深度學習工具
│           │   ├── metrics.py       # 評估指標
│           │   ├── utils.py         # 通用工具
│           │   ├── tf_utils.py      # TensorFlow 工具
│           │   └── inits.py         # 初始化函數
│           │
│           ├── 📂 config/           # 模型配置
│           │   └── config.py        # 超參數配置
│           │
│           ├── 📂 baselines/        # 基準模型（17種）
│           │   ├── AGCRN/          # 自適應圖卷積循環網路
│           │   ├── ASTGCN/         # 時空圖卷積網路
│           │   ├── DCRNN/          # 擴散卷積循環網路
│           │   ├── Graph-WaveNet/  # 圖波網路
│           │   ├── MTGNN/          # 多任務圖神經網路
│           │   ├── T-GCN/          # 時間圖卷積網路
│           │   └── ... (更多模型)
│           │
│           ├── 📂 weights/          # 預訓練權重
│           ├── 📂 results/          # 實驗結果
│           ├── adapter.py           # 🔧 模型適配器
│           ├── run_train.py         # 訓練腳本
│           ├── README.md            # 模型說明
│           └── requirements.txt     # 依賴套件
│
├── 📂 data/                         # 資料存儲目錄
│   ├── 📂 config/                   # 系統配置
│   ├── 📂 locations/                # 位置資料
│   ├── 📂 logs/                     # 系統日誌
│   ├── 📂 predictions/              # 預測結果
│   ├── 📂 realtime_data/            # 即時資料
│   ├── 📂 Taiwan/                   # 台灣交通資料
│   ├── 📂 users/                    # 用戶資料
│   └── 📂 warnings/                 # 警告資料
│
├── 📂 Reference/                    # 參考文獻與資料
│   ├── 中文Reference.txt
│   ├── 英文Reference.txt
│   └── 📂 paper/                    # 相關論文
│
├── 📄 README.md                     # 項目說明
├── 📄 CONFIG_SETUP.md               # 配置設定說明
├── 📄 MT-STNet_Integration_Plan.md  # 模型整合計劃
└── 📄 MT-STNet_Integration_Report.md # 整合完成報告
```

## 🔧 系統功能模組

### 1. 傳統分析模組 (src/detection & src/prediction)
- **交通波動檢測**: 基於統計方法的衝擊波識別
- **即時預測**: 傳統時間序列預測方法
- **位置預測**: 基於地理位置的預測模型
- **傳播分析**: 衝擊波傳播路徑分析

### 2. 深度學習模組 (src/models/mt_stnet)
- **MT-STNet**: 多任務時空神經網路主模型
- **17種基準模型**: 包含 AGCRN, DCRNN, Graph-WaveNet 等
- **模型適配器**: 統一的模型使用介面
- **預訓練權重**: 可直接使用的模型權重

### 3. 資料處理模組 (src/data)
- **多源資料整合**: 支援不同格式的交通資料
- **即時資料處理**: 處理即時交通流資料
- **API 介面**: 與外部資料源的連接

### 4. 整合系統 (src/core & src/systems)
- **核心整合**: 統一管理所有預測模組
- **警告系統**: 基於預測結果的警告機制
- **日誌系統**: 完整的系統運行記錄

## 🚀 使用方式

### 傳統方法預測
```python
from src.prediction.realtime_shock_predictor import RealtimeShockPredictor

predictor = RealtimeShockPredictor()
result = predictor.predict(traffic_data)
```

### 深度學習預測
```python
from src.models.mt_stnet.adapter import MTSTNetAdapter

dl_predictor = MTSTNetAdapter()
dl_predictor.load_model("path/to/weights")
result = dl_predictor.predict(traffic_data)
```

### 混合預測
```python
from src.core.integrated_system import IntegratedSystem

system = IntegratedSystem()
hybrid_result = system.hybrid_predict(traffic_data)
```

## 📊 模型能力

- **17種深度學習模型**: 涵蓋圖神經網路、循環網路、注意力機制等
- **多任務學習**: 同時預測流量、速度、密度等多個指標
- **時空建模**: 考慮交通網路的時間和空間相關性
- **即時預測**: 支援毫秒級的即時預測響應

## 🔄 系統工作流程

1. **資料收集**: 從各種來源收集交通資料
2. **預處理**: 清理和標準化資料
3. **特徵提取**: 提取交通流特徵
4. **模型預測**: 使用傳統方法或深度學習模型預測
5. **結果融合**: 整合多個模型的預測結果
6. **警告生成**: 根據預測結果生成警告
7. **結果輸出**: 輸出預測結果和警告資訊

## 💡 技術特點

- **模組化設計**: 清晰的程式碼結構，易於維護和擴展
- **多方法融合**: 結合傳統方法和深度學習的優勢
- **即時處理**: 支援大規模即時交通資料處理
- **可擴展性**: 易於添加新的預測模型和功能
- **高可用性**: 完整的錯誤處理和日誌系統

---

**最後更新**: 2025年1月20日  
**系統狀態**: ✅ 完整整合  
**深度學習支援**: ✅ MT-STNet + 17種基準模型
