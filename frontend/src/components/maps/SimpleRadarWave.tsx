'use client';

import React, { useEffect, useRef } from 'react';

// 類型擴展
declare global {
  interface Window {
    google: typeof google;
  }
}

interface SimpleRadarWaveProps {
  lat: number;
  lng: number;
  map: google.maps.Map;
  severity: 'low' | 'medium' | 'high' | 'critical';
  intensity: number;
  radius: number;
  onRemove?: () => void;
}

// 簡化版的雷達波覆蓋層
class SimpleRadarOverlay {
  private position: google.maps.LatLng;
  private container: HTMLDivElement | null = null;
  private severity: string;
  private intensity: number;
  private maxRadiusMeters: number;
  private waves: HTMLDivElement[] = [];
  private animationIntervals: NodeJS.Timeout[] = [];
  private map: google.maps.Map | null = null;
  private overlayView: google.maps.OverlayView | null = null;

  constructor(position: google.maps.LatLng, severity: string, intensity: number, maxRadiusMeters: number) {
    this.position = position;
    this.severity = severity;
    this.intensity = intensity;
    this.maxRadiusMeters = maxRadiusMeters;
  }

  setMap(map: google.maps.Map | null) {
    if (typeof window === 'undefined' || !window.google) {
      return;
    }

    this.map = map;
    
    if (map && !this.overlayView) {
      // 創建 OverlayView 實例
      this.overlayView = new google.maps.OverlayView();
      
      // 設置 onAdd 方法
      this.overlayView.onAdd = () => {
        this.onAdd();
      };
      
      // 設置 draw 方法
      this.overlayView.draw = () => {
        this.draw();
      };
      
      // 設置 onRemove 方法
      this.overlayView.onRemove = () => {
        this.onRemove();
      };
      
      this.overlayView.setMap(map);
    } else if (!map && this.overlayView) {
      this.overlayView.setMap(null);
      this.overlayView = null;
    }
  }

  private onAdd() {
    if (!this.overlayView) return;
    
    this.container = document.createElement('div');
    this.container.style.position = 'absolute';
    this.container.style.pointerEvents = 'none';
    this.container.style.width = '0px';
    this.container.style.height = '0px';
    
    const panes = this.overlayView.getPanes();
    if (panes) {
      panes.overlayLayer.appendChild(this.container);
    }

    this.startWaveAnimation();
  }

  private draw() {
    if (!this.container || !this.overlayView) return;

    const overlayProjection = this.overlayView.getProjection();
    if (!overlayProjection) return;

    const point = overlayProjection.fromLatLngToDivPixel(this.position);
    if (point) {
      this.container.style.left = point.x + 'px';
      this.container.style.top = point.y + 'px';
    }
  }

  private onRemove() {
    // 清理動畫間隔
    this.animationIntervals.forEach(interval => clearInterval(interval));
    this.animationIntervals = [];

    // 清理波紋元素
    this.waves.forEach(wave => {
      if (wave && wave.parentNode) {
        wave.parentNode.removeChild(wave);
      }
    });
    this.waves = [];

    // 移除容器
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
    this.container = null;
  }

  private getSeverityConfig() {
    switch (this.severity) {
      case 'critical':
        return { 
          color: '#DC2626', 
          interval: 600, 
          maxWaves: 4, 
          duration: 3000, 
          opacity: 0.8 
        };
      case 'high':
        return { 
          color: '#EF4444', 
          interval: 800, 
          maxWaves: 3, 
          duration: 3500, 
          opacity: 0.7 
        };
      case 'medium':
        return { 
          color: '#F59E0B', 
          interval: 1000, 
          maxWaves: 2, 
          duration: 4000, 
          opacity: 0.6 
        };
      default:
        return { 
          color: '#10B981', 
          interval: 1200, 
          maxWaves: 2, 
          duration: 4500, 
          opacity: 0.5 
        };
    }
  }

  private createWave(): HTMLDivElement {
    const config = this.getSeverityConfig();
    const wave = document.createElement('div');
    
    wave.style.position = 'absolute';
    wave.style.left = '0px';
    wave.style.top = '0px';
    wave.style.width = '4px';
    wave.style.height = '4px';
    wave.style.border = `2px solid ${config.color}`;
    wave.style.borderRadius = '50%';
    wave.style.transform = 'translate(-50%, -50%)';
    wave.style.pointerEvents = 'none';
    wave.style.opacity = config.opacity.toString();
    wave.style.transition = `all ${config.duration}ms ease-out`;
    
    return wave;
  }

  private animateWave(wave: HTMLDivElement) {
    const config = this.getSeverityConfig();
    
    // 計算最大像素半徑
    if (!this.map) return;

    const zoom = this.map.getZoom();
    if (!zoom) return;

    // 簡化的像素轉換計算
    const metersPerPixel = 156543.03392 * Math.cos(this.position.lat() * Math.PI / 180) / Math.pow(2, zoom);
    const maxPixelRadius = this.maxRadiusMeters / metersPerPixel;

    // 立即開始動畫
    setTimeout(() => {
      wave.style.width = `${maxPixelRadius * 2}px`;
      wave.style.height = `${maxPixelRadius * 2}px`;
      wave.style.opacity = '0';
      wave.style.borderWidth = '1px';
    }, 10);

    // 動畫結束後移除元素
    setTimeout(() => {
      if (wave && wave.parentNode) {
        wave.parentNode.removeChild(wave);
      }
      this.waves = this.waves.filter(w => w !== wave);
    }, config.duration);
  }

  private startWaveAnimation() {
    const config = this.getSeverityConfig();
    
    const createAndAnimateWave = () => {
      if (!this.container || this.waves.length >= config.maxWaves) return;

      const wave = this.createWave();
      this.container.appendChild(wave);
      this.waves.push(wave);
      this.animateWave(wave);
    };

    // 立即創建第一個波紋
    createAndAnimateWave();

    // 設置週期性創建波紋
    const interval = setInterval(createAndAnimateWave, config.interval);
    this.animationIntervals.push(interval);
  }

  public destroy() {
    this.setMap(null);
  }
}

const SimpleRadarWave: React.FC<SimpleRadarWaveProps> = ({
  lat,
  lng,
  map,
  severity,
  intensity,
  radius,
  onRemove
}) => {
  const overlayRef = useRef<SimpleRadarOverlay | null>(null);

  useEffect(() => {
    // 確保只在客戶端且 Google Maps API 已載入時執行
    if (typeof window === 'undefined' || !window.google || !map) {
      return;
    }

    const position = new google.maps.LatLng(lat, lng);
    const overlay = new SimpleRadarOverlay(position, severity, intensity, radius);
    overlay.setMap(map);
    overlayRef.current = overlay;

    return () => {
      if (overlayRef.current) {
        overlayRef.current.destroy();
        overlayRef.current = null;
      }
      onRemove?.();
    };
  }, [map, lat, lng, severity, intensity, radius, onRemove]);

  // 確保只在客戶端渲染
  if (typeof window === 'undefined') {
    return null;
  }

  return null;
};

export default SimpleRadarWave;
