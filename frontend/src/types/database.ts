export type DatabaseType = 'mysql' | 'postgresql' | 'mongodb' | 'sqlite' | 'redis' | 'oracle' | 'mssql' | 'kosis_api' | 'external_api';

export interface DatabaseConnection {
  id: string;
  name: string;
  type: DatabaseType;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  ssl?: boolean;
  connectionString?: string;
  options?: Record<string, any>;
  isActive?: boolean;
  lastConnected?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface DatabaseConnectionConfig {
  type: DatabaseType;
  label: string;
  icon: string;
  defaultPort: number;
  fields: ConnectionField[];
  description: string;
  documentationUrl?: string;
}

export interface ConnectionField {
  name: string;
  label: string;
  type: 'text' | 'number' | 'password' | 'boolean' | 'select' | 'textarea';
  required: boolean;
  placeholder?: string;
  defaultValue?: any;
  options?: Array<{ value: any; label: string }>;
  description?: string;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    message?: string;
  };
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  details?: {
    latency?: number;
    version?: string;
    schemas?: string[];
    tables?: string[];
  };
  error?: string;
}

export interface DatabaseSchema {
  name: string;
  tables: DatabaseTable[];
  views?: DatabaseView[];
  procedures?: DatabaseProcedure[];
}

export interface DatabaseTable {
  name: string;
  schema?: string;
  type: 'table' | 'view';
  columns: DatabaseColumn[];
  rowCount?: number;
  size?: string;
  engine?: string;
  collation?: string;
  comment?: string;
  indexes?: DatabaseIndex[];
  foreignKeys?: DatabaseForeignKey[];
}

export interface DatabaseColumn {
  name: string;
  type: string;
  nullable: boolean;
  defaultValue?: any;
  primaryKey: boolean;
  autoIncrement?: boolean;
  unique?: boolean;
  comment?: string;
  length?: number;
  precision?: number;
  scale?: number;
}

export interface DatabaseIndex {
  name: string;
  columns: string[];
  unique: boolean;
  type?: string;
}

export interface DatabaseForeignKey {
  name: string;
  column: string;
  referencedTable: string;
  referencedColumn: string;
  onUpdate?: string;
  onDelete?: string;
}

export interface DatabaseView {
  name: string;
  definition: string;
  columns: DatabaseColumn[];
}

export interface DatabaseProcedure {
  name: string;
  parameters: Array<{
    name: string;
    type: string;
    direction: 'IN' | 'OUT' | 'INOUT';
  }>;
  returnType?: string;
}

// Database Driver Interface for extensibility
export interface DatabaseDriver {
  type: DatabaseType;
  connect(connection: DatabaseConnection): Promise<boolean>;
  disconnect(connectionId: string): Promise<boolean>;
  testConnection(connection: DatabaseConnection): Promise<ConnectionTestResult>;
  getSchema(connectionId: string, includeColumns?: boolean): Promise<DatabaseSchema>;
  executeQuery(connectionId: string, query: string): Promise<any>;
  getTableData(connectionId: string, tableName: string, limit?: number): Promise<any>;
} 