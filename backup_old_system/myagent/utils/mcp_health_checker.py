#!/usr/bin/env python3
"""
🏥 MCP Health Checker - MCP 서버 상태 체크 및 초기화 테스트
============================================================
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import json

@dataclass
class MCPToolHealth:
    """MCP 도구 상태 정보"""
    name: str
    available: bool
    last_test_time: float
    last_error: Optional[str]
    success_rate: float
    response_time: float
    test_count: int
    success_count: int

class MCPHealthChecker:
    """🏥 MCP 서버 상태 체크 전문가"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tool_health = {}  # 도구별 상태 정보
        self.initialized = False
        self.initialization_results = {}
        
        # 기본 테스트 도구 목록
        self.test_tools = [
            'search_kosis',
            'fetch_kosis_data', 
            'get_stat_list',
            'get_table_meta'
        ]
        
        self.logger.info("[MCPHealthChecker] 🏥 MCP 상태 체크 시스템 초기화")
    
    async def initialize_and_test_all(self, mcp_tools: Dict[str, Any]) -> Dict[str, Any]:
        """모든 MCP 도구 초기화 및 테스트"""
        
        self.logger.info("[MCPHealthChecker] 🚀 MCP 서버 전체 초기화 및 테스트 시작")
        
        initialization_report = {
            'success': True,
            'total_tools': len(self.test_tools),
            'available_tools': 0,
            'failed_tools': 0,
            'tool_details': {},
            'recommendations': [],
            'fallback_needed': False
        }
        
        # 각 도구별 테스트
        for tool_name in self.test_tools:
            if tool_name in mcp_tools:
                tool_health = await self._test_single_tool(tool_name, mcp_tools[tool_name])
                self.tool_health[tool_name] = tool_health
                initialization_report['tool_details'][tool_name] = asdict(tool_health)
                
                if tool_health.available:
                    initialization_report['available_tools'] += 1
                else:
                    initialization_report['failed_tools'] += 1
            else:
                # 도구가 등록되지 않음
                dummy_health = MCPToolHealth(
                    name=tool_name,
                    available=False,
                    last_test_time=time.time(),
                    last_error="도구가 등록되지 않음",
                    success_rate=0.0,
                    response_time=0.0,
                    test_count=0,
                    success_count=0
                )
                self.tool_health[tool_name] = dummy_health
                initialization_report['tool_details'][tool_name] = asdict(dummy_health)
                initialization_report['failed_tools'] += 1
        
        # 전체 성공률 계산
        total_success_rate = initialization_report['available_tools'] / initialization_report['total_tools']
        initialization_report['overall_success_rate'] = total_success_rate
        
        # 권장사항 생성
        initialization_report['recommendations'] = self._generate_recommendations(total_success_rate)
        
        # 폴백 모드 필요 여부
        if total_success_rate < 0.5:  # 50% 미만 성공시
            initialization_report['fallback_needed'] = True
            initialization_report['success'] = False
        
        self.initialized = True
        self.initialization_results = initialization_report
        
        self.logger.info(f"[MCPHealthChecker] ✅ 초기화 완료: {initialization_report['available_tools']}/{initialization_report['total_tools']} 도구 사용가능")
        
        return initialization_report
    
    async def _test_single_tool(self, tool_name: str, tool_func) -> MCPToolHealth:
        """개별 도구 테스트"""
        
        self.logger.info(f"[MCPHealthChecker] 🔧 도구 테스트: {tool_name}")
        
        start_time = time.time()
        test_success = False
        error_message = None
        
        try:
            # 도구별 테스트 파라미터
            test_params = self._get_test_params(tool_name)
            
            # 타임아웃 설정하여 테스트
            result = await asyncio.wait_for(
                asyncio.create_task(self._call_tool_async(tool_func, test_params)),
                timeout=10.0  # 10초 타임아웃
            )
            
            # 결과 검증
            if self._validate_tool_result(tool_name, result):
                test_success = True
                self.logger.info(f"[MCPHealthChecker] ✅ {tool_name} 테스트 성공")
            else:
                error_message = "응답 형식 오류"
                self.logger.warning(f"[MCPHealthChecker] ⚠️ {tool_name} 응답 형식 오류")
                
        except asyncio.TimeoutError:
            error_message = "타임아웃 (10초)"
            self.logger.warning(f"[MCPHealthChecker] ⏰ {tool_name} 타임아웃")
        except Exception as e:
            error_message = str(e)
            self.logger.error(f"[MCPHealthChecker] ❌ {tool_name} 테스트 실패: {e}")
        
        response_time = time.time() - start_time
        
        return MCPToolHealth(
            name=tool_name,
            available=test_success,
            last_test_time=time.time(),
            last_error=error_message,
            success_rate=1.0 if test_success else 0.0,
            response_time=response_time,
            test_count=1,
            success_count=1 if test_success else 0
        )
    
    def _get_test_params(self, tool_name: str) -> Dict[str, Any]:
        """도구별 테스트 파라미터"""
        
        test_params_map = {
            'search_kosis': {'keyword': '인구'},
            'fetch_kosis_data': {
                'orgId': '101',
                'tblId': 'DT_1B040A3',
                'prdSe': 'Y',
                'startPrdDe': '2023',
                'endPrdDe': '2023'
            },
            'get_stat_list': {'vwCd': 'MT_ZTITLE'},
            'get_table_meta': {'tblId': 'DT_1B040A3', 'metaType': 'ITM'}
        }
        
        return test_params_map.get(tool_name, {})
    
    async def _call_tool_async(self, tool_func, params: Dict[str, Any]) -> Any:
        """비동기로 도구 호출"""
        # 동기 함수를 비동기로 실행
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: tool_func(**params))
    
    def _validate_tool_result(self, tool_name: str, result: Any) -> bool:
        """도구 결과 검증"""
        
        if not isinstance(result, dict):
            return False
        
        # 기본 검증: error가 없고 data가 있는지
        if result.get('error'):
            return False
        
        # 도구별 특별 검증
        if tool_name in ['search_kosis', 'fetch_kosis_data']:
            data = result.get('data', [])
            return isinstance(data, list) and len(data) > 0
        elif tool_name in ['get_stat_list', 'get_table_meta']:
            return 'data' in result
        
        return True
    
    def _generate_recommendations(self, success_rate: float) -> List[str]:
        """성공률 기반 권장사항 생성"""
        
        recommendations = []
        
        if success_rate >= 0.8:
            recommendations.append("🎯 모든 MCP 도구가 정상 작동합니다.")
        elif success_rate >= 0.5:
            recommendations.append("⚠️ 일부 MCP 도구에 문제가 있습니다. 폴백 전략을 준비하세요.")
            recommendations.append("🔧 실패한 도구들을 재시작해보세요.")
        else:
            recommendations.append("❌ 대부분의 MCP 도구가 작동하지 않습니다.")
            recommendations.append("🚨 폴백 모드로 전환하거나 더미 데이터를 사용하세요.")
            recommendations.append("🔍 MCP 서버 설정을 점검해보세요.")
        
        return recommendations
    
    def get_tool_health(self, tool_name: str) -> Optional[MCPToolHealth]:
        """특정 도구의 상태 조회"""
        return self.tool_health.get(tool_name)
    
    def is_tool_available(self, tool_name: str) -> bool:
        """도구 사용 가능 여부 확인"""
        health = self.get_tool_health(tool_name)
        return health.available if health else False
    
    def get_available_tools(self) -> List[str]:
        """사용 가능한 도구 목록"""
        return [name for name, health in self.tool_health.items() if health.available]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """전체 상태 요약"""
        if not self.initialized:
            return {'status': 'not_initialized'}
        
        total_tools = len(self.tool_health)
        available_tools = len([h for h in self.tool_health.values() if h.available])
        
        return {
            'status': 'initialized',
            'total_tools': total_tools,
            'available_tools': available_tools,
            'success_rate': available_tools / total_tools if total_tools > 0 else 0,
            'available_tool_names': self.get_available_tools(),
            'last_check': max([h.last_test_time for h in self.tool_health.values()]) if self.tool_health else 0,
            'recommendations': self.initialization_results.get('recommendations', [])
        }
    
    async def retest_failed_tools(self, mcp_tools: Dict[str, Any]) -> Dict[str, Any]:
        """실패한 도구들 재테스트"""
        
        failed_tools = [name for name, health in self.tool_health.items() if not health.available]
        
        if not failed_tools:
            return {'message': '재테스트할 실패한 도구가 없습니다.', 'retested_tools': []}
        
        self.logger.info(f"[MCPHealthChecker] 🔄 실패한 도구 재테스트: {failed_tools}")
        
        retest_results = {'retested_tools': [], 'newly_available': [], 'still_failed': []}
        
        for tool_name in failed_tools:
            if tool_name in mcp_tools:
                new_health = await self._test_single_tool(tool_name, mcp_tools[tool_name])
                old_health = self.tool_health[tool_name]
                
                # 통계 업데이트
                new_health.test_count = old_health.test_count + 1
                if new_health.available:
                    new_health.success_count = old_health.success_count + 1
                else:
                    new_health.success_count = old_health.success_count
                
                new_health.success_rate = new_health.success_count / new_health.test_count
                
                self.tool_health[tool_name] = new_health
                retest_results['retested_tools'].append(tool_name)
                
                if new_health.available:
                    retest_results['newly_available'].append(tool_name)
                    self.logger.info(f"[MCPHealthChecker] ✅ {tool_name} 재테스트 성공!")
                else:
                    retest_results['still_failed'].append(tool_name)
        
        return retest_results

# 전역 health checker 인스턴스
_health_checker = None

def get_mcp_health_checker() -> MCPHealthChecker:
    """전역 MCP Health Checker 인스턴스 반환"""
    global _health_checker
    if _health_checker is None:
        _health_checker = MCPHealthChecker()
    return _health_checker 