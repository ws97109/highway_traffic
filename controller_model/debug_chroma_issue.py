#!/usr/bin/env python3
"""
調試 ChromaDB 集合問題
檢查為什麼集合對象為 None
"""

import os
import sys
sys.path.append('/Users/tommy/Desktop/Highway_trafficwave')

def debug_chromadb_collection():
    """調試 ChromaDB 集合問題"""
    print("🔍 調試 ChromaDB 集合問題...")
    
    try:
        from train_model.embeddings.vector_store import VectorStore
        
        # 初始化向量存儲
        print("1. 初始化向量存儲...")
        vector_store = VectorStore()
        
        # 檢查集合對象
        print(f"2. 集合對象: {vector_store.collection}")
        print(f"3. 向量資料庫對象: {vector_store.vector_db}")
        
        if vector_store.collection is None:
            print("❌ 集合對象為 None！")
            
            # 嘗試手動重新初始化
            print("4. 嘗試手動重新初始化...")
            vector_store._initialize_vector_db()
            print(f"   重新初始化後集合: {vector_store.collection}")
        
        # 檢查集合統計
        if vector_store.collection:
            print("5. 檢查集合統計...")
            stats = vector_store.get_collection_stats()
            print(f"   文檔數量: {stats['document_count']}")
            print(f"   嵌入維度: {stats['embedding_dimension']}")
            
            # 嘗試檢視集合內容
            try:
                sample = vector_store.collection.peek(limit=2)
                print(f"   樣本文檔: {len(sample.get('documents', []))}")
                if sample.get('documents'):
                    print(f"   第一個文檔預覽: {sample['documents'][0][:100]}...")
            except Exception as e:
                print(f"   ❌ 無法獲取樣本: {e}")
        
        # 測試簡單搜索
        print("6. 測試簡單搜索...")
        try:
            results = vector_store.search("國道", top_k=2)
            print(f"   搜索結果數量: {len(results)}")
            if results:
                print(f"   第一個結果: {results[0]}")
            else:
                print("   ❌ 搜索無結果")
        except Exception as e:
            print(f"   ❌ 搜索失敗: {e}")
        
        # 檢查配置
        print("7. 檢查配置...")
        print(f"   資料庫類型: {vector_store.vector_db_config['type']}")
        print(f"   集合名稱: {vector_store.vector_db_config['collection_name']}")
        print(f"   持久化目錄: {vector_store.vector_db_config['persist_directory']}")
        
        # 檢查持久化目錄
        persist_dir = vector_store.vector_db_config['persist_directory']
        if os.path.exists(persist_dir):
            files = os.listdir(persist_dir)
            print(f"   持久化目錄內容: {files}")
        else:
            print(f"   ❌ 持久化目錄不存在: {persist_dir}")
            
    except Exception as e:
        print(f"❌ 調試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()

def debug_enhanced_data():
    """檢查增強資料是否正確生成"""
    print("\n🔍 檢查增強資料...")
    
    try:
        import json
        
        # 檢查增強資料檔案
        enhanced_file = "/Users/tommy/Desktop/Highway_trafficwave/train_model/configs/processed_data/enhanced_highway_data.json"
        
        if os.path.exists(enhanced_file):
            print(f"✅ 增強資料檔案存在: {enhanced_file}")
            
            # 檢查檔案大小
            size = os.path.getsize(enhanced_file)
            print(f"   檔案大小: {size / 1024 / 1024:.1f} MB")
            
            # 載入並檢查內容
            with open(enhanced_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"   資料項目數量: {len(data)}")
            
            # 檢查前幾個項目的結構
            if data:
                sample = data[0]
                print(f"   樣本項目鍵: {list(sample.keys())}")
                print(f"   友善位置: {sample.get('friendly_location', 'N/A')}")
                print(f"   文本預覽: {sample.get('text', '')[:100]}...")
                
                # 檢查有多少項目有友善位置
                friendly_count = sum(1 for item in data[:100] if item.get('friendly_location'))
                print(f"   前100項中有友善位置的: {friendly_count}")
                
        else:
            print(f"❌ 增強資料檔案不存在: {enhanced_file}")
            
    except Exception as e:
        print(f"❌ 檢查增強資料失敗: {e}")

if __name__ == "__main__":
    debug_chromadb_collection()
    debug_enhanced_data()