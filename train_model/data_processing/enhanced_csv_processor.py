"""
增強的 CSV 資料處理器
解決代號檢索問題，添加駕駛友善的路段描述
"""

import pandas as pd
import numpy as np
import os
import json
from typing import List, Dict, Any, Tuple
from loguru import logger
import jieba

# 導入配置管理器和原始處理器
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from train_model.utils.config_manager import get_config_manager
from train_model.data_processing.csv_processor import HighwayCSVProcessor

class EnhancedHighwayCSVProcessor(HighwayCSVProcessor):
    """增強的國道CSV資料處理器 - 支援駕駛友善描述"""
    
    def __init__(self, config_path: str = None):
        """初始化增強處理器"""
        super().__init__(config_path)
        
        # 載入站點映射資料
        self.etag_data = self._load_etag_mapping()
        self.station_mapping = self._build_station_mapping()
        
        # 載入休息站和交流道資訊
        self.rest_areas = self._load_rest_areas()
        self.interchange_info = self._load_interchange_info()
        
        logger.info("增強CSV處理器初始化完成")
    
    def _load_etag_mapping(self) -> pd.DataFrame:
        """載入 Etag 站點映射資料"""
        try:
            base_path = self.config_manager.resolve_path(self.data_config['input_data_path'])
            etag_file = os.path.join(base_path, '../Taiwan/Etag.csv')
            
            if os.path.exists(etag_file):
                etag_df = pd.read_csv(etag_file, encoding='utf-8')
                logger.info(f"載入 Etag 映射資料: {len(etag_df)} 筆記錄")
                return etag_df
            else:
                logger.warning(f"Etag 檔案不存在: {etag_file}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"載入 Etag 映射資料失敗: {e}")
            return pd.DataFrame()
    
    def _build_station_mapping(self) -> Dict[str, Dict[str, Any]]:
        """建立站點代號到友善名稱的映射（使用專案現有邏輯）"""
        station_mapping = {}
        
        if self.etag_data.empty:
            return station_mapping
        
        for _, row in self.etag_data.iterrows():
            try:
                # 提取站點編號（去除版本號）- 使用與 propagation_system.py 相同邏輯
                station_code = row['編號']
                if pd.isna(station_code):
                    continue
                    
                # 將站點編號轉換為資料中的格式
                # 例如：01F-034.0N -> 01F0340N
                clean_code = station_code.replace('-', '').replace('.', '')
                
                # 建立映射（使用專案現有結構）
                station_mapping[clean_code] = {
                    'id': row['ID'],
                    'direction': row['方向'], 
                    'original_code': station_code,
                    'start_ic': row['交流道(起)'],
                    'end_ic': row['交流道(迄)'],
                    'friendly_name': f"{row['交流道(起)']} 至 {row['交流道(迄)']}",
                    'highway': station_code[:3] if len(station_code) >= 3 else "",
                    'mileage': self._extract_mileage(station_code),
                    'latitude': row['緯度(北緯)'] if pd.notna(row['緯度(北緯)']) else None,
                    'longitude': row['經度(東經)'] if pd.notna(row['經度(東經)']) else None
                }
                
            except Exception as e:
                logger.warning(f"處理站點映射失敗 {row.get('編號', 'Unknown')}: {e}")
                continue
        
        logger.info(f"建立站點映射: {len(station_mapping)} 個站點")
        return station_mapping
    
    def _extract_mileage(self, station_code: str) -> float:
        """從站點編號中提取里程數"""
        try:
            # 01F-034.0N -> 34.0
            if '-' in station_code and '.' in station_code:
                parts = station_code.split('-')[1]  # 034.0N
                mileage_str = parts.replace('N', '').replace('S', '')  # 034.0
                return float(mileage_str)
            return 0.0
        except:
            return 0.0
    
    def _load_rest_areas(self) -> Dict[str, List[Dict[str, Any]]]:
        """載入休息站資訊"""
        # 國道休息站資訊（可以從外部檔案載入）
        rest_areas = {
            '01F': [  # 國道一號
                {'name': '中壢服務區', 'mileage': 53.2, 'direction': 'both', 'facilities': ['加油站', '餐廳', '便利店', '停車場']},
                {'name': '湖口服務區', 'mileage': 62.5, 'direction': 'both', 'facilities': ['加油站', '餐廳', '便利店', '停車場']},
                {'name': '西螺服務區', 'mileage': 232.0, 'direction': 'both', 'facilities': ['加油站', '餐廳', '便利店', '停車場']},
                {'name': '泰安服務區', 'mileage': 264.5, 'direction': 'both', 'facilities': ['加油站', '餐廳', '便利店', '停車場', '休息區']},
            ],
            '03F': [  # 國道三號
                {'name': '關西服務區', 'mileage': 79.0, 'direction': 'both', 'facilities': ['加油站', '餐廳', '便利店', '停車場']},
                {'name': '西湖服務區', 'mileage': 132.5, 'direction': 'both', 'facilities': ['加油站', '餐廳', '便利店', '停車場']},
                {'name': '南投服務區', 'mileage': 214.0, 'direction': 'both', 'facilities': ['加油站', '餐廳', '便利店', '停車場']},
                {'name': '古坑服務區', 'mileage': 254.5, 'direction': 'both', 'facilities': ['加油站', '餐廳', '便利店', '停車場']},
            ]
        }
        
        logger.info(f"載入休息站資訊: 國道1號 {len(rest_areas['01F'])} 個，國道3號 {len(rest_areas['03F'])} 個")
        return rest_areas
    
    def _load_interchange_info(self) -> Dict[str, Dict[str, Any]]:
        """載入交流道替代路線資訊"""
        # 主要交流道的替代路線資訊
        interchange_info = {
            # 北部地區
            '五股': {
                'alternatives': ['台64線', '台1線', '台15線'],
                'description': '可使用台64線快速道路或台1線省道作為替代道路',
                'peak_hours': ['07:00-09:00', '17:00-19:00']
            },
            '林口': {
                'alternatives': ['台61線', '台1線'],
                'description': '可經由台61線西濱快速道路繞行',
                'peak_hours': ['07:30-09:30', '17:30-19:30']
            },
            '桃園': {
                'alternatives': ['台4線', '台1線', '縣道113線'],
                'description': '可使用台4線或縣道113線進入桃園市區',
                'peak_hours': ['07:00-09:00', '17:00-19:00']
            },
            '中壢': {
                'alternatives': ['台1線', '縣道114線', '台66線'],
                'description': '可使用台66線東西向快速道路或台1線',
                'peak_hours': ['07:30-09:30', '17:30-19:30']
            },
            
            # 中部地區
            '台中': {
                'alternatives': ['台74線', '台1線', '台3線'],
                'description': '可使用台74線快速道路或台1線省道',
                'peak_hours': ['07:00-09:00', '17:00-19:00']
            },
            '彰化': {
                'alternatives': ['台1線', '台19線', '縣道139線'],
                'description': '可經由台1線或台19線繞行彰化市區',
                'peak_hours': ['07:30-09:30', '17:30-19:30']
            },
            
            # 南部地區
            '台南': {
                'alternatives': ['台86線', '台1線', '台17線'],
                'description': '可使用台86線快速道路或台17線濱海公路',
                'peak_hours': ['07:00-09:00', '17:00-19:00']
            },
            '高雄': {
                'alternatives': ['台88線', '台1線', '台17線'],
                'description': '可使用台88線快速道路進入高雄',
                'peak_hours': ['07:30-09:30', '17:30-19:30']
            }
        }
        
        logger.info(f"載入交流道替代路線資訊: {len(interchange_info)} 個交流道")
        return interchange_info
    
    def resolve_station_code(self, station_code: str) -> str:
        """解析站點代號為友善名稱（使用專案現有邏輯）"""
        
        # 首先嘗試從 CSV 格式解析：N0010_SB,034K+000
        if ',' in station_code and 'K+' in station_code:
            try:
                parts = station_code.split(',')
                direction_code = parts[0].strip()
                mileage_code = parts[1].strip()
                
                # 解析國道和方向
                if 'N0010' in direction_code:
                    highway = '國道1號'
                    direction = '北向' if 'NB' in direction_code else '南向'
                    highway_code = '01F'
                elif 'N0030' in direction_code:
                    highway = '國道3號' 
                    direction = '北向' if 'NB' in direction_code else '南向'
                    highway_code = '03F'
                else:
                    return station_code  # 無法識別的格式
                
                # 解析里程
                if 'K+' in mileage_code:
                    km_str = mileage_code.split('K+')[0]
                    km = float(km_str)
                    
                    # 構建對應的 Etag 格式進行查找
                    # 例如：034K+000 -> 01F-034.0N
                    etag_format = f"{highway_code}-{km_str:0>3}.0{'N' if '北向' in direction else 'S'}"
                    clean_etag = etag_format.replace('-', '').replace('.', '')
                    
                    # 嘗試從映射中查找
                    if clean_etag in self.station_mapping:
                        mapping = self.station_mapping[clean_etag]
                        return mapping['friendly_name']
                    
                    # 如果沒找到映射，返回基本描述
                    return f"{highway}{direction} {km}公里處"
                    
            except Exception as e:
                logger.warning(f"解析CSV格式代號失敗 {station_code}: {e}")
        
        # 嘗試直接從 Etag 格式映射查找
        if station_code in self.station_mapping:
            return self.station_mapping[station_code]['friendly_name']
        
        # 嘗試清理格式後查找
        clean_code = station_code.replace('-', '').replace('.', '').replace('_', '')
        if clean_code in self.station_mapping:
            return self.station_mapping[clean_code]['friendly_name']
        
        return station_code  # 如果無法解析，返回原代號
    
    def find_nearby_rest_areas(self, highway: str, mileage: float, direction: str = 'both') -> List[Dict[str, Any]]:
        """尋找附近的休息站"""
        if highway not in self.rest_areas:
            return []
        
        nearby_areas = []
        for area in self.rest_areas[highway]:
            distance = abs(area['mileage'] - mileage)
            
            # 只考慮50公里內的休息站
            if distance <= 50:
                area_info = area.copy()
                area_info['distance_km'] = distance
                area_info['is_ahead'] = area['mileage'] > mileage
                nearby_areas.append(area_info)
        
        # 按距離排序
        nearby_areas.sort(key=lambda x: x['distance_km'])
        return nearby_areas
    
    def get_alternative_routes(self, start_ic: str, end_ic: str) -> List[str]:
        """獲取替代路線建議"""
        alternatives = []
        
        # 檢查起點交流道的替代路線
        for ic_name, info in self.interchange_info.items():
            if ic_name in start_ic or ic_name in end_ic:
                alternatives.extend(info['alternatives'])
        
        # 去重並返回
        return list(set(alternatives))
    
    def generate_enhanced_text_descriptions(self, df: pd.DataFrame) -> List[str]:
        """生成增強的文字描述 - 包含友善名稱和駕駛建議"""
        descriptions = []
        
        for idx, row in df.iterrows():
            try:
                # 解析基本資訊
                direction_code = str(row['國道編號方向'])
                mileage_str = str(row['樁號'])
                mileage_num = float(row['里程']) / 1000  # 轉換為公里
                
                # 解析國道和方向
                if 'N0010' in direction_code:
                    highway = '國道1號'
                    highway_code = '01F'
                    direction = '北向' if 'NB' in direction_code else '南向'
                elif 'N0030' in direction_code:
                    highway = '國道3號'
                    highway_code = '03F'
                    direction = '北向' if 'NB' in direction_code else '南向'
                else:
                    highway = '國道'
                    highway_code = '01F'
                    direction = ''
                
                # 基本路段描述
                desc = f"""=== {highway}{direction} {mileage_num:.1f}公里處路段資訊 ===

📍 位置資訊：
• 國道：{highway}
• 方向：{direction}
• 里程：{mileage_num:.1f}公里 ({mileage_str})
• 調查日期：{row['調查日期']}
• 座標：北緯 {row['經緯度坐標Lat']:.6f}，東經 {row['經緯度坐標Lon']:.6f}

🛣️ 道路規格：
• 鋪面類型：{row['鋪面種類']}
• 路幅寬度：{row['路幅寬']}公尺（全路幅：{row['全路幅寬']}公尺）
• 主線車道數：{int(row['車道數'])}車道"""

                # 車道寬度詳細資訊
                lane_info = []
                for i in range(1, 7):
                    lane_width = row.get(f'車道{i}寬', 0)
                    if pd.notna(lane_width) and float(lane_width) > 0:
                        lane_info.append(f"第{i}車道 {lane_width}公尺")
                
                if lane_info:
                    desc += f"\n• 車道寬度：{' | '.join(lane_info)}"
                
                # 路肩資訊
                shoulder_info = []
                if row.get('內路肩') == '有' and pd.notna(row.get('內路肩寬')) and float(row.get('內路肩寬', 0)) > 0:
                    shoulder_info.append(f"內路肩 {row['內路肩寬']}公尺")
                if row.get('外路肩') == '無' and pd.notna(row.get('外路肩寬')) and float(row.get('外路肩寬', 0)) > 0:
                    shoulder_info.append(f"外路肩 {row['外路肩寬']}公尺")
                
                if shoulder_info:
                    desc += f"\n• 路肩設施：{' | '.join(shoulder_info)}"
                
                # 輔助車道資訊
                aux_lanes = []
                for i in range(1, 4):
                    aux_lane = row.get(f'輔助車道{i}')
                    aux_width = row.get(f'輔助車道{i}寬', 0)
                    if pd.notna(aux_lane) and aux_lane != '無' and pd.notna(aux_width) and float(aux_width) > 0:
                        aux_lanes.append(f"輔助車道{i} {aux_width}公尺")
                
                if aux_lanes:
                    desc += f"\n• 輔助車道：{' | '.join(aux_lanes)}"
                
                # 幾何設計特性
                desc += f"\n\n🔄 幾何設計："
                if pd.notna(row.get('曲率半徑')) and float(row.get('曲率半徑', 0)) > 0:
                    curvature = float(row['曲率半徑'])
                    if curvature < 500:
                        curve_desc = "急彎路段"
                    elif curvature < 1000:
                        curve_desc = "彎道路段"
                    else:
                        curve_desc = "緩彎路段"
                    desc += f"\n• 曲率半徑：{curvature}公尺 ({curve_desc})"
                
                if pd.notna(row.get('縱向坡度')):
                    slope = float(row['縱向坡度'])
                    if abs(slope) > 0.03:
                        slope_desc = "陡坡路段" if abs(slope) > 0.05 else "緩坡路段"
                    else:
                        slope_desc = "平坦路段"
                    desc += f"\n• 縱向坡度：{slope:.3f} ({slope_desc})"
                
                if pd.notna(row.get('橫向坡度')):
                    desc += f"\n• 橫向坡度：{float(row['橫向坡度']):.3f}"
                
                # 尋找附近休息站
                nearby_rest_areas = self.find_nearby_rest_areas(highway_code, mileage_num)
                if nearby_rest_areas:
                    desc += f"\n\n🏨 附近休息站："
                    for area in nearby_rest_areas[:3]:  # 最多顯示3個最近的
                        direction_desc = "前方" if area['is_ahead'] else "後方"
                        desc += f"\n• {area['name']}：{direction_desc}{area['distance_km']:.1f}公里"
                        desc += f" (設施：{', '.join(area['facilities'])})"
                
                # 特殊路段警示
                warnings = []
                if pd.notna(row.get('曲率半徑')) and float(row['曲率半徑']) < 500:
                    warnings.append("注意急彎，建議減速慢行")
                if pd.notna(row.get('縱向坡度')) and abs(float(row['縱向坡度'])) > 0.05:
                    warnings.append("注意坡度變化，保持安全車距")
                if row.get('避車彎') != '無':
                    warnings.append("路段設有避車彎，注意安全")
                
                if warnings:
                    desc += f"\n\n⚠️ 駕駛提醒：\n• " + "\n• ".join(warnings)
                
                # 駕駛建議
                desc += f"\n\n💡 駕駛建議："
                desc += f"\n• 建議車速：依路況調整，注意速限標示"
                desc += f"\n• 車道選擇：建議使用中間車道行駛"
                if aux_lanes:
                    desc += f"\n• 匯入匯出：注意輔助車道車輛動態"
                
                descriptions.append(desc.strip())
                
            except Exception as e:
                logger.warning(f"生成路段 {idx} 的增強描述失敗: {e}")
                # 使用基本描述作為備用
                basic_desc = f"路段資訊：{row.get('國道編號方向', '')} {row.get('樁號', '')} - 基本道路資料"
                descriptions.append(basic_desc)
        
        logger.info(f"生成增強文字描述: {len(descriptions)} 個")
        return descriptions
    
    def process_all_data_enhanced(self) -> List[Dict[str, Any]]:
        """處理所有資料並生成增強的訓練格式"""
        # 載入資料
        highway1_df, highway3_df = self.load_highway_data()
        
        # 清理資料
        highway1_clean = self.clean_and_normalize_data(highway1_df)
        highway3_clean = self.clean_and_normalize_data(highway3_df)
        
        # 生成增強的文字描述
        highway1_texts = self.generate_enhanced_text_descriptions(highway1_clean)
        highway3_texts = self.generate_enhanced_text_descriptions(highway3_clean)
        
        # 合併所有文本
        all_texts = highway1_texts + highway3_texts
        
        # 分割文本並添加元數據
        processed_data = []
        for i, text in enumerate(all_texts):
            chunks = self.chunk_text(text)
            
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
                    'id': f'{source}_{i}_{j}',
                    'text': chunk,
                    'source': source,
                    'chunk_index': j,
                    'original_index': i,
                    'highway': '國道1號' if 'N0010' in direction_code else '國道3號',
                    'direction': '北向' if 'NB' in direction_code else '南向',
                    'mileage': mileage_num,
                    'station_code': f"{row['國道編號方向']},{row['樁號']}",
                    'friendly_location': self.resolve_station_code(f"{row['國道編號方向']},{row['樁號']}"),
                    'coordinates': {
                        'lat': float(row['經緯度坐標Lat']) if pd.notna(row['經緯度坐標Lat']) else None,
                        'lng': float(row['經緯度坐標Lon']) if pd.notna(row['經緯度坐標Lon']) else None
                    }
                })
        
        logger.info(f"增強處理完成，總共生成 {len(processed_data)} 個文本塊")
        
        # 統計增強資料
        highway_stats = {}
        for item in processed_data:
            highway = item['highway']
            highway_stats[highway] = highway_stats.get(highway, 0) + 1
        
        logger.info(f"增強資料分布: {highway_stats}")
        
        return processed_data

def main():
    """測試增強處理器"""
    try:
        processor = EnhancedHighwayCSVProcessor()
        processed_data = processor.process_all_data_enhanced()
        
        # 儲存增強資料
        output_file = "enhanced_highway_data.json"
        output_path = processor.save_processed_data(processed_data, output_file)
        
        print(f"增強處理完成！生成了 {len(processed_data)} 個文本塊")
        print(f"輸出檔案：{output_path}")
        
        # 顯示範例
        print("\n=== 範例增強描述 ===")
        for i in range(min(2, len(processed_data))):
            print(f"\n--- 塊 {i+1} ---")
            print(f"位置：{processed_data[i]['friendly_location']}")
            print(f"文本預覽：{processed_data[i]['text'][:300]}...")
            
        return processed_data
        
    except Exception as e:
        logger.error(f"增強處理失敗: {e}")
        return None

if __name__ == "__main__":
    main()