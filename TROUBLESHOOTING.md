# Ollama API 連接問題排查指南

## 🔍 問題診斷步驟

### 1. 檢查 Ollama 服務是否運行

```bash
# 測試 Ollama 服務
curl http://localhost:11434/api/tags
```

**預期結果:** 應該看到可用模型列表，包含 `qwen2.5:7b`

---

### 2. 測試簡化的診斷端點

重啟開發伺服器後，訪問：

```
http://localhost:3000/api/test-ollama
```

這會顯示詳細的診斷資訊，包括：
- 環境變數配置
- Ollama 連接測試
- 模型生成測試

---

### 3. 檢查開發伺服器日誌

在運行 `npm run dev` 的終端中，查找以下訊息：

- ✅ **成功**: `🤖 發送請求到 Ollama`
- ❌ **錯誤**: `❌ RAG Chat API 錯誤`

複製完整的錯誤堆疊訊息以便診斷。

---

### 4. 測試頁面

訪問測試頁面來驗證所有功能：

```
http://localhost:3000/test-api
```

依序點擊三個測試按鈕：
1. 測試 Ollama 服務狀態
2. 測試 RAG Chat API
3. 測試震波分析 API

---

## 🐛 常見問題

### 問題 1: "Failed to fetch" 或連接錯誤

**原因:** Ollama 服務未運行或端口錯誤

**解決方法:**
```bash
# 檢查 Ollama 是否運行
ps aux | grep ollama

# 重啟 Ollama (macOS)
ollama serve

# 確認端口
curl http://localhost:11434/api/tags
```

---

### 問題 2: "Model not found"

**原因:** 模型 `qwen2.5:7b` 未安裝

**解決方法:**
```bash
# 拉取模型
ollama pull qwen2.5:7b

# 確認模型已安裝
ollama list
```

---

### 問題 3: API Route 500 錯誤

**原因:** Next.js API Route 中的執行錯誤

**解決方法:**
1. 查看開發伺服器終端的完整錯誤訊息
2. 訪問 `/api/test-ollama` 獲取詳細診斷
3. 檢查 `.env.local` 中的環境變數設定

---

### 問題 4: 環境變數未生效

**原因:** Next.js 開發伺服器未重啟

**解決方法:**
```bash
# 停止開發伺服器 (Ctrl+C)
# 重新啟動
cd frontend
npm run dev
```

**重要:** 修改 `.env.local` 後必須重啟開發伺服器

---

## 📋 檢查清單

在報告問題前，請確認：

- [ ] Ollama 服務正在運行 (`curl http://localhost:11434/api/tags`)
- [ ] 模型 `qwen2.5:7b` 已安裝 (`ollama list`)
- [ ] `.env.local` 包含 `NEXT_PUBLIC_OLLAMA_URL=http://localhost:11434`
- [ ] 修改環境變數後已重啟開發伺服器
- [ ] 已訪問 `/api/test-ollama` 查看診斷結果
- [ ] 已檢查開發伺服器終端的完整錯誤訊息

---

## 🔧 快速診斷命令

```bash
# 一鍵診斷腳本
cd /Users/lishengfeng/Desktop/Highway_trafficwave
node test-ollama-api.js
```

這會自動測試：
- Ollama 服務連接
- Next.js API Route 狀態
- 模型生成功能

---

## 📞 獲取幫助

如果問題仍未解決，請提供以下資訊：

1. `/api/test-ollama` 的完整 JSON 輸出
2. 開發伺服器終端的錯誤訊息
3. `curl http://localhost:11434/api/tags` 的輸出
4. `.env.local` 的內容 (隱藏敏感資訊)

## 🎯 測試 API 直接呼叫

```bash
# 測試 RAG Chat API
curl -X POST http://localhost:3000/api/rag/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好",
    "user_location": {"lat": 25.0330, "lng": 121.5654}
  }'
```

**預期結果:** 應該返回 JSON，包含 `response` 欄位
