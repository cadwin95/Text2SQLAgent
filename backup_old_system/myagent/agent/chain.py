"""
🔗 CHAIN (전체 워크플로우 조율)
=============================
역할: Plan-Execute-Reflect 사이클을 조율하는 마스터 컨트롤러

📖 새로운 구조에서의 역할:
- Planner → Executor → Reflector 워크플로우 관리
- 각 모듈 간 데이터 전달 및 상태 동기화
- 재계획 사이클 제어 및 최적화
- 최종 결과 통합 및 포맷팅

🔄 연동:
- planner.py: 분석 계획 수립 요청
- executor.py: 계획 실행 및 결과 수집
- reflector.py: 결과 분석 및 재계획 판단
- sql_agent.py: SQL 분석 엔진 관리

🚀 핵심 특징:
- 마스터 조율자: 전체 에이전트 생명주기 관리
- 적응적 실행: 실행 중 동적 조정 및 최적화
- 품질 보장: 최소 품질 기준 충족 시까지 반복
- 효율성: 불필요한 재실행 방지 및 성능 최적화
"""

import sys
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional

# 동일 디렉토리 모듈들 import
from .planner import Planner
from .executor import Executor  
from .reflector import Reflector
from .sql_agent import SQLAgent

class Chain:
    """
    🔗 Plan-Execute-Reflect 마스터 체인
    
    새로운 아키텍처에서의 역할:
    - 전체 워크플로우 생명주기 관리
    - 모듈 간 데이터 흐름 제어
    - 품질 기준 기반 반복 실행
    - 최적화된 결과 도출
    """
    
    def __init__(self, llm_backend: str = None, max_iterations: int = 3):
        # 핵심 에이전트들 초기화
        self.sql_agent = SQLAgent(llm_backend)
        self.planner = Planner(llm_backend)
        self.executor = Executor(self.sql_agent)
        self.reflector = Reflector(llm_backend)
        
        # 체인 설정
        self.max_iterations = max_iterations
        self.quality_threshold = 0.7  # 최소 품질 기준
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 실행 기록
        self.execution_history = []
        self.current_iteration = 0
        
        # MCP 건강 상태
        self.mcp_health_report = None
        self.mcp_initialized = False
        
        self.logger.info("[Chain] 🔗 Plan-Execute-Reflect 체인 초기화 완료")
        self.logger.info(f"[Chain] 📊 구성: Planner → Executor → Reflector (최대 {max_iterations}회 반복)")
    
    async def initialize_mcp_system(self) -> Dict[str, Any]:
        """MCP 시스템 초기화 및 건강 상태 체크"""
        try:
            self.logger.info("[Chain] 🏥 MCP 시스템 초기화 시작")
            
            # Executor의 MCP 건강 상태 체크
            health_report = await self.executor.initialize_mcp_health()
            self.mcp_health_report = health_report
            self.mcp_initialized = True
            
            # 건강 상태 로깅
            if health_report.get('success'):
                self.logger.info(f"[Chain] ✅ MCP 시스템 준비완료: {health_report.get('available_tools', 0)}개 도구 사용가능")
            else:
                self.logger.warning(f"[Chain] ⚠️ MCP 시스템 부분실패: {health_report.get('error', '알 수 없는 오류')}")
                
            # 폴백 모드 여부
            if health_report.get('fallback_needed'):
                self.logger.warning("[Chain] 🚨 폴백 모드로 실행됩니다")
            
            return health_report
            
        except Exception as e:
            self.logger.error(f"[Chain] ❌ MCP 시스템 초기화 실패: {e}")
            self.mcp_health_report = {
                'success': False,
                'error': str(e),
                'fallback_needed': True
            }
            return self.mcp_health_report
    
    def run(self, question: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        전체 Plan-Execute-Reflect 체인 실행
        
        Parameters:
        - question: 사용자 질문
        - context: 추가 컨텍스트 정보
        
        Returns:
        - 최종 분석 결과 및 실행 기록
        """
        try:
            self.logger.info(f"[Chain] 🚀 체인 실행 시작: {question}")
            
            # 초기화
            self.current_iteration = 0
            self.execution_history = []
            
            if context is None:
                context = {}
            
            # 첫 번째 계획 수립
            plan_result = self.planner.create_analysis_plan(question, context)
            
            if not plan_result.get('success'):
                return self._create_error_result(f"계획 수립 실패: {plan_result.get('error')}", question)
            
            current_plan = plan_result['plan']
            best_result = None
            best_score = 0
            
            # Plan-Execute-Reflect 반복 사이클
            for iteration in range(1, self.max_iterations + 1):
                self.current_iteration = iteration
                self.logger.info(f"[Chain] 🔄 반복 {iteration}/{self.max_iterations} 시작")
                
                # EXECUTE: 계획 실행
                execution_result = self.executor.execute_plan(current_plan)
                
                # REFLECT: 실행 결과 분석
                reflection_result = self.reflector.analyze_execution_result(execution_result, question)
                
                # 반복 기록 저장
                iteration_record = {
                    'iteration': iteration,
                    'plan': current_plan,
                    'execution_result': execution_result,
                    'reflection_result': reflection_result,
                    'timestamp': __import__('time').time()
                }
                self.execution_history.append(iteration_record)
                
                # 품질 평가
                current_score = self._extract_quality_score(reflection_result)
                
                # 최고 결과 업데이트
                if current_score > best_score:
                    best_score = current_score
                    best_result = execution_result
                
                self.logger.info(f"[Chain] 📊 반복 {iteration} 결과: 점수 {current_score:.2f}")
                
                # 품질 기준 충족 시 종료
                if current_score >= self.quality_threshold:
                    self.logger.info(f"[Chain] ✅ 품질 기준 달성: {current_score:.2f} >= {self.quality_threshold}")
                    break
                
                # 재계획 필요성 판단
                if not reflection_result.get('needs_replanning', False):
                    self.logger.info(f"[Chain] 📋 재계획 불필요, 현재 결과로 종료")
                    break
                
                # 마지막 반복이 아닌 경우 재계획
                if iteration < self.max_iterations:
                    replan_result = self.reflector.generate_replan(
                        reflection_result.get('analysis_result', {}), 
                        question
                    )
                    
                    if replan_result.get('success'):
                        current_plan = replan_result['replan']
                        self.logger.info(f"[Chain] 🔄 재계획 완료: {len(current_plan.get('steps', []))}개 단계")
                    else:
                        self.logger.warning(f"[Chain] ⚠️ 재계획 실패, 최고 결과로 종료")
                        break
            
            # 최종 결과 생성
            final_result = self._generate_final_result(best_result, best_score, question)
            
            self.logger.info(f"[Chain] 🎯 체인 실행 완료: {self.current_iteration}회 반복, 최고 점수 {best_score:.2f}")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"[Chain] ❌ 체인 실행 오류: {e}")
            return self._create_error_result(str(e), question)
    
    def _extract_quality_score(self, reflection_result: Dict[str, Any]) -> float:
        """반성 결과에서 품질 점수 추출"""
        try:
            if not reflection_result.get('success'):
                return 0.0
            
            analysis_result = reflection_result.get('analysis_result', {})
            overall_assessment = analysis_result.get('overall_assessment', {})
            return overall_assessment.get('total_score', 0.0)
            
        except Exception:
            return 0.0
    
    def _generate_final_result(self, best_execution_result: Dict[str, Any], best_score: float, question: str) -> Dict[str, Any]:
        """최종 결과 생성"""
        
        if not best_execution_result:
            return self._create_error_result("실행 결과가 없습니다", question)
        
        final_result = best_execution_result.get('final_result', {})
        
        # 체인 실행 요약
        chain_summary = {
            'total_iterations': self.current_iteration,
            'best_quality_score': best_score,
            'quality_threshold': self.quality_threshold,
            'achieved_quality': best_score >= self.quality_threshold,
            'execution_strategy': 'Plan-Execute-Reflect'
        }
        
        # SQL 결과가 있으면 우선 사용
        sql_results = final_result.get('sql_results', [])
        if sql_results:
            primary_result = sql_results[0]  # 첫 번째 SQL 결과
            result_format = "sql_query_result"
        else:
            # 데이터 테이블 정보 사용
            primary_result = final_result.get('final_tables', {})
            result_format = "table_info"
        
        return {
            'success': True,
            'question': question,
            'result': primary_result,
            'result_format': result_format,
            'chain_summary': chain_summary,
            'execution_history': self.execution_history,
            'final_data': final_result,
            'available_dataframes': list(self.sql_agent.dataframes.keys()),
            'chart_data': final_result.get('chart_data')
        }
    
    def _create_error_result(self, error_message: str, question: str) -> Dict[str, Any]:
        """에러 결과 생성"""
        return {
            'success': False,
            'question': question,
            'error': error_message,
            'chain_summary': {
                'total_iterations': self.current_iteration,
                'best_quality_score': 0.0,
                'achieved_quality': False,
                'execution_strategy': 'Plan-Execute-Reflect'
            },
            'execution_history': self.execution_history
        }
    
    def get_chain_status(self) -> Dict[str, Any]:
        """체인 상태 조회"""
        return {
            'current_iteration': self.current_iteration,
            'max_iterations': self.max_iterations,
            'quality_threshold': self.quality_threshold,
            'total_executions': len(self.execution_history),
            'executor_status': self.executor.get_execution_status(),
            'available_tables': list(self.sql_agent.dataframes.keys())
        }
    
    def reset_chain(self):
        """체인 상태 초기화"""
        self.current_iteration = 0
        self.execution_history = []
        self.executor.reset_executor()
        self.logger.info("[Chain] 🔄 체인 상태 초기화 완료")
    
    def set_quality_threshold(self, threshold: float):
        """품질 기준 설정"""
        if 0.0 <= threshold <= 1.0:
            self.quality_threshold = threshold
            self.logger.info(f"[Chain] 📊 품질 기준 변경: {threshold}")
        else:
            self.logger.warning(f"[Chain] ⚠️ 잘못된 품질 기준: {threshold} (0.0-1.0 범위)")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """실행 요약 정보"""
        if not self.execution_history:
            return {"message": "실행 기록이 없습니다"}
        
        # 점수 변화 추적
        scores = []
        for record in self.execution_history:
            score = self._extract_quality_score(record.get('reflection_result', {}))
            scores.append(score)
        
        # 개선 패턴 분석
        improvement_pattern = "stable"
        if len(scores) >= 2:
            if scores[-1] > scores[0]:
                improvement_pattern = "improving"
            elif scores[-1] < scores[0]:
                improvement_pattern = "declining"
        
        return {
            'total_iterations': len(self.execution_history),
            'quality_scores': scores,
            'improvement_pattern': improvement_pattern,
            'best_iteration': scores.index(max(scores)) + 1 if scores else 0,
            'final_quality': scores[-1] if scores else 0,
            'achieved_threshold': max(scores) >= self.quality_threshold if scores else False
        }
    
    def run_single_execution(self, question: str, custom_plan: Dict[str, Any] = None) -> Dict[str, Any]:
        """단일 실행 (재계획 없이 1회만)"""
        try:
            self.logger.info(f"[Chain] ⚡ 단일 실행: {question}")
            
            # 계획 사용 (커스텀 또는 새로 생성)
            if custom_plan:
                current_plan = custom_plan
            else:
                plan_result = self.planner.create_analysis_plan(question)
                if not plan_result.get('success'):
                    return self._create_error_result(f"계획 수립 실패: {plan_result.get('error')}", question)
                current_plan = plan_result['plan']
            
            # 실행
            execution_result = self.executor.execute_plan(current_plan)
            
            # 결과 포맷팅 (반성 없이)
            final_result = execution_result.get('final_result', {})
            
            return {
                'success': execution_result.get('success', False),
                'question': question,
                'result': final_result,
                'execution_mode': 'single',
                'plan_used': current_plan,
                'execution_stats': execution_result.get('stats', {}),
                'available_dataframes': list(self.sql_agent.dataframes.keys())
            }
            
        except Exception as e:
            self.logger.error(f"[Chain] ❌ 단일 실행 오류: {e}")
            return self._create_error_result(str(e), question) 