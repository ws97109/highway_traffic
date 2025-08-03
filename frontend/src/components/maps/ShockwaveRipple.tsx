'use client';

import React from 'react';

interface ShockwaveRippleProps {
  severity: 'low' | 'medium' | 'high' | 'critical';
  size?: number;
  intensity?: number;
}

const ShockwaveRipple: React.FC<ShockwaveRippleProps> = ({ 
  severity, 
  size = 24,  // 調整預設大小為更小
  intensity = 5.0
}) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#DC2626';
      case 'high': return '#EF4444';
      case 'medium': return '#F59E0B';
      case 'low': return '#10B981';
      default: return '#10B981';
    }
  };

  const getSeverityConfig = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          rippleCount: 5,
          maxScale: 3.0,
          animationDuration: '3s',
          strokeWidth: 3
        };
      case 'high':
        return {
          rippleCount: 4,
          maxScale: 2.5,
          animationDuration: '3.5s',
          strokeWidth: 2
        };
      case 'medium':
        return {
          rippleCount: 3,
          maxScale: 2.0,
          animationDuration: '4s',
          strokeWidth: 2
        };
      case 'low':
      default:
        return {
          rippleCount: 2,
          maxScale: 1.5,
          animationDuration: '4.5s',
          strokeWidth: 1
        };
    }
  };

  const color = getSeverityColor(severity);
  const config = getSeverityConfig(severity);
  
  // 根據強度調整大小
  const adjustedSize = Math.max(16, Math.min(size * (0.8 + intensity / 20), 48));
  
  return (
    <div 
      className="absolute pointer-events-none"
      style={{
        width: adjustedSize,
        height: adjustedSize,
        transform: 'translate(-50%, -50%)',
      }}
    >
      {/* 中心點 */}
      <div
        className={`absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 rounded-full shockwave-${severity}`}
        style={{
          width: adjustedSize * 0.25,  // 更小的中心點
          height: adjustedSize * 0.25,
          backgroundColor: color,
          opacity: 0.9,
          boxShadow: `0 0 ${adjustedSize * 0.1}px ${color}`,
        }}
      />
      
      {/* 動態生成水波紋圓圈 */}
      {Array.from({ length: config.rippleCount }, (_, index) => {
        const delay = index * (parseFloat(config.animationDuration) / config.rippleCount);
        const rippleSize = adjustedSize * (1 + index * 0.3);
        
        return (
          <div
            key={index}
            className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 rounded-full border"
            style={{
              width: rippleSize,
              height: rippleSize,
              borderColor: color,
              borderWidth: config.strokeWidth,
              backgroundColor: 'transparent',
              animation: `ripple-expand ${config.animationDuration} ease-out infinite`,
              animationDelay: `${delay}s`,
              opacity: 0,
            }}
          />
        );
      })}
      
      {/* 額外的大範圍水波紋（僅限高危險等級） */}
      {(severity === 'critical' || severity === 'high') && (
        <>
          <div
            className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 rounded-full border"
            style={{
              width: adjustedSize * 2,
              height: adjustedSize * 2,
              borderColor: color,
              borderWidth: 1,
              backgroundColor: 'transparent',
              animation: `ripple-expand-large 6s ease-out infinite`,
              animationDelay: '1s',
              opacity: 0,
            }}
          />
          <div
            className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 rounded-full border"
            style={{
              width: adjustedSize * 2.5,
              height: adjustedSize * 2.5,
              borderColor: color,
              borderWidth: 1,
              backgroundColor: 'transparent',
              animation: `ripple-expand-large 7s ease-out infinite`,
              animationDelay: '2.5s',
              opacity: 0,
            }}
          />
        </>
      )}
      
      {/* 小範圍快速水波紋（所有等級） */}
      <div
        className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 rounded-full border"
        style={{
          width: adjustedSize * 0.8,
          height: adjustedSize * 0.8,
          borderColor: color,
          borderWidth: 2,
          backgroundColor: 'transparent',
          animation: `ripple-expand-small 2s ease-out infinite`,
          opacity: 0,
        }}
      />
    </div>
  );
};

export default ShockwaveRipple;
