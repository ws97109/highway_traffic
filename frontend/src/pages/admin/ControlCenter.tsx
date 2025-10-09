'use client';

import React, { useState, useEffect } from 'react';
import { 
  ChartBarIcon, 
  ExclamationTriangleIcon, 
  MapIcon, 
  ClockIcon,
  CpuChipIcon,
  BoltIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline';
import TrafficMap from '../../components/maps/TrafficMap';
import MTSTNetPredictor from '../../components/prediction/MTSTNetPredictor';
import { useShockwaveData } from '../../hooks/useShockwaveData';
import { useTrafficData } from '../../hooks/useTrafficData';
import RAGChatbot from '../../components/chat/RagChatbot';

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
  const [chatbotOpen, setChatbotOpen] = useState(false);
  const [selectedShockwaveId, setSelectedShockwaveId] = useState<string | null>(null);

  // 使用 refs 來管理衝擊波列表的滾動
  const shockwaveListRef = React.useRef<HTMLDivElement>(null);
  const shockwaveItemRefs = React.useRef<Map<string, HTMLDivElement>>(new Map());

  // 使用 hooks 獲取即時資料
  const { trafficData } = useTrafficData();
  const { shockwaves, predictions, alerts } = useShockwaveData(); // 管理者介面不需要位置限制

  // 當選中的衝擊波改變時，滾動列表到該項目
  useEffect(() => {
    if (selectedShockwaveId && shockwaveListRef.current) {
      const selectedElement = shockwaveItemRefs.current.get(selectedShockwaveId);
      if (selectedElement) {
        selectedElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [selectedShockwaveId]);

  // 模擬即時資料更新
  useEffect(() => {
    const fetchSystemData = async () => {
      try {
        // 系統狀態
        const statusResponse = await fetch('/api/admin/system-status');
        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          setSystemStatus(prevStatus => ({
            ...prevStatus,
            ...statusData,
            lastUpdate: statusData.lastUpdate ? new Date(statusData.lastUpdate) : new Date()
          }));
        } else {
          // API 不存在時使用模擬資料
          setSystemStatus(prevStatus => ({
            ...prevStatus,
            overallHealth: 'healthy',
            activeShockwaves: Math.floor(Math.random() * 5),
            monitoringStations: 62,
            predictionsAccuracy: 0.85 + Math.random() * 0.1,
            systemLoad: Math.floor(Math.random() * 30) + 20,
            lastUpdate: new Date()
          }));
        }

        // 交通指標
        const metricsResponse = await fetch('/api/admin/traffic-metrics');
        if (metricsResponse.ok) {
          const metricsData = await metricsResponse.json();
          setTrafficMetrics(metricsData);
        } else {
          // API 不存在時使用模擬資料
          setTrafficMetrics({
            totalFlow: Math.floor(Math.random() * 5000) + 15000,
            averageSpeed: Math.floor(Math.random() * 40) + 60,
            congestionLevel: Math.floor(Math.random() * 60) + 20,
            incidentCount: Math.floor(Math.random() * 3),
            predictionConfidence: 0.8 + Math.random() * 0.15
          });
        }

        // AI建議
        const actionsResponse = await fetch('/api/admin/recommended-actions');
        if (actionsResponse.ok) {
          const actionsData = await actionsResponse.json();
          // 檢查返回的資料結構，可能是 { actions: [...] } 或直接是陣列
          const actions = Array.isArray(actionsData) ? actionsData : (actionsData.actions || []);
          setRecommendedActions(actions);
        } else {
          // API 不存在時使用模擬資料
          setRecommendedActions([
            {
              id: '1',
              priority: 'high',
              type: 'traffic_control',
              title: '國道1號南下車流管制',
              description: '建議在台北交流道實施匝道儀控，預計可減少30%壅塞',
              expectedImpact: '減少壅塞30%',
              estimatedCost: 50000,
              implementationTime: 15,
              confidence: 0.92
            },
            {
              id: '2',
              priority: 'medium',
              type: 'route_guidance',
              title: '替代路線引導',
              description: '引導車輛使用省道台1線，分散主線車流',
              expectedImpact: '分散車流15%',
              estimatedCost: 20000,
              implementationTime: 5,
              confidence: 0.78
            }
          ]);
        }

      } catch (error) {
        console.error('獲取系統資料失敗:', error);
        // 發生錯誤時確保 lastUpdate 有值
        setSystemStatus(prevStatus => ({
          ...prevStatus,
          lastUpdate: new Date()
        }));
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
                最後更新: {systemStatus.lastUpdate ? systemStatus.lastUpdate.toLocaleTimeString('zh-TW') : '載入中...'}
              </div>

              {/* AI 智能助手按鈕 */}
              <button
                onClick={() => setChatbotOpen(true)}
                className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-2 rounded-full hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg"
                title="開啟 AI 智能助手"
              >
                <ChatBubbleLeftRightIcon className="w-4 h-4" />
                <span className="text-sm font-medium">AI智能助手</span>
              </button>
              
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
              { key: 'predictions', label: 'MT-STNet預測分析', icon: CpuChipIcon }
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
            
            {/* 衝擊波列表 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <BoltIcon className="w-5 h-5 mr-2 text-red-600" />
                交通衝擊波監測
                {shockwaves.length > 0 && (
                  <span className="ml-2 bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                    {shockwaves.length}
                  </span>
                )}
              </h2>

              {shockwaves.length > 0 ? (
                <div ref={shockwaveListRef} className="space-y-3 max-h-96 overflow-y-auto pr-2">
                  {shockwaves
                    .sort((a: any, b: any) => {
                      const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
                      return (severityOrder[b.severity as keyof typeof severityOrder] || 0) -
                             (severityOrder[a.severity as keyof typeof severityOrder] || 0);
                    })
                    .map((shockwave: any, index: number) => {
                      const severityConfig = {
                        critical: { bg: 'bg-red-50 border-red-400', text: 'text-red-800', icon: '🚨', title: '極危險' },
                        high: { bg: 'bg-orange-50 border-orange-400', text: 'text-orange-800', icon: '⚠️', title: '高風險' },
                        medium: { bg: 'bg-yellow-50 border-yellow-400', text: 'text-yellow-800', icon: '⚡', title: '中度' },
                        low: { bg: 'bg-blue-50 border-blue-400', text: 'text-blue-800', icon: '📍', title: '輕微' }
                      };

                      const severity = shockwave.severity || 'medium';
                      const config = severityConfig[severity as keyof typeof severityConfig] || severityConfig.medium;
                      const isSelected = selectedShockwaveId === shockwave.id;

                      return (
                        <div
                          key={shockwave.id || index}
                          ref={(el) => {
                            if (el && shockwave.id) {
                              shockwaveItemRefs.current.set(shockwave.id, el);
                            }
                          }}
                          onClick={() => setSelectedShockwaveId(shockwave.id)}
                          className={`rounded-lg p-4 border-l-4 cursor-pointer transition-all duration-200 hover:shadow-md hover:scale-[1.02] ${config.bg} ${
                            isSelected ? 'ring-2 ring-blue-500 shadow-lg' : ''
                          }`}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <span className="text-lg">{config.icon}</span>
                              <div>
                                <h3 className={`font-semibold text-sm ${config.text}`}>
                                  {shockwave.location || `${config.title}衝擊波`}
                                </h3>
                                <p className="text-xs text-gray-600">
                                  {shockwave.description || '檢測到真實交通衝擊波'}
                                </p>
                              </div>
                            </div>
                          </div>

                          <div className="grid grid-cols-3 gap-2 text-xs mt-2">
                            <div className="bg-white/60 rounded p-2 text-center">
                              <div className={`font-bold ${config.text}`}>
                                {(shockwave.intensity || 0).toFixed(1)}
                              </div>
                              <div className="text-gray-600">強度</div>
                            </div>
                            <div className="bg-white/60 rounded p-2 text-center">
                              <div className="font-bold text-blue-600">
                                {shockwave.shock_duration || shockwave.duration || '-'}
                              </div>
                              <div className="text-gray-600">持續(分)</div>
                            </div>
                            <div className="bg-white/60 rounded p-2 text-center">
                              <div className="font-bold text-purple-600">
                                {(shockwave.affectedArea || shockwave.affected_area || 0).toFixed(1)}
                              </div>
                              <div className="text-gray-600">半徑(km)</div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <p className="text-gray-500 text-sm font-medium">目前沒有衝擊波</p>
                  <p className="text-gray-400 text-xs mt-1">交通狀況正常</p>
                </div>
              )}
            </div>

            {/* 衝擊波詳細資訊 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <ExclamationTriangleIcon className="w-5 h-5 mr-2 text-orange-600" />
                衝擊波詳細資訊
              </h2>

              {selectedShockwaveId ? (
                (() => {
                  const selectedShockwave = shockwaves.find(sw => sw.id === selectedShockwaveId);
                  if (!selectedShockwave) {
                    return (
                      <div className="text-center py-8 text-gray-500 text-sm">
                        找不到選中的衝擊波資料
                      </div>
                    );
                  }

                  const severityConfig = {
                    critical: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
                    high: { color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
                    medium: { color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200' },
                    low: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' }
                  };
                  const config = severityConfig[selectedShockwave.severity as keyof typeof severityConfig] || severityConfig.medium;

                  return (
                    <div className="space-y-4">
                      {/* 基本資訊 */}
                      <div className={`p-4 rounded-lg ${config.bg} border ${config.border}`}>
                        <h3 className={`font-bold text-sm mb-2 ${config.color}`}>
                          {selectedShockwave.location || '衝擊波事件'}
                        </h3>
                        <p className="text-xs text-gray-600">
                          {selectedShockwave.description || '檢測到真實交通衝擊波'}
                        </p>
                      </div>

                      {/* 關鍵指標 */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 mb-1">強度等級</div>
                          <div className={`text-lg font-bold ${config.color}`}>
                            {(selectedShockwave.intensity || 0).toFixed(1)}/10
                          </div>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 mb-1">嚴重程度</div>
                          <div className={`text-lg font-bold ${config.color}`}>
                            {selectedShockwave.severity === 'critical' ? '極危險' :
                             selectedShockwave.severity === 'high' ? '高風險' :
                             selectedShockwave.severity === 'medium' ? '中度' : '輕微'}
                          </div>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 mb-1">持續時間</div>
                          <div className="text-lg font-bold text-blue-600">
                            {selectedShockwave.shock_duration || '-'} 分鐘
                          </div>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 mb-1">影響半徑</div>
                          <div className="text-lg font-bold text-purple-600">
                            {(selectedShockwave.affectedArea || selectedShockwave.affected_area || 0).toFixed(1)} km
                          </div>
                        </div>
                      </div>

                      {/* 管理者進階資訊 */}
                      <div className="border-t pt-4">
                        <h4 className="font-semibold text-sm text-gray-900 mb-3">管理者資訊</h4>
                        <div className="space-y-2 text-sm">
                          {selectedShockwave.propagationSpeed && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">傳播速度</span>
                              <span className="font-medium">{selectedShockwave.propagationSpeed.toFixed(1)} km/h</span>
                            </div>
                          )}
                          {selectedShockwave.waveDirection && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">波向</span>
                              <span className="font-medium">
                                {selectedShockwave.waveDirection === 'upstream' ? '上游' : '下游'}
                              </span>
                            </div>
                          )}
                          {selectedShockwave.speedDrop !== undefined && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">速度下降</span>
                              <span className="font-medium text-red-600">{selectedShockwave.speedDrop.toFixed(1)} km/h</span>
                            </div>
                          )}
                          {selectedShockwave.initialSpeed !== undefined && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">初始速度</span>
                              <span className="font-medium">{selectedShockwave.initialSpeed.toFixed(1)} km/h</span>
                            </div>
                          )}
                          {selectedShockwave.finalSpeed !== undefined && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">最終速度</span>
                              <span className="font-medium">{selectedShockwave.finalSpeed.toFixed(1)} km/h</span>
                            </div>
                          )}
                          {selectedShockwave.queueGrowthRate !== undefined && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">隊列增長率</span>
                              <span className="font-medium">{selectedShockwave.queueGrowthRate.toFixed(0)} 車/小時</span>
                            </div>
                          )}
                          {selectedShockwave.initialFlow !== undefined && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">初始流量</span>
                              <span className="font-medium">{selectedShockwave.initialFlow.toFixed(0)} 車/小時</span>
                            </div>
                          )}
                          {selectedShockwave.finalFlow !== undefined && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">最終流量</span>
                              <span className="font-medium">{selectedShockwave.finalFlow.toFixed(0)} 車/小時</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* 座標資訊 */}
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-xs text-gray-600 mb-1">座標位置</div>
                        <div className="text-xs font-mono text-gray-800">
                          {selectedShockwave.lat.toFixed(6)}, {selectedShockwave.lng.toFixed(6)}
                        </div>
                      </div>
                    </div>
                  );
                })()
              ) : (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <ExclamationTriangleIcon className="w-8 h-8 text-gray-400" />
                  </div>
                  <p className="text-gray-500 text-sm font-medium">請選擇衝擊波</p>
                  <p className="text-gray-400 text-xs mt-1">點擊左側列表或地圖上的衝擊波查看詳細資訊</p>
                </div>
              )}
            </div>
          </div>

          {/* 主要內容區域 */}
          <div className="xl:col-span-3">
            {selectedView === 'predictions' ? (
              /* MT-STNet 預測分析 */
              <MTSTNetPredictor />
            ) : (
              /* 地圖視圖 */
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
                    trafficData={trafficData}
                    shockwaves={shockwaves as any}
                    predictions={predictions}
                    showTrafficLayer={true}
                    showShockwaveOverlay={true}
                    zoom={9}
                    selectedShockwaveId={selectedShockwaveId}
                    onShockwaveClick={(id) => setSelectedShockwaveId(id)}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* RAG 聊天機器人組件 */}
      <RAGChatbot
        isOpen={chatbotOpen}
        onClose={() => setChatbotOpen(false)}
        position="fixed"
        trafficData={trafficData}
        shockwaves={shockwaves}
        predictions={predictions}
      />
    </div>
  );
};

export default ControlCenter;
