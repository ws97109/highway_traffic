'use client';

import { useState, useEffect, useCallback } from 'react';

interface ShockwaveData {
  id: string;
  location: string;
  lat: number;
  lng: number;
  intensity: number;
  propagationSpeed: number;
  estimatedArrivalTime: Date;
  affectedArea: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  recommendations: string[];
  alternativeRoutes?: AlternativeRoute[];
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
      // 獲取震波資料
      const shockwaveResponse = await fetch('/api/shockwave/active');
      if (!shockwaveResponse.ok) {
        throw new Error(`震波資料獲取失敗: ${shockwaveResponse.status}`);
      }
      const shockwaveData = await shockwaveResponse.json();
      
      // 轉換震波資料格式
      const formattedShockwaves: ShockwaveData[] = shockwaveData.shockwaves.map((sw: any) => ({
        id: sw.id,
        location: sw.location_name,
        lat: sw.latitude,
        lng: sw.longitude,
        intensity: sw.intensity,
        propagationSpeed: sw.propagation_speed,
        estimatedArrivalTime: new Date(sw.estimated_arrival),
        affectedArea: sw.affected_area,
        severity: determineSeverity(sw.intensity, sw.propagation_speed),
        description: sw.description || `在 ${sw.location_name} 檢測到交通震波`,
        recommendations: generateRecommendations(sw.intensity, sw.propagation_speed),
        alternativeRoutes: sw.alternative_routes || []
      }));

      setShockwaves(formattedShockwaves);

      // 獲取預測資料
      const predictionResponse = await fetch('/api/prediction/traffic');
      if (predictionResponse.ok) {
        const predictionData = await predictionResponse.json();
        const formattedPredictions: PredictionData[] = predictionData.predictions.map((pred: any) => ({
          stationId: pred.station_id,
          location: pred.location_name,
          predictedSpeed: pred.predicted_speed,
          predictedFlow: pred.predicted_flow,
          confidence: pred.confidence,
          timeHorizon: pred.time_horizon,
          timestamp: new Date(pred.timestamp)
        }));
        setPredictions(formattedPredictions);
      }

      // 生成警告
      const generatedAlerts = generateAlerts(formattedShockwaves, userLocation);
      setAlerts(generatedAlerts);

    } catch (err) {
      setError(err instanceof Error ? err.message : '獲取震波資料失敗');
      console.error('獲取震波資料失敗:', err);
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
    
    // 只對附近的震波生成警告（50km內）
    if (!distance || distance <= 50) {
      const timeToArrival = Math.max(0, (sw.estimatedArrivalTime.getTime() - Date.now()) / (1000 * 60));
      
      if (timeToArrival <= 60) { // 60分鐘內會到達
        alerts.push({
          id: `alert-${sw.id}`,
          title: `${sw.location} 震波警報`,
          description: `預計 ${Math.round(timeToArrival)} 分鐘後到達您的位置`,
          level: sw.severity === 'critical' || sw.severity === 'high' ? 'high' : 
                 sw.severity === 'medium' ? 'medium' : 'low',
          estimatedImpact: `車速可能下降至 ${Math.max(10, 80 - sw.intensity * 8)} km/h`,
          timestamp: new Date().toISOString(),
          recommendations: sw.recommendations
        });
      }
    }
  });
  
  return alerts;
}

export default useShockwaveData;
