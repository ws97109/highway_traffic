#!/usr/bin/env python3
"""
簡化的 RAG 系統啟動腳本
避免複雜的依賴檢查，直接啟動系統
"""

import os
import sys
import asyncio
from pathlib import Path

# 設定路徑
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("🚀 簡化 RAG 系統啟動腳本")
print("=" * 50)

async def simple_test():
    """簡單測試系統組件"""
    print("正在測試系統組件...")
    
    try:
        # 測試配置管理器
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        print("✓ 配置管理器正常")
        
        # 測試 Ollama 客戶端
        from models.ollama_client import OllamaClient
        ollama_client = OllamaClient()
        print("✓ Ollama 客戶端初始化成功")
        
        # 檢查 Ollama 連接
        is_connected = await ollama_client.check_connection()
        if is_connected:
            print("✓ Ollama 服務連接成功")
        else:
            print("⚠ Ollama 服務未連接")
            print("請執行：")
            print("1. ollama serve")
            print("2. ollama pull deepseek-r1:32b")
            return False
        
        # 測試向量存儲
        from embeddings.vector_store import VectorStore, RAGRetriever
        vector_store = VectorStore()
        stats = vector_store.get_collection_stats()
        print(f"✓ 向量存儲正常 ({stats.get('document_count', 0)} 個文檔)")
        
        # 測試 CSV 處理器
        from data_processing.csv_processor import HighwayCSVProcessor
        csv_processor = HighwayCSVProcessor()
        print("✓ CSV 處理器正常")
        
        return True
        
    except Exception as e:
        print(f"✗ 系統測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def start_training():
    """啟動訓練流程"""
    print("\\n開始 RAG 系統訓練...")
    
    try:
        from scripts.train_rag import RAGTrainer
        trainer = RAGTrainer()
        
        # 執行完整訓練流程
        await trainer.run_training_pipeline(force_reprocess=False, force_rebuild=False)
        print("✓ 訓練完成")
        return True
        
    except Exception as e:
        print(f"✗ 訓練失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def start_chat():
    """啟動聊天功能"""
    print("\\n啟動互動聊天...")
    
    try:
        from scripts.train_rag import RAGTrainer
        trainer = RAGTrainer()
        
        # 設置組件
        await trainer.setup_components()
        
        # 啟動聊天
        await trainer.interactive_chat()
        
    except Exception as e:
        print(f"✗ 聊天啟動失敗: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函數"""
    # 1. 基本系統測試
    if not await simple_test():
        print("\\n系統測試失敗，請修復問題後重試")
        return
    
    print("\\n" + "=" * 50)
    print("系統就緒！請選擇操作：")
    print("1. 訓練系統 (train)")
    print("2. 開始聊天 (chat)")
    print("3. 測試系統 (test)")
    print("4. 退出 (exit)")
    
    while True:
        try:
            choice = input("\\n請輸入選擇 (1-4): ").strip()
            
            if choice in ['1', 'train']:
                success = await start_training()
                if success:
                    print("\\n訓練完成，現在可以開始聊天了！")
                    continue
                    
            elif choice in ['2', 'chat']:
                await start_chat()
                
            elif choice in ['3', 'test']:
                from scripts.train_rag import RAGTrainer
                trainer = RAGTrainer()
                await trainer.setup_components()
                await trainer.test_rag_system()
                
            elif choice in ['4', 'exit']:
                print("再見！")
                break
                
            else:
                print("無效選擇，請輸入 1-4")
                continue
                
        except KeyboardInterrupt:
            print("\\n\\n再見！")
            break
        except Exception as e:
            print(f"操作失敗: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n程序被用戶中斷")
    except Exception as e:
        print(f"\\n程序執行失敗: {e}")
        import traceback
        traceback.print_exc()