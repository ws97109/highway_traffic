'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import RadarWave from './RadarWave2';

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
  severity?: 'low' | 'medium' | 'high' | 'critical';
  description?: string;
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
  const [radarWaves, setRadarWaves] = useState<{ id: string; component: React.ReactElement }[]>([]);

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

  // 更新衝擊波覆蓋層 - 使用真正的雷達式水波效果
  useEffect(() => {
    if (!map || !showShockwaveOverlay) {
      // 清理現有的雷達波
      setRadarWaves([]);
      return;
    }

    // 清除現有覆蓋層
    shockwaveOverlays.forEach(overlay => overlay.setMap(null));

    // 建立新覆蓋層和雷達波
    const newOverlays: google.maps.Circle[] = [];
    const newRadarWaves: { id: string; component: React.ReactElement }[] = [];
    
    shockwaves.forEach(shockwave => {
      // 驗證座標是否在有效範圍內（台灣地區）
      if (!isValidCoordinate(shockwave.lat, shockwave.lng)) {
        console.warn(`無效的衝擊波座標: ${shockwave.lat}, ${shockwave.lng}`);
        return;
      }

      const { color, opacity, strokeWeight } = getShockwaveStyle(shockwave);
      const radius = calculateShockwaveRadius(shockwave);
      const severity = shockwave.severity || determineSeverityFromIntensity(shockwave.intensity);

      // 添加中心點標記
      const centerMarker = new google.maps.Marker({
        position: { lat: shockwave.lat, lng: shockwave.lng },
        map,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 6,
          fillColor: color,
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2,
        },
        title: `衝擊波中心 - 強度: ${shockwave.intensity}`,
        zIndex: 1000
      });

      // 添加點擊事件顯示詳細資訊
      centerMarker.addListener('click', () => {
        try {
          // 安全檢查
          if (!map || !shockwave) {
            console.error('地圖或衝擊波資料遺失');
            return;
          }

          const content = createShockwaveInfoContent(shockwave);
          
          const infoWindow = new google.maps.InfoWindow({
            content: content,
            position: { 
              lat: shockwave.lat || 0, 
              lng: shockwave.lng || 0 
            },
            maxWidth: 420,
          });
          
          infoWindow.open(map);

          // 等待 InfoWindow 完全載入後再載入 AI 推薦
          google.maps.event.addListenerOnce(infoWindow, 'domready', () => {
            loadAIRecommendation(shockwave);
          });

        } catch (error) {
          console.error('開啟衝擊波資訊視窗時發生錯誤:', error);
          
          // 顯示錯誤提示
          const errorInfoWindow = new google.maps.InfoWindow({
            content: `
              <div style="padding: 16px; text-align: center; color: #666;">
                <div style="margin-bottom: 8px;">⚠️</div>
                <div>載入衝擊波資訊時發生錯誤</div>
                <div style="font-size: 12px; margin-top: 8px; color: #999;">請稍後再試或聯繫系統管理員</div>
              </div>
            `,
            position: { 
              lat: shockwave?.lat || 0, 
              lng: shockwave?.lng || 0 
            },
          });
          errorInfoWindow.open(map);
        }
      });

      // 創建雷達波組件
      const radarWave = (
        <RadarWave
          key={shockwave.id}
          lat={shockwave.lat}
          lng={shockwave.lng}
          map={map}
          severity={severity}
          intensity={shockwave.intensity}
          radius={radius}
          onRemove={() => {
            // 當雷達波被移除時的回調
            setRadarWaves(prev => prev.filter(wave => wave.id !== shockwave.id));
          }}
        />
      );

      newRadarWaves.push({
        id: shockwave.id,
        component: radarWave
      });

      // 保留一個靜態的半透明圓圈作為影響範圍指示
      const staticCircle = new google.maps.Circle({
        strokeColor: color,
        strokeOpacity: 0.3,
        strokeWeight: 1,
        fillColor: color,
        fillOpacity: 0.1,
        map,
        center: { lat: shockwave.lat, lng: shockwave.lng },
        radius: radius,
        clickable: false,
      });

      newOverlays.push(staticCircle);
    });

    setShockwaveOverlays(newOverlays);
    setRadarWaves(newRadarWaves);
  }, [map, shockwaves, showShockwaveOverlay]);

  // 驗證座標是否在台灣範圍內
  const isValidCoordinate = (lat: number, lng: number): boolean => {
    // 台灣地區的大致範圍
    const taiwanBounds = {
      north: 25.3,
      south: 21.9,
      east: 122.0,
      west: 119.3
    };
    
    return lat >= taiwanBounds.south && lat <= taiwanBounds.north &&
           lng >= taiwanBounds.west && lng <= taiwanBounds.east;
  };

  // 根據衝擊波嚴重程度獲取樣式
  const getShockwaveStyle = (shockwave: ShockwaveData) => {
    const severity = shockwave.severity || determineSeverityFromIntensity(shockwave.intensity);
    
    switch (severity) {
      case 'critical':
        return {
          color: '#DC2626', // 深紅色
          opacity: 0.9,
          strokeWeight: 4
        };
      case 'high':
        return {
          color: '#EF4444', // 紅色
          opacity: 0.8,
          strokeWeight: 3
        };
      case 'medium':
        return {
          color: '#F59E0B', // 橙色
          opacity: 0.7,
          strokeWeight: 2
        };
      case 'low':
      default:
        return {
          color: '#10B981', // 綠色
          opacity: 0.6,
          strokeWeight: 2
        };
    }
  };

  // 根據強度判斷嚴重程度
  const determineSeverityFromIntensity = (intensity: number): 'low' | 'medium' | 'high' | 'critical' => {
    if (intensity >= 8) return 'critical';
    if (intensity >= 6) return 'high';
    if (intensity >= 4) return 'medium';
    return 'low';
  };

  // 計算衝擊波半徑 - 調整為更明顯的大小
  const calculateShockwaveRadius = (shockwave: ShockwaveData): number => {
    // 基礎半徑：增加顯示範圍讓衝擊波更明顯
    const baseRadius = Math.min(shockwave.affectedArea * 400, 2000); // 最大2km顯示
    
    // 根據強度調整大小
    const intensityMultiplier = 0.8 + (shockwave.intensity / 10) * 0.4;
    
    // 最終半徑，確保足夠明顯
    return Math.max(baseRadius * intensityMultiplier, 300); // 最小300m
  };

  // 計算衝擊波持續時間
  const calculateDuration = (shockwave: ShockwaveData): string => {
    if (!shockwave.estimatedArrival) return '未知';
    
    const now = new Date();
    const arrival = new Date(shockwave.estimatedArrival);
    const diffMinutes = Math.max(0, Math.floor((arrival.getTime() - now.getTime()) / 60000));
    
    if (diffMinutes < 60) {
      return `${diffMinutes} 分鐘`;
    } else {
      const hours = Math.floor(diffMinutes / 60);
      const minutes = diffMinutes % 60;
      return `${hours} 小時 ${minutes} 分鐘`;
    }
  };

  // 計算衝擊波半徑（用於顯示）
  const getDisplayRadius = (shockwave: ShockwaveData): string => {
    if (!shockwave.affectedArea || shockwave.affectedArea <= 0) {
      return '未知';
    }
    
    const radiusKm = shockwave.affectedArea;
    if (radiusKm < 1) {
      return `${(radiusKm * 1000).toFixed(0)} 公尺`;
    } else {
      return `${radiusKm.toFixed(1)} 公里`;
    }
  };

  // 創建衝擊波資訊窗口內容
  const createShockwaveInfoContent = (shockwave: ShockwaveData): string => {
    try {
      // 安全檢查
      if (!shockwave) {
        return '<div style="padding: 12px; color: #666;">無法載入衝擊波資訊</div>';
      }

      const severity = shockwave.severity || determineSeverityFromIntensity(shockwave.intensity || 0);
      const severityText = {
        'critical': '極危險',
        'high': '高危險',
        'medium': '中等',
        'low': '輕微'
      }[severity] || '未知';

      const severityColor = getShockwaveStyle(shockwave).color;
      const duration = calculateDuration(shockwave);
      const displayRadius = getDisplayRadius(shockwave);

      return `
        <div style="padding: 16px; min-width: 320px; max-width: 400px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.4;">
          <div style="display: flex; align-items: center; margin-bottom: 16px; border-bottom: 2px solid ${severityColor}; padding-bottom: 8px;">
            <span style="font-size: 20px; margin-right: 8px;">🌊</span>
            <h3 style="margin: 0; color: #333; font-size: 18px; font-weight: 600;">交通衝擊波警報</h3>
          </div>
          
          <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-weight: 600; color: #555;">嚴重程度</span>
              <span style="color: ${severityColor}; font-weight: bold; padding: 4px 8px; background: ${severityColor}15; border-radius: 6px; border: 1px solid ${severityColor}40;">
                ${severityText}
              </span>
            </div>
          </div>

          <div style="background: #f8f9fa; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 14px;">
              <div>
                <span style="color: #666; display: block;">強度指數</span>
                <span style="font-weight: 600; color: #333;">${(shockwave.intensity || 0).toFixed(2)}</span>
              </div>
              <div>
                <span style="color: #666; display: block;">持續時間</span>
                <span style="font-weight: 600; color: #333;">${duration}</span>
              </div>
              <div>
                <span style="color: #666; display: block;">影響半徑</span>
                <span style="font-weight: 600; color: #333;">${displayRadius}</span>
              </div>
              <div>
                <span style="color: #666; display: block;">傳播速度</span>
                <span style="font-weight: 600; color: #333;">${(shockwave.propagationSpeed || 0).toFixed(1)} km/h</span>
              </div>
            </div>
          </div>

          <div style="margin-bottom: 12px; font-size: 14px;">
            <div style="color: #666; margin-bottom: 4px;">位置座標</div>
            <div style="font-family: monospace; background: #f1f3f4; padding: 6px 8px; border-radius: 4px; font-size: 13px;">
              ${(shockwave.lat || 0).toFixed(6)}, ${(shockwave.lng || 0).toFixed(6)}
            </div>
          </div>

          ${shockwave.estimatedArrival ? `
            <div style="margin-bottom: 12px; font-size: 14px;">
              <div style="color: #666; margin-bottom: 4px;">預估到達時間</div>
              <div style="font-weight: 600; color: #d73527;">
                ${new Date(shockwave.estimatedArrival).toLocaleString('zh-TW', {
                  year: 'numeric',
                  month: '2-digit', 
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </div>
            </div>
          ` : ''}

          ${shockwave.description ? `
            <div style="margin-bottom: 16px; padding: 10px; background: #e3f2fd; border-left: 4px solid #2196f3; border-radius: 4px; font-size: 13px; color: #1565c0;">
              <div style="font-weight: 600; margin-bottom: 4px;">詳細描述</div>
              ${shockwave.description}
            </div>
          ` : ''}

          <!-- AI 推薦區域 -->
          <div style="margin-top: 16px; padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; color: white;">
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
              <span style="font-size: 16px; margin-right: 6px;">🤖</span>
              <span style="font-weight: 600; font-size: 14px;">AI 智能建議</span>
            </div>
            <div id="ai-recommendation-${shockwave.id}" style="font-size: 13px; line-height: 1.4; min-height: 40px;">
              <div style="color: rgba(255,255,255,0.8);">正在分析當前交通狀況...</div>
            </div>
          </div>
        </div>
      `;
    } catch (error) {
      console.error('創建衝擊波資訊內容時發生錯誤:', error);
      return `
        <div style="padding: 16px; color: #666; text-align: center;">
          <div style="margin-bottom: 8px;">⚠️</div>
          <div>載入衝擊波資訊時發生錯誤</div>
        </div>
      `;
    }
  };

  // 載入 AI 推薦內容
  const loadAIRecommendation = async (shockwave: ShockwaveData): Promise<void> => {
    try {
      const recommendationElement = document.getElementById(`ai-recommendation-${shockwave.id}`);
      if (!recommendationElement) {
        console.warn('找不到 AI 推薦容器元素');
        return;
      }

      // 顯示載入中狀態
      recommendationElement.innerHTML = `
        <div style="display: flex; align-items: center; color: rgba(255,255,255,0.8);">
          <div style="margin-right: 8px;">⏳</div>
          <div>AI 正在分析中...</div>
        </div>
      `;

      // 模擬 API 調用 - 這裡你可以替換為實際的 API 調用
      // 根據衝擊波數據生成建議
      await new Promise(resolve => setTimeout(resolve, 1500)); // 模擬網路延遲

      const recommendations = generateAIRecommendations(shockwave);
      
      recommendationElement.innerHTML = `
        <div style="line-height: 1.5;">
          ${recommendations.map(rec => `
            <div style="margin-bottom: 8px; display: flex; align-items: flex-start;">
              <span style="margin-right: 6px; font-size: 12px;">${rec.icon}</span>
              <span style="font-size: 13px;">${rec.text}</span>
            </div>
          `).join('')}
        </div>
      `;

    } catch (error) {
      console.error('載入 AI 推薦時發生錯誤:', error);
      const recommendationElement = document.getElementById(`ai-recommendation-${shockwave.id}`);
      if (recommendationElement) {
        recommendationElement.innerHTML = `
          <div style="color: rgba(255,255,255,0.7); font-size: 13px;">
            暫時無法載入 AI 建議，請稍後再試
          </div>
        `;
      }
    }
  };

  // 根據衝擊波數據生成 AI 推薦
  const generateAIRecommendations = (shockwave: ShockwaveData): Array<{icon: string, text: string}> => {
    const recommendations = [];
    const severity = shockwave.severity || determineSeverityFromIntensity(shockwave.intensity || 0);
    const intensityLevel = shockwave.intensity || 0;

    // 根據嚴重程度提供建議
    if (severity === 'critical' || intensityLevel > 0.8) {
      recommendations.push({
        icon: '🚨',
        text: '建議立即避開此區域，尋找替代路線'
      });
      recommendations.push({
        icon: '⏰',
        text: '預估需額外 15-30 分鐘通行時間'
      });
    } else if (severity === 'high' || intensityLevel > 0.6) {
      recommendations.push({
        icon: '⚠️',
        text: '建議減速慢行，保持安全距離'
      });
      recommendations.push({
        icon: '🛣️',
        text: '可考慮使用平行道路或替代路線'
      });
    } else if (severity === 'medium' || intensityLevel > 0.4) {
      recommendations.push({
        icon: '💡',
        text: '注意前方交通狀況，準備減速'
      });
      recommendations.push({
        icon: '📱',
        text: '建議開啟導航避塞功能'
      });
    } else {
      recommendations.push({
        icon: '✅',
        text: '影響較輕，正常通行即可'
      });
      recommendations.push({
        icon: '👀',
        text: '持續關注交通狀況變化'
      });
    }

    // 根據傳播速度提供建議
    const propagationSpeed = shockwave.propagationSpeed || 0;
    if (propagationSpeed > 50) {
      recommendations.push({
        icon: '⚡',
        text: '衝擊波傳播迅速，盡快通過或迴避'
      });
    } else if (propagationSpeed > 20) {
      recommendations.push({
        icon: '🕐',
        text: '有足夠時間調整路線或準備應對'
      });
    }

    // 根據影響範圍提供建議
    const affectedArea = shockwave.affectedArea || 0;
    if (affectedArea > 2) {
      recommendations.push({
        icon: '🗺️',
        text: '影響範圍較大，建議使用長程替代路線'
      });
    }

    return recommendations;
  };

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
          <div className="mb-2">
            <div className="text-xs font-medium text-gray-600 mb-1">交通狀況</div>
            <div className="flex items-center mb-1">
              <div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div>
              <span>順暢</span>
            </div>
            <div className="flex items-center mb-1">
              <div className="w-3 h-3 rounded-full bg-orange-500 mr-2"></div>
              <span>壅塞</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 rounded-full bg-red-500 mr-2"></div>
              <span>阻塞</span>
            </div>
          </div>
          
          {showShockwaveOverlay && (
            <div className="border-t pt-2">
              <div className="text-xs font-medium text-gray-600 mb-1">衝擊波嚴重程度</div>
              <div className="flex items-center mb-1">
                <div className="w-3 h-3 rounded-full bg-green-500 mr-2 opacity-60"></div>
                <span>輕微</span>
              </div>
              <div className="flex items-center mb-1">
                <div className="w-3 h-3 rounded-full bg-yellow-500 mr-2 opacity-70"></div>
                <span>中等</span>
              </div>
              <div className="flex items-center mb-1">
                <div className="w-3 h-3 rounded-full bg-red-500 mr-2 opacity-80"></div>
                <span>高危險</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-red-700 mr-2 opacity-90"></div>
                <span>極危險</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 渲染雷達波組件 */}
      {radarWaves.map(wave => wave.component)}
    </div>
  );
};

export default TrafficMap;
