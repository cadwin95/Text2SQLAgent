#!/usr/bin/env python3
"""
End-to-End 통합 테스트 스크립트
===============================
전체 시스템의 End-to-End 기능을 테스트합니다.
"""

import json
import time
import requests
from typing import Dict, Any, List

class E2ETestRunner:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        
    def test_system_integration(self) -> Dict[str, Any]:
        """시스템 통합 테스트"""
        print("🔗 시스템 통합 테스트")
        print("=" * 50)
        
        results = {
            "api_server": False,
            "frontend": False,
            "mcp_connection": False,
            "fallback_system": False
        }
        
        # 1. API 서버 상태 확인
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                results["api_server"] = True
                print("✅ API 서버: 정상")
                
                # MCP 서버 연결 상태 확인
                mcp_servers = data.get('mcp_servers', [])
                if mcp_servers:
                    connected_servers = [s for s in mcp_servers if s.get('connected')]
                    if connected_servers:
                        results["mcp_connection"] = True
                        print(f"✅ MCP 연결: {len(connected_servers)}개 서버 연결됨")
                    else:
                        print("⚠️ MCP 연결: 연결된 서버 없음 (Fallback 모드)")
                        results["fallback_system"] = True
                else:
                    print("⚠️ MCP 서버: 설정되지 않음 (Fallback 모드)")
                    results["fallback_system"] = True
            else:
                print(f"❌ API 서버: 응답 오류 ({response.status_code})")
        except Exception as e:
            print(f"❌ API 서버: 연결 실패 ({e})")
        
        # 2. Frontend 상태 확인
        try:
            response = requests.get(self.frontend_url, timeout=5)
            if response.status_code == 200:
                results["frontend"] = True
                print("✅ Frontend: 정상")
            else:
                print(f"❌ Frontend: 응답 오류 ({response.status_code})")
        except Exception as e:
            print(f"❌ Frontend: 연결 실패 ({e})")
        
        return results
    
    def test_chat_scenarios(self) -> List[Dict[str, Any]]:
        """다양한 채팅 시나리오 테스트"""
        print("\n💬 채팅 시나리오 테스트")
        print("=" * 50)
        
        scenarios = [
            {
                "name": "일반 인사",
                "message": "안녕하세요!",
                "expected_type": "general",
                "timeout": 10
            },
            {
                "name": "프로그래밍 질문",
                "message": "Python 리스트 컴프리헨션을 설명해주세요",
                "expected_type": "general",
                "timeout": 15
            },
            {
                "name": "인구 통계 데이터",
                "message": "한국의 인구 통계를 보여주세요",
                "expected_type": "data",
                "timeout": 20
            },
            {
                "name": "경제 지표 분석",
                "message": "GDP 성장률을 분석해주세요",
                "expected_type": "data",
                "timeout": 20
            }
        ]
        
        results = []
        
        for scenario in scenarios:
            print(f"\n🎯 시나리오: {scenario['name']}")
            print(f"📝 메시지: {scenario['message']}")
            
            result = self.test_single_chat(
                scenario['message'], 
                scenario['timeout']
            )
            
            result['scenario'] = scenario['name']
            result['expected_type'] = scenario['expected_type']
            results.append(result)
            
            if result['success']:
                print(f"✅ 성공 (응답시간: {result['response_time']:.2f}초)")
                print(f"📊 응답 길이: {result['response_length']}자")
            else:
                print(f"❌ 실패: {result['error']}")
        
        return results
    
    def test_single_chat(self, message: str, timeout: int = 15) -> Dict[str, Any]:
        """단일 채팅 테스트"""
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
            "stream": False
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.api_base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                return {
                    'success': True,
                    'response_time': end_time - start_time,
                    'response_length': len(content),
                    'content': content,
                    'usage': data.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'response_time': end_time - start_time
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response_time': 0
            }
    
    def test_streaming_functionality(self) -> Dict[str, Any]:
        """스트리밍 기능 테스트"""
        print("\n🌊 스트리밍 기능 테스트")
        print("=" * 50)
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": "간단한 파이썬 코드 예제를 보여주세요"
                }
            ],
            "max_tokens": 300,
            "temperature": 0.7,
            "stream": True
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.api_base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                stream=True,
                timeout=20
            )
            
            if response.status_code == 200:
                chunks = []
                full_content = ""
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:].strip()
                            
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                data = json.loads(data_str)
                                content = data.get('content', '')
                                if content:
                                    chunks.append(content)
                                    full_content += content
                            except json.JSONDecodeError:
                                continue
                
                end_time = time.time()
                
                return {
                    'success': True,
                    'response_time': end_time - start_time,
                    'chunk_count': len(chunks),
                    'total_length': len(full_content),
                    'content': full_content
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_test_report(self, integration_results: Dict, chat_results: List, streaming_result: Dict):
        """테스트 보고서 생성"""
        print("\n📊 테스트 결과 종합 보고서")
        print("=" * 60)
        
        # 시스템 통합 결과
        print("\n🔗 시스템 통합 테스트:")
        for component, status in integration_results.items():
            status_icon = "✅" if status else "❌"
            print(f"   {component:20} {status_icon}")
        
        # 채팅 시나리오 결과
        print("\n💬 채팅 시나리오 테스트:")
        successful_chats = sum(1 for r in chat_results if r['success'])
        print(f"   성공률: {successful_chats}/{len(chat_results)} ({successful_chats/len(chat_results)*100:.1f}%)")
        
        for result in chat_results:
            status_icon = "✅" if result['success'] else "❌"
            print(f"   {result['scenario']:20} {status_icon}")
        
        # 스트리밍 결과
        print(f"\n🌊 스트리밍 테스트:")
        status_icon = "✅" if streaming_result['success'] else "❌"
        print(f"   스트리밍 기능        {status_icon}")
        
        if streaming_result['success']:
            print(f"   - 청크 수: {streaming_result['chunk_count']}")
            print(f"   - 응답 시간: {streaming_result['response_time']:.2f}초")
        
        # 전체 요약
        total_tests = len(integration_results) + len(chat_results) + 1
        passed_tests = (
            sum(integration_results.values()) + 
            successful_chats + 
            (1 if streaming_result['success'] else 0)
        )
        
        print(f"\n🎯 전체 테스트 요약:")
        print(f"   총 테스트: {total_tests}개")
        print(f"   통과: {passed_tests}개")
        print(f"   실패: {total_tests - passed_tests}개")
        print(f"   성공률: {passed_tests/total_tests*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 모든 테스트가 성공했습니다!")
            print("   시스템이 정상적으로 작동하고 있습니다.")
        else:
            print(f"\n⚠️ {total_tests - passed_tests}개의 테스트가 실패했습니다.")
            print("   실패한 컴포넌트를 확인하고 수정이 필요합니다.")
    
    def run_full_test_suite(self):
        """전체 테스트 스위트 실행"""
        print("🚀 End-to-End 통합 테스트 시작")
        print("=" * 60)
        print(f"🔗 API 서버: {self.api_base_url}")
        print(f"🌐 Frontend: {self.frontend_url}")
        print("=" * 60)
        
        # 1. 시스템 통합 테스트
        integration_results = self.test_system_integration()
        
        # 2. 채팅 시나리오 테스트
        chat_results = self.test_chat_scenarios()
        
        # 3. 스트리밍 기능 테스트
        streaming_result = self.test_streaming_functionality()
        
        # 4. 테스트 보고서 생성
        self.generate_test_report(integration_results, chat_results, streaming_result)

def main():
    """메인 실행 함수"""
    tester = E2ETestRunner()
    tester.run_full_test_suite()

if __name__ == "__main__":
    main() 