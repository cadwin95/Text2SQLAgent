// components/chart/ChartDisplay.tsx
// ===================================
// 데이터 시각화 차트 컴포넌트
// - Chart.js를 사용한 다양한 차트 타입 지원
// - 선 그래프, 막대 그래프, 파이 차트 등
// - 인구, GDP 등 통계 데이터 시각화

'use client';

import React, { useEffect, useRef } from 'react';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

// Chart.js 모든 컴포넌트 등록
Chart.register(...registerables);

interface ChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string;
    borderWidth?: number;
    tension?: number;
  }[];
}

interface ChartDisplayProps {
  type: 'line' | 'bar' | 'pie' | 'doughnut';
  data: ChartData;
  title?: string;
  width?: number;
  height?: number;
  options?: any;
}

const ChartDisplay: React.FC<ChartDisplayProps> = ({
  type,
  data,
  title,
  width = 600,
  height = 400,
  options = {}
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    // 기존 차트 제거
    if (chartRef.current) {
      chartRef.current.destroy();
    }

    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    // 기본 차트 옵션
    const defaultOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: !!title,
          text: title,
          font: {
            size: 16,
            weight: 'bold',
          },
        },
        legend: {
          display: true,
          position: 'bottom' as const,
        },
      },
      scales: type === 'line' || type === 'bar' ? {
        x: {
          display: true,
          title: {
            display: true,
            text: '연도',
          },
        },
        y: {
          display: true,
          title: {
            display: true,
            text: '값',
          },
          beginAtZero: true,
        },
      } : {},
    };

    // 차트 설정
    const config: ChartConfiguration = {
      type: type,
      data: data,
      options: {
        ...defaultOptions,
        ...options,
      },
    };

    // 차트 생성
    chartRef.current = new Chart(ctx, config);

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [type, data, title, options]);

  return (
    <div className="chart-container bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="max-w-full h-auto"
      />
    </div>
  );
};

export default ChartDisplay; 