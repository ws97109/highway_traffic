# RAG 訓練系統

基於 Ollama deepseek-r1:32b 模型和台灣國道資料的檢索增強生成 (RAG) 系統。

## 🚀 快速開始

### 1. 環境準備

```bash
# 安裝 Ollama (如果尚未安裝)
curl -fsSL https://ollama.ai/install.sh | sh

# 拉取 deepseek-r1:32b 模型
ollama pull deepseek-r1:32b

# 安裝 Python 依賴
pip install -r requirements.txt
```

### 2. 配置設置

確保主項目的 `.env` 文件已包含 Ollama 配置：

```env
# Ollama 設定
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:32b
```

### 3. 訓練 RAG 系統

```bash
# 完整訓練流程
python scripts/train_rag.py --mode train

# 強制重新處理資料和重建索引
python scripts/train_rag.py --mode train --force-reprocess --force-rebuild
```

### 4. 測試系統

```bash
# 執行評估測試
python scripts/train_rag.py --mode test
```

### 5. 互動式聊天

```bash
# 啟動聊天模式
python scripts/train_rag.py --mode chat
```

## 📁 專案結構

```
train_model/
├── configs/
│   └── rag_config.yaml           # RAG 系統配置
├── data_processing/
│   └── csv_processor.py          # CSV 資料處理器
├── embeddings/
│   └── vector_store.py           # 向量儲存和檢索
├── models/
│   └── ollama_client.py          # Ollama 客戶端
├── scripts/
│   └── train_rag.py              # 主訓練腳本
├── utils/
│   └── evaluation.py             # 評估工具
├── vector_db/                    # 向量資料庫儲存
├── processed_data/               # 處理後的資料
├── requirements.txt              # Python 依賴
└── README.md                     # 說明文件
```

## 🔧 系統組件

### 資料處理 (CSV Processor)
- 載入國道一號和三號整合資料
- 清理和正規化資料
- 轉換結構化資料為文字描述
- 文本分塊處理

### 向量儲存 (Vector Store)
- 支援 ChromaDB 向量資料庫
- 使用 SentenceTransformer 生成嵌入
- 提供相似度搜索功能
- 可配置的檢索參數

### Ollama 客戶端
- 連接本地 Ollama 服務
- 支援同步和異步生成
- 流式回應支援
- 模型管理功能

### RAG 聊天系統
- 整合檢索和生成功能
- 對話歷史管理
- 上下文感知回答
- 可配置的檢索策略

## ⚙️ 配置說明

### rag_config.yaml 主要參數：

```yaml
# Ollama 設定
ollama:
  model: "deepseek-r1:32b"          # 使用的模型
  temperature: 0.1               # 生成溫度
  max_tokens: 2048              # 最大生成長度

# 嵌入設定
embeddings:
  model_name: "all-MiniLM-L6-v2" # 嵌入模型
  batch_size: 32                 # 批次大小

# 文本分塊
chunking:
  chunk_size: 1000              # 塊大小
  chunk_overlap: 200            # 重疊大小

# 檢索設定
retrieval:
  top_k: 5                      # 檢索文檔數量
  score_threshold: 0.7          # 相似度閾值
```

## 🎯 使用範例

### 程式化使用

```python
from train_model.scripts.train_rag import RAGTrainer
import asyncio

async def main():
    # 初始化訓練器
    trainer = RAGTrainer()
    
    # 設置組件
    await trainer.setup_components()
    
    # 互動對話
    response = await trainer.rag_chat.chat("國道一號的車道寬度是多少？")
    print(response)

asyncio.run(main())
```

### 命令行使用

```bash
# 訓練系統
python scripts/train_rag.py --mode train

# 測試特定問題
echo "國道三號有什麼特色？" | python scripts/train_rag.py --mode chat

# 使用自定義配置
python scripts/train_rag.py --config custom_config.yaml --mode train
```

## 📊 評估系統

系統包含自動評估功能，評估指標包括：

- **關鍵詞覆蓋率**: 回答包含預期關鍵詞的比例
- **回答長度**: 回答長度適中性評分
- **資訊密度**: 基於句子結構的資訊豐富度
- **專業術語**: 專業術語使用頻率
- **總體評分**: 加權平均綜合評分

## 🚧 故障排除

### 常見問題：

1. **Ollama 連接失敗**
   ```bash
   # 檢查 Ollama 服務狀態
   ollama list
   
   # 重啟 Ollama 服務
   ollama serve
   ```

2. **記憶體不足**
   - 減小 `batch_size` 參數
   - 使用更小的嵌入模型
   - 增加系統交換空間

3. **向量資料庫錯誤**
   ```bash
   # 刪除現有資料庫重新開始
   rm -rf train_model/vector_db
   python scripts/train_rag.py --mode train --force-rebuild
   ```

### 效能調優：

- **GPU 加速**: 在配置中設置 `device: "cuda"`
- **批次處理**: 調整 `batch_size` 參數
- **索引優化**: 調整 `chunk_size` 和 `top_k` 參數

## 📈 進階功能

### 自定義評估問題

創建 `test_questions.json` 文件：

```json
[
  {
    "id": "custom_q1",
    "question": "自定義問題",
    "category": "分類",
    "expected_keywords": ["關鍵詞1", "關鍵詞2"],
    "difficulty": "困難"
  }
]
```

### 模型微調

雖然此系統主要使用 RAG，但可以透過以下方式優化：

1. **提示工程**: 調整系統提示模板
2. **檢索策略**: 實驗不同的 `top_k` 和閾值設定
3. **分塊策略**: 調整 `chunk_size` 和重疊參數

## 📝 開發指南

### 添加新的資料來源

1. 修改 `csv_processor.py` 中的資料載入邏輯
2. 更新 `rag_config.yaml` 中的資料路徑
3. 重新執行訓練流程

### 支援新的向量資料庫

1. 在 `vector_store.py` 中添加新的資料庫實作
2. 更新配置文件中的資料庫類型選項
3. 實作對應的初始化和操作方法

## 📄 授權

本專案遵循主項目的授權條款。