// QueryResultChart.tsx
// --------------------
// 쿼리 결과 그래프(차트) 시각화 컴포넌트 파일
// - LLM/공공API/DB 등에서 받은 결과를 다양한 차트(막대/선/파이 등)로 렌더링
// - 차트 옵션/다운로드 등 UX 확장
// - index.tsx(메인 페이지)에서 조합하여 사용
// - 공식 규칙/명세(.cursor/rules/rl-text2sql-public-api.md) 기반 설계/구현
// - 확장성/유지보수성/테스트 용이성 고려

'use client';

import React, { useState } from 'react';
import ChartDisplay from './chart/ChartDisplay';

interface ChartData {
  type: 'line' | 'bar' | 'pie' | 'doughnut';
  title?: string;
  data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      borderColor?: string;
      backgroundColor?: string | string[];
      borderWidth?: number;
      tension?: number;
      fill?: boolean;
    }>;
  };
  options?: any;
}

interface QueryResultChartProps {
  data: ChartData;
  title?: string;
  subtitle?: string;
  width?: number;
  height?: number;
  className?: string;
  showDownload?: boolean;
  showLegend?: boolean;
}

/**
 * QueryResultChart 컴포넌트
 * 
 * 주요 기능:
 * - LLM/공공API/DB 등에서 받은 결과를 다양한 차트로 렌더링
 * - 선형, 막대, 파이, 도넛, 영역, 산점도 차트 지원
 * - 차트 다운로드 (PNG, SVG)
 * - 인터랙티브 기능 (호버, 줌, 필터)
 * - 반응형 차트 디자인
 */
const QueryResultChart: React.FC<QueryResultChartProps> = ({
  data,
  title,
  subtitle,
  width = 600,
  height = 400,
  className = '',
  showDownload = true,
  showLegend = true,
}) => {
  console.log('🎯 QueryResultChart 렌더링 시작:', {
    data,
    title,
    hasData: !!data,
    hasDataData: !!data?.data,
    dataType: data?.type,
    labelsLength: data?.data?.labels?.length,
    datasetsLength: data?.data?.datasets?.length
  });

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [chartType, setChartType] = useState(data.type);

  // 차트 타입 변경
  const handleChartTypeChange = (newType: ChartData['type']) => {
    setChartType(newType);
  };

  // 이미지 다운로드
  const handleDownload = (format: 'png' | 'svg' = 'png') => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return;

    if (format === 'png') {
      const url = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.download = `chart_${new Date().getTime()}.png`;
      link.href = url;
      link.click();
    }
  };

  // 전체화면 토글
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  // 차트 옵션 병합
  const mergedOptions = React.useMemo(() => {
    const defaultOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: showLegend,
          position: 'top' as const,
        },
        title: {
          display: !!(title || data.title),
          text: title || data.title,
          font: {
            size: 16,
            weight: 'bold' as const,
          },
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: 'white',
          bodyColor: 'white',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
        },
      },
      scales: chartType === 'pie' || chartType === 'doughnut' ? undefined : {
        x: {
          grid: {
            display: true,
            color: 'rgba(0, 0, 0, 0.1)',
          },
        },
        y: {
          grid: {
            display: true,
            color: 'rgba(0, 0, 0, 0.1)',
          },
          beginAtZero: true,
        },
      },
      animation: {
        duration: 1000,
      },
    };

    return {
      ...defaultOptions,
      ...data.options,
    };
  }, [data.options, title, data.title, showLegend, chartType]);

  // 차트 데이터 처리
  const chartData = React.useMemo(() => {
    return {
      ...data.data,
      datasets: data.data.datasets.map((dataset) => {
        const chartDataset: any = {
          label: dataset.label,
          data: dataset.data,
          backgroundColor: dataset.backgroundColor || 'rgba(54, 162, 235, 0.2)',
        };
        
        if (dataset.borderColor) chartDataset.borderColor = dataset.borderColor;
        if (dataset.borderWidth) chartDataset.borderWidth = dataset.borderWidth;
        if (dataset.tension !== undefined) chartDataset.tension = dataset.tension;
        if (dataset.fill !== undefined) chartDataset.fill = dataset.fill;
        
        return chartDataset;
      }),
    };
  }, [data.data]);

  if (!data || !data.data) {
    return (
      <div className={`bg-white dark:bg-gray-800 border rounded-lg p-6 text-center ${className}`}>
        <div className="text-gray-500 dark:text-gray-400">
          <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p>표시할 차트 데이터가 없습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 border rounded-lg overflow-hidden ${className}`}>
      {/* 헤더 */}
      <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 border-b">
        <div className="flex items-center justify-between">
          <div>
            {(title || data.title) && (
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
                {title || data.title}
              </h3>
            )}
            {subtitle && (
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {subtitle}
              </p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {/* 차트 타입 선택 */}
            <select
              value={chartType}
              onChange={(e) => handleChartTypeChange(e.target.value as ChartData['type'])}
              className="text-sm bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded px-2 py-1"
            >
              <option value="line">선형 차트</option>
              <option value="bar">막대 차트</option>
              <option value="pie">파이 차트</option>
              <option value="doughnut">도넛 차트</option>
            </select>

            {/* 전체화면 버튼 */}
            <button
              onClick={toggleFullscreen}
              className="p-1.5 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
              title="전체화면"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              </svg>
            </button>

            {/* 다운로드 버튼 */}
            {showDownload && (
              <button
                onClick={() => handleDownload('png')}
                className="flex items-center space-x-1 px-2 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                title="PNG로 다운로드"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>다운로드</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 차트 영역 */}
      <div className="p-4">
        <div
          className={`transition-all duration-300 ${
            isFullscreen ? 'fixed inset-0 z-50 bg-white dark:bg-gray-900 p-8' : ''
          }`}
        >
          {isFullscreen && (
            <button
              onClick={toggleFullscreen}
              className="absolute top-4 right-4 p-2 bg-gray-200 dark:bg-gray-700 rounded-full hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
          
          <div style={{ 
            width: isFullscreen ? '100%' : width, 
            height: isFullscreen ? 'calc(100vh - 120px)' : height 
          }}>
            <ChartDisplay
              type={chartType}
              data={chartData}
              options={mergedOptions}
              width={isFullscreen ? undefined : (width || 400)}
              height={isFullscreen ? undefined : (height || 300)}
            />
          </div>
        </div>
      </div>

      {/* 데이터 요약 */}
      <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 border-t">
        <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center space-x-4">
            <span>{data.data.labels?.length || 0}개 데이터 포인트</span>
            <span>{data.data.datasets?.length || 0}개 데이터셋</span>
          </div>
          <div className="text-xs">
            {chartType === 'line' && '📈 선형 차트'}
            {chartType === 'bar' && '📊 막대 차트'}
            {chartType === 'pie' && '🥧 파이 차트'}
            {chartType === 'doughnut' && '🍩 도넛 차트'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default QueryResultChart;

