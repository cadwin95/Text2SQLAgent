"""
🔄 REFLECTOR (재계획 전담)
========================
역할: 실행 결과를 분석하여 개선된 재계획을 수립

📖 새로운 구조에서의 역할:
- Executor 실행 결과 분석 및 평가
- 실패 원인 파악 및 개선 방안 도출
- 사용자 만족도 기반 재계획 생성
- Chain에서 호출되어 Reflection 사이클 완성

🔄 연동:
- ../utils/llm_client.py: LLM 기반 결과 분석
- planner.py: 개선된 계획 재생성 요청
- Chain: 재계획 결과를 다시 실행할지 결정
- Executor: 실행 결과 데이터 분석

🚀 핵심 특징:
- 단일 책임: 결과 분석 및 재계획만 담당
- 학습 능력: 이전 실패에서 배운 개선사항 적용
- 적응적 전략: 다양한 실패 패턴에 맞는 대응책
- 성능 지표: 정량적 평가를 통한 객관적 판단
"""

import sys
import os
import logging
from typing import Dict, Any, List, Optional

# 상위 디렉토리 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import get_llm_client, create_chat_messages, extract_json_from_response

class Reflector:
    """
    🔄 실행 결과 분석 및 재계획 전문가
    
    새로운 아키텍처에서의 역할:
    - 실행 결과 품질 평가
    - 실패 패턴 분석 및 학습
    - 개선된 대안 계획 제안
    - 연속적인 개선 사이클 지원
    """
    
    def __init__(self, llm_backend: str = None):
        # LLM 클라이언트
        self.llm_client = get_llm_client(llm_backend)
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 학습 데이터 (실패 패턴 및 개선사항)
        self.failure_patterns = {}
        self.improvement_history = []
        
        # 성능 평가 지표
        self.evaluation_criteria = {
            'data_quality': {'weight': 0.3, 'min_score': 0.7},
            'execution_success': {'weight': 0.4, 'min_score': 0.8},
            'user_satisfaction': {'weight': 0.3, 'min_score': 0.6}
        }
        
        self.logger.info("[Reflector] 🔄 재계획 전문가 초기화 완료")
    
    def analyze_execution_result(self, execution_result: Dict[str, Any], original_question: str) -> Dict[str, Any]:
        """
        실행 결과 분석 및 평가
        
        Parameters:
        - execution_result: Executor의 실행 결과
        - original_question: 원래 사용자 질문
        
        Returns:
        - 분석 결과 및 재계획 권고사항
        """
        try:
            self.logger.info(f"[Reflector] 🔍 실행 결과 분석 시작: {original_question}")
            
            # 1. 정량적 평가
            quantitative_scores = self._evaluate_quantitatively(execution_result)
            
            # 2. 정성적 평가 (LLM 기반)
            qualitative_analysis = self._evaluate_qualitatively(execution_result, original_question)
            
            # 3. 종합 평가
            overall_assessment = self._generate_overall_assessment(
                quantitative_scores, 
                qualitative_analysis,
                execution_result
            )
            
            # 4. 개선 권고사항 생성
            improvement_recommendations = self._generate_improvement_recommendations(
                overall_assessment,
                execution_result,
                original_question
            )
            
            self.logger.info(f"[Reflector] ✅ 분석 완료: 종합 점수 {overall_assessment.get('total_score', 0):.2f}")
            
            return {
                'success': True,
                'analysis_result': {
                    'quantitative_scores': quantitative_scores,
                    'qualitative_analysis': qualitative_analysis,
                    'overall_assessment': overall_assessment,
                    'improvement_recommendations': improvement_recommendations
                },
                'needs_replanning': overall_assessment.get('total_score', 0) < 0.7,
                'original_question': original_question
            }
            
        except Exception as e:
            self.logger.error(f"[Reflector] ❌ 결과 분석 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'needs_replanning': True,
                'original_question': original_question
            }
    
    def _evaluate_quantitatively(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """정량적 평가"""
        stats = execution_result.get('stats', {})
        final_result = execution_result.get('final_result', {})
        
        # 실행 성공률
        total_steps = stats.get('total_steps', 1)
        successful_steps = stats.get('successful_steps', 0)
        execution_success_rate = successful_steps / total_steps if total_steps > 0 else 0
        
        # 데이터 품질 평가
        data_quality_score = self._evaluate_data_quality(final_result)
        
        # MCP 도구 활용도
        mcp_calls = stats.get('mcp_calls', 0)
        mcp_utilization = min(mcp_calls / 3, 1.0)  # 최대 3개 호출을 완벽한 활용으로 간주
        
        # SQL 분석 수행도
        sql_queries = stats.get('sql_queries', 0)
        sql_analysis_score = min(sql_queries / 2, 1.0)  # 최대 2개 쿼리를 완벽한 분석으로 간주
        
        return {
            'execution_success_rate': execution_success_rate,
            'data_quality_score': data_quality_score,
            'mcp_utilization': mcp_utilization,
            'sql_analysis_score': sql_analysis_score,
            'total_steps_executed': total_steps,
            'successful_steps': successful_steps
        }
    
    def _evaluate_data_quality(self, final_result: Dict[str, Any]) -> float:
        """데이터 품질 평가"""
        try:
            data_summary = final_result.get('data_summary', {})
            total_tables = data_summary.get('total_tables', 0)
            total_rows = data_summary.get('total_rows', 0)
            
            # 기본 점수
            base_score = 0.5 if total_tables > 0 else 0
            
            # 데이터 양 점수
            data_volume_score = min(total_rows / 100, 0.3)  # 100행을 기준으로 최대 0.3점
            
            # 데이터 다양성 점수 (출처의 다양성)
            data_sources = data_summary.get('data_sources', [])
            diversity_score = min(len(data_sources) / 2, 0.2)  # 2개 출처를 기준으로 최대 0.2점
            
            return base_score + data_volume_score + diversity_score
            
        except Exception:
            return 0.0
    
    def _evaluate_qualitatively(self, execution_result: Dict[str, Any], original_question: str) -> Dict[str, Any]:
        """정성적 평가 (LLM 기반)"""
        
        # 실행 히스토리 요약
        execution_summary = self._summarize_execution_history(execution_result.get('execution_history', []))
        
        # 최종 결과 요약
        final_result_summary = self._summarize_final_result(execution_result.get('final_result', {}))
        
        system_prompt = """
당신은 데이터 분석 결과 평가 전문가입니다.

🎯 평가 목표: 실행 결과가 사용자 질문에 얼마나 잘 답했는지 평가

📋 평가 기준:
1. 질문 적합성: 결과가 원래 질문에 얼마나 부합하는가?
2. 완성도: 분석이 충분히 상세하고 완전한가?
3. 신뢰성: 데이터와 분석 방법이 신뢰할 만한가?
4. 실용성: 결과가 실제로 유용한 정보를 제공하는가?

각 기준별로 1-5점으로 평가하고, 개선점을 제시하세요.

JSON 형식으로 응답:
{
  "question_relevance": {
    "score": 4,
    "comment": "평가 설명"
  },
  "completeness": {
    "score": 3,
    "comment": "평가 설명"
  },
  "reliability": {
    "score": 4,
    "comment": "평가 설명"
  },
  "practicality": {
    "score": 3,
    "comment": "평가 설명"
  },
  "overall_assessment": "전반적 평가",
  "key_strengths": ["강점1", "강점2"],
  "improvement_areas": ["개선점1", "개선점2"]
}
"""
        
        user_prompt = f"""
원래 질문: {original_question}

실행 과정:
{execution_summary}

최종 결과:
{final_result_summary}

위 결과를 평가해주세요.
"""
        
        try:
            messages = create_chat_messages(system_prompt, user_prompt)
            response = self.llm_client.chat(messages, max_tokens=600)
            
            # JSON 추출
            evaluation_json = extract_json_from_response(response)
            
            if evaluation_json:
                return evaluation_json
            else:
                # 백업 평가
                return self._generate_fallback_qualitative_evaluation()
                
        except Exception as e:
            self.logger.error(f"[Reflector] LLM 정성적 평가 오류: {e}")
            return self._generate_fallback_qualitative_evaluation()
    
    def _summarize_execution_history(self, execution_history: List[Dict[str, Any]]) -> str:
        """실행 히스토리 요약"""
        if not execution_history:
            return "실행 히스토리가 없습니다."
        
        summary_parts = []
        for i, step in enumerate(execution_history, 1):
            step_type = step.get('step_type', 'unknown')
            success = '✅' if step.get('success') else '❌'
            description = step.get('description', '')
            message = step.get('message', step.get('error', ''))
            
            summary_parts.append(f"{i}. {step_type} {success}: {description} - {message}")
        
        return "\n".join(summary_parts)
    
    def _summarize_final_result(self, final_result: Dict[str, Any]) -> str:
        """최종 결과 요약"""
        if not final_result:
            return "최종 결과가 없습니다."
        
        summary_parts = []
        
        # 데이터 요약
        data_summary = final_result.get('data_summary', {})
        if data_summary:
            summary_parts.append(f"데이터: {data_summary.get('total_tables', 0)}개 테이블, {data_summary.get('total_rows', 0)}행")
        
        # SQL 결과 요약
        sql_results = final_result.get('sql_results', [])
        if sql_results:
            summary_parts.append(f"SQL 분석: {len(sql_results)}개 쿼리 실행")
        
        # 차트 데이터
        chart_data = final_result.get('chart_data')
        if chart_data:
            summary_parts.append(f"시각화: {chart_data.get('type', 'unknown')} 차트 생성")
        
        return "\n".join(summary_parts) if summary_parts else "구체적인 결과가 없습니다."
    
    def _generate_fallback_qualitative_evaluation(self) -> Dict[str, Any]:
        """백업 정성적 평가"""
        return {
            "question_relevance": {"score": 3, "comment": "평가 불가"},
            "completeness": {"score": 3, "comment": "평가 불가"},
            "reliability": {"score": 3, "comment": "평가 불가"}, 
            "practicality": {"score": 3, "comment": "평가 불가"},
            "overall_assessment": "LLM 평가를 사용할 수 없어 기본 평가를 적용했습니다.",
            "key_strengths": ["기본 실행 완료"],
            "improvement_areas": ["LLM 기반 평가 활성화 필요"]
        }
    
    def _generate_overall_assessment(self, quantitative: Dict[str, Any], qualitative: Dict[str, Any], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """종합 평가 생성"""
        
        # 정량적 점수 정규화 (0-1 범위)
        quant_score = (
            quantitative.get('execution_success_rate', 0) * 0.4 +
            quantitative.get('data_quality_score', 0) * 0.3 +
            quantitative.get('mcp_utilization', 0) * 0.2 +
            quantitative.get('sql_analysis_score', 0) * 0.1
        )
        
        # 정성적 점수 정규화 (1-5 → 0-1 범위)
        qual_scores = []
        for criterion in ['question_relevance', 'completeness', 'reliability', 'practicality']:
            score = qualitative.get(criterion, {}).get('score', 3)
            normalized_score = (score - 1) / 4  # 1-5 → 0-1
            qual_scores.append(normalized_score)
        
        qual_score = sum(qual_scores) / len(qual_scores) if qual_scores else 0
        
        # 종합 점수 (정량 70%, 정성 30%)
        total_score = quant_score * 0.7 + qual_score * 0.3
        
        # 등급 결정
        if total_score >= 0.8:
            grade = "Excellent"
        elif total_score >= 0.6:
            grade = "Good"
        elif total_score >= 0.4:
            grade = "Fair"
        else:
            grade = "Poor"
        
        return {
            'total_score': total_score,
            'quantitative_score': quant_score,
            'qualitative_score': qual_score,
            'grade': grade,
            'meets_criteria': total_score >= 0.7,
            'score_breakdown': {
                'execution_success': quantitative.get('execution_success_rate', 0),
                'data_quality': quantitative.get('data_quality_score', 0),
                'question_relevance': qual_scores[0] if qual_scores else 0,
                'completeness': qual_scores[1] if qual_scores else 0
            }
        }
    
    def _generate_improvement_recommendations(self, assessment: Dict[str, Any], execution_result: Dict[str, Any], original_question: str) -> Dict[str, Any]:
        """개선 권고사항 생성"""
        
        recommendations = {
            'priority': 'low',
            'suggested_actions': [],
            'alternative_approaches': [],
            'parameter_adjustments': {}
        }
        
        total_score = assessment.get('total_score', 0)
        
        if total_score < 0.4:
            recommendations['priority'] = 'high'
            recommendations['suggested_actions'].append("전면적인 계획 재수립 필요")
        elif total_score < 0.7:
            recommendations['priority'] = 'medium'
            recommendations['suggested_actions'].append("부분적인 개선 필요")
        
        # 실행 성공률이 낮은 경우
        if assessment.get('quantitative_score', 0) < 0.6:
            recommendations['suggested_actions'].append("MCP 도구 호출 파라미터 재검토")
            recommendations['parameter_adjustments']['mcp_retry'] = True
        
        # 데이터 품질이 낮은 경우
        data_summary = execution_result.get('final_result', {}).get('data_summary', {})
        if data_summary.get('total_rows', 0) < 10:
            recommendations['suggested_actions'].append("더 많은 데이터 수집 필요")
            recommendations['alternative_approaches'].append("다른 통계표 탐색")
        
        # 질문 적합성이 낮은 경우
        score_breakdown = assessment.get('score_breakdown', {})
        if score_breakdown.get('question_relevance', 0) < 0.5:
            recommendations['suggested_actions'].append("질문 분석 및 계획 수정 필요")
            recommendations['alternative_approaches'].append("질문 의도 재해석")
        
        return recommendations
    
    def generate_replan(self, analysis_result: Dict[str, Any], original_question: str) -> Dict[str, Any]:
        """분석 결과를 바탕으로 재계획 생성"""
        
        try:
            self.logger.info(f"[Reflector] 🔄 재계획 생성: {original_question}")
            
            improvement_recommendations = analysis_result.get('improvement_recommendations', {})
            
            # 기본 재계획 생성 (LLM 대신 룰 기반)
            replan = self._generate_basic_replan(original_question, improvement_recommendations)
            
            self.logger.info(f"[Reflector] ✅ 재계획 생성 완료: {len(replan.get('steps', []))}개 단계")
            
            return {
                'success': True,
                'replan': replan,
                'improvement_focus': improvement_recommendations.get('priority', 'low'),
                'original_question': original_question
            }
                
        except Exception as e:
            self.logger.error(f"[Reflector] ❌ 재계획 생성 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_question': original_question
            }
    
    def _generate_basic_replan(self, question: str, improvements: Dict[str, Any]) -> Dict[str, Any]:
        """기본 재계획 생성 (룰 기반)"""
        
        priority = improvements.get('priority', 'low')
        
        if priority == 'high':
            # 전면 재수립 - 더 확실한 데이터 소스 사용
            steps = [
                {
                    "type": "mcp_tool_call",
                    "tool_name": "search_kosis",
                    "description": f"{question} 관련 통계표 재검색",
                    "params": {"keyword": self._extract_keyword_from_question(question)},
                    "priority": "high"
                },
                {
                    "type": "mcp_tool_call", 
                    "tool_name": "fetch_kosis_data",
                    "description": "개선된 매개변수로 데이터 재수집",
                    "params": {
                        "orgId": "101",
                        "tblId": "DT_1B040A3",
                        "prdSe": "Y",
                        "startPrdDe": "2020",
                        "endPrdDe": "2024",
                        "itmId": "T20",
                        "objL1": "00"
                    },
                    "priority": "high"
                },
                {
                    "type": "sql_analysis",
                    "description": f"개선된 {question} 분석",
                    "priority": "medium"
                }
            ]
        else:
            # 부분 개선
            steps = [
                {
                    "type": "mcp_tool_call",
                    "tool_name": "fetch_kosis_data", 
                    "description": "개선된 데이터 수집",
                    "params": {
                        "orgId": "101",
                        "tblId": "DT_1B040A3",
                        "itmId": "T20",
                        "objL1": "00"
                    },
                    "priority": "high"
                },
                {
                    "type": "sql_analysis",
                    "description": f"{question} 재분석",
                    "priority": "medium"
                }
            ]
        
        return {
            "steps": steps,
            "analysis_type": "개선된 분석",
            "improvement_focus": f"{priority} 우선순위 개선",
            "confidence": "medium"
        }
    
    def _extract_keyword_from_question(self, question: str) -> str:
        """질문에서 키워드 추출 (간단 버전)"""
        keywords = ['인구', '경제', 'GDP', '물가', '고용', '교육']
        
        for keyword in keywords:
            if keyword in question:
                return keyword
        
        # 기본값
        return "인구"
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """학습 데이터 요약"""
        return {
            'total_improvements': len(self.improvement_history),
            'recent_scores': [record.get('original_score', 0) for record in self.improvement_history[-5:]],
            'common_issues': self._analyze_common_failure_patterns(),
            'improvement_trends': self._analyze_improvement_trends()
        }
    
    def _analyze_common_failure_patterns(self) -> List[str]:
        """공통 실패 패턴 분석"""
        # 간단한 패턴 분석
        all_actions = []
        for record in self.improvement_history:
            all_actions.extend(record.get('improvement_actions', []))
        
        # 빈도 기반 패턴 추출 (간단 버전)
        action_counts = {}
        for action in all_actions:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # 상위 3개 패턴 반환
        sorted_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)
        return [action for action, count in sorted_actions[:3]]
    
    def _analyze_improvement_trends(self) -> Dict[str, Any]:
        """개선 트렌드 분석"""
        if len(self.improvement_history) < 2:
            return {"trend": "insufficient_data"}
        
        recent_scores = [record.get('original_score', 0) for record in self.improvement_history[-5:]]
        
        if len(recent_scores) >= 2:
            trend = "improving" if recent_scores[-1] > recent_scores[0] else "declining"
            avg_score = sum(recent_scores) / len(recent_scores)
        else:
            trend = "stable"
            avg_score = recent_scores[0] if recent_scores else 0
        
        return {
            "trend": trend,
            "average_score": avg_score,
            "recent_improvements": len([s for s in recent_scores if s > 0.7])
        } 