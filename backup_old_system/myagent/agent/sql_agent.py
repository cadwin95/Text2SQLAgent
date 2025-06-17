"""
🗃️ SQL AGENT (독립형)
====================
역할: DataFrame 데이터를 SQL로 분석하는 전문 에이전트

📖 새로운 구조에서의 역할:
- MCP Server에서 수집한 데이터를 SQL 테이블로 관리
- 자연어 질문을 SQL 쿼리로 변환 (LLM 활용)
- 메모리 내 SQLite로 고성능 쿼리 실행
- Executor에서 호출되어 데이터 분석 담당

🔄 연동:
- ../utils/llm_client.py: LLM 기반 SQL 생성
- Executor: MCP 데이터 처리 요청
- Chain: 전체 워크플로우에서 SQL 분석 담당

🚀 핵심 특징:
- 독립적인 SQL 엔진
- 자동 스키마 감지 및 변환
- 안전한 SELECT 전용 실행
- MCP 데이터 특별 처리
"""

import pandas as pd
import sqlite3
import logging
import sys
import os
from typing import Dict, Any, List, Optional

# 상위 디렉토리의 utils 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import get_llm_client, create_chat_messages, extract_json_from_response

class SQLAgent:
    """
    🗃️ SQL 분석 전문 에이전트
    
    새로운 아키텍처에서의 역할:
    - MCP Server 데이터 → SQL 테이블 변환
    - LLM 기반 자연어 → SQL 쿼리 변환
    - 고성능 메모리 내 SQL 실행
    - 결과 구조화 및 반환
    """
    
    def __init__(self, llm_backend: str = None):
        # DataFrame 저장소
        self.dataframes: Dict[str, pd.DataFrame] = {}
        
        # 메모리 내 SQLite 연결
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # 테이블 스키마 정보
        self.table_schemas: Dict[str, Dict[str, str]] = {}
        
        # LLM 클라이언트
        self.llm_client = get_llm_client(llm_backend)
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("[SQL Agent] 🗃️ 독립형 SQL 엔진 초기화 완료")
    
    def register_dataframe(self, name: str, df: pd.DataFrame) -> str:
        """MCP Server에서 가져온 DataFrame을 SQL 테이블로 등록"""
        try:
            # DataFrame 저장
            self.dataframes[name] = df.copy()
            
            # 테이블명 정규화
            table_name = self._normalize_table_name(name)
            
            # SQLite에 테이블로 저장
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            
            # 스키마 정보 저장
            self.table_schemas[table_name] = self._get_table_schema(df)
            
            self.logger.info(f"[SQL Agent] ✅ DataFrame 등록: {name} → {table_name} ({len(df)}행)")
            return table_name
            
        except Exception as e:
            self.logger.error(f"[SQL Agent] ❌ DataFrame 등록 오류: {e}")
            return None
    
    def _normalize_table_name(self, name: str) -> str:
        """테이블명을 SQL 친화적으로 변환"""
        import re
        
        # MCP KOSIS 데이터 특별 처리
        if 'mcp_kosis' in name.lower() or 'kosis' in name.lower():
            if 'DT_1B040A3' in name:
                return 'mcp_population_stats'
            elif 'DT_1DA7001' in name:
                return 'mcp_gdp_stats'
            else:
                return 'mcp_kosis_data'
        
        # 일반적인 정규화
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
        return cleaned[:63]  # SQLite 제한
    
    def _get_table_schema(self, df: pd.DataFrame) -> Dict[str, str]:
        """DataFrame 스키마 분석"""
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
        """사용 가능한 SQL 테이블 정보"""
        tables_info = {}
        
        for table_name, schema in self.table_schemas.items():
            # 테이블 정보 조회
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # 샘플 데이터
            cursor = self.conn.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # 데이터 출처 판별
            data_source = "MCP Server" if "mcp" in table_name else "Direct Import"
            
            tables_info[table_name] = {
                'schema': schema,
                'row_count': row_count,
                'columns': columns,
                'sample_data': sample_rows,
                'data_source': data_source
            }
        
        return tables_info
    
    def analyze_question(self, question: str) -> Dict[str, Any]:
        """자연어 질문을 SQL 쿼리로 변환하고 실행"""
        try:
            # 사용 가능한 테이블 확인
            tables_info = self.get_available_tables()
            
            if not tables_info:
                return {
                    "error": "등록된 데이터 테이블이 없습니다. 먼저 MCP Server에서 데이터를 로드해주세요.",
                    "sql_query": None,
                    "result": None
                }
            
            self.logger.info(f"[SQL Agent] 🔍 SQL 쿼리 생성: {question}")
            
            # LLM으로 SQL 쿼리 생성
            sql_query = self._generate_sql_query(question, tables_info)
            
            if not sql_query:
                return {
                    "error": "SQL 쿼리 생성에 실패했습니다.",
                    "sql_query": None,
                    "result": None
                }
            
            # SQL 쿼리 실행
            result = self._execute_sql_query(sql_query)
            
            self.logger.info(f"[SQL Agent] ✅ SQL 쿼리 실행 완료: {len(result.get('rows', []))}행")
            
            return {
                "error": None,
                "sql_query": sql_query,
                "result": result,
                "available_tables": list(tables_info.keys()),
                "data_sources": [info['data_source'] for info in tables_info.values()]
            }
            
        except Exception as e:
            self.logger.error(f"[SQL Agent] ❌ 질문 분석 오류: {e}")
            return {
                "error": str(e),
                "sql_query": None,
                "result": None
            }
    
    def _generate_sql_query(self, question: str, tables_info: Dict) -> str:
        """LLM을 활용한 SQL 쿼리 생성"""
        
        # 테이블 스키마 설명 생성
        schema_desc = self._build_schema_description(tables_info)
        
        system_prompt = """
당신은 SQL 쿼리 생성 전문가입니다.

규칙:
1. 주어진 테이블 스키마에 맞는 정확한 SELECT 쿼리만 생성
2. 테이블명과 컬럼명을 정확히 사용
3. 집계 함수, GROUP BY, ORDER BY 등을 적절히 활용
4. KOSIS 데이터의 경우 PRD_DE=연도, DT=수치값 고려
5. 설명 없이 SQL 쿼리만 출력

JSON 형식으로 응답:
{
  "sql_query": "SELECT ... FROM ..."
}
"""
        
        user_prompt = f"""
데이터베이스 스키마:
{schema_desc}

사용자 질문: {question}

위 스키마를 기반으로 SQL 쿼리를 생성해주세요.
"""
        
        try:
            messages = create_chat_messages(system_prompt, user_prompt)
            response = self.llm_client.chat(messages, max_tokens=300)
            
            # JSON에서 SQL 쿼리 추출
            json_result = extract_json_from_response(response)
            if json_result and 'sql_query' in json_result:
                sql_query = json_result['sql_query']
            else:
                # Fallback: 응답에서 직접 SQL 추출
                sql_query = self._extract_sql_from_text(response)
            
            # SQL 쿼리 정리
            sql_query = self._clean_sql_query(sql_query)
            
            self.logger.info(f"[SQL Agent] 🔧 생성된 SQL: {sql_query}")
            return sql_query
            
        except Exception as e:
            self.logger.error(f"[SQL Agent] ❌ LLM SQL 생성 오류: {e}")
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
                sample_data = f"\n📊 샘플 데이터: {info['sample_data'][:2]}"
            
            schema_parts.append(f"""
📋 테이블: {table_name} ({info['row_count']}행)
출처: {info['data_source']}
컬럼:
{chr(10).join(columns_desc)}{sample_data}
""")
        
        return "\n".join(schema_parts)
    
    def _extract_sql_from_text(self, text: str) -> str:
        """텍스트에서 SQL 쿼리 추출"""
        import re
        
        # SQL 블록 찾기
        sql_match = re.search(r'```sql\s*(.*?)\s*```', text, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        
        # SELECT로 시작하는 부분 찾기
        if 'SELECT' in text.upper():
            lines = text.split('\n')
            sql_lines = []
            in_sql = False
            
            for line in lines:
                if 'SELECT' in line.upper():
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                    if ';' in line:
                        break
            
            return ' '.join(sql_lines).replace(';', '').strip()
        
        return text.strip()
    
    def _clean_sql_query(self, sql_query: str) -> str:
        """SQL 쿼리 정리"""
        import re
        
        # 여러 줄을 한 줄로
        sql_query = ' '.join(sql_query.split())
        
        # 주석 제거
        sql_query = re.sub(r'--[^\n]*', '', sql_query)
        sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
        
        # 불필요한 공백 제거
        sql_query = re.sub(r'\s+', ' ', sql_query).strip()
        
        # 세미콜론 제거
        sql_query = sql_query.rstrip(';')
        
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
                "query_executed": sql_query
            }
            
        except Exception as e:
            self.logger.error(f"[SQL Agent] ❌ SQL 실행 오류: {e}")
            raise e
    
    def clear_all_data(self):
        """모든 데이터 정리"""
        self.dataframes.clear()
        self.table_schemas.clear()
        
        # 테이블 삭제
        cursor = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            self.conn.execute(f"DROP TABLE IF EXISTS {table[0]}")
        
        self.conn.commit()
        self.logger.info("[SQL Agent] 🧹 모든 데이터 정리 완료")
    
    def __del__(self):
        """소멸자"""
        if hasattr(self, 'conn'):
            self.conn.close() 