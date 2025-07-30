# 高速公路智慧交通預警決策支援系統 - 快速啟動指南

## 🚀 系統啟動步驟

### 1. 後端API服務器啟動

```bash
# 進入API目錄
cd api

# 啟動FastAPI服務器
python main.py
```

**服務運行地址：** http://localhost:8000
**API文檔：** http://localhost:8000/docs

### 2. 前端應用啟動

```bash
# 進入前端目錄
cd frontend

# 安裝依賴（首次運行）
npm install

# 啟動開發服務器
npm run dev
```

**應用運行地址：** http://localhost:3000

## 📱 系統訪問

### 駕駛者介面
- **URL：** http://localhost:3000/driver
- **功能：** 智慧導航、震波預警、出發時間建議

### 管理者介面  
- **URL：** http://localhost:3000/admin
- **功能：** 系統監控、AI決策支援、大屏管理

## 🔧 環境配置

### 前端環境變數 (.env.local)
```
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_api_key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 後端環境變數
- 系統會自動使用模擬資料模式
- 實際部署時需要配置真實的資料源

## 📊 系統功能驗證

### 1. API健康檢查
```bash
curl http://localhost:8000/health
```

### 2. 震波資料測試
```bash
curl http://localhost:8000/api/shockwave/active
```

### 3. 交通資料測試
```bash
curl http://localhost:8000/api/traffic/current
```

## 🎯 核心功能展示

### 駕駛者功能
- ✅ 即時交通地圖
- ✅ 震波即時警報
- ✅ 智慧出發時間建議
- ✅ 替代路線推薦

### 管理者功能
- ✅ 系統狀態監控
- ✅ AI決策建議
- ✅ 交通指標儀表板
- ✅ 警報管理

## 🔍 故障排除

### 前端無法啟動
1. 確認 Node.js 版本 >= 18
2. 刪除 node_modules 重新安裝
3. 檢查 .env.local 配置

### 後端無法啟動
1. 確認 Python 版本 >= 3.8
2. 安裝必要依賴：`pip install -r requirements.txt`
3. 檢查端口 8000 是否被占用

### API 連接失敗
1. 確認後端服務正在運行
2. 檢查 CORS 設定
3. 驗證 API_BASE_URL 配置

## 📈 系統監控

### 效能指標
- API響應時間 < 200ms
- 前端載入時間 < 3秒
- 資料更新頻率：30秒（震波）/ 5分鐘（交通）

### 系統狀態
- 訪問 http://localhost:8000/api/status 查看系統狀態
- 前端會自動顯示連接狀態

## 🎉 系統已完全就緒！

所有功能已實現並可立即使用：
- 🚗 完整的駕駛者智慧導航系統
- ⚡ 精確的震波預警服務  
- 🎯 AI驅動的出發時間建議
- 📊 專業級管理者監控平台
- 🗺️ 互動式交通地圖
- 📱 響應式多設備支援

**立即體驗革命性的智慧交通管理系統！**
