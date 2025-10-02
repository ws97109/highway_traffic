# 🚀 RAG 智能交通助手 - 完整使用指南

## 📋 系統概述

本系統已成功整合 **train_model** 目錄中的完整 RAG（Retrieval-Augmented Generation）系統，提供真正的向量檢索增強生成功能。

### ✨ 主要特點

1. **真正的 RAG 實作**
   - ✅ ChromaDB 向量資料庫
   - ✅ Sentence Transformers 嵌入模型
   - ✅ 基於國道一號和三號真實 CSV 資料的知識庫
   - ✅ 語義搜尋和檢索

2. **繁體中文支援**
   - ✅ 簡繁轉換函數
   - ✅ 強制繁體中文回應
   - ✅ 台灣本土化交通術語

3. **完整整合**
   - ✅ train_model RAG 系統 → API 路由
   - ✅ API → 前端 (駕駛者介面 + 聊天機器人)
   - ✅ 即時交通數據整合
   - ✅ 震波預警整合

## 🛠️ 系統架構

```
Highway_trafficwave/
├── train_model/                    # RAG 核心系統
│   ├── models/
│   │   ├── ollama_client.py       # Ollama 客戶端
│   │   └── driver_advisor.py      # 智能駕駛建議系統
│   ├── embeddings/
│   │   └── vector_store.py        # 向量存儲（ChromaDB）
│   ├── data_processing/           # 資料處理
│   └── configs/
│       └── rag_config.yaml        # RAG 配置
│
├── api/routes/
│   └── rag_integrated.py          # RAG API 整合
│
└── frontend/src/
    ├── components/chat/RagChatbot.tsx  # RAG 聊天機器人
    └── pages/driver/Dashboard.tsx      # 駕駛者介面
```

## 📦 環境準備

### 1. 安裝 Ollama

#### macOS/Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Windows:
從 [Ollama 官網](https://ollama.ai) 下載安裝包

### 2. 下載 AI 模型

```bash
# 啟動 Ollama 服務
ollama serve

# 在新終端下載模型（建議）
ollama pull qwen2.5:7b

# 或使用其他模型
ollama pull deepseek-r1:32b
ollama pull llama3:latest
```

### 3. 安裝 Python 依賴

```bash
cd train_model
pip install -r requirements.txt
```

如果遇到問題：
```bash
pip install torch sentence-transformers chromadb httpx loguru pandas numpy jieba pyyaml
```

### 4. 準備資料並建立向量資料庫

```bash
cd train_model/scripts

# 完整訓練流程（處理資料 + 建立向量索引）
python train_rag.py --mode train

# 或分步驟執行
python train_rag.py --mode train --force-reprocess  # 重新處理資料
python train_rag.py --mode train --force-rebuild    # 重建向量索引
```

### 5. 測試 RAG 系統

```bash
# 測試 RAG 系統
python train_rag.py --mode test

# 啟動互動聊天測試
python train_rag.py --mode chat
```

## 🚀 啟動系統

### 1. 啟動後端 API

```bash
# 確保在項目根目錄
cd /Users/lishengfeng/Desktop/Highway_trafficwave

# 啟動 FastAPI 服務器
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 啟動前端

```bash
cd frontend
npm run dev
```

### 3. 訪問系統

- **前端介面**: http://localhost:3000
- **API 文件**: http://localhost:8000/docs
- **RAG 狀態**: http://localhost:8000/api/rag/status

## 📡 API 使用

### 端點 1: RAG 對話

```bash
POST http://localhost:8000/api/rag/chat
Content-Type: application/json

{
  "message": "五股林口塞車問題可以怎麼解決？",
  "use_rag": true,
  "traffic_data": {
    "stations": [...]
  },
  "shockwave_data": {...},
  "user_location": {
    "lat": 25.0330,
    "lng": 121.5654
  }
}
```

**回應格式：**
```json
{
  "response": "五股林口路段是北部最容易壅塞的路段之一...",
  "sources": ["使用 RAG 知識庫檢索相關交通資訊"],
  "confidence_score": 0.85,
  "model": "Ollama + RAG (train_model)",
  "timestamp": "2025-10-02T06:37:07Z",
  "rag_enabled": true
}
```

### 端點 2: 系統狀態

```bash
GET http://localhost:8000/api/rag/status
```

**回應：**
```json
{
  "status": "healthy",
  "rag_enabled": true,
  "ollama_connected": true,
  "conversation_count": 10,
  "rag_usage_rate": 0.8,
  "model": "Ollama + Vector Store (ChromaDB)",
  "features": {
    "vector_search": true,
    "traditional_chinese": true,
    "real_time_data": true,
    "shockwave_analysis": true
  }
}
```

### 端點 3: 清除對話歷史

```bash
POST http://localhost:8000/api/rag/clear-history
```

### 端點 4: 對話統計

```bash
GET http://localhost:8000/api/rag/stats
```

## 🧪 測試 RAG 系統

### 使用測試腳本

```bash
python test_rag_system.py
```

### 預期輸出

```
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀
               RAG 系統完整測試
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀

============================================================
📊 測試 RAG 系統狀態
============================================================
✅ RAG 系統狀態： healthy
📚 知識庫文件數：100+
🤖 Ollama 連接：True
✨ RAG 啟用：True
🇹🇼 繁體中文支援：True

============================================================
📊 測試總結
============================================================
系統狀態              : ✅ 通過
RAG 對話              : ✅ 通過
繁體中文              : ✅ 通過

總計：3/3 個測試通過
🎉 所有測試通過！RAG 系統運作正常！
```

## 💻 前端整合

### 駕駛者介面

駕駛者介面的 AI 建議按鈕已整合 RAG：

```typescript
// 點擊 AI 建議按鈕
const response = await fetch('/api/rag/chat', {
  method: 'POST',
  body: JSON.stringify({
    message: "請分析當前路況並提供建議",
    traffic_data: { stations: trafficData },
    user_location: userLocation,
    use_rag: true
  })
});

const result = await response.json();
// result.response 包含 AI 建議
// result.sources 包含 RAG 來源
// result.confidence_score 為信心分數
```

### RAG 聊天機器人

聊天機器人自動使用 RAG API：

```typescript
const response = await fetch('/api/rag/chat', {
  method: 'POST',
  body: JSON.stringify({
    message: userMessage,
    use_rag: true
  })
});
```

## 🔧 配置說明

### RAG 配置文件

位置：`train_model/configs/rag_config.yaml`

```yaml
# Ollama 設定
ollama:
  base_url: "http://localhost:11434"
  model: "qwen2.5:7b"
  timeout: 300
  max_tokens: 2048
  temperature: 0.1

# 向量嵌入設定
embeddings:
  model_name: "all-MiniLM-L6-v2"
  device: "cpu"  # 或 "cuda" (如有 GPU)
  batch_size: 32
  max_length: 512

# 向量資料庫設定
vector_db:
  type: "chroma"
  persist_directory: "./vector_db"
  collection_name: "highway_data"

# 檢索設定
retrieval:
  top_k: 5
  score_threshold: 0.7
```

### 環境變數

可選的環境變數：

```bash
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="qwen2.5:7b"
export RAG_CONFIG_PATH="/path/to/custom/config.yaml"
```

## 🐛 疑難排解

### 問題 1: Ollama 連接失敗

**症狀：** `Ollama 服務連接失敗`

**解決方案：**
```bash
# 檢查 Ollama 是否運行
ollama list

# 重啟 Ollama
ollama serve

# 確認端口
curl http://localhost:11434/api/tags
```

### 問題 2: RAG 模組導入失敗

**症狀：** `無法導入 RAG 模組`

**解決方案：**
```bash
# 檢查 Python 路徑
python -c "import sys; print(sys.path)"

# 安裝缺失依賴
cd train_model
pip install -r requirements.txt

# 重新建立向量資料庫
python scripts/train_rag.py --mode train --force-rebuild
```

### 問題 3: 向量資料庫未初始化

**症狀：** `向量資料庫不存在或為空`

**解決方案：**
```bash
cd train_model/scripts

# 檢查資料文件
ls -la ../../data/Taiwan/

# 重新訓練
python train_rag.py --mode train --force-rebuild
```

### 問題 4: 簡體中文出現在回應中

**症狀：** AI 回應包含簡體字

**解決方案：**
1. 檢查 `ensure_traditional_chinese()` 函數
2. 更新簡繁對照表
3. 在 prompt 中強調使用繁體中文

### 問題 5: GPU 記憶體不足

**症狀：** `CUDA out of memory`

**解決方案：**
```yaml
# 在 rag_config.yaml 中修改
embeddings:
  device: "cpu"  # 改用 CPU
  batch_size: 16  # 減小批次大小
```

## 📊 系統對比

### RAG vs 傳統 AI

| 功能 | 傳統 AI | RAG 系統 (新版) |
|------|---------|----------------|
| 知識來源 | ❌ AI 模型內建 | ✅ 向量資料庫 + 真實 CSV |
| 資料準確性 | ⚠️ 可能幻覺 | ✅ 基於真實資料 |
| 台灣本土化 | ⚠️ 通用知識 | ✅ 國道專業知識 |
| 繁體中文 | ⚠️ 可能混用 | ✅ 強制繁體 |
| 向量檢索 | ❌ 無 | ✅ ChromaDB |
| 來源追溯 | ❌ 無 | ✅ 顯示來源 |

## 📈 效能指標

### 正常運行指標

- **資料處理速度**: ~1000 筆記錄/分鐘
- **向量索引建立**: ~100 個文檔/分鐘
- **問答響應時間**: 2-10 秒（取決於模型）
- **RAG 檢索時間**: <1 秒
- **向量相似度搜尋**: <500ms

### 資源使用

- **記憶體使用**: 2-4GB (CPU模式) / 4-8GB (GPU模式)
- **磁碟空間**: ~500MB (向量資料庫) + ~2GB (模型)
- **CPU 使用率**: 30-60% (查詢時)

## 🔐 安全性

### API 安全

1. **CORS 配置**: 已限制允許的來源
2. **輸入驗證**: 所有輸入經過 Pydantic 驗證
3. **錯誤處理**: 不洩露敏感資訊

### 資料隱私

1. **本地運行**: 所有 AI 計算在本地進行
2. **無資料外傳**: 不向外部 API 發送資料
3. **對話歷史**: 僅存在記憶體中，可隨時清除

## 📚 進階使用

### 自定義知識庫

```python
# 添加自定義文檔到向量資料庫
from train_model.embeddings.vector_store import VectorStore

vector_store = VectorStore()
documents = [
    {
        "id": "custom_1",
        "text": "您的自定義交通知識...",
        "source": "custom",
        "chunk_index": 0,
        "original_index": 0
    }
]
vector_store.add_documents(documents)
```

### 程式化調用

```python
from train_model.models.ollama_client import OllamaClient, RAGOllamaChat
from train_model.embeddings.vector_store import VectorStore, RAGRetriever

# 初始化
vector_store = VectorStore()
retriever = RAGRetriever(vector_store)
ollama_client = OllamaClient()
rag_chat = RAGOllamaChat(ollama_client, retriever)

# 對話
response = await rag_chat.chat("國道一號的特色是什麼？")
print(response)
```

## 🚧 未來改進

### 短期（1-2 週）
- [ ] 多語言支援（英文、日文）
- [ ] 語音輸入/輸出
- [ ] 更多交通資料來源

### 中期（1-2 個月）
- [ ] 即時資料自動更新知識庫
- [ ] 多輪對話上下文追蹤
- [ ] 個人化建議引擎

### 長期（3+ 個月）
- [ ] 微調專門的台灣交通 AI 模型
- [ ] 圖像辨識（路況照片分析）
- [ ] 預測性維護和路線優化

## 📞 支援與聯繫

- **API 文件**: http://localhost:8000/docs
- **RAG 狀態**: http://localhost:8000/api/rag/status
- **對話統計**: http://localhost:8000/api/rag/stats
- **日誌文件**: `train_model/rag_training.log`

---

**版本**: 2.0.0 (RAG Enhanced)
**最後更新**: 2025-10-02
**系統狀態**: ✅ 生產就緒
