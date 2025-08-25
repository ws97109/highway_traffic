'use client';

import React, { useState, useEffect } from 'react';
import { CheckCircleIcon, ExclamationTriangleIcon, XCircleIcon } from '@heroicons/react/24/outline';

interface APIEndpointStatus {
  name: string;
  endpoint: string;
  status: 'success' | 'warning' | 'error';
  responseTime?: number;
  data?: any;
  error?: string;
}

const DataConnectionStatus: React.FC = () => {
  const [apiStatuses, setApiStatuses] = useState<APIEndpointStatus[]>([]);
  const [isVisible, setIsVisible] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const endpoints = [
    { name: '交通資料', endpoint: '/api/traffic/current' },
    { name: '震波資料', endpoint: '/api/shockwave/active' },
    { name: '預測資料', endpoint: '/api/prediction/traffic' },
    { name: 'RAG狀態', endpoint: '/api/smart/rag-status' },
  ];

  const checkAPIStatus = async () => {
    setIsLoading(true);
    const results: APIEndpointStatus[] = [];

    for (const endpoint of endpoints) {
      const startTime = Date.now();
      try {
        const response = await fetch(endpoint.endpoint, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          // 添加超時控制
          signal: AbortSignal.timeout(10000)
        });

        const responseTime = Date.now() - startTime;
        
        if (response.ok) {
          const data = await response.json();
          results.push({
            name: endpoint.name,
            endpoint: endpoint.endpoint,
            status: 'success',
            responseTime,
            data
          });
        } else {
          results.push({
            name: endpoint.name,
            endpoint: endpoint.endpoint,
            status: 'error',
            responseTime,
            error: `HTTP ${response.status}: ${response.statusText}`
          });
        }
      } catch (error: any) {
        const responseTime = Date.now() - startTime;
        results.push({
          name: endpoint.name,
          endpoint: endpoint.endpoint,
          status: 'error',
          responseTime,
          error: error.message || '連接失敗'
        });
      }
    }

    setApiStatuses(results);
    setIsLoading(false);
  };

  // 組件載入時自動檢查一次
  useEffect(() => {
    if (isVisible) {
      checkAPIStatus();
    }
  }, [isVisible]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="w-5 h-5 text-green-600" />;
      case 'warning':
        return <ExclamationTriangleIcon className="w-5 h-5 text-yellow-600" />;
      case 'error':
        return <XCircleIcon className="w-5 h-5 text-red-600" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'border-green-200 bg-green-50';
      case 'warning':
        return 'border-yellow-200 bg-yellow-50';
      case 'error':
        return 'border-red-200 bg-red-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="fixed bottom-4 left-4 bg-blue-600 text-white px-3 py-2 rounded-lg text-xs hover:bg-blue-700 transition-colors z-50"
        title="檢查API連接狀態"
      >
        📊 API狀態
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 left-4 bg-white rounded-xl shadow-xl border border-gray-200 p-4 max-w-md z-50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">API 連接狀態</h3>
        <div className="flex space-x-2">
          <button
            onClick={checkAPIStatus}
            disabled={isLoading}
            className="bg-blue-600 text-white px-3 py-1 rounded text-xs hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? '檢查中...' : '重新檢查'}
          </button>
          <button
            onClick={() => setIsVisible(false)}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {apiStatuses.length === 0 ? (
          <div className="text-center py-4 text-gray-500">
            點擊「重新檢查」開始診斷
          </div>
        ) : (
          apiStatuses.map((api, index) => (
            <div
              key={index}
              className={`border rounded-lg p-3 ${getStatusColor(api.status)}`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(api.status)}
                  <span className="font-medium text-sm">{api.name}</span>
                </div>
                {api.responseTime && (
                  <span className="text-xs text-gray-500">
                    {api.responseTime}ms
                  </span>
                )}
              </div>
              
              <div className="text-xs text-gray-600 mb-2">
                <code className="bg-gray-100 px-1 rounded">{api.endpoint}</code>
              </div>

              {api.error && (
                <div className="text-xs text-red-600 bg-red-100 p-2 rounded">
                  <strong>錯誤:</strong> {api.error}
                </div>
              )}

              {api.data && api.status === 'success' && (
                <div className="text-xs text-green-700 bg-green-100 p-2 rounded">
                  <strong>成功:</strong> 
                  {api.endpoint.includes('traffic') && api.data.stations && 
                    ` 載入 ${api.data.stations.length} 個交通站點`}
                  {api.endpoint.includes('shockwave') && api.data.shockwaves && 
                    ` 發現 ${api.data.shockwaves.length} 個震波事件`}
                  {api.endpoint.includes('prediction') && api.data.predictions && 
                    ` 載入 ${api.data.predictions.length} 個預測資料`}
                  {api.endpoint.includes('rag-status') && api.data.system_health && 
                    ` RAG系統: ${api.data.system_health}`}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-gray-200">
        <div className="text-xs text-gray-500">
          <p>💡 提示: 如果看到錯誤，請確認:</p>
          <p>1. 後端 API 服務是否在 http://localhost:8000 運行</p>
          <p>2. 前端是否在 http://localhost:3000 運行</p>
          <p>3. 防火牆是否允許連接</p>
        </div>
      </div>
    </div>
  );
};

export default DataConnectionStatus;