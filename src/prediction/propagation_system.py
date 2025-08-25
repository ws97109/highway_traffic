import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 導入我們已經驗證的震波檢測器
from ..detection.final_optimized_detector import FinalOptimizedShockDetector

class RealDataShockWavePropagationAnalyzer:
    """
    基於實際資料的震波傳播分析器
    
    使用您提供的：
    1. 整合Etag.csv - 站點資訊、經緯度
    2. dis.csv - 站點間距離矩陣
    3. train_enhanced_full.csv - 交通流資料
    """
    
    def __init__(self, etag_file, distance_file):
        self.detector = FinalOptimizedShockDetector()
        
        # 讀取站點資訊
        print("=== 載入實際資料 ===")
        self.etag_data = pd.read_csv(etag_file, encoding='utf-8')
        print(f"載入站點資訊: {len(self.etag_data)} 個站點")
        
        # 讀取距離矩陣
        self.distance_matrix = pd.read_csv(distance_file, header=None, encoding='utf-8')
        print(f"載入距離矩陣: {self.distance_matrix.shape}")
        
        # 建立站點映射
        self.station_info = self._build_station_mapping()
        
        # 建立距離查詢字典
        self.distance_lookup = self._build_distance_lookup()
        
        print(f"成功建立 {len(self.station_info)} 個站點的資訊")
        print(f"成功建立 {len(self.distance_lookup)} 個站點對的距離資訊")
    
    def _build_station_mapping(self):
        """建立站點映射字典"""
        station_info = {}
        
        for _, row in self.etag_data.iterrows():
            # 提取站點編號（去除版本號）
            station_code = row['編號']
            if pd.isna(station_code):
                continue
                
            # 將站點編號轉換為我們資料中的格式
            # 例如：01F-034.0N -> 01F0340N
            clean_code = station_code.replace('-', '').replace('.', '')
            
            station_info[clean_code] = {
                'id': row['ID'],
                'direction': row['方向'],
                'original_code': station_code,
                'start_ic': row['交流道(起)'],
                'end_ic': row['交流道(迄)'],
                'latitude': row['緯度(北緯)'],
                'longitude': row['經度(東經)']
            }
        
        return station_info
    
    def _build_distance_lookup(self):
        """建立距離查詢字典"""
        distance_lookup = {}
        
        # 距離矩陣的第一行和第一列是站點ID
        station_ids = self.distance_matrix.iloc[0, :].values
        
        for i in range(1, len(station_ids)):
            for j in range(1, len(station_ids)):
                if i != j:
                    station_i = int(station_ids[i])
                    station_j = int(station_ids[j])
                    distance = self.distance_matrix.iloc[i, j]
                    
                    if not pd.isna(distance) and distance > 0:
                        distance_lookup[(station_i, station_j)] = distance
        
        return distance_lookup
    
    def get_station_distance(self, station1, station2):
        """獲取兩個站點間的距離"""
        # 從站點編號獲取ID
        id1 = self.station_info.get(station1, {}).get('id')
        id2 = self.station_info.get(station2, {}).get('id')
        
        if id1 is None or id2 is None:
            return None
        
        # 查詢距離
        return self.distance_lookup.get((id1, id2))
    
    def get_connected_stations(self, station):
        """獲取與指定站點直接相連的站點"""
        station_id = self.station_info.get(station, {}).get('id')
        if station_id is None:
            return []
        
        connected = []
        for (id1, id2), distance in self.distance_lookup.items():
            if id1 == station_id:
                # 找到對應的站點編號
                for code, info in self.station_info.items():
                    if info['id'] == id2:
                        connected.append((code, distance))
                        break
            elif id2 == station_id:
                # 找到對應的站點編號
                for code, info in self.station_info.items():
                    if info['id'] == id1:
                        connected.append((code, distance))
                        break
        
        return connected
    
    def get_freeway_sequence(self, freeway='01F', direction='N'):
        """獲取特定國道的站點序列"""
        stations = []
        
        for code, info in self.station_info.items():
            if code.startswith(freeway) and info['direction'] == direction:
                stations.append(code)
        
        # 按照里程排序（從站點編號中提取）
        def extract_mileage(code):
            # 從 01F0340N 中提取 034.0
            try:
                mileage_str = code[3:7]  # 0340
                return float(mileage_str[:-1] + '.' + mileage_str[-1])
            except:
                return 0
        
        stations.sort(key=extract_mileage)
        return stations
    
    def analyze_real_data_propagation(self, df):
        """
        基於實際資料的震波傳播分析 - 分析所有國道方向
        """
        print("\n=== 基於實際資料的震波傳播分析 ===")
        
        # 分析所有國道方向
        all_directions = [
            ('01F', 'N', '國道1號北向'),
            ('01F', 'S', '國道1號南向'),
            ('03F', 'N', '國道3號北向'),
            ('03F', 'S', '國道3號南向')
        ]
        
        all_results = {}
        
        for freeway, direction, name in all_directions:
            print(f"\n=== 分析 {name} ===")
            
            # 獲取該方向的站點序列
            station_sequence = self.get_freeway_sequence(freeway, direction)
            
            if not station_sequence:
                print(f"  {name} 無站點資料")
                continue
                
            print(f"  {name} 站點序列: {len(station_sequence)} 個站點")
            
            # 顯示站點序列
            for i, station in enumerate(station_sequence):
                info = self.station_info[station]
                print(f"    {i+1}. {station} - {info['start_ic']} → {info['end_ic']}")
            
            # 1. 為每個站點檢測震波
            station_shocks = {}
            
            print(f"\n  步驟1: {name} 各站點震波檢測")
            for i, station in enumerate(station_sequence):
                print(f"    分析站點 {station} ({i+1}/{len(station_sequence)})")
                
                station_data = df[df['station'] == station].sort_values(['date', 'hour', 'minute'])
                
                if len(station_data) > 0:
                    shocks = self.detector.detect_significant_shocks(station_data)
                    station_shocks[station] = shocks
                    print(f"      發現 {len(shocks)} 個震波事件")
                else:
                    station_shocks[station] = []
                    print(f"      無資料")
            
            # 2. 分析震波傳播軌跡
            print(f"\n  步驟2: {name} 震波傳播軌跡分析")
            propagation_events = self._trace_real_propagation(station_shocks, station_sequence)
            
            # 3. 計算傳播統計
            print(f"\n  步驟3: {name} 傳播統計計算")
            propagation_stats = self._calculate_real_propagation_stats(propagation_events)
            
            # 儲存該方向的結果
            direction_key = f"{freeway}_{direction}"
            all_results[direction_key] = {
                'name': name,
                'station_sequence': station_sequence,
                'station_shocks': station_shocks,
                'propagation_events': propagation_events,
                'propagation_stats': propagation_stats
            }
        
        return {
            'all_directions': all_results,
            'station_info': self.station_info
        }
    
    def _trace_real_propagation(self, station_shocks, station_sequence):
        """基於實際距離追蹤震波傳播"""
        propagation_events = []
        
        # 對每對相鄰站點分析震波傳播
        for i in range(len(station_sequence) - 1):
            upstream = station_sequence[i]
            downstream = station_sequence[i + 1]
            
            upstream_shocks = station_shocks.get(upstream, [])
            downstream_shocks = station_shocks.get(downstream, [])
            
            print(f"  分析 {upstream} → {downstream}")
            
            # 獲取實際距離
            distance = self.get_station_distance(upstream, downstream)
            if distance is None:
                print(f"    無法獲取距離資料")
                continue
                
            print(f"    實際距離: {distance:.2f} km")
            print(f"    上游震波: {len(upstream_shocks)} 個")
            print(f"    下游震波: {len(downstream_shocks)} 個")
            
            # 匹配震波傳播事件
            matches = self._match_real_shock_events(
                upstream_shocks, downstream_shocks, upstream, downstream, distance
            )
            
            propagation_events.extend(matches)
            print(f"    匹配傳播事件: {len(matches)} 個")
        
        return propagation_events
    
    def _match_real_shock_events(self, upstream_shocks, downstream_shocks, 
                                upstream_station, downstream_station, distance):
        """基於實際資料匹配震波事件"""
        matches = []
        
        for up_shock in upstream_shocks:
            up_time = pd.to_datetime(up_shock['start_time'])
            
            # 在合理時間窗口內尋找下游震波
            for down_shock in downstream_shocks:
                down_time = pd.to_datetime(down_shock['start_time'])
                
                # 時間差（分鐘）
                time_diff = (down_time - up_time).total_seconds() / 60
                
                # 震波應該向下游傳播，時間差應為正
                if 0 < time_diff < 180:  # 3小時內
                    # 檢查震波特徵相似性
                    if self._is_similar_shock_real(up_shock, down_shock):
                        # 計算實際傳播速度
                        propagation_speed = distance / (time_diff / 60)  # km/h
                        
                        # 合理的傳播速度範圍：2-80 km/h
                        if 2 <= propagation_speed <= 80:
                            similarity = self._calculate_similarity_real(up_shock, down_shock)
                            
                            match = {
                                'upstream_station': upstream_station,
                                'downstream_station': downstream_station,
                                'upstream_shock': up_shock,
                                'downstream_shock': down_shock,
                                'real_distance': distance,
                                'time_diff': time_diff,
                                'propagation_speed': propagation_speed,
                                'upstream_time': up_time,
                                'downstream_time': down_time,
                                'similarity_score': similarity,
                                'upstream_info': self.station_info[upstream_station],
                                'downstream_info': self.station_info[downstream_station]
                            }
                            
                            matches.append(match)
        
        # 去除重複和衝突的匹配
        return self._filter_best_matches_real(matches)
    
    def _is_similar_shock_real(self, shock1, shock2):
        """判斷兩個震波是否相似（基於實際資料）"""
        # 速度下降差異
        speed_diff = abs(shock1['speed_drop'] - shock2['speed_drop'])
        
        # 等級相似性
        level_similarity = shock1['level'] == shock2['level']
        
        # 強度相似性
        strength_diff = abs(shock1['shock_strength'] - shock2['shock_strength'])
        
        return (speed_diff < 20 and  # 速度下降差異 < 20 km/h
                (level_similarity or strength_diff < 25))  # 等級相同或強度差異 < 25%
    
    def _calculate_similarity_real(self, shock1, shock2):
        """計算震波相似度分數（基於實際資料）"""
        # 速度下降相似度
        speed_sim = 1 - min(abs(shock1['speed_drop'] - shock2['speed_drop']) / 60, 1)
        
        # 強度相似度
        strength_sim = 1 - min(abs(shock1['shock_strength'] - shock2['shock_strength']) / 100, 1)
        
        # 等級相似度
        level_weights = {'mild': 1, 'moderate': 2, 'severe': 3}
        level_diff = abs(level_weights[shock1['level']] - level_weights[shock2['level']])
        level_sim = 1 - min(level_diff / 2, 1)
        
        # 持續時間相似度
        duration_sim = 1 - min(abs(shock1['duration'] - shock2['duration']) / 60, 1)
        
        # 綜合相似度
        return (speed_sim * 0.3 + strength_sim * 0.25 + level_sim * 0.25 + duration_sim * 0.2)
    
    def _filter_best_matches_real(self, matches):
        """過濾最佳匹配（基於實際資料）"""
        if not matches:
            return []
        
        # 按相似度排序
        matches = sorted(matches, key=lambda x: x['similarity_score'], reverse=True)
        
        # 去除時間重疊的匹配
        filtered = []
        used_upstream = set()
        used_downstream = set()
        
        for match in matches:
            up_id = f"{match['upstream_station']}_{match['upstream_shock']['start_time']}"
            down_id = f"{match['downstream_station']}_{match['downstream_shock']['start_time']}"
            
            if up_id not in used_upstream and down_id not in used_downstream:
                filtered.append(match)
                used_upstream.add(up_id)
                used_downstream.add(down_id)
        
        return filtered
    
    def _calculate_real_propagation_stats(self, propagation_events):
        """計算基於實際資料的傳播統計"""
        if not propagation_events:
            return {}
        
        df = pd.DataFrame(propagation_events)
        
        stats = {
            'total_propagations': len(propagation_events),
            'avg_propagation_speed': df['propagation_speed'].mean(),
            'speed_std': df['propagation_speed'].std(),
            'avg_time_diff': df['time_diff'].mean(),
            'avg_real_distance': df['real_distance'].mean(),
            'avg_similarity': df['similarity_score'].mean(),
            'speed_range': (df['propagation_speed'].min(), df['propagation_speed'].max()),
            'distance_range': (df['real_distance'].min(), df['real_distance'].max()),
            'by_station_pair': df.groupby(['upstream_station', 'downstream_station']).size().to_dict()
        }
        
        return stats
    
    def predict_real_shock_arrival_multi(self, results, direction_key, target_station, current_time):
        """
        基於多方向資料預測震波到達時間
        """
        print(f"\n=== 震波到達時間預測：{target_station} ===")
        
        direction_results = results['all_directions'][direction_key]
        station_sequence = direction_results['station_sequence']
        
        # 找到目標站點在序列中的位置
        if target_station not in station_sequence:
            print(f"目標站點 {target_station} 不在分析序列中")
            return []
        
        target_idx = station_sequence.index(target_station)
        
        predictions = []
        
        # 檢查所有上游站點的最新震波
        for i in range(target_idx):
            upstream_station = station_sequence[i]
            upstream_shocks = direction_results['station_shocks'].get(upstream_station, [])
            
            # 找到最近的震波事件
            for shock in upstream_shocks[-3:]:  # 檢查最近3個事件
                shock_time = pd.to_datetime(shock['start_time'])
                
                # 計算到目標站點的總距離
                total_distance = 0
                for j in range(i, target_idx):
                    distance = self.get_station_distance(station_sequence[j], station_sequence[j+1])
                    if distance:
                        total_distance += distance
                
                if total_distance > 0:
                    # 使用平均傳播速度預測
                    avg_speed = direction_results['propagation_stats'].get('avg_propagation_speed', 25)
                    
                    # 預測到達時間
                    travel_time = total_distance / avg_speed * 60  # 分鐘
                    predicted_arrival = shock_time + timedelta(minutes=travel_time)
                    
                    prediction = {
                        'source_station': upstream_station,
                        'source_shock': shock,
                        'target_station': target_station,
                        'total_distance': total_distance,
                        'predicted_speed': avg_speed,
                        'travel_time': travel_time,
                        'predicted_arrival': predicted_arrival,
                        'confidence': self._calculate_real_confidence(direction_results, upstream_station, target_station),
                        'source_info': self.station_info[upstream_station],
                        'target_info': self.station_info[target_station]
                    }
                    
                    predictions.append(prediction)
        
        # 按預測時間排序
        predictions = sorted(predictions, key=lambda x: x['predicted_arrival'])
        
        return predictions[:5]  # 返回最近5個預測
    
    def _calculate_real_confidence(self, results, source_station, target_station):
        """計算基於實際資料的預測信心度"""
        propagation_events = results['propagation_events']
        
        # 計算該路徑的歷史成功率
        relevant_events = [
            event for event in propagation_events
            if event['upstream_station'] == source_station
        ]
        
        if not relevant_events:
            return 0.4  # 默認信心度
        
        # 基於歷史相似度和距離準確性計算信心度
        avg_similarity = np.mean([event['similarity_score'] for event in relevant_events])
        
        return min(avg_similarity + 0.1, 0.9)

def main():
    # 設定檔案路徑
    etag_file = '../data/Taiwan/Etag.csv'
    distance_file = '../data/Taiwan/dis.csv'
    traffic_file = '../data/Taiwan/train_enhanced_full.csv'
    
    try:
        # 初始化基於實際資料的分析器
        analyzer = RealDataShockWavePropagationAnalyzer(etag_file, distance_file)
        
        # 載入交通流資料
        print("\n=== 載入交通流資料 ===")
        df = pd.read_csv(traffic_file)
        print(f"載入交通流資料: {len(df)} 筆記錄")
        
        # 執行基於實際資料的震波傳播分析
        results = analyzer.analyze_real_data_propagation(df)
        
        # 輸出所有方向的結果
        print(f"\n=== 所有方向的傳播分析總結 ===")
        
        total_propagations = 0
        for direction_key, direction_results in results['all_directions'].items():
            stats = direction_results['propagation_stats']
            name = direction_results['name']
            
            print(f"\n{name}:")
            if stats:
                print(f"  總傳播事件: {stats['total_propagations']} 個")
                print(f"  平均傳播速度: {stats['avg_propagation_speed']:.1f} ± {stats['speed_std']:.1f} km/h")
                print(f"  平均傳播時間: {stats['avg_time_diff']:.1f} 分鐘")
                print(f"  平均實際距離: {stats['avg_real_distance']:.1f} km")
                print(f"  平均相似度: {stats['avg_similarity']:.3f}")
                print(f"  速度範圍: {stats['speed_range'][0]:.1f} - {stats['speed_range'][1]:.1f} km/h")
                
                total_propagations += stats['total_propagations']
                
                # 顯示主要站點對的傳播數量
                print(f"  主要傳播路徑:")
                sorted_pairs = sorted(stats['by_station_pair'].items(), 
                                    key=lambda x: x[1], reverse=True)
                for pair, count in sorted_pairs[:5]:  # 顯示前5個
                    upstream_info = results['station_info'][pair[0]]
                    downstream_info = results['station_info'][pair[1]]
                    print(f"    {upstream_info['start_ic']} → {downstream_info['start_ic']}: {count} 個")
            else:
                print(f"  無傳播事件")
        
        print(f"\n=== 總體統計 ===")
        print(f"總傳播事件: {total_propagations} 個")
        print(f"分析方向數: {len(results['all_directions'])} 個")
        
        # 震波到達預測示例（選擇有最多傳播事件的方向）
        best_direction = None
        max_propagations = 0
        
        for direction_key, direction_results in results['all_directions'].items():
            stats = direction_results['propagation_stats']
            if stats and stats['total_propagations'] > max_propagations:
                max_propagations = stats['total_propagations']
                best_direction = direction_key
        
        if best_direction:
            direction_results = results['all_directions'][best_direction]
            station_sequence = direction_results['station_sequence']
            
            if len(station_sequence) > 10:
                target_station = station_sequence[10]  # 選擇中間的站點
                current_time = pd.to_datetime('2025/01/15 08:00')
                
                predictions = analyzer.predict_real_shock_arrival_multi(
                    results, best_direction, target_station, current_time
                )
                
                print(f"\n=== 震波到達預測示例 ===")
                print(f"方向: {direction_results['name']}")
                print(f"目標站點: {target_station} ({analyzer.station_info[target_station]['start_ic']})")
                
                for i, pred in enumerate(predictions[:3]):
                    print(f"預測 {i+1}:")
                    print(f"  來源: {pred['source_station']} ({pred['source_info']['start_ic']})")
                    print(f"  震波等級: {pred['source_shock']['level']}")
                    print(f"  總距離: {pred['total_distance']:.1f} km")
                    print(f"  預測速度: {pred['predicted_speed']:.1f} km/h")
                    print(f"  預計到達: {pred['predicted_arrival']}")
                    print(f"  信心度: {pred['confidence']:.2f}")
                    print()
        
        return analyzer, results
        
    except Exception as e:
        print(f"錯誤: {str(e)}")
        print("請確認檔案路徑正確且檔案存在")
        return None, None

if __name__ == "__main__":
    analyzer, results = main()