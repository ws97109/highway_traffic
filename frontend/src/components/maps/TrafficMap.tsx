'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Loader } from '@googlemaps/js-api-loader';

// 類型定義
interface TrafficMapProps {
  onLocationUpdate?: (lat: number, lng: number) => void;
  trafficData?: TrafficData[];
  shockwaves?: ShockwaveData[];
  predictions?: PredictionData[];
  center?: { lat: number; lng: number };
  zoom?: number;
  showTrafficLayer?: boolean;
  showShockwaveOverlay?: boolean;
}

interface TrafficData {
  stationId: string;
  name: string;
  lat: number;
  lng: number;
  flow: number;
  speed: number;
  status: 'normal' | 'congested' | 'blocked';
}

interface ShockwaveData {
  id: string;
  lat: number;
  lng: number;
  intensity: number;
  propagationSpeed: number;
  estimatedArrival: Date;
  affectedArea: number;
}

interface PredictionData {
  stationId: string;
  predictedFlow: number;
  predictedSpeed: number;
  confidence: number;
  timeHorizon: number;
}

const TrafficMap: React.FC<TrafficMapProps> = ({
  onLocationUpdate,
  trafficData = [],
  shockwaves = [],
  predictions = [],
  center = { lat: 25.0330, lng: 121.5654 }, // 台北預設位置
  zoom = 10,
  showTrafficLayer = true,
  showShockwaveOverlay = true,
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [markers, setMarkers] = useState<google.maps.Marker[]>([]);
  const [trafficLayer, setTrafficLayer] = useState<google.maps.TrafficLayer | null>(null);
  const [shockwaveOverlays, setShockwaveOverlays] = useState<google.maps.Circle[]>([]);

  // Google Maps API 載入
  useEffect(() => {
    const loader = new Loader({
      apiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
      version: 'weekly',
      libraries: ['places', 'geometry'],
      language: 'zh-TW',
      region: 'TW',
    });

    loader.load().then(() => {
      setIsLoaded(true);
    }).catch((error) => {
      console.error('Google Maps API 載入失敗:', error);
    });
  }, []);

  // 初始化地圖
  useEffect(() => {
    if (isLoaded && mapRef.current && !map) {
      const newMap = new google.maps.Map(mapRef.current, {
        center,
        zoom,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        mapTypeControl: true,
        streetViewControl: false,
        fullscreenControl: true,
        zoomControl: true,
        styles: [
          {
            featureType: 'poi',
            elementType: 'labels',
            stylers: [{ visibility: 'off' }]
          }
        ]
      });

      // 交通狀況圖層
      if (showTrafficLayer) {
        const traffic = new google.maps.TrafficLayer();
        traffic.setMap(newMap);
        setTrafficLayer(traffic);
      }

      // 點擊事件
      newMap.addListener('click', (event: google.maps.MapMouseEvent) => {
        if (event.latLng) {
          const lat = event.latLng.lat();
          const lng = event.latLng.lng();
          onLocationUpdate?.(lat, lng);
        }
      });

      setMap(newMap);
    }
  }, [isLoaded, center, zoom, onLocationUpdate, showTrafficLayer]);

  // 更新交通資料標記
  useEffect(() => {
    if (!map) return;

    // 清除現有標記
    markers.forEach(marker => marker.setMap(null));

    // 建立新標記
    const newMarkers = trafficData.map(station => {
      const marker = new google.maps.Marker({
        position: { lat: station.lat, lng: station.lng },
        map,
        title: station.name,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: getStatusColor(station.status),
          fillOpacity: 0.8,
          strokeColor: '#ffffff',
          strokeWeight: 2,
        },
      });

      // 資訊窗口
      const infoWindow = new google.maps.InfoWindow({
        content: createInfoWindowContent(station),
      });

      marker.addListener('click', () => {
        infoWindow.open(map, marker);
      });

      return marker;
    });

    setMarkers(newMarkers);
  }, [map, trafficData]);

  // 更新衝擊波覆蓋層
  useEffect(() => {
    if (!map || !showShockwaveOverlay) return;

    // 清除現有覆蓋層
    shockwaveOverlays.forEach(overlay => overlay.setMap(null));

    // 建立新覆蓋層
    const newOverlays = shockwaves.map(shockwave => {
      const circle = new google.maps.Circle({
        strokeColor: '#FF0000',
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillColor: '#FF0000',
        fillOpacity: 0.2,
        map,
        center: { lat: shockwave.lat, lng: shockwave.lng },
        radius: shockwave.affectedArea * 1000, // 轉換為公尺
      });

      return circle;
    });

    setShockwaveOverlays(newOverlays);
  }, [map, shockwaves, showShockwaveOverlay]);

  // 工具函數
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'normal': return '#4CAF50';
      case 'congested': return '#FF9800';
      case 'blocked': return '#F44336';
      default: return '#9E9E9E';
    }
  };

  const createInfoWindowContent = (station: TrafficData): string => {
    return `
      <div style="padding: 10px; min-width: 200px;">
        <h3 style="margin: 0 0 10px 0; color: #333;">${station.name}</h3>
        <div style="margin-bottom: 5px;">
          <strong>車流量:</strong> ${station.flow.toFixed(0)} 車/小時
        </div>
        <div style="margin-bottom: 5px;">
          <strong>車速:</strong> ${station.speed.toFixed(1)} km/h
        </div>
        <div style="margin-bottom: 5px;">
          <strong>狀態:</strong> 
          <span style="color: ${getStatusColor(station.status)}; font-weight: bold;">
            ${getStatusText(station.status)}
          </span>
        </div>
        <div style="font-size: 12px; color: #666; margin-top: 10px;">
          位置: ${station.lat.toFixed(6)}, ${station.lng.toFixed(6)}
        </div>
      </div>
    `;
  };

  const getStatusText = (status: string): string => {
    switch (status) {
      case 'normal': return '順暢';
      case 'congested': return '壅塞';
      case 'blocked': return '阻塞';
      default: return '未知';
    }
  };

  // 公開方法
  const fitBounds = useCallback((bounds: google.maps.LatLngBounds) => {
    if (map) {
      map.fitBounds(bounds);
    }
  }, [map]);

  const panTo = useCallback((lat: number, lng: number) => {
    if (map) {
      map.panTo({ lat, lng });
    }
  }, [map]);

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">載入地圖中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full" />
      
      {/* 地圖控制面板 */}
      <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-2">
        <div className="flex flex-col space-y-2">
          <button
            onClick={() => {
              if (trafficLayer) {
                const isVisible = trafficLayer.getMap() !== null;
                trafficLayer.setMap(isVisible ? null : map);
              }
            }}
            className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            交通狀況
          </button>
          
          <button
            onClick={() => {
              // 取得用戶位置
              if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                  (position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    panTo(lat, lng);
                    onLocationUpdate?.(lat, lng);
                  },
                  (error) => {
                    console.error('無法取得位置:', error);
                  }
                );
              }
            }}
            className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600"
          >
            我的位置
          </button>
        </div>
      </div>

      {/* 圖例 */}
      <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-3">
        <h4 className="font-semibold mb-2 text-sm">圖例</h4>
        <div className="space-y-1 text-xs">
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
            <span>順暢</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-orange-500 mr-2"></div>
            <span>壅塞</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-red-500 mr-2"></div>
            <span>阻塞</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TrafficMap;