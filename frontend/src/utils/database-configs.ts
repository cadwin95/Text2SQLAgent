import { DatabaseConnectionConfig, DatabaseType, DatabaseConnection } from '@/types/database';

export const DATABASE_CONFIGS: Record<DatabaseType, DatabaseConnectionConfig> = {
  mysql: {
    type: 'mysql',
    label: 'MySQL',
    icon: '🐬',
    defaultPort: 3306,
    description: 'MySQL 관계형 데이터베이스',
    documentationUrl: 'https://dev.mysql.com/doc/',
    fields: [
      {
        name: 'host',
        label: '호스트',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        defaultValue: 'localhost',
        description: 'MySQL 서버 호스트 주소'
      },
      {
        name: 'port',
        label: '포트',
        type: 'number',
        required: true,
        defaultValue: 3306,
        validation: { min: 1, max: 65535 }
      },
      {
        name: 'database',
        label: '데이터베이스',
        type: 'text',
        required: true,
        placeholder: 'mydb',
        description: '연결할 데이터베이스 이름'
      },
      {
        name: 'username',
        label: '사용자명',
        type: 'text',
        required: true,
        placeholder: 'root'
      },
      {
        name: 'password',
        label: '비밀번호',
        type: 'password',
        required: false,
        placeholder: '비밀번호'
      },
      {
        name: 'ssl',
        label: 'SSL 사용',
        type: 'boolean',
        required: false,
        defaultValue: false,
        description: 'SSL 연결 사용 여부'
      },
      {
        name: 'schema',
        label: '기본 스키마',
        type: 'text',
        required: false,
        placeholder: '스키마명 (선택)',
        description: '기본 스키마명 (미지정시 데이터베이스명 사용)'
      }
    ]
  },

  postgresql: {
    type: 'postgresql',
    label: 'PostgreSQL',
    icon: '🐘',
    defaultPort: 5432,
    description: '고급 오픈소스 관계형 데이터베이스',
    documentationUrl: 'https://www.postgresql.org/docs/',
    fields: [
      {
        name: 'host',
        label: '호스트',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        defaultValue: 'localhost'
      },
      {
        name: 'port',
        label: '포트',
        type: 'number',
        required: true,
        defaultValue: 5432,
        validation: { min: 1, max: 65535 }
      },
      {
        name: 'database',
        label: '데이터베이스',
        type: 'text',
        required: true,
        placeholder: 'postgres',
        description: '연결할 데이터베이스 이름'
      },
      {
        name: 'username',
        label: '사용자명',
        type: 'text',
        required: true,
        placeholder: 'postgres'
      },
      {
        name: 'password',
        label: '비밀번호',
        type: 'password',
        required: false,
        placeholder: '비밀번호'
      },
      {
        name: 'ssl',
        label: 'SSL 사용',
        type: 'boolean',
        required: false,
        defaultValue: false
      },
      {
        name: 'schema',
        label: '기본 스키마',
        type: 'text',
        required: false,
        placeholder: 'public',
        defaultValue: 'public'
      }
    ]
  },

  mongodb: {
    type: 'mongodb',
    label: 'MongoDB',
    icon: '🍃',
    defaultPort: 27017,
    description: 'NoSQL 도큐먼트 데이터베이스',
    documentationUrl: 'https://docs.mongodb.com/',
    fields: [
      {
        name: 'connectionString',
        label: '연결 문자열',
        type: 'textarea',
        required: false,
        placeholder: 'mongodb://localhost:27017/mydb',
        description: 'MongoDB 연결 URI (옵션)'
      },
      {
        name: 'host',
        label: '호스트',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        defaultValue: 'localhost'
      },
      {
        name: 'port',
        label: '포트',
        type: 'number',
        required: true,
        defaultValue: 27017,
        validation: { min: 1, max: 65535 }
      },
      {
        name: 'database',
        label: '데이터베이스',
        type: 'text',
        required: true,
        placeholder: 'mydb'
      },
      {
        name: 'username',
        label: '사용자명',
        type: 'text',
        required: false,
        placeholder: '사용자명 (선택)'
      },
      {
        name: 'password',
        label: '비밀번호',
        type: 'password',
        required: false,
        placeholder: '비밀번호 (선택)'
      },
      {
        name: 'authSource',
        label: '인증 데이터베이스',
        type: 'text',
        required: false,
        placeholder: 'admin',
        defaultValue: 'admin'
      }
    ]
  },

  sqlite: {
    type: 'sqlite',
    label: 'SQLite',
    icon: '🗃️',
    defaultPort: 0,
    description: '파일 기반 경량 데이터베이스',
    documentationUrl: 'https://sqlite.org/docs.html',
    fields: [
      {
        name: 'filePath',
        label: '파일 경로',
        type: 'text',
        required: true,
        placeholder: '/path/to/database.db',
        description: 'SQLite 데이터베이스 파일 경로'
      },
      {
        name: 'mode',
        label: '모드',
        type: 'select',
        required: false,
        defaultValue: 'readwrite',
        options: [
          { value: 'readonly', label: '읽기 전용' },
          { value: 'readwrite', label: '읽기/쓰기' },
          { value: 'readwritecreate', label: '읽기/쓰기/생성' }
        ]
      }
    ]
  },

  redis: {
    type: 'redis',
    label: 'Redis',
    icon: '🔴',
    defaultPort: 6379,
    description: '인메모리 키-값 저장소',
    documentationUrl: 'https://redis.io/documentation',
    fields: [
      {
        name: 'host',
        label: '호스트',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        defaultValue: 'localhost'
      },
      {
        name: 'port',
        label: '포트',
        type: 'number',
        required: true,
        defaultValue: 6379,
        validation: { min: 1, max: 65535 }
      },
      {
        name: 'password',
        label: '비밀번호',
        type: 'password',
        required: false,
        placeholder: '비밀번호 (선택)'
      },
      {
        name: 'database',
        label: '데이터베이스 번호',
        type: 'number',
        required: false,
        defaultValue: 0,
        validation: { min: 0, max: 15 }
      }
    ]
  },

  oracle: {
    type: 'oracle',
    label: 'Oracle',
    icon: '🏛️',
    defaultPort: 1521,
    description: 'Oracle 엔터프라이즈 데이터베이스',
    documentationUrl: 'https://docs.oracle.com/database/',
    fields: [
      {
        name: 'host',
        label: '호스트',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        defaultValue: 'localhost'
      },
      {
        name: 'port',
        label: '포트',
        type: 'number',
        required: true,
        defaultValue: 1521,
        validation: { min: 1, max: 65535 }
      },
      {
        name: 'serviceName',
        label: '서비스 이름',
        type: 'text',
        required: true,
        placeholder: 'ORCL',
        description: 'Oracle 서비스 이름 또는 SID'
      },
      {
        name: 'username',
        label: '사용자명',
        type: 'text',
        required: true,
        placeholder: 'system'
      },
      {
        name: 'password',
        label: '비밀번호',
        type: 'password',
        required: true,
        placeholder: '비밀번호'
      }
    ]
  },

  mssql: {
    type: 'mssql',
    label: 'Microsoft SQL Server',
    icon: '🏢',
    defaultPort: 1433,
    description: 'Microsoft SQL Server',
    documentationUrl: 'https://docs.microsoft.com/sql/',
    fields: [
      {
        name: 'host',
        label: '호스트',
        type: 'text',
        required: true,
        placeholder: 'localhost',
        defaultValue: 'localhost'
      },
      {
        name: 'port',
        label: '포트',
        type: 'number',
        required: true,
        defaultValue: 1433,
        validation: { min: 1, max: 65535 }
      },
      {
        name: 'database',
        label: '데이터베이스',
        type: 'text',
        required: true,
        placeholder: 'master'
      },
      {
        name: 'username',
        label: '사용자명',
        type: 'text',
        required: true,
        placeholder: 'sa'
      },
      {
        name: 'password',
        label: '비밀번호',
        type: 'password',
        required: true,
        placeholder: '비밀번호'
      },
      {
        name: 'trustServerCertificate',
        label: '서버 인증서 신뢰',
        type: 'boolean',
        required: false,
        defaultValue: false
      }
    ]
  },

  // API 연결들
  kosis_api: {
    type: 'kosis_api',
    label: 'KOSIS API',
    icon: '📊',
    defaultPort: 0,
    description: '한국 통계청(KOSIS) 공공데이터 API',
    documentationUrl: 'https://kosis.kr/openapi/',
    fields: [
      {
        name: 'password',
        label: 'API 키',
        type: 'password',
        required: true,
        placeholder: 'KOSIS API 키를 입력하세요',
        description: 'KOSIS OpenAPI 인증키'
      },
      {
        name: 'host',
        label: 'Base URL',
        type: 'text',
        required: false,
        defaultValue: 'https://kosis.kr/openapi',
        placeholder: 'https://kosis.kr/openapi',
        description: 'KOSIS API 베이스 URL (기본값 사용 권장)'
      }
    ]
  },

  external_api: {
    type: 'external_api',
    label: 'External API',
    icon: '🌐',
    defaultPort: 0,
    description: '외부 REST API 연결',
    documentationUrl: '',
    fields: [
      {
        name: 'host',
        label: 'Base URL',
        type: 'text',
        required: true,
        placeholder: 'https://api.example.com',
        description: 'API 베이스 URL'
      },
      {
        name: 'password',
        label: 'API 키',
        type: 'password',
        required: false,
        placeholder: 'API 키 (선택사항)',
        description: 'API 인증키 (필요한 경우)'
      },
      {
        name: 'username',
        label: '사용자명',
        type: 'text',
        required: false,
        placeholder: '사용자명 (선택사항)',
        description: 'Basic Auth 사용자명'
      }
    ]
  }
};

export const getSupportedDatabaseTypes = (): DatabaseType[] => {
  return Object.keys(DATABASE_CONFIGS) as DatabaseType[];
};

export const getDatabaseConfig = (type: DatabaseType): DatabaseConnectionConfig => {
  return DATABASE_CONFIGS[type];
};

export const getDefaultConnection = (type: DatabaseType): Partial<DatabaseConnection> => {
  const config = DATABASE_CONFIGS[type];
  const defaultConnection: Partial<DatabaseConnection> = {
    type,
    port: config.defaultPort || undefined,
  };

  // 기본값 설정
  config.fields.forEach(field => {
    if (field.defaultValue !== undefined) {
      (defaultConnection as any)[field.name] = field.defaultValue;
    }
  });

  return defaultConnection;
}; 