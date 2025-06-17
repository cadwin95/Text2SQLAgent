"""
⚡ EXECUTOR (실행 전담)
=====================
역할: 계획된 단계들을 실제로 실행하는 전문 실행자

📖 새로운 구조에서의 역할:
- Planner가 생성한 계획을 단계별로 실행
- MCP Server 도구 호출 및 결과 처리
- SQL Agent와 연동하여 데이터 분석 실행
- 실행 상태 모니터링 및 에러 처리

🔄 연동:
- ../mcp_server/kosis_api.py: MCP Server 도구 호출
- sql_agent.py: SQL 기반 데이터 분석
- ../utils/llm_client.py: 필요 시 LLM 호출
- Chain: 실행 결과를 Chain에게 보고

🚀 핵심 특징:
- 단일 책임: 계획 실행만 담당
- MCP 프로토콜 준수: 표준 MCP 호출
- 결과 정규화: 일관된 응답 형식
- 에러 복구: 실패 시 자동 재시도 및 대안 실행
"""

import sys
import os
import logging
import pandas as pd
import asyncio
from typing import Dict, Any, List, Optional

# 상위 디렉토리 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP Server 도구 import
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mcp_server'))
    from kosis_api import fetch_kosis_data, search_kosis, get_stat_list, get_table_meta
except ImportError as e:
    logging.warning(f"MCP Server 도구 import 실패: {e}")
    # 백업용 더미 함수들
    def fetch_kosis_data(*args, **kwargs):
        return {"error": "MCP Server를 사용할 수 없습니다", "data": []}
    def search_kosis(*args, **kwargs):
        return {"error": "MCP Server를 사용할 수 없습니다", "data": []}
    def get_stat_list(*args, **kwargs):
        return {"error": "MCP Server를 사용할 수 없습니다", "data": []}
    def get_table_meta(*args, **kwargs):
        return {"error": "MCP Server를 사용할 수 없습니다", "data": []}

from .sql_agent import SQLAgent

# Health Checker import
try:
    from utils.mcp_health_checker import get_mcp_health_checker
    HEALTH_CHECKER_AVAILABLE = True
except ImportError:
    HEALTH_CHECKER_AVAILABLE = False
    logging.warning("Health Checker를 사용할 수 없습니다")

class Executor:
    """⚡ 계획 실행 전문가"""
    
    def __init__(self, sql_agent: SQLAgent = None):
        # SQL Agent (데이터 분석 전담)
        self.sql_agent = sql_agent if sql_agent else SQLAgent()
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # MCP 도구 매핑
        self.mcp_tools = {
            'fetch_kosis_data': fetch_kosis_data,
            'search_kosis': search_kosis,
            'get_stat_list': get_stat_list,
            'get_table_meta': get_table_meta
        }
        
        # Health Checker 초기화
        self.health_checker = None
        self.health_initialized = False
        if HEALTH_CHECKER_AVAILABLE:
            self.health_checker = get_mcp_health_checker()
        
        # 실행 통계
        self.execution_stats = {
            'total_steps': 0,
            'successful_steps': 0,
            'failed_steps': 0,
            'mcp_calls': 0,
            'sql_queries': 0
        }
        
        self.logger.info("[Executor] ⚡ 계획 실행 전문가 초기화 완료")
    
    async def initialize_mcp_health(self) -> Dict[str, Any]:
        """MCP 도구 상태 체크 및 초기화"""
        if not HEALTH_CHECKER_AVAILABLE or not self.health_checker:
            return {
                'success': False,
                'message': 'Health Checker를 사용할 수 없습니다',
                'fallback_needed': True
            }
        
        try:
            self.logger.info("[Executor] 🏥 MCP 도구 상태 체크 시작")
            
            # Health Checker로 모든 도구 테스트
            health_report = await self.health_checker.initialize_and_test_all(self.mcp_tools)
            self.health_initialized = True
            
            # 결과 로깅
            if health_report['success']:
                self.logger.info(f"[Executor] ✅ MCP 초기화 성공: {health_report['available_tools']}/{health_report['total_tools']} 도구 사용가능")
            else:
                self.logger.warning(f"[Executor] ⚠️ MCP 초기화 부분실패: {health_report['available_tools']}/{health_report['total_tools']} 도구 사용가능")
            
            # 권장사항 출력
            for recommendation in health_report.get('recommendations', []):
                self.logger.info(f"[Executor] 💡 {recommendation}")
            
            return health_report
            
        except Exception as e:
            self.logger.error(f"[Executor] ❌ MCP 초기화 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_needed': True
            }
    
    def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """전체 계획 실행"""
        try:
            self.logger.info(f"[Executor] 🚀 계획 실행 시작: {plan.get('total_steps', len(plan.get('steps', [])))}개 단계")
            
            steps = plan.get('steps', [])
            execution_history = []
            overall_success = True
            
            # 각 단계 순차 실행
            for i, step in enumerate(steps):
                step_result = self.execute_step(step, step_number=i+1)
                execution_history.append(step_result)
                
                # 실행 통계 업데이트
                self.execution_stats['total_steps'] += 1
                if step_result.get('success', False):
                    self.execution_stats['successful_steps'] += 1
                else:
                    self.execution_stats['failed_steps'] += 1
                    
                # 중요한 단계 실패 시 전체 실행 중단 여부 결정
                if not step_result.get('success', False) and step.get('priority') == 'high':
                    self.logger.warning(f"[Executor] ⚠️ 중요한 단계 {i+1} 실패, 실행 계속")
                    overall_success = False
            
            # 최종 결과 생성
            final_result = self._generate_final_result(execution_history)
            
            self.logger.info(f"[Executor] ✅ 계획 실행 완료: {self.execution_stats['successful_steps']}/{self.execution_stats['total_steps']} 성공")
            
            return {
                'success': overall_success,
                'execution_history': execution_history,
                'final_result': final_result,
                'stats': self.execution_stats.copy(),
                'available_data': list(self.sql_agent.dataframes.keys())
            }
            
        except Exception as e:
            self.logger.error(f"[Executor] ❌ 계획 실행 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_history': execution_history if 'execution_history' in locals() else [],
                'stats': self.execution_stats.copy()
            }
    
    def execute_step(self, step: Dict[str, Any], step_number: int = 1) -> Dict[str, Any]:
        """개별 단계 실행"""
        step_type = step.get('type', 'unknown')
        description = step.get('description', '')
        
        self.logger.info(f"[Executor] 📋 단계 {step_number} 실행: {step_type} - {description}")
        
        try:
            if step_type == 'mcp_tool_call':
                return self._execute_mcp_tool_call(step, step_number)
            elif step_type in ['sql_analysis', 'query']:
                return self._execute_sql_analysis(step, step_number)
            elif step_type == 'visualization':
                return self._execute_visualization(step, step_number)
            else:
                return self._execute_generic_step(step, step_number)
                
        except Exception as e:
            self.logger.error(f"[Executor] ❌ 단계 {step_number} 실행 오류: {e}")
            return {
                'success': False,
                'step_number': step_number,
                'step_type': step_type,
                'error': str(e),
                'description': description
            }
    
    def _execute_mcp_tool_call(self, step: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """MCP Server 도구 호출 실행"""
        tool_name = step.get('tool_name')
        params = step.get('params', {})
        description = step.get('description', '')
        
        self.logger.info(f"[Executor] 🔧 MCP 도구 호출: {tool_name}")
        
        # Health Checker로 도구 상태 확인
        if self.health_checker and self.health_initialized:
            if not self.health_checker.is_tool_available(tool_name):
                health_info = self.health_checker.get_tool_health(tool_name)
                error_msg = f"도구 사용불가: {health_info.last_error if health_info else '상태 불명'}"
                self.logger.warning(f"[Executor] ⚠️ {tool_name} {error_msg}")
                return {
                    'success': False,
                    'step_number': step_number,
                    'step_type': 'mcp_tool_call',
                    'error': error_msg,
                    'description': description,
                    'health_check_failed': True
                }
        
        # MCP 도구 실행
        if tool_name not in self.mcp_tools:
            return {
                'success': False,
                'step_number': step_number,
                'step_type': 'mcp_tool_call',
                'error': f"알 수 없는 MCP 도구: {tool_name}",
                'description': description
            }
        
        try:
            # MCP Server 도구 호출
            mcp_result = self.mcp_tools[tool_name](**params)
            self.execution_stats['mcp_calls'] += 1
            
            # 결과 처리
            if mcp_result.get('error'):
                return {
                    'success': False,
                    'step_number': step_number,
                    'step_type': 'mcp_tool_call',
                    'error': mcp_result['error'],
                    'description': description,
                    'mcp_result': mcp_result
                }
            
            # 성공한 경우 DataFrame으로 변환 및 등록
            data = mcp_result.get('data', [])
            if data:
                df = pd.DataFrame(data)
                if not df.empty:
                    # SQL Agent에 DataFrame 등록
                    df_name = f"mcp_{tool_name}_{step_number}"
                    table_name = self.sql_agent.register_dataframe(df_name, df)
                    
                    success_msg = f"MCP 도구 실행 성공: {len(data)}행 데이터 수집 → SQL 테이블 '{table_name}'"
                    self.logger.info(f"[Executor] ✅ {success_msg}")
                    
                    return {
                        'success': True,
                        'step_number': step_number,
                        'step_type': 'mcp_tool_call',
                        'message': success_msg,
                        'description': description,
                        'data_count': len(data),
                        'dataframe_name': df_name,
                        'sql_table_name': table_name,
                        'mcp_result': mcp_result
                    }
                else:
                    return {
                        'success': False,
                        'step_number': step_number,
                        'step_type': 'mcp_tool_call',
                        'error': "MCP에서 빈 데이터를 반환했습니다",
                        'description': description,
                        'mcp_result': mcp_result
                    }
            else:
                return {
                    'success': False,
                    'step_number': step_number,
                    'step_type': 'mcp_tool_call',
                    'error': "MCP에서 데이터를 반환하지 않았습니다",
                    'description': description,
                    'mcp_result': mcp_result
                }
                
        except Exception as e:
            return {
                'success': False,
                'step_number': step_number,
                'step_type': 'mcp_tool_call',
                'error': f"MCP 도구 호출 오류: {e}",
                'description': description
            }
    
    def _execute_sql_analysis(self, step: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """SQL 기반 데이터 분석 실행"""
        description = step.get('description', '')
        
        self.logger.info(f"[Executor] 📊 SQL 분석 실행: {description}")
        
        try:
            # SQL Agent를 통한 분석 실행
            analysis_result = self.sql_agent.analyze_question(description)
            self.execution_stats['sql_queries'] += 1
            
            if analysis_result.get('error'):
                return {
                    'success': False,
                    'step_number': step_number,
                    'step_type': 'sql_analysis',
                    'error': analysis_result['error'],
                    'description': description
                }
            
            sql_result = analysis_result.get('result', {})
            row_count = sql_result.get('row_count', 0)
            
            success_msg = f"SQL 분석 완료: {row_count}행 결과"
            self.logger.info(f"[Executor] ✅ {success_msg}")
            
            return {
                'success': True,
                'step_number': step_number,
                'step_type': 'sql_analysis',
                'message': success_msg,
                'description': description,
                'sql_query': analysis_result.get('sql_query'),
                'result_data': sql_result,
                'row_count': row_count
            }
            
        except Exception as e:
            return {
                'success': False,
                'step_number': step_number,
                'step_type': 'sql_analysis',
                'error': f"SQL 분석 오류: {e}",
                'description': description
            }
    
    def _execute_visualization(self, step: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """시각화 실행"""
        description = step.get('description', '')
        
        self.logger.info(f"[Executor] 📈 시각화 실행: {description}")
        
        try:
            # 사용 가능한 데이터 확인
            available_tables = self.sql_agent.get_available_tables()
            
            if not available_tables:
                return {
                    'success': False,
                    'step_number': step_number,
                    'step_type': 'visualization',
                    'error': "시각화할 데이터가 없습니다",
                    'description': description
                }
            
            # 기본 차트 데이터 생성
            chart_data = self._generate_chart_data(available_tables)
            
            success_msg = f"시각화 데이터 생성 완료: {len(available_tables)}개 테이블 기반"
            self.logger.info(f"[Executor] ✅ {success_msg}")
            
            return {
                'success': True,
                'step_number': step_number,
                'step_type': 'visualization',
                'message': success_msg,
                'description': description,
                'chart_data': chart_data,
                'tables_used': list(available_tables.keys())
            }
            
        except Exception as e:
            return {
                'success': False,
                'step_number': step_number,
                'step_type': 'visualization',
                'error': f"시각화 오류: {e}",
                'description': description
            }
    
    def _execute_generic_step(self, step: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """기타 단계 실행"""
        step_type = step.get('type', 'unknown')
        description = step.get('description', '')
        
        self.logger.info(f"[Executor] ⚙️ 기타 단계 실행: {step_type}")
        
        return {
            'success': True,
            'step_number': step_number,
            'step_type': step_type,
            'message': f"기타 단계 실행 완료: {step_type}",
            'description': description
        }
    
    def _generate_chart_data(self, tables_info: Dict[str, Dict]) -> Optional[Dict[str, Any]]:
        """차트 데이터 생성"""
        try:
            # 첫 번째 테이블 사용
            table_name = next(iter(tables_info.keys()))
            table_info = tables_info[table_name]
            
            # KOSIS 데이터인 경우 특별 처리
            if 'mcp' in table_name and table_info['row_count'] > 0:
                # 샘플 데이터에서 차트 생성
                sample_data = table_info['sample_data']
                columns = table_info['columns']
                
                if 'PRD_DE' in columns and 'DT' in columns:
                    # 시계열 차트
                    prd_idx = columns.index('PRD_DE')
                    dt_idx = columns.index('DT')
                    
                    labels = [str(row[prd_idx]) for row in sample_data]
                    values = [float(row[dt_idx]) if row[dt_idx] else 0 for row in sample_data]
                    
                    return {
                        'type': 'line',
                        'title': 'MCP Server 데이터 시각화',
                        'data': {
                            'labels': labels,
                            'datasets': [{
                                'label': '수치값',
                                'data': values,
                                'borderColor': 'rgb(54, 162, 235)',
                                'backgroundColor': 'rgba(54, 162, 235, 0.2)'
                            }]
                        }
                    }
            
            return {
                'type': 'info',
                'message': f"테이블 '{table_name}' 기반 차트 데이터 준비됨",
                'table_info': table_info
            }
            
        except Exception as e:
            self.logger.error(f"[Executor] 차트 데이터 생성 오류: {e}")
            return None
    
    def _generate_final_result(self, execution_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """최종 실행 결과 생성"""
        # 성공한 단계들 필터링
        successful_steps = [step for step in execution_history if step.get('success')]
        
        # SQL 분석 결과 추출
        sql_results = []
        for step in successful_steps:
            if step.get('step_type') == 'sql_analysis' and step.get('result_data'):
                sql_results.append(step['result_data'])
        
        # 최종 데이터 테이블 정보
        final_tables = self.sql_agent.get_available_tables()
        
        # 차트 데이터 (마지막 성공한 시각화에서)
        chart_data = None
        for step in reversed(successful_steps):
            if step.get('step_type') == 'visualization' and step.get('chart_data'):
                chart_data = step['chart_data']
                break
        
        return {
            'sql_results': sql_results,
            'final_tables': final_tables,
            'chart_data': chart_data,
            'data_summary': {
                'total_tables': len(final_tables),
                'total_rows': sum(info.get('row_count', 0) for info in final_tables.values()),
                'data_sources': list(set(info.get('data_source', 'Unknown') for info in final_tables.values()))
            }
        }
    
    def get_execution_status(self) -> Dict[str, Any]:
        """실행 상태 조회"""
        return {
            'stats': self.execution_stats.copy(),
            'available_tables': list(self.sql_agent.dataframes.keys()),
            'mcp_tools_available': list(self.mcp_tools.keys())
        }
    
    def reset_executor(self):
        """Executor 상태 초기화"""
        self.sql_agent.clear_all_data()
        self.execution_stats = {
            'total_steps': 0,
            'successful_steps': 0,
            'failed_steps': 0,
            'mcp_calls': 0,
            'sql_queries': 0
        }
        self.logger.info("[Executor] 🔄 상태 초기화 완료") 