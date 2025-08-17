#!/usr/bin/env python3
"""
直接測試 RAG 系統
繞過 train_rag.py 中的問題
"""

import sys
import asyncio
sys.path.append('/Users/tommy/Desktop/Highway_trafficwave')

async def test_rag_direct():
    """直接測試 RAG 系統"""
    print("🚀 直接測試 RAG 系統...")
    
    try:
        # 直接初始化組件
        from train_model.embeddings.vector_store import VectorStore
        from train_model.models.ollama_client import OllamaClient, RAGOllamaChat
        
        print("1. 初始化向量存儲...")
        vector_store = VectorStore()
        
        print("2. 檢查向量存儲狀態...")
        stats = vector_store.get_collection_stats()
        print(f"   - 文檔數量: {stats['document_count']}")
        print(f"   - 集合對象: {vector_store.collection}")
        
        if vector_store.collection is None:
            print("❌ 集合對象為 None，嘗試重新初始化...")
            vector_store._initialize_vector_db()
            print(f"   - 重新初始化後: {vector_store.collection}")
        
        print("3. 測試向量檢索...")
        results = vector_store.search("五股林口段車道寬度", top_k=3)
        print(f"   - 找到 {len(results)} 個結果")
        
        if results:
            for i, result in enumerate(results):
                print(f"   {i+1}. 分數: {result['score']:.3f}")
                print(f"      內容: {result['text'][:100]}...")
        
        print("4. 初始化 Ollama 客戶端...")
        ollama_client = OllamaClient()
        
        print("5. 檢查 Ollama 連接...")
        is_connected = await ollama_client.check_connection()
        if not is_connected:
            print("❌ Ollama 連接失敗")
            return
        
        print("6. 初始化 RAG 聊天系統...")
        from train_model.embeddings.vector_store import RAGRetriever
        retriever = RAGRetriever(vector_store)
        rag_chat = RAGOllamaChat(ollama_client, retriever)
        
        print("7. 測試 RAG 對話...")
        test_questions = [
            "五股到林口段的車道寬度是多少？",
            "國道一號有哪些休息站？",
            "湖口段的路況如何？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n--- 測試 {i}: {question} ---")
            
            try:
                # 先測試檢索
                retrieved_docs = retriever.retrieve_context(question)
                print(f"檢索到 {len(retrieved_docs)} 個文檔")
                
                if retrieved_docs:
                    print(f"檢索示例: {str(retrieved_docs[0])[:100]}...")
                
                # 測試完整對話
                response = await rag_chat.chat(question)
                print(f"回答: {response[:200]}...")
                
                # 檢查 RAG 使用情況
                stats = rag_chat.get_conversation_stats()
                print(f"RAG 使用率: {stats['rag_usage_rate']:.2%}")
                
            except Exception as e:
                print(f"❌ 測試失敗: {e}")
                import traceback
                traceback.print_exc()
            
            print()
        
        print("✅ 直接測試完成！")
        
    except Exception as e:
        print(f"❌ 直接測試失敗: {e}")
        import traceback
        traceback.print_exc()

async def interactive_chat():
    """互動聊天模式"""
    print("🎪 啟動互動聊天模式...")
    
    try:
        # 初始化組件
        from train_model.embeddings.vector_store import VectorStore, RAGRetriever
        from train_model.models.ollama_client import OllamaClient, RAGOllamaChat
        
        vector_store = VectorStore()
        ollama_client = OllamaClient()
        retriever = RAGRetriever(vector_store)
        rag_chat = RAGOllamaChat(ollama_client, retriever)
        
        print("系統初始化完成！")
        print("輸入 'quit' 或 'exit' 結束對話")
        print("=" * 50)
        
        while True:
            question = input("\n您的問題: ")
            
            if question.lower() in ['quit', 'exit', '退出']:
                print("再見！")
                break
            
            if not question.strip():
                continue
            
            try:
                print("🤖 正在思考...")
                response = await rag_chat.chat(question)
                print(f"\n回答: {response}")
                
                # 顯示統計
                stats = rag_chat.get_conversation_stats()
                print(f"\n[統計] RAG 使用率: {stats['rag_usage_rate']:.1%}")
                
            except Exception as e:
                print(f"❌ 回答失敗: {e}")
        
    except Exception as e:
        print(f"❌ 聊天系統初始化失敗: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="直接測試 RAG 系統")
    parser.add_argument("--mode", choices=["test", "chat"], default="test",
                        help="運行模式: test=測試, chat=聊天")
    
    args = parser.parse_args()
    
    if args.mode == "test":
        asyncio.run(test_rag_direct())
    else:
        asyncio.run(interactive_chat())