'use client';

import { useState, useEffect, useCallback } from 'react';

interface TrafficStation {
  stationId: string;
  name: string;
  lat: number;
  lng: number;
  flow: number;
  speed: number;
  status: 'normal' | 'congested' | 'blocked';
  lastUpdate: Date;
}

interface TrafficDataHook {
  trafficData: TrafficStation[];
  loading: boolean;
  error: string | null;
  refreshData: () => Promise<void>;
  getStationById: (stationId: string) => TrafficStation | undefined;
}

export const useTrafficData = (): TrafficDataHook => {
  const [trafficData, setTrafficData] = useState<TrafficStation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTrafficData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('🔄 正在獲取交通資料...');
      const response = await fetch('/api/traffic/current');
      
      console.log('📡 API 回應狀態:', response.status, response.statusText);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('📊 收到交通資料:', data);
      
      // 檢查資料結構
      if (!data.stations || !Array.isArray(data.stations)) {
        throw new Error('API 返回資料格式錯誤: 缺少 stations 陣列');
      }
      
      // 轉換資料格式
      const formattedData: TrafficStation[] = data.stations.map((station: any) => ({
        stationId: station.id,
        name: station.name,
        lat: station.latitude,
        lng: station.longitude,
        flow: station.flow || 0,
        speed: station.speed || 0,
        status: determineStatus(station.speed, station.flow),
        lastUpdate: new Date(station.timestamp)
      }));
      
      console.log('✅ 成功處理交通資料:', formattedData.length, '個站點');
      setTrafficData(formattedData);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '獲取交通資料失敗';
      setError(errorMessage);
      console.error('❌ 獲取交通資料失敗:', err);
      
      // 不再使用模擬資料，等待真實資料
      console.log('⚠️ 暫無真實交通資料可用');
      setTrafficData([]);
      
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshData = useCallback(async () => {
    await fetchTrafficData();
  }, [fetchTrafficData]);

  const getStationById = useCallback((stationId: string) => {
    return trafficData.find(station => station.stationId === stationId);
  }, [trafficData]);

  // 初始載入和定期更新
  useEffect(() => {
    fetchTrafficData();
    
    // 每5分鐘更新一次
    const interval = setInterval(fetchTrafficData, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [fetchTrafficData]);

  return {
    trafficData,
    loading,
    error,
    refreshData,
    getStationById
  };
};

// 輔助函數：根據速度和流量判斷交通狀態
function determineStatus(speed: number, flow: number): 'normal' | 'congested' | 'blocked' {
  if (speed < 20) {
    return 'blocked';
  } else if (speed < 50 || flow > 2000) {
    return 'congested';
  } else {
    return 'normal';
  }
}

export default useTrafficData;
