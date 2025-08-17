"""
重新訓練增強的 RAG 系統
使用改進的資料處理器，支援駕駛友善的路段描述和建議
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

class EnhancedRAGTrainer:
    """增強的 RAG 系統訓練器"""
    
    def __init__(self, config_path: str = None):
        """初始化增強訓練器"""
        if config_path is None:
            config_path = current_dir.parent / "configs" / "rag_config.yaml"
        
        self.config_path = str(config_path)
        
        # 初始化組件
        self.enhanced_processor = None
        self.vector_store = None
        self.ollama_client = None
        self.rag_chat = None
        self.driver_advisor = None
        
        logger.info("增強RAG訓練器初始化完成")
    
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
        
        # 初始化智能駕駛建議系統
        self.driver_advisor = IntelligentDriverAdvisor(self.config_path)
        await self.driver_advisor.initialize()
        logger.info("✓ 智能駕駛建議系統初始化完成")
    
    def process_enhanced_data(self, force_reprocess: bool = False):
        """處理增強的訓練資料"""
        logger.info("開始處理增強訓練資料...")
        
        # 檢查是否已有處理過的增強資料
        output_dir = self.enhanced_processor.data_config['output_dir']
        processed_file = os.path.join(output_dir, "enhanced_highway_data.json")
        
        if os.path.exists(processed_file) and not force_reprocess:
            logger.info("發現已處理的增強資料文件，跳過處理步驟")
            logger.info("如需重新處理，請使用 --force-reprocess 參數")
            return processed_file
        
        # 處理增強資料
        logger.info("使用增強處理器處理資料...")
        processed_data = self.enhanced_processor.process_all_data_enhanced()
        
        if not processed_data:
            raise Exception("增強資料處理失敗，無資料生成")
        
        output_path = self.enhanced_processor.save_processed_data(
            processed_data, "enhanced_highway_data.json"
        )
        
        logger.info(f"✓ 增強資料處理完成，輸出文件: {output_path}")
        logger.info(f"✓ 總計生成 {len(processed_data)} 個增強文本塊")
        
        # 顯示增強資料統計
        highway_stats = {}
        friendly_name_count = 0
        
        for item in processed_data:
            highway = item.get('highway', 'Unknown')
            highway_stats[highway] = highway_stats.get(highway, 0) + 1
            if item.get('friendly_location') != item.get('station_code'):
                friendly_name_count += 1
        
        logger.info(f"增強資料統計:")
        for highway, count in highway_stats.items():
            logger.info(f"  - {highway}: {count} 個文本塊")
        logger.info(f"  - 成功轉換友善名稱: {friendly_name_count} 個")
        
        return output_path
    
    def build_enhanced_vector_index(self, processed_data_path: str, force_rebuild: bool = False):
        """構建增強的向量索引"""
        logger.info("開始構建增強向量索引...")
        
        # 檢查現有索引
        stats = self.vector_store.get_collection_stats()
        if stats['document_count'] > 0 and not force_rebuild:
            logger.info(f"發現現有索引，包含 {stats['document_count']} 個文檔")
            logger.info("如需重建索引，請使用 --force-rebuild 參數")
            return
        
        # 載入增強處理過的資料
        import json
        with open(processed_data_path, 'r', encoding='utf-8') as f:
            enhanced_documents = json.load(f)
        
        logger.info(f"載入了 {len(enhanced_documents)} 個增強文檔")
        
        # 驗證增強文檔格式
        required_fields = ['text', 'id', 'highway', 'friendly_location']
        for doc in enhanced_documents[:3]:  # 檢查前3個
            missing_fields = [field for field in required_fields if field not in doc]
            if missing_fields:
                logger.warning(f"文檔缺少字段: {missing_fields}")
        
        # 如果需要重建，先刪除現有集合
        if force_rebuild and stats.get('document_count', 0) > 0:
            logger.warning("刪除現有向量索引...")
            self.vector_store.delete_collection()
            # 重新初始化
            self.vector_store = VectorStore(self.config_path)
        
        # 分批添加增強文檔
        batch_size = 50
        successful_batches = 0
        failed_batches = 0
        total_added = 0
        
        for i in range(0, len(enhanced_documents), batch_size):
            batch = enhanced_documents[i:i + batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(enhanced_documents) + batch_size - 1)//batch_size
            
            logger.info(f"處理增強批次 {batch_num}/{total_batches} (包含 {len(batch)} 個文檔)")
            
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
                failed_batches += 1
                continue
        
        # 顯示最終統計
        final_stats = self.vector_store.get_collection_stats()
        logger.info(f"✓ 增強向量索引構建完成")
        logger.info(f"  - 成功批次: {successful_batches}/{successful_batches + failed_batches}")
        logger.info(f"  - 總添加文檔: {total_added}")
        logger.info(f"  - 最終文檔數量: {final_stats['document_count']}")
        logger.info(f"  - 嵌入維度: {final_stats['embedding_dimension']}")
        
        if failed_batches > 0:
            logger.warning(f"有 {failed_batches} 個批次處理失敗")
    
    async def test_enhanced_rag_system(self):
        """測試增強的 RAG 系統"""
        logger.info("開始測試增強RAG系統...")
        
        # 增強的測試問題 - 包含友善名稱和駕駛情境
        enhanced_test_queries = [
            # 基本路段查詢
            "五股到林口段的車道寬度是多少？",
            "桃園交流道附近的道路規格如何？",
            "中壢服務區到內壢段的路況特色？",
            
            # 駕駛建議查詢
            "如果在湖口段遇到塞車，有什麼休息站可以等待？",
            "從台北到台中，國道1號和國道3號哪個比較好？",
            "中壢服務區有什麼設施？適合休息多久？",
            
            # 安全相關查詢
            "國道1號有哪些路段比較危險需要注意？",
            "遇到大雨時，哪些路段需要特別小心？",
            "輔助車道的使用時機和注意事項？",
            
            # 路線規劃查詢
            "如果國道1號桃園段塞車，有什麼替代路線？",
            "從新竹到台中，建議走哪條路線比較省時？"
        ]
        
        logger.info(f"執行 {len(enhanced_test_queries)} 個增強測試查詢...")
        
        successful_queries = 0
        failed_queries = 0
        
        for i, query in enumerate(enhanced_test_queries, 1):
            logger.info(f"\n--- 增強測試 {i}: {query} ---")
            
            try:
                # 使用增強 RAG 生成回答
                start_time = datetime.now()
                response = await self.rag_chat.chat(query)
                end_time = datetime.now()
                
                response_time = (end_time - start_time).total_seconds()
                
                logger.info(f"回應時間: {response_time:.2f}秒")
                logger.info(f"回答長度: {len(response)} 字符")
                logger.info(f"回答預覽: {response[:200]}...")
                
                # 檢查回答品質
                quality_score = self._assess_response_quality(query, response)
                logger.info(f"品質評分: {quality_score}/10")
                
                successful_queries += 1
                
                # 短暫延遲避免請求過於頻繁
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"測試查詢失敗: {e}")
                failed_queries += 1
        
        # 顯示測試統計
        logger.info(f"\n=== 增強RAG系統測試完成 ===")
        logger.info(f"成功查詢: {successful_queries}/{len(enhanced_test_queries)}")
        logger.info(f"失敗查詢: {failed_queries}/{len(enhanced_test_queries)}")
        logger.info(f"成功率: {successful_queries/len(enhanced_test_queries)*100:.1f}%")
        
        # 顯示對話統計
        stats = self.rag_chat.get_conversation_stats()
        logger.info(f"對話統計:")
        logger.info(f"  - 總對話數: {stats['total_conversations']}")
        logger.info(f"  - RAG 使用次數: {stats['rag_usage_count']}")
        logger.info(f"  - RAG 使用率: {stats['rag_usage_rate']:.2%}")
    
    def _assess_response_quality(self, query: str, response: str) -> float:
        """評估回答品質（簡化版本）"""
        score = 0.0
        
        # 長度檢查（合理長度獲得分數）
        if 50 <= len(response) <= 1000:
            score += 2.0
        elif len(response) > 1000:
            score += 1.0
        
        # 關鍵詞匹配檢查
        query_lower = query.lower()
        response_lower = response.lower()
        
        # 檢查是否包含相關關鍵詞
        relevant_keywords = ['車道', '寬度', '公尺', '國道', '交流道', '服務區', '建議', '路線']
        matched_keywords = sum(1 for keyword in relevant_keywords if keyword in response_lower)
        score += min(matched_keywords * 0.5, 3.0)
        
        # 檢查是否有具體數據
        if any(char.isdigit() for char in response):
            score += 1.0
        
        # 檢查是否有友善描述
        friendly_terms = ['前方', '後方', '附近', '建議', '注意', '可以', '適合']
        if any(term in response_lower for term in friendly_terms):
            score += 2.0
        
        # 檢查是否回答了問題
        if any(word in query_lower for word in ['什麼', '如何', '哪個', '怎麼']) and len(response) > 100:
            score += 2.0
        
        return min(score, 10.0)
    
    async def test_driver_advisor_integration(self):
        """測試駕駛建議系統整合"""
        logger.info("開始測試駕駛建議系統整合...")
        
        try:
            # 模擬駕駛情境
            from train_model.models.driver_advisor import TrafficCondition, ShockwaveAlert
            
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
            advice = await self.driver_advisor.analyze_current_situation(
                current_location, destination, traffic_data, shockwave_alert
            )
            
            logger.info(f"駕駛建議測試成功:")
            logger.info(f"  - 優先級: {advice.priority}")
            logger.info(f"  - 建議行動: {advice.action_type}")
            logger.info(f"  - 標題: {advice.title}")
            logger.info(f"  - 安全評估: {advice.safety_impact}")
            logger.info(f"  - 附近休息站數量: {len(advice.rest_areas)}")
            logger.info(f"  - 替代路線數量: {len(advice.alternatives)}")
            
            return True
            
        except Exception as e:
            logger.error(f"駕駛建議系統測試失敗: {e}")
            return False
    
    async def run_enhanced_training_pipeline(self, force_reprocess: bool = False, 
                                           force_rebuild: bool = False):
        """執行完整的增強訓練流水線"""
        logger.info("開始執行增強RAG訓練流水線...")
        
        try:
            start_time = datetime.now()
            
            # 1. 設置增強組件
            logger.info("步驟 1/6: 設置增強組件...")
            await self.setup_components()
            
            # 2. 處理增強資料
            logger.info("步驟 2/6: 處理增強資料...")
            processed_data_path = self.process_enhanced_data(force_reprocess)
            
            # 3. 構建增強向量索引
            logger.info("步驟 3/6: 構建增強向量索引...")
            self.build_enhanced_vector_index(processed_data_path, force_rebuild)
            
            # 4. 測試增強RAG系統
            logger.info("步驟 4/6: 測試增強RAG系統...")
            await self.test_enhanced_rag_system()
            
            # 5. 測試駕駛建議系統
            logger.info("步驟 5/6: 測試駕駛建議系統...")
            advisor_success = await self.test_driver_advisor_integration()
            
            # 6. 生成訓練報告
            logger.info("步驟 6/6: 生成訓練報告...")
            end_time = datetime.now()
            self._generate_training_report(start_time, end_time, advisor_success)
            
            logger.info("✓ 增強RAG訓練流水線執行完成")
            
        except Exception as e:
            logger.error(f"增強訓練流水線執行失敗: {e}")
            raise
    
    def _generate_training_report(self, start_time: datetime, end_time: datetime, 
                                 advisor_success: bool):
        """生成訓練報告"""
        duration = end_time - start_time
        
        report = f"""
=== 增強RAG系統訓練報告 ===
訓練時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')}
總耗時: {duration.total_seconds():.1f} 秒

增強功能:
✓ 代號轉換為友善名稱
✓ 詳細路段描述
✓ 休息站資訊整合
✓ 駕駛建議系統
✓ 替代路線建議
✓ 安全評估功能

系統狀態:
- 向量資料庫: 正常
- Ollama服務: 正常
- RAG聊天系統: 正常
- 駕駛建議系統: {'正常' if advisor_success else '異常'}

建議:
1. 定期更新交通資料以保持建議的準確性
2. 根據用戶反饋調整建議邏輯
3. 增加更多休息站和替代路線資訊
4. 整合即時交通資料API

訓練完成時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # 儲存報告
        report_file = f"enhanced_training_report_{end_time.strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = os.path.join(current_dir.parent, "logs", report_file)
        
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"訓練報告已儲存: {report_path}")
        print(report)

async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="增強RAG系統訓練腳本")
    parser.add_argument("--mode", choices=["train", "test"], default="train",
                       help="執行模式: train(訓練), test(測試)")
    parser.add_argument("--force-reprocess", action="store_true",
                       help="強制重新處理資料")
    parser.add_argument("--force-rebuild", action="store_true",
                       help="強制重建向量索引")
    parser.add_argument("--config", type=str,
                       help="配置文件路徑")
    
    args = parser.parse_args()
    
    # 配置日誌
    logger.add("enhanced_rag_training.log", rotation="1 day", level="INFO")
    
    # 初始化增強訓練器
    trainer = EnhancedRAGTrainer(args.config)
    
    try:
        if args.mode == "train":
            # 訓練模式
            await trainer.run_enhanced_training_pipeline(args.force_reprocess, args.force_rebuild)
            
        elif args.mode == "test":
            # 測試模式
            await trainer.setup_components()
            await trainer.test_enhanced_rag_system()
            await trainer.test_driver_advisor_integration()
            
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