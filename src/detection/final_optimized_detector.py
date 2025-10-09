import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class FinalOptimizedShockDetector:
    """
    最終優化版衝擊波檢測器
    
    基於文獻校準：
    - 印第安納州研究：後向衝擊波速度 4.2 mph (6.7 km/h)
    - 59個衝擊波案例，200小時壅塞
    - 更嚴格的檢測標準以符合實際頻率
    """
    
    # 在 src/detection/final_optimized_detector.py 第 16-40 行
    # 將現有的 shock_criteria 替換成以下內容：

    def __init__(self):
        self.free_flow_speed = 90  # km/h
        self.jam_density = 150     # veh/km
        
        # 🔧 調整後的檢測標準 - 適應真實間斷資料
        self.shock_criteria = {
            'mild': {
                'speed_drop_min': 10,       # 降低到10 km/h，捕捉較小衝擊波
                'speed_drop_max': 25,       
                'duration_min': 1,          # 保持1個間隔
                'density_increase_min': 1,  # 降低密度要求
                'initial_speed_min': 25,    # 降低初始速度要求
                'max_time_gap': 20          # 允許最大20分鐘間隔
            },
            'moderate': {
                'speed_drop_min': 25,       # 降低到25 km/h
                'speed_drop_max': 40,       
                'duration_min': 1,          
                'density_increase_min': 2,  
                'initial_speed_min': 30,    # 降低要求
                'max_time_gap': 20          
            },
            'severe': {
                'speed_drop_min': 40,       # 降低到40 km/h，您的資料顯示38-46 km/h
                'speed_drop_max': 100,      
                'duration_min': 1,          
                'density_increase_min': 3,  
                'initial_speed_min': 35,    # 降低要求
                'max_time_gap': 20          
            }
        }

    # 🆕 新增方法：在 final_optimized_detector.py 最後加入
    def _calculate_time_gap_minutes(self, data, idx1, idx2):
        """計算兩個資料點之間的時間間隔（分鐘）"""
        if idx1 >= len(data) or idx2 >= len(data):
            return float('inf')
        
        row1 = data.iloc[idx1]
        row2 = data.iloc[idx2]
        
        # 假設資料有hour和minute欄位，如果沒有需要從其他欄位解析
        time1 = row1.get('hour', 0) * 60 + row1.get('minute', 0)
        time2 = row2.get('hour', 0) * 60 + row2.get('minute', 0)
        
        return abs(time2 - time1)

    def _detect_gap_tolerant_shocks(self, data, level, criteria):
        """🆕 新增：容忍時間間隔的衝擊波檢測"""
        shocks = []
        
        for i in range(len(data) - 1):
            current = data.iloc[i]
            next_point = data.iloc[i + 1]
            
            # 檢查時間間隔
            time_gap = self._calculate_time_gap_minutes(data, i, i + 1)
            
            # 如果時間間隔在容忍範圍內
            if time_gap <= criteria.get('max_time_gap', 10):
                speed_drop = current['median_speed'] - next_point['median_speed']
                
                # 檢查是否符合衝擊波條件
                if (speed_drop >= criteria['speed_drop_min'] and 
                    speed_drop <= criteria['speed_drop_max'] and
                    current['median_speed'] >= criteria['initial_speed_min']):
                    
                    # 計算其他指標
                    initial_density = current['flow'] / max(current['median_speed'], 0.1)
                    final_density = next_point['flow'] / max(next_point['median_speed'], 0.1)
                    density_change = final_density - initial_density
                    
                    shock_event = {
                        'level': level,
                        'start_time': f"{current.get('hour', 0):02d}:{current.get('minute', 0):02d}",
                        'end_time': f"{next_point.get('hour', 0):02d}:{next_point.get('minute', 0):02d}",
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
                        'time_gap': time_gap  # 🆕 記錄時間間隔
                    }
                    
                    shocks.append(shock_event)
        
        return shocks
    
    def calculate_density(self, flow, speed):
        """計算密度"""
        speed = np.where(speed <= 0.1, 0.1, speed)
        return flow / speed
    
    def detect_significant_shocks(self, station_data):
        """檢測顯著衝擊波事件 - 支援間隔資料"""
        data = station_data.copy().reset_index(drop=True)
        data['density'] = self.calculate_density(data['flow'], data['median_speed'])
        
        # 🔧 進一步減少平滑化，保留真實變化
        data['speed_smooth'] = data['median_speed'].rolling(window=2, center=False, min_periods=1).mean()
        data['density_smooth'] = data['density'].rolling(window=2, center=False, min_periods=1).mean()
        
        # 🔧 填充NaN值
        data['speed_smooth'].fillna(data['median_speed'], inplace=True)
        data['density_smooth'].fillna(data['density'], inplace=True)
        
        all_shocks = []
        
        # 🆕 使用新的間隔容忍檢測方法
        for level, criteria in self.shock_criteria.items():
            # 使用新的檢測方法
            shocks = self._detect_gap_tolerant_shocks(data, level, criteria)
            all_shocks.extend(shocks)
        
        # 🔧 更寬鬆的去重邏輯
        filtered_shocks = self._remove_overlapping_shocks_relaxed(all_shocks)
        
        return self._format_shock_output(filtered_shocks, data)

    def _remove_overlapping_shocks_relaxed(self, shocks):
        """🆕 更寬鬆的去重方法"""
        if not shocks:
            return []
        
        # 按嚴重程度排序
        sorted_shocks = sorted(shocks, key=lambda x: x['speed_drop'], reverse=True)
        
        filtered = []
        used_times = set()
        
        for shock in sorted_shocks:
            time_key = f"{shock['start_time']}-{shock['end_time']}"
            
            # 檢查是否與已有的衝擊波時間重疊
            overlap = False
            for used_time in used_times:
                if self._times_overlap(time_key, used_time):
                    overlap = True
                    break
            
            if not overlap:
                filtered.append(shock)
                used_times.add(time_key)
        
        return filtered

    def _times_overlap(self, time1, time2):
        """檢查兩個時間段是否重疊"""
        # 簡單的字符串比較，您可以根據需要改進
        return time1 == time2

    def _format_shock_output(self, shocks, data):
        """格式化輸出結果"""
        if not shocks:
            print(f"未檢測到衝擊波 - 共分析 {len(data)} 個資料點")
            return []
        
        print(f"🚨 檢測到 {len(shocks)} 個衝擊波:")
        for i, shock in enumerate(shocks, 1):
            print(f"  {i}. {shock['level'].upper()} 級別")
            print(f"     時間: {shock['start_time']} → {shock['end_time']} (間隔 {shock.get('time_gap', 'N/A')} 分鐘)")
            print(f"     速度: {shock['initial_speed']} → {shock['final_speed']} km/h (下降 {shock['speed_drop']} km/h)")
            print(f"     流量: {shock['max_flow']:.0f} → {shock['min_flow']:.0f}")
            print()
        
        return shocks
    
    def _detect_strict_shocks(self, data, level, criteria):
        """嚴格衝擊波檢測"""
        shocks = []
        i = 0
        
        while i < len(data) - criteria['duration_min'] * 2:
            # 更嚴格的觸發條件
            if self._is_significant_shock_start(data, i, criteria):
                
                shock_analysis = self._analyze_shock_strictly(data, i, criteria)
                
                if shock_analysis['is_valid']:
                    # 額外驗證：檢查衝擊波是否符合物理特性
                    if self._validate_shock_physics(shock_analysis):
                        shock_event = {
                            'level': level,
                            'start_time': self._format_time(data.iloc[shock_analysis['start_idx']]),
                            'end_time': self._format_time(data.iloc[shock_analysis['end_idx']]),
                            'duration': shock_analysis['duration'] * 5,
                            'speed_drop': shock_analysis['speed_drop'],
                            'initial_speed': shock_analysis['initial_speed'],
                            'final_speed': shock_analysis['final_speed'],
                            'initial_density': shock_analysis['initial_density'],
                            'final_density': shock_analysis['final_density'],
                            'density_increase': shock_analysis['density_increase'],
                            'avg_flow': shock_analysis['avg_flow'],
                            'start_idx': shock_analysis['start_idx'],
                            'end_idx': shock_analysis['end_idx'],
                            'wave_speed': shock_analysis['wave_speed'],
                            'shock_strength': shock_analysis['shock_strength']
                        }
                        
                        shocks.append(shock_event)
                        i = shock_analysis['end_idx'] + 5  # 跳過更多點避免重複
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        
        return shocks
    
    def _is_significant_shock_start(self, data, idx, criteria):
        """檢查是否為顯著衝擊波起始點 - 適應真實資料特性"""
        if idx >= len(data) - 1:
            return False
        
        current = data.iloc[idx]
        
        # 放寬基本條件：初始速度要求
        if current['median_speed'] < criteria['initial_speed_min']:
            return False
        
        # 🔧 簡化檢查：只需要下一個點有明顯速度下降即可
        if idx + 1 < len(data):
            next_point = data.iloc[idx + 1]
            speed_drop = current['median_speed'] - next_point['median_speed']
            
            # 檢查是否有足夠的速度下降
            if speed_drop >= criteria['speed_drop_min']:
                return True
        
        # 如果有更多資料點，檢查接下來的趨勢
        if idx + 2 < len(data):
            next_points = data.iloc[idx:idx+3]
            
            # 檢查總體速度下降
            total_drop = next_points.iloc[0]['median_speed'] - next_points.iloc[-1]['median_speed']
            if total_drop >= criteria['speed_drop_min']:
                return True
        
        return False
    
    def _analyze_shock_strictly(self, data, start_idx, criteria):
        """嚴格分析衝擊波"""
        initial_speed = data.iloc[start_idx]['median_speed']
        initial_density = data.iloc[start_idx]['density']
        
        best_shock = {'is_valid': False}
        
        # 限制分析範圍（最多40分鐘）
        max_duration = min(8, len(data) - start_idx - 1)
        
        for duration in range(criteria['duration_min'], max_duration + 1):
            end_idx = start_idx + duration
            
            if end_idx >= len(data):
                break
            
            analysis = self._analyze_shock_window(data, start_idx, end_idx, criteria)
            
            if analysis['meets_strict_criteria']:
                best_shock = analysis
                best_shock['is_valid'] = True
                # 繼續尋找最佳持續時間
        
        return best_shock
    
    def _analyze_shock_window(self, data, start_idx, end_idx, criteria):
        """分析衝擊波窗口"""
        window_data = data.iloc[start_idx:end_idx+1]
        
        initial_speed = window_data.iloc[0]['median_speed']
        final_speed = window_data.iloc[-1]['median_speed']
        initial_density = window_data.iloc[0]['density']
        final_density = window_data.iloc[-1]['density']
        
        speed_drop = initial_speed - final_speed
        density_increase = final_density - initial_density
        duration = end_idx - start_idx
        
        # 嚴格條件檢查
        meets_criteria = (
            speed_drop >= criteria['speed_drop_min'] and
            speed_drop <= criteria['speed_drop_max'] and
            density_increase >= criteria['density_increase_min'] and
            duration >= criteria['duration_min'] and
            initial_speed >= criteria['initial_speed_min'] and
            final_speed > 10 and  # 最終速度不能太低
            self._check_monotonic_trend(window_data)  # 檢查趨勢的一致性
        )
        
        # 計算實際波速（參考文獻公式）
        wave_speed = self._calculate_realistic_wave_speed(
            initial_density, final_density, initial_speed, final_speed
        )
        
        return {
            'meets_strict_criteria': meets_criteria,
            'start_idx': start_idx,
            'end_idx': end_idx,
            'duration': duration,
            'speed_drop': speed_drop,
            'initial_speed': initial_speed,
            'final_speed': final_speed,
            'initial_density': initial_density,
            'final_density': final_density,
            'density_increase': density_increase,
            'avg_flow': window_data['flow'].mean(),
            'wave_speed': wave_speed,
            'shock_strength': speed_drop / initial_speed * 100  # 相對強度
        }
    
    def _check_monotonic_trend(self, window_data):
        """檢查衝擊波的單調性 - 放寬條件適應真實資料"""
        speeds = window_data['median_speed'].values
        
        if len(speeds) < 2:
            return True  # 資料點太少時直接通過
        
        # 檢查是否有明顯的速度下降
        speed_drop = speeds[0] - speeds[-1]
        
        # 如果總體下降超過10 km/h，就認為符合衝擊波特徵
        if speed_drop >= 10:
            return True
            
        # 計算下降趨勢的一致性 - 放寬到40%
        decreasing_count = 0
        total_pairs = len(speeds) - 1
        
        for i in range(total_pairs):
            if speeds[i] >= speeds[i+1]:
                decreasing_count += 1
        
        # 降低到40%的點對顯示下降趨勢即可
        return decreasing_count / total_pairs >= 0.4
    
    def _calculate_realistic_wave_speed(self, rho_i, rho_f, u_i, u_f):
        """計算符合文獻的波速"""
        if abs(rho_f - rho_i) < 0.1:
            return 0
        
        # 使用簡化的Rankine-Hugoniot條件
        # 參考文獻：後向衝擊波速度約 4-7 km/h
        flow_i = rho_i * u_i
        flow_f = rho_f * u_f
        
        raw_speed = (flow_f - flow_i) / (rho_f - rho_i)
        
        # 限制在合理範圍內（根據文獻）
        return max(-15, min(15, raw_speed))
    
    def _validate_shock_physics(self, shock_analysis):
        """驗證衝擊波的物理合理性"""
        # 檢查波速是否在合理範圍內
        if abs(shock_analysis['wave_speed']) > 20:
            return False
        
        # 檢查密度-速度關係
        density_ratio = shock_analysis['final_density'] / shock_analysis['initial_density']
        speed_ratio = shock_analysis['final_speed'] / shock_analysis['initial_speed']
        
        # 密度增加時速度應該下降
        if density_ratio > 1.2 and speed_ratio > 0.95:
            return False
        
        return True
    
    def _strict_filtering(self, shocks):
        """嚴格過濾重複事件"""
        if not shocks:
            return []
        
        # 按時間排序
        shocks = sorted(shocks, key=lambda x: x['start_idx'])
        
        filtered = []
        severity_order = {'mild': 1, 'moderate': 2, 'severe': 3}
        
        for current in shocks:
            # 檢查是否與已有事件時間太近
            too_close = False
            for existing in filtered:
                time_gap = abs(current['start_idx'] - existing['end_idx'])
                if time_gap < 6:  # 至少間隔30分鐘
                    too_close = True
                    break
            
            if not too_close:
                filtered.append(current)
        
        return filtered
    
    def _format_time(self, row):
        """格式化時間"""
        return f"{row['date']} {row['hour']:02d}:{row['minute']:02d}"
    
    def calculate_final_statistics(self, shocks):
        """計算最終統計"""
        if not shocks:
            return {}
        
        df = pd.DataFrame(shocks)
        
        return {
            'total_events': len(shocks),
            'by_level': df['level'].value_counts().to_dict(),
            'avg_duration': df['duration'].mean(),
            'avg_speed_drop': df['speed_drop'].mean(),
            'avg_density_increase': df['density_increase'].mean(),
            'avg_wave_speed': df['wave_speed'].mean(),
            'avg_shock_strength': df['shock_strength'].mean(),
            'wave_speed_range': (df['wave_speed'].min(), df['wave_speed'].max()),
            'duration_range': (df['duration'].min(), df['duration'].max())
        }

def main():
    # 載入資料
    file_path = '../../data/Taiwan/train_enhanced_full.csv'
    df = pd.read_csv(file_path)
    
    # 初始化最終優化檢測器
    detector = FinalOptimizedShockDetector()
    
    print("=== 最終優化版衝擊波檢測器 ===")
    print("適用於日常交通波的調整標準：")
    for level, criteria in detector.shock_criteria.items():
        print(f"  {level}: 速度下降 {criteria['speed_drop_min']}-{criteria['speed_drop_max']} km/h, "
              f"持續 {criteria['duration_min']*5} 分鐘+, 密度增加 {criteria['density_increase_min']}+ veh/km, "
              f"初始速度 {criteria['initial_speed_min']}+ km/h")
    
    # 測試站點
    test_station = '01F0340N'
    print(f"\n=== 分析站點: {test_station} ===")
    
    station_data = df[df['station'] == test_station].sort_values(['date', 'hour', 'minute'])
    
    # 衝擊波檢測
    shocks = detector.detect_significant_shocks(station_data)
    
    print(f"\n=== 最終檢測結果 ===")
    print(f"顯著衝擊波事件: {len(shocks)} 個")
    
    # 統計分析
    stats = detector.calculate_final_statistics(shocks)
    
    if stats:
        print(f"\n=== 統計分析（校準後） ===")
        print(f"各等級分布: {stats['by_level']}")
        print(f"平均持續時間: {stats['avg_duration']:.1f} 分鐘")
        print(f"平均速度下降: {stats['avg_speed_drop']:.1f} km/h")
        print(f"平均密度增加: {stats['avg_density_increase']:.1f} veh/km")
        print(f"平均波速: {stats['avg_wave_speed']:.1f} km/h")
        print(f"平均衝擊波強度: {stats['avg_shock_strength']:.1f}%")
        print(f"波速範圍: {stats['wave_speed_range'][0]:.1f} - {stats['wave_speed_range'][1]:.1f} km/h")
        
        # 計算頻率
        total_days = len(station_data) / 288
        daily_rate = len(shocks) / total_days
        print(f"\n每日衝擊波頻率: {daily_rate:.2f} 個/天")
        
        # 與文獻比較
        print(f"\n=== 與文獻比較 ===")
        print(f"印第安納研究: 59事件/200小時 = 0.295事件/小時 = 7.08事件/天")
        print(f"本研究結果: {daily_rate:.2f} 事件/天")
        print(f"文獻波速: 4.2 mph (6.7 km/h)")
        print(f"本研究波速: {stats['avg_wave_speed']:.1f} km/h")
        
        if abs(stats['avg_wave_speed']) <= 10:
            print("✅ 波速符合文獻範圍")
        else:
            print("⚠️ 波速需要進一步校準")
    
    # 詳細事件
    print(f"\n=== 顯著衝擊波事件詳情 ===")
    for i, shock in enumerate(shocks[:5]):
        print(f"\n衝擊波 {i+1} ({shock['level']}):")
        print(f"  時間: {shock['start_time']} - {shock['end_time']}")
        print(f"  持續: {shock['duration']} 分鐘")
        print(f"  速度: {shock['initial_speed']:.1f} → {shock['final_speed']:.1f} km/h "
              f"(下降 {shock['speed_drop']:.1f})")
        print(f"  密度: {shock['initial_density']:.1f} → {shock['final_density']:.1f} veh/km "
              f"(增加 {shock['density_increase']:.1f})")
        print(f"  波速: {shock['wave_speed']:.1f} km/h")
        print(f"  強度: {shock['shock_strength']:.1f}%")
    
    return detector, shocks, stats

if __name__ == "__main__":
    detector, shocks, stats = main()