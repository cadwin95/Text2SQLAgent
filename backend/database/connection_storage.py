"""
Connection Storage - 연결 정보 영구 저장
연결 설정을 JSON 파일로 저장하여 서버 재시작 후에도 유지
"""

import json
import os
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from datetime import datetime
from cryptography.fernet import Fernet
import base64

from .handlers.base_handler import ConnectionConfig, DatabaseType

logger = logging.getLogger(__name__)


class ConnectionStorage:
    """연결 정보 영구 저장 클래스"""
    
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.connections_file = self.storage_dir / "connections.json"
        self.key_file = self.storage_dir / "encryption.key"
        
        # 디렉토리 생성
        self.storage_dir.mkdir(exist_ok=True)
        
        # 암호화 키 초기화
        self._encryption_key = self._load_or_create_key()
        self._cipher = Fernet(self._encryption_key)
        
        # 파일 lock
        self._lock = asyncio.Lock()
    
    def _load_or_create_key(self) -> bytes:
        """암호화 키 로드 또는 생성"""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            # 새 키 생성
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key
    
    def _encrypt_sensitive_data(self, data: str) -> str:
        """민감한 데이터 암호화"""
        if not data:
            return data
        try:
            encrypted = self._cipher.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def _decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """민감한 데이터 복호화"""
        if not encrypted_data:
            return encrypted_data
        try:
            decoded = base64.b64decode(encrypted_data.encode())
            decrypted = self._cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data
    
    async def save_connections(self, connections: Dict[str, ConnectionConfig]) -> bool:
        """연결 정보 저장"""
        async with self._lock:
            try:
                connections_data = []
                
                for conn_id, config in connections.items():
                    # 연결 설정을 dict로 변환
                    conn_dict = {
                        "id": config.id,
                        "name": config.name,
                        "type": config.type.value,
                        "host": config.host,
                        "port": config.port,
                        "database": config.database,
                        "username": config.username,
                        # 민감한 데이터 암호화
                        "password": self._encrypt_sensitive_data(config.password) if config.password else None,
                        "connection_string": self._encrypt_sensitive_data(config.connection_string) if config.connection_string else None,
                        "ssl": config.ssl,
                        "options": config.options,
                        "created_at": config.created_at.isoformat() if config.created_at else None,
                        "updated_at": datetime.now().isoformat()
                    }
                    connections_data.append(conn_dict)
                
                # JSON 파일로 저장
                with open(self.connections_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "version": "1.0",
                        "saved_at": datetime.now().isoformat(),
                        "connections": connections_data
                    }, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Saved {len(connections)} connections to {self.connections_file}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save connections: {e}")
                return False
    
    async def load_connections(self) -> Dict[str, ConnectionConfig]:
        """연결 정보 로드"""
        async with self._lock:
            try:
                if not self.connections_file.exists():
                    logger.info("No saved connections found")
                    return {}
                
                with open(self.connections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                connections = {}
                
                for conn_data in data.get("connections", []):
                    try:
                        # ConnectionConfig 객체 재생성
                        config = ConnectionConfig(
                            id=conn_data["id"],
                            name=conn_data["name"],
                            type=DatabaseType(conn_data["type"]),
                            host=conn_data.get("host"),
                            port=conn_data.get("port"),
                            database=conn_data.get("database"),
                            username=conn_data.get("username"),
                            # 민감한 데이터 복호화
                            password=self._decrypt_sensitive_data(conn_data.get("password")) if conn_data.get("password") else None,
                            connection_string=self._decrypt_sensitive_data(conn_data.get("connection_string")) if conn_data.get("connection_string") else None,
                            ssl=conn_data.get("ssl", False),
                            options=conn_data.get("options", {}),
                            created_at=datetime.fromisoformat(conn_data["created_at"]) if conn_data.get("created_at") else datetime.now()
                        )
                        
                        connections[config.id] = config
                        
                    except Exception as e:
                        logger.error(f"Failed to load connection {conn_data.get('name', 'unknown')}: {e}")
                        continue
                
                logger.info(f"Loaded {len(connections)} connections from {self.connections_file}")
                return connections
                
            except Exception as e:
                logger.error(f"Failed to load connections: {e}")
                return {}
    
    async def delete_connection(self, connection_id: str) -> bool:
        """특정 연결 삭제"""
        connections = await self.load_connections()
        if connection_id in connections:
            del connections[connection_id]
            return await self.save_connections(connections)
        return True
    
    async def backup_connections(self, backup_name: Optional[str] = None) -> str:
        """연결 정보 백업"""
        if not backup_name:
            backup_name = f"connections_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        backup_file = self.storage_dir / backup_name
        
        try:
            if self.connections_file.exists():
                import shutil
                shutil.copy2(self.connections_file, backup_file)
                logger.info(f"Backup created: {backup_file}")
                return str(backup_file)
            else:
                logger.warning("No connections file to backup")
                return ""
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return ""
    
    def get_storage_info(self) -> Dict[str, Any]:
        """저장소 정보 조회"""
        info = {
            "storage_dir": str(self.storage_dir),
            "connections_file": str(self.connections_file),
            "file_exists": self.connections_file.exists(),
            "file_size": 0,
            "last_modified": None
        }
        
        if self.connections_file.exists():
            stat = self.connections_file.stat()
            info["file_size"] = stat.st_size
            info["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return info


# 전역 인스턴스
_storage_instance: Optional[ConnectionStorage] = None

def get_connection_storage() -> ConnectionStorage:
    """ConnectionStorage 싱글톤 인스턴스 반환"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ConnectionStorage()
    return _storage_instance 