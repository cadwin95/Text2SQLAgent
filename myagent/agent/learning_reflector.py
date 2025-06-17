#!/usr/bin/env python3
"""
🧠 학습형 Reflector - 경험을 통해 학습하는 반성 전문가
========================================================
이론적 접근법들을 실제로 구현한 학습형 Reflector입니다.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

@dataclass
class ExecutionExperience:
    """실행 경험 데이터"""
    timestamp: str
    query: str
    plan: Dict[str, Any]
    execution_result: Dict[str, Any]
    quality_score: float
    success_factors: List[str]
    failure_factors: List[str]
    context: Dict[str, Any]

class LearningReflector:
    """🧠 학습형 Reflector - 경험 기반 학습"""
    
    def __init__(self, llm_client, experience_db_path: str = "reflection_experiences.json"):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # 경험 데이터베이스
        self.experiences = []
        self.db_path = experience_db_path
        self.load_experiences()
        
        # 학습 통계
        self.learning_stats = {
            'total_experiences': len(self.experiences),
            'success_patterns': {},
            'failure_patterns': {},
            'improvement_trends': []
        }
        
        self.logger.info("[LearningReflector] 🧠 학습형 반성 전문가 초기화 완료")
    
    def reflect_and_learn(self, query: str, plan: Dict[str, Any], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """반성하면서 학습하기"""
        
        # 1. 기본 품질 평가
        quality_score = self._calculate_quality_score(execution_result)
        
        # 2. 패턴 분석
        success_factors, failure_factors = self._analyze_patterns(query, plan, execution_result)
        
        # 3. 경험 저장
        experience = ExecutionExperience(
            timestamp=datetime.now().isoformat(),
            query=query,
            plan=plan,
            execution_result=execution_result,
            quality_score=quality_score,
            success_factors=success_factors,
            failure_factors=failure_factors,
            context=self._extract_context(query, plan)
        )
        
        self.experiences.append(experience)
        self.save_experiences()
        
        # 4. 학습 기반 개선 제안
        learning_insights = self._generate_learning_insights(experience)
        
        # 5. 개선된 계획 생성
        replan = self._create_improved_plan(query, plan, learning_insights)
        
        self.logger.info(f"[LearningReflector] 🎓 학습 완료: 품질 {quality_score:.2f}")
        
        return {
            'quality_score': quality_score,
            'analysis': self._create_analysis(execution_result, learning_insights),
            'replan': replan,
            'learning_insights': learning_insights,
            'experience_count': len(self.experiences)
        }
    
    def _calculate_quality_score(self, execution_result: Dict[str, Any]) -> float:
        """품질 점수 계산"""
        
        stats = execution_result.get('stats', {})
        total_steps = stats.get('total_steps', 0)
        successful_steps = stats.get('successful_steps', 0)
        
        if total_steps == 0:
            return 0.0
        
        # 기본 성공률
        success_rate = successful_steps / total_steps
        
        # 데이터 수집 보너스
        available_data = execution_result.get('available_data', [])
        data_bonus = len(available_data) * 0.2
        
        # MCP 호출 성공 보너스
        mcp_calls = stats.get('mcp_calls', 0)
        mcp_bonus = min(0.3, mcp_calls * 0.1)
        
        return min(1.0, success_rate + data_bonus + mcp_bonus)
    
    def _analyze_patterns(self, query: str, plan: Dict[str, Any], execution_result: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """패턴 분석"""
        
        success_factors = []
        failure_factors = []
        
        # 쿼리 패턴 분석
        if 'KOSIS' in query:
            success_factors.append('kosis_query_pattern')
        if any(word in query for word in ['검색', '조회', '분석']):
            success_factors.append('multi_action_query')
        
        # 실행 결과 패턴 분석
        execution_history = execution_result.get('execution_history', [])
        
        for step in execution_history:
            if step.get('success', False):
                step_type = step.get('step_type', '')
                if step_type == 'mcp_tool_call':
                    success_factors.append('successful_mcp_call')
                elif step_type == 'sql_analysis':
                    success_factors.append('successful_sql_analysis')
            else:
                error = step.get('error', '')
                if 'MCP' in error:
                    failure_factors.append('mcp_connection_failure')
                elif 'timeout' in error.lower():
                    failure_factors.append('timeout_failure')
                else:
                    failure_factors.append('general_execution_failure')
        
        return success_factors, failure_factors
    
    def _extract_context(self, query: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트 추출"""
        return {
            'query_length': len(query),
            'plan_complexity': len(plan.get('steps', [])),
            'has_kosis': 'KOSIS' in query,
            'has_multi_steps': any(char in query for char in ['1.', '2.', '3.']),
            'query_keywords': [word for word in ['검색', '조회', '분석', '인구', '통계'] if word in query]
        }
    
    def _generate_learning_insights(self, current_experience: ExecutionExperience) -> Dict[str, Any]:
        """학습 기반 인사이트 생성"""
        
        insights = {
            'historical_performance': self._get_historical_performance(),
            'pattern_analysis': self._analyze_historical_patterns(current_experience),
            'improvement_suggestions': [],
            'risk_factors': []
        }
        
        # 유사한 과거 경험 찾기
        similar_experiences = self._find_similar_experiences(current_experience)
        
        if similar_experiences:
            # 과거 성공 사례 분석
            successful_experiences = [exp for exp in similar_experiences if exp.quality_score > 0.5]
            if successful_experiences:
                best_experience = max(successful_experiences, key=lambda x: x.quality_score)
                insights['improvement_suggestions'].append(
                    f"과거 최고 성과(점수: {best_experience.quality_score:.2f})를 참고하세요"
                )
            
            # 공통 실패 패턴 분석
            common_failures = {}
            for exp in similar_experiences:
                for failure in exp.failure_factors:
                    common_failures[failure] = common_failures.get(failure, 0) + 1
            
            if common_failures:
                most_common = max(common_failures.items(), key=lambda x: x[1])
                insights['risk_factors'].append(f"주의: {most_common[0]} 실패가 빈번함")
        
        return insights
    
    def _find_similar_experiences(self, current_exp: ExecutionExperience, limit: int = 5) -> List[ExecutionExperience]:
        """유사한 경험 찾기"""
        
        scored_experiences = []
        current_context = current_exp.context
        
        for exp in self.experiences[:-1]:  # 현재 경험 제외
            similarity_score = self._calculate_similarity(current_context, exp.context)
            scored_experiences.append((similarity_score, exp))
        
        # 유사도 순 정렬
        scored_experiences.sort(key=lambda x: x[0], reverse=True)
        return [exp for _, exp in scored_experiences[:limit]]
    
    def _calculate_similarity(self, context1: Dict[str, Any], context2: Dict[str, Any]) -> float:
        """컨텍스트 유사도 계산"""
        
        score = 0.0
        total_weight = 0.0
        
        # KOSIS 쿼리 여부 (가중치: 0.3)
        if context1.get('has_kosis') == context2.get('has_kosis'):
            score += 0.3
        total_weight += 0.3
        
        # 다단계 쿼리 여부 (가중치: 0.2)
        if context1.get('has_multi_steps') == context2.get('has_multi_steps'):
            score += 0.2
        total_weight += 0.2
        
        # 계획 복잡도 유사성 (가중치: 0.2)
        complexity1 = context1.get('plan_complexity', 0)
        complexity2 = context2.get('plan_complexity', 0)
        if abs(complexity1 - complexity2) <= 1:  # 복잡도 차이 1 이하
            score += 0.2
        total_weight += 0.2
        
        # 키워드 유사성 (가중치: 0.3)
        keywords1 = set(context1.get('query_keywords', []))
        keywords2 = set(context2.get('query_keywords', []))
        if keywords1 and keywords2:
            keyword_similarity = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
            score += 0.3 * keyword_similarity
        total_weight += 0.3
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _get_historical_performance(self) -> Dict[str, float]:
        """과거 성능 통계"""
        
        if len(self.experiences) < 2:
            return {'average_score': 0.0, 'trend': 'insufficient_data'}
        
        scores = [exp.quality_score for exp in self.experiences]
        recent_scores = scores[-5:]  # 최근 5개
        
        average_score = sum(scores) / len(scores)
        recent_average = sum(recent_scores) / len(recent_scores)
        
        trend = 'improving' if recent_average > average_score else 'declining'
        
        return {
            'average_score': average_score,
            'recent_average': recent_average,
            'trend': trend,
            'total_experiences': len(self.experiences)
        }
    
    def _analyze_historical_patterns(self, current_exp: ExecutionExperience) -> Dict[str, Any]:
        """과거 패턴 분석"""
        
        pattern_analysis = {
            'success_pattern_frequency': {},
            'failure_pattern_frequency': {},
            'recommendations': []
        }
        
        # 성공/실패 패턴 빈도 계산
        for exp in self.experiences:
            for pattern in exp.success_factors:
                pattern_analysis['success_pattern_frequency'][pattern] = \
                    pattern_analysis['success_pattern_frequency'].get(pattern, 0) + 1
            
            for pattern in exp.failure_factors:
                pattern_analysis['failure_pattern_frequency'][pattern] = \
                    pattern_analysis['failure_pattern_frequency'].get(pattern, 0) + 1
        
        # 현재 실패 패턴에 대한 권장사항
        for failure in current_exp.failure_factors:
            frequency = pattern_analysis['failure_pattern_frequency'].get(failure, 0)
            if frequency > 2:  # 3회 이상 발생한 실패
                pattern_analysis['recommendations'].append(
                    f"{failure} 패턴이 {frequency}회 발생했습니다. 대안 전략을 고려하세요."
                )
        
        return pattern_analysis
    
    def _create_improved_plan(self, query: str, original_plan: Dict[str, Any], insights: Dict[str, Any]) -> Dict[str, Any]:
        """개선된 계획 생성"""
        
        # 기존 계획 복사
        improved_plan = {
            'objective': f"개선된 실행: {query}",
            'strategy': '학습 기반 최적화',
            'steps': []
        }
        
        # 학습 기반 개선사항 적용
        risk_factors = insights.get('risk_factors', [])
        
        # MCP 연결 실패가 빈번한 경우 대안 전략
        if any('mcp' in risk.lower() for risk in risk_factors):
            improved_plan['steps'].append({
                'type': 'mcp_tool_call',
                'tool_name': 'search_kosis',
                'params': {'keyword': '인구'},
                'description': 'MCP 연결 안정성 우선 확인',
                'priority': 'high',
                'retry_strategy': 'exponential_backoff'
            })
        
        # 기본 데이터 조회 단계
        improved_plan['steps'].append({
            'type': 'mcp_tool_call',
            'tool_name': 'fetch_kosis_data',
            'params': {
                'orgId': '101',
                'tblId': 'DT_1B040A3',
                'prdSe': 'Y',
                'startPrdDe': '2020',
                'endPrdDe': '2023'
            },
            'description': '검증된 주민등록인구 데이터 조회',
            'priority': 'high'
        })
        
        # SQL 분석 단계
        improved_plan['steps'].append({
            'type': 'sql_analysis',
            'description': '수집된 데이터 분석 및 요약',
            'priority': 'medium'
        })
        
        improved_plan['total_steps'] = len(improved_plan['steps'])
        improved_plan['learning_applied'] = True
        improved_plan['risk_mitigation'] = risk_factors
        
        return improved_plan
    
    def _create_analysis(self, execution_result: Dict[str, Any], insights: Dict[str, Any]) -> str:
        """분석 요약 생성"""
        
        stats = execution_result.get('stats', {})
        total_steps = stats.get('total_steps', 0)
        successful_steps = stats.get('successful_steps', 0)
        
        analysis = f"실행 결과: {successful_steps}/{total_steps} 단계 성공. "
        
        historical = insights.get('historical_performance', {})
        trend = historical.get('trend', 'unknown')
        
        if trend == 'improving':
            analysis += "학습을 통해 성능이 개선되고 있습니다. "
        elif trend == 'declining':
            analysis += "성능 하락 추세입니다. 전략 재검토가 필요합니다. "
        
        experience_count = historical.get('total_experiences', 0)
        analysis += f"총 {experience_count}개의 경험에서 학습했습니다."
        
        return analysis
    
    def save_experiences(self):
        """경험 저장"""
        try:
            data = [asdict(exp) for exp in self.experiences]
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"경험 저장 실패: {e}")
    
    def load_experiences(self):
        """경험 로드"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.experiences = [ExecutionExperience(**exp) for exp in data]
                self.logger.info(f"[LearningReflector] 📚 {len(self.experiences)}개 경험 로드됨")
            except Exception as e:
                self.logger.warning(f"경험 로드 실패: {e}")
                self.experiences = [] 