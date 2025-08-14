import { useState, useEffect, useCallback } from 'react';
import GoogleServices, { GeocodeResult, PlaceSearchResult, RouteResult } from '../services/googleServices';

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
        }
      } catch (geocodeError: any) {
        console.warn('無法取得地址資訊:', geocodeError);
        
        // 如果是 REQUEST_DENIED，提供備用地址顯示方式
        if (geocodeError.message && geocodeError.message.includes('REQUEST_DENIED')) {
          setAddress(`位置: ${lat.toFixed(4)}, ${lng.toFixed(4)}`);
          console.info('💡 提示: 啟用 Geocoding API 以顯示詳細地址');
        } else {
          setAddress('位置已取得');
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
      }
    } catch (error) {
      console.warn('無法取得地址資訊:', error);
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