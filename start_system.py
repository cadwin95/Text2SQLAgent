#!/usr/bin/env python3
"""
Text2SQL MCP 통합 시스템 시작 스크립트
=====================================
백엔드와 프론트엔드를 함께 시작하는 통합 스크립트
"""

import os
import sys
import subprocess
import time
import signal
import threading
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
║       Text2SQL MCP (Model Context Protocol) System        ║
╚═══════════════════════════════════════════════════════════╝{RESET}

{GREEN}🚀 시스템 구성:{RESET}
├── 📊 KOSIS MCP Server (포트: stdio)
├── 🔧 MCP Client Application (포트: 8100)
├── 🌐 Backend API Server (포트: 8000)
└── 🎨 Frontend Next.js (포트: 3000)

{YELLOW}📝 필수 환경변수 (.env 파일):{RESET}
- KOSIS_OPEN_API_KEY: KOSIS API 키
- OPENAI_API_KEY: OpenAI API 키
- OPENAI_MODEL: 사용할 모델 (기본: gpt-3.5-turbo)
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
        if not os.getenv('OPENAI_API_KEY') and not os.getenv('KOSIS_OPEN_API_KEY'):
            print(f"{YELLOW}⚠️  API 키가 설정되지 않았습니다. .env 파일을 확인하세요.{RESET}")
            
        return True
        
    def install_dependencies(self):
        """의존성 설치"""
        print(f"\n{BLUE}📦 의존성 설치 중...{RESET}")
        
        # Python 패키지 설치
        print(f"{YELLOW}Installing Python packages...{RESET}")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        
        # Frontend 패키지 설치
        print(f"{YELLOW}Installing Node packages...{RESET}")
        os.chdir(self.root_dir / 'frontend')
        subprocess.run(['npm', 'install'])
        os.chdir(self.root_dir)
        
    def start_kosis_server(self):
        """KOSIS MCP Server 시작"""
        print(f"\n{GREEN}🚀 KOSIS MCP Server 시작 중...{RESET}")
        # MCP 서버는 클라이언트가 자동으로 시작함
        return True
        
    def start_mcp_application(self):
        """MCP Client Application 시작"""
        print(f"\n{GREEN}🚀 MCP Client Application 시작 중...{RESET}")
        proc = subprocess.Popen(
            [sys.executable, 'application/main.py'],
            cwd=self.root_dir
        )
        self.processes.append(proc)
        time.sleep(3)  # 초기화 대기
        return True
        
    def start_backend(self):
        """Backend API Server 시작"""
        print(f"\n{GREEN}🚀 Backend API Server 시작 중...{RESET}")
        proc = subprocess.Popen(
            [sys.executable, 'backend/integrated_api_server.py'],
            cwd=self.root_dir
        )
        self.processes.append(proc)
        time.sleep(3)  # 서버 시작 대기
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
        
    def monitor_processes(self):
        """프로세스 모니터링"""
        print(f"\n{GREEN}✅ 모든 서비스가 시작되었습니다!{RESET}")
        print(f"\n{BLUE}📌 접속 정보:{RESET}")
        print(f"- Frontend: http://localhost:3000")
        print(f"- Backend API: http://localhost:8000")
        print(f"- API 문서: http://localhost:8000/docs")
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
        if not self.start_backend():
            print(f"{RED}Backend 시작 실패{RESET}")
            sys.exit(1)
            
        if not self.start_frontend():
            print(f"{RED}Frontend 시작 실패{RESET}")
            sys.exit(1)
            
        # 모니터링
        self.monitor_processes()

if __name__ == "__main__":
    launcher = SystemLauncher()
    launcher.run() 