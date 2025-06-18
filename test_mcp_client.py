#!/usr/bin/env python3
"""
MCP Client 테스트 스크립트
========================
MCP 클라이언트와 KOSIS 서버 연결을 테스트합니다.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_client.client import MCPClient, MCPServerConfig

async def test_mcp_client():
    """MCP 클라이언트 기본 기능 테스트"""
    print("🔌 MCP Client 테스트 시작")
    
    # MCP 클라이언트 생성
    client = MCPClient()
    
    try:
        # KOSIS 서버 설정
        kosis_config = MCPServerConfig(
            name="kosis",
            command="python",
            args=["mcp_servers/kosis_server/server.py"],
            env={"KOSIS_OPEN_API_KEY": os.getenv("KOSIS_OPEN_API_KEY", "")}
        )
        
        print("📡 KOSIS MCP 서버에 연결 중...")
        success = await client.add_server(kosis_config)
        
        if success:
            print("✅ KOSIS MCP 서버 연결 성공!")
            
            # 서버 목록 확인
            servers = client.list_servers()
            print(f"📋 연결된 서버: {len(servers)}개")
            for server in servers:
                print(f"  - {server['name']}: {server['tools']}개 도구, {server['resources']}개 리소스, {server['prompts']}개 프롬프트")
            
            # 도구 목록 확인
            tools = client.list_all_tools()
            print(f"\n🛠️ 사용 가능한 도구: {len(tools)}개")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")
            
            # 리소스 목록 확인
            resources = client.list_all_resources()
            print(f"\n📁 사용 가능한 리소스: {len(resources)}개")
            for resource in resources:
                print(f"  - {resource['uri']}: {resource['name']}")
            
            # 프롬프트 목록 확인
            prompts = client.list_all_prompts()
            print(f"\n💬 사용 가능한 프롬프트: {len(prompts)}개")
            for prompt in prompts:
                print(f"  - {prompt['name']}: {prompt['description']}")
            
            # 도구 호출 테스트
            print("\n🧪 도구 호출 테스트...")
            
            # 1. 통계 검색 테스트
            print("1️⃣ 통계 검색 테스트 (키워드: 인구)")
            try:
                result = await client.call_tool(
                    "kosis",
                    "search_statistics",
                    {"keyword": "인구"}
                )
                print(f"   결과: {result['success']}")
                if result['success']:
                    content = result.get('content', {})
                    if isinstance(content, dict) and 'results' in content:
                        print(f"   검색 결과: {len(content['results'])}개")
                    else:
                        print(f"   응답: {str(content)[:200]}...")
                else:
                    print(f"   오류: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"   예외 발생: {e}")
            
            # 2. 통계 목록 테스트
            print("\n2️⃣ 통계 목록 테스트")
            try:
                result = await client.call_tool(
                    "kosis",
                    "list_statistics",
                    {"vwCd": "MT_ZTITLE"}
                )
                print(f"   결과: {result['success']}")
                if result['success']:
                    content = result.get('content', {})
                    if isinstance(content, dict) and 'list' in content:
                        print(f"   목록 개수: {len(content['list'])}개")
                    else:
                        print(f"   응답: {str(content)[:200]}...")
                else:
                    print(f"   오류: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"   예외 발생: {e}")
            
            # 3. 통계 데이터 조회 테스트 (주민등록인구)
            print("\n3️⃣ 통계 데이터 조회 테스트 (주민등록인구)")
            try:
                result = await client.call_tool(
                    "kosis",
                    "fetch_statistics_data",
                    {
                        "orgId": "101",
                        "tblId": "DT_1B040A3",
                        "startPrdDe": "2020",
                        "endPrdDe": "2023",
                        "prdSe": "Y"
                    }
                )
                print(f"   결과: {result['success']}")
                if result['success']:
                    content = result.get('content', {})
                    if isinstance(content, dict) and 'data' in content:
                        data = content['data']
                        if hasattr(data, 'shape'):
                            print(f"   데이터 크기: {data.shape}")
                        else:
                            print(f"   데이터: {str(data)[:200]}...")
                    else:
                        print(f"   응답: {str(content)[:200]}...")
                else:
                    print(f"   오류: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"   예외 발생: {e}")
            
        else:
            print("❌ KOSIS MCP 서버 연결 실패")
            return False
            
    except Exception as e:
        print(f"❌ MCP 클라이언트 테스트 실패: {e}")
        return False
    
    finally:
        # 연결 정리
        await client.close_all()
        print("\n🔌 MCP 연결 종료")
    
    return True

async def main():
    """메인 실행 함수"""
    print("🚀 MCP Client 통합 테스트")
    print("=" * 50)
    
    # 환경변수 확인
    api_key = os.getenv("KOSIS_OPEN_API_KEY")
    if not api_key:
        print("❌ KOSIS_OPEN_API_KEY 환경변수가 설정되지 않았습니다.")
        return
    else:
        print(f"✅ KOSIS API 키 확인됨: {api_key[:10]}...")
    
    # MCP 클라이언트 테스트
    success = await test_mcp_client()
    
    if success:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n💥 테스트 실패")

if __name__ == "__main__":
    asyncio.run(main()) 