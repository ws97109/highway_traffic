#!/usr/bin/env python3
"""
調試 ChromaDB 向量資料庫連接問題
"""
import sys
import os
sys.path.append('.')

def debug_chromadb():
    print("🔍 調試 ChromaDB 連接問題...")
    
    # 1. 檢查檔案系統
    vector_db_path = "train_model/vector_db"
    print(f"\n1️⃣ 檢查向量資料庫目錄:")
    print(f"   路徑: {vector_db_path}")
    print(f"   存在: {os.path.exists(vector_db_path)}")
    
    if os.path.exists(vector_db_path):
        files = list(os.listdir(vector_db_path))
        print(f"   檔案數量: {len(files)}")
        if files:
            print(f"   前5個檔案: {files[:5]}")
    
    # 2. 測試 VectorStore 初始化
    print(f"\n2️⃣ 測試 VectorStore 初始化:")
    try:
        from train_model.embeddings.vector_store import VectorStore
        vs = VectorStore()
        print("   ✅ VectorStore 初始化成功")
        
        # 檢查 collection
        print(f"\n3️⃣ 檢查 Collection:")
        print(f"   Collection 物件: {type(vs.collection)}")
        print(f"   Collection 是否為 None: {vs.collection is None}")
        
        if vs.collection is not None:
            # 嘗試獲取 collection 資訊
            try:
                count = vs.collection.count()
                print(f"   文檔數量: {count}")
            except Exception as e:
                print(f"   ❌ 無法獲取文檔數量: {e}")
        
        # 4. 測試統計功能
        print(f"\n4️⃣ 測試統計功能:")
        try:
            stats = vs.get_collection_stats()
            print(f"   ✅ 統計資料: {stats}")
        except Exception as e:
            print(f"   ❌ 獲取統計失敗: {e}")
            import traceback
            traceback.print_exc()
        
        # 5. 測試搜索功能
        print(f"\n5️⃣ 測試搜索功能:")
        try:
            # 先測試簡單搜索
            results = vs.search("測試", top_k=1)
            print(f"   ✅ 搜索成功，結果數量: {len(results)}")
        except Exception as e:
            print(f"   ❌ 搜索失敗: {e}")
            import traceback
            traceback.print_exc()
            
        # 6. 檢查 ChromaDB 客戶端
        print(f"\n6️⃣ 檢查 ChromaDB 客戶端:")
        print(f"   Client 類型: {type(vs.client)}")
        print(f"   Client 是否為 None: {vs.client is None}")
        
        if hasattr(vs, 'config'):
            print(f"   配置: {vs.config.get('vector_store', {})}")
            
    except Exception as e:
        print(f"   ❌ VectorStore 初始化失敗: {e}")
        import traceback
        traceback.print_exc()

def test_direct_chromadb():
    """直接測試 ChromaDB"""
    print(f"\n🧪 直接測試 ChromaDB:")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # 使用相同的設定初始化 ChromaDB
        db_path = "train_model/vector_db"
        client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        print(f"   ✅ ChromaDB 客戶端建立成功")
        
        # 列出所有 collections
        collections = client.list_collections()
        print(f"   Collections 數量: {len(collections)}")
        
        for i, collection in enumerate(collections):
            print(f"   Collection {i+1}: {collection.name}")
            try:
                count = collection.count()
                print(f"     文檔數量: {count}")
                
                # 測試查詢
                if count > 0:
                    result = collection.query(
                        query_texts=["測試"],
                        n_results=1
                    )
                    print(f"     查詢測試: 成功")
                    
            except Exception as e:
                print(f"     ❌ Collection 操作失敗: {e}")
                
    except Exception as e:
        print(f"   ❌ 直接 ChromaDB 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_chromadb()
    test_direct_chromadb()