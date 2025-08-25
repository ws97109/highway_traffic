'use client';

import React, { useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';

interface RadarWaveProps {
  lat: number;
  lng: number;
  map: google.maps.Map;
  severity: 'low' | 'medium' | 'high' | 'critical';
  intensity: number;
  radius: number;
  onRemove?: () => void;
}

const RadarWaveImplementation: React.FC<RadarWaveProps> = ({
  lat,
  lng,
  map,
  severity,
  intensity,
  radius,
  onRemove
}) => {
  const wavesRef = useRef<google.maps.Circle[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const centerMarkerRef = useRef<google.maps.Circle | null>(null);
  const currentWaveIndex = useRef(0);

  const getSeverityConfig = () => {
    switch (severity) {
      case 'critical':
        return { 
          color: '#DC2626', 
          interval: 600, 
          maxWaves: 5, // 增加更多波紋
          duration: 4000, // 更長的動畫時間
          opacity: 0.9 // 更高的不透明度
        };
      case 'high':
        return { 
          color: '#EF4444', 
          interval: 800, 
          maxWaves: 4, 
          duration: 3500, 
          opacity: 0.8 
        };
      case 'medium':
        return { 
          color: '#F59E0B', 
          interval: 1000, 
          maxWaves: 3, 
          duration: 3000, 
          opacity: 0.7 
        };
      default:
        return { 
          color: '#10B981', 
          interval: 1200, 
          maxWaves: 2, 
          duration: 2500, 
          opacity: 0.6 
        };
    }
  };

  const createWave = () => {
    if (!map || typeof window === 'undefined' || !window.google) return;

    const config = getSeverityConfig();
    currentWaveIndex.current++;

    // 創建一個更明顯的起始圓圈，並且有填充色
    const wave = new google.maps.Circle({
      strokeColor: config.color,
      strokeOpacity: config.opacity,
      strokeWeight: 3,
      fillColor: config.color,
      fillOpacity: config.opacity * 0.3, // 添加填充讓波更明顯
      map,
      center: { lat, lng },
      radius: 100, // 更大的起始半徑
      clickable: false,
    });

    wavesRef.current.push(wave);

    // 更戲劇性的動畫擴展
    let currentRadius = 100;
    let currentStrokeOpacity = config.opacity;
    let currentFillOpacity = config.opacity * 0.3;
    const maxRadius = Math.max(radius, 2000); // 確保最大半徑足夠大
    const totalSteps = config.duration / 30; // 每30ms一步，更流暢
    const radiusStep = (maxRadius - 100) / totalSteps;
    const strokeOpacityStep = config.opacity / totalSteps;
    const fillOpacityStep = (config.opacity * 0.3) / totalSteps;

    let stepCount = 0;
    const animationInterval = setInterval(() => {
      stepCount++;
      currentRadius += radiusStep;
      currentStrokeOpacity -= strokeOpacityStep;
      currentFillOpacity -= fillOpacityStep;

      // 使用緩動函數讓擴散更自然
      const progress = stepCount / totalSteps;
      const easeOut = 1 - Math.pow(1 - progress, 2); // 緩動函數
      const actualRadius = 100 + (maxRadius - 100) * easeOut;
      
      // 創造脈衝效果 - 邊框寬度也會變化
      const pulseEffect = Math.sin(progress * Math.PI * 4) * 0.3 + 1; // 創造脈衝
      const strokeWeight = Math.max(0.5, 3 * (1 - progress) * pulseEffect);

      if (progress >= 1 || currentStrokeOpacity <= 0) {
        // 動畫結束，移除圓圈
        wave.setMap(null);
        wavesRef.current = wavesRef.current.filter(w => w !== wave);
        clearInterval(animationInterval);
        return;
      }

      // 更新圓圈 - 更戲劇性的效果
      wave.setRadius(actualRadius);
      wave.setOptions({
        strokeOpacity: Math.max(0, currentStrokeOpacity),
        fillOpacity: Math.max(0, currentFillOpacity),
        strokeWeight: strokeWeight
      });
    }, 30); // 更頻繁的更新讓動畫更流暢
  };

  useEffect(() => {
    if (!map || typeof window === 'undefined' || !window.google) return;

    const config = getSeverityConfig();

    // 創建中心脈衝點 - 更明顯的效果
    const centerMarker = new google.maps.Circle({
      strokeColor: config.color,
      strokeOpacity: 1,
      strokeWeight: 4,
      fillColor: config.color,
      fillOpacity: 0.8,
      map,
      center: { lat, lng },
      radius: 150, // 更大的中心點
      clickable: false,
    });

    centerMarkerRef.current = centerMarker;

    // 中心點脈衝動畫
    let pulseDirection = 1; // 1 為擴大，-1 為縮小
    let pulseScale = 1;
    
    const pulseInterval = setInterval(() => {
      pulseScale += pulseDirection * 0.15; // 更明顯的脈衝
      
      if (pulseScale >= 1.6) {
        pulseDirection = -1; // 開始縮小
      } else if (pulseScale <= 0.8) {
        pulseDirection = 1; // 開始擴大
      }
      
      const newRadius = 150 * pulseScale;
      const newOpacity = 0.8 + (pulseScale - 1) * 0.3; // 透明度也跟著變化
      
      centerMarker.setRadius(newRadius);
      centerMarker.setOptions({
        fillOpacity: Math.max(0.3, Math.min(1, newOpacity)),
        strokeOpacity: Math.max(0.6, Math.min(1, newOpacity + 0.2))
      });
    }, 120); // 較快的脈衝速度

    // 立即創建第一個波紋
    createWave();

    // 設置週期性創建波紋
    intervalRef.current = setInterval(() => {
      if (wavesRef.current.length < config.maxWaves) {
        createWave();
      }
    }, config.interval);

    return () => {
      // 清理脈衝動畫
      clearInterval(pulseInterval);
      centerMarker.setMap(null);
      
      // 清理波紋
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      
      wavesRef.current.forEach(wave => {
        wave.setMap(null);
      });
      wavesRef.current = [];
      
      onRemove?.();
    };
  }, [map, lat, lng, severity, intensity, radius]);

  return null;
};

// 使用動態導入避免 SSR 問題
const RadarWave = dynamic(() => Promise.resolve(RadarWaveImplementation), {
  ssr: false,
  loading: () => null
});

export default RadarWave;
