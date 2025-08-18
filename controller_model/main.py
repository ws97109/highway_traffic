# train_model/main.py
"""
高速公路智能交通系統主服務器
整合 RAG 聊天和交通管理者顧問功能
支援自動檢測並執行訓練流程
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# 導入本地模組
from controller_train_model.controller_advisor import router as controller_router
from controller_train_model.ollama_client import OllamaClient, RAGOllamaChat
from embeddings.vector_store import VectorStore, RAGRetriever

# 導入 API 模型
from pydantic import BaseModel
from typing import Optional, List

# =============================================================================
# API 模型定義
# =============================================================================

class SimpleChatRequest(BaseModel):
    """簡單聊天請求"""
    message: str
    session_id: Optional[str] = None
    include_sources: bool = True

class SimpleChatResponse(BaseModel):
    """簡單聊天回應"""
    response: str
    sources: Optional[List[str]] = []
    confidence: Optional[float] = 0.0
    session_id: str
    processing_time: Optional[float] = None

# =============================================================================
# 全域變數
# =============================================================================

rag_chat_system = None

# =============================================================================
# 自動訓練函數
# =============================================================================

async def auto_setup_rag_system():
    """自動設置 RAG 系統，如需要則執行訓練"""
    global rag_chat_system
    
    print("🔍 檢查 RAG 系統狀態...")
    
    try:
        # 檢查向量資料庫
        vector_store = VectorStore()
        stats = vector_store.get_collection_stats()
        document_count = stats.get('document_count', 0)
        
        print(f"📊 當前向量資料庫文檔數量: {document_count}")
        
        # 如果文檔數量少於 10，執行自動訓練
        if document_count < 10:
            print("⚠️ 向量資料庫為空或文檔過少，開始自動訓練...")
            await auto_train_rag_system()
            
            # 重新檢查
            stats = vector_store.get_collection_stats()
            document_count = stats.get('document_count', 0)
            print(f"📊 訓練後文檔數量: {document_count}")
        
        # 初始化 Ollama 客戶端
        ollama_client = OllamaClient()
        
        # 檢查 Ollama 連接
        print("🔗 檢查 Ollama 服務連接...")
        ollama_connected = await ollama_client.check_connection()
        
        if not ollama_connected:
            print("❌ Ollama 服務未連接")
            print("請執行以下命令啟動 Ollama:")
            print("1. ollama serve")
            print("2. ollama pull qwen2.5:7b")
            return None
        
        print("✅ Ollama 服務連接成功")
        
        # 初始化 RAG 聊天系統
        retriever = RAGRetriever(vector_store)
        rag_chat_system = RAGOllamaChat(ollama_client, retriever)
        
        print("✅ RAG 聊天系統初始化完成")
        return rag_chat_system
        
    except Exception as e:
        print(f"❌ RAG 系統設置失敗: {e}")
        return None

async def auto_train_rag_system():
    """自動執行 RAG 系統訓練"""
    print("🚀 開始自動訓練 RAG 系統...")
    
    try:
        # 動態導入訓練模組（避免循環導入）
        from scripts.train_rag import RAGTrainer
        
        # 創建訓練器
        trainer = RAGTrainer()
        
        print("📚 設置訓練組件...")
        await trainer.setup_components()
        
        print("🔄 處理訓練資料...")
        processed_data_path = trainer.process_data(force_reprocess=False)
        
        print("🏗️ 建立向量索引...")
        trainer.build_vector_index(processed_data_path, force_rebuild=False)
        
        print("✅ 自動訓練完成")
        
    except ImportError as e:
        print(f"❌ 無法導入訓練模組: {e}")
        print("請確保 train_rag.py 檔案存在")
        raise
    except Exception as e:
        print(f"❌ 自動訓練失敗: {e}")
        raise

# =============================================================================
# 應用生命週期管理
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    global rag_chat_system
    
    print("🚀 啟動高速公路智能交通系統...")
    print("=" * 60)
    
    # 自動設置 RAG 系統
    rag_chat_system = await auto_setup_rag_system()
    
    if rag_chat_system:
        print("🤖 交通管理者顧問系統已準備就緒")
    else:
        print("⚠️ RAG 聊天系統未成功初始化，部分功能將受限")
    
    print("=" * 60)
    print("🌐 服務端點:")
    print("   • 簡單聊天: POST /api/chat")
    print("   • 管理者顧問: POST /api/controller/chat")
    print("   • 系統狀態: GET /api/status")
    print("   • 手動訓練: POST /api/admin/retrain")
    print("   • API 文檔: http://localhost:8000/docs")
    print("=" * 60)
    
    yield
    
    print("⏹️ 關閉高速公路智能交通系統...")

# =============================================================================
# FastAPI 應用設置
# =============================================================================

app = FastAPI(
    title="Highway Intelligent Traffic System",
    description="高速公路智能交通系統 - 包含 RAG 聊天和交通管理者顧問",
    version="2.1.0",
    lifespan=lifespan
)

# CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",     # React 開發服務器
        "http://127.0.0.1:3000",    # 替代本地地址
        "http://localhost:3001",    # 備用端口
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 路由註冊
# =============================================================================

# 包含交通管理者顧問路由
app.include_router(controller_router, prefix="/api", tags=["Controller Advisor"])

# =============================================================================
# 簡單 RAG 聊天端點
# =============================================================================

@app.post("/api/chat", response_model=SimpleChatResponse)
async def simple_chat(request: SimpleChatRequest):
    """簡單的 RAG 聊天端點"""
    start_time = datetime.now()
    
    try:
        if not rag_chat_system:
            raise HTTPException(
                status_code=503, 
                detail="RAG 聊天系統未初始化，請檢查 Ollama 服務或執行手動訓練"
            )
        
        # 生成回應
        response = await rag_chat_system.chat(request.message)
        
        # 檢索相關文檔作為來源
        vector_store = VectorStore()
        search_results = vector_store.search(request.message, top_k=3)
        sources = [result['text'][:200] + '...' for result in search_results]
        
        # 計算信心度
        confidence = sum(result['score'] for result in search_results) / len(search_results) if search_results else 0.0
        
        # 計算處理時間
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return SimpleChatResponse(
            response=response,
            sources=sources if request.include_sources else [],
            confidence=min(confidence, 1.0),
            session_id=request.session_id or f"chat-{int(datetime.now().timestamp())}",
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天處理失敗: {str(e)}")

# =============================================================================
# 管理端點
# =============================================================================

@app.post("/api/admin/retrain")
async def manual_retrain():
    """手動重新訓練 RAG 系統"""
    global rag_chat_system
    
    try:
        print("🔄 開始手動重新訓練...")
        
        # 執行訓練
        await auto_train_rag_system()
        
        # 重新初始化聊天系統
        rag_chat_system = await auto_setup_rag_system()
        
        return {
            "status": "success",
            "message": "RAG 系統重新訓練完成",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新訓練失敗: {str(e)}")

@app.get("/api/admin/training-status")
async def get_training_status():
    """獲取訓練狀態"""
    try:
        vector_store = VectorStore()
        stats = vector_store.get_collection_stats()
        
        return {
            "document_count": stats.get('document_count', 0),
            "is_trained": stats.get('document_count', 0) > 0,
            "rag_system_ready": rag_chat_system is not None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "document_count": 0,
            "is_trained": False,
            "rag_system_ready": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# =============================================================================
# 系統狀態和資訊端點
# =============================================================================

@app.get("/")
async def root():
    """根端點 - 系統資訊"""
    return {
        "name": "Highway Intelligent Traffic System",
        "version": "2.1.0",
        "description": "高速公路智能交通系統 - 支援自動訓練",
        "status": "operational",
        "auto_training": "enabled",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "simple_chat": {
                "url": "/api/chat",
                "method": "POST",
                "description": "簡單的 RAG 聊天功能"
            },
            "controller_chat": {
                "url": "/api/controller/chat", 
                "method": "POST",
                "description": "交通管理者專用顧問"
            },
            "manual_retrain": {
                "url": "/api/admin/retrain",
                "method": "POST",
                "description": "手動重新訓練系統"
            },
            "training_status": {
                "url": "/api/admin/training-status",
                "method": "GET",
                "description": "查看訓練狀態"
            }
        }
    }

@app.get("/api/status")
async def get_system_status():
    """獲取整體系統狀態"""
    try:
        # 檢查 RAG 系統
        rag_status = "operational" if rag_chat_system else "unavailable"
        
        # 檢查向量資料庫
        try:
            vector_store = VectorStore()
            vector_stats = vector_store.get_collection_stats()
            vector_status = "operational" if vector_stats.get('document_count', 0) > 0 else "empty"
        except Exception:
            vector_stats = {"document_count": 0}
            vector_status = "error"
        
        # 檢查 Ollama
        try:
            ollama_client = OllamaClient()
            ollama_status = "operational" if await ollama_client.check_connection() else "unavailable"
        except Exception:
            ollama_status = "error"
        
        return {
            "system": {
                "status": "operational",
                "timestamp": datetime.now().isoformat(),
                "auto_training": "enabled"
            },
            "services": {
                "rag_chat": {
                    "status": rag_status,
                    "endpoint": "/api/chat"
                },
                "controller_advisor": {
                    "status": "operational",
                    "endpoint": "/api/controller/chat"
                },
                "vector_database": {
                    "status": vector_status,
                    "document_count": vector_stats.get("document_count", 0)
                },
                "ollama_service": {
                    "status": ollama_status,
                    "description": "Large Language Model Service"
                }
            },
            "health_check": {
                "overall": "healthy" if all([
                    rag_status != "error",
                    vector_status != "error", 
                    ollama_status != "error"
                ]) else "degraded"
            }
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "system": {"status": "error", "error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/health")
async def health_check():
    """簡單的健康檢查"""
    return {
        "status": "healthy",
        "service": "Highway Intelligent Traffic System",
        "auto_training": "enabled",
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# 主函數
# =============================================================================

def main():
    """主函數 - 啟動服務器"""
    print("🚀 啟動高速公路智能交通系統服務器...")
    print("📍 服務器將在 http://localhost:8000 啟動")
    print("📖 API 文檔可在 http://localhost:8000/docs 查看")
    print("🤖 支援自動訓練和手動重訓功能")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        reload_dirs=["./"]  # 監控當前目錄變化
    )

if __name__ == "__main__":
    main()