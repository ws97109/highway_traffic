'use client';

import React, { useState, useEffect } from 'react';
import { ExclamationTriangleIcon, ClockIcon, MapPinIcon, XMarkIcon } from '@heroicons/react/24/outline';

interface ShockwaveAlertProps {
  shockwave: ShockwaveData;
  userLocation?: { lat: number; lng: number };
  onDismiss: () => void;
  onViewDetails: (shockwave: ShockwaveData) => void;
  onGetAlternativeRoute: (shockwave: ShockwaveData) => void;
}

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

const ShockwaveAlert: React.FC<ShockwaveAlertProps> = ({
  shockwave,
  userLocation,
  onDismiss,
  onViewDetails,
  onGetAlternativeRoute
}) => {
  const [timeToArrival, setTimeToArrival] = useState<number>(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [countdown, setCountdown] = useState<string>('');

  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date();
      const arrival = new Date(shockwave.estimatedArrivalTime);
      const diff = arrival.getTime() - now.getTime();
      
      if (diff > 0) {
        const minutes = Math.floor(diff / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);
        setTimeToArrival(minutes);
        setCountdown(`${minutes}分${seconds}秒`);
      } else {
        setTimeToArrival(0);
        setCountdown('已到達');
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [shockwave.estimatedArrivalTime]);

  const getSeverityConfig = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          bgColor: 'bg-red-100 border-red-500',
          textColor: 'text-red-800',
          iconColor: 'text-red-600',
          pulseColor: 'animate-pulse',
          title: '🚨 緊急震波警報'
        };
      case 'high':
        return {
          bgColor: 'bg-orange-100 border-orange-500',
          textColor: 'text-orange-800',
          iconColor: 'text-orange-600',
          pulseColor: 'animate-pulse',
          title: '⚠️ 高風險震波警報'
        };
      case 'medium':
        return {
          bgColor: 'bg-yellow-100 border-yellow-500',
          textColor: 'text-yellow-800',
          iconColor: 'text-yellow-600',
          pulseColor: '',
          title: '⚡ 中度震波警報'
        };
      default:
        return {
          bgColor: 'bg-blue-100 border-blue-500',
          textColor: 'text-blue-800',
          iconColor: 'text-blue-600',
          pulseColor: '',
          title: '📍 震波提醒'
        };
    }
  };

  const config = getSeverityConfig(shockwave.severity);

  const calculateDistance = () => {
    if (!userLocation) return null;
    
    const R = 6371; // 地球半徑 (km)
    const dLat = (shockwave.lat - userLocation.lat) * Math.PI / 180;
    const dLon = (shockwave.lng - userLocation.lng) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(userLocation.lat * Math.PI / 180) * Math.cos(shockwave.lat * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const distance = R * c;
    
    return distance.toFixed(1);
  };

  const distance = calculateDistance();

  return (
    <div className={`border-l-4 rounded-lg shadow-lg ${config.bgColor} ${config.pulseColor}`}>
      {/* 主要警報內容 */}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <ExclamationTriangleIcon className={`w-6 h-6 ${config.iconColor} mt-1`} />
            
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <h3 className={`font-bold text-lg ${config.textColor}`}>
                  {config.title}
                </h3>
                <button
                  onClick={onDismiss}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>
              
              <div className={`text-sm ${config.textColor} mb-3`}>
                <div className="flex items-center mb-1">
                  <MapPinIcon className="w-4 h-4 mr-1" />
                  <span className="font-medium">{shockwave.location}</span>
                  {distance && (
                    <span className="ml-2 text-xs bg-white bg-opacity-50 px-2 py-1 rounded">
                      距離 {distance} km
                    </span>
                  )}
                </div>
                <p>{shockwave.description}</p>
              </div>

              {/* 倒數計時 */}
              <div className="flex items-center space-x-4 mb-3">
                <div className={`flex items-center ${config.textColor}`}>
                  <ClockIcon className="w-4 h-4 mr-1" />
                  <span className="font-bold text-lg">{countdown}</span>
                  <span className="text-sm ml-1">後到達</span>
                </div>
                
                <div className="text-sm">
                  <span className="font-medium">強度:</span>
                  <span className="ml-1">{shockwave.intensity}/10</span>
                </div>
                
                <div className="text-sm">
                  <span className="font-medium">傳播速度:</span>
                  <span className="ml-1">{shockwave.propagationSpeed} km/h</span>
                </div>
              </div>

              {/* 快速行動按鈕 */}
              <div className="flex space-x-2">
                <button
                  onClick={() => onGetAlternativeRoute(shockwave)}
                  className="bg-white bg-opacity-80 hover:bg-opacity-100 px-3 py-1 rounded text-sm font-medium transition-all"
                >
                  🛣️ 替代路線
                </button>
                
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="bg-white bg-opacity-80 hover:bg-opacity-100 px-3 py-1 rounded text-sm font-medium transition-all"
                >
                  {isExpanded ? '收起' : '詳細資訊'}
                </button>
                
                <button
                  onClick={() => onViewDetails(shockwave)}
                  className="bg-white bg-opacity-80 hover:bg-opacity-100 px-3 py-1 rounded text-sm font-medium transition-all"
                >
                  📍 地圖定位
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 展開的詳細資訊 */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-white border-opacity-30">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* 建議行動 */}
              <div>
                <h4 className={`font-semibold ${config.textColor} mb-2`}>建議行動:</h4>
                <ul className="space-y-1">
                  {shockwave.recommendations.map((rec, index) => (
                    <li key={index} className={`text-sm ${config.textColor} flex items-start`}>
                      <span className="mr-2">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 替代路線 */}
              {shockwave.alternativeRoutes && shockwave.alternativeRoutes.length > 0 && (
                <div>
                  <h4 className={`font-semibold ${config.textColor} mb-2`}>替代路線:</h4>
                  <div className="space-y-2">
                    {shockwave.alternativeRoutes.map((route) => (
                      <div key={route.id} className="bg-white bg-opacity-50 p-2 rounded text-sm">
                        <div className="font-medium">{route.name}</div>
                        <div className="text-xs">
                          額外時間: +{route.additionalTime}分鐘 | 
                          成功率: {route.avoidanceSuccess}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* 技術資訊 */}
            <div className="mt-4 pt-3 border-t border-white border-opacity-30">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="font-medium">影響範圍:</span>
                  <div>{shockwave.affectedArea} km²</div>
                </div>
                <div>
                  <span className="font-medium">預計到達:</span>
                  <div>{new Date(shockwave.estimatedArrivalTime).toLocaleTimeString('zh-TW')}</div>
                </div>
                <div>
                  <span className="font-medium">震波ID:</span>
                  <div className="font-mono text-xs">{shockwave.id.slice(0, 8)}</div>
                </div>
                <div>
                  <span className="font-medium">更新時間:</span>
                  <div>{new Date().toLocaleTimeString('zh-TW')}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 緊急情況的額外視覺提示 */}
      {shockwave.severity === 'critical' && (
        <div className="bg-red-600 text-white px-4 py-2 text-center font-bold text-sm">
          ⚠️ 建議立即尋找最近出口或停車區域 ⚠️
        </div>
      )}
    </div>
  );
};

export default ShockwaveAlert;
