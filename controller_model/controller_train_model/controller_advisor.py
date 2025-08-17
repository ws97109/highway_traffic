"""
交通管理者顧問後端系統
專為交通管理人員設計的 RAG 對話系統，提供交通管理策略和決策建議
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid

# 導入 RAG 系統
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models.ollama_client import OllamaClient, RAGOllamaChat
from embeddings.vector_store import VectorStore, RAGRetriever

# =============================================================================
# API 請求/回應模型
# =============================================================================

class ControllerChatRequest(BaseModel):
    """管理者聊天請求"""
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # 可包含當前交通狀況等上下文
    priority: Optional[str] = "normal"  # normal, urgent, emergency
    
class TrafficContext(BaseModel):
    """交通上下文資訊"""
    highway_section: Optional[str] = None
    current_speed: Optional[float] = None
    flow_rate: Optional[int] = None
    incident_reports: Optional[List[str]] = None
    weather_conditions: Optional[str] = None
    time_period: Optional[str] = None

class ControllerChatResponse(BaseModel):
    """管理者聊天回應"""
    response: str
    recommendations: List[str]  # 具體的管理建議
    priority_actions: List[str]  # 優先執行的行動
    estimated_impact: Optional[str] = None  # 預估影響
    supporting_data: List[str]  # 支持資料來源
    session_id: str
    confidence_score: float
    processing_time: float
    follow_up_questions: Optional[List[str]] = None  # 建議的後續問題

class ConversationHistory(BaseModel):
    """對話歷史"""
    session_id: str
    messages: List[Dict[str, Any]]
    created_at: datetime
    last_updated: datetime

# =============================================================================
# 交通管理者顧問系統
# =============================================================================

class ControllerAdvisorBackend:
    """交通管理者顧問後端系統"""
    
    def __init__(self, config_path: str = None):
        """初始化系統"""
        self.config_path = config_path
        self.ollama_client = None
        self.rag_chat = None
        self.vector_store = None
        self._initialized = False
        
        # 對話會話管理
        self.conversations: Dict[str, ConversationHistory] = {}
        
        # 交通管理知識庫
        self.management_strategies = self._load_management_strategies()
        self.emergency_protocols = self._load_emergency_protocols()
        
        logger.info("交通管理者顧問系統初始化中...")
    
    async def initialize(self):
        """初始化 RAG 系統"""
        if self._initialized:
            return
        
        try:
            # 初始化向量存儲
            self.vector_store = VectorStore(self.config_path)
            
            # 檢查向量資料庫狀態
            stats = self.vector_store.get_collection_stats()
            if stats['document_count'] == 0:
                raise Exception("RAG 系統尚未初始化或向量資料庫為空")
            
            # 初始化 Ollama 客戶端
            self.ollama_client = OllamaClient(self.config_path)
            
            # 檢查 Ollama 連接
            if not await self.ollama_client.check_connection():
                raise Exception("Ollama 服務連接失敗")
            
            # 初始化 RAG 聊天系統
            retriever = RAGRetriever(self.vector_store)
            self.rag_chat = RAGOllamaChat(self.ollama_client, retriever)
            
            self._initialized = True
            logger.info(f"✅ 交通管理者顧問系統初始化成功，包含 {stats['document_count']} 個文檔")
            
        except Exception as e:
            logger.error(f"❌ 初始化失敗: {e}")
            raise
    
    async def chat_with_advisor(self, request: ControllerChatRequest) -> ControllerChatResponse:
        """與交通管理顧問對話"""
        start_time = datetime.now()
        
        try:
            if not self._initialized:
                await self.initialize()
            
            # 生成或使用現有會話ID
            session_id = request.session_id or str(uuid.uuid4())
            
            # 構建增強的查詢提示
            enhanced_query = self._build_management_query(request)
            
            # 檢索相關文檔
            search_results = self.vector_store.search(enhanced_query, top_k=8)
            supporting_data = [result['text'][:300] + '...' for result in search_results[:5]]
            
            # 計算信心度
            confidence = self._calculate_confidence(search_results, request.priority)
            
            # 生成回應
            rag_response = await self.rag_chat.chat(enhanced_query)
            
            # 分析回應並提取建議
            recommendations = self._extract_recommendations(rag_response)
            priority_actions = self._extract_priority_actions(rag_response, request.priority)
            estimated_impact = self._estimate_impact(rag_response)
            
            # 生成後續問題建議
            follow_up_questions = self._generate_follow_up_questions(request.message, rag_response)
            
            # 更新對話歷史
            self._update_conversation_history(session_id, request.message, rag_response)
            
            # 計算處理時間
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            response = ControllerChatResponse(
                response=rag_response,
                recommendations=recommendations,
                priority_actions=priority_actions,
                estimated_impact=estimated_impact,
                supporting_data=supporting_data,
                session_id=session_id,
                confidence_score=confidence,
                processing_time=processing_time,
                follow_up_questions=follow_up_questions
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ 管理者對話處理失敗: {e}")
            raise Exception(f"對話處理失敗: {str(e)}")
    
    def _build_management_query(self, request: ControllerChatRequest) -> str:
        """構建管理導向的查詢提示"""
        current_time = datetime.now()
        
        # 基礎查詢
        enhanced_query = f"""【交通管理諮詢】- {current_time.strftime('%Y-%m-%d %H:%M:%S')}

管理者問題：{request.message}

請以專業交通管理顧問的身份回答，重點關注：
1. 具體的交通管理策略和措施
2. 可量化的預期效益和影響評估
3. 實施的優先順序和時程安排
4. 所需的資源和人力配置
5. 風險評估和應急預案
6. 相關的法規和政策考量"""

        # 添加上下文資訊
        if request.context:
            enhanced_query += f"""

當前交通狀況：
"""
            for key, value in request.context.items():
                if value is not None:
                    enhanced_query += f"• {key}: {value}\n"

        # 根據優先級調整查詢
        if request.priority == "urgent":
            enhanced_query += """

⚠️ 緊急情況 - 請優先提供：
• 立即可執行的短期措施
• 人員調度和資源分配建議
• 風險控制和安全防護措施"""
        
        elif request.priority == "emergency":
            enhanced_query += """

🚨 緊急狀況 - 請重點關注：
• 緊急應變程序和標準作業流程
• 跨部門協調和通報機制
• 媒體應對和公眾溝通策略
• 後續調查和改善措施"""

        enhanced_query += """

請提供專業、具體且可執行的管理建議，包含預期效益和實施細節。"""

        return enhanced_query
    
    def _calculate_confidence(self, search_results: List[Dict], priority: str) -> float:
        """計算回應信心度"""
        if not search_results:
            return 0.3
        
        # 基於檢索結果的相似度
        avg_similarity = sum(result['score'] for result in search_results) / len(search_results)
        
        # 基於文檔數量的信心度調整
        doc_count_factor = min(len(search_results) / 5, 1.0)
        
        # 緊急情況下提高信心度要求
        priority_factor = 0.9 if priority in ["urgent", "emergency"] else 1.0
        
        confidence = (avg_similarity * 0.7 + doc_count_factor * 0.3) * priority_factor
        
        return min(confidence, 0.95)  # 最高95%信心度
    
    def _extract_recommendations(self, response: str) -> List[str]:
        """從回應中提取具體建議"""
        recommendations = []
        
        # 尋找標記的建議
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            # 檢查是否為建議項目
            if (line.startswith('•') or line.startswith('-') or line.startswith('1.') or
                line.startswith('2.') or line.startswith('3.') or '建議' in line):
                if len(line) > 10:  # 過濾太短的內容
                    recommendations.append(line.lstrip('•-123456789. '))
        
        # 如果沒找到標記的建議，嘗試提取關鍵句子
        if not recommendations:
            sentences = response.split('。')
            for sentence in sentences:
                if any(keyword in sentence for keyword in ['應該', '建議', '可以', '需要', '執行']):
                    if len(sentence.strip()) > 15:
                        recommendations.append(sentence.strip() + '。')
        
        return recommendations[:5]  # 最多返回5個建議
    
    def _extract_priority_actions(self, response: str, priority: str) -> List[str]:
        """提取優先行動項目"""
        priority_actions = []
        
        # 尋找優先或緊急相關的行動
        priority_keywords = ['立即', '緊急', '優先', '首先', '馬上', '第一', '重要']
        
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in priority_keywords):
                if len(line) > 10:
                    priority_actions.append(line.lstrip('•-123456789. '))
        
        # 如果是緊急情況但沒找到優先行動，從建議中選取
        if priority in ["urgent", "emergency"] and not priority_actions:
            recommendations = self._extract_recommendations(response)
            priority_actions = recommendations[:2]  # 取前兩個作為優先行動
        
        return priority_actions[:3]  # 最多3個優先行動
    
    def _estimate_impact(self, response: str) -> Optional[str]:
        """估算影響效果"""
        impact_indicators = []
        
        # 尋找量化指標
        import re
        
        # 尋找百分比
        percentages = re.findall(r'(\d+(?:\.\d+)?%)', response)
        if percentages:
            impact_indicators.extend([f"預期改善 {p}" for p in percentages[:2]])
        
        # 尋找時間指標
        time_patterns = re.findall(r'(\d+(?:\.\d+)?(?:分鐘|小時|天|週|月))', response)
        if time_patterns:
            impact_indicators.extend([f"執行時程 {t}" for t in time_patterns[:2]])
        
        # 尋找速度改善
        speed_patterns = re.findall(r'(\d+(?:\.\d+)?(?:km/h|公里))', response)
        if speed_patterns:
            impact_indicators.extend([f"速度提升 {s}" for s in speed_patterns[:1]])
        
        return "; ".join(impact_indicators) if impact_indicators else None
    
    def _generate_follow_up_questions(self, original_question: str, response: str) -> List[str]:
        """生成後續問題建議"""
        follow_ups = []
        
        # 基於原問題類型生成後續問題
        if '壅塞' in original_question or '塞車' in original_question:
            follow_ups.extend([
                "這些措施的實施成本大概是多少？",
                "需要多長時間才能看到明顯效果？",
                "是否有其他路段也適用這些策略？"
            ])
        
        elif '事故' in original_question:
            follow_ups.extend([
                "如何建立更完善的事故預防機制？",
                "事故處理時的最佳人員配置是什麼？",
                "如何改善事故現場的交通疏導效率？"
            ])
        
        elif '管制' in original_question or '限制' in original_question:
            follow_ups.extend([
                "這些管制措施對用路人的接受度如何？",
                "如何評估管制效果？",
                "是否需要配套的替代方案？"
            ])
        
        # 從回應中尋找可能的後續話題
        if '研究' in response or '分析' in response:
            follow_ups.append("是否有相關的研究報告可以參考？")
        
        if '技術' in response or '系統' in response:
            follow_ups.append("實施這些技術方案需要什麼樣的基礎設施？")
        
        return follow_ups[:3]  # 最多3個後續問題
    
    def _update_conversation_history(self, session_id: str, question: str, response: str):
        """更新對話歷史"""
        current_time = datetime.now()
        
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationHistory(
                session_id=session_id,
                messages=[],
                created_at=current_time,
                last_updated=current_time
            )
        
        conversation = self.conversations[session_id]
        conversation.messages.append({
            'timestamp': current_time.isoformat(),
            'question': question,
            'response': response
        })
        conversation.last_updated = current_time
        
        # 限制歷史記錄長度
        if len(conversation.messages) > 20:
            conversation.messages = conversation.messages[-20:]
    
    def get_conversation_history(self, session_id: str) -> Optional[ConversationHistory]:
        """獲取對話歷史"""
        return self.conversations.get(session_id)
    
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        try:
            if not self._initialized:
                return {
                    'status': 'not_initialized',
                    'rag_system': False,
                    'active_sessions': 0,
                    'document_count': 0
                }
            
            stats = self.vector_store.get_collection_stats()
            
            return {
                'status': 'operational',
                'rag_system': True,
                'active_sessions': len(self.conversations),
                'document_count': stats['document_count'],
                'total_conversations': sum(len(conv.messages) for conv in self.conversations.values()),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"獲取系統狀態失敗: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'rag_system': False,
                'active_sessions': 0
            }
    
    def _load_management_strategies(self) -> Dict[str, List[str]]:
        """載入交通管理策略庫"""
        return {
            'congestion_management': [
                '動態車道管制',
                '匝道儀控調整',
                '速限動態調整',
                '大型車分流',
                'HOV車道啟用'
            ],
            'incident_management': [
                '快速事故排除',
                '替代路線導引',
                '資訊即時發布',
                '交通疏導部署',
                '跨單位協調'
            ],
            'flow_optimization': [
                '號誌時制調整',
                '交流道管制',
                '路網負載平衡',
                '預測性管理',
                '智慧交通系統'
            ]
        }
    
    def _load_emergency_protocols(self) -> Dict[str, List[str]]:
        """載入緊急應變程序"""
        return {
            'major_incident': [
                '立即現場管制',
                '緊急救援通道',
                '媒體統一發言',
                '替代路線開放',
                '跨部門協調會議'
            ],
            'severe_weather': [
                '預警訊息發布',
                '車輛限行措施',
                '安全設施檢查',
                '應急設備部署',
                '持續監控評估'
            ],
            'system_failure': [
                '備援系統啟動',
                '人工交通管制',
                '緊急通訊建立',
                '影響範圍評估',
                '修復優先順序'
            ]
        }

# =============================================================================
# FastAPI 路由器設置
# =============================================================================

# 創建全域後端實例
advisor_backend = None

async def get_advisor_backend():
    """獲取或初始化顧問後端"""
    global advisor_backend
    
    if advisor_backend is None:
        advisor_backend = ControllerAdvisorBackend()
        await advisor_backend.initialize()
    
    return advisor_backend

# 創建 FastAPI 路由器
router = APIRouter()

@router.post("/controller/chat", response_model=ControllerChatResponse)
async def chat_with_controller_advisor(request: ControllerChatRequest):
    """交通管理者與顧問對話"""
    try:
        backend = await get_advisor_backend()
        return await backend.chat_with_advisor(request)
    except Exception as e:
        logger.error(f"❌ 管理者對話失敗: {e}")
        raise HTTPException(status_code=500, detail=f"對話處理失敗: {str(e)}")

@router.get("/controller/conversation/{session_id}")
async def get_conversation_history(session_id: str):
    """獲取對話歷史"""
    try:
        backend = await get_advisor_backend()
        history = backend.get_conversation_history(session_id)
        
        if not history:
            raise HTTPException(status_code=404, detail="找不到指定的對話記錄")
        
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 獲取對話歷史失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取對話歷史失敗: {str(e)}")

@router.get("/controller/status")
async def get_controller_system_status():
    """獲取系統狀態"""
    try:
        backend = await get_advisor_backend()
        return backend.get_system_status()
    except Exception as e:
        logger.error(f"❌ 獲取系統狀態失敗: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'rag_system': False,
            'active_sessions': 0
        }

@router.post("/controller/initialize")
async def initialize_controller_system():
    """手動初始化系統"""
    try:
        global advisor_backend
        advisor_backend = ControllerAdvisorBackend()
        await advisor_backend.initialize()
        
        status = advisor_backend.get_system_status()
        return {
            'message': '交通管理者顧問系統初始化成功',
            'status': status
        }
    except Exception as e:
        logger.error(f"❌ 系統初始化失敗: {e}")
        raise HTTPException(status_code=500, detail=f"系統初始化失敗: {str(e)}")

# =============================================================================
# 命令行測試界面
# =============================================================================

async def run_interactive_chat():
    """運行互動式聊天界面（類似你終端機的版本）"""
    print("=" * 50)
    print("🚗 交通管理者顧問系統 - RAG 對話界面")
    print("=" * 50)
    print("輸入 'quit' 或 'exit' 來退出")
    print("輸入 'status' 查看系統狀態")
    print("輸入 'history' 查看對話歷史")
    print("-" * 50)
    
    # 初始化系統
    backend = ControllerAdvisorBackend()
    await backend.initialize()
    
    session_id = str(uuid.uuid4())
    
    while True:
        try:
            # 獲取用戶輸入
            user_input = input("\n管理者: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("再見！")
                break
            
            if user_input.lower() == 'status':
                status = backend.get_system_status()
                print(f"\n系統狀態: {status}")
                continue
            
            if user_input.lower() == 'history':
                history = backend.get_conversation_history(session_id)
                if history:
                    print(f"\n對話歷史 (共 {len(history.messages)} 則):")
                    for msg in history.messages[-3:]:  # 顯示最近3則
                        print(f"Q: {msg['question'][:100]}...")
                        print(f"A: {msg['response'][:200]}...")
                        print("-" * 30)
                else:
                    print("\n尚無對話歷史")
                continue
            
            if not user_input:
                continue
            
            # 創建請求
            request = ControllerChatRequest(
                message=user_input,
                session_id=session_id,
                priority="normal"
            )
            
            # 獲取回應
            print("顧問: ", end="", flush=True)
            response = await backend.chat_with_advisor(request)
            
            # 顯示回應
            print(response.response)
            
            # 顯示建議摘要
            if response.recommendations:
                print(f"\n📋 管理建議:")
                for i, rec in enumerate(response.recommendations, 1):
                    print(f"  {i}. {rec}")
            
            if response.priority_actions:
                print(f"\n⚡ 優先行動:")
                for i, action in enumerate(response.priority_actions, 1):
                    print(f"  {i}. {action}")
            
            if response.estimated_impact:
                print(f"\n📊 預期影響: {response.estimated_impact}")
            
            # 顯示信心度和處理時間
            print(f"\n💡 信心度: {response.confidence_score:.2%} | "
                  f"處理時間: {response.processing_time:.0f}ms")
            
            # 顯示後續問題建議
            if response.follow_up_questions:
                print(f"\n❓ 建議後續問題:")
                for i, question in enumerate(response.follow_up_questions, 1):
                    print(f"  {i}. {question}")
            
        except KeyboardInterrupt:
            print("\n\n再見！")
            break
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")

# =============================================================================
# 主函數
# =============================================================================

async def main():
    """主函數 - 可選擇 API 模式或互動模式"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        # 互動模式
        await run_interactive_chat()
    else:
        # 測試模式
        print("=== 測試交通管理者顧問系統 ===")
        
        backend = ControllerAdvisorBackend()
        await backend.initialize()
        
        # 測試請求
        test_request = ControllerChatRequest(
            message="五股林口段塞車問題可以怎麼解決？需要什麼管理措施？",
            priority="urgent",
            context={
                "highway_section": "國道1號五股-林口",
                "current_speed": 25.5,
                "flow_rate": 1800,
                "time_period": "morning_peak"
            }
        )
        
        response = await backend.chat_with_advisor(test_request)
        
        print(f"問題: {test_request.message}")
        print(f"回應: {response.response}")
        print(f"建議數量: {len(response.recommendations)}")
        print(f"優先行動: {len(response.priority_actions)}")
        print(f"信心度: {response.confidence_score:.2%}")
        print(f"處理時間: {response.processing_time:.0f}ms")

if __name__ == "__main__":
    asyncio.run(main())