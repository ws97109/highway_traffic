'use client';

import React, { useEffect, useRef } from 'react';

interface RadarWaveProps {
  lat: number;
  lng: number;
  map: google.maps.Map;
  severity: 'low' | 'medium' | 'high' | 'critical';
  intensity: number;
  radius: number;
  onRemove?: () => void;
}

class RadarWaveOverlay extends google.maps.OverlayView {
  private position: google.maps.LatLng;
  private container: HTMLDivElement | null = null;
  private severity: string;
  private intensity: number;
  private maxRadius: number;
  private animationFrameId: number | null = null;
  private waves: Array<{ element: HTMLDivElement; startTime: number; waveIndex: number }> = [];
  private isDestroyed = false;

  constructor(position: google.maps.LatLng, severity: string, intensity: number, maxRadius: number) {
    super();
    this.position = position;
    this.severity = severity;
    this.intensity = intensity;
    this.maxRadius = maxRadius;
  }

  onAdd() {
    // 創建容器
    this.container = document.createElement('div');
    this.container.style.position = 'absolute';
    this.container.style.pointerEvents = 'none';
    this.container.style.width = '0px';
    this.container.style.height = '0px';
    
    // 添加到地圖覆蓋層
    const panes = this.getPanes();
    if (panes) {
      panes.overlayLayer.appendChild(this.container);
    }

    // 開始雷達波動畫
    this.startRadarAnimation();
  }

  draw() {
    if (!this.container) return;

    const overlayProjection = this.getProjection();
    if (!overlayProjection) return;

    // 將經緯度轉換為像素座標
    const point = overlayProjection.fromLatLngToDivPixel(this.position);
    if (point) {
      this.container.style.left = point.x + 'px';
      this.container.style.top = point.y + 'px';
    }
  }

  onRemove() {
    this.isDestroyed = true;
    
    // 停止動畫
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
    }

    // 清理所有波紋元素
    this.waves.forEach(wave => {
      if (wave.element && wave.element.parentNode) {
        wave.element.parentNode.removeChild(wave.element);
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
          waveInterval: 800, // 更快的波紋間隔
          waveDuration: 4000,
          maxWaves: 6,
          opacity: 0.8
        };
      case 'high':
        return {
          color: '#EF4444',
          waveInterval: 1000,
          waveDuration: 4500,
          maxWaves: 5,
          opacity: 0.7
        };
      case 'medium':
        return {
          color: '#F59E0B',
          waveInterval: 1200,
          waveDuration: 5000,
          maxWaves: 4,
          opacity: 0.6
        };
      default:
        return {
          color: '#10B981',
          waveInterval: 1500,
          waveDuration: 5500,
          maxWaves: 3,
          opacity: 0.5
        };
    }
  }

  private createWaveElement(waveIndex: number): HTMLDivElement {
    const config = this.getSeverityConfig();
    const wave = document.createElement('div');
    
    wave.style.position = 'absolute';
    wave.style.left = '0px';
    wave.style.top = '0px';
    wave.style.width = '0px';
    wave.style.height = '0px';
    wave.style.border = `2px solid ${config.color}`;
    wave.style.borderRadius = '50%';
    wave.style.transform = 'translate(-50%, -50%)';
    wave.style.pointerEvents = 'none';
    wave.style.opacity = '0';
    
    return wave;
  }

  private startRadarAnimation() {
    const config = this.getSeverityConfig();
    let lastWaveTime = 0;
    let waveCounter = 0;

    const animate = (currentTime: number) => {
      if (this.isDestroyed) return;

      // 創建新波紋
      if (currentTime - lastWaveTime >= config.waveInterval) {
        if (this.waves.length < config.maxWaves) {
          const waveElement = this.createWaveElement(waveCounter);
          if (this.container) {
            this.container.appendChild(waveElement);
            this.waves.push({
              element: waveElement,
              startTime: currentTime,
              waveIndex: waveCounter
            });
          }
          lastWaveTime = currentTime;
          waveCounter++;
        }
      }

      // 更新現有波紋
      this.waves = this.waves.filter(wave => {
        const elapsed = currentTime - wave.startTime;
        const progress = elapsed / config.waveDuration;

        if (progress >= 1) {
          // 移除完成的波紋
          if (wave.element && wave.element.parentNode) {
            wave.element.parentNode.removeChild(wave.element);
          }
          return false;
        }

        // 更新波紋大小和透明度
        const overlayProjection = this.getProjection();
        if (overlayProjection && wave.element) {
          // 計算當前半徑（像素）
          const earthRadius = 6371000; // 地球半徑（米）
          const lat = this.position.lat() * Math.PI / 180;
          const metersPerPixel = 156543.03392 * Math.cos(lat) / Math.pow(2, this.getMap()!.getZoom()!);
          const currentRadiusPx = (this.maxRadius * progress) / metersPerPixel;

          // 使用緩動函數讓擴散更自然
          const easeOut = 1 - Math.pow(1 - progress, 3);
          const finalRadiusPx = currentRadiusPx * easeOut;

          // 透明度變化：開始時最亮，然後逐漸消失
          const opacity = config.opacity * (1 - progress) * (progress < 0.1 ? progress * 10 : 1);

          wave.element.style.width = `${finalRadiusPx * 2}px`;
          wave.element.style.height = `${finalRadiusPx * 2}px`;
          wave.element.style.opacity = opacity.toString();
        }

        return true;
      });

      // 繼續動畫
      this.animationFrameId = requestAnimationFrame(animate);
    };

    this.animationFrameId = requestAnimationFrame(animate);
  }

  public destroy() {
    this.setMap(null);
  }
}

const RadarWave: React.FC<RadarWaveProps> = ({ 
  lat, 
  lng, 
  map, 
  severity, 
  intensity, 
  radius,
  onRemove 
}) => {
  const overlayRef = useRef<RadarWaveOverlay | null>(null);

  useEffect(() => {
    if (!map) return;

    const position = new google.maps.LatLng(lat, lng);
    const overlay = new RadarWaveOverlay(position, severity, intensity, radius);
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

  // 當屬性變化時重新創建覆蓋層
  useEffect(() => {
    if (overlayRef.current) {
      overlayRef.current.destroy();
      
      const position = new google.maps.LatLng(lat, lng);
      const overlay = new RadarWaveOverlay(position, severity, intensity, radius);
      overlay.setMap(map);
      overlayRef.current = overlay;
    }
  }, [lat, lng, severity, intensity, radius]);

  return null; // 這個組件不渲染任何React元素
};

export default RadarWave;
