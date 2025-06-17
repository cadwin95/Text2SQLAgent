#!/usr/bin/env python3
"""
🚀 통합 AI Assistant 시작 스크립트 v3.0
========================================

📋 시스템 구성:
┌─────────────────────────────────────────────────────────────────┐
│                      전체 시스템 실행                            │
│                                                                 │
│  1️⃣ 환경 검증                                                   │
│     ├── Python 3.8+ 확인                                        │
│     ├── Node.js 확인                                            │
│     ├── OPENAI_API_KEY 확인                                      │
│     └── KOSIS_OPEN_API_KEY 확인 (선택사항)                        │
│                                                                 │
│  2️⃣ 의존성 설치 (옵션)                                           │
│     ├── Python packages (FastAPI, OpenAI, MCP)                  │
│     └── Frontend packages (Next.js, React)                      │
│                                                                 │
│  3️⃣ 서비스 시작                                                  │
│     ├── API 서버 (포트 8000)                                     │
│     │   ├── OpenAI 클라이언트 초기화                             │
│     │   ├── MCP 클라이언트 연결 시도                             │
│     │   └── Fallback 시스템 준비                                │
│     │                                                           │
│     └── Frontend 서버 (포트 3000)                                │
│         ├── Next.js 개발 서버                                    │
│         ├── React 컴포넌트                                       │
│         └── API 통신 설정                                        │
│                                                                 │
│  4️⃣ 상태 모니터링                                                │
│     ├── 프로세스 상태 확인                                       │
│     ├── API 서버 Health Check                                   │
│     ├── MCP 연결 상태 확인                                       │
│     └── 실시간 로그 출력                                         │
└─────────────────────────────────────────────────────────────────┘

🎯 주요 특징:
- 완전 자동화된 시스템 시작
- 견고한 오류 처리 및 복구
- 실시간 상태 모니터링
- 우아한 종료 처리 (Ctrl+C)

🔧 사용법:
1. 환경변수 설정 (.env 파일)
2. python start_system.py 실행
3. 웹브라우저에서 http://localhost:3000 접속
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

# 색상 코드
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

class SystemLauncher:
    def __init__(self):
        self.processes = []
        self.root_dir = Path(__file__).parent
        
    def print_banner(self):
        print(f"""
{BLUE}╔═══════════════════════════════════════════════════════════╗
║         통합 AI Assistant System v3.0                      ║
║     General Chat + Data Analysis with MCP                  ║
╚═══════════════════════════════════════════════════════════╝{RESET}

{GREEN}🤖 시스템 구성:{RESET}
├── 🧠 OpenAI GPT (일반 대화)
├── 📊 KOSIS MCP Server (데이터 분석)
├── 🌐 통합 API 서버 (포트: 8000)
└── 🎨 Frontend Next.js (포트: 3000)

{YELLOW}📝 필수 환경변수 (.env 파일):{RESET}
- OPENAI_API_KEY: OpenAI API 키
- KOSIS_OPEN_API_KEY: KOSIS API 키
""")
        
    def check_requirements(self):
        """필수 요구사항 확인"""
        print(f"{BLUE}📋 시스템 요구사항 확인 중...{RESET}")
        
        # Python 버전 확인
        if sys.version_info < (3, 8):
            print(f"{RED}❌ Python 3.8 이상이 필요합니다.{RESET}")
            return False
            
        # Node.js 확인
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            node_version = result.stdout.strip()
            print(f"{GREEN}✅ Node.js {node_version}{RESET}")
        except:
            print(f"{RED}❌ Node.js가 설치되지 않았습니다.{RESET}")
            return False
            
        # 환경변수 확인
        if not os.getenv('OPENAI_API_KEY'):
            print(f"{RED}❌ OPENAI_API_KEY가 설정되지 않았습니다.{RESET}")
            return False
        else:
            print(f"{GREEN}✅ OpenAI API 키 설정됨{RESET}")
            
        if not os.getenv('KOSIS_OPEN_API_KEY'):
            print(f"{YELLOW}⚠️  KOSIS_OPEN_API_KEY가 설정되지 않았습니다. 데이터 분석 기능이 제한될 수 있습니다.{RESET}")
        else:
            print(f"{GREEN}✅ KOSIS API 키 설정됨{RESET}")
            
        return True
        
    def install_dependencies(self):
        """의존성 설치"""
        print(f"\n{BLUE}📦 의존성 설치 중...{RESET}")
        
        # Python 패키지 설치
        print(f"{YELLOW}Installing Python packages...{RESET}")
        requirements = [
            "fastapi",
            "uvicorn",
            "openai",
            "mcp",
            "python-dotenv",
            "pandas",
            "requests"
        ]
        
        for package in requirements:
            subprocess.run([sys.executable, '-m', 'pip', 'install', package])
        
        # Frontend 패키지 설치
        print(f"{YELLOW}Installing Frontend packages...{RESET}")
        os.chdir(self.root_dir / 'frontend')
        subprocess.run(['npm', 'install'])
        os.chdir(self.root_dir)
        
    def start_api_server(self):
        """통합 API 서버 시작"""
        print(f"\n{GREEN}🚀 통합 API 서버 시작 중...{RESET}")
        proc = subprocess.Popen(
            [sys.executable, 'api_server.py'],
            cwd=self.root_dir
        )
        self.processes.append(proc)
        time.sleep(5)  # 서버 시작 대기
        return True
        
    def start_frontend(self):
        """Frontend 개발 서버 시작"""
        print(f"\n{GREEN}🚀 Frontend 개발 서버 시작 중...{RESET}")
        proc = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd=self.root_dir / 'frontend',
            shell=True
        )
        self.processes.append(proc)
        return True
        
    def test_api_connection(self):
        """API 서버 연결 테스트"""
        import requests
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print(f"{GREEN}✅ API 서버 정상 작동 중{RESET}")
                health_data = response.json()
                if health_data.get('openai'):
                    print(f"{GREEN}  - OpenAI 연결 상태: ✅{RESET}")
                if health_data.get('mcp_servers'):
                    print(f"{GREEN}  - MCP 서버 수: {len(health_data['mcp_servers'])}{RESET}")
                return True
        except:
            pass
        return False
        
    def monitor_processes(self):
        """프로세스 모니터링"""
        print(f"\n{GREEN}✅ 모든 서비스가 시작되었습니다!{RESET}")
        print(f"\n{BLUE}📌 접속 정보:{RESET}")
        print(f"- Frontend: http://localhost:3000")
        print(f"- API 서버: http://localhost:8000")
        print(f"- API 문서: http://localhost:8000/docs")
        print(f"- Health Check: http://localhost:8000/health")
        print(f"\n{YELLOW}💡 사용 팁:{RESET}")
        print(f"- 일반 대화: '안녕하세요', '오늘 날씨 어때?', '지금 몇 시야?'")
        print(f"- 데이터 분석: '인구 통계 보여줘', 'GDP 추이 분석해줘'")
        print(f"\n{YELLOW}종료하려면 Ctrl+C를 누르세요.{RESET}")
        
        try:
            while True:
                # 프로세스 상태 확인
                for proc in self.processes:
                    if proc.poll() is not None:
                        print(f"{RED}⚠️  프로세스가 종료되었습니다: PID {proc.pid}{RESET}")
                time.sleep(5)
        except KeyboardInterrupt:
            self.shutdown()
            
    def shutdown(self):
        """시스템 종료"""
        print(f"\n{YELLOW}🛑 시스템을 종료합니다...{RESET}")
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        print(f"{GREEN}✅ 종료 완료{RESET}")
        
    def run(self):
        """시스템 실행"""
        self.print_banner()
        
        if not self.check_requirements():
            sys.exit(1)
            
        # 의존성 설치 옵션
        install = input(f"\n{YELLOW}의존성을 설치하시겠습니까? (y/N): {RESET}")
        if install.lower() == 'y':
            self.install_dependencies()
            
        # 서비스 시작
        if not self.start_api_server():
            print(f"{RED}API 서버 시작 실패{RESET}")
            sys.exit(1)
            
        # API 서버 연결 테스트
        print(f"\n{BLUE}🔍 API 서버 연결 테스트 중...{RESET}")
        time.sleep(3)
        if self.test_api_connection():
            print(f"{GREEN}✅ API 서버 준비 완료!{RESET}")
        else:
            print(f"{YELLOW}⚠️  API 서버 응답이 느립니다. 계속 진행합니다.{RESET}")
            
        if not self.start_frontend():
            print(f"{RED}Frontend 시작 실패{RESET}")
            sys.exit(1)
            
        # 모니터링
        self.monitor_processes()

if __name__ == "__main__":
    launcher = SystemLauncher()
    launcher.run() 