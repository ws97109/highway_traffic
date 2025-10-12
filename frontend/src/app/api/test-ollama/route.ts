import { NextResponse } from 'next/server';

/**
 * 簡單的 Ollama 測試端點
 * 用於診斷連接問題
 */
export async function GET() {
  const results: any = {
    timestamp: new Date().toISOString(),
    environment: {
      NEXT_PUBLIC_OLLAMA_URL: process.env.NEXT_PUBLIC_OLLAMA_URL,
      NODE_ENV: process.env.NODE_ENV,
    },
    tests: {}
  };

  try {
    const ollamaUrl = process.env.NEXT_PUBLIC_OLLAMA_URL || 'http://localhost:11434';

    console.log('🔍 測試 Ollama 連接:', ollamaUrl);

    // 測試 1: 檢查服務可用性
    try {
      const response = await fetch(`${ollamaUrl}/api/tags`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      results.tests.connectivity = {
        status: response.ok ? 'success' : 'failed',
        statusCode: response.status,
        url: `${ollamaUrl}/api/tags`
      };

      if (response.ok) {
        const data = await response.json();
        results.tests.connectivity.models = data.models?.map((m: any) => m.name) || [];
      } else {
        const errorText = await response.text();
        results.tests.connectivity.error = errorText;
      }
    } catch (error) {
      results.tests.connectivity = {
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
        details: 'Failed to connect to Ollama service'
      };
    }

    // 測試 2: 簡單生成測試
    if (results.tests.connectivity.status === 'success') {
      try {
        const generateResponse = await fetch(`${ollamaUrl}/api/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: 'qwen2.5:14b',
            prompt: '說"測試成功"',
            stream: false,
            options: {
              num_predict: 10
            }
          })
        });

        results.tests.generation = {
          status: generateResponse.ok ? 'success' : 'failed',
          statusCode: generateResponse.status
        };

        if (generateResponse.ok) {
          const data = await generateResponse.json();
          results.tests.generation.response = data.response;
          results.tests.generation.model = data.model;
        } else {
          const errorText = await generateResponse.text();
          results.tests.generation.error = errorText;
        }
      } catch (error) {
        results.tests.generation = {
          status: 'error',
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }

    // 判斷整體狀態
    const allSuccess = Object.values(results.tests).every(
      (test: any) => test.status === 'success'
    );

    return NextResponse.json({
      success: allSuccess,
      message: allSuccess ? 'All tests passed' : 'Some tests failed',
      ...results
    });

  } catch (error) {
    console.error('❌ 測試過程中發生錯誤:', error);

    return NextResponse.json({
      success: false,
      message: 'Test execution failed',
      error: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined,
      ...results
    }, { status: 500 });
  }
}
