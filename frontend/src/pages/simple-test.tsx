import React, { useState, useEffect } from 'react';

const SimpleTest: React.FC = () => {
  const [trafficData, setTrafficData] = useState<any>(null);
  const [shockwaveData, setShockwaveData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const testAPIs = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('📡 開始測試 API...');
      
      // 測試交通數據
      const trafficResponse = await fetch('/api/traffic/current');
      console.log('交通 API 狀態:', trafficResponse.status);
      
      if (trafficResponse.ok) {
        const trafficResult = await trafficResponse.json();
        console.log('交通數據:', trafficResult);
        setTrafficData(trafficResult);
      }
      
      // 測試震波數據
      const shockwaveResponse = await fetch('/api/shockwave/active');
      console.log('震波 API 狀態:', shockwaveResponse.status);
      
      if (shockwaveResponse.ok) {
        const shockwaveResult = await shockwaveResponse.json();
        console.log('震波數據:', shockwaveResult);
        setShockwaveData(shockwaveResult);
      }
      
    } catch (err) {
      console.error('API 測試失敗:', err);
      setError(err instanceof Error ? err.message : '未知錯誤');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    testAPIs();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">簡單 API 測試</h1>
        
        <button
          onClick={testAPIs}
          disabled={loading}
          className="mb-6 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? '測試中...' : '重新測試 API'}
        </button>

        {error && (
          <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            <strong>錯誤: </strong>{error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 交通數據 */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">交通數據</h2>
            {trafficData ? (
              <div>
                <p className="text-green-600 mb-2">✅ 成功載入</p>
                <p>站點數量: {trafficData.stations ? trafficData.stations.length : 0}</p>
                <p>更新時間: {trafficData.last_updated}</p>
                {trafficData.stations && trafficData.stations.length > 0 && (
                  <div className="mt-4">
                    <h3 className="font-medium mb-2">第一個站點:</h3>
                    <pre className="bg-gray-100 p-2 rounded text-sm">
                      {JSON.stringify(trafficData.stations[0], null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500">無數據</p>
            )}
          </div>

          {/* 震波數據 */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">震波數據</h2>
            {shockwaveData ? (
              <div>
                <p className="text-green-600 mb-2">✅ 成功載入</p>
                <p>震波數量: {shockwaveData.shockwaves ? shockwaveData.shockwaves.length : 0}</p>
                <p>更新時間: {shockwaveData.last_updated}</p>
                {shockwaveData.shockwaves && shockwaveData.shockwaves.length > 0 && (
                  <div className="mt-4">
                    <h3 className="font-medium mb-2">第一個震波:</h3>
                    <pre className="bg-gray-100 p-2 rounded text-sm">
                      {JSON.stringify(shockwaveData.shockwaves[0], null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500">無數據</p>
            )}
          </div>
        </div>

        {/* 控制台日誌提示 */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-medium text-blue-800 mb-2">💡 調試提示</h3>
          <p className="text-blue-700 text-sm">
            請打開瀏覽器開發者工具（F12）查看控制台日誌，以獲取更詳細的API請求信息。
          </p>
        </div>
      </div>
    </div>
  );
};

export default SimpleTest;