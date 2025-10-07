import { NextRequest, NextResponse } from 'next/server';

/**
 * RAG Chat API Route
 * 連接到 Ollama 服務進行 AI 對話
 */
export async function POST(request: NextRequest) {
  console.log('🔵 RAG Chat API 被呼叫');

  try {
    const body = await request.json();
    console.log('📥 收到請求 body:', {
      hasMessage: !!body.message,
      hasTrafficData: !!body.traffic_data,
      hasShockwaveData: !!body.shockwave_data,
      hasUserLocation: !!body.user_location
    });

    const { message, traffic_data, shockwave_data, user_location, use_rag = true } = body;

    if (!message) {
      console.error('❌ 訊息為空');
      return NextResponse.json(
        { error: '訊息不能為空' },
        { status: 400 }
      );
    }

    // 從環境變數取得 Ollama URL (優先使用 NEXT_PUBLIC_)
    const ollamaUrl = process.env.NEXT_PUBLIC_OLLAMA_URL || process.env.OLLAMA_URL || 'http://localhost:11434';
    const model = 'qwen2.5:7b';

    console.log('🔧 使用配置:', { ollamaUrl, model });

    // 建立詳細的提示詞
    let fullPrompt = buildPrompt(message, traffic_data, shockwave_data, user_location);

    console.log('🤖 發送請求到 Ollama:', {
      url: ollamaUrl,
      model,
      promptLength: fullPrompt.length,
      hasTrafficData: !!traffic_data,
      hasShockwaveData: !!shockwave_data,
      hasUserLocation: !!user_location
    });

    // 呼叫 Ollama API
    const ollamaResponse = await fetch(`${ollamaUrl}/api/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        prompt: fullPrompt,
        stream: false,
        options: {
          temperature: 0.7,
          num_predict: 1024,
        }
      })
    });

    if (!ollamaResponse.ok) {
      const errorText = await ollamaResponse.text();
      console.error('❌ Ollama API 錯誤:', ollamaResponse.status, errorText);

      return NextResponse.json(
        {
          error: 'Ollama 服務暫時無法使用',
          details: errorText,
          status: ollamaResponse.status
        },
        { status: 502 }
      );
    }

    const ollamaResult = await ollamaResponse.json();
    const aiResponse = ollamaResult.response || '抱歉，無法生成回應。';

    console.log('✅ Ollama 回應成功:', {
      responseLength: aiResponse.length,
      model: ollamaResult.model,
      done: ollamaResult.done
    });

    // 返回結果
    return NextResponse.json({
      response: aiResponse,
      model,
      confidence_score: 0.85,
      sources: use_rag ? ['交通知識庫', '即時數據'] : ['即時數據'],
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('❌ RAG Chat API 錯誤:', error);
    console.error('錯誤堆疊:', error instanceof Error ? error.stack : 'N/A');

    // 提供更詳細的錯誤訊息
    let errorMessage = '處理請求時發生錯誤';
    let errorDetails = '未知錯誤';

    if (error instanceof Error) {
      errorDetails = error.message;

      // 檢查是否是連接錯誤
      if (error.message.includes('fetch') || error.message.includes('ECONNREFUSED')) {
        errorMessage = '無法連接到 Ollama 服務';
        errorDetails = '請確認 Ollama 服務是否在 http://localhost:11434 運行';
      }
    }

    return NextResponse.json(
      {
        error: errorMessage,
        details: errorDetails,
        timestamp: new Date().toISOString()
      },
      { status: 500 }
    );
  }
}

/**
 * 建立完整的提示詞
 */
function buildPrompt(
  userMessage: string,
  trafficData: any,
  shockwaveData: any,
  userLocation: any
): string {
  try {
    let prompt = `你是一個專業的台灣高速公路交通資訊助手。請用繁體中文回答以下問題。\n\n`;

    // 加入使用者位置資訊
    if (userLocation && typeof userLocation.lat === 'number' && typeof userLocation.lng === 'number') {
      prompt += `【使用者位置】\n`;
      prompt += `緯度: ${userLocation.lat.toFixed(4)}, 經度: ${userLocation.lng.toFixed(4)}\n\n`;
    }

  // 加入交通數據
  if (trafficData?.stations && trafficData.stations.length > 0) {
    const avgSpeed = trafficData.stations.reduce((sum: number, s: any) => sum + (s.speed || 0), 0) / trafficData.stations.length;
    const congestedCount = trafficData.stations.filter((s: any) => s.speed < 50).length;
    const smoothCount = trafficData.stations.filter((s: any) => s.speed >= 80).length;

    prompt += `【即時交通數據】\n`;
    prompt += `- 監測站點總數: ${trafficData.stations.length} 個\n`;
    prompt += `- 平均車速: ${avgSpeed.toFixed(1)} km/h\n`;
    prompt += `- 順暢站點: ${smoothCount} 個 (車速 ≥80 km/h)\n`;
    prompt += `- 壅塞站點: ${congestedCount} 個 (車速 <50 km/h)\n\n`;
  }

  // 加入震波數據
  if (shockwaveData?.shockwaves && shockwaveData.shockwaves.length > 0) {
    prompt += `【交通震波警報】\n`;
    prompt += `檢測到 ${shockwaveData.shockwaves.length} 個交通震波事件:\n`;

    shockwaveData.shockwaves.slice(0, 3).forEach((shock: any, index: number) => {
      prompt += `\n震波 ${index + 1}:\n`;
      prompt += `- 位置: ${shock.location_name || shock.station_name || '未知'}\n`;
      prompt += `- 座標: ${shock.latitude?.toFixed(4) || 'N/A'}, ${shock.longitude?.toFixed(4) || 'N/A'}\n`;
      prompt += `- 嚴重程度: ${shock.intensity || 'N/A'}/10\n`;
      prompt += `- 持續時間: ${shock.shock_duration || 'N/A'} 分鐘\n`;
      prompt += `- 影響範圍: 半徑 ${shock.affected_area || 'N/A'} 公里\n`;
    });
    prompt += `\n`;
  }

    // 加入使用者問題
    prompt += `【使用者問題】\n${userMessage}\n\n`;

    // 加入回答指引
    prompt += `【回答要求】\n`;
    prompt += `1. 請基於以上實際監測資料提供專業的台灣本土化駕駛建議\n`;
    prompt += `2. 回答要準確、具體，包括詳細的路線規劃和行駛指引\n`;
    prompt += `3. 如果有震波警報，請特別說明如何應對\n`;
    prompt += `4. 提供有用的補充資訊和注意事項\n`;
    prompt += `5. 回答要結構化且易於理解\n`;
    prompt += `6. 使用繁體中文回答\n\n`;
    prompt += `請開始回答:\n`;

    return prompt;
  } catch (error) {
    console.error('❌ buildPrompt 錯誤:', error);
    // 如果建立提示詞時發生錯誤，返回基本提示詞
    return `你是一個專業的台灣高速公路交通資訊助手。請用繁體中文回答以下問題：\n\n${userMessage}`;
  }
}

/**
 * 允許 GET 請求檢查服務狀態
 */
export async function GET() {
  const ollamaUrl = process.env.NEXT_PUBLIC_OLLAMA_URL || 'http://localhost:11434';

  try {
    const response = await fetch(`${ollamaUrl}/api/tags`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.ok) {
      const data = await response.json();
      return NextResponse.json({
        status: 'healthy',
        ollama_connected: true,
        available_models: data.models || [],
        timestamp: new Date().toISOString()
      });
    } else {
      return NextResponse.json({
        status: 'unavailable',
        ollama_connected: false,
        error: 'Ollama 服務無回應'
      }, { status: 502 });
    }
  } catch (error) {
    return NextResponse.json({
      status: 'error',
      ollama_connected: false,
      error: error instanceof Error ? error.message : '未知錯誤'
    }, { status: 500 });
  }
}
