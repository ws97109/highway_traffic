"""
快速測試增強 RAG 系統
僅處理少量資料進行快速驗證
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from loguru import logger
from datetime import datetime

# 添加項目路徑
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# 導入增強的模組
from train_model.data_processing.enhanced_csv_processor import EnhancedHighwayCSVProcessor
from train_model.embeddings.vector_store import VectorStore, RAGRetriever
from train_model.models.ollama_client import OllamaClient, RAGOllamaChat
from train_model.models.driver_advisor import IntelligentDriverAdvisor

class QuickEnhancedRAGTester:
    """快速增強 RAG 系統測試器"""
    
    def __init__(self, config_path: str = None):
        """初始化快速測試器"""
        if config_path is None:
            config_path = current_dir.parent / "configs" / "rag_config.yaml"
        
        self.config_path = str(config_path)
        
        # 初始化組件
        self.enhanced_processor = None
        self.vector_store = None
        self.ollama_client = None
        self.rag_chat = None
        
        logger.info("快速增強RAG測試器初始化完成")
    
    async def setup_components(self):
        """設置所有增強組件"""
        logger.info("正在設置增強RAG系統組件...")
        
        # 初始化增強 CSV 處理器
        self.enhanced_processor = EnhancedHighwayCSVProcessor(self.config_path)
        logger.info("✓ 增強CSV處理器初始化完成")
        
        # 初始化向量儲存
        self.vector_store = VectorStore(self.config_path)
        logger.info("✓ 向量儲存系統初始化完成")
        
        # 初始化 Ollama 客戶端
        self.ollama_client = OllamaClient(self.config_path)
        
        # 檢查 Ollama 連接
        if not await self.ollama_client.check_connection():
            raise Exception("Ollama 服務連接失敗，請確保服務正在運行")
        logger.info("✓ Ollama 客戶端初始化完成")
        
        # 初始化檢索器和聊天系統
        retriever = RAGRetriever(self.vector_store)
        self.rag_chat = RAGOllamaChat(self.ollama_client, retriever)
        logger.info("✓ RAG 聊天系統初始化完成")
    
    def process_sample_data(self, sample_size: int = 100):
        """處理少量樣本資料"""
        logger.info(f"開始處理樣本資料（{sample_size} 筆）...")
        
        # 載入資料
        highway1_df, highway3_df = self.enhanced_processor.load_highway_data()
        
        # 只取前面的樣本
        highway1_sample = highway1_df.head(sample_size // 2)
        highway3_sample = highway3_df.head(sample_size // 2)
        
        logger.info(f"國道1號樣本: {len(highway1_sample)} 筆")
        logger.info(f"國道3號樣本: {len(highway3_sample)} 筆")
        
        # 清理樣本資料
        highway1_clean = self.enhanced_processor.clean_and_normalize_data(highway1_sample)
        highway3_clean = self.enhanced_processor.clean_and_normalize_data(highway3_sample)
        
        # 生成增強的文字描述
        highway1_texts = self.enhanced_processor.generate_enhanced_text_descriptions(highway1_clean)
        highway3_texts = self.enhanced_processor.generate_enhanced_text_descriptions(highway3_clean)
        
        # 合併所有文本
        all_texts = highway1_texts + highway3_texts
        
        # 分割文本並添加元數據
        processed_data = []
        for i, text in enumerate(all_texts):
            chunks = self.enhanced_processor.chunk_text(text)
            
            # 確定來源和基本資訊
            source = 'highway1' if i < len(highway1_texts) else 'highway3'
            
            # 從原始資料獲取位置資訊
            if source == 'highway1':
                row = highway1_clean.iloc[i]
            else:
                row = highway3_clean.iloc[i - len(highway1_texts)]
            
            # 解析位置資訊
            direction_code = str(row['國道編號方向'])
            mileage_num = float(row['里程']) / 1000
            
            for j, chunk in enumerate(chunks):
                processed_data.append({
                    'id': f'{source}_sample_{i}_{j}',
                    'text': chunk,
                    'source': source,
                    'chunk_index': j,
                    'original_index': i,
                    'highway': '國道1號' if 'N0010' in direction_code else '國道3號',
                    'direction': '北向' if 'NB' in direction_code else '南向',
                    'mileage': mileage_num,
                    'station_code': f"{row['國道編號方向']},{row['樁號']}",
                    'friendly_location': self.enhanced_processor.resolve_station_code(f"{row['國道編號方向']},{row['樁號']}"),
                    'coordinates': {
                        'lat': float(row['經緯度坐標Lat']) if row['經緯度坐標Lat'] else None,
                        'lng': float(row['經緯度坐標Lon']) if row['經緯度坐標Lon'] else None
                    }
                })
        
        logger.info(f"樣本處理完成，總共生成 {len(processed_data)} 個文本塊")
        return processed_data
    
    def build_sample_vector_index(self, processed_data: list):
        """構建樣本向量索引"""
        logger.info("開始構建樣本向量索引...")
        
        # 清除現有索引
        stats = self.vector_store.get_collection_stats()
        if stats['document_count'] > 0:
            logger.info("清除現有索引...")
            self.vector_store.delete_collection()
            # 重新初始化
            self.vector_store = VectorStore(self.config_path)
        
        # 分批添加樣本文檔
        batch_size = 10  # 小批次測試
        successful_batches = 0
        total_added = 0
        
        for i in range(0, len(processed_data), batch_size):
            batch = processed_data[i:i + batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(processed_data) + batch_size - 1)//batch_size
            
            logger.info(f"處理樣本批次 {batch_num}/{total_batches} (包含 {len(batch)} 個文檔)")
            
            try:
                # 為每個文檔添加增強元數據
                enhanced_batch = []
                for doc in batch:
                    enhanced_doc = {
                        'text': doc['text'],
                        'id': doc['id'],
                        'metadata': {
                            'highway': doc.get('highway', ''),
                            'direction': doc.get('direction', ''),
                            'mileage': doc.get('mileage', 0),
                            'friendly_location': doc.get('friendly_location', ''),
                            'station_code': doc.get('station_code', ''),
                            'source': doc.get('source', ''),
                            'coordinates': doc.get('coordinates', {})
                        }
                    }
                    enhanced_batch.append(enhanced_doc)
                
                self.vector_store.add_documents(enhanced_batch)
                successful_batches += 1
                total_added += len(batch)
                
                logger.info(f"  ✓ 批次 {batch_num} 成功添加 {len(batch)} 個文檔")
                
            except Exception as e:
                logger.error(f"批次 {batch_num} 處理失敗: {e}")
                continue
        
        # 顯示最終統計
        final_stats = self.vector_store.get_collection_stats()
        logger.info(f"✓ 樣本向量索引構建完成")
        logger.info(f"  - 成功批次: {successful_batches}/{(len(processed_data) + batch_size - 1)//batch_size}")
        logger.info(f"  - 總添加文檔: {total_added}")
        logger.info(f"  - 最終文檔數量: {final_stats['document_count']}")
        logger.info(f"  - 嵌入維度: {final_stats['embedding_dimension']}")
    
    async def test_enhanced_rag_system(self):
        """測試增強的 RAG 系統"""
        logger.info("開始測試增強RAG系統...")
        
        # 測試問題
        test_queries = [
            "五股交流道附近的路段規格如何？",
            "如果在林口段遇到塞車，有什麼建議？",
            "國道1號有哪些休息站？",
            "中壢服務區有什麼設施？",
            "桃園交流道到內壢段的路況特色？"
        ]
        
        logger.info(f"執行 {len(test_queries)} 個測試查詢...")
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\n--- 測試 {i}: {query} ---")
            
            try:
                start_time = datetime.now()
                response = await self.rag_chat.chat(query)
                end_time = datetime.now()
                
                response_time = (end_time - start_time).total_seconds()
                
                logger.info(f"回應時間: {response_time:.2f}秒")
                logger.info(f"回答預覽: {response[:300]}...")
                
            except Exception as e:
                logger.error(f"測試查詢失敗: {e}")
        
        # 顯示對話統計
        stats = self.rag_chat.get_conversation_stats()
        logger.info(f"\n測試完成統計:")
        logger.info(f"  - 總對話數: {stats['total_conversations']}")
        logger.info(f"  - RAG 使用次數: {stats['rag_usage_count']}")
        logger.info(f"  - RAG 使用率: {stats['rag_usage_rate']:.2%}")
    
    async def test_driver_advisor(self):
        """測試駕駛建議系統"""
        logger.info("開始測試駕駛建議系統...")
        
        try:
            # 初始化駕駛建議系統
            driver_advisor = IntelligentDriverAdvisor(self.config_path)
            await driver_advisor.initialize()
            
            # 模擬駕駛情境
            from train_model.models.driver_advisor import TrafficCondition, ShockwaveAlert
            from datetime import timedelta
            
            current_location = {
                'highway': '國道1號',
                'direction': '南向',
                'mileage': 85.5,
                'station_id': '01F0855S',
                'friendly_name': '湖口至新豐',
                'lat': 24.123456,
                'lng': 121.123456
            }
            
            destination = {
                'name': '台中市',
                'distance_km': 150,
                'estimated_time_min': 120
            }
            
            traffic_data = TrafficCondition(
                station_id='01F0855S',
                speed=35.5,
                flow=1200,
                travel_time=8.5,
                congestion_level='congested',
                timestamp=datetime.now()
            )
            
            shockwave_alert = ShockwaveAlert(
                intensity=7.2,
                propagation_speed=25.0,
                estimated_arrival=datetime.now() + timedelta(minutes=15),
                affected_area='湖口至新竹段',
                warning_level='high'
            )
            
            # 獲取駕駛建議
            advice = await driver_advisor.analyze_current_situation(
                current_location, destination, traffic_data, shockwave_alert
            )
            
            logger.info(f"駕駛建議測試成功:")
            logger.info(f"  - 優先級: {advice.priority}")
            logger.info(f"  - 建議行動: {advice.action_type}")
            logger.info(f"  - 標題: {advice.title}")
            logger.info(f"  - 描述: {advice.description[:100]}...")
            logger.info(f"  - 安全評估: {advice.safety_impact}")
            logger.info(f"  - 附近休息站: {len(advice.rest_areas)} 個")
            logger.info(f"  - 替代路線: {len(advice.alternatives)} 個")
            
            return True
            
        except Exception as e:
            logger.error(f"駕駛建議系統測試失敗: {e}")
            return False
    
    async def run_quick_test_pipeline(self, sample_size: int = 100):
        """執行快速測試流水線"""
        logger.info("開始執行快速測試流水線...")
        
        try:
            start_time = datetime.now()
            
            # 1. 設置組件
            logger.info("步驟 1/5: 設置組件...")
            await self.setup_components()
            
            # 2. 處理樣本資料
            logger.info("步驟 2/5: 處理樣本資料...")
            sample_data = self.process_sample_data(sample_size)
            
            # 3. 構建樣本索引
            logger.info("步驟 3/5: 構建樣本索引...")
            self.build_sample_vector_index(sample_data)
            
            # 4. 測試 RAG 系統
            logger.info("步驟 4/5: 測試 RAG 系統...")
            await self.test_enhanced_rag_system()
            
            # 5. 測試駕駛建議系統
            logger.info("步驟 5/5: 測試駕駛建議系統...")
            advisor_success = await self.test_driver_advisor()
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("✓ 快速測試流水線執行完成")
            logger.info(f"總耗時: {duration.total_seconds():.1f} 秒")
            logger.info(f"樣本資料量: {len(sample_data)} 個文本塊")
            logger.info(f"駕駛建議系統: {'正常' if advisor_success else '異常'}")
            
            # 顯示成功測試的範例
            if sample_data:
                logger.info("\n=== 範例增強描述 ===")
                for i in range(min(2, len(sample_data))):
                    logger.info(f"\n位置: {sample_data[i]['friendly_location']}")
                    logger.info(f"文本預覽: {sample_data[i]['text'][:200]}...")
            
        except Exception as e:
            logger.error(f"快速測試流水線執行失敗: {e}")
            raise

async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="快速測試增強RAG系統")
    parser.add_argument("--sample-size", type=int, default=100,
                       help="樣本資料大小（預設100筆）")
    parser.add_argument("--config", type=str,
                       help="配置文件路徑")
    
    args = parser.parse_args()
    
    # 配置日誌
    logger.add("quick_enhanced_rag_test.log", rotation="1 day", level="INFO")
    
    # 初始化測試器
    tester = QuickEnhancedRAGTester(args.config)
    
    try:
        await tester.run_quick_test_pipeline(args.sample_size)
        
    except KeyboardInterrupt:
        logger.info("用戶中斷操作")
    except Exception as e:
        logger.error(f"執行失敗: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # 執行主函數
    exit_code = asyncio.run(main())
    sys.exit(exit_code)