"""
向量儲存和檢索模組
支援 ChromaDB 和 FAISS 向量資料庫
"""

import os
import json
import numpy as np
import gc
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
try:
    from chromadb.errors import InvalidCollectionException
except ImportError:
    # ChromaDB 較新版本中的異常類名
    try:
        from chromadb.api.types import CollectionNotExistError as InvalidCollectionException
    except ImportError:
        # 如果都找不到，使用通用異常
        InvalidCollectionException = ValueError

# 導入配置管理器
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from train_model.utils.config_manager import get_config_manager

class VectorStore:
    """向量儲存和檢索系統"""
    
    def __init__(self, config_path: str = None):
        """初始化向量儲存系統"""
        # 使用配置管理器
        if config_path:
            os.environ['RAG_CONFIG_PATH'] = config_path
        
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        
        self.embedding_config = self.config['embeddings']
        self.vector_db_config = self.config['vector_db']
        self.retrieval_config = self.config['retrieval']
        
        # 初始化嵌入模型
        self.embedding_model = SentenceTransformer(
            self.embedding_config['model_name'],
            device=self.embedding_config['device']
        )
        
        # 初始化向量資料庫
        self.vector_db = None
        self.collection = None
        self._initialize_vector_db()
        
        logger.info("向量儲存系統初始化完成")
    
    def _initialize_vector_db(self):
        """初始化向量資料庫"""
        if self.vector_db_config['type'] == 'chroma':
            self._initialize_chromadb()
        elif self.vector_db_config['type'] == 'faiss':
            self._initialize_faiss()
        else:
            raise ValueError(f"不支援的向量資料庫類型: {self.vector_db_config['type']}")
    
    def _initialize_chromadb(self):
        """初始化 ChromaDB"""
        persist_dir = self.vector_db_config['persist_directory']
        os.makedirs(persist_dir, exist_ok=True)
        
        # 創建 ChromaDB 客戶端
        self.vector_db = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 獲取或創建集合
        collection_name = self.vector_db_config['collection_name']
        try:
            self.collection = self.vector_db.get_collection(collection_name)
            logger.info(f"載入現有集合: {collection_name}")
        except (InvalidCollectionException, ValueError, Exception) as e:
            logger.info(f"集合不存在，創建新集合: {collection_name}")
            self.collection = self.vector_db.create_collection(
                name=collection_name,
                metadata={"description": "Highway traffic data embeddings"}
            )
        except Exception as e:
            logger.error(f"初始化集合時發生未預期錯誤: {e}")
            raise
    
    def _initialize_faiss(self):
        """初始化 FAISS (暫時佔位，後續可擴展)"""
        # TODO: 實作 FAISS 支援
        raise NotImplementedError("FAISS 支援尚未實作")
    
    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """對文本進行向量化編碼"""
        batch_size = self.embedding_config['batch_size']
        max_length = self.embedding_config['max_length']
        
        # 分批處理以避免記憶體問題
        all_embeddings = []
        try:
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # 編碼
                embeddings = self.embedding_model.encode(
                    batch_texts,
                    batch_size=batch_size,
                    show_progress_bar=True,
                    convert_to_numpy=True,
                    normalize_embeddings=True  # 正規化嵌入向量
                )
                all_embeddings.append(embeddings)
                
                # 定期清理記憶體
                if (i // batch_size + 1) % 10 == 0:
                    gc.collect()
                    logger.debug(f"已處理 {i // batch_size + 1} 個批次，執行記憶體清理")
            
            # 合併所有嵌入
            all_embeddings = np.vstack(all_embeddings)
            logger.info(f"完成 {len(texts)} 個文本的向量化編碼")
            return all_embeddings
        
        except Exception as e:
            logger.error(f"向量化編碼過程中發生錯誤: {e}")
            # 清理記憶體
            gc.collect()
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """添加文檔到向量資料庫"""
        if self.vector_db_config['type'] == 'chroma':
            self._add_documents_chromadb(documents)
        else:
            raise NotImplementedError(f"未實作的向量資料庫類型: {self.vector_db_config['type']}")
    
    def _add_documents_chromadb(self, documents: List[Dict[str, Any]]):
        """添加文檔到 ChromaDB"""
        texts = [doc['text'] for doc in documents]
        ids = [doc['id'] for doc in documents]
        
        # 準備元數據
        metadatas = []
        for doc in documents:
            metadata = {
                'source': doc.get('source', ''),
                'chunk_index': doc.get('chunk_index', 0),
                'original_index': doc.get('original_index', 0)
            }
            metadatas.append(metadata)
        
        # 生成嵌入
        logger.info("正在生成文檔嵌入...")
        try:
            embeddings = self.encode_texts(texts)
            
            # 添加到集合
            logger.info("正在添加文檔到向量資料庫...")
            self.collection.add(
                documents=texts,
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"成功添加 {len(documents)} 個文檔到向量資料庫")
            
        except Exception as e:
            logger.error(f"添加文檔到向量資料庫時發生錯誤: {e}")
            raise
        finally:
            # 清理記憶體
            if 'embeddings' in locals():
                del embeddings
            gc.collect()
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """搜索相關文檔"""
        if top_k is None:
            top_k = self.retrieval_config['top_k']
        
        if self.vector_db_config['type'] == 'chroma':
            return self._search_chromadb(query, top_k)
        else:
            raise NotImplementedError(f"未實作的向量資料庫類型: {self.vector_db_config['type']}")
    
    def _search_chromadb(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """在 ChromaDB 中搜索"""
        try:
            # 生成查詢嵌入
            query_embedding = self.embedding_model.encode(
                [query], 
                normalize_embeddings=True
            )
            
            # 執行搜索
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=min(top_k, 100),  # 限制最大結果數
                include=["documents", "metadatas", "distances"]
            )
            
            # 格式化結果
            formatted_results = []
            if results.get('documents') and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    distance = results['distances'][0][i]
                    # 將距離轉換為相似度 (cosine距離: score = 1 - distance)
                    score = max(0, 1 - distance)
                    
                    result = {
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'score': score,
                        'metadata': results.get('metadatas', [{}])[0][i] if results.get('metadatas') else {}
                    }
                    
                    # 過濾低於閾值的結果
                    if score >= self.retrieval_config['score_threshold']:
                        formatted_results.append(result)
            
            logger.info(f"搜索完成，找到 {len(formatted_results)} 個相關文檔")
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索過程中發生錯誤: {e}")
            return []
        finally:
            # 清理記憶體
            if 'query_embedding' in locals():
                del query_embedding
            gc.collect()
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """獲取集合統計資訊"""
        try:
            if self.vector_db_config['type'] == 'chroma':
                count = self.collection.count()
                return {
                    'document_count': count,
                    'collection_name': self.vector_db_config['collection_name'],
                    'embedding_dimension': self.embedding_model.get_sentence_embedding_dimension(),
                    'vector_db_type': 'chroma',
                    'persist_directory': self.vector_db_config['persist_directory']
                }
            else:
                return {'vector_db_type': self.vector_db_config['type']}
        except Exception as e:
            logger.error(f"獲取統計資訊時發生錯誤: {e}")
            return {'error': str(e)}
    
    def delete_collection(self):
        """刪除整個集合 (謹慎使用)"""
        try:
            if self.vector_db_config['type'] == 'chroma':
                collection_name = self.vector_db_config['collection_name']
                self.vector_db.delete_collection(collection_name)
                logger.warning(f"已刪除集合: {collection_name}")
                # 重置集合引用
                self.collection = None
        except Exception as e:
            logger.error(f"刪除集合時發生錯誤: {e}")
            raise

class RAGRetriever:
    """RAG 檢索器"""
    
    def __init__(self, vector_store: VectorStore):
        """初始化檢索器"""
        self.vector_store = vector_store
        self.config = vector_store.config
        
    def retrieve_context(self, query: str, max_context_length: int = 2000) -> str:
        """檢索相關上下文"""
        # 搜索相關文檔
        results = self.vector_store.search(query)
        
        # 組合上下文
        context_parts = []
        current_length = 0
        
        for result in results:
            text = result['text']
            if current_length + len(text) <= max_context_length:
                context_parts.append(text)
                current_length += len(text)
            else:
                # 如果超出長度限制，截斷最後一個文本
                remaining_length = max_context_length - current_length
                if remaining_length > 100:  # 至少保留100個字符
                    context_parts.append(text[:remaining_length])
                break
        
        context = "\n\n".join(context_parts)
        logger.info(f"檢索到 {len(context_parts)} 個文檔片段，總長度: {len(context)} 字符")
        return context

if __name__ == "__main__":
    # 測試向量儲存系統
    vector_store = VectorStore()
    print("向量儲存系統測試:")
    print(f"集合統計: {vector_store.get_collection_stats()}")
    
    # 測試搜索
    query = "國道一號車道寬度"
    results = vector_store.search(query, top_k=3)
    print(f"\n搜索查詢: {query}")
    for i, result in enumerate(results, 1):
        print(f"{i}. 相似度: {result['score']:.3f}")
        print(f"   文本: {result['text'][:100]}...")
        print(f"   來源: {result['metadata']}")