"""
CSV 資料預處理模組
處理國道一號和國道三號的整合資料
"""

import pandas as pd
import numpy as np
import os
from typing import List, Dict, Any, Tuple
from loguru import logger
import jieba
import json
import yaml

# 導入配置管理器
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from train_model.utils.config_manager import get_config_manager

class HighwayCSVProcessor:
    """國道CSV資料處理器"""
    
    def __init__(self, config_path: str = None):
        """初始化處理器"""
        # 使用配置管理器
        if config_path:
            os.environ['RAG_CONFIG_PATH'] = config_path
        
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        
        self.data_config = self.config['data_processing']
        self.chunking_config = self.config['chunking']
        
        # 初始化中文分詞
        jieba.initialize()
        
        logger.info("CSV處理器初始化完成")
    
    def load_highway_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """載入國道一號和三號資料"""
        base_path = self.config_manager.resolve_path(self.data_config['input_data_path'])
        
        # 檢查數據目錄是否存在
        if not os.path.exists(base_path):
            logger.error(f"數據目錄不存在: {base_path}")
            raise FileNotFoundError(f"找不到數據目錄: {base_path}")
        
        # 載入國道一號資料
        highway1_path = os.path.join(base_path, self.data_config['highway1_file'])
        if not os.path.exists(highway1_path):
            logger.error(f"國道一號數據文件不存在: {highway1_path}")
            raise FileNotFoundError(f"找不到國道一號數據文件: {highway1_path}")
            
        try:
            highway1_df = pd.read_csv(highway1_path, encoding='utf-8')
            logger.info(f"載入國道一號資料: {len(highway1_df)} 筆記錄")
        except Exception as e:
            logger.error(f"讀取國道一號數據文件失敗: {e}")
            raise
        
        # 載入國道三號資料
        highway3_path = os.path.join(base_path, self.data_config['highway3_file'])
        if not os.path.exists(highway3_path):
            logger.error(f"國道三號數據文件不存在: {highway3_path}")
            raise FileNotFoundError(f"找不到國道三號數據文件: {highway3_path}")
            
        try:
            highway3_df = pd.read_csv(highway3_path, encoding='utf-8')
            logger.info(f"載入國道三號資料: {len(highway3_df)} 筆記錄")
        except Exception as e:
            logger.error(f"讀取國道三號數據文件失敗: {e}")
            raise
        
        return highway1_df, highway3_df
    
    def clean_and_normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理和正規化資料"""
        # 複製資料框避免修改原始資料
        cleaned_df = df.copy()
        
        # 處理缺失值
        cleaned_df = cleaned_df.fillna("")
        
        # 正規化文字欄位
        text_columns = ['鋪面種類', '槽化區', '內路肩', '外路肩', '輔助車道1', '輔助車道2', '輔助車道3', '避車彎']
        for col in text_columns:
            if col in cleaned_df.columns:
                cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
        
        # 處理數值欄位
        numeric_columns = ['里程', '經緯度坐標Lon', '經緯度坐標Lat', '路幅寬', '全路幅寬', 
                          '車道數', '曲率半徑', '縱向坡度', '橫向坡度']
        
        numeric_conversion_stats = {}
        for col in numeric_columns:
            if col in cleaned_df.columns:
                original_count = cleaned_df[col].notna().sum()
                # 轉換數值，記錄錯誤
                converted_series = pd.to_numeric(cleaned_df[col], errors='coerce')
                converted_count = converted_series.notna().sum()
                
                # 記錄轉換統計
                numeric_conversion_stats[col] = {
                    'original_valid': original_count,
                    'converted_valid': converted_count,
                    'conversion_errors': original_count - converted_count
                }
                
                # 用適當的預設值填充
                if col in ['經緯度坐標Lon', '經緯度坐標Lat']:
                    # 座標用 NaN，後續可以過濾或特別處理
                    cleaned_df[col] = converted_series
                else:
                    # 其他數值用 0 填充
                    cleaned_df[col] = converted_series.fillna(0)
                    
                # 記錄轉換警告
                if numeric_conversion_stats[col]['conversion_errors'] > 0:
                    logger.warning(
                        f"欄位 {col}: {numeric_conversion_stats[col]['conversion_errors']} 個值無法轉換為數值"
                    )
        
        # 記錄總體轉換統計
        total_errors = sum(stats['conversion_errors'] for stats in numeric_conversion_stats.values())
        if total_errors > 0:
            logger.info(f"數值欄位轉換完成，共 {total_errors} 個轉換錯誤")
        
        logger.info(f"資料清理完成，剩餘 {len(cleaned_df)} 筆記錄")
        return cleaned_df
    
    def generate_text_descriptions(self, df: pd.DataFrame) -> List[str]:
        """將結構化資料轉換為文字描述"""
        descriptions = []
        
        for idx, row in df.iterrows():
            # 基本資訊
            desc = f"調查日期: {row['調查日期']}\n"
            desc += f"國道編號方向: {row['國道編號方向']}\n"
            desc += f"樁號: {row['樁號']} (里程 {row['里程']}公尺)\n"
            desc += f"位置座標: 經度 {row['經緯度坐標Lon']}, 緯度 {row['經緯度坐標Lat']}\n"
            
            # 路面資訊
            desc += f"鋪面種類: {row['鋪面種類']}\n"
            desc += f"路幅寬度: {row['路幅寬']}公尺 (全路幅寬 {row['全路幅寬']}公尺)\n"
            desc += f"車道數: {row['車道數']}個\n"
            
            # 車道寬度資訊
            lane_widths = []
            for i in range(1, 7):
                col = f'車道{i}寬'
                if col in row and pd.notna(row[col]) and row[col] > 0:
                    lane_widths.append(f"車道{i}: {row[col]}公尺")
            if lane_widths:
                desc += f"車道寬度: {', '.join(lane_widths)}\n"
            
            # 路肩資訊
            if row.get('內路肩') and row['內路肩'] != '無' and row.get('內路肩寬', 0) > 0:
                desc += f"內路肩: 有 (寬度 {row['內路肩寬']}公尺)\n"
            if row.get('外路肩') and row['外路肩'] != '無' and row.get('外路肩寬', 0) > 0:
                desc += f"外路肩: 有 (寬度 {row['外路肩寬']}公尺)\n"
            
            # 輔助車道資訊
            aux_lanes = []
            for i in range(1, 4):
                col = f'輔助車道{i}'
                width_col = f'輔助車道{i}寬'
                if col in row and row[col] and row[col] != '無' and row.get(width_col, 0) > 0:
                    aux_lanes.append(f"輔助車道{i}: {row[width_col]}公尺")
            if aux_lanes:
                desc += f"輔助車道: {', '.join(aux_lanes)}\n"
            
            # 幾何特徵
            if row.get('曲率半徑', 0) > 0:
                desc += f"曲率半徑: {row['曲率半徑']}公尺\n"
            desc += f"縱向坡度: {row['縱向坡度']}\n"
            desc += f"橫向坡度: {row['橫向坡度']}\n"
            
            descriptions.append(desc.strip())
        
        logger.info(f"生成 {len(descriptions)} 個文字描述")
        return descriptions
    
    def chunk_text(self, text: str) -> List[str]:
        """將長文本分割成小塊"""
        chunk_size = self.chunking_config['chunk_size']
        chunk_overlap = self.chunking_config['chunk_overlap']
        separators = self.chunking_config['separators']
        
        # 使用分隔符分割文本
        chunks = [text]
        for separator in separators:
            new_chunks = []
            for chunk in chunks:
                new_chunks.extend(chunk.split(separator))
            chunks = new_chunks
        
        # 過濾空白塊
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        
        # 如果塊太大，進一步分割
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= chunk_size:
                final_chunks.append(chunk)
            else:
                # 使用滑動窗口分割大塊
                for i in range(0, len(chunk), chunk_size - chunk_overlap):
                    sub_chunk = chunk[i:i + chunk_size]
                    if sub_chunk.strip():
                        final_chunks.append(sub_chunk.strip())
        
        return final_chunks
    
    def process_all_data(self) -> List[Dict[str, Any]]:
        """處理所有資料並生成訓練格式"""
        # 載入資料
        highway1_df, highway3_df = self.load_highway_data()
        
        # 清理資料
        highway1_clean = self.clean_and_normalize_data(highway1_df)
        highway3_clean = self.clean_and_normalize_data(highway3_df)
        
        # 生成文字描述
        highway1_texts = self.generate_text_descriptions(highway1_clean)
        highway3_texts = self.generate_text_descriptions(highway3_clean)
        
        # 合併所有文本
        all_texts = highway1_texts + highway3_texts
        
        # 分割文本
        processed_data = []
        for i, text in enumerate(all_texts):
            chunks = self.chunk_text(text)
            for j, chunk in enumerate(chunks):
                processed_data.append({
                    'id': f'highway_data_{i}_{j}',
                    'text': chunk,
                    'source': 'highway1' if i < len(highway1_texts) else 'highway3',
                    'chunk_index': j,
                    'original_index': i
                })
        
        logger.info(f"處理完成，總共生成 {len(processed_data)} 個文本塊")
        
        # 統計資料來源分布
        source_stats = {}
        for item in processed_data:
            source = item['source']
            source_stats[source] = source_stats.get(source, 0) + 1
        
        logger.info(f"資料來源分布: {source_stats}")
        
        # 檢查文本塊長度分布
        text_lengths = [len(item['text']) for item in processed_data]
        if text_lengths:
            avg_length = sum(text_lengths) / len(text_lengths)
            min_length = min(text_lengths)
            max_length = max(text_lengths)
            logger.info(f"文本塊長度統計 - 平均: {avg_length:.1f}, 最小: {min_length}, 最大: {max_length}")
        
        return processed_data
    
    def save_processed_data(self, data: List[Dict[str, Any]], output_file: str = "processed_highway_data.json"):
        """儲存處理後的資料"""
        output_dir = self.config_manager.resolve_path(self.data_config['output_dir'])
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_file)
            
            # 驗證資料完整性
            if not data:
                logger.warning("沒有資料需要儲存")
                return None
            
            # 檢查資料格式
            required_fields = ['id', 'text', 'source']
            for i, item in enumerate(data[:5]):  # 檢查前5個項目
                missing_fields = [field for field in required_fields if field not in item]
                if missing_fields:
                    logger.error(f"資料項目 {i} 缺少必要欄位: {missing_fields}")
                    raise ValueError(f"資料格式不正確，缺少欄位: {missing_fields}")
            
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 驗證檔案是否正確寫入
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"處理後資料已儲存至: {output_path}")
                logger.info(f"檔案大小: {os.path.getsize(output_path)} bytes")
                logger.info(f"資料項目數量: {len(data)}")
                return output_path
            else:
                logger.error("檔案儲存失敗或檔案為空")
                return None
                
        except Exception as e:
            logger.error(f"儲存處理後資料時發生錯誤: {e}")
            raise

class DataProcessor:
    
    def __init__(self, config_path: str = "train_model/configs/rag_config.yaml"):
        """載入設定"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.data_path = self.config['data_processing']['input_data_path']
    
    # 您現有的CSV處理方法保持不變...
    
    def load_json_data(self, filename: str) -> List[Dict[str, Any]]:
        """載入JSON檔案"""
        file_path = os.path.join(self.data_path, filename)
        
        if not os.path.exists(file_path):
            print(f"⚠️ JSON檔案不存在: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 統一轉換為列表格式
            if isinstance(data, dict):
                data = [data]
            
            # 新增來源標記
            highway_type = "國道一號" if "N01" in filename else "國道三號"
            for item in data:
                if isinstance(item, dict):
                    item['_highway_type'] = highway_type
                    item['_source_file'] = filename
                    item['_data_category'] = 'geometric_statistical'
            
            print(f"✅ 成功載入JSON: {filename}, 共 {len(data)} 筆資料")
            return data
            
        except Exception as e:
            print(f"❌ 載入JSON失敗 {filename}: {e}")
            return []
    
    def json_to_text_chunks(self, json_data: List[Dict[str, Any]]) -> List[str]:
        """將JSON資料轉換為文字塊"""
        if not json_data:
            return []
        
        text_chunks = []
        for item in json_data:
            if isinstance(item, dict):
                text_chunk = self._convert_json_item_to_text(item)
                if text_chunk:
                    text_chunks.append(text_chunk)
        
        print(f"✅ JSON轉文字完成: 產生 {len(text_chunks)} 個文字塊")
        return text_chunks
    
    def _convert_json_item_to_text(self, item: Dict[str, Any]) -> str:
        """將單個JSON項目轉換為文字"""
        text_parts = []
        
        # 基本資訊
        highway_type = item.get('_highway_type', '未知國道')
        data_category = item.get('_data_category', '未知類別')
        
        text_parts.append(f"資料來源: {highway_type}")
        text_parts.append(f"資料類別: {data_category}")
        
        # 處理其他欄位（排除內部標記）
        for key, value in item.items():
            if key.startswith('_'):  # 跳過內部標記
                continue
                
            if isinstance(value, dict):
                # 處理嵌套字典
                dict_items = []
                for k, v in value.items():
                    if not isinstance(v, (dict, list)):
                        dict_items.append(f"{k}={v}")
                if dict_items:
                    text_parts.append(f"{key}: {', '.join(dict_items[:5])}")
            
            elif isinstance(value, list):
                # 處理列表
                if len(value) <= 5 and all(not isinstance(x, (dict, list)) for x in value):
                    text_parts.append(f"{key}: {', '.join(map(str, value))}")
                else:
                    text_parts.append(f"{key}: [包含{len(value)}個項目]")
            
            else:
                # 處理簡單值
                text_parts.append(f"{key}: {value}")
        
        return " | ".join(text_parts[:20])  # 限制欄位數量避免過長
    
    def process_all_data(self) -> Dict[str, List[str]]:
        """處理所有資料來源"""
        result = {
            'csv_chunks': [],
            'json_chunks': [],
            'total_chunks': []
        }
        
        data_sources = self.config['data_processing'].get('data_sources', ['csv'])
        
        # 處理CSV資料 (如果在data_sources中)
        if 'csv' in data_sources:
            csv_files = self.config['data_processing']['csv_files']
            for key, filename in csv_files.items():
                print(f"🔄 處理CSV: {filename}")
                # 這裡呼叫您現有的CSV處理方法
                # csv_chunks = self.process_csv(filename)  # 您現有的方法
                # result['csv_chunks'].extend(csv_chunks)
        
        # 處理JSON資料 (如果在data_sources中)
        if 'json' in data_sources:
            json_files = self.config['data_processing']['json_files']
            for key, filename in json_files.items():
                print(f"🔄 處理JSON: {filename}")
                json_data = self.load_json_data(filename)
                if json_data:
                    json_chunks = self.json_to_text_chunks(json_data)
                    result['json_chunks'].extend(json_chunks)
        
        # 合併所有文字塊
        result['total_chunks'] = result['csv_chunks'] + result['json_chunks']
        
        print(f"📊 處理完成:")
        print(f"   CSV文字塊: {len(result['csv_chunks'])}")
        print(f"   JSON文字塊: {len(result['json_chunks'])}")
        print(f"   總計: {len(result['total_chunks'])}")
        
        return result
    
    def save_processed_data(self, data: Dict[str, List[str]]) -> None:
        """儲存處理後的資料到output_dir"""
        output_dir = self.config['data_processing']['output_dir']
        os.makedirs(output_dir, exist_ok=True)
        
        for data_type, chunks in data.items():
            if chunks:
                output_file = os.path.join(output_dir, f"{data_type}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=2)
                print(f"💾 已儲存 {data_type}: {len(chunks)} 個文字塊 -> {output_file}")

if __name__ == "__main__":
    # 測試處理器
    processor = HighwayCSVProcessor()
    processed_data = processor.process_all_data()
    processor.save_processed_data(processed_data)
    
    print(f"處理完成！生成了 {len(processed_data)} 個文本塊")
    print("範例文本塊:")
    for i in range(min(3, len(processed_data))):
        print(f"\n--- 塊 {i+1} ---")
        print(processed_data[i]['text'][:200] + "...")