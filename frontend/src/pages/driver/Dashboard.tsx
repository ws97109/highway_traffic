'use client';

import React, { useState, useEffect } from 'react';
import { MapPinIcon, ExclamationTriangleIcon, ClockIcon, MapIcon, ChatBubbleLeftRightIcon, SparklesIcon } from '@heroicons/react/24/outline';
import TrafficMap from '../../components/maps/TrafficMap';
import { useUserLocation, useAddressSearch, useDirections } from '../../hooks/useGoogleServices';
import { useTrafficData } from '../../hooks/useTrafficData';
import { useShockwaveData } from '../../hooks/useShockwaveData';
import DepartureTimeOptimizer from '../../components/smart/DepartureTimeOptimizer';
import ShockwaveAlert from '../../components/alerts/ShockwaveAlert';
import apiDiagnostics from '../../utils/apiDiagnostics';
import DataConnectionStatus from '../../components/diagnostics/DataConnectionStatus';

const DriverDashboard: React.FC = () => {
  const [destination, setDestination] = useState('');
  const [showRouteInput, setShowRouteInput] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<any>(null);
  
  // RAG 智能建議相關狀態
  const [showRAGAdvice, setShowRAGAdvice] = useState(false);
  const [ragAdvice, setRagAdvice] = useState<any>(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [showRAGChat, setShowRAGChat] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [ragStatus, setRagStatus] = useState<any>(null);
  const [chatLoading, setChatLoading] = useState(false);

  // Google 服務 Hooks
  const { 
    location: userLocation, 
    address: userAddress, 
    loading: locationLoading,
    getCurrentLocation,
    setCustomLocation 
  } = useUserLocation();

  const { 
    results: searchResults, 
    loading: searchLoading,
    searchAddress 
  } = useAddressSearch();

  const { 
    route, 
    loading: routeLoading,
    getDirections,
    clearRoute 
  } = useDirections();

  // 交通資料 Hooks
  const { trafficData, loading: trafficLoading, error: trafficError } = useTrafficData();
  const { shockwaves, predictions, alerts, loading: shockwaveLoading, error: shockwaveError } = useShockwaveData(userLocation);

  // 調試：打印數據狀態
  useEffect(() => {
    console.log('📊 Dashboard 數據狀態更新:');
    console.log('- 交通數據:', trafficData.length, '個站點');
    console.log('- 震波數據:', shockwaves.length, '個事件');
    console.log('- 預測數據:', predictions.length, '個預測');
    console.log('- 警告數據:', alerts.length, '個警告');
    console.log('- 交通錯誤:', trafficError);
    console.log('- 震波錯誤:', shockwaveError);
  }, [trafficData, shockwaves, predictions, alerts, trafficError, shockwaveError]);

  // 初始化時取得位置、RAG狀態和API診斷
  useEffect(() => {
    getCurrentLocation();
    checkRAGStatus();
    
    // 延遲執行 API 診斷，確保 Google Maps API 已載入
    setTimeout(async () => {
      try {
        const diagnostics = await apiDiagnostics.runDiagnostics();
        apiDiagnostics.logDiagnosticsReport(diagnostics);
      } catch (error) {
        console.warn('API 診斷失敗:', error);
      }
    }, 3000);
  }, [getCurrentLocation]);

  // 檢查 Ollama AI 狀態
  const checkRAGStatus = async () => {
    try {
      const response = await fetch('http://localhost:11434/api/tags');
      if (response.ok) {
        const data = await response.json();
        setRagStatus({ 
          system_health: 'healthy', 
          ollama_connected: true,
          available_models: data.models?.length || 0,
          current_model: 'qwen2.5:7b'
        });
      } else {
        setRagStatus({ system_health: 'unavailable', error: 'Ollama 連接失敗' });
      }
    } catch (error) {
      console.error('檢查 Ollama 狀態失敗:', error);
      setRagStatus({ system_health: 'unavailable', error: 'Ollama 服務不可用' });
    }
  };

  // 獲取RAG智能建議
  const getRAGAdvice = async () => {
    if (!userLocation) {
      alert('請先取得您的位置');
      return;
    }

    setRagLoading(true);
    try {
      // 構建 AI 分析提示
      let advicePrompt = `【交通諮詢】我是台灣駕駛人，目前位置：${userLocation.lat}, ${userLocation.lng}`;

      if (destination) {
        advicePrompt += `，計劃前往：${destination}`;
      }

      if (trafficData.length > 0) {
        const avgSpeed = trafficData.reduce((sum, station) => sum + (station.speed || 0), 0) / trafficData.length;
        const congestedCount = trafficData.filter(station => station.speed < 50).length;
        advicePrompt += `\n\n【即時路況】監測站點：${trafficData.length}個，平均車速：${avgSpeed.toFixed(1)}km/h`;
        if (congestedCount > 0) {
          advicePrompt += `，壅塞站點：${congestedCount}個`;
        }
      }

      if (alerts.length > 0) {
        advicePrompt += `\n【警報】檢測到${alerts.length}個交通警報事件`;
      }

      advicePrompt += `\n\n請根據以上實際監測資料，提供專業的台灣本土化駕駛建議，包括詳細的路線規劃、行駛指引和注意事項。使用繁體中文回答。`;

      const response = await fetch('http://localhost:11434/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'qwen2.5:7b',
          prompt: advicePrompt,
          stream: false,
          options: {
            temperature: 0.2,
            num_predict: 400,
            stop: ["如果您還有", "祝您一路平安", "希望以上建議"]
          }
        })
      });

      if (!response.ok) {
        throw new Error('AI 服務暫時不可用');
      }

      const result = await response.json();
      const advice = {
        title: "🤖 AI 智能建議",
        description: result.response || '暫無建議',
        priority: "medium",
        action_type: "route_optimization",
        reasoning: "基於即時交通數據分析",
        confidence: 0.85,
        source: "Ollama AI"
      };
      setRagAdvice(advice);
      setShowRAGAdvice(true);
    } catch (error) {
      console.error('獲取RAG建議失敗:', error);
      alert('獲取智能建議失敗，請稍後再試');
    } finally {
      setRagLoading(false);
    }
  };

  // Ollama AI 對話功能
  const sendChatMessage = async () => {
    if (!chatMessage.trim() || chatLoading) return;

    const userMessage = chatMessage;
    setChatMessage('');
    setChatLoading(true);
    
    // 添加用戶消息到歷史
    setChatHistory(prev => [...prev, { type: 'user', content: userMessage, timestamp: new Date() }]);
    
    // 添加"AI思考中"消息
    setChatHistory(prev => [...prev, { 
      type: 'thinking', 
      content: 'AI助手正在分析交通數據...', 
      timestamp: new Date() 
    }]);

    try {
      console.log('🤖 發送消息到 Ollama AI:', userMessage);
      
      // 準備發送給 AI 的數據
      const chatData = {
        message: userMessage,
        traffic_data: {
          stations: trafficData,
          total_count: trafficData.length,
          last_updated: new Date().toISOString()
        },
        shockwave_data: {
          shockwaves: shockwaves,
          predictions: predictions,
          count: shockwaves.length
        },
        user_location: userLocation
      };

      console.log('📊 發送給AI的數據:', chatData);
      
      // 直接調用 Ollama API
      const response = await fetch('http://localhost:11434/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'qwen2.5:7b',
          prompt: buildTrafficAnalysisPrompt(userMessage, chatData),
          stream: false,
          options: {
            temperature: 0.2,
            num_predict: 400,
            stop: ["如果您還有", "祝您一路平安", "希望以上建議"]
          }
        })
      });

      console.log('📡 Ollama API 回應狀態:', response.status);

      // 移除"思考中"消息
      setChatHistory(prev => prev.filter(msg => msg.type !== 'thinking'));

      if (!response.ok) {
        throw new Error(`Ollama API 錯誤 ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ 收到 Ollama 回應:', result);
      
      // 添加AI回應到歷史
      setChatHistory(prev => [...prev, { 
        type: 'assistant', 
        content: result.response || '抱歉，AI 無法生成回應。', 
        timestamp: new Date(),
        source: 'Ollama AI (qwen2.5:7b)'
      }]);
    } catch (error) {
      console.error('❌ AI 對話失敗:', error);
      
      // 移除"思考中"消息
      setChatHistory(prev => prev.filter(msg => msg.type !== 'thinking'));
      
      setChatHistory(prev => [...prev, { 
        type: 'error', 
        content: `抱歉，AI助手暫時不可用：${error instanceof Error ? error.message : '未知錯誤'}`, 
        timestamp: new Date() 
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  // 構建交通分析提示詞
  const buildTrafficAnalysisPrompt = (userMessage: string, data: any) => {
    const { traffic_data, shockwave_data, user_location } = data;
    
    let prompt = `【台灣交通諮詢】我是台灣駕駛人`;

    if (user_location) {
      prompt += `，目前位置：${user_location.lat.toFixed(4)}, ${user_location.lng.toFixed(4)}`;
    }

    if (traffic_data && traffic_data.stations.length > 0) {
      const avgSpeed = traffic_data.stations.reduce((sum: number, station: any) => sum + (station.speed || 0), 0) / traffic_data.stations.length;
      const congestedStations = traffic_data.stations.filter((s: any) => s.speed < 50);
      const smoothStations = traffic_data.stations.filter((s: any) => s.speed >= 80);
      
      prompt += `\n\n【即時路況資料】`;
      prompt += `\n監測站點：${traffic_data.stations.length}個`;
      prompt += `\n平均車速：${avgSpeed.toFixed(1)}km/h`;
      prompt += `\n順暢站點：${smoothStations.length}個（≥80km/h）`;
      
      if (congestedStations.length > 0) {
        prompt += `\n壅塞站點：${congestedStations.length}個（<50km/h）`;
      }
    }

    if (shockwave_data && shockwave_data.shockwaves.length > 0) {
      prompt += `\n\n【震波警報】偵測到${shockwave_data.shockwaves.length}個交通震波事件`;
    }

    prompt += `\n\n【駕駛問題】${userMessage}`;
    prompt += `\n\n請根據以上實際監測資料，提供台灣本土化的專業駕駛建議，包括詳細的路線指引和行駛方式（使用繁體中文）：`;

    return prompt;
  };

  // 處理目的地搜尋
  const handleDestinationSearch = async (query: string) => {
    setDestination(query);
    if (query.length > 2) {
      await searchAddress(query);
    }
  };

  // 處理路線規劃
  const handleRouteRequest = async (destinationAddress: string) => {
    if (!userLocation) {
      alert('請先取得您的位置');
      return;
    }

    try {
      await getDirections(userLocation, destinationAddress);
      setShowRouteInput(false);
      setDestination(destinationAddress);
    } catch (error) {
      console.error('路線規劃失敗:', error);
    }
  };

  // 風險等級顏色
  const getRiskColor = (level: string) => {
    switch (level) {
      case 'low': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'high': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  // 格式化時間
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    
    if (hours > 0) {
      return `${hours}小時${remainingMins}分鐘`;
    }
    return `${remainingMins}分鐘`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* 頂部導航列 */}
      <nav className="bg-white/90 backdrop-blur-md shadow-lg border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                  <MapIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">智慧交通助手</h1>
                  <p className="text-xs text-gray-500">Driver Dashboard</p>
                </div>
              </div>
              
              {userLocation && (
                <div className="hidden md:flex items-center bg-gray-100/80 rounded-full px-3 py-1">
                  <MapPinIcon className="w-4 h-4 mr-2 text-blue-600" />
                  <span className="text-sm text-gray-700 truncate max-w-xs">
                    {userAddress || `${userLocation.lat.toFixed(4)}, ${userLocation.lng.toFixed(4)}`}
                  </span>
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-600">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span>即時監控</span>
                {ragStatus && (
                  <div className="flex items-center space-x-1 ml-3">
                    <div className={`w-2 h-2 rounded-full ${
                      ragStatus.system_health === 'healthy' ? 'bg-green-500' :
                      ragStatus.system_health === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
                    }`}></div>
                    <span className="text-xs">RAG</span>
                  </div>
                )}
              </div>
              
              {/* RAG智能建議按鈕 */}
              <button
                onClick={getRAGAdvice}
                disabled={ragLoading || ragStatus?.system_health === 'unavailable'}
                className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-2 rounded-full text-sm font-medium hover:from-purple-700 hover:to-pink-700 flex items-center shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                title="獲取AI智能建議"
              >
                <SparklesIcon className="w-4 h-4 mr-2" />
                {ragLoading ? 'AI分析中...' : 'AI建議'}
              </button>
              
              {/* RAG對話按鈕 */}
              <button
                onClick={() => setShowRAGChat(true)}
                disabled={ragStatus?.system_health === 'unavailable'}
                className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-4 py-2 rounded-full text-sm font-medium hover:from-emerald-700 hover:to-teal-700 flex items-center shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                title="與AI助手對話"
              >
                <ChatBubbleLeftRightIcon className="w-4 h-4 mr-2" />
                AI助手
              </button>
              
              <button
                onClick={() => setShowRouteInput(true)}
                className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-2 rounded-full text-sm font-medium hover:from-blue-700 hover:to-indigo-700 flex items-center shadow-lg hover:shadow-xl transition-all duration-200"
              >
                <MapIcon className="w-4 h-4 mr-2" />
                規劃路線
              </button>
              
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

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          
          {/* 左側面板 - 警告和資訊 */}
          <div className="lg:col-span-1 space-y-6">
            
            {/* 數據狀態面板 - 調試用 */}
            <div className="bg-white/90 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200/50 p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">📊 系統狀態</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>交通數據:</span>
                  <span className={trafficError ? 'text-red-600' : 'text-green-600'}>
                    {trafficError ? '錯誤' : `${trafficData.length} 個站點`}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>震波事件:</span>
                  <span className={shockwaveError ? 'text-red-600' : 'text-blue-600'}>
                    {shockwaveError ? '錯誤' : `${shockwaves.length} 個事件`}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>預測數據:</span>
                  <span className="text-purple-600">{predictions.length} 個預測</span>
                </div>
                <div className="flex justify-between">
                  <span>警告數量:</span>
                  <span className={alerts.length > 0 ? 'text-orange-600' : 'text-gray-600'}>
                    {alerts.length} 個警告
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>RAG系統:</span>
                  <span className={ragStatus?.system_health === 'available' ? 'text-green-600' : 'text-yellow-600'}>
                    {ragStatus?.system_health || '檢查中...'}
                  </span>
                </div>
              </div>
            </div>
            
            {/* 即時警告 */}
            <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200/50 p-6">              
              {alerts.length > 0 ? (
                <div className="space-y-3">
                  {alerts.slice(0, 3).map((alert, index) => (
                    <div
                      key={index}
                      className={`p-4 rounded-xl cursor-pointer transition-all duration-200 hover:scale-105 border-l-4 ${
                        alert.level === 'high' ? 'border-l-red-500 bg-red-50 hover:bg-red-100' :
                        alert.level === 'medium' ? 'border-l-yellow-500 bg-yellow-50 hover:bg-yellow-100' :
                        'border-l-blue-500 bg-blue-50 hover:bg-blue-100'
                      }`}
                      onClick={() => setSelectedAlert(alert)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="font-semibold text-sm text-gray-900">{alert.title}</div>
                          <div className="text-xs mt-1 text-gray-600">{alert.description}</div>
                          <div className="flex items-center text-xs mt-2 text-gray-500">
                            <ClockIcon className="w-3 h-3 mr-1" />
                            {alert.estimatedImpact}
                          </div>
                        </div>
                        <div className={`w-2 h-2 rounded-full ${
                          alert.level === 'high' ? 'bg-red-500 animate-pulse' :
                          alert.level === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'
                        }`}></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <p className="text-gray-500 text-sm font-medium">目前沒有警告</p>
                  <p className="text-gray-400 text-xs mt-1">路況良好，安全出行</p>
                </div>
              )}
            </div>

            {/* 路線資訊 */}
            {route && (
              <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200/50 p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center mr-3">
                    <MapIcon className="w-5 h-5 text-white" />
                  </div>
                  路線資訊
                </h2>
                
                <div className="space-y-4">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600">{route.distance.text}</div>
                        <div className="text-xs text-gray-600">總距離</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-indigo-600">{route.duration.text}</div>
                        <div className="text-xs text-gray-600">預估時間</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="pt-2">
                    <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                      <svg className="w-4 h-4 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      路線指引
                    </h3>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {route.steps.slice(0, 5).map((step, index) => (
                        <div key={index} className="flex items-start space-x-3 p-2 rounded-lg hover:bg-gray-50">
                          <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-xs font-bold text-blue-600">{index + 1}</span>
                          </div>
                          <div className="text-xs text-gray-700 leading-relaxed">
                            {step.instruction.replace(/<[^>]*>/g, '')}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                
                <button
                  onClick={clearRoute}
                  className="w-full mt-4 bg-red-50 text-red-600 py-2 px-4 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors"
                >
                  清除路線
                </button>
              </div>
            )}

            {/* 交通預測 */}
            <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200/50 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg flex items-center justify-center mr-3">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                交通預測
              </h2>
              
              {predictions.length > 0 ? (
                <div className="space-y-3">
                  {predictions.slice(0, 2).map((prediction, index) => (
                    <div key={index} className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 border-l-4 border-green-400">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-sm font-semibold text-gray-900">{prediction.location}</div>
                        <div className="flex items-center space-x-1">
                          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                          <span className="text-xs text-green-600 font-medium">即時</span>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div className="bg-white/60 rounded-lg p-2 text-center">
                          <div className="font-bold text-lg text-green-600">{prediction.predictedSpeed}</div>
                          <div className="text-gray-600">km/h</div>
                        </div>
                        <div className="bg-white/60 rounded-lg p-2 text-center">
                          <div className="font-bold text-lg text-blue-600">{(prediction.confidence * 100).toFixed(0)}%</div>
                          <div className="text-gray-600">信心度</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-8 h-8 text-blue-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </div>
                  <p className="text-gray-500 text-sm font-medium">正在載入預測資料</p>
                  <p className="text-gray-400 text-xs mt-1">AI 分析中...</p>
                </div>
              )}
            </div>
          </div>

          {/* 主要地圖區域 */}
          <div className="lg:col-span-3">
            <div className="bg-white/90 backdrop-blur-sm rounded-xl shadow-xl border border-gray-200/50 overflow-hidden" style={{ height: '600px' }}>
              <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-white">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                      <MapIcon className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold">即時交通地圖</h2>
                      <p className="text-xs text-blue-100">Real-time Traffic Monitor</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-3 text-sm">
                      <div className="flex items-center space-x-1">
                        <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                        <span className="text-xs">順暢</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
                        <span className="text-xs">壅塞</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <div className="w-3 h-3 bg-red-400 rounded-full"></div>
                        <span className="text-xs">阻塞</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <div className="w-3 h-3 bg-purple-400 rounded-full animate-pulse"></div>
                        <span className="text-xs">震波</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div style={{ height: 'calc(100% - 80px)' }} className="relative">
                <TrafficMap
                  center={userLocation || undefined}
                  trafficData={trafficData}
                  shockwaves={shockwaves as any}
                  predictions={predictions}
                  onLocationUpdate={setCustomLocation}
                  showTrafficLayer={true}
                  showShockwaveOverlay={true}
                />
                
                {/* 地圖控制按鈕 */}
                <div className="absolute top-20 right-2 flex flex-col space-y-2">
                  <button
                    onClick={getCurrentLocation}
                    className="bg-white/90 backdrop-blur-sm p-3 rounded-lg shadow-lg hover:bg-white transition-colors"
                    title="定位到我的位置"
                  >
                    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </button>
                  
                  <button
                    className="bg-white/90 backdrop-blur-sm p-3 rounded-lg shadow-lg hover:bg-white transition-colors"
                    title="重新整理地圖"
                  >
                    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                </div>
                
                {/* 載入覆蓋層 */}
                {(trafficLoading || locationLoading) && (
                  <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center">
                    <div className="bg-white rounded-lg shadow-lg p-6 flex items-center space-x-3">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                      <span className="text-gray-700 font-medium">載入地圖資料中...</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 路線輸入對話框 */}
      {showRouteInput && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 max-w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">規劃路線</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  目的地
                </label>
                <input
                  type="text"
                  value={destination}
                  onChange={(e) => handleDestinationSearch(e.target.value)}
                  placeholder="輸入目的地地址..."
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              {searchResults.length > 0 && (
                <div className="max-h-40 overflow-y-auto border border-gray-200 rounded-md">
                  {searchResults.map((result, index) => (
                    <div
                      key={index}
                      onClick={() => handleRouteRequest(result.address)}
                      className="p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                    >
                      <div className="font-medium text-sm">{result.address}</div>
                      <div className="text-xs text-gray-500">
                        {result.lat.toFixed(6)}, {result.lng.toFixed(6)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setShowRouteInput(false);
                  setDestination('');
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                取消
              </button>
              <button
                onClick={() => handleRouteRequest(destination)}
                disabled={!destination || routeLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {routeLoading ? '規劃中...' : '開始導航'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 警告詳情對話框 */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 max-w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">警告詳情</h3>
              <button
                onClick={() => setSelectedAlert(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-4">
              <div className={`p-3 rounded-md ${getRiskColor(selectedAlert.level)}`}>
                <div className="font-medium">{selectedAlert.title}</div>
                <div className="text-sm mt-1">{selectedAlert.description}</div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">風險等級:</span>
                  <span className="font-medium capitalize">{selectedAlert.level}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">預估影響:</span>
                  <span className="font-medium">{selectedAlert.estimatedImpact}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">發生時間:</span>
                  <span className="font-medium">{selectedAlert.timestamp}</span>
                </div>
              </div>
              
              {selectedAlert.recommendations && (
                <div>
                  <h4 className="font-medium text-sm mb-2">建議行動:</h4>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {selectedAlert.recommendations.map((rec: string, index: number) => (
                      <li key={index} className="flex items-start">
                        <span className="mr-2">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            
            <div className="flex justify-end mt-6">
              <button
                onClick={() => setSelectedAlert(null)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RAG智能建議對話框 */}
      {showRAGAdvice && ragAdvice && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                  <SparklesIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">AI智能建議</h3>
                  <p className="text-sm text-gray-600">基於RAG模型的個人化駕駛建議</p>
                </div>
              </div>
              <button
                onClick={() => setShowRAGAdvice(false)}
                className="text-gray-400 hover:text-gray-600 p-2 rounded-full hover:bg-gray-100"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-6">
              {/* 建議優先級和信心度 */}
              <div className="flex items-center justify-between bg-gray-50 rounded-lg p-4">
                <div className="flex items-center space-x-3">
                  <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                    ragAdvice.priority === 'urgent' ? 'bg-red-100 text-red-800' :
                    ragAdvice.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                    ragAdvice.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {ragAdvice.priority.toUpperCase()}
                  </div>
                  <span className="text-sm text-gray-600">優先級</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">信心度</span>
                  <div className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium">
                    {(ragAdvice.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
              
              {/* 建議標題和描述 */}
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-6 border-l-4 border-purple-400">
                <h4 className="text-lg font-bold text-gray-900 mb-3">{ragAdvice.title}</h4>
                <p className="text-gray-700 leading-relaxed">{ragAdvice.description}</p>
              </div>
              
              {/* 安全影響 */}
              <div className="bg-blue-50 rounded-lg p-4">
                <h5 className="font-semibold text-gray-900 mb-2 flex items-center">
                  <ExclamationTriangleIcon className="w-5 h-5 mr-2 text-blue-600" />
                  安全評估
                </h5>
                <p className="text-gray-700">{ragAdvice.safety_impact}</p>
              </div>
              
              {/* 時間節省 */}
              {ragAdvice.time_saving_min && (
                <div className="bg-green-50 rounded-lg p-4">
                  <h5 className="font-semibold text-gray-900 mb-2 flex items-center">
                    <ClockIcon className="w-5 h-5 mr-2 text-green-600" />
                    時間影響
                  </h5>
                  <p className="text-gray-700">
                    預計{ragAdvice.time_saving_min > 0 ? '節省' : '增加'} {Math.abs(ragAdvice.time_saving_min)} 分鐘
                  </p>
                </div>
              )}
              
              {/* AI分析理由 */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h5 className="font-semibold text-gray-900 mb-2">AI分析理由</h5>
                <p className="text-gray-700 text-sm leading-relaxed">{ragAdvice.reasoning}</p>
              </div>
              
              {/* 替代路線 */}
              {ragAdvice.alternatives && ragAdvice.alternatives.length > 0 && (
                <div>
                  <h5 className="font-semibold text-gray-900 mb-3">替代路線建議</h5>
                  <div className="space-y-3">
                    {ragAdvice.alternatives.map((alt, index) => (
                      <div key={index} className="bg-white border border-gray-200 rounded-lg p-4">
                        <div className="font-medium text-gray-900">{alt.route_name}</div>
                        <div className="text-sm text-gray-600 mt-1">{alt.description}</div>
                        <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                          <span>額外距離: {alt.extra_distance_km}km</span>
                          <span>時間差: {alt.time_difference_min > 0 ? '+' : ''}{alt.time_difference_min}分鐘</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* 附近休息站 */}
              {ragAdvice.rest_areas && ragAdvice.rest_areas.length > 0 && (
                <div>
                  <h5 className="font-semibold text-gray-900 mb-3">附近休息站</h5>
                  <div className="space-y-3">
                    {ragAdvice.rest_areas.map((area, index) => (
                      <div key={index} className="bg-white border border-gray-200 rounded-lg p-4">
                        <div className="font-medium text-gray-900">{area.name}</div>
                        <div className="text-sm text-gray-600 mt-1">
                          {area.direction} {area.distance_km}km，約 {area.estimated_travel_time} 分鐘車程
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          設施: {area.facilities.join(', ')}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* 成本估算 */}
              {ragAdvice.estimated_cost && (
                <div className="bg-yellow-50 rounded-lg p-4">
                  <h5 className="font-semibold text-gray-900 mb-2">成本估算</h5>
                  <p className="text-gray-700 text-sm">{ragAdvice.estimated_cost}</p>
                </div>
              )}
            </div>
            
            <div className="flex justify-between items-center mt-6 pt-6 border-t border-gray-200">
              <div className="text-sm text-gray-500">
                由 RAG+Ollama AI 提供 • 建議僅供參考
              </div>
              <button
                onClick={() => setShowRAGAdvice(false)}
                className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 transition-colors"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RAG對話助手 */}
      {showRAGChat && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-2xl mx-4 h-[600px] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg flex items-center justify-center">
                  <ChatBubbleLeftRightIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">AI交通助手</h3>
                  <p className="text-sm text-gray-600">智能駕駛諮詢服務</p>
                </div>
              </div>
              <button
                onClick={() => setShowRAGChat(false)}
                className="text-gray-400 hover:text-gray-600 p-2 rounded-full hover:bg-gray-100"
              >
                ✕
              </button>
            </div>
            
            {/* 對話歷史 */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {chatHistory.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <ChatBubbleLeftRightIcon className="w-8 h-8 text-emerald-600" />
                  </div>
                  <p className="text-gray-500 font-medium">您好！我是AI交通助手</p>
                  <p className="text-gray-400 text-sm mt-2">
                    您可以詢問關於交通狀況、路線建議、駕駛安全等任何問題
                  </p>
                  <div className="flex flex-wrap justify-center gap-2 mt-4">
                    {['目前路況如何？', '有什麼替代路線？', '什麼時候出發最好？'].map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => setChatMessage(suggestion)}
                        className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1 rounded-full text-xs transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                chatHistory.map((msg, index) => (
                  <div key={index} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-lg p-4 ${
                      msg.type === 'user' ? 'bg-blue-600 text-white' :
                      msg.type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
                      'bg-gray-100 text-gray-900'
                    }`}>
                      <div className="text-sm">{msg.content}</div>
                      <div className="text-xs mt-2 opacity-70">
                        {msg.timestamp.toLocaleTimeString()}
                        {msg.source && ` • ${msg.source}`}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
            
            {/* 輸入區域 */}
            <div className="p-6 border-t border-gray-200">
              <div className="flex space-x-3">
                <input
                  type="text"
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
                  placeholder="輸入您的問題..."
                  className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
                <button
                  onClick={sendChatMessage}
                  disabled={!chatMessage.trim()}
                  className="bg-emerald-600 text-white px-6 py-2 rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  發送
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 載入指示器 */}
      {(locationLoading || trafficLoading || routeLoading || ragLoading) && (
        <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-lg p-4 flex items-center space-x-3">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="text-sm text-gray-600">
            {locationLoading && '取得位置中...'}
            {trafficLoading && '載入交通資料...'}
            {routeLoading && '規劃路線中...'}
            {ragLoading && 'AI分析中...'}
          </span>
        </div>
      )}

      {/* API連接狀態診斷工具 */}
      <DataConnectionStatus />
    </div>
  );
};

export default DriverDashboard;
