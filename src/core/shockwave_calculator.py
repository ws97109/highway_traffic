"""
衝擊波計算器 - 基於交通流理論文獻（完整修正版）
實現 Lighthill-Whitham-Richards (LWR) 模型和 Rankine-Hugoniot 條件
新增：Lax 熵條件驗證、稀疏波處理、改進的強度計算
"""

import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta


class ShockwaveCalculator:
    """
    衝擊波計算器（文獻標準實現）
    
    基於文獻公式：
    1. 衝擊波速度: vw = (q₂ - q₁)/(k₂ - k₁) = Δq/Δk
    2. 隊列增長率: dN/dt = q₁ - q₂
    3. 相對速度: vr = v - vw
    4. Lax 熵條件: f'(k₂) < vw < f'(k₁)
    """
    
    def __init__(self):
        """初始化計算器參數"""
        # 道路參數
        self.free_flow_speed = 90.0  # 自由流速度 (km/h)
        self.jam_density = 150.0     # 阻塞密度 (veh/km)
        self.critical_density = 50.0 # 臨界密度 (veh/km)
        
        # 典型駕駛反應時間
        self.reaction_time = 1.5  # 秒
        
    def greenshields_fundamental_diagram(self, k: float) -> Dict[str, float]:
        """
        Greenshields 基本圖
        
        公式:
            v(k) = vf * (1 - k/kj)
            q(k) = k * v(k) = vf * k * (1 - k/kj)
            dq/dk = vf * (1 - 2k/kj)
        """
        if k >= self.jam_density:
            return {'q': 0, 'v': 0, 'dq_dk': -self.free_flow_speed}
        
        v = self.free_flow_speed * (1 - k / self.jam_density)
        q = k * v
        dq_dk = self.free_flow_speed * (1 - 2 * k / self.jam_density)
        
        return {
            'q': q,
            'v': v,
            'dq_dk': dq_dk  # 特徵速度
        }
    
    def verify_lax_entropy_condition(
        self,
        k1: float,
        k2: float,
        vw: float
    ) -> Dict[str, any]:
        """
        驗證 Lax 熵條件
        
        物理意義：
        - 衝擊波速度必須介於兩側特徵速度之間
        - f'(k₂) < vw < f'(k₁)
        - 保證解的唯一性和穩定性
        
        返回:
            valid: 是否滿足熵條件
            type: 'shock' 或 'rarefaction' 或 'invalid'
        """
        fd1 = self.greenshields_fundamental_diagram(k1)
        fd2 = self.greenshields_fundamental_diagram(k2)
        
        f_prime_k1 = fd1['dq_dk']
        f_prime_k2 = fd2['dq_dk']
        
        # Lax 熵條件: f'(k₂) < vw < f'(k₁)
        if k1 < k2:  # 密度增加（衝擊波）
            # 對於衝擊波，應滿足 f'(k₂) < vw < f'(k₁)
            if f_prime_k2 < vw < f_prime_k1:
                return {
                    'valid': True,
                    'type': 'shock',
                    'satisfies_entropy': True,
                    'f_prime_k1': f_prime_k1,
                    'f_prime_k2': f_prime_k2,
                    'reason': 'Lax熵條件滿足：衝擊波'
                }
            else:
                return {
                    'valid': False,
                    'type': 'invalid',
                    'satisfies_entropy': False,
                    'f_prime_k1': f_prime_k1,
                    'f_prime_k2': f_prime_k2,
                    'reason': f'違反Lax熵條件：vw={vw:.2f} 不在 [{f_prime_k2:.2f}, {f_prime_k1:.2f}] 範圍內'
                }
        else:  # k1 >= k2，密度降低（稀疏波）
            return {
                'valid': True,
                'type': 'rarefaction',
                'satisfies_entropy': True,
                'f_prime_k1': f_prime_k1,
                'f_prime_k2': f_prime_k2,
                'reason': '密度降低：稀疏波（非衝擊波）'
            }
    
    def calculate_shockwave_speed(
        self,
        q1: float,
        k1: float,
        q2: float,
        k2: float,
        verify_entropy: bool = True
    ) -> Dict[str, any]:
        """
        計算衝擊波速度（使用 Rankine-Hugoniot 條件 + Lax 熵條件驗證）

        公式: vw = (q₂ - q₁)/(k₂ - k₁) = Δq/Δk

        參數:
            q1: 上游流量 (veh/hr)
            k1: 上游密度 (veh/km)
            q2: 下游流量 (veh/hr)
            k2: 下游密度 (veh/km)
            verify_entropy: 是否驗證熵條件（預設True）

        返回:
            字典包含:
                - valid: 計算是否有效 (bool)
                - speed: 衝擊波速度 (km/hr)
                - type: 'shock', 'rarefaction', 或 'invalid'
                - satisfies_entropy: 是否滿足熵條件
                - reason: 說明
        """
        # 避免除以零
        if abs(k2 - k1) < 0.01:
            return {
                'valid': False,
                'speed': 0.0,
                'type': 'invalid',
                'satisfies_entropy': False,
                'reason': f'密度差異過小 (Δk = {k2 - k1:.3f})'
            }

        # 計算衝擊波速度（Rankine-Hugoniot 條件）
        vw = (q2 - q1) / (k2 - k1)
        
        # 驗證 Lax 熵條件
        if verify_entropy:
            entropy_check = self.verify_lax_entropy_condition(k1, k2, vw)
            
            return {
                'valid': entropy_check['valid'],
                'speed': vw,
                'type': entropy_check['type'],
                'satisfies_entropy': entropy_check['satisfies_entropy'],
                'f_prime_k1': entropy_check.get('f_prime_k1'),
                'f_prime_k2': entropy_check.get('f_prime_k2'),
                'reason': entropy_check['reason']
            }
        else:
            return {
                'valid': True,
                'speed': vw,
                'type': 'shock' if k1 < k2 else 'rarefaction',
                'satisfies_entropy': None,
                'reason': '未驗證熵條件'
            }
    
    def calculate_shock_intensity(self, speed_drop, density_increase, flow_drop, duration_minutes=0, wave_type='shock'):
        """
        計算衝擊波強度指數 (1-10)
        
        改進點:
        1. 調整參考值更符合實際
        2. 根據波類型調整權重
        3. 加入非線性調整
        4. 考慮持續時間影響
        
        參數:
            speed_drop: 速度下降 (km/h)
            density_increase: 密度增加 (veh/km)
            flow_drop: 流量下降 (veh/hr)
            duration_minutes: 持續時間 (分鐘)
            wave_type: 波類型 ('shock' 或 'rarefaction')
        
        返回:
            dict: 包含強度分數和各項因子
        """
        
        # ===== 1. 調整後的參考值 =====
        speed_reference = 55.0  # 從 70 降到 55 (更合理)
        density_reference = self.jam_density * 0.6  # 約 90 veh/km (基於阻塞密度)
        flow_reference = 2000.0  # 保持不變
        
        # ===== 2. 計算標準化因子 =====
        speed_factor = min(1.0, abs(speed_drop) / speed_reference)
        density_factor = min(1.0, abs(density_increase) / density_reference)
        flow_factor = min(1.0, abs(flow_drop) / flow_reference)
        
        # ===== 3. 根據波類型調整權重 =====
        if wave_type == 'shock':
            # 衝擊波: 密度變化更重要
            weight_speed = 0.45
            weight_density = 0.35
            weight_flow = 0.20
        else:  # rarefaction
            # 稀疏波: 速度變化更明顯
            weight_speed = 0.50
            weight_density = 0.25
            weight_flow = 0.25
        
        # ===== 4. 計算組合強度 =====
        combined_intensity = (
            weight_speed * speed_factor + 
            weight_density * density_factor + 
            weight_flow * flow_factor
        )
        
        # ===== 5. 非線性調整 (嚴重事件加強) =====
        if combined_intensity > 0.7:
            # 嚴重事件的強度應該更突出
            excess = combined_intensity - 0.7
            combined_intensity = 0.7 + excess * 1.5
            combined_intensity = min(1.0, combined_intensity)
        
        # ===== 6. 映射到 1-10 分 =====
        base_intensity = 1.0 + 9.0 * combined_intensity
        
        # ===== 7. 時間加成因子 =====
        if duration_minutes > 15:
            duration_multiplier = 1.3  # 持續超過15分鐘: +30%
        elif duration_minutes > 5:
            duration_multiplier = 1.15  # 持續5-15分鐘: +15%
        else:
            duration_multiplier = 1.0  # 持續不到5分鐘: 無加成
        
        # ===== 8. 最終強度 (不超過10分) =====
        final_intensity = min(10.0, base_intensity * duration_multiplier)
        
        # ===== 9. 判斷主導因子 =====
        factors = {
            'speed': speed_factor,
            'density': density_factor,
            'flow': flow_factor
        }
        dominant_factor = max(factors, key=factors.get)
        
        # ===== 10. 分級說明 =====
        if final_intensity < 4.0:
            severity_level = 'mild'
            description = '輕度 - 輕微速度下降,短期影響'
        elif final_intensity < 7.0:
            severity_level = 'moderate'
            description = '中度 - 明顯壅塞,需要注意'
        else:
            severity_level = 'severe'
            description = '嚴重 - 嚴重壅塞,可能造成事故'
        
        return {
            'intensity': round(final_intensity, 2),
            'base_intensity': round(base_intensity, 2),
            'severity_level': severity_level,
            'description': description,
            
            # 各項因子
            'speed_factor': round(speed_factor, 3),
            'density_factor': round(density_factor, 3),
            'flow_factor': round(flow_factor, 3),
            'combined_factor': round(combined_intensity, 3),
            
            # 權重資訊
            'weights': {
                'speed': weight_speed,
                'density': weight_density,
                'flow': weight_flow
            },
            
            # 主導因子
            'dominant_factor': dominant_factor,
            
            # 時間資訊
            'duration_minutes': duration_minutes,
            'duration_multiplier': round(duration_multiplier, 2),
            
            # 波類型
            'wave_type': wave_type
        }
    
    def calculate_affected_area(
        self,
        wave_speed: float,
        duration_minutes: float,
        num_lanes: int = 4,
        lane_width_m: float = 3.5
    ) -> Dict[str, float]:
        """
        基於物理原理計算影響範圍
        
        參數:
            wave_speed: 衝擊波速度 (km/hr)
            duration_minutes: 持續時間 (分鐘)
            num_lanes: 車道數
            lane_width_m: 車道寬度 (米)
            
        返回:
            longitudinal_km: 縱向影響距離
            lateral_km: 橫向影響距離
            area_km2: 影響面積
        """
        # 縱向傳播距離（基於波速）
        longitudinal_distance = abs(wave_speed) * (duration_minutes / 60.0)
        
        # 橫向影響範圍（基於車道寬度）
        lateral_distance = (num_lanes * lane_width_m) / 1000  # 轉換為km
        
        # 影響面積（矩形近似）
        area = longitudinal_distance * lateral_distance
        
        return {
            'longitudinal_km': longitudinal_distance,
            'lateral_km': lateral_distance,
            'area_km2': area,
            'num_lanes_affected': num_lanes
        }
    
    def estimate_arrival_time_with_decay(
        self,
        distance_km: float,
        initial_wave_speed: float,
        decay_rate: float = 0.95,
        current_time: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        考慮衝擊波衰減的到達時間估算
        
        參數:
            distance_km: 距離 (km)
            initial_wave_speed: 初始波速 (km/hr)
            decay_rate: 每公里的衰減係數（預設0.95）
            current_time: 當前時間
            
        返回:
            arrival_time: 預估到達時間
            travel_minutes: 行進時間（分鐘）
            effective_speed: 有效傳播速度
        """
        if current_time is None:
            current_time = datetime.now()
        
        # 考慮衝擊波強度隨距離衰減
        effective_speed = initial_wave_speed * (decay_rate ** distance_km)
        
        # 如果波速太小，視為消散
        if abs(effective_speed) < 1.0:
            return {
                'arrival_time': None,
                'travel_minutes': float('inf'),
                'effective_speed': effective_speed,
                'dissipated': True,
                'reason': f'衝擊波在 {distance_km:.1f} km 處消散'
            }
        
        # 計算到達時間
        time_hours = distance_km / abs(effective_speed)
        time_minutes = time_hours * 60
        arrival_time = current_time + timedelta(hours=time_hours)
        
        return {
            'arrival_time': arrival_time,
            'travel_minutes': time_minutes,
            'effective_speed': effective_speed,
            'dissipated': False,
            'decay_factor': decay_rate ** distance_km
        }
    
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
            speed = 0.1  # 避免除零
        
        return flow / speed
    
    def estimate_arrival_time(
        self,
        distance_km: float,
        wave_speed_kmh: float,
        current_time: Optional[datetime] = None
    ) -> Tuple[datetime, float]:
        """
        估算衝擊波到達時間（簡單版本，不考慮衰減）
        
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
        
        # 計算衝擊波速度（含熵條件驗證）
        wave_result = self.calculate_shockwave_speed(
            flow_upstream, k1,
            flow_downstream, k2,
            verify_entropy=True
        )
        wave_speed = wave_result['speed']
        
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
        
        # 計算速度下降、密度增加、流量下降
        speed_drop = speed_upstream - speed_downstream
        density_increase = k2 - k1
        flow_drop = flow_upstream - flow_downstream
        
        # 計算強度（使用新的綜合方法）
        intensity_result = self.calculate_shock_intensity(
            speed_drop, 
            density_increase, 
            flow_drop
        )
        
        return {
            'wave_speed_kmh': wave_speed,
            'wave_type': wave_result['type'],
            'satisfies_entropy': wave_result['satisfies_entropy'],
            'wave_direction': 'upstream' if wave_speed < 0 else 'downstream',
            'growth_rate_veh_per_hr': growth_rate,
            'relative_speed_kmh': relative_speed,
            'speed_drop_kmh': speed_drop,
            'density_increase_veh_per_km': density_increase,
            'flow_drop_veh_per_hr': flow_drop,
            'intensity': intensity_result['intensity'],
            'intensity_components': {
                'speed_factor': intensity_result['speed_factor'],
                'density_factor': intensity_result['density_factor'],
                'flow_factor': intensity_result['flow_factor'],
                'dominant_factor': intensity_result['dominant_factor']
            },
            'upstream_density_veh_per_km': k1,
            'downstream_density_veh_per_km': k2,
            'analysis_time': current_time.isoformat(),
            'entropy_validation': wave_result.get('reason', '')
        }


def example_usage():
    """使用範例"""
    calculator = ShockwaveCalculator()
    
    print("=== 衝擊波計算器 - 完整修正版 ===\n")
    
    # 範例 1：道路事故造成的衝擊波（驗證熵條件）
    print("範例 1：道路事故造成的衝擊波（含熵條件驗證）")
    print("-" * 60)
    
    q1 = 2000  # veh/hr
    v1 = 80    # km/hr
    k1 = q1 / v1  # 25 veh/km
    
    q2 = 0     # veh/hr
    v2 = 0     # km/hr
    k2 = 150   # veh/km (阻塞密度)
    
    result = calculator.calculate_shockwave_speed(q1, k1, q2, k2, verify_entropy=True)
    print(f"衝擊波速度: {result['speed']:.2f} km/hr")
    print(f"類型: {result['type']}")
    print(f"滿足熵條件: {result['satisfies_entropy']}")
    print(f"說明: {result['reason']}")
    
    print("\n" + "=" * 60 + "\n")
    
    # 範例 2：稀疏波情況
    print("範例 2：稀疏波檢測")
    print("-" * 60)
    
    q1_rare = 500   # veh/hr
    v1_rare = 50    # km/hr
    k1_rare = 10    # veh/km
    
    q2_rare = 1500  # veh/hr
    v2_rare = 75    # km/hr
    k2_rare = 20    # veh/km（密度反而降低）
    
    result_rare = calculator.calculate_shockwave_speed(
        q1_rare, k1_rare, q2_rare, k2_rare, verify_entropy=True
    )
    print(f"波速: {result_rare['speed']:.2f} km/hr")
    print(f"類型: {result_rare['type']}")
    print(f"說明: {result_rare['reason']}")
    
    print("\n" + "=" * 60 + "\n")
    
    # 範例 3：改進的強度計算
    print("範例 3：綜合強度計算")
    print("-" * 60)
    
    intensity_result = calculator.calculate_shock_intensity(
        speed_drop=40.0,
        density_increase=50.0,
        flow_drop=1200.0
    )
    
    print(f"總體強度: {intensity_result['intensity']:.2f} / 10")
    print(f"速度因子: {intensity_result['speed_factor']:.2f}")
    print(f"密度因子: {intensity_result['density_factor']:.2f}")
    print(f"流量因子: {intensity_result['flow_factor']:.2f}")
    print(f"主導因子: {intensity_result['dominant_factor']}")
    
    print("\n" + "=" * 60 + "\n")
    
    # 範例 4：基於物理的影響範圍
    print("範例 4：影響範圍計算（基於物理）")
    print("-" * 60)
    
    affected = calculator.calculate_affected_area(
        wave_speed=-15.0,
        duration_minutes=30,
        num_lanes=4
    )
    
    print(f"縱向影響: {affected['longitudinal_km']:.2f} km")
    print(f"橫向影響: {affected['lateral_km']:.3f} km")
    print(f"影響面積: {affected['area_km2']:.3f} km²")
    print(f"受影響車道: {affected['num_lanes_affected']} 道")
    
    print("\n" + "=" * 60 + "\n")
    
    # 範例 5：考慮衰減的到達時間
    print("範例 5：衝擊波到達時間（考慮衰減）")
    print("-" * 60)
    
    arrival_info = calculator.estimate_arrival_time_with_decay(
        distance_km=20.0,
        initial_wave_speed=-15.0,
        decay_rate=0.95
    )
    
    if not arrival_info['dissipated']:
        print(f"初始波速: -15.0 km/hr")
        print(f"有效波速: {arrival_info['effective_speed']:.2f} km/hr")
        print(f"到達時間: {arrival_info['travel_minutes']:.1f} 分鐘")
        print(f"衰減因子: {arrival_info['decay_factor']:.3f}")
    else:
        print(arrival_info['reason'])


if __name__ == "__main__":
    example_usage()