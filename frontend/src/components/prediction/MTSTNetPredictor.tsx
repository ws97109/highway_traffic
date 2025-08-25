import React, { useState, useEffect } from 'react';
import { 
  ChartBarIcon, 
  CpuChipIcon, 
  ClockIcon, 
  SignalIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon
} from '@heroicons/react/24/outline';

interface PredictionData {
  station_id: string;
  location_name: string;
  predicted_flow: number;
  predicted_speed: number;
  confidence: number;
  time_horizon: number;
  timestamp: string;
  highway?: string;
  direction?: string;
}

interface MTSTNetPrediction {
  predictions: PredictionData[];
  model_version: string;
  generated_at: string;
  time_horizon: number;
  total_stations: number;
  data_source: string;
}

interface ModelStatus {
  model_name: string;
  version: string;
  status: string;
  is_running: boolean;
  last_prediction_time?: string;
  prediction_interval_minutes: number;
  target_stations_count: number;
  cached_predictions_count: number;
  data_collector_available: boolean;
  parameters: {
    input_window: number;
    output_window: number;
    hidden_dim: number;
    num_heads: number;
    num_blocks: number;
    site_num: number;
  };
  data_source: string;
  model_type: string;
  features: string[];
}

const MTSTNetPredictor: React.FC = () => {
  const [predictions, setPredictions] = useState<MTSTNetPrediction | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [selectedView, setSelectedView] = useState<'predictions' | 'status'>('predictions');

  // 取得預測資料
  const fetchPredictions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/prediction/traffic');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setPredictions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '取得預測資料失敗');
      console.error('取得預測資料失敗:', err);
    } finally {
      setLoading(false);
    }
  };

  // 取得模型狀態
  const fetchModelStatus = async () => {
    try {
      const response = await fetch('/api/prediction/model/status');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setModelStatus(data);
    } catch (err) {
      console.error('取得模型狀態失敗:', err);
    }
  };

  // 初始載入
  useEffect(() => {
    fetchPredictions();
    fetchModelStatus();
  }, []);

  // 自動刷新
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchPredictions();
      if (selectedView === 'status') {
        fetchModelStatus();
      }
    }, 30000); // 30秒刷新一次

    return () => clearInterval(interval);
  }, [autoRefresh, selectedView]);

  // 格式化時間
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 取得信心度顏色
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-50';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  // 取得速度趨勢圖示
  const getSpeedTrendIcon = (speed: number) => {
    if (speed >= 70) return <ArrowTrendingUpIcon className="w-4 h-4 text-green-500" />;
    if (speed >= 40) return <SignalIcon className="w-4 h-4 text-yellow-500" />;
    return <ArrowTrendingDownIcon className="w-4 h-4 text-red-500" />;
  };

  // 取得狀態顏色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-50';
      case 'model_not_loaded': return 'text-yellow-600 bg-yellow-50';
      default: return 'text-red-600 bg-red-50';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200">
      {/* 標題列 */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <CpuChipIcon className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">MT-STNet 交通預測</h2>
              <p className="text-sm text-gray-600">時空圖神經網路即時預測系統</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* 視圖切換 */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setSelectedView('predictions')}
                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                  selectedView === 'predictions'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                預測結果
              </button>
              <button
                onClick={() => setSelectedView('status')}
                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                  selectedView === 'status'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                系統狀態
              </button>
            </div>

            {/* 自動刷新開關 */}
            <label className="flex items-center space-x-2 text-sm">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-gray-600">自動刷新</span>
            </label>

            {/* 手動刷新按鈕 */}
            <button
              onClick={() => {
                fetchPredictions();
                if (selectedView === 'status') fetchModelStatus();
              }}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '載入中...' : '刷新'}
            </button>
          </div>
        </div>
      </div>

      {/* 內容區域 */}
      <div className="p-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-3">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-500 flex-shrink-0" />
            <div>
              <p className="text-red-800 font-medium">載入失敗</p>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          </div>
        )}

        {selectedView === 'predictions' && (
          <div>
            {/* 預測資訊摘要 */}
            {predictions && (
              <div className="mb-6 grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-blue-600 text-sm font-medium">預測站點</p>
                      <p className="text-2xl font-bold text-blue-900">{predictions.total_stations}</p>
                    </div>
                    <ChartBarIcon className="w-8 h-8 text-blue-500" />
                  </div>
                </div>

                <div className="bg-green-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-green-600 text-sm font-medium">預測時間範圍</p>
                      <p className="text-2xl font-bold text-green-900">{predictions.time_horizon}分</p>
                    </div>
                    <ClockIcon className="w-8 h-8 text-green-500" />
                  </div>
                </div>

                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-purple-600 text-sm font-medium">模型版本</p>
                      <p className="text-lg font-bold text-purple-900">{predictions.model_version}</p>
                    </div>
                    <CpuChipIcon className="w-8 h-8 text-purple-500" />
                  </div>
                </div>

                <div className="bg-orange-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-orange-600 text-sm font-medium">資料來源</p>
                      <p className="text-sm font-bold text-orange-900">即時資料</p>
                    </div>
                    <SignalIcon className="w-8 h-8 text-orange-500" />
                  </div>
                </div>
              </div>
            )}

            {/* 預測結果列表 */}
            {loading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <p className="mt-2 text-gray-600">載入預測資料中...</p>
              </div>
            ) : predictions?.predictions ? (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  預測結果 ({formatTime(predictions.generated_at)})
                </h3>
                
                <div className="grid gap-4">
                  {predictions.predictions.slice(0, 10).map((pred, index) => (
                    <div key={pred.station_id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <h4 className="font-semibold text-gray-900">{pred.location_name}</h4>
                            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                              {pred.station_id}
                            </span>
                            {pred.highway && (
                              <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                                國道{pred.highway} {pred.direction === 'N' ? '北向' : '南向'}
                              </span>
                            )}
                          </div>
                          
                          <div className="grid grid-cols-3 gap-4">
                            <div className="flex items-center space-x-2">
                              <div className="flex items-center space-x-1">
                                {getSpeedTrendIcon(pred.predicted_speed)}
                                <span className="text-sm text-gray-600">速度</span>
                              </div>
                              <span className="font-bold text-lg">
                                {pred.predicted_speed.toFixed(1)} km/h
                              </span>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <span className="text-sm text-gray-600">流量</span>
                              <span className="font-bold text-lg">
                                {pred.predicted_flow.toFixed(0)} 輛/h
                              </span>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <span className="text-sm text-gray-600">信心度</span>
                              <span className={`px-2 py-1 rounded-full text-sm font-medium ${getConfidenceColor(pred.confidence)}`}>
                                {(pred.confidence * 100).toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {predictions.predictions.length > 10 && (
                  <div className="text-center py-4">
                    <p className="text-gray-600">
                      顯示前 10 個站點，共 {predictions.predictions.length} 個預測結果
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <ExclamationTriangleIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">暫無預測資料</p>
              </div>
            )}
          </div>
        )}

        {selectedView === 'status' && (
          <div>
            {modelStatus ? (
              <div className="space-y-6">
                {/* 系統狀態概覽 */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-gray-600 text-sm font-medium">模型狀態</p>
                        <span className={`inline-block px-2 py-1 rounded-full text-sm font-medium ${getStatusColor(modelStatus.status)}`}>
                          {modelStatus.status === 'active' ? '運行中' : '未載入'}
                        </span>
                      </div>
                      <CheckCircleIcon className={`w-8 h-8 ${modelStatus.status === 'active' ? 'text-green-500' : 'text-gray-400'}`} />
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-gray-600 text-sm font-medium">目標站點</p>
                        <p className="text-2xl font-bold text-gray-900">{modelStatus.target_stations_count}</p>
                      </div>
                      <SignalIcon className="w-8 h-8 text-blue-500" />
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-gray-600 text-sm font-medium">預測間隔</p>
                        <p className="text-2xl font-bold text-gray-900">{modelStatus.prediction_interval_minutes}分</p>
                      </div>
                      <ClockIcon className="w-8 h-8 text-purple-500" />
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-gray-600 text-sm font-medium">快取預測</p>
                        <p className="text-2xl font-bold text-gray-900">{modelStatus.cached_predictions_count}</p>
                      </div>
                      <ChartBarIcon className="w-8 h-8 text-green-500" />
                    </div>
                  </div>
                </div>

                {/* 模型詳細資訊 */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-gray-50 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">模型資訊</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-600">模型名稱</span>
                        <span className="font-medium">{modelStatus.model_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">版本</span>
                        <span className="font-medium">{modelStatus.version}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">類型</span>
                        <span className="font-medium text-sm">{modelStatus.model_type}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">資料來源</span>
                        <span className="font-medium text-sm">{modelStatus.data_source}</span>
                      </div>
                      {modelStatus.last_prediction_time && (
                        <div className="flex justify-between">
                          <span className="text-gray-600">最後預測</span>
                          <span className="font-medium text-sm">{formatTime(modelStatus.last_prediction_time)}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">模型參數</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-600">輸入視窗</span>
                        <span className="font-medium">{modelStatus.parameters.input_window}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">輸出視窗</span>
                        <span className="font-medium">{modelStatus.parameters.output_window}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">隱藏維度</span>
                        <span className="font-medium">{modelStatus.parameters.hidden_dim}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">注意力頭數</span>
                        <span className="font-medium">{modelStatus.parameters.num_heads}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">注意力層數</span>
                        <span className="font-medium">{modelStatus.parameters.num_blocks}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">站點數量</span>
                        <span className="font-medium">{modelStatus.parameters.site_num}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 模型特性 */}
                <div className="bg-gray-50 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">模型特性</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {modelStatus.features.map((feature, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <CheckCircleIcon className="w-5 h-5 text-green-500 flex-shrink-0" />
                        <span className="text-gray-700">{feature}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <p className="mt-2 text-gray-600">載入系統狀態中...</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MTSTNetPredictor;
