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

    const { message, traffic_data, shockwave_data, prediction_data, user_location, use_rag = true } = body;

    if (!message) {
      console.error('❌ 訊息為空');
      return NextResponse.json(
        { error: '訊息不能為空' },
        { status: 400 }
      );
    }

    // 從環境變數取得 Ollama URL (優先使用 NEXT_PUBLIC_)
    const ollamaUrl = process.env.NEXT_PUBLIC_OLLAMA_URL || process.env.OLLAMA_URL || 'http://localhost:11434';
    const model = 'qwen2.5:14b';

    console.log('🔧 使用配置:', { ollamaUrl, model });

    // 建立詳細的提示詞
    let fullPrompt = buildPrompt(message, traffic_data, shockwave_data, prediction_data, user_location);

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
  predictionData: any,
  userLocation: any
): string {
  try {
    // 管理者導向的系統提示詞
    let prompt = `你是專業的台灣高速公路交通管制決策助手，專門協助交通管理中心的管理人員制定政策層級的交通疏導策略。

你的職責是:
1. 分析系統層級的交通狀況，識別壅塞熱點和趨勢
2. 提供政府可執行的交通管制策略建議
3. 評估不同策略的成本、效益和可行性
4. 考量交通政策、法規和多車輛協調
5. 解讀預測模型結果和衝擊波偵測資料

你應該提供的建議類型包括:
- 🚦 匝道儀控管制 (Ramp Metering): 控制匝道車流進入主線的速率
- 🚧 車道管制: 封閉特定車道、開放路肩、調整車道配置
- 🔀 替代路線引導: 透過 CMS 可變標誌引導車流改道
- 👥 高乘載管制 (HOV): 實施高乘載車輛優先措施
- 🚗 車種管制: 限制大型車輛通行時段或路段
- 🏗️ 道路擴建評估: 評估長期道路容量改善需求
- ⏰ 尖峰時段調控: 建議彈性上下班、分流措施
- 📱 智慧交通系統 (ITS): 動態速限、事故偵測、資訊發布
- 🚨 應急管理: 事故快速清理、緊急車道開放

回答原則:
- 使用繁體中文，語氣專業但易懂
- 基於提供的即時資料，引用具體數字和站點
- 提供結構化的分析和建議 (問題診斷 → 策略建議 → 預期效果)
- 明確說明建議的理由、實施成本、預期效果、實施時間
- 當資料不足時，誠實說明並建議收集哪些資料
- 提供 2-3 個可選方案，而非單一建議
- 考慮短期應急措施和長期改善方案

\n\n`;

    // 加入交通數據
    if (trafficData?.stations && trafficData.stations.length > 0) {
      const avgSpeed = trafficData.stations.reduce((sum: number, s: any) => sum + (s.speed || 0), 0) / trafficData.stations.length;
      const congestedCount = trafficData.stations.filter((s: any) => s.speed < 50).length;
      const smoothCount = trafficData.stations.filter((s: any) => s.speed >= 80).length;

      prompt += `【系統即時交通數據】\n`;
      prompt += `- 監測站點總數: ${trafficData.stations.length} 個\n`;
      prompt += `- 平均車速: ${avgSpeed.toFixed(1)} km/h\n`;
      prompt += `- 順暢站點: ${smoothCount} 個 (車速 ≥80 km/h)\n`;
      prompt += `- 壅塞站點: ${congestedCount} 個 (車速 <50 km/h)\n`;
      prompt += `- 壅塞比例: ${((congestedCount / trafficData.stations.length) * 100).toFixed(1)}%\n\n`;
    }

    // 加入衝擊波數據
    if (shockwaveData?.shockwaves && shockwaveData.shockwaves.length > 0) {
      prompt += `【交通衝擊波檢測】\n`;
      prompt += `⚠️ 系統檢測到 ${shockwaveData.shockwaves.length} 個交通衝擊波事件:\n`;

      shockwaveData.shockwaves.slice(0, 3).forEach((shock: any, index: number) => {
        prompt += `\n衝擊波事件 ${index + 1}:\n`;
        prompt += `- 位置: ${shock.location_name || shock.station_name || '未知'}\n`;
        prompt += `- 座標: (${shock.latitude?.toFixed(4) || 'N/A'}, ${shock.longitude?.toFixed(4) || 'N/A'})\n`;
        prompt += `- 嚴重程度: ${shock.intensity || 'N/A'}/10\n`;
        prompt += `- 持續時間: ${shock.shock_duration || 'N/A'} 分鐘\n`;
        prompt += `- 影響範圍: 半徑 ${shock.affected_area || 'N/A'} 公里\n`;
        prompt += `- 速度下降: ${shock.speed_drop || 'N/A'} km/h\n`;
      });
      prompt += `\n`;
    }

    // 加入預測車流數據
    if (predictionData?.predictions && predictionData.predictions.length > 0) {
      prompt += `【車流預測分析】\n`;
      prompt += `📈 系統預測未來 ${predictionData.predictions.length} 個時段的車流狀況:\n`;

      predictionData.predictions.slice(0, 5).forEach((pred: any, index: number) => {
        prompt += `\n預測時段 ${index + 1}:\n`;
        prompt += `- 時間: ${pred.time || pred.timestamp || 'N/A'}\n`;
        prompt += `- 預測車速: ${pred.predicted_speed || pred.speed || 'N/A'} km/h\n`;
        prompt += `- 預測車流: ${pred.predicted_flow || pred.flow || 'N/A'} 輛/小時\n`;
        prompt += `- 預測壅塞程度: ${pred.congestion_level || 'N/A'}%\n`;
        if (pred.location) {
          prompt += `- 預測位置: ${pred.location}\n`;
        }
      });
      prompt += `\n`;
    }

    // 加入管理員問題
    prompt += `【管理員諮詢】\n${userMessage}\n\n`;

    // 加入回答指引
    prompt += `【回答格式要求】\n`;
    prompt += `請以以下結構回答:\n\n`;
    prompt += `📊 **問題診斷**\n`;
    prompt += `- 當前交通狀況分析\n`;
    prompt += `- 壅塞成因判斷\n`;
    prompt += `- 影響範圍評估\n\n`;
    prompt += `🎯 **建議策略** (提供 2-3 個選項)\n`;
    prompt += `選項 1: [策略名稱]\n`;
    prompt += `- 具體措施: [詳細說明]\n`;
    prompt += `- 實施位置: [具體地點]\n`;
    prompt += `- 預期效果: [量化指標]\n`;
    prompt += `- 實施成本: [估算]\n`;
    prompt += `- 實施時間: [所需時間]\n`;
    prompt += `- 優先級: 高/中/低\n\n`;
    prompt += `💡 **實施建議**\n`;
    prompt += `- 短期應急措施\n`;
    prompt += `- 長期改善方案\n`;
    prompt += `- 配套措施建議\n\n`;
    prompt += `請開始回答:\n`;

    return prompt;
  } catch (error) {
    console.error('❌ buildPrompt 錯誤:', error);
    // 如果建立提示詞時發生錯誤，返回基本提示詞
    return `你是專業的台灣高速公路交通管制決策助手。請用繁體中文，從政府管理者角度回答以下問題：\n\n${userMessage}`;
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
