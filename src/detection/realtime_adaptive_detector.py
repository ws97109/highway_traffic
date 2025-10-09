import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# 添加項目根目錄到路徑
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 導入計算器
try:
    from src.core.shockwave_calculator import ShockwaveCalculator
except ImportError:
    # 如果上面失敗，嘗試直接導入
    try:
        from core.shockwave_calculator import ShockwaveCalculator
    except ImportError:
        # 最後嘗試：手動添加路徑
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from core.shockwave_calculator import ShockwaveCalculator

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# realtime_adaptive_detector.py 的關鍵修改部分

class RealtimeAdaptiveShockDetector:
    """
    即時適應性衝擊波檢測器（含熵條件驗證）
    
    新增功能：
    - Lax 熵條件驗證
    - 稀疏波檢測
    - 改進的強度計算
    """
    
    def __init__(self):
        self.free_flow_speed = 90  # km/h
        self.jam_density = 150     # veh/km
        
        # 初始化改進的衝擊波計算器
        self.calculator = ShockwaveCalculator()
        
        # 檢測標準（保持不變）
        self.shock_criteria = {
            'mild': {
                'speed_drop_min': 10,
                'speed_drop_max': 25,
                'duration_min': 1,
                'density_increase_min': 1,
                'initial_speed_min': 25,
                'max_time_gap': 20,
                'monotonic_threshold': 0.3
            },
            'moderate': {
                'speed_drop_min': 25,
                'speed_drop_max': 40,
                'duration_min': 1,
                'density_increase_min': 2,
                'initial_speed_min': 35,
                'max_time_gap': 20,
                'monotonic_threshold': 0.4
            },
            'severe': {
                'speed_drop_min': 35,
                'speed_drop_max': 100,
                'duration_min': 1,
                'density_increase_min': 3,
                'initial_speed_min': 45,
                'max_time_gap': 20,
                'monotonic_threshold': 0.5
            }
        }

    def _calculate_time_gap_minutes(self, data, idx1, idx2):
        """計算兩個資料點之間的時間間隔（分鐘）"""
        if idx1 >= len(data) or idx2 >= len(data):
            return float('inf')

        row1 = data.iloc[idx1]
        row2 = data.iloc[idx2]

        # 計算時間差（分鐘）
        time1 = row1['hour'] * 60 + row1['minute']
        time2 = row2['hour'] * 60 + row2['minute']

        # 處理跨日情況
        time_diff = time2 - time1
        if time_diff < 0:
            time_diff += 24 * 60  # 加一天

        return time_diff

    def _parse_time_from_data(self, row):
        """從資料行解析時間"""
        try:
            return f"{int(row['hour']):02d}:{int(row['minute']):02d}"
        except:
            return "00:00"

    def detect_realtime_shocks(self, station_data):
        """檢測即時衝擊波事件 - 適應真實資料間隔"""
        data = station_data.copy().reset_index(drop=True)
        data['density'] = self.calculate_density(data['flow'], data['median_speed'])

        # 輕度的平滑化（3點移動平均）
        data['speed_smooth'] = data['median_speed'].rolling(window=3, center=True, min_periods=1).mean()
        data['density_smooth'] = data['density'].rolling(window=3, center=True, min_periods=1).mean()

        all_shocks = []

        for level, criteria in self.shock_criteria.items():
            shocks = self._detect_gap_tolerant_shocks(data, level, criteria)
            all_shocks.extend(shocks)

        # 輕度過濾，保留更多事件
        filtered_shocks = self._light_filtering(all_shocks)

        return filtered_shocks

    def _detect_gap_tolerant_shocks(self, data, level, criteria):
        """容忍時間間隔的衝擊波檢測（含熵條件驗證）"""
        shocks = []
        
        for i in range(len(data) - 1):
            current = data.iloc[i]
            next_point = data.iloc[i + 1]
            
            # 檢查時間間隔
            time_gap = self._calculate_time_gap_minutes(data, i, i + 1)
            
            if time_gap <= criteria.get('max_time_gap', 15):
                speed_drop = current['median_speed'] - next_point['median_speed']
                
                # 檢查是否符合基本衝擊波條件
                if (speed_drop >= criteria['speed_drop_min'] and 
                    speed_drop <= criteria['speed_drop_max'] and
                    current['median_speed'] >= criteria['initial_speed_min']):
                    
                    # 計算密度
                    initial_density = current['flow'] / max(current['median_speed'], 0.1)
                    final_density = next_point['flow'] / max(next_point['median_speed'], 0.1)
                    density_change = final_density - initial_density
                    
                    # 放寬密度增加要求
                    if density_change >= criteria['density_increase_min'] or speed_drop >= 30:

                        # 使用計算器驗證衝擊波速度
                        wave_result = self.calculator.calculate_shockwave_speed(
                            q1=current['flow'],
                            k1=initial_density,
                            q2=next_point['flow'],
                            k2=final_density,
                            verify_entropy=True
                        )

                        # 過濾：只保留有效的結果
                        if not wave_result.get('valid', False):
                            continue

                        wave_speed = wave_result['speed']
                        wave_type = wave_result['type']

                        flow_drop = current['flow'] - next_point['flow']
                        intensity_result = self.calculator.calculate_shock_intensity(
                            speed_drop=speed_drop,
                            density_increase=density_change,
                            flow_drop=flow_drop,
                            duration_minutes=time_gap,  # 加入持續時間
                            wave_type=wave_type  # 加入波類型

)

                        shock_event = {
                            'level': level,
                            'start_time': self._parse_time_from_data(current),
                            'end_time': self._parse_time_from_data(next_point),
                            'duration': time_gap,
                            'speed_drop': speed_drop,
                            'initial_speed': current['median_speed'],
                            'final_speed': next_point['median_speed'],
                            'initial_density': initial_density,
                            'final_density': final_density,
                            'density_increase': density_change,
                            'max_flow': max(current['flow'], next_point['flow']),
                            'min_flow': min(current['flow'], next_point['flow']),
                            'start_idx': i,
                            'end_idx': i + 1,
                            
                            # 🔥 新增：熵條件驗證結果
                            'wave_type': wave_type,  # 'shock' 或 'rarefaction'
                            'satisfies_entropy': wave_result['satisfies_entropy'],
                            'entropy_validation': wave_result.get('reason', ''),
                            'theoretical_wave_speed': wave_speed,
                            
                            # 🔥 新增：改進的強度資訊
                            'intensity_breakdown': {
                                'speed_factor': intensity_result['speed_factor'],
                                'density_factor': intensity_result['density_factor'],
                                'flow_factor': intensity_result['flow_factor'],
                                'combined_factor': intensity_result['combined_factor'],
                                'dominant_factor': intensity_result['dominant_factor'],
                                'weights': intensity_result['weights'],  # 使用的權重
                                'duration_multiplier': intensity_result['duration_multiplier']  # 時間加成
                            },
                            
                            'time_gap': time_gap,
                            'station': current.get('station', 'Unknown')
                        }

                        shocks.append(shock_event)

        return shocks

    def _light_filtering(self, shocks):
        """輕度過濾重複事件"""
        if not shocks:
            return []

        # 按時間排序
        shocks = sorted(shocks, key=lambda x: x['start_idx'])

        filtered = []
        severity_order = {'mild': 1, 'moderate': 2, 'severe': 3}

        for current in shocks:
            # 檢查是否與已有事件時間太近（同一站點）
            too_close = False
            for existing in filtered:
                if (current.get('station') == existing.get('station') and
                    abs(current['start_idx'] - existing['end_idx']) < 2):
                    # 保留更嚴重的事件
                    if severity_order[current['level']] > severity_order[existing['level']]:
                        filtered.remove(existing)
                        break
                    else:
                        too_close = True
                        break

            if not too_close:
                filtered.append(current)

        return filtered
    
    def calculate_density(self, flow, speed):
        """計算密度（使用改進的計算器）"""
        if isinstance(flow, (pd.Series, np.ndarray)):
            return np.array([self.calculator.calculate_density_from_flow_speed(f, s) 
                           for f, s in zip(flow, speed)])
        else:
            return self.calculator.calculate_density_from_flow_speed(flow, speed)
    
    def calculate_final_statistics(self, shocks):
        """計算最終統計（含波類型分布）"""
        if not shocks:
            return {}
        
        df = pd.DataFrame(shocks)
        
        # 統計波類型
        wave_type_counts = df['wave_type'].value_counts().to_dict() if 'wave_type' in df.columns else {}
        
        return {
            'total_events': len(shocks),
            'by_level': df['level'].value_counts().to_dict(),
            'by_wave_type': wave_type_counts,  # 新增：波類型統計
            'by_station': df['station'].value_counts().to_dict() if 'station' in df.columns else {},
            'avg_duration': df['duration'].mean(),
            'avg_speed_drop': df['speed_drop'].mean(),
            'avg_density_increase': df['density_increase'].mean(),
            'avg_wave_speed': df['theoretical_wave_speed'].mean(),
            'avg_intensity': df['intensity'].mean() if 'intensity' in df.columns else 0,
            'max_speed_drop': df['speed_drop'].max(),
            'min_speed_drop': df['speed_drop'].min(),
            'duration_range': (df['duration'].min(), df['duration'].max()),
            'severe_events': len(df[df['level'] == 'severe']),
            'moderate_events': len(df[df['level'] == 'moderate']),
            'mild_events': len(df[df['level'] == 'mild']),
            'shock_waves': len(df[df['wave_type'] == 'shock']) if 'wave_type' in df.columns else 0,
            'rarefaction_waves': len(df[df['wave_type'] == 'rarefaction']) if 'wave_type' in df.columns else 0
        }


def test_realtime_detector():
    """測試即時檢測器（含熵條件驗證）"""
    import os
    
    realtime_dir = '../../data/realtime_data'
    latest_file = None
    latest_time = 0
    
    # 找到最新的檔案
    if os.path.exists(realtime_dir):
        for filename in os.listdir(realtime_dir):
            if filename.startswith('realtime_shock_data_') and filename.endswith('.csv'):
                filepath = os.path.join(realtime_dir, filename)
                mtime = os.path.getmtime(filepath)
                if mtime > latest_time:
                    latest_time = mtime
                    latest_file = filepath
    
    if not latest_file:
        print("❌ 找不到即時資料檔案，使用測試資料")
        # 創建測試資料
        test_data = {
            'station': ['01F0339S', '01F0339S', '01F0928N', '01F0928N'],
            'date': ['2025/08/10', '2025/08/10', '2025/08/10', '2025/08/10'],
            'hour': [18, 18, 18, 18],
            'minute': [45, 54, 45, 54],
            'flow': [1053.1, 220.0, 315.2, 174.0],
            'median_speed': [68.0, 30.0, 73.0, 27.0],
            'avg_travel_time': [356.7, 552.0, 236.2, 376.0]
        }
        df = pd.DataFrame(test_data)
        print("📊 使用測試資料")
    else:
        print(f"📊 載入最新即時資料: {os.path.basename(latest_file)}")
        df = pd.read_csv(latest_file)
    
    # 初始化檢測器
    detector = RealtimeAdaptiveShockDetector()
    
    print("=== 即時適應性衝擊波檢測器（含熵條件驗證）===")
    
    # 測試所有站點
    all_shocks = []
    stations = df['station'].unique()
    
    print(f"\n🔍 檢測 {len(stations)} 個站點...")
    
    for station in stations:
        station_data = df[df['station'] == station].sort_values(['hour', 'minute'])
        if len(station_data) < 2:
            continue
            
        shocks = detector.detect_realtime_shocks(station_data)
        all_shocks.extend(shocks)
        
        if shocks:
            shock_count = len([s for s in shocks if s.get('wave_type') == 'shock'])
            rare_count = len([s for s in shocks if s.get('wave_type') == 'rarefaction'])
            print(f"  📍 {station}: 衝擊波 {shock_count} 個, 稀疏波 {rare_count} 個")
    
    print(f"\n🎯 總檢測結果: {len(all_shocks)} 個波動事件")
    
    # 統計分析
    stats = detector.calculate_final_statistics(all_shocks)
    
    if stats:
        print(f"\n📈 統計分析:")
        print(f"  各等級分布: {stats['by_level']}")
        print(f"  波類型分布: {stats.get('by_wave_type', {})}")
        print(f"  衝擊波: {stats.get('shock_waves', 0)} 個")
        print(f"  稀疏波: {stats.get('rarefaction_waves', 0)} 個")
        print(f"  平均強度: {stats.get('avg_intensity', 0):.2f} / 10")
        print(f"  平均速度下降: {stats['avg_speed_drop']:.1f} km/h")
        
        print(f"\n🔥 嚴重衝擊波詳情:")
        severe_shocks = [s for s in all_shocks if s['level'] == 'severe' and s.get('wave_type') == 'shock']
        for i, shock in enumerate(severe_shocks[:5]):
            print(f"  {i+1}. 站點 {shock['station']}: {shock['start_time']} → {shock['end_time']}")
            print(f"     類型: {shock.get('wave_type', 'unknown')}")
            print(f"     速度: {shock['initial_speed']:.0f} → {shock['final_speed']:.0f} km/h")
            
            # 🔥 新版顯示
            print(f"     強度: {shock.get('intensity', 0):.1f} / 10 ({shock.get('severity_description', 'N/A')})")
            print(f"     基礎強度: {shock.get('base_intensity', 0):.1f}, 時間加成: {shock.get('intensity_breakdown', {}).get('duration_multiplier', 1.0):.2f}x")
            print(f"     主導因子: {shock.get('intensity_breakdown', {}).get('dominant_factor', 'N/A')}")
            print(f"     熵驗證: {shock.get('entropy_validation', 'N/A')}")
        
        print(f"\n📈 稀疏波詳情:")
        rarefaction_waves = [s for s in all_shocks if s.get('wave_type') == 'rarefaction']
        for i, wave in enumerate(rarefaction_waves[:5]):
            print(f"  {i+1}. 站點 {wave['station']}: {wave['start_time']} → {wave['end_time']}")
            print(f"     速度變化: {wave['initial_speed']:.0f} → {wave['final_speed']:.0f} km/h")
            print(f"     密度變化: {wave['density_increase']:.1f} veh/km (降低)")
    
    return detector, all_shocks, stats


if __name__ == "__main__":
    detector, shocks, stats = test_realtime_detector()