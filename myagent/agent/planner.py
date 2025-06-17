"""
🎯 PLANNER (계획 수립 전담)
=========================
역할: LLM을 활용하여 사용자 질문에 대한 분석 계획을 수립

📖 새로운 구조에서의 역할:
- 사용자 질문 분석 및 의도 파악
- MCP Server 도구들을 고려한 실행 계획 생성
- 단계별 액션 계획 및 우선순위 설정
- Chain에서 호출되어 워크플로우 시작점 역할

🔄 연동:
- ../utils/llm_client.py: LLM 기반 계획 생성
- Chain: 계획 결과를 Executor에게 전달
- MCP Config: 사용 가능한 MCP Server 도구 목록 참조

🚀 핵심 특징:
- 단일 책임: 계획 수립만 담당
- MCP 도구 인식: 사용 가능한 도구들을 고려한 계획
- 구조화된 출력: JSON 형태의 실행 가능한 계획
- 확장성: 새로운 MCP Server 추가 시 자동 인식
"""

import json
import sys
import os
import logging
from typing import Dict, Any, List, Optional

# 상위 디렉토리의 utils 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_client import get_llm_client, create_chat_messages, extract_json_from_response

class Planner:
    """
    🎯 분석 계획 수립 전문가
    
    새로운 아키텍처에서의 역할:
    - 사용자 질문 → 구조화된 실행 계획 변환
    - MCP Server 도구들을 활용한 최적 경로 계획
    - 실행 가능한 단계별 액션 정의
    - 실패 시나리오 고려한 대안 계획 포함
    """
    
    def __init__(self, llm_backend: str = None):
        # LLM 클라이언트
        self.llm_client = get_llm_client(llm_backend)
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # MCP Server 도구 정보 (설정 파일에서 로드 가능)
        self.mcp_tools = self._load_mcp_tools_config()
        
        self.logger.info("[Planner] 🎯 계획 수립 전문가 초기화 완료")
    
    def _load_mcp_tools_config(self) -> Dict[str, Any]:
        """MCP Server 도구 설정 로드"""
        # 기본 KOSIS MCP Server 도구들
        default_tools = {
            "kosis_server": {
                "name": "KOSIS-Statistics-API",
                "tools": [
                    {
                        "name": "fetch_kosis_data",
                        "description": "KOSIS 통계자료 직접 조회",
                        "params": ["orgId", "tblId", "prdSe", "startPrdDe", "endPrdDe", "itmId", "objL1"],
                        "priority": "high",
                        "examples": [
                            {
                                "description": "인구 통계 조회",
                                "params": {"orgId": "101", "tblId": "DT_1B040A3", "itmId": "T20", "objL1": "00"}
                            }
                        ]
                    },
                    {
                        "name": "search_kosis", 
                        "description": "KOSIS 키워드 검색",
                        "params": ["keyword"],
                        "priority": "medium"
                    },
                    {
                        "name": "get_stat_list",
                        "description": "KOSIS 통계목록 탐색", 
                        "params": ["vwCd", "parentListId"],
                        "priority": "low"
                    }
                ]
            }
        }
        
        # TODO: mcp_config.json에서 추가 도구들 로드
        # config_path = "../mcp_config.json"
        # if os.path.exists(config_path):
        #     with open(config_path, 'r') as f:
        #         config = json.load(f)
        #         # 추가 MCP Server들 로드
        
        return default_tools
    
    def create_analysis_plan(self, question: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        사용자 질문에 대한 분석 계획 수립
        
        Parameters:
        - question: 사용자 질문
        - context: 추가 컨텍스트 (기존 데이터, 설정 등)
        
        Returns:
        - 구조화된 실행 계획 (JSON)
        """
        try:
            self.logger.info(f"[Planner] 📝 분석 계획 수립: {question}")
            
            # 컨텍스트 정보 구성
            if context is None:
                context = {}
            
            context_info = self._build_context_info(context)
            
            # LLM을 활용한 계획 생성
            plan = self._generate_plan_with_llm(question, context_info)
            
            if plan:
                self.logger.info(f"[Planner] ✅ 계획 수립 완료: {len(plan.get('steps', []))}개 단계")
                return {
                    "success": True,
                    "plan": plan,
                    "question": question,
                    "planner_version": "v2.0"
                }
            else:
                # 백업 계획 생성
                backup_plan = self._create_backup_plan(question)
                self.logger.warning(f"[Planner] ⚠️ LLM 계획 실패, 백업 계획 사용")
                return {
                    "success": True,
                    "plan": backup_plan,
                    "question": question,
                    "planner_version": "v2.0",
                    "backup_used": True
                }
            
        except Exception as e:
            self.logger.error(f"[Planner] ❌ 계획 수립 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question
            }
    
    def _build_context_info(self, context: Dict[str, Any]) -> str:
        """컨텍스트 정보를 문자열로 구성"""
        context_parts = []
        
        # 기존 데이터 정보
        existing_data = context.get('existing_dataframes', [])
        if existing_data:
            context_parts.append(f"기존 로드된 데이터: {', '.join(existing_data)}")
        
        # MCP Server 도구 정보
        tools_info = self._format_mcp_tools_info()
        context_parts.append(f"사용 가능한 MCP 도구:\n{tools_info}")
        
        # 추가 제약사항
        constraints = context.get('constraints', [])
        if constraints:
            context_parts.append(f"제약사항: {', '.join(constraints)}")
        
        return "\n\n".join(context_parts)
    
    def _format_mcp_tools_info(self) -> str:
        """MCP Server 도구 정보를 포맷팅"""
        tools_desc = []
        
        for server_name, server_info in self.mcp_tools.items():
            tools_desc.append(f"📡 {server_info['name']}:")
            for tool in server_info['tools']:
                priority_emoji = "⭐" if tool['priority'] == 'high' else "🔧"
                tools_desc.append(f"  {priority_emoji} {tool['name']}: {tool['description']}")
        
        return "\n".join(tools_desc)
    
    def _generate_plan_with_llm(self, question: str, context_info: str) -> Optional[Dict[str, Any]]:
        """LLM을 활용한 계획 생성"""
        
        system_prompt = f"""
당신은 데이터 분석 계획 수립 전문가입니다.

🎯 목표: 사용자 질문을 분석하여 실행 가능한 단계별 계획을 수립

📋 계획 수립 규칙:
1. MCP Server 도구를 우선적으로 활용
2. 데이터 수집 → 처리 → 분석 → 시각화 순서
3. 각 단계는 독립적으로 실행 가능해야 함
4. 실패 시 대안 경로 포함
5. KOSIS 데이터의 경우 검증된 통계표 우선 사용

🔧 사용 가능한 환경:
{context_info}

📊 검증된 KOSIS 통계표:
- 인구: orgId="101", tblId="DT_1B040A3", itmId="T20", objL1="00"
- GDP: orgId="101", tblId="DT_1DA7001"
- 물가: orgId="101", tblId="DT_1DD0001"

JSON 형식으로만 응답하세요:
{{
  "steps": [
    {{
      "type": "mcp_tool_call",
      "tool_name": "fetch_kosis_data",
      "description": "단계 설명",
      "params": {{"orgId": "101", "tblId": "DT_1B040A3"}},
      "priority": "high",
      "fallback": "대안 계획"
    }},
    {{
      "type": "sql_analysis", 
      "description": "SQL 기반 데이터 분석",
      "priority": "medium"
    }},
    {{
      "type": "visualization",
      "description": "결과 시각화",
      "priority": "low"
    }}
  ],
  "analysis_type": "통계 분석",
  "estimated_duration": "2-3분",
  "confidence": "high"
}}
"""
        
        user_prompt = f"""
사용자 질문: {question}

위 질문에 대한 분석 계획을 수립해주세요.
"""
        
        try:
            messages = create_chat_messages(system_prompt, user_prompt)
            response = self.llm_client.chat(messages, max_tokens=800)
            
            # JSON 추출
            plan_json = extract_json_from_response(response)
            
            if plan_json and 'steps' in plan_json:
                # 계획 검증 및 보완
                validated_plan = self._validate_and_enhance_plan(plan_json)
                return validated_plan
            else:
                self.logger.warning("[Planner] LLM 응답에서 올바른 JSON을 찾을 수 없음")
                return None
                
        except Exception as e:
            self.logger.error(f"[Planner] LLM 계획 생성 오류: {e}")
            return None
    
    def _validate_and_enhance_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """계획 검증 및 보완"""
        steps = plan.get('steps', [])
        
        # 1. MCP 도구 호출 단계 검증
        for i, step in enumerate(steps):
            if step.get('type') == 'mcp_tool_call':
                tool_name = step.get('tool_name')
                if not self._is_valid_mcp_tool(tool_name):
                    # 유효하지 않은 도구면 대체
                    steps[i] = self._create_fallback_step(step)
        
        # 2. 필수 단계 확인 및 추가
        if not any(step.get('type') == 'mcp_tool_call' for step in steps):
            # MCP 데이터 수집 단계가 없으면 추가
            data_step = {
                "type": "mcp_tool_call",
                "tool_name": "fetch_kosis_data",
                "description": "기본 인구 통계 데이터 수집",
                "params": {"orgId": "101", "tblId": "DT_1B040A3", "itmId": "T20", "objL1": "00"},
                "priority": "high"
            }
            steps.insert(0, data_step)
        
        # 3. 분석 단계 확인
        if not any(step.get('type') in ['sql_analysis', 'query'] for step in steps):
            analysis_step = {
                "type": "sql_analysis",
                "description": "MCP 데이터 기반 SQL 분석", 
                "priority": "medium"
            }
            steps.append(analysis_step)
        
        # 4. 메타데이터 추가
        plan['steps'] = steps
        plan['total_steps'] = len(steps)
        plan['mcp_tools_used'] = [s.get('tool_name') for s in steps if s.get('type') == 'mcp_tool_call']
        
        return plan
    
    def _is_valid_mcp_tool(self, tool_name: str) -> bool:
        """MCP 도구 유효성 검증"""
        for server_info in self.mcp_tools.values():
            for tool in server_info['tools']:
                if tool['name'] == tool_name:
                    return True
        return False
    
    def _create_fallback_step(self, original_step: Dict[str, Any]) -> Dict[str, Any]:
        """대체 단계 생성"""
        return {
            "type": "mcp_tool_call",
            "tool_name": "fetch_kosis_data",
            "description": f"대체 계획: {original_step.get('description', '')}",
            "params": {"orgId": "101", "tblId": "DT_1B040A3", "itmId": "T20", "objL1": "00"},
            "priority": "medium",
            "fallback_for": original_step.get('tool_name')
        }
    
    def _create_backup_plan(self, question: str) -> Dict[str, Any]:
        """LLM 실패 시 백업 계획 생성"""
        return {
            "steps": [
                {
                    "type": "mcp_tool_call",
                    "tool_name": "fetch_kosis_data",
                    "description": f"{question} 관련 기본 인구 통계 수집",
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
                    "description": f"MCP 데이터를 활용한 {question} 분석",
                    "priority": "medium"
                },
                {
                    "type": "visualization",
                    "description": "분석 결과 시각화",
                    "priority": "low"
                }
            ],
            "analysis_type": "기본 통계 분석",
            "estimated_duration": "2-3분",
            "confidence": "medium",
            "backup_plan": True
        }
    
    def update_mcp_tools_config(self, new_tools: Dict[str, Any]):
        """MCP 도구 설정 업데이트 (런타임 확장)"""
        self.mcp_tools.update(new_tools)
        self.logger.info(f"[Planner] 🔧 MCP 도구 설정 업데이트: {list(new_tools.keys())}")
    
    def get_available_tools(self) -> Dict[str, Any]:
        """사용 가능한 MCP 도구 목록 반환"""
        return self.mcp_tools.copy()
    
    def analyze_question_complexity(self, question: str) -> Dict[str, Any]:
        """질문 복잡도 분석 (고급 계획 수립용)"""
        complexity_indicators = {
            "keywords_count": len(question.split()),
            "has_time_reference": any(word in question.lower() for word in ['년', '월', '기간', '최근', '과거']),
            "has_comparison": any(word in question.lower() for word in ['비교', '차이', '대비', '증가', '감소']),
            "has_aggregation": any(word in question.lower() for word in ['평균', '합계', '총', '최대', '최소']),
            "requires_multiple_datasets": ',' in question or '그리고' in question
        }
        
        # 복잡도 점수 계산
        complexity_score = sum([
            complexity_indicators["keywords_count"] > 10,
            complexity_indicators["has_time_reference"],
            complexity_indicators["has_comparison"], 
            complexity_indicators["has_aggregation"],
            complexity_indicators["requires_multiple_datasets"]
        ])
        
        complexity_level = "simple" if complexity_score <= 1 else "medium" if complexity_score <= 3 else "complex"
        
        return {
            "complexity_level": complexity_level,
            "complexity_score": complexity_score,
            "indicators": complexity_indicators,
            "recommended_steps": complexity_score + 2
        } 