"""
Text2SQL Agent - DataFrame을 SQL 테이블로 취급하여 SQL 쿼리 실행
DataFrame 데이터를 메모리 내 SQLite DB에 로드하여 SQL로 자유롭게 조작
"""

import pandas as pd
import sqlite3
import tempfile
import os
from typing import Dict, Any, List, Optional
import logging

class Text2DFQueryAgent:
    """DataFrame을 SQL 테이블로 매핑하여 SQL 쿼리를 실행하는 에이전트"""
    
    def __init__(self):
        # DataFrame 저장소 (도구 호출 결과 저장)
        self.dataframes: Dict[str, pd.DataFrame] = {}
        
        # 메모리 내 SQLite 연결
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # 테이블 스키마 정보 저장
        self.table_schemas: Dict[str, Dict[str, str]] = {}
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def register_dataframe(self, name: str, df: pd.DataFrame) -> str:
        """DataFrame을 SQL 테이블로 등록"""
        try:
            # DataFrame 저장
            self.dataframes[name] = df.copy()
            
            # 테이블명 정규화 (SQL 친화적으로)
            table_name = self._normalize_table_name(name)
            
            # SQLite에 테이블로 저장
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            
            # 스키마 정보 저장
            self.table_schemas[table_name] = self._get_table_schema(df)
            
            self.logger.info(f"[SQL 테이블 등록] {name} → {table_name} (행 수: {len(df)})")
            return table_name
            
        except Exception as e:
            self.logger.error(f"DataFrame 등록 오류: {e}")
            return None
    
    def _normalize_table_name(self, name: str) -> str:
        """테이블명을 SQL 친화적으로 변환"""
        # fetch_kosis_data_DT_1B040A3 → kosis_population_data
        if 'kosis' in name.lower():
            if 'DT_1B040A3' in name:  # 인구 관련
                return 'population_stats'
            elif 'DT_1B040B1' in name:  # GDP 관련  
                return 'gdp_stats'
            else:
                return 'kosis_data'
        else:
            # 일반적인 정규화
            import re
            cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
            return cleaned[:63]  # SQLite 테이블명 길이 제한
    
    def _get_table_schema(self, df: pd.DataFrame) -> Dict[str, str]:
        """DataFrame의 스키마 정보 추출"""
        schema = {}
        for col in df.columns:
            dtype = df[col].dtype
            if dtype == 'object':
                schema[col] = 'TEXT'
            elif dtype in ['int64', 'int32']:
                schema[col] = 'INTEGER'
            elif dtype in ['float64', 'float32']:
                schema[col] = 'REAL'
            else:
                schema[col] = 'TEXT'
        return schema
    
    def get_available_tables(self) -> Dict[str, Dict]:
        """사용 가능한 테이블 목록과 스키마 정보 반환"""
        tables_info = {}
        
        for table_name, schema in self.table_schemas.items():
            # 테이블 정보 조회
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # 샘플 데이터 조회
            cursor = self.conn.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            tables_info[table_name] = {
                'schema': schema,
                'row_count': row_count,
                'columns': columns,
                'sample_data': sample_rows
            }
        
        return tables_info
    
    def run(self, question: str) -> Dict[str, Any]:
        """자연어 질문을 SQL 쿼리로 변환하여 실행"""
        try:
            # 사용 가능한 테이블 정보
            tables_info = self.get_available_tables()
            
            if not tables_info:
                return {
                    "error": "사용 가능한 테이블이 없습니다. 먼저 데이터를 로드해주세요.",
                    "result": None,
                    "sql_query": None
                }
            
            # SQL 쿼리 생성
            sql_query = self._generate_sql_query(question, tables_info)
            
            if not sql_query:
                return {
                    "error": "SQL 쿼리 생성에 실패했습니다.",
                    "result": None,
                    "sql_query": None
                }
            
            # SQL 쿼리 실행
            result = self._execute_sql_query(sql_query)
            
            return {
                "error": None,
                "result": result,
                "sql_query": sql_query,
                "available_tables": list(tables_info.keys())
            }
            
        except Exception as e:
            self.logger.error(f"쿼리 실행 오류: {e}")
            return {
                "error": str(e),
                "result": None,
                "sql_query": None
            }
    
    def _generate_sql_query(self, question: str, tables_info: Dict) -> str:
        """자연어 질문을 SQL 쿼리로 변환"""
        
        # 테이블 스키마 정보 구성
        schema_desc = self._build_schema_description(tables_info)
        
        prompt = f"""
다음 데이터베이스 스키마를 참고하여 사용자 질문에 대한 SQL 쿼리를 생성하세요.

{schema_desc}

사용자 질문: {question}

규칙:
1. 실행 가능한 SQL 쿼리만 반환하세요
2. SELECT 문만 사용하세요 (INSERT, UPDATE, DELETE 금지)
3. 설명이나 주석 없이 SQL 쿼리만 출력하세요
4. 테이블명과 컬럼명을 정확히 사용하세요
5. 집계 함수나 GROUP BY 등을 적절히 활용하세요

SQL 쿼리:"""

        try:
            from llm_client import get_llm_client
            llm_client = get_llm_client()
            
            response = llm_client.chat([
                {"role": "system", "content": "당신은 SQL 전문가입니다. 주어진 스키마에 맞는 정확한 SQL 쿼리만 생성하세요."},
                {"role": "user", "content": prompt}
            ])
            
            sql_query = response.strip()
            
            # SQL 쿼리 정리 (주석이나 불필요한 텍스트 제거)
            sql_query = self._clean_sql_query(sql_query)
            
            self.logger.info(f"[생성된 SQL] {sql_query}")
            return sql_query
            
        except Exception as e:
            self.logger.error(f"SQL 쿼리 생성 오류: {e}")
            return None
    
    def _build_schema_description(self, tables_info: Dict) -> str:
        """테이블 스키마 설명 구성"""
        schema_parts = []
        
        for table_name, info in tables_info.items():
            columns_desc = []
            for col, dtype in info['schema'].items():
                columns_desc.append(f"  {col} {dtype}")
            
            sample_data = ""
            if info['sample_data']:
                sample_data = f"\n샘플 데이터: {info['sample_data'][:2]}"
            
            schema_parts.append(f"""
테이블: {table_name} ({info['row_count']}행)
컬럼:
{chr(10).join(columns_desc)}{sample_data}
""")
        
        return "\n".join(schema_parts)
    
    def _clean_sql_query(self, sql_query: str) -> str:
        """SQL 쿼리 정리"""
        # 여러 줄을 한 줄로 합치기
        sql_query = ' '.join(sql_query.split())
        
        # 주석 제거
        import re
        sql_query = re.sub(r'--[^\n]*', '', sql_query)
        sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
        
        # 불필요한 공백 제거
        sql_query = re.sub(r'\s+', ' ', sql_query).strip()
        
        # SQL 쿼리만 추출 (다른 텍스트 제거)
        if 'SELECT' in sql_query.upper():
            start_idx = sql_query.upper().find('SELECT')
            sql_query = sql_query[start_idx:]
            
            # 세미콜론으로 끝나는 경우 처리
            if ';' in sql_query:
                sql_query = sql_query.split(';')[0]
        
        return sql_query
    
    def _execute_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """SQL 쿼리 실행"""
        try:
            cursor = self.conn.execute(sql_query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # 결과를 딕셔너리 형태로 변환
            result_data = []
            for row in rows:
                result_data.append(dict(zip(columns, row)))
            
            return {
                "columns": columns,
                "rows": result_data,
                "row_count": len(result_data),
                "query_type": "SELECT"
            }
            
        except Exception as e:
            self.logger.error(f"SQL 실행 오류: {e}")
            raise e
    
    def execute_custom_sql(self, sql_query: str) -> Dict[str, Any]:
        """사용자 정의 SQL 쿼리 직접 실행"""
        try:
            return self._execute_sql_query(sql_query)
        except Exception as e:
            return {
                "error": str(e),
                "columns": [],
                "rows": [],
                "row_count": 0
            }
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """특정 테이블 정보 조회"""
        if table_name not in self.table_schemas:
            return {"error": f"테이블 '{table_name}'을 찾을 수 없습니다."}
        
        try:
            cursor = self.conn.execute(f"SELECT * FROM {table_name} LIMIT 10")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cursor.fetchone()[0]
            
            return {
                "table_name": table_name,
                "schema": self.table_schemas[table_name],
                "columns": columns,
                "sample_rows": rows,
                "total_rows": total_rows
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def clear_dataframes(self):
        """모든 DataFrame 삭제 (기존 호환성)"""
        self.clear_all_data()
    
    def clear_all_data(self):
        """모든 데이터 정리"""
        self.dataframes.clear()
        self.table_schemas.clear()
        
        # 모든 테이블 삭제
        cursor = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            self.conn.execute(f"DROP TABLE IF EXISTS {table[0]}")
        
        self.conn.commit()
        self.logger.info("[데이터 정리] 모든 테이블과 DataFrame 삭제됨")
    
    def __del__(self):
        """소멸자: 연결 종료"""
        if hasattr(self, 'conn'):
            self.conn.close() 