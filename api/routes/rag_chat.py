"""
RAG (Retrieval-Augmented Generation) Chat API
整合 train_model 中的完整 RAG 系統
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sys
from pathlib import Path
from datetime import datetime

# 導入 train_model 中的 RAG 組件
train_model_path = str(Path(__file__).parent.parent.parent / "train_model")
sys.path.insert(0, train_model_path)

from train_model.models.ollama_client import OllamaClient, RAGOllamaChat
from train_model.embeddings.vector_store import VectorStore, RAGRetriever

router = APIRouter()

# 全域變數存儲 RAG 系統
rag_system = None

async def initialize_rag_system():
    """初始化 RAG 系統"""
    global rag_system

    if rag_system is not None:
        return rag_system

    try:
        # 初始化向量存儲
        vector_store = VectorStore()
        retriever = RAGRetriever(vector_store)

        # 初始化 Ollama 客戶端
        ollama_client = OllamaClient()

        # 檢查連接
        if not await ollama_client.check_connection():
            raise Exception("Ollama 服務連接失敗")

        # 初始化 RAG 聊天系統
        rag_system = RAGOllamaChat(ollama_client, retriever)

        return rag_system
    except Exception as e:
        print(f"❌ RAG 系統初始化失敗: {e}")
        raise

# 台灣交通知識庫（補充資料，用於檢查和備用）
TRAFFIC_KNOWLEDGE_BASE = [
    {
        "id": "highway_1_overview",
        "category": "高速公路資訊",
        "content": "國道一號（中山高速公路）北起基隆，南至高雄，全長372.8公里，是台灣第一條高速公路。主要路段包括：基隆-台北、台北-新竹、新竹-台中、台中-嘉義、嘉義-高雄。",
        "keywords": ["國道一號", "中山高速公路", "基隆", "高雄", "全長"]
    },
    {
        "id": "highway_3_overview",
        "category": "高速公路資訊",
        "content": "國道三號（福爾摩沙高速公路）北起基隆，南至屏東，全長431.5公里。主要路段包括：基隆-台北、台北-桃園、桃園-新竹、新竹-台中、台中-南投、南投-嘉義、嘉義-台南、台南-高雄、高雄-屏東。",
        "keywords": ["國道三號", "福爾摩沙高速公路", "基隆", "屏東", "全長"]
    },
    {
        "id": "rest_area_north",
        "category": "休息站資訊",
        "content": "北部主要休息站：泰安服務區（國道三號）、湖口服務區（國道一號）、清水服務區（國道三號）。泰安服務區位於苗栗縣，提供餐飲、加油、休息設施。湖口服務區位於新竹縣，是國道一號重要休息點。",
        "keywords": ["休息站", "泰安", "湖口", "清水", "服務區", "北部"]
    },
    {
        "id": "rest_area_central",
        "category": "休息站資訊",
        "content": "中部主要休息站：西螺服務區（國道一號）、南投服務區（國道三號）、清水服務區（國道三號）。西螺服務區位於雲林縣，提供24小時服務。南投服務區位於南投縣，是國道三號中部重要休息點。",
        "keywords": ["休息站", "西螺", "南投", "清水", "服務區", "中部"]
    },
    {
        "id": "rest_area_south",
        "category": "休息站資訊",
        "content": "南部主要休息站：新營服務區（國道一號）、關廟服務區（國道三號）、東山服務區（國道三號）、仁德服務區（國道一號）。新營服務區位於台南市，提供完整餐飲設施。關廟服務區位於台南市關廟區。",
        "keywords": ["休息站", "新營", "關廟", "東山", "仁德", "服務區", "南部"]
    },
    {
        "id": "congestion_wugu_linkou",
        "category": "壅塞熱點",
        "content": "五股林口路段（國道一號）是北部最容易壅塞的路段之一。主要壅塞時段：平日上午7-9點、下午5-7點。建議替代路線：走國道三號轉國道一號、或走台61西濱快速道路、或走台65快速道路轉國道一號。",
        "keywords": ["五股", "林口", "壅塞", "替代路線", "國道一號", "尖峰時段"]
    },
    {
        "id": "congestion_yangmei",
        "category": "壅塞熱點",
        "content": "楊梅路段（國道一號）經常在假日出現壅塞，特別是北上方向。主要壅塞時段：週五下午3-8點、週日下午3-晚上10點。建議替代路線：改走國道三號經關西接回國道一號，或提早/延後出發避開尖峰。",
        "keywords": ["楊梅", "壅塞", "假日", "國道一號", "替代路線"]
    },
    {
        "id": "congestion_taichung",
        "category": "壅塞熱點",
        "content": "台中路段（國道一號王田-大雅段）是中部主要壅塞路段。主要壅塞時段：平日上下班時段、假日午後。建議替代路線：改走國道三號、或走台74線中彰快速道路、或走台63中投快速道路。",
        "keywords": ["台中", "王田", "大雅", "壅塞", "國道一號", "中彰快速道路"]
    },
    {
        "id": "shockwave_definition",
        "category": "交通衝擊波知識",
        "content": "交通衝擊波是指車流中突然的減速波動，會向後傳播造成壅塞。常見原因包括：前方事故、車道縮減、匝道車輛匯入、駕駛急煞車。衝擊波會以15-25公里/小時的速度向後傳播，影響範圍可達數公里。",
        "keywords": ["交通衝擊波", "減速", "壅塞", "傳播速度", "影響範圍"]
    },
    {
        "id": "shockwave_response",
        "category": "交通衝擊波知識",
        "content": "遇到交通衝擊波的建議應對方式：1️⃣ 提前減速，保持安全車距（至少50公尺）2️⃣ 避免急煞車，緩慢減速 3️⃣ 考慮改走替代路線或就近休息站等待 4️⃣ 如衝擊波強度高（>7/10），建議延後30分鐘以上出發 5️⃣ 使用即時路況App監控衝擊波移動",
        "keywords": ["交通衝擊波", "應對", "安全車距", "替代路線", "即時路況"]
    },
    {
        "id": "speed_limit_highway",
        "category": "行車規範",
        "content": "高速公路速限規定：小型車最高速限110公里/小時、最低速限60公里/小時。大型車最高速限90公里/小時。外側車道（內側車道）為超車道，非超車時應回到中線或內側車道。雨天應減速10-20公里/小時，濃霧時速限40公里/小時。",
        "keywords": ["速限", "高速公路", "小型車", "大型車", "超車道", "雨天"]
    },
    {
        "id": "safe_distance",
        "category": "行車規範",
        "content": "安全跟車距離計算：在高速公路上，安全車距（公尺）= 車速（公里/小時）- 20。例如時速100公里時，應保持80公尺以上車距。雨天應加倍車距。衝擊波影響區域建議保持至少100公尺以上車距，並隨時準備減速。",
        "keywords": ["安全車距", "跟車距離", "高速公路", "衝擊波", "雨天"]
    },
    {
        "id": "etag_system",
        "category": "系統資訊",
        "content": "eTag是台灣高速公路電子收費系統（ETC）使用的車載單元，採用RFID射頻識別技術。全台設有測站監測車流，包含速度、流量、密度等數據。這些資料可用於交通衝擊波偵測和路況預測。",
        "keywords": ["eTag", "ETC", "電子收費", "RFID", "測站", "車流監測"]
    },
    {
        "id": "weather_impact",
        "category": "天氣影響",
        "content": "天氣對高速公路的影響：豪大雨時車速應降至60公里/小時以下，濃霧時應開霧燈並降至40公里/小時。強風特報時，大型車、機車應避免上國道。颱風天建議避免非必要行駛。雨天衝擊波傳播速度較慢但影響時間較長。",
        "keywords": ["天氣", "豪雨", "濃霧", "強風", "颱風", "安全駕駛"]
    },
    {
        "id": "peak_hours",
        "category": "尖峰時段",
        "content": "國道尖峰時段：平日上午7:00-9:00（北上南下皆塞）、下午17:00-19:00（北上南下皆塞）。週五下午15:00起南下開始塞車，週日下午15:00起北��開始塞車。連續假期第一天與最後一天全天壅塞。建議避開尖峰時段或提早2-3小時出發。",
        "keywords": ["尖峰時段", "上班時間", "下班時間", "週五", "週日", "連假"]
    }
]

# 簡單的向量存儲（實際應用應使用 ChromaDB 或 FAISS）
class SimpleVectorStore:
    def __init__(self):
        self.documents = []
        self.embeddings = []

    def add_documents(self, documents: List[Dict]):
        """添加文件到向量存儲"""
        self.documents = documents
        # 在實際應用中，這裡應該呼叫嵌入模型生成向量
        # 暫時使用簡單的關鍵詞匹配

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """根據查詢檢索最相關的文件"""
        # 簡單的關鍵詞匹配（實際應用應使用向量相似度）
        query_lower = query.lower()

        # 計算每個文件的相關性分數
        scores = []
        for doc in self.documents:
            score = 0
            # 關鍵詞匹配
            for keyword in doc.get('keywords', []):
                if keyword.lower() in query_lower:
                    score += 2
            # 內容匹配
            if any(word in doc['content'].lower() for word in query_lower.split()):
                score += 1
            scores.append(score)

        # 獲取 top_k 個最相關的文件
        top_indices = np.argsort(scores)[-top_k:][::-1]
        results = [self.documents[i] for i in top_indices if scores[i] > 0]

        return results

# 初始化向量存儲
vector_store = SimpleVectorStore()
vector_store.add_documents(TRAFFIC_KNOWLEDGE_BASE)

# ==================== API Models ====================

class RAGChatRequest(BaseModel):
    message: str
    traffic_data: Optional[Dict[str, Any]] = None
    shockwave_data: Optional[Dict[str, Any]] = None
    user_location: Optional[Dict[str, float]] = None
    use_rag: bool = True  # 是否啟用 RAG

class RAGChatResponse(BaseModel):
    response: str
    sources: List[str]  # RAG 檢索到的來源
    confidence_score: float  # 信心分數
    model: str
    timestamp: str

# ==================== 繁體中文轉換 ====================

def ensure_traditional_chinese(text: str) -> str:
    """
    確保文本為繁體中文
    使用 OpenCC 或內建轉換表
    """
    # 簡單的簡繁對照表（實際應用建議使用 OpenCC library）
    simplified_to_traditional = {
        '车': '車', '线': '線', '为': '為', '国': '國', '时': '時',
        '应': '應', '间': '間', '发': '發', '经': '經', '过': '過',
        '这': '這', '还': '還', '没': '沒', '现': '現', '长': '長',
        '认': '認', '业': '業', '产': '產', '务': '務', '价': '價',
        '质': '質', '级': '級', '检': '檢', '测': '測', '给': '給',
        '紧': '緊', '进': '進', '运': '運', '转': '轉', '传': '傳',
        '响': '響', '围': '圍', '选': '選', '环': '環', '联': '聯',
        '结': '結', '标': '標', '确': '確', '记': '記', '资': '資',
        '获': '獲', '设': '設', '场': '場', '显': '顯', '态': '態',
        '继': '繼', '维': '維', '总': '總', '压': '壓', '优': '優',
        '节': '節', '满': '滿', '达': '達', '强': '強', '区': '區',
        '铁': '鐵', '拥': '擁', '堵': '堵', '阻': '阻', '驾': '駕',
        '驶': '駛', '险': '險', '紧急': '緊急', '建议': '建議',
        '情况': '情況', '时间': '時間', '车辆': '車輛', '交通': '交通',
        '路线': '路線', '国道': '國道', '高速': '高速', '公路': '公路',
        '壅塞': '壅塞', '畅通': '暢通', '缓慢': '緩慢', '预测': '預測',
        '监测': '監測', '检测': '檢測', '观察': '觀察', '变化': '變化',
        '影响': '影響', '范围': '範圍', '选择': '選擇', '继续': '繼續',
        '维持': '維持', '调整': '調整', '优化': '優化', '确保': '確保',
        '获取': '獲取', '显示': '顯示', '设置': '設置', '区域': '區域',
        '当前': '當前', '实时': '即時', '即时': '即時', '历史': '歷史',
        '统计': '統計', '评估': '評估', '预警': '預警', '紧急情况': '緊急情況'
    }

    result = text
    for simp, trad in simplified_to_traditional.items():
        result = result.replace(simp, trad)

    return result

# ==================== RAG Chat Endpoint ====================

@router.post("/chat", response_model=RAGChatResponse)
async def rag_chat(request: RAGChatRequest):
    """
    RAG 增強的聊天端點
    使用向量檢索增強生成，提供更準確的交通建議
    """
    try:
        # 1️⃣ 向量檢索：從知識庫中檢索相關資訊
        relevant_docs = []
        sources = []

        if request.use_rag:
            relevant_docs = vector_store.search(request.message, top_k=3)
            sources = [doc['content'] for doc in relevant_docs]
            print(f"🔍 RAG 檢索到 {len(relevant_docs)} 個相關文件")

        # 2️⃣ 構建增強的 Prompt
        knowledge_context = ""
        if relevant_docs:
            knowledge_context = "\n【知識庫資訊】\n"
            for i, doc in enumerate(relevant_docs, 1):
                knowledge_context += f"{i}. {doc['content']}\n"

        # 3️⃣ 交通數據摘要
        traffic_summary = ""
        if request.traffic_data and request.traffic_data.get('stations'):
            stations = request.traffic_data['stations']
            total_stations = len(stations)
            avg_speed = sum(s.get('speed', 0) for s in stations) / total_stations if total_stations > 0 else 0
            congested = [s for s in stations if s.get('speed', 100) < 50]

            traffic_summary = f"\n【即時路況數據】\n"
            traffic_summary += f"監測站點：{total_stations}個\n"
            traffic_summary += f"平均車速：{avg_speed:.1f} km/h\n"
            if congested:
                traffic_summary += f"壅塞站點：{len(congested)}個（車速<50km/h）\n"

        # 4️⃣ 衝擊波數據摘要
        shockwave_summary = ""
        if request.shockwave_data and request.shockwave_data.get('shockwaves'):
            shockwaves = request.shockwave_data['shockwaves']
            if shockwaves:
                shockwave_summary = f"\n【交通衝擊波警報】\n偵測到 {len(shockwaves)} 個衝擊波事件：\n"

                for i, shock in enumerate(shockwaves[:3], 1):  # 只取前3個
                    distance = None
                    if request.user_location:
                        # 計算距離
                        import math
                        R = 6371
                        user_lat = request.user_location.get('lat', 0)
                        user_lng = request.user_location.get('lng', 0)
                        shock_lat = shock.get('latitude', 0)
                        shock_lng = shock.get('longitude', 0)

                        dLat = math.radians(shock_lat - user_lat)
                        dLon = math.radians(shock_lng - user_lng)
                        a = (math.sin(dLat/2) ** 2 +
                             math.cos(math.radians(user_lat)) * math.cos(math.radians(shock_lat)) *
                             math.sin(dLon/2) ** 2)
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                        distance = R * c

                    shockwave_summary += f"衝擊波{i}：{shock.get('location_name', '未知位置')} "
                    shockwave_summary += f"(強度{shock.get('intensity', 0)}/10"
                    if distance:
                        shockwave_summary += f", 距離{distance:.1f}km"
                    shockwave_summary += f", 持續{shock.get('shock_duration', 0)}分鐘)\n"

        # 5️⃣ 用戶位置資訊
        location_info = ""
        if request.user_location:
            location_info = f"\n【用戶位置】\n緯度：{request.user_location.get('lat', '未知')}, 經度：{request.user_location.get('lng', '未知')}\n"

        # 6️⃣ 構建完整的 Prompt
        system_prompt = """你是台灣的專業交通分析專家，專門為駕駛者提供智能建議。

【重要指示】
1. **必須使用繁體中文（Traditional Chinese）回答**，禁止使用簡體字
2. 回答要基於提供的知識庫資訊和即時數據
3. 提供具體可執行的建議（路線名稱、時間、距離）
4. 語氣要專業且友善
5. 簡潔明瞭，重點突出

【回答格式】
🛣️ 路線建議：（具體的替代路線名稱和方向）
⏰ 時間建議：（根據交通衝擊波建議出發時間或等待時間）
🅿️ 休息站建議：（最近的休息站名稱和距離）
⚠️ 安全注意：（車速、車距等具體數值）
"""

        full_prompt = f"""{system_prompt}

{knowledge_context}{traffic_summary}{shockwave_summary}{location_info}

【用戶問題】
{request.message}

請根據以上資訊提供專業建議（必須使用繁體中文，禁止簡體字）："""

        # 7️⃣ 呼叫 Ollama API
        ollama_response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # 降低溫度提高準確性
                    "top_p": 0.9,
                    "num_predict": 400,
                    "stop": ["【", "如果您還有", "祝您一路平安"]
                }
            },
            timeout=30
        )

        if not ollama_response.ok:
            raise HTTPException(
                status_code=500,
                detail=f"Ollama API 錯誤: {ollama_response.status_code}"
            )

        ollama_data = ollama_response.json()
        ai_response = ollama_data.get('response', '抱歉，AI 助手暫時無法回應。')

        # 8️⃣ 確保輸出為繁體中文
        ai_response = ensure_traditional_chinese(ai_response)

        # 9️⃣ 計算信心分數（基於檢索到的文件數量和相關性）
        confidence_score = 0.5  # 基礎分數
        if relevant_docs:
            confidence_score += 0.3  # RAG 加成
        if traffic_summary:
            confidence_score += 0.1  # 即時數據加成
        if shockwave_summary:
            confidence_score += 0.1  # 衝擊波數據加成
        confidence_score = min(1.0, confidence_score)

        return RAGChatResponse(
            response=ai_response,
            sources=sources,
            confidence_score=confidence_score,
            model=OLLAMA_MODEL,
            timestamp=datetime.now().isoformat()
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="AI 回應超時，請稍後再試"
        )
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail=f"無法連接到 AI 服務 ({OLLAMA_BASE_URL})"
        )
    except Exception as e:
        import traceback
        print(f"❌ RAG Chat Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"RAG 對話失敗: {str(e)}"
        )

@router.get("/knowledge-base")
async def get_knowledge_base():
    """獲取知識庫內容"""
    return {
        "total_documents": len(TRAFFIC_KNOWLEDGE_BASE),
        "categories": list(set(doc['category'] for doc in TRAFFIC_KNOWLEDGE_BASE)),
        "documents": TRAFFIC_KNOWLEDGE_BASE
    }

@router.post("/search-knowledge")
async def search_knowledge(query: str, top_k: int = 5):
    """搜索知識庫"""
    results = vector_store.search(query, top_k=top_k)
    return {
        "query": query,
        "results_count": len(results),
        "results": results
    }

@router.get("/status")
async def check_rag_status():
    """檢查 RAG 系統狀態"""
    try:
        # 檢查 Ollama
        ollama_response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        ollama_healthy = ollama_response.ok

        # 檢查知識庫
        kb_count = len(TRAFFIC_KNOWLEDGE_BASE)

        return {
            "status": "healthy" if ollama_healthy else "degraded",
            "ollama_url": OLLAMA_BASE_URL,
            "ollama_model": OLLAMA_MODEL,
            "ollama_connected": ollama_healthy,
            "knowledge_base_documents": kb_count,
            "rag_enabled": True,
            "features": {
                "vector_search": True,
                "traditional_chinese": True,
                "real_time_data": True,
                "shockwave_analysis": True
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "ollama_connected": False
        }
