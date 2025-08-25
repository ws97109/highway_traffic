'use client';

import React, { useState, useEffect } from 'react';
import { ClockIcon, CalendarIcon, MapIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface DepartureTimeOptimizerProps {
  origin: { lat: number; lng: number; address: string };
  destination: { lat: number; lng: number; address: string };
  preferredArrivalTime?: Date;
  onOptimalTimeSelected: (departureTime: Date, route: any) => void;
}

interface TimeSlot {
  departureTime: Date;
  arrivalTime: Date;
  duration: number;
  trafficScore: number;
  shockwaveRisk: 'low' | 'medium' | 'high';
  fuelConsumption: number;
  recommendation: string;
}

const DepartureTimeOptimizer: React.FC<DepartureTimeOptimizerProps> = ({
  origin,
  destination,
  preferredArrivalTime,
  onOptimalTimeSelected
}) => {
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
  const [analysisRange, setAnalysisRange] = useState(2); // 分析前後2小時

  useEffect(() => {
    if (origin && destination) {
      analyzeOptimalDepartureTimes();
    }
  }, [origin, destination, preferredArrivalTime]);

  const analyzeOptimalDepartureTimes = async () => {
    setLoading(true);
    try {
      // 呼叫後端API進行智慧分析
      const response = await fetch('/api/smart/departure-optimizer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin,
          destination,
          preferredArrivalTime,
          analysisRange,
          includeShockwavePrediction: true,
          includeTrafficPrediction: true
        })
      });

      const data = await response.json();
      setTimeSlots(data.timeSlots);
      
      // 自動選擇最佳時段
      const optimal = data.timeSlots.find((slot: TimeSlot) => slot.recommendation === 'optimal');
      if (optimal) {
        setSelectedSlot(optimal);
      }
    } catch (error) {
      console.error('分析最佳出發時間失敗:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'high': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getRecommendationIcon = (recommendation: string) => {
    switch (recommendation) {
      case 'optimal': return '⭐';
      case 'good': return '👍';
      case 'avoid': return '⚠️';
      default: return '📍';
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-TW', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}小時${mins}分鐘` : `${mins}分鐘`;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
          <span className="text-gray-600">分析最佳出發時間中...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center">
          <ClockIcon className="w-5 h-5 mr-2 text-blue-600" />
          智慧出發時間建議
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          基於AI預測和震波分析，為您推薦最佳出發時間
        </p>
      </div>

      <div className="p-6">
        {/* 路線資訊 */}
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center text-sm text-gray-600 mb-2">
            <MapIcon className="w-4 h-4 mr-2" />
            <span>路線規劃</span>
          </div>
          <div className="text-sm">
            <div className="mb-1">
              <span className="font-medium">起點:</span> {origin.address}
            </div>
            <div>
              <span className="font-medium">終點:</span> {destination.address}
            </div>
          </div>
        </div>

        {/* 時間選項 */}
        <div className="space-y-3">
          {timeSlots.map((slot, index) => (
            <div
              key={index}
              className={`border rounded-lg p-4 cursor-pointer transition-all ${
                selectedSlot === slot 
                  ? 'border-blue-500 bg-blue-50' 
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setSelectedSlot(slot)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-lg">
                    {getRecommendationIcon(slot.recommendation)}
                  </span>
                  <div>
                    <div className="font-medium text-gray-900">
                      {formatTime(slot.departureTime)} 出發
                    </div>
                    <div className="text-sm text-gray-600">
                      預計 {formatTime(slot.arrivalTime)} 抵達
                    </div>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className="font-medium text-gray-900">
                    {formatDuration(slot.duration)}
                  </div>
                  <div className={`text-xs px-2 py-1 rounded-full ${getRiskColor(slot.shockwaveRisk)}`}>
                    震波風險: {slot.shockwaveRisk}
                  </div>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">交通評分:</span>
                  <span className="ml-2 font-medium">
                    {slot.trafficScore}/100
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">預估油耗:</span>
                  <span className="ml-2 font-medium">
                    {slot.fuelConsumption.toFixed(1)}L
                  </span>
                </div>
              </div>

              {slot.recommendation === 'optimal' && (
                <div className="mt-2 text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                  ⭐ AI推薦最佳時段
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 確認按鈕 */}
        {selectedSlot && (
          <div className="mt-6 pt-4 border-t border-gray-200">
            <button
              onClick={() => onOptimalTimeSelected(selectedSlot.departureTime, selectedSlot)}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              選擇此時間出發
            </button>
          </div>
        )}

        {/* 設定選項 */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">分析時間範圍</span>
            <select
              value={analysisRange}
              onChange={(e) => setAnalysisRange(Number(e.target.value))}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              <option value={1}>前後1小時</option>
              <option value={2}>前後2小時</option>
              <option value={3}>前後3小時</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DepartureTimeOptimizer;
