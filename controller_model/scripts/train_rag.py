"""
RAG 系統訓練腳本
整合資料處理、向量儲存和 Ollama 模型
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from loguru import logger

# 添加項目根目錄到 Python 路徑
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# 導入自定義模組
from controller_model.data_processing.enhanced_csv_processor import EnhancedHighwayCSVProcessor
from controller_model.embeddings.vector_store import VectorStore, RAGRetriever
from controller_model.controller_train_model.ollama_client import OllamaClient, RAGOllamaChat

class RAGTrainer:
    """RAG 系統訓練器"""
    
    def __init__(self, config_path: str = None):
        """初始化訓練器"""
        if config_path is None:
            config_path = current_dir.parent / "configs" / "rag_config.yaml"
        
        self.config_path = str(config_path)
        
        # 初始化各個組件
        self.enhanced_processor = None
        self.vector_store = None
        self.ollama_client = None
        self.rag_chat = None
        
        logger.info("RAG 訓練器初始化完成")
    
    async def setup_components(self):
        """設置所有組件"""
        logger.info("正在設置 RAG 系統組件...")
        
        # 初始化增強 CSV 處理器
        self.enhanced_processor = EnhancedHighwayCSVProcessor(self.config_path)
        logger.info("✓ 增強 CSV 處理器初始化完成")
        
        # 初始化向量儲存
        self.vector_store = VectorStore(self.config_path)
        logger.info("✓ 向量儲存系統初始化完成")
        
        # 初始化 Ollama 客戶端
        self.ollama_client = OllamaClient(self.config_path)
        
        # 檢查 Ollama 連接
        if not await self.ollama_client.check_connection():
            raise Exception("Ollama 服務連接失敗，請確保服務正在運行")
        logger.info("✓ Ollama 客戶端初始化完成")
        
        # 初始化檢索器
        retriever = RAGRetriever(self.vector_store)
        
        # 初始化聊天系統
        self.rag_chat = RAGOllamaChat(self.ollama_client, retriever)
        logger.info("✓ RAG 聊天系統初始化完成")
    
    def process_data(self, force_reprocess: bool = False):
        """處理訓練資料"""
        logger.info("開始處理訓練資料...")
        
        # 檢查是否已有處理過的資料
        output_dir = self.enhanced_processor.data_config['output_dir']
        processed_file = os.path.join(output_dir, "enhanced_highway_data.json")
        
        if os.path.exists(processed_file) and not force_reprocess:
            logger.info("發現已處理的增強資料文件，跳過處理步驟")
            logger.info("如需重新處理，請使用 --force-reprocess 參數")
            return processed_file
        
        # 處理增強資料
        processed_data = self.enhanced_processor.process_all_data_enhanced()
        output_path = self.enhanced_processor.save_processed_data(processed_data, "enhanced_highway_data.json")
        
        logger.info(f"✓ 資料處理完成，輸出文件: {output_path}")
        return output_path
    
    def build_vector_index(self, processed_data_path: str, force_rebuild: bool = False):
        """構建向量索引"""
        logger.info("開始構建向量索引...")
        
        # 檢查現有索引
        stats = self.vector_store.get_collection_stats()
        if stats['document_count'] > 0 and not force_rebuild:
            logger.info(f"發現現有索引，包含 {stats['document_count']} 個文檔")
            logger.info("如需重建索引，請使用 --force-rebuild 參數")
            return
        
        # 載入處理過的資料
        import json
        with open(processed_data_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        logger.info(f"載入了 {len(documents)} 個文檔")
        
        # 驗證文檔格式
        if not documents or not all('text' in doc and 'id' in doc for doc in documents):
            raise ValueError("文檔格式不正確，每個文檔必須包含 'text' 和 'id' 欄位")
        
        # 如果需要重建，先刪除現有集合
        if force_rebuild and stats.get('document_count', 0) > 0:
            logger.warning("刪除現有向量索引...")
            self.vector_store.delete_collection()
            # 重新初始化
            self.vector_store = VectorStore()
        
        # 分批添加文檔以避免記憶體問題
        batch_size = 50  # 減少批次大小以節省記憶體
        successful_batches = 0
        failed_batches = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(documents) + batch_size - 1)//batch_size
            
            logger.info(f"處理批次 {batch_num}/{total_batches}")
            
            try:
                self.vector_store.add_documents(batch)
                successful_batches += 1
            except Exception as e:
                logger.error(f"批次 {batch_num} 處理失敗: {e}")
                failed_batches += 1
                # 繼續處理下一批次
                continue
        
        if failed_batches > 0:
            logger.warning(f"有 {failed_batches} 個批次處理失敗，{successful_batches} 個批次成功")
        
        # 顯示最終統計
        final_stats = self.vector_store.get_collection_stats()
        logger.info(f"✓ 向量索引構建完成")
        logger.info(f"  - 文檔數量: {final_stats['document_count']}")
        logger.info(f"  - 嵌入維度: {final_stats['embedding_dimension']}")
    
    async def test_rag_system(self):
        """測試 RAG 系統"""
        logger.info("開始測試 RAG 系統...")
        
        # 增強的測試問題列表
        test_queries = [
            "五股到林口段的車道寬度是多少？",
            "桃園交流道附近的路段規格如何？",
            "如果在湖口段遇到塞車，有什麼休息站可以等待？",
            "中壢服務區有什麼設施？",
            "國道1號有哪些路段比較危險需要注意？"
        ]
        
        logger.info("執行測試查詢...")
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\n--- 測試 {i}: {query} ---")
            
            try:
                # 使用 RAG 生成回答
                response = await self.rag_chat.chat(query)
                logger.info(f"回答: {response[:200]}...")  # 只顯示前200字符
                
                # 簡短延遲避免請求過於頻繁
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"測試查詢失敗: {e}")
        
        # 顯示對話統計
        stats = self.rag_chat.get_conversation_stats()
        logger.info(f"\n對話統計:")
        logger.info(f"  - 總對話數: {stats['total_conversations']}")
        logger.info(f"  - RAG 使用次數: {stats['rag_usage_count']}")
        logger.info(f"  - RAG 使用率: {stats['rag_usage_rate']:.2%}")
    
    async def interactive_chat(self):
        """互動式聊天"""
        logger.info("啟動互動式聊天模式...")
        logger.info("輸入 'exit' 結束，輸入 'clear' 清除對話歷史")
        
        print("\n" + "="*50)
        print("🚗 高速公路交通助手 - RAG 聊天系統")
        print("="*50)
        
        while True:
            try:
                user_input = input("\n您: ").strip()
                
                if user_input.lower() == 'exit':
                    print("再見！")
                    break
                elif user_input.lower() == 'clear':
                    self.rag_chat.clear_history()
                    print("對話歷史已清除")
                    continue
                elif not user_input:
                    continue
                
                print("助手: ", end="", flush=True)
                
                # 流式回應
                async for chunk in self.rag_chat.stream_chat(user_input):
                    print(chunk, end="", flush=True)
                print()  # 換行
                
            except KeyboardInterrupt:
                print("\n\n再見！")
                break
            except Exception as e:
                print(f"發生錯誤: {e}")
    
    async def run_training_pipeline(self, force_reprocess: bool = False, force_rebuild: bool = False):
        """執行完整的訓練流水線"""
        logger.info("開始執行 RAG 訓練流水線...")
        
        try:
            # 1. 設置組件
            await self.setup_components()
            
            # 2. 處理資料
            processed_data_path = self.process_data(force_reprocess)
            
            # 3. 構建向量索引
            self.build_vector_index(processed_data_path, force_rebuild)
            
            # 4. 測試系統
            await self.test_rag_system()
            
            logger.info("✓ RAG 訓練流水線執行完成")
            
        except Exception as e:
            logger.error(f"訓練流水線執行失敗: {e}")
            raise

async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="RAG 系統訓練腳本")
    parser.add_argument("--mode", choices=["train", "test", "chat"], default="train",
                       help="執行模式: train(訓練), test(測試), chat(聊天)")
    parser.add_argument("--force-reprocess", action="store_true",
                       help="強制重新處理資料")
    parser.add_argument("--force-rebuild", action="store_true",
                       help="強制重建向量索引")
    parser.add_argument("--config", type=str,
                       help="配置文件路徑")
    
    args = parser.parse_args()
    
    # 配置日誌
    logger.add("rag_training.log", rotation="1 day", level="INFO")
    
    # 初始化訓練器
    trainer = RAGTrainer(args.config)
    
    try:
        if args.mode == "train":
            # 訓練模式
            await trainer.run_training_pipeline(args.force_reprocess, args.force_rebuild)
            
        elif args.mode == "test":
            # 測試模式
            await trainer.setup_components()
            await trainer.test_rag_system()
            
        elif args.mode == "chat":
            # 聊天模式
            await trainer.setup_components()
            await trainer.interactive_chat()
            
    except KeyboardInterrupt:
        logger.info("用戶中斷操作")
    except Exception as e:
        logger.error(f"執行失敗: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # 執行主函數
    exit_code = asyncio.run(main())