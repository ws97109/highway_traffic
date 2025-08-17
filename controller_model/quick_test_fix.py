#!/usr/bin/env python3
"""
快速測試修復後的 VectorStore
"""

import sys
import os
sys.path.append('.')

def test_fixed_vectorstore():
    """測試修復後的 VectorStore"""
    print("🔧 測試修復後的 VectorStore...")
    
    try:
        from train_model.embeddings.vector_store import VectorStore
        
        # 初始化 VectorStore
        print("初始化 VectorStore...")
        vs = VectorStore()
        
        # 檢查統計資訊
        stats = vs.get_collection_stats()
        print(f"\n📊 集合統計:")
        print(f"   文檔數量: {stats['document_count']}")
        print(f"   集合名稱: {stats['collection_name']}")
        print(f"   資料庫路徑: {stats['persist_directory']}")
        
        if stats['document_count'] > 0:
            print(f"✅ 成功！找到 {stats['document_count']} 個文檔")
            
            # 測試搜索
            print(f"\n🔍 測試搜索功能...")
            vs.retrieval_config['score_threshold'] = 0.3
            
            test_queries = [
                "五股-林口段",
                "交通瓶頸分析", 
                "國道一號",
                "車道寬度"
            ]
            
            for query in test_queries:
                try:
                    results = vs.search(query, top_k=3)
                    print(f"\n查詢: '{query}' -> {len(results)} 個結果")
                    
                    for i, result in enumerate(results, 1):
                        data_type = 'JSON分析' if '交通分析報告' in result['text'] else 'CSV路段'
                        print(f"  {i}. 分數: {result['score']:.3f} | 類型: {data_type}")
                        print(f"     內容: {result['text'][:120]}...")
                    
                    if results:
                        print(f"🎉 搜索功能正常工作！")
                        break
                        
                except Exception as e:
                    print(f"❌ 搜索 '{query}' 失敗: {e}")
            
            return True
        else:
            print("❌ 修復失敗，集合仍然為空")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def manual_fix_if_needed():
    """如果自動修復失敗，提供手動修復方案"""
    print(f"\n🔍 檢查是否需要手動修復...")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # 可能的路徑
        possible_paths = [
            './vector_db',
            'train_model/vector_db',
            '/Users/tommy/Desktop/Highway_trafficwave/train_model/vector_db',
            '/Users/tommy/Desktop/Highway_trafficwave/vector_db'
        ]
        
        best_collection = None
        best_count = 0
        best_path = None
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    client = chromadb.PersistentClient(
                        path=path,
                        settings=Settings(anonymized_telemetry=False)
                    )
                    collections = client.list_collections()
                    
                    for coll in collections:
                        count = coll.count()
                        if count > best_count:
                            best_collection = coll
                            best_count = count
                            best_path = path
                            
                except Exception as e:
                    continue
        
        if best_collection:
            print(f"🎯 找到最佳集合:")
            print(f"   路徑: {best_path}")
            print(f"   集合: {best_collection.name}")
            print(f"   文檔數: {best_count}")
            
            # 提供手動修復代碼
            print(f"\n💡 手動修復代碼:")
            print(f"""
# 手動修復 VectorStore
from train_model.embeddings.vector_store import VectorStore
import chromadb
from chromadb.config import Settings

vs = VectorStore()
client = chromadb.PersistentClient(
    path='{best_path}',
    settings=Settings(anonymized_telemetry=False)
)
vs.vector_db = client
vs.collection = client.get_collection('{best_collection.name}')

# 測試
print(f"修復後文檔數: {{vs.collection.count()}}")
""")
            return best_path, best_collection.name
        else:
            print("❌ 沒有找到任何有資料的集合")
            return None, None
            
    except Exception as e:
        print(f"❌ 檢查失敗: {e}")
        return None, None

def main():
    """主函數"""
    print("🚀 開始測試修復後的 VectorStore...")
    
    # 1. 測試修復結果
    success = test_fixed_vectorstore()
    
    # 2. 如果失敗，提供手動修復方案
    if not success:
        print(f"\n" + "="*50)
        best_path, best_collection = manual_fix_if_needed()
        
        if best_path and best_collection:
            print(f"\n🔧 嘗試執行手動修復...")
            try:
                from train_model.embeddings.vector_store import VectorStore
                import chromadb
                from chromadb.config import Settings
                
                vs = VectorStore()
                client = chromadb.PersistentClient(
                    path=best_path,
                    settings=Settings(anonymized_telemetry=False)
                )
                vs.vector_db = client
                vs.collection = client.get_collection(best_collection)
                
                print(f"✅ 手動修復成功！文檔數: {vs.collection.count()}")
                
                # 測試搜索
                vs.retrieval_config['score_threshold'] = 0.3
                results = vs.search("五股-林口段", top_k=3)
                print(f"🔍 搜索測試: 找到 {len(results)} 個結果")
                
                for i, result in enumerate(results, 1):
                    print(f"  {i}. 分數: {result['score']:.3f}")
                    print(f"     內容: {result['text'][:100]}...")
                
            except Exception as e:
                print(f"❌ 手動修復失敗: {e}")

if __name__ == "__main__":
    main()