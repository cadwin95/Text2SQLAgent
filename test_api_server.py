#!/usr/bin/env python3
"""
API 서버 테스트 스크립트
=======================
통합 AI Assistant API 서버의 기능을 테스트합니다.
"""

import asyncio
import json
import time
import requests
from typing import Dict, Any

# API 서버 기본 URL
API_BASE_URL = "http://localhost:8000"

def test_server_health():
    """서버 상태 확인"""
    print("🏥 서버 Health Check")
    print("-" * 30)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ 서버 상태: 정상")
            print(f"📊 OpenAI 연결: {'✅' if data.get('openai') else '❌'}")
            print(f"🔌 MCP 서버 수: {len(data.get('mcp_servers', []))}")
            
            for server in data.get('mcp_servers', []):
                status = "✅" if server.get('connected') else "❌"
                print(f"   - {server['name']}: {status}")
            
            return True
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ Health Check 실패: {e}")
        return False

def test_tools_endpoint():
    """도구 목록 엔드포인트 테스트"""
    print("\n🛠️ 도구 목록 조회 테스트")
    print("-" * 30)
    
    try:
        response = requests.get(f"{API_BASE_URL}/tools", timeout=5)
        if response.status_code == 200:
            data = response.json()
            tools = data.get('tools', [])
            resources = data.get('resources', [])
            prompts = data.get('prompts', [])
            
            print(f"✅ 도구: {len(tools)}개")
            for tool in tools:
                print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
            
            print(f"✅ 리소스: {len(resources)}개")
            for resource in resources:
                print(f"   - {resource.get('uri', 'Unknown')}")
            
            print(f"✅ 프롬프트: {len(prompts)}개")
            for prompt in prompts:
                print(f"   - {prompt.get('name', 'Unknown')}")
            
            return True
        else:
            print(f"❌ 도구 목록 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 도구 목록 조회 오류: {e}")
        return False

def test_chat_completion(question: str, question_type: str = "일반"):
    """채팅 완료 API 테스트"""
    print(f"\n💬 채팅 API 테스트 ({question_type})")
    print(f"❓ 질문: {question}")
    print("-" * 50)
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.7,
        "stream": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            print(f"✅ 응답 성공 (소요시간: {end_time - start_time:.2f}초)")
            print(f"📝 응답 길이: {len(content)}자")
            print(f"🤖 응답 미리보기: {content[:200]}...")
            
            # 토큰 사용량 확인
            usage = data.get('usage', {})
            if usage:
                print(f"🔢 토큰 사용량:")
                print(f"   - 프롬프트: {usage.get('prompt_tokens', 0)}")
                print(f"   - 완료: {usage.get('completion_tokens', 0)}")
                print(f"   - 총합: {usage.get('total_tokens', 0)}")
            
            return True
        else:
            print(f"❌ 채팅 API 실패: {response.status_code}")
            try:
                error_data = response.json()
                print(f"오류 내용: {error_data}")
            except:
                print(f"응답 텍스트: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print("❌ 요청 시간 초과 (30초)")
        return False
    except Exception as e:
        print(f"❌ 채팅 API 오류: {e}")
        return False

def test_streaming_chat(question: str):
    """스트리밍 채팅 API 테스트"""
    print(f"\n🌊 스트리밍 채팅 테스트")
    print(f"❓ 질문: {question}")
    print("-" * 50)
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 500,
        "temperature": 0.7,
        "stream": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ 스트리밍 시작...")
            
            full_content = ""
            chunk_count = 0
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:].strip()
                        
                        if data_str == '[DONE]':
                            print("\n✅ 스트리밍 완료")
                            break
                        
                        try:
                            data = json.loads(data_str)
                            content = data.get('content', '')
                            if content:
                                full_content += content
                                chunk_count += 1
                                print(content, end='', flush=True)
                        except json.JSONDecodeError:
                            continue
            
            print(f"\n📊 스트리밍 통계:")
            print(f"   - 청크 수: {chunk_count}")
            print(f"   - 총 길이: {len(full_content)}자")
            
            return True
        else:
            print(f"❌ 스트리밍 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 스트리밍 오류: {e}")
        return False

def run_comprehensive_test():
    """종합 테스트 실행"""
    print("🚀 통합 AI Assistant API 서버 종합 테스트")
    print("=" * 60)
    
    test_results = []
    
    # 1. 서버 상태 확인
    result = test_server_health()
    test_results.append(("Health Check", result))
    
    if not result:
        print("\n❌ 서버가 실행되지 않았습니다. 먼저 서버를 시작하세요:")
        print("python api_server.py")
        return
    
    # 2. 도구 목록 확인
    result = test_tools_endpoint()
    test_results.append(("Tools Endpoint", result))
    
    # 3. 일반 대화 테스트
    general_questions = [
        "안녕하세요!",
        "오늘 몇 시야?",
        "파이썬으로 Hello World를 출력하는 방법을 알려주세요"
    ]
    
    for question in general_questions:
        result = test_chat_completion(question, "일반 대화")
        test_results.append((f"일반 대화: {question[:20]}...", result))
    
    # 4. 데이터 분석 테스트
    data_questions = [
        "한국의 인구 통계를 보여주세요",
        "GDP 성장률을 분석해주세요",
        "최근 고용률 통계를 조회해주세요"
    ]
    
    for question in data_questions:
        result = test_chat_completion(question, "데이터 분석")
        test_results.append((f"데이터 분석: {question[:20]}...", result))
    
    # 5. 스트리밍 테스트
    result = test_streaming_chat("간단한 인사말을 해주세요")
    test_results.append(("스트리밍 채팅", result))
    
    # 결과 요약
    print(f"\n📊 테스트 결과 요약")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name:30} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n🎯 총 {len(test_results)}개 테스트 중:")
    print(f"✅ 통과: {passed}개")
    print(f"❌ 실패: {failed}개")
    print(f"📈 성공률: {passed/len(test_results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 모든 테스트가 통과했습니다!")
    else:
        print(f"\n⚠️ {failed}개의 테스트가 실패했습니다. 로그를 확인해주세요.")

if __name__ == "__main__":
    run_comprehensive_test() 