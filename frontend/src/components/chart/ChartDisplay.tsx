// components/chart/ChartDisplay.tsx
// ===================================
// 데이터 시각화 차트 컴포넌트
// - Chart.js를 사용한 다양한 차트 타입 지원
// - 선 그래프, 막대 그래프, 파이 차트 등
// - 인구, GDP 등 통계 데이터 시각화

'use client';

import React, { useEffect, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Chart } from 'react-chartjs-2';

// Chart.js 컴포넌트 등록
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

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
  console.log('🎬 ChartDisplay 렌더링:', { 
    type, 
    data, 
    title,
    hasData: !!data,
    hasLabels: !!data?.labels,
    hasDatasets: !!data?.datasets,
    labelsLength: data?.labels?.length,
    datasetsLength: data?.datasets?.length,
    firstDatasetData: data?.datasets?.[0]?.data
  });

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
          weight: 'bold' as const,
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
    ...options,
  };

  return (
    <div className="chart-container bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div style={{ width: `${width}px`, height: `${height}px`, maxWidth: '100%' }}>
        <Chart
          type={type}
          data={data}
          options={defaultOptions}
        />
      </div>
    </div>
  );
};

export default ChartDisplay; 