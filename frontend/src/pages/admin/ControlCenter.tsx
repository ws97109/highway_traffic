'use client';

import React, { useState, useEffect } from 'react';
import { 
  ChartBarIcon, 
  ExclamationTriangleIcon, 
  MapIcon, 
  ClockIcon,
  CpuChipIcon,
  SignalIcon,
  BoltIcon,
  UserGroupIcon
} from '@heroicons/react/24/outline';
import TrafficMap from '../../components/maps/TrafficMap';

interface ControlCenterProps {}

interface SystemStatus {
  overallHealth: 'healthy' | 'warning' | 'critical';
  activeShockwaves: number;
  monitoringStations: number;
  predictionsAccuracy: number;
  systemLoad: number;
  lastUpdate: Date;
}

interface TrafficMetrics {
  totalFlow: number;
  averageSpeed: number;
  congestionLevel: number;
  incidentCount: number;
  predictionConfidence: number;
}

interface RecommendedAction {
  id: string;
  priority: 'high' | 'medium' | 'low';
  type: 'traffic_control' | 'route_guidance' | 'emergency_response';
  title: string;
  description: string;
  expectedImpact: string;
  estimatedCost: number;
  implementationTime: number;
  confidence: number;
}

const ControlCenter: React.FC<ControlCenterProps> = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    overallHealth: 'healthy',
    activeShockwaves: 0,
    monitoringStations: 62,
    predictionsAccuracy: 0,
    systemLoad: 0,
    lastUpdate: new Date()
  });

  const [trafficMetrics, setTrafficMetrics] = useState<TrafficMetrics>({
    totalFlow: 0,
    averageSpeed: 0,
    congestionLevel: 0,
    incidentCount: 0,
    predictionConfidence: 0
  });

  const [recommendedActions, setRecommendedActions] = useState<RecommendedAction[]>([]);
  const [selectedView, setSelectedView] = useState<'overview' | 'shockwaves' | 'predictions' | 'control'>('overview');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 模擬即時資料更新
  useEffect(() => {
    const fetchSystemData = async () => {
      try {
        // 系統狀態
        const statusResponse = await fetch('/api/admin/system-status');
        const statusData = await statusResponse.json();
        setSystemStatus(statusData);

        // 交通指標
        const metricsResponse = await fetch('/api/admin/traffic-metrics');
        const metricsData = await metricsResponse.json();
        setTrafficMetrics(metricsData);

        // AI建議
        const actionsResponse = await fetch('/api/admin/recommended-actions');
        const actionsData = await actionsResponse.json();
        setRecommendedActions(actionsData);

      } catch (error) {
        console.error('獲取系統資料失敗:', error);
      }
    };

    fetchSystemData();

    if (autoRefresh) {
      const interval = setInterval(fetchSystemData, 30000); // 30秒更新
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'warning': return 'text-yellow-600 bg-yellow-100';
      case 'critical': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'border-l-red-500 bg-red-50';
      case 'medium': return 'border-l-yellow-500 bg-yellow-50';
      case 'low': return 'border-l-blue-500 bg-blue-50';
      default: return 'border-l-gray-500 bg-gray-50';
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('zh-TW').format(num);
  };

  const executeAction = async (actionId: string) => {
    try {
      const response = await fetch('/api/admin/execute-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actionId })
      });
      
      if (response.ok) {
        // 更新建議列表
        setRecommendedActions(prev => 
          prev.filter(action => action.id !== actionId)
        );
      }
    } catch (error) {
      console.error('執行建議失敗:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* 頂部導航列 */}
      <nav className="bg-white/90 backdrop-blur-md shadow-xl border-b border-gray-200/50 sticky top-0 z-50">
        <div className="max-w-full px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center">
                  <CpuChipIcon className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">智慧交通控制中心</h1>
                  <p className="text-sm text-gray-500">Highway Traffic Control Center</p>
                </div>
              </div>
              
              <div className={`px-4 py-2 rounded-full text-sm font-bold shadow-lg ${getHealthColor(systemStatus.overallHealth)}`}>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    systemStatus.overallHealth === 'healthy' ? 'bg-green-500 animate-pulse' :
                    systemStatus.overallHealth === 'warning' ? 'bg-yellow-500 animate-pulse' : 'bg-red-500 animate-pulse'
                  }`}></div>
                  <span>系統狀態: {systemStatus.overallHealth === 'healthy' ? '正常' : 
                            systemStatus.overallHealth === 'warning' ? '警告' : '異常'}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-6">
              <div className="text-sm text-gray-600 bg-gray-100/80 rounded-full px-3 py-1">
                <ClockIcon className="w-4 h-4 inline mr-1" />
                最後更新: {systemStatus.lastUpdate.toLocaleTimeString('zh-TW')}
              </div>
              
              <label className="flex items-center bg-blue-50 rounded-full px-3 py-1 cursor-pointer hover:bg-blue-100 transition-colors">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="mr-2 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-blue-700">自動更新</span>
              </label>
              
              <button
                onClick={() => window.location.href = '/'}
                className="text-gray-600 hover:text-gray-800 p-2 rounded-full hover:bg-gray-100 transition-colors"
                title="返回首頁"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-full px-6 py-6">
        {/* 導航標籤 */}
        <div className="mb-6">
          <nav className="flex space-x-8">
            {[
              { key: 'overview', label: '總覽', icon: ChartBarIcon },
              { key: 'shockwaves', label: '震波監控', icon: BoltIcon },
              { key: 'predictions', label: '預測分析', icon: CpuChipIcon },
              { key: 'control', label: '交通管制', icon: SignalIcon }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setSelectedView(key as any)}
                className={`flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                  selectedView === key
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {label}
              </button>
            ))}
          </nav>
        </div>

        {/* 主要內容區域 */}
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          
          {/* 左側資訊面板 */}
          <div className="xl:col-span-1 space-y-6">
            
            {/* 系統概況 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <CpuChipIcon className="w-5 h-5 mr-2 text-blue-600" />
                系統概況
              </h2>
              
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">活躍震波</span>
                  <span className="font-bold text-lg text-red-600">
                    {systemStatus.activeShockwaves}
                  </span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">監測站點</span>
                  <span className="font-bold text-lg text-green-600">
                    {systemStatus.monitoringStations}
                  </span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">預測準確度</span>
                  <span className="font-bold text-lg text-blue-600">
                    {(systemStatus.predictionsAccuracy * 100).toFixed(1)}%
                  </span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">系統負載</span>
                  <div className="flex items-center">
                    <div className="w-20 bg-gray-200 rounded-full h-2 mr-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `${systemStatus.systemLoad}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium">{systemStatus.systemLoad}%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 交通指標 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <ChartBarIcon className="w-5 h-5 mr-2 text-green-600" />
                即時交通指標
              </h2>
              
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600">總車流量</span>
                    <span className="font-bold">{formatNumber(trafficMetrics.totalFlow)} 車/小時</span>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600">平均車速</span>
                    <span className="font-bold">{trafficMetrics.averageSpeed.toFixed(1)} km/h</span>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600">壅塞程度</span>
                    <span className={`font-bold ${
                      trafficMetrics.congestionLevel > 70 ? 'text-red-600' :
                      trafficMetrics.congestionLevel > 40 ? 'text-yellow-600' : 'text-green-600'
                    }`}>
                      {trafficMetrics.congestionLevel.toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${
                        trafficMetrics.congestionLevel > 70 ? 'bg-red-600' :
                        trafficMetrics.congestionLevel > 40 ? 'bg-yellow-600' : 'bg-green-600'
                      }`}
                      style={{ width: `${trafficMetrics.congestionLevel}%` }}
                    ></div>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600">事件數量</span>
                    <span className="font-bold text-orange-600">{trafficMetrics.incidentCount}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* AI建議行動 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <BoltIcon className="w-5 h-5 mr-2 text-purple-600" />
                AI決策建議
              </h2>
              
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {recommendedActions.slice(0, 5).map((action) => (
                  <div key={action.id} className={`border-l-4 p-3 rounded ${getPriorityColor(action.priority)}`}>
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-medium text-sm">{action.title}</h4>
                      <span className={`text-xs px-2 py-1 rounded ${
                        action.priority === 'high' ? 'bg-red-200 text-red-800' :
                        action.priority === 'medium' ? 'bg-yellow-200 text-yellow-800' :
                        'bg-blue-200 text-blue-800'
                      }`}>
                        {action.priority === 'high' ? '高' : action.priority === 'medium' ? '中' : '低'}
                      </span>
                    </div>
                    
                    <p className="text-xs text-gray-600 mb-2">{action.description}</p>
                    
                    <div className="flex justify-between items-center text-xs text-gray-500">
                      <span>預期效果: {action.expectedImpact}</span>
                      <span>信心度: {(action.confidence * 100).toFixed(0)}%</span>
                    </div>
                    
                    <button
                      onClick={() => executeAction(action.id)}
                      className="mt-2 w-full bg-blue-600 text-white py-1 px-2 rounded text-xs hover:bg-blue-700 transition-colors"
                    >
                      執行建議
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 主要地圖區域 */}
          <div className="xl:col-span-3">
            <div className="bg-white rounded-lg shadow overflow-hidden" style={{ height: '800px' }}>
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                    <MapIcon className="w-5 h-5 mr-2 text-blue-600" />
                    即時交通監控地圖
                  </h2>
                  
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-2 text-sm">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <span>順暢</span>
                      <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                      <span>壅塞</span>
                      <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                      <span>阻塞</span>
                      <div className="w-3 h-3 bg-purple-500 rounded-full animate-pulse"></div>
                      <span>震波</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div style={{ height: 'calc(100% - 73px)' }}>
                <TrafficMap
                  center={{ lat: 25.0330, lng: 121.5654 }}
                  showTrafficLayer={true}
                  showShockwaveOverlay={true}
                  zoom={9}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlCenter;
