import React, { useState, useEffect } from 'react';

const APITestPage: React.FC = () => {
  const [testResults, setTestResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const testEndpoints = [
    { name: '交通資料', url: '/api/traffic/current' },
    { name: '震波資料', url: '/api/shockwave/active' },
    { name: '預測資料', url: '/api/prediction/traffic' },
    { name: 'RAG狀態', url: '/api/smart/rag-status' },
  ];

  const runTests = async () => {
    setLoading(true);
    const results = [];

    for (const endpoint of testEndpoints) {
      const startTime = Date.now();
      try {
        console.log(`測試 ${endpoint.name}: ${endpoint.url}`);
        
        const response = await fetch(endpoint.url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        const responseTime = Date.now() - startTime;
        const data = await response.json();

        results.push({
          name: endpoint.name,
          url: endpoint.url,
          status: response.ok ? 'success' : 'error',
          statusCode: response.status,
          responseTime,
          dataSize: JSON.stringify(data).length,
          data: data,
          error: response.ok ? null : `HTTP ${response.status}`
        });

        console.log(`✅ ${endpoint.name} 成功:`, response.status, data);

      } catch (error: any) {
        const responseTime = Date.now() - startTime;
        results.push({
          name: endpoint.name,
          url: endpoint.url,
          status: 'error',
          statusCode: 0,
          responseTime,
          dataSize: 0,
          data: null,
          error: error.message
        });

        console.error(`❌ ${endpoint.name} 失敗:`, error);
      }
    }

    setTestResults(results);
    setLoading(false);
  };

  useEffect(() => {
    runTests();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">API 連接測試</h1>
        
        <div className="mb-6">
          <button
            onClick={runTests}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? '測試中...' : '重新測試'}
          </button>
        </div>

        <div className="grid gap-6">
          {testResults.map((result, index) => (
            <div
              key={index}
              className={`bg-white rounded-lg shadow p-6 border-l-4 ${
                result.status === 'success' ? 'border-green-500' : 'border-red-500'
              }`}
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">
                  {result.name}
                </h2>
                <div className="flex items-center space-x-4">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    result.status === 'success' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {result.status === 'success' ? '成功' : '失敗'}
                  </span>
                  <span className="text-gray-500 text-sm">
                    {result.responseTime}ms
                  </span>
                </div>
              </div>

              <div className="space-y-2 text-sm">
                <div><strong>URL:</strong> <code className="bg-gray-100 px-2 py-1 rounded">{result.url}</code></div>
                <div><strong>狀態碼:</strong> {result.statusCode}</div>
                <div><strong>資料大小:</strong> {result.dataSize} bytes</div>
                
                {result.error && (
                  <div className="bg-red-50 p-3 rounded">
                    <strong className="text-red-800">錯誤:</strong>
                    <div className="text-red-700">{result.error}</div>
                  </div>
                )}

                {result.data && (
                  <div className="mt-4">
                    <strong>回應資料:</strong>
                    <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto max-h-40 mt-2">
                      {JSON.stringify(result.data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {testResults.length === 0 && !loading && (
          <div className="text-center text-gray-500 py-12">
            點擊「重新測試」開始 API 連接測試
          </div>
        )}
      </div>
    </div>
  );
};

export default APITestPage;