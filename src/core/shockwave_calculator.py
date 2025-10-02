"""
衝擊波計算器 - 基於交通流理論文獻
實現 Lighthill-Whitham-Richards (LWR) 模型和 Rankine-Hugoniot 條件
"""

import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta


class ShockwaveCalculator:
    """
    衝擊波計算器
    
    基於文獻公式：
    1. 衝擊波速度: vw = (q₂ - q₁)/(k₂ - k₁) = Δq/Δk
    2. 隊列增長率: dN/dt = q₁ - q₂
    3. 相對速度: vr = v - vw
    """
    
    def __init__(self):
        """初始化計算器參數"""
        # 道路參數
        self.free_flow_speed = 90.0  # 自由流速度 (km/h)
        self.jam_density = 150.0     # 阻塞密度 (veh/km)
        
        # 典型駕駛反應時間
        self.reaction_time = 1.5  # 秒
        
    def calculate_shockwave_speed(
        self, 
        q1: float, 
        k1: float, 
        q2: float, 
        k2: float
    ) -> float:
        """
        計算衝擊波速度（使用 Rankine-Hugoniot 條件）
        
        公式: vw = (q₂ - q₁)/(k₂ - k₁) = Δq/Δk
        
        參數:
            q1: 上游流量 (veh/hr)
            k1: 上游密度 (veh/km)
            q2: 下游流量 (veh/hr)
            k2: 下游密度 (veh/km)
            
        返回:
            vw: 衝擊波速度 (km/hr)
                - 負值 → 向上游傳播（隊列向後增長）
                - 正值 → 向下游傳播（隊列向前消散）
                - 零值 → 靜止衝擊波
        """
        # 避免除以零
        if abs(k2 - k1) < 0.01:
            return 0.0
        
        # 計算衝擊波速度
        vw = (q2 - q1) / (k2 - k1)
        
        return vw
    
    def calculate_queue_growth_rate(
        self, 
        q_upstream: float, 
        q_downstream: float
    ) -> float:
        """
        計算隊列增長速率
        
        公式: dN/dt = q₁ - q₂
        
        參數:
            q_upstream: 上游流量 (veh/hr)
            q_downstream: 下游流量 (veh/hr)
            
        返回:
            增長速率 (veh/hr)
        """
        return q_upstream - q_downstream
    
    def calculate_queue_length(
        self, 
        growth_rate: float, 
        duration_hours: float,
        jam_density: Optional[float] = None
    ) -> Dict[str, float]:
        """
        計算隊列長度和車輛數
        
        公式:
            N = (q₁ - q₂) × T
            L = N / k_jam
        
        參數:
            growth_rate: 隊列增長速率 (veh/hr)
            duration_hours: 持續時間 (小時)
            jam_density: 阻塞密度 (veh/km)，可選
            
        返回:
            包含車輛數和空間長度的字典
        """
        if jam_density is None:
            jam_density = self.jam_density
        
        # 計算累積車輛數
        total_vehicles = growth_rate * duration_hours
        
        # 計算空間長度
        queue_length_km = total_vehicles / jam_density if jam_density > 0 else 0
        
        return {
            'total_vehicles': total_vehicles,
            'queue_length_km': queue_length_km,
            'queue_length_m': queue_length_km * 1000,
            'growth_rate_veh_per_hr': growth_rate,
            'duration_hours': duration_hours
        }
    
    def calculate_dissipation_time(
        self, 
        queue_vehicles: float,
        discharge_capacity: float,
        demand: float
    ) -> float:
        """
        計算隊列消散時間
        
        公式: T_dissipation = N₀ / (q_discharge - q_demand)
        
        參數:
            queue_vehicles: 隊列中的車輛數 (veh)
            discharge_capacity: 消散階段的流量容量 (veh/hr)
            demand: 上游需求流量 (veh/hr)
            
        返回:
            消散時間 (小時)，如果無法消散則返回 inf
        """
        if discharge_capacity <= demand:
            return float('inf')  # 無法消散
        
        return queue_vehicles / (discharge_capacity - demand)
    
    def calculate_relative_speed(
        self, 
        vehicle_speed: float, 
        wave_speed: float
    ) -> float:
        """
        計算相對速度
        
        公式: vr = v - vw
        
        參數:
            vehicle_speed: 車輛速度 (km/hr)
            wave_speed: 衝擊波速度 (km/hr)
            
        返回:
            相對速度 (km/hr)
        """
        return vehicle_speed - wave_speed
    
    def calculate_density_from_flow_speed(
        self, 
        flow: float, 
        speed: float
    ) -> float:
        """
        從流量和速度計算密度
        
        公式: k = q / v
        
        參數:
            flow: 流量 (veh/hr)
            speed: 速度 (km/hr)
            
        返回:
            密度 (veh/km)
        """
        if speed <= 0.1:
            speed = 0.1  # 避免除以零
        
        return flow / speed
    
    def estimate_arrival_time(
        self,
        distance_km: float,
        wave_speed_kmh: float,
        current_time: Optional[datetime] = None
    ) -> Tuple[datetime, float]:
        """
        估算衝擊波到達時間
        
        參數:
            distance_km: 距離 (km)
            wave_speed_kmh: 衝擊波速度 (km/hr)，負值表示向上游傳播
            current_time: 當前時間，如果為 None 則使用現在
            
        返回:
            (預估到達時間, 到達所需分鐘數)
        """
        if current_time is None:
            current_time = datetime.now()
        
        # 衝擊波向上游傳播時，速度為負值
        # 計算到達時間需要取絕對值
        if wave_speed_kmh == 0:
            return current_time, 0.0
        
        # 計算到達時間（小時）
        time_hours = abs(distance_km / wave_speed_kmh)
        time_minutes = time_hours * 60
        
        # 計算到達時刻
        arrival_time = current_time + timedelta(hours=time_hours)
        
        return arrival_time, time_minutes
    
    def calculate_shock_duration_from_times(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> float:
        """
        從起始和結束時間計算持續時間
        
        參數:
            start_time: 開始時間
            end_time: 結束時間
            
        返回:
            持續時間（分鐘）
        """
        duration_seconds = (end_time - start_time).total_seconds()
        return duration_seconds / 60.0
    
    def calculate_affected_area(
        self,
        intensity: float,
        wave_speed: float,
        duration_minutes: float
    ) -> float:
        """
        計算影響範圍
        
        基於衝擊波強度、速度和持續時間估算影響範圍
        
        參數:
            intensity: 強度指數 (1-10)
            wave_speed: 衝擊波速度 (km/hr)
            duration_minutes: 持續時間 (分鐘)
            
        返回:
            影響半徑 (km)
        """
        # 衝擊波傳播距離
        propagation_distance = abs(wave_speed) * (duration_minutes / 60.0)
        
        # 基於強度調整影響範圍
        # 強度越高，影響範圍越大
        intensity_factor = intensity / 10.0
        
        # 計算影響半徑（考慮橫向擴散）
        affected_radius = propagation_distance * (0.3 + 0.7 * intensity_factor)
        
        # 限制在合理範圍內 (0.5 - 10 km)
        return max(0.5, min(10.0, affected_radius))
    
    def calculate_intensity_from_speed_drop(
        self,
        speed_drop: float,
        max_speed_drop: float = 50.0
    ) -> float:
        """
        從速度下降計算強度指數
        
        參數:
            speed_drop: 速度下降 (km/hr)
            max_speed_drop: 最大速度下降 (km/hr)，用於標準化
            
        返回:
            強度指數 (1-10)
        """
        # 線性映射到 1-10
        intensity = 1.0 + 9.0 * (speed_drop / max_speed_drop)
        
        # 限制在 1-10 範圍內
        return max(1.0, min(10.0, intensity))
    
    def calculate_economic_cost(
        self,
        n_vehicles: float,
        avg_delay_hours: float,
        time_value: float = 10.0
    ) -> Dict[str, float]:
        """
        計算延誤經濟成本
        
        參數:
            n_vehicles: 受影響的車輛數
            avg_delay_hours: 平均延誤時間 (小時)
            time_value: 時間價值 ($/hr/vehicle)
            
        返回:
            包含總成本和分項的字典
        """
        total_delay_hours = n_vehicles * avg_delay_hours
        total_cost = total_delay_hours * time_value
        
        return {
            'total_vehicles': n_vehicles,
            'avg_delay_hours': avg_delay_hours,
            'total_delay_hours': total_delay_hours,
            'time_value_per_hour': time_value,
            'total_cost_usd': total_cost,
            'cost_per_vehicle': total_cost / n_vehicles if n_vehicles > 0 else 0
        }
    
    def analyze_shockwave_from_data(
        self,
        flow_upstream: float,
        speed_upstream: float,
        flow_downstream: float,
        speed_downstream: float,
        current_time: Optional[datetime] = None
    ) -> Dict:
        """
        從上下游數據綜合分析衝擊波
        
        參數:
            flow_upstream: 上游流量 (veh/hr)
            speed_upstream: 上游速度 (km/hr)
            flow_downstream: 下游流量 (veh/hr)
            speed_downstream: 下游速度 (km/hr)
            current_time: 當前時間
            
        返回:
            完整的衝擊波分析結果
        """
        if current_time is None:
            current_time = datetime.now()
        
        # 計算密度
        k1 = self.calculate_density_from_flow_speed(flow_upstream, speed_upstream)
        k2 = self.calculate_density_from_flow_speed(flow_downstream, speed_downstream)
        
        # 計算衝擊波速度
        wave_speed = self.calculate_shockwave_speed(
            flow_upstream, k1, 
            flow_downstream, k2
        )
        
        # 計算隊列增長率
        growth_rate = self.calculate_queue_growth_rate(
            flow_upstream, 
            flow_downstream
        )
        
        # 計算相對速度
        relative_speed = self.calculate_relative_speed(
            speed_upstream, 
            wave_speed
        )
        
        # 計算速度下降
        speed_drop = speed_upstream - speed_downstream
        
        # 計算強度
        intensity = self.calculate_intensity_from_speed_drop(speed_drop)
        
        return {
            'wave_speed_kmh': wave_speed,
            'wave_direction': 'upstream' if wave_speed < 0 else 'downstream',
            'growth_rate_veh_per_hr': growth_rate,
            'relative_speed_kmh': relative_speed,
            'speed_drop_kmh': speed_drop,
            'intensity': intensity,
            'upstream_density_veh_per_km': k1,
            'downstream_density_veh_per_km': k2,
            'density_change_veh_per_km': k2 - k1,
            'analysis_time': current_time.isoformat()
        }


def example_usage():
    """使用範例"""
    calculator = ShockwaveCalculator()
    
    print("=== 衝擊波計算器 - 基於文獻公式 ===\n")
    
    # 範例 1：道路事故造成的衝擊波
    print("範例 1：道路事故造成的衝擊波")
    print("-" * 50)
    
    # 上游條件（正常交通）
    q1 = 2000  # veh/hr
    v1 = 80    # km/hr
    k1 = q1 / v1  # 25 veh/km
    
    # 下游條件（完全阻塞）
    q2 = 0     # veh/hr
    v2 = 0     # km/hr
    k2 = 150   # veh/km (阻塞密度)
    
    # 計算衝擊波速度
    vw = calculator.calculate_shockwave_speed(q1, k1, q2, k2)
    print(f"衝擊波速度: {vw:.2f} km/hr")
    print(f"方向: {'向上游傳播（逆車流）' if vw < 0 else '向下游傳播（順車流）'}")
    
    # 計算隊列增長
    growth_rate = calculator.calculate_queue_growth_rate(q1, q2)
    print(f"隊列增長率: {growth_rate:.0f} veh/hr")
    
    # 計算1小時後的隊列
    queue_1hr = calculator.calculate_queue_length(growth_rate, 1.0)
    print(f"1小時後隊列: {queue_1hr['total_vehicles']:.0f} 輛車, "
          f"長度 {queue_1hr['queue_length_km']:.2f} km")
    
    # 計算30分鐘後的隊列
    queue_30min = calculator.calculate_queue_length(growth_rate, 0.5)
    print(f"30分鐘後隊列: {queue_30min['total_vehicles']:.0f} 輛車, "
          f"長度 {queue_30min['queue_length_km']:.2f} km")
    
    print("\n")
    
    # 範例 2：事故清除後的消散時間
    print("範例 2：隊列消散時間")
    print("-" * 50)
    
    # 事故累積了 2000 輛車
    # 道路容量恢復到 1800 veh/hr
    # 上游需求降為 1200 veh/hr
    dissipation_time = calculator.calculate_dissipation_time(2000, 1800, 1200)
    print(f"消散時間: {dissipation_time:.2f} 小時 ({dissipation_time * 60:.0f} 分鐘)")
    
    print("\n")
    
    # 範例 3：經濟成本計算
    print("範例 3：延誤經濟成本")
    print("-" * 50)
    
    cost_analysis = calculator.calculate_economic_cost(
        n_vehicles=2000,
        avg_delay_hours=0.5,
        time_value=10.0
    )
    print(f"總延誤成本: ${cost_analysis['total_cost_usd']:,.0f}")
    print(f"平均每輛車成本: ${cost_analysis['cost_per_vehicle']:.2f}")
    
    print("\n")
    
    # 範例 4：綜合分析
    print("範例 4：從實際數據綜合分析")
    print("-" * 50)
    
    analysis = calculator.analyze_shockwave_from_data(
        flow_upstream=1053.1,
        speed_upstream=68.0,
        flow_downstream=220.0,
        speed_downstream=30.0
    )
    
    print(f"衝擊波速度: {analysis['wave_speed_kmh']:.2f} km/hr")
    print(f"傳播方向: {analysis['wave_direction']}")
    print(f"速度下降: {analysis['speed_drop_kmh']:.1f} km/hr")
    print(f"強度指數: {analysis['intensity']:.1f} / 10")
    print(f"隊列增長率: {analysis['growth_rate_veh_per_hr']:.0f} veh/hr")
    print(f"上游密度: {analysis['upstream_density_veh_per_km']:.1f} veh/km")
    print(f"下游密度: {analysis['downstream_density_veh_per_km']:.1f} veh/km")


if __name__ == "__main__":
    example_usage()
