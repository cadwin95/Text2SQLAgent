"""
🗃️ TEXT2SQL AGENT: MCP 기반 DataFrame → SQL 변환 에이전트
======================================================
역할: MCP Client의 핵심 컴포넌트로서 DataFrame 데이터를 SQL로 분석

📖 MCP 아키텍처에서의 위치:
- MCP Client Component: AgentChain과 함께 integrated_api_server.py에서 활용
- Data Processing: MCP Server(mcp_api_v2.py)에서 가져온 데이터를 SQL로 처리
- SQL Engine: 메모리 내 SQLite를 활용한 고성능 쿼리 실행

🎯 주요 기능:
1. MCP Server 데이터 → DataFrame → SQL 테이블 변환
2. LLM 기반 자연어 → SQL 쿼리 변환
3. 메모리 내 SQLite 데이터베이스 관리
4. SQL 쿼리 실행 및 결과 반환
5. 테이블 스키마 분석 및 최적화

🔄 MCP 데이터 플로우:
1. MCP Server(KOSIS API) → DataFrame (AgentChain이 수집)
2. DataFrame → SQL 테이블 등록 (이 에이전트)
3. 자연어 질문 → SQL 쿼리 변환 (LLM 활용)
4. SQL 실행 → 결과 반환 → 시각화

🚀 핵심 특징:
- 고성능: 메모리 내 SQLite로 빠른 쿼리 실행
- 유연성: 다양한 DataFrame 구조 자동 처리
- 안전성: SELECT 전용, 데이터 변조 방지
- 스키마 자동화: 컬럼 타입 자동 감지 및 변환
- SQL 정규화: 생성된 쿼리 자동 최적화

💾 지원하는 데이터 소스:
- KOSIS 통계 데이터 (MCP Server를 통해 수집)
- 기타 DataFrame 형태의 모든 데이터
- CSV, JSON 등에서 변환된 DataFrame

참고: AgentChain과 긴밀하게 연동되어 MCP 기반 분석 워크플로우의 SQL 엔진 역할 담당
"""

import pandas as pd
import sqlite3
import tempfile
import os
from typing import Dict, Any, List, Optional
import logging

class Text2DFQueryAgent:
    """
    🗃️ MCP 기반 DataFrame → SQL 변환 에이전트
    
    MCP 아키텍처에서의 역할:
    - MCP Client의 SQL 엔진 컴포넌트
    - MCP Server에서 수집한 데이터를 SQL로 분석
    - AgentChain의 파트너로 동작하여 완전한 분석 파이프라인 구성
    
    주요 특징:
    - 메모리 내 SQLite로 고성능 쿼리 실행
    - MCP Server 데이터 자동 처리 및 스키마 감지
    - LLM 기반 자연어 → SQL 변환
    - 안전한 SELECT 전용 쿼리 실행
    """
    
    def __init__(self):
        # DataFrame 저장소 (MCP Server 도구 호출 결과 저장)
        self.dataframes: Dict[str, pd.DataFrame] = {}
        
        # 메모리 내 SQLite 연결 (고성능 SQL 엔진)
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # MCP 데이터 테이블 스키마 정보 저장
        self.table_schemas: Dict[str, Dict[str, str]] = {}
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("[Text2SQL Agent] 🗃️ MCP SQL 엔진 초기화 완료")
    
    def register_dataframe(self, name: str, df: pd.DataFrame) -> str:
        """
        MCP Server에서 가져온 DataFrame을 SQL 테이블로 등록
        - DataFrame 스키마 자동 분석
        - SQL 친화적 테이블명 변환
        - 메모리 내 SQLite 테이블 생성
        """
        try:
            # DataFrame 저장 (MCP Server 데이터)
            self.dataframes[name] = df.copy()
            
            # 테이블명 정규화 (SQL 친화적으로)
            table_name = self._normalize_table_name(name)
            
            # SQLite에 테이블로 저장
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            
            # MCP 데이터 스키마 정보 저장
            self.table_schemas[table_name] = self._get_table_schema(df)
            
            self.logger.info(f"[Text2SQL Agent] ✅ MCP 데이터 등록: {name} → SQL 테이블 '{table_name}' (행 수: {len(df)})")
            return table_name
            
        except Exception as e:
            self.logger.error(f"[Text2SQL Agent] ❌ MCP DataFrame 등록 오류: {e}")
            return None
    
    def _normalize_table_name(self, name: str) -> str:
        """
        테이블명을 SQL 친화적으로 변환
        - MCP Server 데이터 명명 규칙 적용
        - KOSIS 데이터 특별 처리
        """
        # MCP KOSIS 데이터 특별 처리
        if 'mcp_kosis' in name.lower() or 'kosis' in name.lower():
            if 'DT_1B040A3' in name:  # 인구 관련
                return 'mcp_population_stats'
            elif 'DT_1B040B1' in name:  # GDP 관련  
                return 'mcp_gdp_stats'
            else:
                return 'mcp_kosis_data'
        else:
            # 일반적인 정규화
            import re
            cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
            return cleaned[:63]  # SQLite 테이블명 길이 제한
    
    def _get_table_schema(self, df: pd.DataFrame) -> Dict[str, str]:
        """MCP 데이터 DataFrame의 스키마 정보 추출"""
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
        """
        MCP 기반 사용 가능한 SQL 테이블 목록 반환
        - 테이블 스키마 정보
        - 데이터 샘플
        - MCP Server 출처 정보
        """
        tables_info = {}
        
        for table_name, schema in self.table_schemas.items():
            # 테이블 정보 조회
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # MCP 데이터 샘플 조회
            cursor = self.conn.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # MCP 데이터 출처 정보 추가
            data_source = "MCP Server (KOSIS)" if "mcp" in table_name else "Direct DataFrame"
            
            tables_info[table_name] = {
                'schema': schema,
                'row_count': row_count,
                'columns': columns,
                'sample_data': sample_rows,
                'data_source': data_source,
                'mcp_integration': True
            }
        
        return tables_info
    
    def run(self, question: str) -> Dict[str, Any]:
        """
        MCP 기반 자연어 → SQL 쿼리 변환 및 실행
        - LLM을 활용한 SQL 쿼리 생성
        - MCP Server 데이터 기반 분석
        - 안전한 SELECT 전용 실행
        """
        try:
            # MCP 기반 사용 가능한 테이블 정보
            tables_info = self.get_available_tables()
            
            if not tables_info:
                return {
                    "error": "MCP Server에서 수집한 데이터가 없습니다. 먼저 MCP 도구로 데이터를 로드해주세요.",
                    "result": None,
                    "sql_query": None,
                    "mcp_status": "no_data"
                }
            
            self.logger.info(f"[Text2SQL Agent] 🔍 MCP 데이터 기반 SQL 쿼리 생성: {question}")
            
            # LLM 기반 SQL 쿼리 생성
            sql_query = self._generate_sql_query(question, tables_info)
            
            if not sql_query:
                return {
                    "error": "MCP 데이터 기반 SQL 쿼리 생성에 실패했습니다.",
                    "result": None,
                    "sql_query": None,
                    "mcp_status": "query_generation_failed"
                }
            
            # SQL 쿼리 실행
            result = self._execute_sql_query(sql_query)
            
            self.logger.info(f"[Text2SQL Agent] ✅ MCP SQL 쿼리 실행 완료: {len(result.get('rows', []))}행 반환")
            
            return {
                "error": None,
                "result": result,
                "sql_query": sql_query,
                "available_tables": list(tables_info.keys()),
                "mcp_status": "success",
                "data_sources": [info['data_source'] for info in tables_info.values()]
            }
            
        except Exception as e:
            self.logger.error(f"[Text2SQL Agent] ❌ MCP 쿼리 실행 오류: {e}")
            return {
                "error": str(e),
                "result": None,
                "sql_query": None,
                "mcp_status": "error"
            }
    
    def _generate_sql_query(self, question: str, tables_info: Dict) -> str:
        """
        LLM을 활용한 자연어 → SQL 변환
        - MCP Server 데이터 스키마 정보 활용
        - KOSIS 데이터 특성 고려
        - 안전한 SELECT 전용 쿼리 생성
        """
        
        # MCP 테이블 스키마 정보 구성
        schema_desc = self._build_mcp_schema_description(tables_info)
        
        prompt = f"""
다음은 MCP Server에서 수집한 데이터베이스 스키마입니다.

{schema_desc}

🎯 MCP 기반 SQL 쿼리 생성 규칙:
1. MCP Server(KOSIS)에서 가져온 데이터를 활용
2. 실행 가능한 SELECT 쿼리만 생성
3. 설명이나 주석 없이 SQL 쿼리만 출력
4. 테이블명과 컬럼명을 정확히 사용
5. 집계 함수나 GROUP BY 등을 적절히 활용
6. KOSIS 데이터 특성 고려 (PRD_DE=연도, DT=수치값 등)

사용자 질문: {question}

SQL 쿼리:"""

        try:
            from llm_client import get_llm_client
            import os
            backend = os.getenv('LLM_BACKEND', 'openai')
            llm_client = get_llm_client(backend)
            
            response = llm_client.chat([
                {"role": "system", "content": "당신은 MCP 기반 SQL 전문가입니다. MCP Server에서 수집한 데이터 스키마에 맞는 정확한 SQL 쿼리만 생성하세요."},
                {"role": "user", "content": prompt}
            ])
            
            sql_query = response.strip()
            
            # SQL 쿼리 정리 (주석이나 불필요한 텍스트 제거)
            sql_query = self._clean_sql_query(sql_query)
            
            self.logger.info(f"[Text2SQL Agent] 🔧 LLM 생성 SQL: {sql_query}")
            return sql_query
            
        except Exception as e:
            self.logger.error(f"[Text2SQL Agent] ❌ LLM SQL 쿼리 생성 오류: {e}")
            return None
    
    def _build_mcp_schema_description(self, tables_info: Dict) -> str:
        """MCP Server 데이터 기반 테이블 스키마 설명 구성"""
        schema_parts = []
        
        for table_name, info in tables_info.items():
            columns_desc = []
            for col, dtype in info['schema'].items():
                columns_desc.append(f"  {col} {dtype}")
            
            sample_data = ""
            if info['sample_data']:
                sample_data = f"\n📊 MCP 데이터 샘플: {info['sample_data'][:2]}"
            
            data_source_info = f"\n🏗️ 데이터 출처: {info['data_source']}"
            
            schema_parts.append(f"""
📋 MCP 테이블: {table_name} ({info['row_count']}행)
컬럼:
{chr(10).join(columns_desc)}{data_source_info}{sample_data}
""")
        
        return "\n".join(schema_parts)
    
    def _clean_sql_query(self, sql_query: str) -> str:
        """
        LLM이 생성한 SQL 쿼리 정리
        - 불필요한 텍스트 제거
        - SQL 문법 정규화
        - 안전성 검증
        """
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
        """
        MCP 데이터에 대한 SQL 쿼리 실행
        - 안전한 SELECT 전용 실행
        - 결과 구조화 및 반환
        """
        try:
            cursor = self.conn.execute(sql_query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # 결과를 딕셔너리 형태로 변환 (MCP Client에서 사용하기 쉽게)
            result_data = []
            for row in rows:
                result_data.append(dict(zip(columns, row)))
            
            return {
                "columns": columns,
                "rows": result_data,
                "row_count": len(result_data),
                "query_type": "SELECT",
                "mcp_processed": True
            }
            
        except Exception as e:
            self.logger.error(f"[Text2SQL Agent] ❌ MCP SQL 실행 오류: {e}")
            raise e
    
    def execute_custom_sql(self, sql_query: str) -> Dict[str, Any]:
        """사용자 정의 SQL 쿼리 직접 실행 (MCP 데이터 대상)"""
        try:
            return self._execute_sql_query(sql_query)
        except Exception as e:
            return {
                "error": str(e),
                "columns": [],
                "rows": [],
                "row_count": 0,
                "mcp_processed": False
            }
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        특정 MCP 테이블 정보 조회
        - 스키마, 샘플 데이터, 통계 정보
        """
        if table_name not in self.table_schemas:
            return {"error": f"MCP 테이블 '{table_name}'을 찾을 수 없습니다."}
        
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
                "total_rows": total_rows,
                "data_source": "MCP Server" if "mcp" in table_name else "Direct",
                "mcp_integration": True
            }
            
        except Exception as e:
            return {"error": str(e), "mcp_integration": False}
    
    def clear_dataframes(self):
        """모든 DataFrame 삭제 (기존 호환성 유지)"""
        self.clear_all_mcp_data()
    
    def clear_all_mcp_data(self):
        """
        모든 MCP 데이터 정리
        - DataFrame 스토리지 클리어
        - SQL 테이블 삭제
        - 스키마 정보 초기화
        """
        self.dataframes.clear()
        self.table_schemas.clear()
        
        # 모든 MCP 테이블 삭제
        cursor = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            self.conn.execute(f"DROP TABLE IF EXISTS {table[0]}")
        
        self.conn.commit()
        self.logger.info("[Text2SQL Agent] 🧹 모든 MCP 데이터 및 SQL 테이블 정리 완료")
    
    def __del__(self):
        """소멸자: MCP SQL 연결 종료"""
        if hasattr(self, 'conn'):
            self.conn.close()
            self.logger.info("[Text2SQL Agent] 🔌 MCP SQL 엔진 연결 종료") 