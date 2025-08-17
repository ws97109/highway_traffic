"""
Ollama 客戶端模組
用於與 Ollama 本地 LLM 進行交互
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
import httpx
from loguru import logger

# 導入配置管理器
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from train_model.utils.config_manager import get_config_manager

class OllamaClient:
    """Ollama 客戶端"""
    
    def __init__(self, config_path: str = None):
        """初始化 Ollama 客戶端"""
        # 使用配置管理器
        if config_path:
            os.environ['RAG_CONFIG_PATH'] = config_path
        
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        
        self.ollama_config = self.config['ollama']
        self.base_url = self.ollama_config['base_url']
        self.model = self.ollama_config['model']
        self.timeout = self.ollama_config['timeout']
        self.max_tokens = self.ollama_config['max_tokens']
        self.temperature = self.ollama_config['temperature']
        
        logger.info(f"Ollama 客戶端初始化完成 - 模型: {self.model}")
    
    async def check_connection(self) -> bool:
        """檢查 Ollama 服務連接"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json()
                    available_models = [model['name'] for model in models.get('models', [])]
                    logger.info(f"Ollama 服務正常，可用模型: {available_models}")
                    
                    if self.model not in available_models:
                        logger.warning(f"指定模型 {self.model} 不在可用模型列表中")
                        return False
                    return True
                else:
                    logger.error(f"Ollama 服務響應異常: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"無法連接 Ollama 服務: {e}")
            return False
    
    async def generate_response(self, prompt: str, context: str = "", system_prompt: str = "") -> str:
        """生成回應"""
        # 構建完整的提示
        full_prompt = self._build_prompt(prompt, context, system_prompt)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                }
                
                logger.info(f"發送請求到 Ollama - 模型: {self.model}")
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result.get('response', '')
                    logger.info("成功生成回應")
                    return generated_text.strip()
                else:
                    logger.error(f"Ollama 生成失敗: {response.status_code} - {response.text}")
                    return "抱歉，無法生成回應。"
        
        except Exception as e:
            logger.error(f"生成回應時發生錯誤: {e}")
            return "抱歉，發生了技術錯誤。"
    
    async def stream_response(self, prompt: str, context: str = "", system_prompt: str = "") -> AsyncGenerator[str, None]:
        """流式生成回應"""
        full_prompt = self._build_prompt(prompt, context, system_prompt)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": True,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                }
                
                async with client.stream(
                    'POST',
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    data = json.loads(line)
                                    if 'response' in data:
                                        yield data['response']
                                    if data.get('done', False):
                                        break
                                except json.JSONDecodeError:
                                    continue
                    else:
                        logger.error(f"流式生成失敗: {response.status_code}")
                        yield "抱歉，無法生成回應。"
        
        except Exception as e:
            logger.error(f"流式生成時發生錯誤: {e}")
            yield "抱歉，發生了技術錯誤。"
    
    def _build_prompt(self, prompt: str, context: str = "", system_prompt: str = "") -> str:
        """構建完整的提示"""
        # 預設系統提示
        default_system = """你是一個專業的台灣高速公路交通資訊助手。你擁有關於國道一號和國道三號的詳細工程和交通資料知識。

請根據提供的上下文資訊回答問題，並遵循以下原則：
1. 回答要準確、具體，基於提供的資料
2. 使用繁體中文回答
3. 如果資料不足以回答問題，請誠實說明
4. 提供有用的補充資訊和建議
5. 回答要結構化且易於理解"""
        
        # 使用自定義系統提示或預設提示
        system_msg = system_prompt if system_prompt else default_system
        
        # 構建完整提示
        full_prompt = f"{system_msg}\n\n"
        
        if context:
            full_prompt += f"相關資料:\n{context}\n\n"
        
        full_prompt += f"問題: {prompt}\n\n回答:"
        
        return full_prompt
    
    async def get_embeddings(self, text: str) -> Optional[List[float]]:
        """獲取文本嵌入（如果模型支援）"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "prompt": text
                }
                
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('embedding', None)
                else:
                    logger.warning("模型不支援嵌入生成或請求失敗")
                    return None
        
        except Exception as e:
            logger.warning(f"獲取嵌入時發生錯誤: {e}")
            return None
    
    async def pull_model(self, model_name: Optional[str] = None) -> bool:
        """拉取模型"""
        target_model = model_name or self.model
        
        try:
            if not self.http_client:
                self._create_http_client()
                
            payload = {"name": target_model}
            
            logger.info(f"開始拉取模型: {target_model} (這可能需要幾分鐘)")
            
            # 使用更長的超時時間來下載模型
            download_client = httpx.AsyncClient(timeout=httpx.Timeout(1200))  # 20 分鐘
            
            try:
                response = await download_client.post(
                    f"{self.base_url}/api/pull",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"成功拉取模型: {target_model}")
                    return True
                else:
                    logger.error(f"拉取模型失敗: {response.status_code} - {response.text}")
                    return False
                    
            finally:
                await download_client.aclose()
        
        except httpx.TimeoutException:
            logger.error(f"拉取模型超時: {target_model}")
            return False
        except Exception as e:
            logger.error(f"拉取模型時發生錯誤: {e}")
            return False

class RAGOllamaChat:
    """RAG + Ollama 聊天系統"""
    
    def __init__(self, ollama_client: OllamaClient, vector_store_retriever):
        """初始化聊天系統"""
        self.ollama_client = ollama_client
        self.retriever = vector_store_retriever
        self.conversation_history = []
        
        logger.info("RAG Ollama 聊天系統初始化完成")
    
    async def chat(self, user_message: str, use_rag: bool = True, max_history: int = 5) -> str:
        """聊天對話"""
        # 如果啟用 RAG，檢索相關上下文
        context = ""
        if use_rag:
            context = self.retriever.retrieve_context(user_message)
        
        # 構建對話歷史
        history_prompt = self._build_history_prompt(max_history)
        
        # 生成系統提示
        system_prompt = f"""你是台灣高速公路交通專家助手。{history_prompt}

請基於以下上下文資料回答用戶問題："""
        
        # 生成回應
        response = await self.ollama_client.generate_response(
            prompt=user_message,
            context=context,
            system_prompt=system_prompt
        )
        
        # 更新對話歷史
        self.conversation_history.append({
            'user': user_message,
            'assistant': response,
            'context_used': bool(context)
        })
        
        return response
    
    async def stream_chat(self, user_message: str, use_rag: bool = True, max_history: int = 5) -> AsyncGenerator[str, None]:
        """流式聊天對話"""
        # 如果啟用 RAG，檢索相關上下文
        context = ""
        if use_rag:
            context = self.retriever.retrieve_context(user_message)
        
        # 構建對話歷史
        history_prompt = self._build_history_prompt(max_history)
        
        # 生成系統提示
        system_prompt = f"""你是台灣高速公路交通專家助手。{history_prompt}

請基於以下上下文資料回答用戶問題："""
        
        # 流式生成回應
        full_response = ""
        async for chunk in self.ollama_client.stream_response(
            prompt=user_message,
            context=context,
            system_prompt=system_prompt
        ):
            full_response += chunk
            yield chunk
        
        # 更新對話歷史
        self.conversation_history.append({
            'user': user_message,
            'assistant': full_response,
            'context_used': bool(context)
        })
    
    def _build_history_prompt(self, max_history: int) -> str:
        """構建對話歷史提示"""
        if not self.conversation_history:
            return ""
        
        recent_history = self.conversation_history[-max_history:]
        history_text = "以下是近期對話歷史供參考：\n"
        
        for i, conv in enumerate(recent_history, 1):
            history_text += f"對話 {i}:\n"
            history_text += f"用戶: {conv['user']}\n"
            history_text += f"助手: {conv['assistant']}\n\n"
        
        return history_text
    
    def clear_history(self):
        """清除對話歷史"""
        self.conversation_history = []
        logger.info("對話歷史已清除")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """獲取對話統計"""
        total_conversations = len(self.conversation_history)
        rag_used = sum(1 for conv in self.conversation_history if conv['context_used'])
        
        return {
            'total_conversations': total_conversations,
            'rag_usage_count': rag_used,
            'rag_usage_rate': rag_used / total_conversations if total_conversations > 0 else 0
        }

if __name__ == "__main__":
    # 測試 Ollama 客戶端
    import asyncio
    
    async def test_ollama():
        client = OllamaClient()
        
        # 檢查連接
        if await client.check_connection():
            print("✓ Ollama 服務連接正常")
            
            # 測試生成
            response = await client.generate_response(
                "請簡單介紹一下台灣的高速公路系統。",
                context="台灣有國道一號和國道三號等主要高速公路。"
            )
            print(f"生成回應: {response}")
        else:
            print("✗ Ollama 服務連接失敗")
    
    # 執行測試
    asyncio.run(test_ollama())
