import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class RefinedTrafficShockWaveDetector:
    """
    精修版震波檢測器 - 修正邏輯錯誤，提高檢測精度
    
    基於文獻：
    1. 只檢測真正的壅塞波（backward forming shock waves）
    2. 震波必須是速度下降 + 密度上升
    3. 合理的閾值設定
    """
    
    def __init__(self):
        self.free_flow_speed = 90  # km/h
        self.jam_density = 150     # veh/km  
        self.critical_density = 25 # veh/km
        
        # 精修後的震波檢測標準
        self.shock_criteria = {
            'mild': {
                'speed_drop_min': 5,      # 最小速度下降 5 km/h
                'speed_drop_max': 15,     # 最大速度下降 15 km/h
                'duration_min': 2,        # 最少持續 10 分鐘
                'density_increase_min': 2 # 最小密度增加 2 veh/km
            },
            'moderate': {
                'speed_drop_min': 15,
                'speed_drop_max': 30,
                'duration_min': 3,
                'density_increase_min': 5
            },
            'severe': {
                'speed_drop_min': 30,
                'speed_drop_max': 100,
                'duration_min': 2,
                'density_increase_min': 10
            }
        }
    
    def calculate_density(self, flow, speed):
        """計算交通密度"""
        speed = np.where(speed <= 0.1, 0.1, speed)
        return flow / speed
    
    def detect_congestion_shocks(self, station_data):
        """
        檢測壅塞震波 - 嚴格定義
        只檢測真正的 backward forming shock waves
        """
        data = station_data.copy().reset_index(drop=True)
        data['density'] = self.calculate_density(data['flow'], data['median_speed'])
        
        # 計算5點移動平均以減少噪聲
        data['speed_smooth'] = data['median_speed'].rolling(window=5, center=True).mean()
        data['density_smooth'] = data['density'].rolling(window=5, center=True).mean()
        
        all_shocks = []
        
        # 對每個震波等級進行檢測
        for level, criteria in self.shock_criteria.items():
            shocks = self._detect_shocks_strict(data, level, criteria)
            all_shocks.extend(shocks)
        
        # 排序並去除重疊
        all_shocks = sorted(all_shocks, key=lambda x: x['start_idx'])
        filtered_shocks = self._remove_overlapping_events(all_shocks)
        
        return filtered_shocks
    
    def _detect_shocks_strict(self, data, level, criteria):
        """嚴格的震波檢測邏輯"""
        shocks = []
        i = 0
        
        while i < len(data) - criteria['duration_min']:
            # 檢查是否符合震波起始條件
            if self._is_shock_trigger(data, i, criteria):
                
                # 分析震波發展
                shock_analysis = self._analyze_shock_development(data, i, criteria)
                
                if shock_analysis['is_valid_shock']:
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
                        'max_flow': shock_analysis['max_flow'],
                        'min_flow': shock_analysis['min_flow'],
                        'start_idx': shock_analysis['start_idx'],
                        'end_idx': shock_analysis['end_idx'],
                        'theoretical_wave_speed': shock_analysis['wave_speed']
                    }
                    
                    shocks.append(shock_event)
                    i = shock_analysis['end_idx'] + 1
                else:
                    i += 1
            else:
                i += 1
        
        return shocks
    
    def _is_shock_trigger(self, data, idx, criteria):
        """檢查震波觸發條件"""
        if idx >= len(data) - 1:
            return False
        
        current = data.iloc[idx]
        next_point = data.iloc[idx + 1]
        
        # 基本條件：速度必須足夠高才可能有震波
        if current['median_speed'] < 20:
            return False
        
        # 檢查速度下降
        speed_drop = current['median_speed'] - next_point['median_speed']
        
        # 檢查密度上升
        density_increase = next_point['density'] - current['density']
        
        # 震波條件：速度下降 + 密度上升
        return (speed_drop >= criteria['speed_drop_min'] * 0.3 and  # 初始檢測較寬鬆
                density_increase > 0 and
                current['median_speed'] > next_point['median_speed'])
    
    def _analyze_shock_development(self, data, start_idx, criteria):
        """分析震波發展過程"""
        initial_speed = data.iloc[start_idx]['median_speed']
        initial_density = data.iloc[start_idx]['density']
        
        max_duration = min(20, len(data) - start_idx - 1)  # 最多分析100分鐘
        
        best_shock = {
            'is_valid_shock': False,
            'start_idx': start_idx,
            'end_idx': start_idx,
            'duration': 0
        }
        
        for duration in range(criteria['duration_min'], max_duration):
            end_idx = start_idx + duration
            
            if end_idx >= len(data):
                break
            
            # 分析這段期間的變化
            analysis = self._analyze_period(data, start_idx, end_idx, criteria)
            
            if analysis['meets_criteria']:
                best_shock = analysis
                best_shock['is_valid_shock'] = True
                # 繼續尋找更長的震波
            elif best_shock['is_valid_shock']:
                # 如果已經找到有效震波，且當前不滿足條件，則結束
                break
        
        return best_shock
    
    def _analyze_period(self, data, start_idx, end_idx, criteria):
        """分析特定時間段"""
        period_data = data.iloc[start_idx:end_idx+1]
        
        initial_speed = period_data.iloc[0]['median_speed']
        final_speed = period_data.iloc[-1]['median_speed']
        initial_density = period_data.iloc[0]['density']
        final_density = period_data.iloc[-1]['density']
        
        speed_drop = initial_speed - final_speed
        density_increase = final_density - initial_density
        duration = end_idx - start_idx
        
        # 嚴格檢查是否符合震波條件
        meets_criteria = (
            speed_drop >= criteria['speed_drop_min'] and
            speed_drop <= criteria['speed_drop_max'] and
            density_increase >= criteria['density_increase_min'] and
            duration >= criteria['duration_min'] and
            initial_speed > final_speed and  # 確保是真正的速度下降
            final_density > initial_density  # 確保是真正的密度上升
        )
        
        # 計算理論震波速度
        wave_speed = 0
        if abs(final_density - initial_density) > 0.1:
            flow_initial = initial_density * initial_speed
            flow_final = final_density * final_speed
            wave_speed = (flow_final - flow_initial) / (final_density - initial_density)
        
        return {
            'meets_criteria': meets_criteria,
            'start_idx': start_idx,
            'end_idx': end_idx,
            'duration': duration,
            'speed_drop': speed_drop,
            'initial_speed': initial_speed,
            'final_speed': final_speed,
            'initial_density': initial_density,
            'final_density': final_density,
            'density_increase': density_increase,
            'max_flow': period_data['flow'].max(),
            'min_flow': period_data['flow'].min(),
            'wave_speed': wave_speed
        }
    
    def _format_time(self, row):
        """格式化時間"""
        return f"{row['date']} {row['hour']:02d}:{row['minute']:02d}"
    
    def _remove_overlapping_events(self, shocks):
        """去除重疊事件，保留更嚴重的"""
        if not shocks:
            return []
        
        severity_order = {'mild': 1, 'moderate': 2, 'severe': 3}
        filtered = []
        
        for current in shocks:
            # 檢查是否與已有事件重疊
            overlapped = False
            for i, existing in enumerate(filtered):
                if (current['start_idx'] <= existing['end_idx'] and 
                    current['end_idx'] >= existing['start_idx']):
                    
                    # 有重疊，保留更嚴重的事件
                    if severity_order[current['level']] > severity_order[existing['level']]:
                        filtered[i] = current
                    overlapped = True
                    break
            
            if not overlapped:
                filtered.append(current)
        
        return filtered
    
    def calculate_statistics(self, shocks):
        """計算統計數據"""
        if not shocks:
            return {}
        
        df_shocks = pd.DataFrame(shocks)
        
        return {
            'total_events': len(shocks),
            'by_level': df_shocks['level'].value_counts().to_dict(),
            'avg_duration': df_shocks['duration'].mean(),
            'avg_speed_drop': df_shocks['speed_drop'].mean(),
            'avg_density_increase': df_shocks['density_increase'].mean(),
            'avg_wave_speed': df_shocks['theoretical_wave_speed'].mean(),
            'speed_drop_range': (df_shocks['speed_drop'].min(), df_shocks['speed_drop'].max()),
            'duration_range': (df_shocks['duration'].min(), df_shocks['duration'].max())
        }
    
    def visualize_refined_results(self, station_data, station_name, shocks):
        """精修版視覺化"""
        fig, axes = plt.subplots(3, 2, figsize=(18, 12))
        
        data = station_data.copy().reset_index(drop=True)
        data['density'] = self.calculate_density(data['flow'], data['median_speed'])
        time_index = range(len(data))
        
        colors = {'mild': 'yellow', 'moderate': 'orange', 'severe': 'red'}
        
        # 1. 速度時間序列 + 震波標記
        axes[0,0].plot(time_index, data['median_speed'], 'b-', linewidth=0.8, alpha=0.7)
        axes[0,0].set_title(f'{station_name} - 速度時間序列（精修版）')
        axes[0,0].set_ylabel('速度 (km/h)')
        axes[0,0].grid(True, alpha=0.3)
        
        for shock in shocks:
            color = colors[shock['level']]
            axes[0,0].axvspan(shock['start_idx'], shock['end_idx'], 
                             alpha=0.6, color=color)
        
        # 2. 密度時間序列 + 震波標記
        axes[0,1].plot(time_index, data['density'], 'g-', linewidth=0.8, alpha=0.7)
        axes[0,1].set_title(f'{station_name} - 密度時間序列')
        axes[0,1].set_ylabel('密度 (veh/km)')
        axes[0,1].grid(True, alpha=0.3)
        
        for shock in shocks:
            color = colors[shock['level']]
            axes[0,1].axvspan(shock['start_idx'], shock['end_idx'], 
                             alpha=0.6, color=color)
        
        # 3. 震波強度分析
        if shocks:
            shock_levels = [shock['level'] for shock in shocks]
            shock_speeds = [shock['speed_drop'] for shock in shocks]
            shock_durations = [shock['duration'] for shock in shocks]
            
            level_colors = [colors[level] for level in shock_levels]
            
            axes[1,0].scatter(shock_durations, shock_speeds, 
                             c=level_colors, s=60, alpha=0.7, edgecolors='black')
            axes[1,0].set_xlabel('持續時間 (分鐘)')
            axes[1,0].set_ylabel('速度下降 (km/h)')
            axes[1,0].set_title('震波強度 vs 持續時間')
            axes[1,0].grid(True, alpha=0.3)
        
        # 4. 震波等級分布
        if shocks:
            level_counts = {}
            for shock in shocks:
                level_counts[shock['level']] = level_counts.get(shock['level'], 0) + 1
            
            levels = list(level_counts.keys())
            counts = list(level_counts.values())
            bar_colors = [colors[level] for level in levels]
            
            axes[1,1].bar(levels, counts, color=bar_colors, alpha=0.7, edgecolor='black')
            axes[1,1].set_title('震波等級分布')
            axes[1,1].set_ylabel('事件數量')
            
            # 添加數值標籤
            for i, count in enumerate(counts):
                axes[1,1].text(i, count + 0.1, str(count), ha='center')
        
        # 5. 基本圖關係 + 震波點標記
        scatter = axes[2,0].scatter(data['density'], data['flow'], 
                                   c=data['median_speed'], cmap='viridis', 
                                   s=3, alpha=0.6)
        
        # 標記震波起始點
        for shock in shocks:
            start_idx = shock['start_idx']
            axes[2,0].scatter(data.iloc[start_idx]['density'], 
                             data.iloc[start_idx]['flow'],
                             color='red', s=50, marker='x', linewidth=3)
        
        axes[2,0].set_xlabel('密度 (veh/km)')
        axes[2,0].set_ylabel('流量 (veh/h)')
        axes[2,0].set_title('基本圖關係（震波起始點標記為紅X）')
        plt.colorbar(scatter, ax=axes[2,0], label='速度 (km/h)')
        
        # 6. 每日震波頻率
        if shocks:
            shock_dates = [shock['start_time'].split()[0] for shock in shocks]
            daily_counts = pd.Series(shock_dates).value_counts().sort_index()
            
            axes[2,1].bar(range(len(daily_counts)), daily_counts.values, 
                         alpha=0.7, color='skyblue', edgecolor='black')
            axes[2,1].set_title('每日震波頻率')
            axes[2,1].set_ylabel('震波數量')
            axes[2,1].set_xlabel('日期索引')
            axes[2,1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()

def main():
    # 載入資料
    file_path = '../../data/Taiwan/train_enhanced_full.csv'
    df = pd.read_csv(file_path)
    
    # 初始化精修版檢測器
    detector = RefinedTrafficShockWaveDetector()
    
    print("=== 精修版震波檢測系統 ===")
    print("檢測標準:")
    for level, criteria in detector.shock_criteria.items():
        print(f"  {level}: 速度下降 {criteria['speed_drop_min']}-{criteria['speed_drop_max']} km/h, "
              f"持續 {criteria['duration_min']*5} 分鐘以上, 密度增加 {criteria['density_increase_min']} veh/km以上")
    
    # 測試站點
    test_station = '01F0340N'
    print(f"\n=== 分析站點: {test_station} ===")
    
    station_data = df[df['station'] == test_station].sort_values(['date', 'hour', 'minute'])
    print(f"資料期間: {station_data['date'].min()} 到 {station_data['date'].max()}")
    print(f"總資料點數: {len(station_data)} ({len(station_data)/288:.1f} 天)")
    
    # 震波檢測
    shocks = detector.detect_congestion_shocks(station_data)
    
    print(f"\n=== 精修版檢測結果 ===")
    print(f"總震波事件: {len(shocks)} 個")
    
    # 統計分析
    stats = detector.calculate_statistics(shocks)
    
    if stats:
        print(f"\n=== 統計分析 ===")
        print(f"各等級分布: {stats['by_level']}")
        print(f"平均持續時間: {stats['avg_duration']:.1f} 分鐘")
        print(f"平均速度下降: {stats['avg_speed_drop']:.1f} km/h")
        print(f"平均密度增加: {stats['avg_density_increase']:.1f} veh/km")
        print(f"平均理論波速: {stats['avg_wave_speed']:.1f} km/h")
        print(f"速度下降範圍: {stats['speed_drop_range'][0]:.1f} - {stats['speed_drop_range'][1]:.1f} km/h")
        print(f"持續時間範圍: {stats['duration_range'][0]:.1f} - {stats['duration_range'][1]:.1f} 分鐘")
        
        # 計算頻率
        total_days = len(station_data) / 288
        daily_rate = len(shocks) / total_days
        print(f"\n每日平均震波數: {daily_rate:.2f} 個/天")
    
    # 顯示詳細事件
    print(f"\n=== 前5個震波事件詳情 ===")
    for i, shock in enumerate(shocks[:5]):
        print(f"\n震波 {i+1} ({shock['level']}):")
        print(f"  時間: {shock['start_time']} - {shock['end_time']}")
        print(f"  持續: {shock['duration']} 分鐘")
        print(f"  速度: {shock['initial_speed']:.1f} → {shock['final_speed']:.1f} km/h "
              f"(下降 {shock['speed_drop']:.1f})")
        print(f"  密度: {shock['initial_density']:.1f} → {shock['final_density']:.1f} veh/km "
              f"(增加 {shock['density_increase']:.1f})")
        print(f"  理論波速: {shock['theoretical_wave_speed']:.1f} km/h")
    
    # 視覺化
    if len(shocks) > 0:
        print(f"\n=== 生成精修版視覺化 ===")
        detector.visualize_refined_results(station_data, test_station, shocks)
    else:
        print("\n未檢測到符合條件的震波事件")
    
    return detector, shocks, stats

if __name__ == "__main__":
    detector, shocks, stats = main()