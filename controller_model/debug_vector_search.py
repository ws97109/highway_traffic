#!/usr/bin/env python3
"""
調試向量檢索問題
檢查為什麼搜索返回 0 個文檔
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from train_model.embeddings.vector_store import VectorStore
from train_model.utils.config_manager import get_config_manager

def debug_vector_search():
    """調試向量檢索"""
    print("🔍 開始調試向量檢索...")
    
    try:
        # 初始化向量存儲
        vector_store = VectorStore()
        
        # 檢查集合統計
        stats = vector_store.get_collection_stats()
        print(f"📊 向量資料庫統計:")
        print(f"   文檔數量: {stats['document_count']}")
        print(f"   嵌入維度: {stats['embedding_dimension']}")
        
        # 測試簡單查詢
        test_queries = [
            "車道",
            "國道",
            "路幅",
            "highway",
            "lane"
        ]
        
        print(f"\n🧪 測試基本檢索...")
        for query in test_queries:
            print(f"\n測試查詢: '{query}'")
            
            try:
                # 直接使用向量存儲搜索
                results = vector_store.search(query, top_k=3)
                print(f"   結果數量: {len(results)}")
                
                if results:
                    for i, result in enumerate(results[:2]):
                        content = result.get('content', result.get('text', ''))[:100]
                        score = result.get('score', result.get('distance', 0))
                        print(f"   {i+1}. 分數: {score:.3f}")
                        print(f"      內容: {content}...")
                else:
                    print("   ❌ 未找到任何結果")
                    
            except Exception as e:
                print(f"   ❌ 查詢失敗: {e}")
        
        # 檢查集合內容樣本
        print(f"\n📋 檢查集合內容樣本...")
        try:
            # 嘗試獲取一些文檔樣本
            collection = vector_store.collection
            if hasattr(collection, 'peek'):
                sample = collection.peek(limit=3)
                print(f"   樣本文檔數: {len(sample.get('documents', []))}")
                
                for i, doc in enumerate(sample.get('documents', [])[:2]):
                    print(f"   文檔 {i+1}: {doc[:100]}...")
            else:
                print("   無法獲取文檔樣本")
                
        except Exception as e:
            print(f"   ❌ 獲取樣本失敗: {e}")
        
        # 檢查嵌入模型
        print(f"\n🤖 檢查嵌入模型...")
        try:
            test_text = "國道一號車道寬度"
            embedding = vector_store.encode_texts([test_text])
            print(f"   測試文本: '{test_text}'")
            print(f"   嵌入維度: {embedding.shape}")
            print(f"   嵌入範圍: [{embedding.min():.3f}, {embedding.max():.3f}]")
        except Exception as e:
            print(f"   ❌ 嵌入測試失敗: {e}")
        
        # 檢查配置
        print(f"\n⚙️ 檢查配置...")
        config_manager = get_config_manager()
        config = config_manager.get_config()
        
        print(f"   向量資料庫類型: {config['vector_db']['type']}")
        print(f"   集合名稱: {config['vector_db']['collection_name']}")
        print(f"   嵌入模型: {config['embeddings']['model_name']}")
        print(f"   檢索 top_k: {config['retrieval']['top_k']}")
        print(f"   分數閾值: {config['retrieval']['score_threshold']}")
        
    except Exception as e:
        print(f"❌ 調試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_vector_search()