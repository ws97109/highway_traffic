import { useState, useEffect, useCallback } from 'react';
import GoogleServices, { GeocodeResult, PlaceSearchResult, RouteResult } from '../services/googleServices';

// 基本地理區域判斷函數
const getApproximateLocation = (lat: number, lng: number): string => {
  // 台灣主要行政區域的大致範圍
  const regions = [
    // 新北市
    { name: '新北市淡水區', bounds: { north: 25.22, south: 25.15, east: 121.47, west: 121.41 } },
    { name: '新北市三重區', bounds: { north: 25.08, south: 25.04, east: 121.50, west: 121.47 } },
    { name: '新北市板橋區', bounds: { north: 25.02, south: 24.98, east: 121.47, west: 121.43 } },
    { name: '新北市中和區', bounds: { north: 25.00, south: 24.95, east: 121.52, west: 121.47 } },
    { name: '新北市永和區', bounds: { north: 25.02, south: 24.98, east: 121.52, west: 121.50 } },
    { name: '新北市新店區', bounds: { north: 25.00, south: 24.93, east: 121.55, west: 121.50 } },
    { name: '新北市土城區', bounds: { north: 24.98, south: 24.93, east: 121.47, west: 121.40 } },
    { name: '新北市蘆洲區', bounds: { north: 25.10, south: 25.07, east: 121.48, west: 121.45 } },
    { name: '新北市五股區', bounds: { north: 25.12, south: 25.07, east: 121.45, west: 121.41 } },
    { name: '新北市泰山區', bounds: { north: 25.07, south: 25.04, east: 121.43, west: 121.40 } },
    { name: '新北市林口區', bounds: { north: 25.12, south: 25.06, east: 121.40, west: 121.35 } },

    // 台北市
    { name: '台北市中正區', bounds: { north: 25.05, south: 25.03, east: 121.53, west: 121.51 } },
    { name: '台北市大同區', bounds: { north: 25.07, south: 25.04, east: 121.52, west: 121.50 } },
    { name: '台北市中山區', bounds: { north: 25.08, south: 25.05, east: 121.55, west: 121.52 } },
    { name: '台北市松山區', bounds: { north: 25.07, south: 25.04, east: 121.58, west: 121.55 } },
    { name: '台北市大安區', bounds: { north: 25.04, south: 25.01, east: 121.56, west: 121.53 } },
    { name: '台北市萬華區', bounds: { north: 25.04, south: 25.01, east: 121.51, west: 121.48 } },
    { name: '台北市信義區', bounds: { north: 25.05, south: 25.02, east: 121.58, west: 121.55 } },
    { name: '台北市士林區', bounds: { north: 25.12, south: 25.08, east: 121.55, west: 121.50 } },
    { name: '台北市北投區', bounds: { north: 25.15, south: 25.10, east: 121.53, west: 121.48 } },
    { name: '台北市內湖區', bounds: { north: 25.10, south: 25.06, east: 121.60, west: 121.55 } },
    { name: '台北市南港區', bounds: { north: 25.07, south: 25.03, east: 121.62, west: 121.58 } },
    { name: '台北市文山區', bounds: { north: 25.01, south: 24.97, east: 121.57, west: 121.53 } },

    // 桃園市
    { name: '桃園市桃園區', bounds: { north: 25.00, south: 24.95, east: 121.32, west: 121.28 } },
    { name: '桃園市中壢區', bounds: { north: 24.98, south: 24.93, east: 121.25, west: 121.20 } },
    { name: '桃園市平鎮區', bounds: { north: 24.95, south: 24.90, east: 121.25, west: 121.20 } },
    { name: '桃園市八德區', bounds: { north: 24.97, south: 24.92, east: 121.30, west: 121.25 } },

    // 新竹
    { name: '新竹市東區', bounds: { north: 24.82, south: 24.78, east: 120.98, west: 120.94 } },
    { name: '新竹市北區', bounds: { north: 24.85, south: 24.81, east: 120.97, west: 120.93 } },
    { name: '新竹市香山區', bounds: { north: 24.78, south: 24.74, east: 120.94, west: 120.90 } },
  ];

  // 尋找匹配的區域
  for (const region of regions) {
    const { bounds } = region;
    if (lat >= bounds.south && lat <= bounds.north &&
        lng >= bounds.west && lng <= bounds.east) {
      return region.name;
    }
  }

  // 如果沒有精確匹配，提供大致區域
  if (lat >= 25.15 && lat <= 25.22 && lng >= 121.40 && lng <= 121.50) {
    return '新北市淡水地區';
  } else if (lat >= 25.00 && lat <= 25.15 && lng >= 121.45 && lng <= 121.65) {
    return '台北都會區';
  } else if (lat >= 24.90 && lat <= 25.00 && lng >= 121.15 && lng <= 121.35) {
    return '桃園市';
  } else if (lat >= 24.70 && lat <= 24.85 && lng >= 120.90 && lng <= 121.00) {
    return '新竹地區';
  }

  // 最後備用：顯示座標
  return `位置 ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
};

// 使用者位置 Hook
export const useUserLocation = () => {
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [address, setAddress] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getCurrentLocation = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      if (!navigator.geolocation) {
        throw new Error('瀏覽器不支援地理位置服務');
      }

      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000, // 5分鐘快取
        });
      });

      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      
      setLocation({ lat, lng });

      // 取得地址 - 優雅地處理 Geocoding API 不可用的情況
      try {
        await GoogleServices.initialize();
        const results = await GoogleServices.reverseGeocode(lat, lng);
        if (results.length > 0) {
          setAddress(results[0].address);
        } else {
          // 如果沒有結果，使用基本地理區域判斷
          const approximateAddress = getApproximateLocation(lat, lng);
          setAddress(approximateAddress);
        }
      } catch (geocodeError: any) {
        console.warn('無法取得地址資訊:', geocodeError);

        // 提供更準確的備用地址
        const approximateAddress = getApproximateLocation(lat, lng);
        setAddress(approximateAddress);

        if (geocodeError.message && geocodeError.message.includes('REQUEST_DENIED')) {
          console.info('💡 提示: 啟用 Geocoding API 以顯示詳細地址');
        }
      }

    } catch (locationError: any) {
      let errorMessage = '無法取得位置';
      
      if (locationError.code === 1) {
        errorMessage = '使用者拒絕位置存取';
      } else if (locationError.code === 2) {
        errorMessage = '位置資訊無法取得';
      } else if (locationError.code === 3) {
        errorMessage = '位置請求逾時';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const setCustomLocation = useCallback(async (lat: number, lng: number) => {
    setLocation({ lat, lng });

    try {
      await GoogleServices.initialize();
      const results = await GoogleServices.reverseGeocode(lat, lng);
      if (results.length > 0) {
        setAddress(results[0].address);
      } else {
        // 如果沒有結果，使用基本地理區域判斷
        const approximateAddress = getApproximateLocation(lat, lng);
        setAddress(approximateAddress);
      }
    } catch (error) {
      console.warn('無法取得地址資訊:', error);
      // 提供更準確的備用地址
      const approximateAddress = getApproximateLocation(lat, lng);
      setAddress(approximateAddress);
    }
  }, []);

  return {
    location,
    address,
    loading,
    error,
    getCurrentLocation,
    setCustomLocation,
  };
};

// 地址搜尋 Hook
export const useAddressSearch = () => {
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchAddress = useCallback(async (address: string) => {
    if (!address.trim()) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await GoogleServices.initialize();
      const geocodeResults = await GoogleServices.geocodeAddress(address);
      setResults(geocodeResults);
    } catch (searchError: any) {
      setError(searchError.message || '搜尋失敗');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setResults([]);
    setError(null);
  }, []);

  return {
    results,
    loading,
    error,
    searchAddress,
    clearResults,
  };
};

// 地點搜尋 Hook
export const usePlaceSearch = () => {
  const [places, setPlaces] = useState<PlaceSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchPlaces = useCallback(async (
    query: string,
    location?: { lat: number; lng: number },
    radius: number = 50000
  ) => {
    if (!query.trim()) {
      setPlaces([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await GoogleServices.initialize();
      const placeResults = await GoogleServices.searchPlaces(query, location, radius);
      setPlaces(placeResults);
    } catch (searchError: any) {
      setError(searchError.message || '搜尋失敗');
      setPlaces([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    places,
    loading,
    error,
    searchPlaces,
  };
};

// 路線規劃 Hook
export const useDirections = () => {
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getDirections = useCallback(async (
    origin: string | { lat: number; lng: number },
    destination: string | { lat: number; lng: number },
    waypoints?: Array<string | { lat: number; lng: number }>
  ) => {
    setLoading(true);
    setError(null);

    try {
      await GoogleServices.initialize();
      const routeResult = await GoogleServices.getDirections(origin, destination, waypoints);
      setRoute(routeResult);
    } catch (routeError: any) {
      setError(routeError.message || '路線規劃失敗');
      setRoute(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearRoute = useCallback(() => {
    setRoute(null);
    setError(null);
  }, []);

  return {
    route,
    loading,
    error,
    getDirections,
    clearRoute,
  };
};

// 距離計算 Hook
export const useDistanceCalculation = () => {
  const calculateDistance = useCallback((
    point1: { lat: number; lng: number },
    point2: { lat: number; lng: number }
  ): number => {
    return GoogleServices.calculateDistance(point1, point2);
  }, []);

  const calculateMultipleDistances = useCallback((
    origin: { lat: number; lng: number },
    destinations: Array<{ lat: number; lng: number }>
  ): number[] => {
    return destinations.map(dest => calculateDistance(origin, dest));
  }, [calculateDistance]);

  return {
    calculateDistance,
    calculateMultipleDistances,
  };
};

// Google Maps 載入狀態 Hook
export const useGoogleMapsLoader = () => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const loadGoogleMaps = async () => {
      if (typeof google !== 'undefined') {
        setIsLoaded(true);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        // 動態載入 Google Maps API
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${
          process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
        }&libraries=places,geometry&language=zh-TW&region=TW`;
        script.async = true;
        script.defer = true;

        await new Promise((resolve, reject) => {
          script.onload = resolve;
          script.onerror = reject;
          document.head.appendChild(script);
        });

        if (mounted) {
          setIsLoaded(true);
          await GoogleServices.initialize();
        }
      } catch (loadError) {
        if (mounted) {
          setError('Google Maps API 載入失敗');
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    loadGoogleMaps();

    return () => {
      mounted = false;
    };
  }, []);

  return {
    isLoaded,
    isLoading,
    error,
  };
};

// API 金鑰驗證 Hook
export const useGoogleApiValidation = () => {
  const [isValid, setIsValid] = useState<boolean | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  const validateApiKey = useCallback(async () => {
    setIsValidating(true);
    
    try {
      await GoogleServices.initialize();
      const valid = await GoogleServices.validateApiKey();
      setIsValid(valid);
    } catch (error) {
      setIsValid(false);
    } finally {
      setIsValidating(false);
    }
  }, []);

  useEffect(() => {
    validateApiKey();
  }, [validateApiKey]);

  return {
    isValid,
    isValidating,
    validateApiKey,
  };
};