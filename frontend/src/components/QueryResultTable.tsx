// QueryResultTable.tsx
// --------------------
// 쿼리 결과 테이블 시각화 컴포넌트 파일
// - LLM/공공API/DB 등에서 받은 결과를 표 형태로 렌더링
// - 컬럼/정렬/필터/다운로드 등 UX 확장
// - index.tsx(메인 페이지)에서 조합하여 사용
// - 공식 규칙/명세(.cursor/rules/rl-text2sql-public-api.md) 기반 설계/구현
// - 확장성/유지보수성/테스트 용이성 고려

'use client';

import React, { useState } from 'react';

interface TableData {
  columns: string[];
  rows: any[];
  total_rows?: number;
  query_code?: string;
  title?: string;
}

interface QueryResultTableProps {
  data: TableData;
  title?: string;
  showQuery?: boolean;
  maxRows?: number;
  className?: string;
}

/**
 * QueryResultTable 컴포넌트
 * 
 * 주요 기능:
 * - LLM/공공API/DB 등에서 받은 결과를 표 형태로 렌더링
 * - 컬럼 정렬, 필터링, 페이지네이션
 * - 데이터 다운로드 (CSV, Excel)
 * - SQL 쿼리 코드 표시
 * - 반응형 테이블 디자인
 */
const QueryResultTable: React.FC<QueryResultTableProps> = ({
  data,
  title,
  showQuery = true,
  // maxRows = 100, // 향후 페이지네이션용
  className = '',
}) => {
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(20);

  const { columns, rows, total_rows, query_code } = data;

  // 정렬 처리
  const sortedRows = React.useMemo(() => {
    if (!sortColumn) return rows;

    return [...rows].sort((a, b) => {
      const aValue = a[sortColumn];
      const bValue = b[sortColumn];

      let comparison = 0;
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        comparison = aValue - bValue;
      } else {
        comparison = String(aValue || '').localeCompare(String(bValue || ''));
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [rows, sortColumn, sortDirection]);

  // 페이지네이션 처리
  const paginatedRows = React.useMemo(() => {
    const startIndex = (currentPage - 1) * rowsPerPage;
    return sortedRows.slice(startIndex, startIndex + rowsPerPage);
  }, [sortedRows, currentPage, rowsPerPage]);

  const totalPages = Math.ceil(sortedRows.length / rowsPerPage);

  // 정렬 핸들러
  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
    setCurrentPage(1);
  };

  // CSV 다운로드
  const handleDownloadCSV = () => {
    const csvContent = [
      columns.join(','),
      ...sortedRows.map(row => 
        columns.map(col => {
          const value = row[col];
          return typeof value === 'string' && value.includes(',') 
            ? `"${value}"` 
            : String(value || '');
        }).join(',')
      )
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `query_result_${new Date().getTime()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 값 포맷팅
  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return 'NULL';
    if (typeof value === 'number') {
      return value.toLocaleString('ko-KR');
    }
    return String(value);
  };

  if (!columns || !rows || rows.length === 0) {
    return (
      <div className={`bg-gray-800 border-gray-700 border rounded-lg p-6 text-center ${className}`}>
        <div className="text-gray-400">
          <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 002 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <p>표시할 데이터가 없습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-800 border-gray-700 border rounded-lg overflow-hidden h-full flex flex-col ${className}`}>
      {/* 헤더 */}
      <div className="bg-gray-700 px-4 py-2 border-b border-gray-600 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="text-xs text-gray-300">
            {paginatedRows.length}개 행 표시 (총 {sortedRows.length}개)
            {total_rows && total_rows > rows.length && (
              <span className="text-orange-400">
                {' '}(전체 {total_rows.toLocaleString()}개 중)
              </span>
            )}
            {' '}• {columns.length}개 컬럼
          </div>
          <button
            onClick={handleDownloadCSV}
            className="flex items-center space-x-1 px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>CSV 다운로드</span>
          </button>
        </div>
      </div>

      {/* 테이블 - 스크롤 가능한 영역 */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="overflow-x-auto overflow-y-auto flex-1">
          <table className="w-full">
            <thead className="bg-gray-700 sticky top-0 z-10">
              <tr>
                {columns.map((column, index) => (
                  <th
                    key={index}
                    onClick={() => handleSort(column)}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-600 transition-colors"
                  >
                    <div className="flex items-center space-x-1">
                      <span>{column}</span>
                      {sortColumn === column && (
                        <svg
                          className={`w-3 h-3 transition-transform ${
                            sortDirection === 'desc' ? 'transform rotate-180' : ''
                          }`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                        </svg>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-gray-800 divide-y divide-gray-600">
              {paginatedRows.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  className={`${
                    rowIndex % 2 === 0
                      ? 'bg-gray-800'
                      : 'bg-gray-750'
                  } hover:bg-gray-700 transition-colors`}
                >
                  {columns.map((column, colIndex) => (
                    <td
                      key={colIndex}
                      className="px-4 py-3 text-sm text-gray-100"
                    >
                      <span className={row[column] === null || row[column] === undefined ? 'text-gray-500 italic' : ''}>
                        {formatValue(row[column])}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 페이지네이션 - 하단 고정 */}
      {totalPages > 1 && (
        <div className="bg-gray-700 px-4 py-3 border-t border-gray-600 flex items-center justify-between flex-shrink-0">
          <div className="text-sm text-gray-300">
            {((currentPage - 1) * rowsPerPage) + 1}-{Math.min(currentPage * rowsPerPage, sortedRows.length)}
            {' '}/ {sortedRows.length}개 행
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm bg-gray-600 border border-gray-500 text-white rounded hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              이전
            </button>
            <span className="text-sm text-gray-300">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm bg-gray-600 border border-gray-500 text-white rounded hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              다음
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default QueryResultTable;

