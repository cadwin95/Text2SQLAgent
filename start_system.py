#!/usr/bin/env python3
"""
Text2SQL Agent 시스템 시작 스크립트
백엔드와 프론트엔드를 자동으로 시작합니다.
"""

import os
import sys
import subprocess
import platform
import time
import shutil
from pathlib import Path


def print_banner():
    """시작 배너 출력"""
    print("=" * 50)
    print("     Text2SQL Agent 시스템 시작")
    print("=" * 50)
    print()


def check_python():
    """Python 버전 확인"""
    print("Python 버전 확인 중...")
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("오류: Python 3.8 이상이 필요합니다.")
        return False
    
    print("✓ Python 버전 확인 완료")
    print()
    return True


def check_node():
    """Node.js 버전 확인"""
    print("Node.js 버전 확인 중...")
    try:
        result = subprocess.run(["node", "--version"], 
                              capture_output=True, text=True, check=True)
        version = result.stdout.strip()
        print(f"Node.js {version}")
        
        # 버전 번호 추출 (v18.0.0 -> 18)
        major_version = int(version.split('.')[0][1:])
        if major_version < 18:
            print("경고: Node.js 18 이상을 권장합니다.")
            
        print("✓ Node.js 버전 확인 완료")
        print()
        return True
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("오류: Node.js가 설치되지 않았거나 PATH에 등록되지 않았습니다.")
        print("Node.js 18 이상을 설치하고 PATH에 등록해주세요.")
        return False


def setup_virtual_environment():
    """가상환경 설정"""
    print("백엔드 가상환경 확인 중...")
    
    # .venv 우선 확인, 없으면 venv 확인
    venv_path = Path(".venv")
    if not venv_path.exists():
        venv_path = Path("venv")
        if not venv_path.exists():
            print("가상환경이 없습니다. .venv로 생성 중...")
            try:
                subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
                venv_path = Path(".venv")
                print("✓ 가상환경 생성 완료")
            except subprocess.CalledProcessError:
                print("오류: 가상환경 생성에 실패했습니다.")
                return False
        else:
            print("✓ 기존 venv 가상환경 확인 완료")
    else:
        print("✓ .venv 가상환경 확인 완료")
    
    # 가상환경 활성화 스크립트 경로
    system = platform.system()
    if system == "Windows":
        python_path = venv_path / "Scripts" / "python.exe"
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:
        python_path = venv_path / "bin" / "python"
        pip_path = venv_path / "bin" / "pip"
    
    # 의존성 설치
    print("백엔드 의존성 설치 중...")
    try:
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], 
                      check=True)
        print("✓ 백엔드 의존성 설치 완료")
        print()
        return python_path
    except subprocess.CalledProcessError:
        print("오류: 백엔드 의존성 설치에 실패했습니다.")
        return False


def setup_frontend():
    """프론트엔드 의존성 설정"""
    print("프론트엔드 의존성 확인 중...")
    
    frontend_path = Path("frontend")
    if not frontend_path.exists():
        print("오류: frontend 디렉토리가 없습니다.")
        return False
    
    node_modules_path = frontend_path / "node_modules"
    if not node_modules_path.exists():
        print("node_modules가 없습니다. 의존성 설치 중...")
        try:
            subprocess.run(["npm", "install"], cwd=frontend_path, check=True)
            print("✓ 프론트엔드 의존성 설치 완료")
        except subprocess.CalledProcessError:
            print("오류: 프론트엔드 의존성 설치에 실패했습니다.")
            return False
    else:
        print("✓ 프론트엔드 의존성 확인 완료")
    
    print()
    return True


def setup_environment():
    """환경 변수 파일 설정"""
    env_path = Path(".env")
    env_example_path = Path("env.example")
    
    if not env_path.exists():
        if env_example_path.exists():
            print(".env 파일이 없습니다. env.example을 복사합니다...")
            shutil.copy(env_example_path, env_path)
            print("✓ .env 파일 생성 완료")
        else:
            print("경고: .env 파일과 env.example 파일이 모두 없습니다.")
            print("필요한 환경 변수를 설정해주세요.")
    else:
        print("✓ .env 파일 확인 완료")
    
    print()


def start_backend(python_path):
    """백엔드 서버 시작"""
    print("백엔드 서버 시작 중...")
    
    system = platform.system()
    if system == "Windows":
        # Windows에서 새 터미널 창으로 실행
        cmd = f'start "백엔드 서버" cmd /k "{python_path} -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"'
        subprocess.Popen(cmd, shell=True)
    else:
        # Linux/Mac에서 새 터미널 창으로 실행
        cmd = [str(python_path), "-m", "uvicorn", "backend.main:app", 
               "--host", "0.0.0.0", "--port", "8000", "--reload"]
        subprocess.Popen(cmd)
    
    print("✓ 백엔드 서버 시작됨 (새 터미널에서)")


def start_frontend():
    """프론트엔드 서버 시작"""
    print("프론트엔드 서버 시작 중...")
    
    system = platform.system()
    if system == "Windows":
        # Windows에서 새 터미널 창으로 실행
        cmd = 'start "프론트엔드 서버" cmd /k "cd frontend && npm run dev"'
        subprocess.Popen(cmd, shell=True)
    else:
        # Linux/Mac에서 새 터미널 창으로 실행
        subprocess.Popen(["npm", "run", "dev"], cwd="frontend")
    
    print("✓ 프론트엔드 서버 시작됨 (새 터미널에서)")


def print_completion_info():
    """완료 정보 출력"""
    print()
    print("=" * 50)
    print("     시스템 시작 완료!")
    print("=" * 50)
    print()
    print("🌐 서비스 URL:")
    print("   백엔드 서버: http://localhost:8000")
    print("   프론트엔드:  http://localhost:3000")
    print()
    print("📖 API 문서:")
    print("   Swagger UI:  http://localhost:8000/docs")
    print("   헬스 체크:   http://localhost:8000/health")
    print()
    print("🛑 종료 방법:")
    print("   각 터미널에서 Ctrl+C를 누르세요.")
    print()


def main():
    """메인 함수"""
    print_banner()
    
    # 현재 디렉토리 확인
    print(f"현재 디렉토리: {os.getcwd()}")
    print()
    
    # 전제 조건 확인
    if not check_python():
        sys.exit(1)
    
    if not check_node():
        sys.exit(1)
    
    # 백엔드 설정
    python_path = setup_virtual_environment()
    if not python_path:
        sys.exit(1)
    
    # 프론트엔드 설정
    if not setup_frontend():
        sys.exit(1)
    
    # 환경 변수 설정
    setup_environment()
    
    print("=" * 50)
    print("     서버 시작 중...")
    print("=" * 50)
    print()
    
    # 서버 시작
    start_backend(python_path)
    
    # 백엔드 초기화 대기
    print("백엔드 서버 초기화 대기 중...")
    time.sleep(5)
    
    start_frontend()
    
    # 완료 정보 출력
    print_completion_info()
    
    # 사용자 입력 대기
    try:
        input("계속하려면 Enter를 누르세요...")
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")


if __name__ == "__main__":
    main() 