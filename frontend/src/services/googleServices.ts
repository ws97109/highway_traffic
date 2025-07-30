/**
 * Google Cloud 服務整合層
 * 包含 Maps API, Places API, Directions API 等服務
 */

// 類型定義
export interface GeocodeResult {
  address: string;
  lat: number;
  lng: number;
  placeId?: string;
  types?: string[];
}

export interface PlaceSearchResult {
  placeId: string;
  name: string;
  address: string;
  lat: number;
  lng: number;
  rating?: number;
  types: string[];
}

export interface RouteResult {
  distance: {
    text: string;
    value: number; // 公尺
  };
  duration: {
    text: string;
    value: number; // 秒
  };
  steps: RouteStep[];
  polyline: string;
}

export interface RouteStep {
  instruction: string;
  distance: {
    text: string;
    value: number;
  };
  duration: {
    text: string;
    value: number;
  };
  startLocation: {
    lat: number;
    lng: number;
  };
  endLocation: {
    lat: number;
    lng: number;
  };
}

export interface TrafficInfo {
  distance: number;
  duration: number;
  durationInTraffic: number;
  trafficCondition: 'light' | 'moderate' | 'heavy' | 'severe';
}

class GoogleServicesClass {
  private apiKey: string;
  private placesService: google.maps.places.PlacesService | null = null;
  private directionsService: google.maps.DirectionsService | null = null;
  private geocoder: google.maps.Geocoder | null = null;

  constructor() {
    this.apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';
    
    // 如果沒有 API 金鑰，警告用戶
    if (!this.apiKey || this.apiKey === 'your_google_maps_api_key_here') {
      console.warn('⚠️ Google Maps API 金鑰未設定或為預設值');
      console.warn('請在 .env.local 中設定正確的 NEXT_PUBLIC_GOOGLE_MAPS_API_KEY');
    }
  }

  /**
   * 初始化 Google Services
   */
  async initialize(): Promise<boolean> {
    try {
      if (!this.apiKey || this.apiKey === 'your_google_maps_api_key_here') {
        console.warn('⚠️ Google Maps API 金鑰未設定，將使用模擬模式');
        return false;
      }

      // 等待 Google Maps API 載入
      if (typeof google === 'undefined') {
        console.warn('⚠️ Google Maps API 尚未載入，將使用模擬模式');
        return false;
      }

      // 初始化服務
      this.geocoder = new google.maps.Geocoder();
      this.directionsService = new google.maps.DirectionsService();
      
      // Places Service 需要地圖實例
      const dummyDiv = document.createElement('div');
      const dummyMap = new google.maps.Map(dummyDiv);
      this.placesService = new google.maps.places.PlacesService(dummyMap);

      console.log('✅ Google Services 初始化成功');
      return true;
    } catch (error) {
      console.warn('⚠️ Google Services 初始化失敗，將使用模擬模式:', error);
      return false;
    }
  }

  /**
   * 地址轉座標 (Geocoding)
   */
  async geocodeAddress(address: string): Promise<GeocodeResult[]> {
    if (!this.geocoder) {
      throw new Error('Geocoder 未初始化');
    }

    return new Promise((resolve, reject) => {
      this.geocoder!.geocode(
        { 
          address,
          region: 'TW', // 台灣區域偏好
          language: 'zh-TW'
        },
        (results, status) => {
          if (status === google.maps.GeocoderStatus.OK && results) {
            const geocodeResults: GeocodeResult[] = results.map(result => ({
              address: result.formatted_address,
              lat: result.geometry.location.lat(),
              lng: result.geometry.location.lng(),
              placeId: result.place_id,
              types: result.types,
            }));
            resolve(geocodeResults);
          } else {
            reject(new Error(`地址轉座標失敗: ${status}`));
          }
        }
      );
    });
  }

  /**
   * 座標轉地址 (Reverse Geocoding)
   */
  async reverseGeocode(lat: number, lng: number): Promise<GeocodeResult[]> {
    if (!this.geocoder) {
      throw new Error('Geocoder 未初始化');
    }

    return new Promise((resolve, reject) => {
      this.geocoder!.geocode(
        { 
          location: { lat, lng },
          language: 'zh-TW'
        },
        (results, status) => {
          if (status === google.maps.GeocoderStatus.OK && results) {
            const geocodeResults: GeocodeResult[] = results.map(result => ({
              address: result.formatted_address,
              lat: result.geometry.location.lat(),
              lng: result.geometry.location.lng(),
              placeId: result.place_id,
              types: result.types,
            }));
            resolve(geocodeResults);
          } else {
            reject(new Error(`座標轉地址失敗: ${status}`));
          }
        }
      );
    });
  }

  /**
   * 地點搜尋
   */
  async searchPlaces(
    query: string, 
    location?: { lat: number; lng: number },
    radius: number = 50000
  ): Promise<PlaceSearchResult[]> {
    if (!this.placesService) {
      throw new Error('Places Service 未初始化');
    }

    return new Promise((resolve, reject) => {
      const request: google.maps.places.TextSearchRequest = {
        query,
        language: 'zh-TW',
        region: 'TW',
      };

      if (location) {
        request.location = new google.maps.LatLng(location.lat, location.lng);
        request.radius = radius;
      }

      this.placesService!.textSearch(request, (results, status) => {
        if (status === google.maps.places.PlacesServiceStatus.OK && results) {
          const placeResults: PlaceSearchResult[] = results.map(place => ({
            placeId: place.place_id!,
            name: place.name!,
            address: place.formatted_address!,
            lat: place.geometry!.location!.lat(),
            lng: place.geometry!.location!.lng(),
            rating: place.rating,
            types: place.types!,
          }));
          resolve(placeResults);
        } else {
          reject(new Error(`地點搜尋失敗: ${status}`));
        }
      });
    });
  }

  /**
   * 路線規劃
   */
  async getDirections(
    origin: string | { lat: number; lng: number },
    destination: string | { lat: number; lng: number },
    waypoints?: Array<string | { lat: number; lng: number }>,
    optimizeWaypoints: boolean = false
  ): Promise<RouteResult> {
    if (!this.directionsService) {
      throw new Error('Directions Service 未初始化');
    }

    return new Promise((resolve, reject) => {
      const request: google.maps.DirectionsRequest = {
        origin: typeof origin === 'string' ? origin : new google.maps.LatLng(origin.lat, origin.lng),
        destination: typeof destination === 'string' ? destination : new google.maps.LatLng(destination.lat, destination.lng),
        travelMode: google.maps.TravelMode.DRIVING,
        unitSystem: google.maps.UnitSystem.METRIC,
        language: 'zh-TW',
        region: 'TW',
        drivingOptions: {
          departureTime: new Date(),
          trafficModel: google.maps.TrafficModel.BEST_GUESS,
        },
      };

      if (waypoints && waypoints.length > 0) {
        request.waypoints = waypoints.map(point => ({
          location: typeof point === 'string' ? point : new google.maps.LatLng(point.lat, point.lng),
          stopover: true,
        }));
        request.optimizeWaypoints = optimizeWaypoints;
      }

      this.directionsService!.route(request, (result, status) => {
        if (status === google.maps.DirectionsStatus.OK && result) {
          const route = result.routes[0];
          const leg = route.legs[0];
          
          const routeResult: RouteResult = {
            distance: {
              text: leg.distance!.text,
              value: leg.distance!.value,
            },
            duration: {
              text: leg.duration!.text,
              value: leg.duration!.value,
            },
            steps: leg.steps.map(step => ({
              instruction: step.instructions,
              distance: {
                text: step.distance!.text,
                value: step.distance!.value,
              },
              duration: {
                text: step.duration!.text,
                value: step.duration!.value,
              },
              startLocation: {
                lat: step.start_location.lat(),
                lng: step.start_location.lng(),
              },
              endLocation: {
                lat: step.end_location.lat(),
                lng: step.end_location.lng(),
              },
            })),
            polyline: route.overview_polyline,
          };

          resolve(routeResult);
        } else {
          reject(new Error(`路線規劃失敗: ${status}`));
        }
      });
    });
  }

  /**
   * 取得即時交通資訊
   */
  async getTrafficInfo(
    origin: { lat: number; lng: number },
    destination: { lat: number; lng: number }
  ): Promise<TrafficInfo> {
    const route = await this.getDirections(origin, destination);
    
    // 模擬交通狀況判斷 (實際應用中可以使用更精確的 API)
    const baseTime = route.duration.value;
    const estimatedTrafficTime = baseTime * 1.2; // 假設交通影響增加 20%
    
    let trafficCondition: TrafficInfo['trafficCondition'] = 'light';
    const trafficRatio = estimatedTrafficTime / baseTime;
    
    if (trafficRatio > 2) {
      trafficCondition = 'severe';
    } else if (trafficRatio > 1.5) {
      trafficCondition = 'heavy';
    } else if (trafficRatio > 1.2) {
      trafficCondition = 'moderate';
    }

    return {
      distance: route.distance.value,
      duration: baseTime,
      durationInTraffic: estimatedTrafficTime,
      trafficCondition,
    };
  }

  /**
   * 計算兩點間距離
   */
  calculateDistance(
    point1: { lat: number; lng: number },
    point2: { lat: number; lng: number }
  ): number {
    const R = 6371; // 地球半徑 (公里)
    const dLat = this.toRadians(point2.lat - point1.lat);
    const dLng = this.toRadians(point2.lng - point1.lng);
    
    const a = 
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRadians(point1.lat)) * Math.cos(this.toRadians(point2.lat)) *
      Math.sin(dLng / 2) * Math.sin(dLng / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  private toRadians(degrees: number): number {
    return degrees * (Math.PI / 180);
  }

  /**
   * 檢查 API 金鑰是否有效
   */
  async validateApiKey(): Promise<boolean> {
    try {
      await this.geocodeAddress('台北車站');
      return true;
    } catch (error) {
      console.error('API 金鑰驗證失敗:', error);
      return false;
    }
  }
}

// 單例模式
export const GoogleServices = new GoogleServicesClass();
export default GoogleServices;