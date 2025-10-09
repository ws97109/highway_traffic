---
name: admin-ai-model
status: backlog
created: 2025-10-07T07:40:51Z
progress: 0%
prd: .claude/prds/admin-ai-model.md
github: [Will be updated when synced to GitHub]
---

# Epic: 管理者介面 AI 模型

## Overview

實作管理者專用的 AI 對話與決策支援系統,使用 Ollama qwen2.5:7b 模型,透過客製化提示詞提供系統層級的交通管理建議。本 epic 包含建立獨立的後端 API 服務和整合現有的前端管理介面。

**核心技術方案:**
- 複用現有的 OllamaClient 架構,建立管理者專用版本
- 使用 FastAPI 建立新的 `/api/admin/chat` 和 `/api/admin/ai-recommendations` 端點
- 設計針對管理決策的系統提示詞模板
- 整合多個資料源(交通指標、震波、預測)提供完整上下文
- 前端透過現有的 RAGChatbot 元件呼叫新 API

## Architecture Decisions

### AD1: 複用 vs 獨立實作
**決策:** 建立獨立的 `admin_chat.py` 路由,但複用 `ollama_client.py` 的底層邏輯

**理由:**
- 駕駛者與管理者的提示詞完全不同,需要獨立管理
- 底層 Ollama 通訊邏輯相同,避免重複程式碼
- 未來可能需要不同的配置(超時、溫度參數等)
- 保持程式碼清晰和職責分離

### AD2: 提示詞管理方式
**決策:** 將提示詞硬編碼在程式碼中,而非外部配置檔

**理由:**
- 簡化實作,減少配置管理複雜度
- 提示詞與業務邏輯緊密耦合,不需要頻繁更新
- 版本控制更簡單
- 未來如需動態配置可輕鬆重構

### AD3: 資料整合策略
**決策:** 在 API 端點內部主動獲取資料,而非要求前端傳遞完整資料

**理由:**
- 減少前端複雜度和資料傳輸量
- 確保資料新鮮度(即時獲取最新資料)
- 後端有完整控制權決定需要哪些資料
- 更好的錯誤處理和降級策略

### AD4: AI 建議生成機制
**決策:** 使用規則引擎結合 AI 生成,而非純 AI 生成

**理由:**
- 規則引擎確保建議的結構化和可執行性
- AI 負責生成描述、理由和預期效果的文字
- 結合兩者優勢:規則的可靠性 + AI 的靈活性
- 更容易測試和驗證

## Technical Approach

### Backend Services

#### 新增模組: `api/routes/admin_chat.py`

**主要功能:**
1. **POST /api/admin/chat** - 管理者對話端點
   - 接收管理員問題
   - 整合系統資料(traffic, shockwave, prediction)
   - 使用管理者提示詞生成回應
   - 維護對話歷史(記憶體)

2. **POST /api/admin/ai-recommendations** - AI 建議生成端點
   - 分析當前交通狀況
   - 應用決策規則引擎
   - 使用 AI 生成建議描述
   - 返回結構化建議列表

3. **GET /api/admin/ollama-status** - 服務狀態檢查
   - 檢查 Ollama 連線
   - 驗證模型可用性
   - 返回服務健康狀態

**關鍵實作細節:**
```python
# 管理者系統提示詞
ADMIN_SYSTEM_PROMPT = """
你是專業的高速公路交通管制決策助手...
[完整提示詞見 PRD]
"""

# 資料整合函數
async def gather_system_data():
    # 並行獲取多個資料源
    traffic_data = await fetch_traffic_metrics()
    shockwaves = await fetch_active_shockwaves()
    predictions = await fetch_predictions()
    return build_context(traffic_data, shockwaves, predictions)

# 建議生成邏輯
def generate_recommendation_rules(system_data):
    # 規則引擎:根據資料判斷需要什麼類型的建議
    if high_congestion_detected(system_data):
        return create_congestion_recommendations()
    if multiple_shockwaves(system_data):
        return create_shockwave_recommendations()
    # ...
```

#### 複用模組: `train_model/models/ollama_client.py`

**使用方式:**
- 直接使用現有的 `OllamaClient` 類別
- 透過 `generate_response()` 方法與 Ollama 通訊
- 傳入客製化的 `system_prompt` 參數

**優勢:**
- 無需重複實作 HTTP 通訊邏輯
- 繼承現有的錯誤處理和重試機制
- 保持程式碼 DRY 原則

### Frontend Integration

**修改項目:** 最小化前端變更

1. **RAGChatbot 元件** (已存在)
   - 新增 `mode` prop: 'driver' | 'admin'
   - 根據 mode 呼叫不同的 API 端點
   - 其他 UI 邏輯保持不變

2. **ControlCenter.tsx** (已存在)
   - AI 建議面板已經存在
   - 更新 API 呼叫從模擬資料改為真實 API
   - 從 `/api/admin/recommended-actions` 改為 `/api/admin/ai-recommendations`

**前端變更極小,主要是切換 API URL。**

### Data Flow

```
1. 使用者在 ControlCenter 點擊「AI 智能助手」
   ↓
2. 開啟 RAGChatbot(mode='admin')
   ↓
3. 使用者輸入問題
   ↓
4. 前端呼叫 POST /api/admin/chat
   ↓
5. 後端 gather_system_data() 獲取即時資料
   ↓
6. 建構包含系統資料的提示詞
   ↓
7. 呼叫 OllamaClient.generate_response()
   ↓
8. Ollama 返回 AI 回應
   ↓
9. 後端格式化回應並返回前端
   ↓
10. RAGChatbot 顯示回應
```

## Implementation Strategy

### 開發順序

**為何這個順序:**
- 先建立核心 API,確保後端邏輯正確
- 再整合資料源,驗證資料流
- 最後前端整合,因為前端已基本完成
- 測試貫穿整個過程

### 風險緩解

1. **Ollama 服務不穩定**
   - 實作 try-catch 和優雅降級
   - 返回友善錯誤訊息而非崩潰
   - 添加健康檢查端點

2. **AI 回應品質不佳**
   - 迭代優化提示詞
   - 收集真實管理員反饋
   - 提供範例問題引導使用者

3. **效能問題**
   - 使用 asyncio 並行獲取資料
   - 限制上下文長度避免超時
   - 添加超時保護

### 測試方法

1. **單元測試** (使用 pytest)
   - 測試資料整合函數
   - 測試提示詞建構邏輯
   - Mock Ollama 回應

2. **整合測試**
   - 使用真實 Ollama 服務
   - 測試完整 API 流程
   - 驗證資料格式

3. **手動測試**
   - 管理員真實場景測試
   - 評估 AI 回應品質
   - 檢查使用者體驗

## Task Breakdown Preview

本 epic 將分解為以下 **8 個任務**:

- [ ] **Task 1**: 建立 admin_chat.py API 路由檔案與基礎結構
  - 建立檔案和 APIRouter
  - 定義 Pydantic 資料模型
  - 註冊路由到主 app

- [ ] **Task 2**: 設計並實作管理者系統提示詞
  - 撰寫完整的系統提示詞
  - 實作提示詞建構函數
  - 支援動態資料注入

- [ ] **Task 3**: 實作資料整合層
  - 建立 gather_system_data() 函數
  - 整合 traffic/shockwave/prediction APIs
  - 實作錯誤處理和降級邏輯

- [ ] **Task 4**: 實作 /api/admin/chat 端點
  - 接收使用者問題
  - 呼叫資料整合層
  - 使用 OllamaClient 生成回應
  - 維護對話歷史

- [ ] **Task 5**: 實作 AI 建議規則引擎
  - 定義決策規則(何時建議匝道管制等)
  - 實作規則評估邏輯
  - 生成建議結構

- [ ] **Task 6**: 實作 /api/admin/ai-recommendations 端點
  - 應用規則引擎
  - 使用 AI 生成建議文字
  - 返回結構化建議列表

- [ ] **Task 7**: 前端整合
  - 更新 RAGChatbot 支援 admin mode
  - 更新 ControlCenter AI 建議面板 API 呼叫
  - 測試使用者流程

- [ ] **Task 8**: 測試與優化
  - 撰寫單元測試
  - 執行整合測試
  - 效能測試與優化
  - 管理員 UAT

## Dependencies

### 外部依賴
- **Ollama Service** (localhost:11434) - 必須運行且模型可用
- **qwen2.5:7b 模型** - 必須已下載

### 內部依賴
- **現有 API 端點**:
  - `/api/admin/system-status`
  - `/api/admin/traffic-metrics`
  - `/api/shockwave/active`
  - `/api/prediction/*`

- **現有模組**:
  - `train_model/models/ollama_client.py`
  - `train_model/utils/config_manager.py`

- **前端元件**:
  - `ControlCenter.tsx`
  - `RAGChatbot.tsx`

### 無阻塞依賴
- 所有必要的基礎設施已存在
- 可立即開始開發

## Success Criteria (Technical)

### 功能驗收
- ✅ POST /api/admin/chat 正確回應管理員問題
- ✅ POST /api/admin/ai-recommendations 返回結構化建議
- ✅ 對話歷史正確保留(最近 5 輪)
- ✅ 錯誤情況優雅處理(Ollama 不可用、資料源失敗)

### 效能基準
- ✅ 非流式回應時間 < 5 秒 (95% 請求)
- ✅ 支援 10 個並發請求不降級
- ✅ API 錯誤率 < 1%

### 品質標準
- ✅ AI 回應使用繁體中文
- ✅ 回應包含具體資料引用(站點名稱、數值)
- ✅ 建議包含優先級、成本、效益資訊
- ✅ 程式碼有完整註釋和錯誤處理

### 使用者驗收
- ✅ 管理員能成功完成決策諮詢
- ✅ AI 語氣專業且易懂
- ✅ 建議具有可執行性
- ✅ 聊天介面流暢無卡頓

## Estimated Effort

### 總體時程
- **預估工時**: 3-4 個工作天
- **關鍵路徑**: Task 1-4 (必須依序完成)
- **可並行**: Task 5-6 可在 Task 4 完成後並行開發

### 任務時間分配
- Task 1: 2 小時 (基礎結構)
- Task 2: 3 小時 (提示詞設計需迭代)
- Task 3: 4 小時 (資料整合較複雜)
- Task 4: 4 小時 (核心對話邏輯)
- Task 5: 3 小時 (規則引擎)
- Task 6: 3 小時 (建議端點)
- Task 7: 2 小時 (前端變更最小)
- Task 8: 4 小時 (測試完整)

**總計**: 25 小時 ≈ 3-4 天

### 資源需求
- **開發者**: 1 名熟悉 Python/FastAPI 的後端工程師
- **測試者**: 1 名管理員用戶參與 UAT
- **環境**: Ollama 服務運行的開發環境

### 里程碑
- **Day 1 EOD**: Task 1-3 完成,資料整合就緒
- **Day 2 EOD**: Task 4 完成,對話功能可測試
- **Day 3 EOD**: Task 5-6 完成,建議功能可測試
- **Day 4**: Task 7-8 完成,前端整合並通過測試

## Notes

### 簡化策略
本 epic 已經過優化,聚焦於核心功能:
1. **複用**現有的 OllamaClient,避免重複開發
2. **最小化**前端變更,利用現有元件
3. **務實**的規則引擎,而非複雜的 AI Agent
4. **記憶體**對話歷史,避免資料庫複雜度

### 未來擴展
如需要,可輕鬆擴展:
- 對話歷史持久化(加入資料庫)
- 流式回應(使用 SSE)
- 多語言支援(擴展提示詞)
- 進階規則引擎(更多決策邏輯)

### 技術債務
無顯著技術債務,架構清晰且可維護。

---

**Epic 建立時間**: 2025-10-07T07:40:51Z
**預計完成時間**: 2025-10-11
**負責團隊**: Backend Development Team
