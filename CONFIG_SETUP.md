# 配置管理說明

## 概述

此專案使用環境變數來保護敏感資訊，確保隱私資料不會被提交到版本控制系統中。

## 檔案結構

- `.env` - 包含實際的敏感資訊（已在 .gitignore 中排除）
- `.env.example` - 環境變數範例檔案
- `src/config_loader.py` - 配置載入器，處理環境變數替換
- `data/config/system_config.json` - 主要配置檔案，使用環境變數佔位符

## 設定步驟

### 1. 複製環境變數範例檔案
```bash
cp .env.example .env
```

### 2. 編輯 .env 檔案
填入您的實際憑證：

```bash
# TDX API 憑證設定
TDX_CLIENT_ID=your_actual_client_id
TDX_CLIENT_SECRET=your_actual_client_secret

# 電子郵件設定
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM_ADDRESS=your_email@gmail.com

# Google Maps API 設定
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

### 3. 在程式中使用配置載入器

```python
from config_loader import load_config_with_env

# 載入配置
config = load_config_with_env('data/config/system_config.json')

# 獲取配置值
email_username = config['warning_config.json']['email']['username']
api_key = config['location_config.json']['google_maps']['api_key']
```

## 環境變數佔位符格式

在配置檔案中使用 `${VARIABLE_NAME}` 格式來引用環境變數：

```json
{
  "email": {
    "username": "${EMAIL_USERNAME}",
    "password": "${EMAIL_PASSWORD}"
  }
}
```

## 安全性注意事項

1. **永遠不要將 .env 檔案提交到版本控制**
2. 使用應用程式專用密碼而不是個人密碼
3. 定期輪換 API 金鑰和密碼
4. 在生產環境中使用更安全的憑證管理系統

## 測試配置載入器

運行以下命令來測試配置是否正確載入：

```bash
python src/config_loader.py
```

如果一切正常，您應該看到 "✅ 配置載入成功！" 的訊息。
