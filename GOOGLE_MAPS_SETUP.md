# Google Maps API 設定指南

## 🗝️ 取得 Google Maps API 金鑰

1. **前往 Google Cloud Console**
   - 開啟 https://console.cloud.google.com/
   - 登入你的 Google 帳戶

2. **創建新專案或選擇現有專案**
   - 點擊專案選擇器
   - 創建新專案或選擇現有專案

3. **啟用必要的 API**
   - 前往「API 和服務」>「程式庫」
   - 搜尋並啟用以下 API：
     - Maps JavaScript API
     - Places API
     - Directions API
     - Geocoding API

4. **創建 API 金鑰**
   - 前往「API 和服務」>「憑證」
   - 點擊「建立憑證」>「API 金鑰」
   - 複製產生的 API 金鑰

5. **設定 API 金鑰限制（建議）**
   - 點擊剛創建的 API 金鑰
   - 設定「應用程式限制」為「HTTP 參照網址」
   - 新增允許的網址：
     - `http://localhost:3000/*`
     - `http://127.0.0.1:3000/*`
     - 你的部署域名
   - 設定「API 限制」，選擇上述啟用的 API

## 🔧 配置環境變數

在 `frontend/.env.local` 文件中設定：

```bash
# 替換 YOUR_ACTUAL_API_KEY 為你的真實 API 金鑰
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=YOUR_ACTUAL_API_KEY
```

## 🚀 重新啟動應用

設定完成後，重新啟動前端應用：

```bash
cd frontend
npm run dev
```

## 💡 臨時解決方案

如果暫時無法取得 API 金鑰，系統會自動使用模擬模式：
- 地圖功能將顯示替代內容
- 地址搜尋使用模擬資料
- 路線規劃提供預設建議

## 🔍 驗證設定

設定完成後，開啟瀏覽器開發者工具：
- 如果看到「✅ Google Services 初始化成功」表示設定正確
- 如果看到警告訊息，請檢查 API 金鑰設定
