"""
RAG 整合 API - 使用 train_model 中的完整 RAG 系統
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sys
from pathlib import Path
from datetime import datetime
import asyncio

# 導入 train_model 中的 RAG 組件
train_model_path = str(Path(__file__).parent.parent.parent / "train_model")
sys.path.insert(0, train_model_path)

try:
    from train_model.models.ollama_client import OllamaClient, RAGOllamaChat
    from train_model.embeddings.vector_store import VectorStore, RAGRetriever
    RAG_AVAILABLE = True
except Exception as e:
    print(f"⚠️ 無法導入 RAG 模組: {e}")
    RAG_AVAILABLE = False

router = APIRouter()

# 全域變數
_rag_system = None
_initialization_lock = asyncio.Lock()

# ==================== API Models ====================

class RAGChatRequest(BaseModel):
    message: str
    traffic_data: Optional[Dict[str, Any]] = None
    shockwave_data: Optional[Dict[str, Any]] = None
    user_location: Optional[Dict[str, float]] = None
    use_rag: bool = True

class RAGChatResponse(BaseModel):
    response: str
    sources: List[str] = []
    confidence_score: float
    model: str
    timestamp: str
    rag_enabled: bool

# ==================== RAG System Initialization ====================

async def get_rag_system():
    """獲取或初始化 RAG 系統（單例模式）"""
    global _rag_system

    if _rag_system is not None:
        return _rag_system

    async with _initialization_lock:
        # 雙重檢查
        if _rag_system is not None:
            return _rag_system

        if not RAG_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="RAG 系統模組不可用，請檢查 train_model 目錄"
            )

        try:
            print("🚀 正在初始化 RAG 系統...")

            # 初始化向量存儲
            vector_store = VectorStore()
            retriever = RAGRetriever(vector_store)

            # 初始化 Ollama 客戶端
            ollama_client = OllamaClient()

            # 檢查連接
            if not await ollama_client.check_connection():
                raise Exception("Ollama 服務連接失敗，請確保 Ollama 正在運行")

            # 初始化 RAG 聊天系統
            _rag_system = RAGOllamaChat(ollama_client, retriever)

            print("✅ RAG 系統初始化完成")
            return _rag_system

        except Exception as e:
            error_msg = f"RAG 系統初始化失敗: {str(e)}"
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=503,
                detail=error_msg
            )

# ==================== 繁體中文轉換 ====================

def ensure_traditional_chinese(text: str) -> str:
    """確保文本為繁體中文"""
    # 簡繁對照表
    conv_table = {
        '车': '車', '线': '線', '为': '為', '国': '國', '时': '時',
        '应': '應', '间': '間', '发': '發', '经': '經', '过': '過',
        '这': '這', '还': '還', '没': '沒', '现': '現', '长': '長',
        '紧': '緊', '进': '進', '运': '運', '转': '轉', '传': '傳',
        '响': '響', '围': '圍', '选': '選', '环': '環', '联': '聯',
        '结': '結', '标': '標', '确': '確', '记': '記', '资': '資',
        '驾': '駕', '驶': '駛', '险': '險', '紧急': '緊急',
        '当前': '當前', '实时': '即時', '即时': '即時',
        '壅塞': '壅塞', '畅通': '暢通', '缓慢': '緩慢',
        '国道': '國道', '高速': '高速', '公路': '公路'
    }

    result = text
    for simp, trad in conv_table.items():
        result = result.replace(simp, trad)

    return result

# ==================== 交通數據處理 ====================

def build_traffic_context(
    message: str,
    traffic_data: Optional[Dict[str, Any]] = None,
    shockwave_data: Optional[Dict[str, Any]] = None,
    user_location: Optional[Dict[str, float]] = None
) -> str:
    """構建交通情境提示"""

    context = f"【用戶問題】{message}\n\n"

    # 即時交通數據
    if traffic_data and traffic_data.get('stations'):
        stations = traffic_data['stations']
        total_stations = len(stations)
        if total_stations > 0:
            avg_speed = sum(s.get('speed', 0) for s in stations) / total_stations
            congested = [s for s in stations if s.get('speed', 100) < 50]

            context += "【即時交通狀況】\n"
            context += f"監測站點：{total_stations}個\n"
            context += f"平均車速：{avg_speed:.1f} km/h\n"
            if congested:
                context += f"壅塞站點：{len(congested)}個（車速<50km/h）\n"
            context += "\n"

    # 震波數據
    if shockwave_data and shockwave_data.get('shockwaves'):
        shockwaves = shockwave_data['shockwaves']
        if shockwaves:
            context += f"【交通震波警報】偵測到 {len(shockwaves)} 個震波事件\n"
            for i, shock in enumerate(shockwaves[:3], 1):
                context += f"震波{i}：{shock.get('location_name', '未知')} "
                context += f"(強度{shock.get('intensity', 0)}/10, "
                context += f"持續{shock.get('shock_duration', 0)}分鐘)\n"
            context += "\n"

    # 用戶位置
    if user_location:
        context += f"【用戶位置】緯度 {user_location.get('lat')}, 經度 {user_location.get('lng')}\n\n"

    # 指示使用繁體中文
    context += "【重要】請使用繁體中文回答所有問題。\n\n"

    return context

# ==================== API Endpoints ====================

@router.post("/chat", response_model=RAGChatResponse)
async def rag_chat(request: RAGChatRequest):
    """
    RAG 增強聊天端點
    整合 train_model 的完整 RAG 系統
    """
    try:
        # 獲取 RAG 系統
        rag_system = await get_rag_system()

        # 構建交通情境
        enhanced_message = build_traffic_context(
            request.message,
            request.traffic_data,
            request.shockwave_data,
            request.user_location
        )

        # 使用 RAG 系統生成回應
        ai_response = await rag_system.chat(
            enhanced_message,
            use_rag=request.use_rag
        )

        # 繁體中文轉換
        ai_response = ensure_traditional_chinese(ai_response)

        # 獲取對話統計（包含來源資訊）
        stats = rag_system.get_conversation_stats()

        # 計算信心分數
        confidence_score = 0.5  # 基礎分數
        if request.use_rag and stats.get('rag_usage_rate', 0) > 0:
            confidence_score += 0.3  # RAG 使用加成
        if request.traffic_data:
            confidence_score += 0.1  # 即時數據加成
        if request.shockwave_data:
            confidence_score += 0.1  # 震波數據加成
        confidence_score = min(1.0, confidence_score)

        # 提取來源（從最近的對話中）
        sources = []
        if rag_system.conversation_history:
            last_conv = rag_system.conversation_history[-1]
            if last_conv.get('context_used'):
                sources = ["使用 RAG 知識庫檢索相關交通資訊"]

        return RAGChatResponse(
            response=ai_response,
            sources=sources,
            confidence_score=confidence_score,
            model="Ollama + RAG (train_model)",
            timestamp=datetime.now().isoformat(),
            rag_enabled=request.use_rag
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ RAG Chat Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"RAG 對話失敗: {str(e)}"
        )

@router.get("/status")
async def check_rag_status():
    """檢查 RAG 系統狀態"""
    try:
        if not RAG_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "RAG 模組不可用",
                "rag_enabled": False
            }

        # 嘗試獲取 RAG 系統
        try:
            rag_system = await get_rag_system()
            stats = rag_system.get_conversation_stats()

            return {
                "status": "healthy",
                "rag_enabled": True,
                "ollama_connected": True,
                "conversation_count": stats.get('total_conversations', 0),
                "rag_usage_rate": stats.get('rag_usage_rate', 0),
                "model": "Ollama + Vector Store (ChromaDB)",
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
                "message": str(e),
                "rag_enabled": False,
                "ollama_connected": False
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/clear-history")
async def clear_conversation_history():
    """清除對話歷史"""
    try:
        rag_system = await get_rag_system()
        rag_system.clear_history()
        return {"message": "對話歷史已清除"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"清除歷史失敗: {str(e)}"
        )

@router.get("/stats")
async def get_conversation_stats():
    """獲取對話統計"""
    try:
        rag_system = await get_rag_system()
        stats = rag_system.get_conversation_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"獲取統計失敗: {str(e)}"
        )
