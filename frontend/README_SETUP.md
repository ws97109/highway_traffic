# 前端環境設定說明

## Google Maps API 設定

### 問題描述
如果看到以下錯誤訊息：
```
⚠️ Google Maps API 金鑰未設定或為預設值
請在 .env.local 中設定正確的 NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
```

### 解決步驟

1. **複製環境變數範例檔案**
   ```bash
   cd frontend
   cp .env.local.example .env.local
   ```

2. **編輯 `.env.local` 檔案**
   將 `your_google_maps_api_key_here` 替換為您的實際 Google Maps API 金鑰：
   ```
   NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
   ```

3. **重新啟動開發服務器**
   ```bash
   npm run dev
   ```

### 如何取得和設定 Google Maps API 金鑰

#### 步驟 1: 建立 Google Cloud 專案
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 確認專案已連結到計費帳戶

#### 步驟 2: 啟用必要的 API 服務
**重要**: 必須啟用以下 4 個 API 服務，否則會出現 `REQUEST_DENIED` 錯誤

1. **Maps JavaScript API** (必須)
   - 🔗 [啟用連結](https://console.cloud.google.com/apis/library/maps-backend.googleapis.com)
   - 用於顯示地圖

2. **Geocoding API** (建議)
   - 🔗 [啟用連結](https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com) 
   - 用於座標轉地址功能
   - **如果未啟用**: 地址會顯示為座標格式

3. **Places API** (建議)
   - 🔗 [啟用連結](https://console.cloud.google.com/apis/library/places-backend.googleapis.com)
   - 用於地點搜尋功能

4. **Directions API** (建議) 
   - 🔗 [啟用連結](https://console.cloud.google.com/apis/library/directions-backend.googleapis.com)
   - 用於路線規劃功能

#### 步驟 3: 建立 API 金鑰
1. 前往「憑證」頁面建立 API 金鑰
2. 建議設定 API 金鑰限制：
   - **應用程式限制**: HTTP 參照網址
   - **API 限制**: 限制為上述 4 個 API

### 注意事項

- `.env.local` 檔案已被 `.gitignore` 排除，不會被提交到版本控制
- 請勿在程式碼中直接寫入 API 金鑰
- 生產環境中請設定適當的 API 金鑰限制

### 驗證設定

成功設定後，您應該在控制台看到：
```
✅ Google Maps API 金鑰已載入: AIzaSyBSrE...
🔑 載入 Google Maps API...
✅ Google Maps API 載入成功
```
