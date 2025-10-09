'use client';

import { useState, useEffect, useCallback } from 'react';

interface ShockwaveData {
  id: string;
  location: string;
  lat: number;
  lng: number;
  intensity: number;
  propagationSpeed: number;
  waveSpeed?: number;  // 實際波速（可能為負）
  waveDirection?: 'upstream' | 'downstream';
  estimatedArrivalTime: Date;
  affectedArea: number;
  affected_area?: number;  // 後端可能使用底線式命名
  shock_duration?: number;  // 持續時間（分鐘）
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  recommendations: string[];
  alternativeRoutes?: AlternativeRoute[];
  shockOccurrenceTime?: string;
  speedDrop?: number;
  initialSpeed?: number;
  finalSpeed?: number;
  initialFlow?: number;
  finalFlow?: number;
  queueGrowthRate?: number;  // 隊列增長率 (veh/hr)
}

interface AlternativeRoute {
  id: string;
  name: string;
  additionalTime: number;
  avoidanceSuccess: number;
}

interface PredictionData {
  stationId: string;
  location: string;
  predictedSpeed: number;
  predictedFlow: number;
  confidence: number;
  timeHorizon: number;
  timestamp: Date;
}

interface AlertData {
  id: string;
  title: string;
  description: string;
  level: 'low' | 'medium' | 'high';
  estimatedImpact: string;
  timestamp: string;
  recommendations?: string[];
}

interface ShockwaveDataHook {
  shockwaves: ShockwaveData[];
  predictions: PredictionData[];
  alerts: AlertData[];
  loading: boolean;
  error: string | null;
  refreshData: () => Promise<void>;
  getShockwaveById: (id: string) => ShockwaveData | undefined;
  dismissAlert: (alertId: string) => void;
}

export const useShockwaveData = (userLocation?: { lat: number; lng: number }): ShockwaveDataHook => {
  const [shockwaves, setShockwaves] = useState<ShockwaveData[]>([]);
  const [predictions, setPredictions] = useState<PredictionData[]>([]);
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchShockwaveData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('🌊 正在獲取震波資料...');
      
      // 獲取震波資料
      const shockwaveResponse = await fetch('/api/shockwave/active');
      console.log('📡 震波 API 回應狀態:', shockwaveResponse.status);
      
      if (!shockwaveResponse.ok) {
        throw new Error(`震波資料獲取失敗: ${shockwaveResponse.status}`);
      }
      const shockwaveData = await shockwaveResponse.json();
      console.log('📊 收到震波資料:', shockwaveData);
      
      // 檢查和轉換震波資料格式
      let formattedShockwaves: ShockwaveData[] = [];
      if (shockwaveData.shockwaves && Array.isArray(shockwaveData.shockwaves)) {
        formattedShockwaves = shockwaveData.shockwaves.map((sw: any) => ({
          id: sw.id,
          location: sw.location_name,
          lat: sw.latitude,
          lng: sw.longitude,
          intensity: sw.intensity,
          propagationSpeed: sw.propagation_speed,
          waveSpeed: sw.wave_speed,  // 實際波速（可能為負）
          waveDirection: sw.wave_direction,  // 'upstream' 或 'downstream'
          estimatedArrivalTime: new Date(sw.estimated_arrival),
          affectedArea: sw.affected_area,
          shock_duration: sw.shock_duration,  // 持續時間（分鐘）
          severity: determineSeverity(sw.intensity, sw.propagation_speed),
          description: sw.description || `在 ${sw.location_name} 檢測到交通震波`,
          recommendations: generateRecommendations(sw.intensity, sw.propagation_speed),
          alternativeRoutes: sw.alternative_routes || [],
          shockOccurrenceTime: sw.shock_occurrence_time,
          speedDrop: sw.speed_drop,
          initialSpeed: sw.initial_speed,
          finalSpeed: sw.final_speed,
          initialFlow: sw.initial_flow,
          finalFlow: sw.final_flow,
          queueGrowthRate: sw.queue_growth_rate  // 隊列增長率
        }));
      } else {
        console.log('⚠️ 沒有震波資料，使用模擬資料');
        // 創建一些模擬震波資料
        formattedShockwaves = [
          {
            id: 'mock-sw-001',
            location: '國道1號桃園段',
            lat: 25.0330,
            lng: 121.5654,
            intensity: 6.5,
            propagationSpeed: 18,
            estimatedArrivalTime: new Date(Date.now() + 15 * 60 * 1000), // 15分鐘後
            affectedArea: 5,
            severity: 'medium',
            description: '模擬震波事件 - 中等強度',
            recommendations: ['建議減速慢行', '保持安全車距'],
            alternativeRoutes: [],
            shockOccurrenceTime: new Date().toISOString(),
            speedDrop: 25
          }
        ];
      }

      setShockwaves(formattedShockwaves);
      console.log('✅ 成功處理震波資料:', formattedShockwaves.length, '個事件');

      // 獲取預測資料
      try {
        console.log('🔮 正在獲取預測資料...');
        const predictionResponse = await fetch('/api/prediction/traffic');
        console.log('📡 預測 API 回應狀態:', predictionResponse.status);
        
        let formattedPredictions: PredictionData[] = [];
        if (predictionResponse.ok) {
          const predictionData = await predictionResponse.json();
          console.log('📊 收到預測資料:', predictionData);
          
          if (predictionData.predictions && Array.isArray(predictionData.predictions)) {
            formattedPredictions = predictionData.predictions.map((pred: any) => ({
              stationId: pred.station_id,
              location: pred.location_name,
              predictedSpeed: pred.predicted_speed,
              predictedFlow: pred.predicted_flow,
              confidence: pred.confidence,
              timeHorizon: pred.time_horizon,
              timestamp: new Date(pred.timestamp)
            }));
          } else {
            // 創建模擬預測資料
            formattedPredictions = [
              {
                stationId: 'mock-pred-001',
                location: '模擬預測站點',
                predictedSpeed: 75,
                predictedFlow: 1100,
                confidence: 0.85,
                timeHorizon: 30,
                timestamp: new Date()
              }
            ];
          }
        }
        
        setPredictions(formattedPredictions);
        console.log('✅ 成功處理預測資料:', formattedPredictions.length, '個預測');
        
      } catch (predError) {
        console.warn('⚠️ 預測資料獲取失敗:', predError);
        // 設置模擬預測資料
        setPredictions([
          {
            stationId: 'mock-pred-001',
            location: '模擬預測站點',
            predictedSpeed: 75,
            predictedFlow: 1100,
            confidence: 0.85,
            timeHorizon: 30,
            timestamp: new Date()
          }
        ]);
      }

      // 生成警告
      const generatedAlerts = generateAlerts(formattedShockwaves, userLocation);
      setAlerts(generatedAlerts);
      console.log('📢 生成警告:', generatedAlerts.length, '個警告');

    } catch (err) {
      setError(err instanceof Error ? err.message : '獲取震波資料失敗');
      console.error('❌ 獲取震波資料失敗:', err);
      
      // 載入備用模擬資料
      console.log('📋 載入模擬震波資料');
      const mockShockwaves = [
        {
          id: 'mock-sw-fallback',
          location: '國道1號模擬段',
          lat: 25.0330,
          lng: 121.5654,
          intensity: 5.5,
          propagationSpeed: 15,
          estimatedArrivalTime: new Date(Date.now() + 20 * 60 * 1000),
          affectedArea: 3,
          severity: 'medium' as const,
          description: '備用模擬震波資料',
          recommendations: ['系統模擬模式', '實際使用請檢查API連接'],
          alternativeRoutes: [],
          shockOccurrenceTime: new Date().toISOString(),
          speedDrop: 20
        }
      ];
      
      const mockPredictions = [
        {
          stationId: 'mock-pred-fallback',
          location: '備用預測站點',
          predictedSpeed: 70,
          predictedFlow: 950,
          confidence: 0.75,
          timeHorizon: 30,
          timestamp: new Date()
        }
      ];
      
      setShockwaves(mockShockwaves);
      setPredictions(mockPredictions);
      
      const mockAlerts = generateAlerts(mockShockwaves, userLocation);
      setAlerts(mockAlerts);
      
    } finally {
      setLoading(false);
    }
  }, [userLocation]);

  const refreshData = useCallback(async () => {
    await fetchShockwaveData();
  }, [fetchShockwaveData]);

  const getShockwaveById = useCallback((id: string) => {
    return shockwaves.find(sw => sw.id === id);
  }, [shockwaves]);

  const dismissAlert = useCallback((alertId: string) => {
    setAlerts(prev => prev.filter(alert => alert.id !== alertId));
  }, []);

  // 初始載入和定期更新
  useEffect(() => {
    fetchShockwaveData();
    
    // 每30秒更新一次震波資料
    const interval = setInterval(fetchShockwaveData, 30 * 1000);
    
    return () => clearInterval(interval);
  }, [fetchShockwaveData]);

  return {
    shockwaves,
    predictions,
    alerts,
    loading,
    error,
    refreshData,
    getShockwaveById,
    dismissAlert
  };
};

// 輔助函數：判斷震波嚴重程度
function determineSeverity(intensity: number, propagationSpeed: number): 'low' | 'medium' | 'high' | 'critical' {
  if (intensity >= 8 || propagationSpeed >= 25) {
    return 'critical';
  } else if (intensity >= 6 || propagationSpeed >= 20) {
    return 'high';
  } else if (intensity >= 4 || propagationSpeed >= 15) {
    return 'medium';
  } else {
    return 'low';
  }
}

// 輔助函數：生成建議
function generateRecommendations(intensity: number, propagationSpeed: number): string[] {
  const recommendations: string[] = [];
  
  if (intensity >= 7) {
    recommendations.push('建議立即尋找最近的出口或休息區');
    recommendations.push('避免變換車道，保持安全距離');
  } else if (intensity >= 5) {
    recommendations.push('減速慢行，注意前方車況');
    recommendations.push('考慮使用替代路線');
  } else {
    recommendations.push('保持警覺，注意交通狀況變化');
  }
  
  if (propagationSpeed >= 20) {
    recommendations.push('震波傳播速度較快，請提前做好準備');
  }
  
  return recommendations;
}

// 輔助函數：生成警告
function generateAlerts(shockwaves: ShockwaveData[], userLocation?: { lat: number; lng: number }): AlertData[] {
  const alerts: AlertData[] = [];
  
  shockwaves.forEach(sw => {
    // 計算距離（如果有用戶位置）
    let distance: number | null = null;
    if (userLocation) {
      const R = 6371; // 地球半徑 (km)
      const dLat = (sw.lat - userLocation.lat) * Math.PI / 180;
      const dLon = (sw.lng - userLocation.lng) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(userLocation.lat * Math.PI / 180) * Math.cos(sw.lat * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      distance = R * c;
    }
    
    // 如果沒有用戶位置（管理者介面），顯示所有警告
    // 如果有用戶位置，只對附近的震波生成警告（50km內）
    if (!userLocation || !distance || distance <= 50) {
      const timeToArrival = Math.max(0, (sw.estimatedArrivalTime.getTime() - Date.now()) / (1000 * 60));
      
      // 管理者介面顯示所有衝擊波，使用者介面只顯示60分鐘內會到達的
      if (!userLocation || timeToArrival <= 60) {
        alerts.push({
          id: `alert-${sw.id}`,
          title: userLocation ? `${sw.location} 震波警報` : `${sw.location} 衝擊波監測`,
          description: userLocation ? 
            `預計 ${Math.round(timeToArrival)} 分鐘後到達您的位置` :
            `檢測到真實交通衝擊波，強度: ${sw.intensity.toFixed(1)}，速度下降: ${sw.speedDrop || 0} km/h`,
          level: sw.severity === 'critical' || sw.severity === 'high' ? 'high' : 
                 sw.severity === 'medium' ? 'medium' : 'low',
          estimatedImpact: `車速可能下降至 ${Math.max(10, 80 - sw.intensity * 8)} km/h`,
          timestamp: sw.shockOccurrenceTime || new Date().toISOString(),
          recommendations: sw.recommendations
        });
      }
    }
  });
  
  return alerts;
}

export default useShockwaveData;
