"""
Agent Orchestrator
==================
MCP 도구와 LLM을 조율하여 사용자 요청을 처리
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ExecutionStep:
    """실행 단계"""
    step_type: str  # tool_call, analysis, response
    details: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

class AgentOrchestrator:
    """
    Agent Orchestrator
    
    LLM과 MCP 도구를 조율하여 복잡한 작업 수행
    """
    
    def __init__(self, mcp_client, llm_manager):
        self.mcp_client = mcp_client
        self.llm_manager = llm_manager
        self.execution_history: List[ExecutionStep] = []
        
    async def process(self, query: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        사용자 쿼리 처리
        
        Args:
            query: 사용자 질의
            max_iterations: 최대 반복 횟수
            
        Returns:
            처리 결과
        """
        self.execution_history.clear()
        
        try:
            # 1. 사용 가능한 도구 확인
            available_tools = self.mcp_client.list_all_tools()
            logger.info(f"Available tools: {len(available_tools)}")
            
            # 2. 초기 프롬프트 생성
            messages = self.llm_manager.create_mcp_aware_prompt(
                query=query,
                available_tools=available_tools
            )
            
            # 3. 반복 실행
            for iteration in range(max_iterations):
                logger.info(f"Iteration {iteration + 1}/{max_iterations}")
                
                # LLM 호출
                response = self.llm_manager.chat(messages)
                messages.append({"role": "assistant", "content": response})
                
                # 도구 호출 파싱
                tool_calls = self._parse_tool_calls(response)
                
                if not tool_calls:
                    # 도구 호출이 없으면 최종 응답으로 간주
                    step = ExecutionStep(
                        step_type="response",
                        details={"content": response},
                        result=response
                    )
                    self.execution_history.append(step)
                    break
                
                # 도구 실행
                for tool_call in tool_calls:
                    result = await self._execute_tool_call(tool_call)
                    
                    # 결과를 메시지에 추가
                    tool_result_msg = f"Tool result for {tool_call['tool']}:\n{json.dumps(result, ensure_ascii=False, indent=2)}"
                    messages.append({"role": "user", "content": tool_result_msg})
            
            # 4. 최종 결과 생성
            return self._create_final_result()
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "history": self._serialize_history()
            }
    
    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        응답에서 도구 호출 파싱
        
        Args:
            response: LLM 응답
            
        Returns:
            도구 호출 목록
        """
        tool_calls = []
        
        # TOOL_CALL: {...} 패턴 찾기 (중첩된 중괄호 지원)
        pattern = r'TOOL_CALL:\s*(\{(?:[^{}]|(?:\{[^{}]*\}))*\})'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                # JSON 문자열 정규화
                json_str = match.strip()
                # 줄바꿈 문자 처리
                json_str = json_str.replace('\n', ' ')
                # 연속된 공백 제거
                json_str = re.sub(r'\s+', ' ', json_str)
                
                tool_call = json.loads(json_str)
                tool_calls.append(tool_call)
                logger.info(f"Successfully parsed tool call: {tool_call}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse tool call: {e}\nJSON: {match}")
        
        return tool_calls
    
    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        도구 호출 실행
        
        Args:
            tool_call: 도구 호출 정보
            
        Returns:
            실행 결과
        """
        server_name = tool_call.get("server")
        tool_name = tool_call.get("tool")
        arguments = tool_call.get("arguments", {})
        
        step = ExecutionStep(
            step_type="tool_call",
            details={
                "server": server_name,
                "tool": tool_name,
                "arguments": arguments
            }
        )
        
        try:
            # MCP 도구 실행
            result = await self.mcp_client.call_tool(
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments
            )
            
            step.result = result
            self.execution_history.append(step)
            
            return result
            
        except Exception as e:
            step.error = str(e)
            self.execution_history.append(step)
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_final_result(self) -> Dict[str, Any]:
        """최종 결과 생성"""
        # 마지막 응답 찾기
        final_response = None
        for step in reversed(self.execution_history):
            if step.step_type == "response":
                final_response = step.result
                break
        
        # 도구 실행 결과 수집
        tool_results = []
        for step in self.execution_history:
            if step.step_type == "tool_call" and step.result:
                tool_results.append({
                    "tool": step.details["tool"],
                    "result": step.result
                })
        
        return {
            "success": True,
            "response": final_response,
            "tool_results": tool_results,
            "history": self._serialize_history()
        }
    
    def _serialize_history(self) -> List[Dict[str, Any]]:
        """실행 기록 직렬화"""
        return [
            {
                "step_type": step.step_type,
                "details": step.details,
                "result": step.result,
                "error": step.error,
                "timestamp": step.timestamp.isoformat()
            }
            for step in self.execution_history
        ] 