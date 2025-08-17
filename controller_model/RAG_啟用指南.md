# RAG 增強模型啟用指南

## 系統概述

這是一個基於 Ollama 的 RAG（檢索增強生成）系統，專門用於台灣高速公路交通資料分析。系統會：
1. 處理國道一號和三號的 CSV 資料
2. 建立向量資料庫進行語義搜索
3. 整合 Ollama 本地大語言模型提供智能問答

## 環境需求

### 基礎需求
- Python 3.8+
- 至少 8GB 可用記憶體
- 至少 10GB 可用硬碟空間

### 系統依賴
- Ollama 服務（用於運行本地 LLM）
- ChromaDB（向量資料庫）
- Sentence Transformers（文本嵌入）

## 安裝步驟

### 1. 安裝 Ollama

#### macOS/Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Windows:
從 [Ollama 官網](https://ollama.ai) 下載安裝包

### 2. 安裝 Python 依賴

```bash
cd /Users/lishengfeng/Desktop/Highway_trafficwave-main/train_model
pip install -r requirements.txt
```

如果遇到依賴問題，請安裝以下套件：
```bash
pip install torch sentence-transformers chromadb httpx loguru pandas numpy jieba pyyaml
```

### 3. 啟動 Ollama 服務

```bash
# 啟動 Ollama 服務
ollama serve

# 在新終端中下載模型（建議使用較小的模型）
ollama pull deepseek-r1:32b
# 或者使用更大的模型（需要更多記憶體）
ollama pull deepseek-r1:32b
```

### 4. 準備資料

確保以下資料文件存在：
- `../data/Taiwan/國道一號_整合資料.csv`
- `../data/Taiwan/國道三號_整合資料.csv`

## 配置設定

系統會自動創建配置文件 `configs/rag_config.yaml`，您可以根據需要調整：

```yaml
# Ollama 設定
ollama:
  base_url: "http://localhost:11434"
  model: "deepseek-r1:32b"  # 可修改為您下載的模型
  timeout: 300
  max_tokens: 2048
  temperature: 0.1

# 向量嵌入設定
embeddings:
  model_name: "all-MiniLM-L6-v2"
  device: "cpu"  # 如有 GPU 可改為 "cuda"
  batch_size: 32
  max_length: 512

# 檢索設定
retrieval:
  top_k: 5
  score_threshold: 0.7
```

## 啟用方法

### 方法一：完整訓練流程

```bash
cd /Users/lishengfeng/Desktop/Highway_trafficwave-main/train_model/scripts
python train_rag.py --mode train
```

這將執行：
1. 資料預處理
2. 向量索引建構
3. 系統測試

### 方法二：分步驟執行

1. **僅處理資料**：
```bash
python train_rag.py --mode train --force-reprocess
```

2. **重建向量索引**：
```bash
python train_rag.py --mode train --force-rebuild
```

3. **僅測試系統**：
```bash
python train_rag.py --mode test
```

4. **啟動互動聊天**：
```bash
python train_rag.py --mode chat
```

## 使用方式

### 互動聊天模式

啟動聊天模式後，您可以詢問關於台灣高速公路的問題：

```
您: 國道一號的車道寬度通常是多少？
助手: 根據資料顯示，國道一號的車道寬度通常為...

您: 國道三號和國道一號在路面設計上有什麼不同？
助手: 在路面設計方面，國道三號和國道一號的主要差異包括...
```

### 程式化調用

```python
from train_model.models.ollama_client import OllamaClient, RAGOllamaChat
from train_model.embeddings.vector_store import VectorStore, RAGRetriever

# 初始化組件
vector_store = VectorStore()
retriever = RAGRetriever(vector_store)
ollama_client = OllamaClient()
rag_chat = RAGOllamaChat(ollama_client, retriever)

# 進行對話
response = await rag_chat.chat("請介紹國道一號的特色")
print(response)
```

## 故障排除

### 常見問題

1. **Ollama 連接失敗**
   - 確認 Ollama 服務正在運行：`ollama list`
   - 檢查服務地址：`http://localhost:11434`
   - 重啟服務：`ollama serve`

2. **模型下載失敗**
   - 檢查網絡連接
   - 嘗試手動下載：`ollama pull deepseek-r1:32b`
   - 使用更小的模型：`ollama pull llama3:latest`

3. **記憶體不足**
   - 使用較小的模型（如 `deepseek-r1:32b` 而非 `deepseek-r1:32b`）
   - 減少批次大小（在配置中修改 `batch_size`）
   - 關閉其他應用程式

4. **向量資料庫錯誤**
   - 刪除 `./vector_db` 目錄重新建立
   - 使用 `--force-rebuild` 參數重建索引

5. **資料文件找不到**
   - 檢查 CSV 文件路徑是否正確
   - 確保文件編碼為 UTF-8

### 日誌查看

系統日誌保存在 `rag_training.log`：
```bash
tail -f rag_training.log
```

### 效能調優

1. **使用 GPU**（如果可用）：
   - 在配置中設定 `device: "cuda"`
   - 安裝 PyTorch GPU 版本

2. **調整批次大小**：
   - 記憶體充足時可增大 `batch_size`
   - 記憶體不足時減小批次大小

3. **模型選擇**：
   - 測試用途：`deepseek-r1:32b`
   - 生產環境：`deepseek-r1:32b`

## 性能指標

正常運行時的預期指標：
- 資料處理：約 1000 筆記錄/分鐘
- 向量索引建立：約 100 個文檔/分鐘
- 問答響應時間：2-10 秒（取決於模型大小）

## 進階設定

### 自定義配置

創建自定義配置文件：
```bash
export RAG_CONFIG_PATH="/path/to/your/config.yaml"
python train_rag.py --mode train
```

### API 整合

系統可以整合到現有的 API 服務中：
```python
from train_model.models.ollama_client import RAGOllamaChat

# 在您的 API 路由中
@app.post("/chat")
async def chat_endpoint(query: str):
    response = await rag_chat.chat(query)
    return {"response": response}
```

## 支援

如果遇到問題：
1. 檢查日誌文件
2. 確認所有依賴已正確安裝
3. 驗證 Ollama 服務狀態
4. 參考故障排除章節

系統正常啟動後，您就可以開始使用 RAG 增強的高速公路交通助手了！