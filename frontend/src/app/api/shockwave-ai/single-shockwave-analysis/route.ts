import { NextRequest, NextResponse } from 'next/server';

/**
 * Single Shockwave AI Analysis API Route
 * 提供單一震波的專業分析
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { user_location, shockwave } = body;

    if (!user_location || !shockwave) {
      return NextResponse.json(
        { error: '缺少必要參數' },
        { status: 400 }
      );
    }

    // 將單個震波轉換為陣列格式，以重用現有分析邏輯
    const shockwaves = [shockwave];

    // 從環境變數取得 Ollama URL
    const ollamaUrl = process.env.NEXT_PUBLIC_OLLAMA_URL || 'http://localhost:11434';
    const model = 'qwen2.5:7b';

    // 計算使用者與震波的距離
    const distance = calculateDistance(
      user_location.lat,
      user_location.lng,
      shockwave.latitude,
      shockwave.longitude
    );

    // 建立震波分析提示詞
    const analysisPrompt = buildSingleShockwaveAnalysisPrompt(user_location, shockwave, distance);

    console.log('🚨 發送單震波分析請求到 Ollama:', {
      url: ollamaUrl,
      model,
      shockwaveLocation: shockwave.location_name,
      distance: distance.toFixed(2) + ' km',
      userLocation: user_location
    });

    // 呼叫 Ollama API
    const ollamaResponse = await fetch(`${ollamaUrl}/api/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        prompt: analysisPrompt,
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
          details: errorText
        },
        { status: 502 }
      );
    }

    const ollamaResult = await ollamaResponse.json();
    const aiAnalysis = ollamaResult.response || '抱歉，無法生成分析。';

    console.log('✅ 單震波分析完成:', {
      responseLength: aiAnalysis.length,
      model: ollamaResult.model,
      distance: distance.toFixed(2) + ' km'
    });

    // 分析震波風險等級
    const riskLevel = calculateRiskLevel(shockwaves, user_location);

    // 生成建議
    const recommendations = generateRecommendations(shockwaves, user_location, riskLevel);

    // 生成摘要
    const summary = generateSummary(shockwaves, riskLevel);

    return NextResponse.json({
      risk_level: riskLevel,
      summary,
      ai_analysis: aiAnalysis,
      recommendations,
      distance: distance.toFixed(2),
      shockwave_count: 1,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('❌ Single Shockwave AI Analysis API 錯誤:', error);

    return NextResponse.json(
      {
        error: '處理請求時發生錯誤',
        details: error instanceof Error ? error.message : '未知錯誤'
      },
      { status: 500 }
    );
  }
}

/**
 * 建立單震波分析提示詞
 */
function buildSingleShockwaveAnalysisPrompt(
  userLocation: any,
  shockwave: any,
  distance: number
): string {
  let prompt = `你是台灣高速公路交通震波專家，負責分析交通震波對駕駛人的影響並提供專業建議。請用繁體中文進行分析。\n\n`;

  // 使用者位置
  prompt += `【駕駛人位置】\n`;
  prompt += `緯度: ${userLocation.lat.toFixed(4)}, 經度: ${userLocation.lng.toFixed(4)}\n\n`;

  // 震波詳細資訊
  prompt += `【交通震波資訊】\n`;
  prompt += `位置: ${shockwave.location_name || '未知位置'}\n`;
  prompt += `座標: (${shockwave.latitude?.toFixed(4) || 'N/A'}, ${shockwave.longitude?.toFixed(4) || 'N/A'})\n`;
  prompt += `與駕駛人距離: ${distance.toFixed(2)} 公里\n`;
  prompt += `嚴重程度: ${(shockwave.intensity / 10).toFixed(1)}/10\n`;
  prompt += `速度下降: ${shockwave.speed_drop || 'N/A'} km/h\n`;
  prompt += `持續時間: ${shockwave.shock_duration || 'N/A'} 分鐘\n`;
  prompt += `影響範圍: 半徑 ${shockwave.affected_area || 'N/A'} 公里\n`;
  prompt += `傳播速度: ${shockwave.propagation_speed || 'N/A'} km/h\n\n`;

  // 分析要求
  prompt += `【分析任務】\n`;
  prompt += `請基於以上震波數據，提供簡潔但實用的專業分析（3-5句話）:\n\n`;
  prompt += `1. 🚨 風險評估 - 這個震波對我的影響程度\n`;
  prompt += `2. 🛣️ 行駛建議 - 我應該如何應對（減速/改道/延遲出發）\n`;
  prompt += `3. ⏰ 時間預估 - 如果繼續前進，大約何時會遇到震波影響\n\n`;
  prompt += `請提供簡潔實用的建議（使用繁體中文，不超過200字）:\n`;

  return prompt;
}

/**
 * 計算兩點之間的距離 (Haversine公式)
 */
function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371; // 地球半徑 (公里)
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * 計算風險等級
 */
function calculateRiskLevel(shockwaves: any[], userLocation: any): 'low' | 'medium' | 'high' {
  let maxRisk = 0;

  for (const shock of shockwaves) {
    const distance = calculateDistance(
      userLocation.lat,
      userLocation.lng,
      shock.latitude,
      shock.longitude
    );

    const intensity = (shock.intensity || 50) / 10; // 轉換為 0-10 範圍
    const affectedArea = shock.affected_area || 5;

    // 計算風險分數
    let riskScore = 0;

    // 距離因素 (距離越近風險越高)
    if (distance < affectedArea) {
      riskScore += 40;
    } else if (distance < affectedArea * 2) {
      riskScore += 20;
    } else if (distance < affectedArea * 3) {
      riskScore += 10;
    }

    // 強度因素
    riskScore += intensity * 4;

    // 持續時間因素
    const duration = shock.shock_duration || 0;
    if (duration > 30) {
      riskScore += 20;
    } else if (duration > 15) {
      riskScore += 10;
    }

    maxRisk = Math.max(maxRisk, riskScore);
  }

  if (maxRisk >= 70) return 'high';
  if (maxRisk >= 40) return 'medium';
  return 'low';
}

interface Recommendation {
  type: string;
  priority: string;
  title: string;
  description: string;
  action_time: string;
}

/**
 * 生成建議
 */
function generateRecommendations(
  shockwaves: any[],
  userLocation: any,
  riskLevel: string
): Recommendation[] {
  const recommendations: Recommendation[] = [];

  // 找出最近的震波
  const nearestShock = shockwaves
    .map(shock => ({
      ...shock,
      distance: calculateDistance(
        userLocation.lat,
        userLocation.lng,
        shock.latitude,
        shock.longitude
      )
    }))
    .sort((a, b) => a.distance - b.distance)[0];

  // 基於風險等級的基本建議
  if (riskLevel === 'high') {
    recommendations.push({
      type: 'route_change',
      priority: 'urgent',
      title: '建議更換路線',
      description: '前方有高風險交通震波，強烈建議選擇替代路線或延後出發。',
      action_time: '立即'
    });

    recommendations.push({
      type: 'time_delay',
      priority: 'high',
      title: '延後出發',
      description: '建議延後 30-60 分鐘出發，等待震波消散。',
      action_time: '30-60 分鐘後'
    });
  } else if (riskLevel === 'medium') {
    recommendations.push({
      type: 'speed_adjustment',
      priority: 'medium',
      title: '降低車速',
      description: '前方有中等強度震波，建議降低車速並保持安全距離。',
      action_time: '接近震波區域前 5 公里'
    });

    recommendations.push({
      type: 'rest_stop',
      priority: 'medium',
      title: '考慮在休息站暫停',
      description: '可在最近的休息站休息 15-20 分鐘，等待交通狀況改善。',
      action_time: '到達下一個休息站'
    });
  } else {
    recommendations.push({
      type: 'monitor',
      priority: 'low',
      title: '持續監控',
      description: '目前風險較低，但請持續關注交通資訊更新。',
      action_time: '行駛過程中'
    });
  }

  // 基於最近震波的具體建議
  if (nearestShock && nearestShock.distance < (nearestShock.affected_area || 5) * 2) {
    const intensity = (nearestShock.intensity || 50) / 10;
    recommendations.push({
      type: 'specific_warning',
      priority: riskLevel === 'high' ? 'urgent' : 'high',
      title: `${nearestShock.location_name || '前方'} 震波警告`,
      description: `距離您約 ${nearestShock.distance.toFixed(1)} 公里處有交通震波，強度 ${intensity.toFixed(1)}/10。建議提前減速並準備應對。`,
      action_time: '前方 ' + nearestShock.distance.toFixed(1) + ' 公里'
    });
  }

  return recommendations;
}

/**
 * 生成摘要
 */
function generateSummary(shockwaves: any[], riskLevel: string): string {
  const shock = shockwaves[0];
  const intensity = (shock.intensity || 50) / 10;

  let summary = `檢測到交通震波事件，`;

  if (riskLevel === 'high') {
    summary += `風險等級為「高」，強度 ${intensity.toFixed(1)}/10。強烈建議更換路線或延後出發。`;
  } else if (riskLevel === 'medium') {
    summary += `風險等級為「中」，強度 ${intensity.toFixed(1)}/10。建議降低車速並保持警覺。`;
  } else {
    summary += `風險等級為「低」，強度 ${intensity.toFixed(1)}/10。可正常行駛，但請持續關注路況。`;
  }

  return summary;
}
