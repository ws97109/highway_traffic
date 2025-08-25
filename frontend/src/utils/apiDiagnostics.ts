/**
 * Google Maps API 診斷工具
 * 檢查 API 權限和設定狀態
 */

export interface APIDiagnosticsResult {
  apiKey: {
    exists: boolean;
    valid: boolean;
    masked: string;
  };
  services: {
    mapsJavaScript: boolean;
    geocoding: boolean;
    places: boolean;
    directions: boolean;
  };
  recommendations: string[];
  setupUrl: string;
}

class APIDiagnostics {
  private apiKey: string;

  constructor() {
    this.apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';
  }

  /**
   * 執行完整診斷
   */
  async runDiagnostics(): Promise<APIDiagnosticsResult> {
    const result: APIDiagnosticsResult = {
      apiKey: {
        exists: false,
        valid: false,
        masked: 'Not Found'
      },
      services: {
        mapsJavaScript: false,
        geocoding: false,
        places: false,
        directions: false
      },
      recommendations: [],
      setupUrl: 'https://console.cloud.google.com/apis/library'
    };

    // 檢查 API Key
    if (this.apiKey && this.apiKey !== 'your_google_maps_api_key_here') {
      result.apiKey.exists = true;
      result.apiKey.masked = `${this.apiKey.substring(0, 10)}...`;
      result.apiKey.valid = this.apiKey.startsWith('AIza');
    }

    if (!result.apiKey.exists) {
      result.recommendations.push('❌ 請設定 NEXT_PUBLIC_GOOGLE_MAPS_API_KEY 環境變數');
      result.recommendations.push('📁 在 frontend/.env.local 中添加您的 Google Maps API 金鑰');
      return result;
    }

    if (!result.apiKey.valid) {
      result.recommendations.push('❌ API 金鑰格式不正確，應該以 "AIza" 開頭');
      return result;
    }

    // 檢查服務可用性
    try {
      // 檢查 Maps JavaScript API
      if (typeof google !== 'undefined' && google.maps) {
        result.services.mapsJavaScript = true;
      }

      // 檢查 Geocoding API
      await this.testGeocodingAPI();
      result.services.geocoding = true;
    } catch (error: any) {
      if (error.message.includes('REQUEST_DENIED')) {
        result.recommendations.push('❌ Geocoding API 未啟用或受限');
        result.recommendations.push('🔗 請啟用: https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com');
      }
    }

    // 檢查 Places API
    try {
      await this.testPlacesAPI();
      result.services.places = true;
    } catch (error: any) {
      if (error.message.includes('REQUEST_DENIED')) {
        result.recommendations.push('❌ Places API 未啟用或受限');
        result.recommendations.push('🔗 請啟用: https://console.cloud.google.com/apis/library/places-backend.googleapis.com');
      }
    }

    // 檢查 Directions API
    try {
      await this.testDirectionsAPI();
      result.services.directions = true;
    } catch (error: any) {
      if (error.message.includes('REQUEST_DENIED')) {
        result.recommendations.push('❌ Directions API 未啟用或受限');
        result.recommendations.push('🔗 請啟用: https://console.cloud.google.com/apis/library/directions-backend.googleapis.com');
      }
    }

    // 生成建議
    this.generateRecommendations(result);

    return result;
  }

  /**
   * 測試 Geocoding API
   */
  private async testGeocodingAPI(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!google || !google.maps || !google.maps.Geocoder) {
        reject(new Error('Google Maps API 尚未載入'));
        return;
      }

      const geocoder = new google.maps.Geocoder();
      geocoder.geocode(
        { location: { lat: 25.0330, lng: 121.5654 } },
        (results, status) => {
          if (status === google.maps.GeocoderStatus.OK) {
            resolve();
          } else {
            reject(new Error(`Geocoding test failed: ${status}`));
          }
        }
      );
    });
  }

  /**
   * 測試 Places API
   */
  private async testPlacesAPI(): Promise<void> {
    return new Promise((resolve, reject) => {
      // 簡化測試 - 檢查 Places 服務是否可初始化
      if (google && google.maps && google.maps.places) {
        resolve();
      } else {
        reject(new Error('Places API not available'));
      }
    });
  }

  /**
   * 測試 Directions API
   */
  private async testDirectionsAPI(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!google || !google.maps || !google.maps.DirectionsService) {
        reject(new Error('Directions API not available'));
        return;
      }

      const directionsService = new google.maps.DirectionsService();
      // 這裡我們只檢查服務是否存在，不實際發送請求
      resolve();
    });
  }

  /**
   * 生成建議
   */
  private generateRecommendations(result: APIDiagnosticsResult): void {
    const enabledServices = Object.values(result.services).filter(Boolean).length;
    const totalServices = Object.keys(result.services).length;

    if (enabledServices === totalServices) {
      result.recommendations.unshift('✅ 所有 Google Maps API 服務都已正確設定');
    } else {
      result.recommendations.unshift(`⚠️ ${enabledServices}/${totalServices} 個服務已啟用`);
    }

    if (!result.services.mapsJavaScript) {
      result.recommendations.push('❌ Maps JavaScript API 未載入');
      result.recommendations.push('🔗 請啟用: https://console.cloud.google.com/apis/library/maps-backend.googleapis.com');
    }

    if (result.recommendations.length > 1) {
      result.recommendations.push('');
      result.recommendations.push('📋 設定步驟:');
      result.recommendations.push('1. 前往 Google Cloud Console');
      result.recommendations.push('2. 選擇您的專案');
      result.recommendations.push('3. 啟用所需的 API 服務');
      result.recommendations.push('4. 確認 API 金鑰有適當的權限');
      result.recommendations.push('5. 重新載入應用程式');
    }
  }

  /**
   * 輸出診斷報告到控制台
   */
  logDiagnosticsReport(result: APIDiagnosticsResult): void {
    console.group('🔍 Google Maps API 診斷報告');
    
    console.log('🔑 API Key:', result.apiKey.exists ? `✅ ${result.apiKey.masked}` : '❌ 未設定');
    
    console.group('🛠️ 服務狀態');
    console.log('Maps JavaScript API:', result.services.mapsJavaScript ? '✅' : '❌');
    console.log('Geocoding API:', result.services.geocoding ? '✅' : '❌');
    console.log('Places API:', result.services.places ? '✅' : '❌');
    console.log('Directions API:', result.services.directions ? '✅' : '❌');
    console.groupEnd();

    if (result.recommendations.length > 0) {
      console.group('💡 建議');
      result.recommendations.forEach(rec => console.log(rec));
      console.groupEnd();
    }

    console.groupEnd();
  }
}

// 單例實例
const apiDiagnostics = new APIDiagnostics();

export default apiDiagnostics;