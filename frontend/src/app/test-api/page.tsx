'use client';

import { useState } from 'react';

/**
 * API 測試頁面
 * 用於測試 Ollama 和其他 API 連接
 */
export default function TestAPIPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>('');

  // 測試 RAG Chat API
  const testRagChat = async () => {
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/api/rag/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: '你好，請介紹一下台灣的高速公路系統',
          traffic_data: null,
          shockwave_data: null,
          user_location: { lat: 25.0330, lng: 121.5654 },
          use_rag: true
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知錯誤');
    } finally {
      setLoading(false);
    }
  };

  // 測試 Ollama 狀態
  const testOllamaStatus = async () => {
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/api/rag/chat', {
        method: 'GET',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知錯誤');
    } finally {
      setLoading(false);
    }
  };

  // 測試震波分析 API
  const testShockwaveAnalysis = async () => {
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/api/shockwave-ai/shockwave-analysis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_location: { lat: 25.0330, lng: 121.5654 },
          shockwaves: [
            {
              id: 1,
              latitude: 25.0500,
              longitude: 121.5800,
              intensity: 7.5,
              shock_duration: 35,
              affected_area: 5.2,
              propagation_speed: 25,
              location_name: '國道一號 南港段',
              severity: 'high'
            }
          ],
          user_message: '請分析目前的震波情況並提供建議'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知錯誤');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">API 測試頁面</h1>

        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">測試項目</h2>

          <div className="space-y-3">
            <button
              onClick={testOllamaStatus}
              disabled={loading}
              className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '測試中...' : '1. 測試 Ollama 服務狀態'}
            </button>

            <button
              onClick={testRagChat}
              disabled={loading}
              className="w-full bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '測試中...' : '2. 測試 RAG Chat API'}
            </button>

            <button
              onClick={testShockwaveAnalysis}
              disabled={loading}
              className="w-full bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '測試中...' : '3. 測試震波分析 API'}
            </button>
          </div>
        </div>

        {/* 錯誤訊息 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-red-800 mb-2">❌ 錯誤</h3>
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* 結果顯示 */}
        {result && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold mb-4">✅ 測試結果</h3>
            <pre className="bg-gray-100 p-4 rounded-lg overflow-auto max-h-96 text-sm">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}

        {/* 環境變數檢查 */}
        <div className="bg-white rounded-lg shadow-lg p-6 mt-6">
          <h3 className="text-lg font-semibold mb-4">🔧 環境變數</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="font-medium">Ollama URL:</span>
              <span className="text-gray-600">
                {process.env.NEXT_PUBLIC_OLLAMA_URL || '未設定'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Google Maps API Key:</span>
              <span className="text-gray-600">
                {process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
                  ? `${process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY.substring(0, 10)}...`
                  : '未設定'}
              </span>
            </div>
          </div>
        </div>

        {/* 返回按鈕 */}
        <div className="mt-6">
          <button
            onClick={() => window.location.href = '/driver/dashboard'}
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            ← 返回 Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
