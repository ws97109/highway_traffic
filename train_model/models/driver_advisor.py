"""
智能駕駛建議系統
整合 RAG 模型與實時交通資料，提供具體的駕駛決策建議
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger

# 導入現有模組
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from train_model.models.ollama_client import OllamaClient, RAGOllamaChat
from train_model.embeddings.vector_store import VectorStore, RAGRetriever

@dataclass
class TrafficCondition:
    """交通狀況資料結構"""
    station_id: str
    speed: float
    flow: float
    travel_time: float
    congestion_level: str
    timestamp: datetime

@dataclass
class ShockwaveAlert:
    """震波預警資料結構"""
    intensity: float
    propagation_speed: float
    estimated_arrival: Optional[datetime]
    affected_area: str
    warning_level: str  # low, medium, high, severe

@dataclass
class RestAreaInfo:
    """休息站資訊"""
    name: str
    distance_km: float
    direction: str  # ahead, behind
    facilities: List[str]
    estimated_travel_time: int  # 分鐘

@dataclass
class RouteAlternative:
    """替代路線資訊"""
    route_name: str
    description: str
    extra_distance_km: float
    time_difference_min: int
    congestion_avoidance: bool
    recommended_conditions: List[str]

@dataclass
class DriverAdvice:
    """駕駛建議"""
    priority: str  # low, medium, high, urgent
    action_type: str  # continue, slow_down, exit, wait, reroute
    title: str
    description: str
    reasoning: str
    time_saving_min: Optional[int]
    safety_impact: str
    alternatives: List[RouteAlternative]
    rest_areas: List[RestAreaInfo]
    estimated_cost: Optional[str]  # fuel, toll, etc.

class IntelligentDriverAdvisor:
    """智能駕駛建議系統"""
    
    def __init__(self, config_path: str = None):
        """初始化駕駛建議系統"""
        self.config_path = config_path
        self.ollama_client = None
        self.rag_chat = None
        self._initialized = False
        
        # 載入靜態資料
        self.rest_areas = self._load_rest_areas()
        self.route_alternatives = self._load_route_alternatives()
        self.traffic_patterns = self._load_traffic_patterns()
        
        logger.info("智能駕駛建議系統初始化中...")
    
    async def initialize(self):
        """初始化 AI 組件"""
        if self._initialized:
            return
        
        try:
            # 初始化 Ollama 客戶端
            self.ollama_client = OllamaClient(self.config_path)
            
            # 檢查連接
            if not await self.ollama_client.check_connection():
                raise Exception("Ollama 服務連接失敗")
            
            # 初始化向量儲存和檢索
            vector_store = VectorStore(self.config_path)
            retriever = RAGRetriever(vector_store)
            
            # 初始化 RAG 聊天系統
            self.rag_chat = RAGOllamaChat(self.ollama_client, retriever)
            
            self._initialized = True
            logger.info("智能駕駛建議系統初始化完成")
            
        except Exception as e:
            logger.error(f"初始化失敗: {e}")
            raise
    
    def _load_rest_areas(self) -> Dict[str, List[Dict[str, Any]]]:
        """載入休息站資訊"""
        return {
            '國道1號': [
                {
                    'name': '中壢服務區',
                    'mileage': 53.2,
                    'facilities': ['加油站', '餐廳', '便利店', '停車場', '廁所'],
                    'rating': 4.2,
                    'peak_congestion': ['08:00-10:00', '18:00-20:00']
                },
                {
                    'name': '湖口服務區',
                    'mileage': 62.5,
                    'facilities': ['加油站', '餐廳', '便利店', '停車場', '廁所', '兒童遊戲區'],
                    'rating': 4.5,
                    'peak_congestion': ['07:30-09:30', '17:30-19:30']
                },
                {
                    'name': '泰安服務區',
                    'mileage': 264.5,
                    'facilities': ['加油站', '餐廳', '便利店', '停車場', '廁所', '觀景台'],
                    'rating': 4.8,
                    'peak_congestion': ['09:00-11:00', '16:00-18:00']
                }
            ],
            '國道3號': [
                {
                    'name': '關西服務區',
                    'mileage': 79.0,
                    'facilities': ['加油站', '餐廳', '便利店', '停車場', '廁所'],
                    'rating': 4.3,
                    'peak_congestion': ['08:00-10:00', '18:00-20:00']
                },
                {
                    'name': '西湖服務區',
                    'mileage': 132.5,
                    'facilities': ['加油站', '餐廳', '便利店', '停車場', '廁所', '特色商店'],
                    'rating': 4.6,
                    'peak_congestion': ['09:00-11:00', '17:00-19:00']
                },
                {
                    'name': '南投服務區',
                    'mileage': 214.0,
                    'facilities': ['加油站', '餐廳', '便利店', '停車場', '廁所', '休息區'],
                    'rating': 4.4,
                    'peak_congestion': ['10:00-12:00', '16:00-18:00']
                }
            ]
        }
    
    def _load_route_alternatives(self) -> Dict[str, List[Dict[str, Any]]]:
        """載入替代路線資訊"""
        return {
            '北部': [
                {
                    'name': '台61線西濱快速道路',
                    'description': '沿海快速道路，風景優美但風大',
                    'suitable_conditions': ['國道1號壅塞', '國道3號施工'],
                    'extra_distance': 15,
                    'time_difference': -10,  # 負值表示可能節省時間
                    'tolls': False,
                    'notes': '注意強風路段，大型車輛需謹慎'
                },
                {
                    'name': '台64線八里新店快速道路',
                    'description': '連接八里與新店，避開市區壅塞',
                    'suitable_conditions': ['台北都會區壅塞'],
                    'extra_distance': 8,
                    'time_difference': 15,
                    'tolls': False,
                    'notes': '適合往返台北市與新北市'
                }
            ],
            '中部': [
                {
                    'name': '台74線快速道路',
                    'description': '台中都會區外環道路',
                    'suitable_conditions': ['台中市區壅塞', '國道1號彰化段壅塞'],
                    'extra_distance': 12,
                    'time_difference': 5,
                    'tolls': False,
                    'notes': '避開台中市區，但假日也可能壅塞'
                },
                {
                    'name': '台78線東西向快速道路',
                    'description': '連接雲林與彰化',
                    'suitable_conditions': ['國道1號雲林段壅塞'],
                    'extra_distance': 20,
                    'time_difference': 10,
                    'tolls': False,
                    'notes': '適合中長途迂迴'
                }
            ]
        }
    
    def _load_traffic_patterns(self) -> Dict[str, Dict[str, Any]]:
        """載入交通流量模式"""
        return {
            'weekday_patterns': {
                'morning_peak': {
                    'time_range': ['07:00', '09:30'],
                    'high_congestion_areas': ['台北都會區', '桃園', '台中', '台南', '高雄'],
                    'recommended_actions': ['提早出發', '使用替代道路', '等待尖峰過後']
                },
                'evening_peak': {
                    'time_range': ['17:00', '19:30'],
                    'high_congestion_areas': ['台北都會區', '桃園', '台中', '台南', '高雄'],
                    'recommended_actions': ['延後出發', '使用大眾運輸', '在服務區等待']
                }
            },
            'weekend_patterns': {
                'outbound_peak': {
                    'time_range': ['08:00', '12:00'],
                    'high_congestion_areas': ['國道1號南向', '國道3號南向'],
                    'recommended_actions': ['提早出發', '使用國道5號', '錯開尖峰時間']
                },
                'return_peak': {
                    'time_range': ['15:00', '20:00'],
                    'high_congestion_areas': ['國道1號北向', '國道3號北向'],
                    'recommended_actions': ['延後返程', '使用替代道路', '分段休息']
                }
            }
        }
    
    async def analyze_current_situation(self, 
                                      current_location: Dict[str, Any],
                                      destination: Dict[str, Any],
                                      traffic_data: TrafficCondition,
                                      shockwave_alert: Optional[ShockwaveAlert] = None) -> DriverAdvice:
        """分析當前情況並提供建議"""
        
        try:
            # 1. 構建詳細的情況分析提示
            situation_prompt = self._build_situation_prompt(
                current_location, destination, traffic_data, shockwave_alert
            )
            
            # 2. 使用 RAG 系統獲取相關路段資訊
            rag_response = await self.rag_chat.chat(situation_prompt)
            
            # 3. 分析交通模式和預測
            pattern_analysis = self._analyze_traffic_patterns(traffic_data)
            
            # 4. 尋找附近的休息站
            nearby_rest_areas = self._find_nearby_rest_areas(current_location)
            
            # 5. 查找替代路線
            alternative_routes = self._find_alternative_routes(current_location, destination)
            
            # 6. 綜合生成建議
            advice = await self._generate_comprehensive_advice(
                rag_response, pattern_analysis, nearby_rest_areas, 
                alternative_routes, traffic_data, shockwave_alert
            )
            
            return advice
            
        except Exception as e:
            logger.error(f"分析當前情況失敗: {e}")
            return self._create_fallback_advice(traffic_data)
    
    def _build_situation_prompt(self, current_location: Dict[str, Any], 
                              destination: Dict[str, Any],
                              traffic_data: TrafficCondition,
                              shockwave_alert: Optional[ShockwaveAlert]) -> str:
        """構建情況分析提示"""
        
        current_time = datetime.now()
        
        prompt = f"""【駕駛情況分析】- {current_time.strftime('%Y-%m-%d %H:%M:%S')}

🚗 當前位置資訊：
• 位置：{current_location.get('highway', '')} {current_location.get('direction', '')}
• 里程：{current_location.get('mileage', 0)}公里
• 站點：{current_location.get('friendly_name', current_location.get('station_id', ''))}
• 座標：{current_location.get('lat', 0):.6f}, {current_location.get('lng', 0):.6f}

🎯 目的地資訊：
• 預計目的地：{destination.get('name', '未指定')}
• 預估距離：{destination.get('distance_km', 0)}公里
• 預計行程時間：{destination.get('estimated_time_min', 0)}分鐘

📊 即時交通狀況：
• 當前速度：{traffic_data.speed} km/h
• 車流量：{traffic_data.flow} 輛/小時
• 行駛時間：{traffic_data.travel_time} 分鐘/公里
• 壅塞程度：{traffic_data.congestion_level}
• 資料時間：{traffic_data.timestamp.strftime('%H:%M:%S')}"""

        # 添加震波預警資訊
        if shockwave_alert:
            arrival_str = shockwave_alert.estimated_arrival.strftime('%H:%M:%S') if shockwave_alert.estimated_arrival else '未知'
            prompt += f"""

⚠️ 震波預警：
• 震波強度：{shockwave_alert.intensity}/10
• 警告等級：{shockwave_alert.warning_level}
• 傳播速度：{shockwave_alert.propagation_speed} km/h
• 預計影響時間：{arrival_str}
• 影響區域：{shockwave_alert.affected_area}"""

        # 添加時間和天氣資訊
        is_weekend = current_time.weekday() >= 5
        time_period = self._get_time_period(current_time.hour)
        
        prompt += f"""

📅 時間資訊：
• 當前時間：{current_time.strftime('%H:%M')}
• 時段：{time_period}
• 類型：{'假日' if is_weekend else '平日'}

🤔 請以專業交通規劃師身分，提供詳細的駕駛建議：

【路線規劃要求】
1. 【建議路線】：提供從當前位置到目的地的完整行駛路線
   - 明確指出應行駛的國道、省道、縣道
   - 標明重要的交流道編號和出入口
   - 說明轉彎和變換車道的具體位置

2. 【行駛指引】：提供詳細的駕駛指示
   - 轉彎方向和時機點
   - 車道選擇建議
   - 重要地標和里程標示

3. 【交通狀況分析】：
   - 評估當前路段的交通狀況和安全性
   - 分析是否存在即將惡化的交通風險
   - 預測沿途可能遇到的壅塞路段

4. 【時間距離估算】：
   - 預估總行車時間和距離
   - 各路段分段時間
   - 最佳出發時機建議

5. 【替代方案】：如遇壅塞時的其他路線選擇
6. 【安全提醒】：基於當前路況的駕駛注意事項

請提供完整詳細的路線指引，不要建議使用其他導航軟體。"""

        return prompt
    
    def _get_time_period(self, hour: int) -> str:
        """獲取時段描述"""
        if 6 <= hour < 9:
            return "晨間尖峰"
        elif 9 <= hour < 11:
            return "上午"
        elif 11 <= hour < 13:
            return "中午"
        elif 13 <= hour < 17:
            return "下午"
        elif 17 <= hour < 20:
            return "晚間尖峰"
        elif 20 <= hour < 23:
            return "晚間"
        else:
            return "深夜"
    
    def _analyze_traffic_patterns(self, traffic_data: TrafficCondition) -> Dict[str, Any]:
        """分析交通模式"""
        current_time = datetime.now()
        is_weekend = current_time.weekday() >= 5
        hour = current_time.hour
        
        pattern_type = 'weekend_patterns' if is_weekend else 'weekday_patterns'
        patterns = self.traffic_patterns[pattern_type]
        
        # 判斷是否在尖峰時段
        is_peak = False
        peak_type = None
        
        for period_name, period_data in patterns.items():
            start_hour = int(period_data['time_range'][0].split(':')[0])
            end_hour = int(period_data['time_range'][1].split(':')[0])
            
            if start_hour <= hour <= end_hour:
                is_peak = True
                peak_type = period_name
                break
        
        return {
            'is_weekend': is_weekend,
            'is_peak': is_peak,
            'peak_type': peak_type,
            'current_hour': hour,
            'congestion_trend': self._predict_congestion_trend(traffic_data, hour),
            'recommended_wait_time': self._calculate_optimal_wait_time(traffic_data, hour)
        }
    
    def _predict_congestion_trend(self, traffic_data: TrafficCondition, current_hour: int) -> str:
        """預測壅塞趨勢"""
        speed = traffic_data.speed
        
        if speed > 80:
            return "暢通"
        elif speed > 60:
            if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
                return "即將惡化"
            else:
                return "良好"
        elif speed > 40:
            return "逐漸改善" if current_hour > 19 or current_hour < 7 else "持續惡化"
        else:
            return "嚴重壅塞"
    
    def _calculate_optimal_wait_time(self, traffic_data: TrafficCondition, current_hour: int) -> int:
        """計算最佳等待時間（分鐘）"""
        if traffic_data.speed > 60:
            return 0  # 不需要等待
        
        # 根據時段和壅塞程度計算等待時間
        if 7 <= current_hour <= 9:
            return 60 if traffic_data.speed < 30 else 30
        elif 17 <= current_hour <= 19:
            return 90 if traffic_data.speed < 20 else 45
        else:
            return 30 if traffic_data.speed < 40 else 15
    
    def _find_nearby_rest_areas(self, current_location: Dict[str, Any]) -> List[RestAreaInfo]:
        """尋找附近休息站"""
        highway = current_location.get('highway', '')
        current_mileage = current_location.get('mileage', 0)
        
        if highway not in self.rest_areas:
            return []
        
        nearby_areas = []
        for area in self.rest_areas[highway]:
            distance = abs(area['mileage'] - current_mileage)
            
            # 只考慮30公里內的休息站
            if distance <= 30:
                direction = "前方" if area['mileage'] > current_mileage else "後方"
                travel_time = int(distance / 80 * 60)  # 假設80km/h計算時間
                
                rest_area = RestAreaInfo(
                    name=area['name'],
                    distance_km=distance,
                    direction=direction,
                    facilities=area['facilities'],
                    estimated_travel_time=travel_time
                )
                nearby_areas.append(rest_area)
        
        # 按距離排序
        nearby_areas.sort(key=lambda x: x.distance_km)
        return nearby_areas[:3]  # 最多返回3個
    
    def _find_alternative_routes(self, current_location: Dict[str, Any], 
                                destination: Dict[str, Any]) -> List[RouteAlternative]:
        """查找替代路線"""
        # 簡化版本，基於區域查找替代路線
        region = self._determine_region(current_location)
        
        if region not in self.route_alternatives:
            return []
        
        alternatives = []
        for route_data in self.route_alternatives[region]:
            alternative = RouteAlternative(
                route_name=route_data['name'],
                description=route_data['description'],
                extra_distance_km=route_data['extra_distance'],
                time_difference_min=route_data['time_difference'],
                congestion_avoidance=True,
                recommended_conditions=route_data['suitable_conditions']
            )
            alternatives.append(alternative)
        
        return alternatives
    
    def _determine_region(self, location: Dict[str, Any]) -> str:
        """判斷地區"""
        mileage = location.get('mileage', 0)
        
        if mileage <= 100:
            return '北部'
        elif mileage <= 250:
            return '中部'
        else:
            return '南部'
    
    async def _generate_comprehensive_advice(self,
                                           rag_response: str,
                                           pattern_analysis: Dict[str, Any],
                                           nearby_rest_areas: List[RestAreaInfo],
                                           alternative_routes: List[RouteAlternative],
                                           traffic_data: TrafficCondition,
                                           shockwave_alert: Optional[ShockwaveAlert]) -> DriverAdvice:
        """綜合生成建議"""
        
        # 根據RAG回應和分析結果決定建議優先級和行動類型
        priority = self._determine_priority(rag_response, traffic_data, shockwave_alert)
        action_type = self._determine_action_type(rag_response, pattern_analysis)
        
        # 生成建議標題和描述
        title, description = self._generate_advice_content(
            action_type, traffic_data, pattern_analysis, shockwave_alert
        )
        
        # 計算時間節省
        time_saving = self._calculate_time_saving(action_type, pattern_analysis)
        
        # 評估安全影響
        safety_impact = self._assess_safety_impact(traffic_data, shockwave_alert)
        
        return DriverAdvice(
            priority=priority,
            action_type=action_type,
            title=title,
            description=description,
            reasoning=rag_response[:500] + "..." if len(rag_response) > 500 else rag_response,
            time_saving_min=time_saving,
            safety_impact=safety_impact,
            alternatives=alternative_routes,
            rest_areas=nearby_rest_areas,
            estimated_cost=self._estimate_cost(action_type, alternative_routes)
        )
    
    def _determine_priority(self, rag_response: str, traffic_data: TrafficCondition, 
                           shockwave_alert: Optional[ShockwaveAlert]) -> str:
        """確定建議優先級"""
        response_lower = rag_response.lower()
        
        # 緊急情況
        if (shockwave_alert and shockwave_alert.warning_level == 'severe' or
            traffic_data.speed < 20 or
            any(word in response_lower for word in ['緊急', '危險', '立即', '嚴重'])):
            return 'urgent'
        
        # 高優先級
        elif (shockwave_alert and shockwave_alert.warning_level == 'high' or
              traffic_data.speed < 40 or
              any(word in response_lower for word in ['建議', '應該', '需要'])):
            return 'high'
        
        # 中等優先級
        elif traffic_data.speed < 60:
            return 'medium'
        
        # 低優先級
        else:
            return 'low'
    
    def _determine_action_type(self, rag_response: str, pattern_analysis: Dict[str, Any]) -> str:
        """確定行動類型"""
        response_lower = rag_response.lower()
        
        if any(word in response_lower for word in ['休息站', '等待', '暫停']):
            return 'wait'
        elif any(word in response_lower for word in ['替代', '改道', '繞行']):
            return 'reroute'
        elif any(word in response_lower for word in ['下交流道', '出去', '離開']):
            return 'exit'
        elif any(word in response_lower for word in ['減速', '慢行', '小心']):
            return 'slow_down'
        else:
            return 'continue'
    
    def _generate_advice_content(self, action_type: str, traffic_data: TrafficCondition,
                               pattern_analysis: Dict[str, Any], 
                               shockwave_alert: Optional[ShockwaveAlert]) -> tuple:
        """生成建議內容"""
        
        if action_type == 'wait':
            title = "建議前往休息站等待"
            description = f"目前路段速度 {traffic_data.speed} km/h，建議等待 {pattern_analysis.get('recommended_wait_time', 30)} 分鐘後再上路。"
            
        elif action_type == 'reroute':
            title = "建議使用替代路線"
            description = f"當前路段嚴重壅塞，建議考慮替代道路以節省時間。"
            
        elif action_type == 'exit':
            title = "建議暫時離開高速公路"
            description = f"前方可能有嚴重壅塞或事故，建議就近下交流道。"
            
        elif action_type == 'slow_down':
            title = "建議減速謹慎駕駛"
            description = f"路段條件需要特別注意，請減速慢行並保持安全車距。"
            
        else:  # continue
            title = "建議繼續當前路線"
            description = f"目前交通狀況良好，可以繼續依計劃路線行駛。"
        
        return title, description
    
    def _calculate_time_saving(self, action_type: str, pattern_analysis: Dict[str, Any]) -> Optional[int]:
        """計算時間節省"""
        if action_type == 'wait':
            return -pattern_analysis.get('recommended_wait_time', 30)  # 等待時間為負節省
        elif action_type == 'reroute':
            return 15  # 假設替代路線平均節省15分鐘
        elif action_type == 'exit':
            return 10  # 假設暫時下交流道節省10分鐘
        else:
            return None
    
    def _assess_safety_impact(self, traffic_data: TrafficCondition, 
                            shockwave_alert: Optional[ShockwaveAlert]) -> str:
        """評估安全影響"""
        if shockwave_alert and shockwave_alert.warning_level in ['high', 'severe']:
            return "高風險 - 建議立即採取行動"
        elif traffic_data.speed < 30:
            return "中等風險 - 注意車距和車速"
        elif traffic_data.speed < 60:
            return "輕微風險 - 保持警覺"
        else:
            return "低風險 - 正常駕駛"
    
    def _estimate_cost(self, action_type: str, alternatives: List[RouteAlternative]) -> Optional[str]:
        """估算成本"""
        if action_type == 'wait':
            return "等待成本：時間成本，無額外費用"
        elif action_type == 'reroute' and alternatives:
            return f"替代路線：可能增加 5-15 公里距離"
        elif action_type == 'exit':
            return "暫時下交流道：可能產生額外過路費"
        else:
            return None
    
    def _create_fallback_advice(self, traffic_data: TrafficCondition) -> DriverAdvice:
        """創建備用建議"""
        return DriverAdvice(
            priority='medium',
            action_type='continue',
            title='系統建議',
            description='AI 系統暫時不可用，請依據當前交通狀況小心駕駛。',
            reasoning='系統暫時無法提供詳細分析，建議駕駛人依實際路況判斷。',
            time_saving_min=None,
            safety_impact='請保持警覺',
            alternatives=[],
            rest_areas=[],
            estimated_cost=None
        )

# 使用範例
async def main():
    """測試智能駕駛建議系統"""
    advisor = IntelligentDriverAdvisor()
    await advisor.initialize()
    
    # 模擬當前狀況
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
    
    # 獲取建議
    advice = await advisor.analyze_current_situation(
        current_location, destination, traffic_data, shockwave_alert
    )
    
    print("=== 智能駕駛建議 ===")
    print(f"優先級：{advice.priority}")
    print(f"建議行動：{advice.action_type}")
    print(f"標題：{advice.title}")
    print(f"描述：{advice.description}")
    print(f"安全評估：{advice.safety_impact}")
    
    if advice.rest_areas:
        print("\n附近休息站：")
        for area in advice.rest_areas:
            print(f"- {area.name} ({area.direction}{area.distance_km:.1f}公里)")
    
    if advice.alternatives:
        print("\n替代路線：")
        for alt in advice.alternatives:
            print(f"- {alt.route_name}: {alt.description}")

if __name__ == "__main__":
    asyncio.run(main())
