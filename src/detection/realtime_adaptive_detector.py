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

class RealtimeAdaptiveShockDetector:
    """
    即時適應性震波檢測器
    
    專為真實即時資料設計：
    - 適應不規則時間間隔（5-15分鐘）
    - 降低檢測門檻以符合實際情況
    - 支援間隔容忍的衝擊波檢測
    """
    
    def __init__(self):
        self.free_flow_speed = 90  # km/h
        self.jam_density = 150     # veh/km
        
        # 初始化衝擊波計算器（使用文獻公式）
        self.calculator = ShockwaveCalculator()
        
        # 🔧 適應真實資料的檢測標準
        self.shock_criteria = {
            'mild': {
                'speed_drop_min': 10,       # 降低到10 km/h
                'speed_drop_max': 25,       
                'duration_min': 1,          # 只需1個間隔
                'density_increase_min': 1,  # 降低密度要求
                'initial_speed_min': 25,    # 降低初始速度要求
                'max_time_gap': 20,         # 允許最大20分鐘間隔
                'monotonic_threshold': 0.3  # 降低單調性要求到30%
            },
            'moderate': {
                'speed_drop_min': 25,       
                'speed_drop_max': 40,       
                'duration_min': 1,          
                'density_increase_min': 2,  
                'initial_speed_min': 35,
                'max_time_gap': 20,         
                'monotonic_threshold': 0.4  # 40%
            },
            'severe': {
                'speed_drop_min': 35,       # 降低到35 km/h（原本50）
                'speed_drop_max': 100,      
                'duration_min': 1,          
                'density_increase_min': 3,  
                'initial_speed_min': 45,
                'max_time_gap': 20,         
                'monotonic_threshold': 0.5  # 50%
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
        return f"{row['hour']:02d}:{row['minute']:02d}"

    def detect_realtime_shocks(self, station_data):
        """檢測即時震波事件 - 適應真實資料間隔"""
        data = station_data.copy().reset_index(drop=True)
        data['density'] = self.calculate_density(data['flow'], data['median_speed'])
        
        # 🔧 更輕度的平滑化（3點移動平均，而非7點）
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
        """容忍時間間隔的衝擊波檢測"""
        shocks = []
        
        for i in range(len(data) - 1):
            current = data.iloc[i]
            next_point = data.iloc[i + 1]
            
            # 檢查時間間隔
            time_gap = self._calculate_time_gap_minutes(data, i, i + 1)
            
            # 如果時間間隔在容忍範圍內
            if time_gap <= criteria.get('max_time_gap', 15):
                speed_drop = current['median_speed'] - next_point['median_speed']
                
                # 檢查是否符合衝擊波條件
                if (speed_drop >= criteria['speed_drop_min'] and 
                    speed_drop <= criteria['speed_drop_max'] and
                    current['median_speed'] >= criteria['initial_speed_min']):
                    
                    # 計算其他指標
                    initial_density = current['flow'] / max(current['median_speed'], 0.1)
                    final_density = next_point['flow'] / max(next_point['median_speed'], 0.1)
                    density_change = final_density - initial_density
                    
                    # 🔧 放寬密度增加要求
                    if density_change >= criteria['density_increase_min'] or speed_drop >= 30:
                        shock_event = {
                            'level': level,
                            'start_time': self._parse_time_from_data(current),
                            'end_time': self._parse_time_from_data(next_point),
                            'duration': time_gap,  # 實際時間間隔
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
                            'theoretical_wave_speed': self._calculate_realistic_wave_speed(
                                initial_density, final_density, 
                                current['median_speed'], next_point['median_speed']
                            ),
                            'time_gap': time_gap,
                            'station': current.get('station', 'Unknown')
                        }
                        
                        shocks.append(shock_event)
        
        return shocks
    
    def calculate_density(self, flow, speed):
        """
        計算密度
        使用基本公式: k = q / v
        """
        # 使用計算器的方法
        if isinstance(flow, (pd.Series, np.ndarray)):
            return np.array([self.calculator.calculate_density_from_flow_speed(f, s) 
                           for f, s in zip(flow, speed)])
        else:
            return self.calculator.calculate_density_from_flow_speed(flow, speed)
    
    def _calculate_realistic_wave_speed(self, rho_i, rho_f, u_i, u_f):
        """
        計算衝擊波速度（使用 Rankine-Hugoniot 條件）
        
        公式: vw = (q₂ - q₁)/(k₂ - k₁) = Δq/Δk
        
        參數:
            rho_i: 初始密度 (veh/km)
            rho_f: 最終密度 (veh/km)
            u_i: 初始速度 (km/hr)
            u_f: 最終速度 (km/hr)
            
        返回:
            vw: 衝擊波速度 (km/hr)
                負值 → 向上游傳播（逆車流方向）
                正值 → 向下游傳播（順車流方向）
        """
        # 計算流量
        q_i = rho_i * u_i  # 上游流量
        q_f = rho_f * u_f  # 下游流量
        
        # 使用文獻公式計算衝擊波速度
        wave_speed = self.calculator.calculate_shockwave_speed(q_i, rho_i, q_f, rho_f)
        
        return wave_speed
    
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
                    abs(current['start_idx'] - existing['end_idx']) < 2):  # 只需間隔2個點（10分鐘）
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
    
    def calculate_final_statistics(self, shocks):
        """計算最終統計"""
        if not shocks:
            return {}
        
        df = pd.DataFrame(shocks)
        
        return {
            'total_events': len(shocks),
            'by_level': df['level'].value_counts().to_dict(),
            'by_station': df['station'].value_counts().to_dict() if 'station' in df.columns else {},
            'avg_duration': df['duration'].mean(),
            'avg_speed_drop': df['speed_drop'].mean(),
            'avg_density_increase': df['density_increase'].mean(),
            'avg_wave_speed': df['theoretical_wave_speed'].mean(),
            'max_speed_drop': df['speed_drop'].max(),
            'min_speed_drop': df['speed_drop'].min(),
            'duration_range': (df['duration'].min(), df['duration'].max()),
            'severe_events': len(df[df['level'] == 'severe']),
            'moderate_events': len(df[df['level'] == 'moderate']),
            'mild_events': len(df[df['level'] == 'mild'])
        }

def test_realtime_detector():
    """測試即時檢測器"""
    # 載入最新的即時資料
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
        # 創建測試資料來驗證您提到的衝擊波
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
        print("📊 使用測試資料驗證您發現的衝擊波")
    else:
        print(f"📊 載入最新即時資料: {os.path.basename(latest_file)}")
        df = pd.read_csv(latest_file)
    
    # 初始化檢測器
    detector = RealtimeAdaptiveShockDetector()
    
    print("=== 即時適應性震波檢測器 ===")
    print("🔧 調整後的檢測標準：")
    for level, criteria in detector.shock_criteria.items():
        print(f"  {level}: 速度下降 {criteria['speed_drop_min']}-{criteria['speed_drop_max']} km/h, "
              f"時間間隔 ≤{criteria['max_time_gap']} 分鐘, "
              f"初始速度 ≥{criteria['initial_speed_min']} km/h")
    
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
            print(f"  📍 {station}: 發現 {len(shocks)} 個衝擊波")
    
    print(f"\n🎯 總檢測結果: {len(all_shocks)} 個衝擊波事件")
    
    # 統計分析
    stats = detector.calculate_final_statistics(all_shocks)
    
    if stats:
        print(f"\n📈 統計分析:")
        print(f"  各等級分布: {stats['by_level']}")
        print(f"  平均速度下降: {stats['avg_speed_drop']:.1f} km/h")
        print(f"  最大速度下降: {stats['max_speed_drop']:.1f} km/h")
        print(f"  平均持續時間: {stats['avg_duration']:.1f} 分鐘")
        print(f"  嚴重事件: {stats['severe_events']} 個")
        print(f"  中等事件: {stats['moderate_events']} 個")
        print(f"  輕微事件: {stats['mild_events']} 個")
        
        print(f"\n🔥 嚴重衝擊波詳情:")
        severe_shocks = [s for s in all_shocks if s['level'] == 'severe']
        for i, shock in enumerate(severe_shocks[:10]):  # 顯示前10個
            print(f"  {i+1}. 站點 {shock['station']}: {shock['start_time']} → {shock['end_time']}")
            print(f"     速度: {shock['initial_speed']:.0f} → {shock['final_speed']:.0f} km/h "
                  f"(下降 {shock['speed_drop']:.0f} km/h)")
            print(f"     時間間隔: {shock['time_gap']:.0f} 分鐘")
    
    return detector, all_shocks, stats

if __name__ == "__main__":
    detector, shocks, stats = test_realtime_detector()
