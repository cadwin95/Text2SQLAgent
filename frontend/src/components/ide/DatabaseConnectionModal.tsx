'use client';

import React, { useState, useEffect } from 'react';
import { DatabaseConnection, DatabaseType, ConnectionField, ConnectionTestResult } from '@/types/database';
import { DATABASE_CONFIGS, getSupportedDatabaseTypes, getDefaultConnection } from '@/utils/database-configs';
import { databaseAPI } from '@/utils/database-api';

interface DatabaseConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (connection: DatabaseConnection) => void;
  editConnection?: DatabaseConnection | null;
}

export default function DatabaseConnectionModal({ 
  isOpen, 
  onClose, 
  onSave, 
  editConnection 
}: DatabaseConnectionModalProps) {
  const [selectedType, setSelectedType] = useState<DatabaseType>('mysql');
  const [connectionData, setConnectionData] = useState<Partial<DatabaseConnection>>({});
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<'basic' | 'advanced' | 'test'>('basic');

  useEffect(() => {
    if (isOpen) {
      if (editConnection) {
        setSelectedType(editConnection.type);
        setConnectionData(editConnection);
      } else {
        resetForm();
      }
      setTestResult(null);
      setErrors({});
      setActiveTab('basic');
    }
  }, [isOpen, editConnection]);

  const resetForm = () => {
    const defaultConnection = getDefaultConnection(selectedType);
    setConnectionData({
      ...defaultConnection,
      name: `${DATABASE_CONFIGS[selectedType].label} Connection`,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      updatedAt: new Date()
    });
  };

  const handleTypeChange = (type: DatabaseType) => {
    setSelectedType(type);
    const defaultConnection = getDefaultConnection(type);
    setConnectionData({
      ...defaultConnection,
      name: `${DATABASE_CONFIGS[type].label} Connection`,
      id: connectionData.id || crypto.randomUUID(),
      createdAt: connectionData.createdAt || new Date(),
      updatedAt: new Date()
    });
    setTestResult(null);
    setErrors({});
  };

  const handleFieldChange = (fieldName: string, value: any) => {
    setConnectionData(prev => ({
      ...prev,
      [fieldName]: value,
      updatedAt: new Date()
    }));
    
    // 에러 클리어
    if (errors[fieldName]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[fieldName];
        return newErrors;
      });
    }
  };

  const validateForm = (): boolean => {
    const config = DATABASE_CONFIGS[selectedType];
    const newErrors: Record<string, string> = {};

    // 연결 이름 검증
    if (!connectionData.name?.trim()) {
      newErrors.name = '연결 이름은 필수입니다';
    }

    // 필드별 검증
    config.fields.forEach(field => {
      const value = (connectionData as any)[field.name];
      
      if (field.required && (!value || value === '')) {
        newErrors[field.name] = `${field.label}은(는) 필수입니다`;
        return;
      }

      if (value && field.validation) {
        const validation = field.validation;
        
        if (field.type === 'number') {
          const numValue = Number(value);
          if (validation.min !== undefined && numValue < validation.min) {
            newErrors[field.name] = `최소값은 ${validation.min}입니다`;
          }
          if (validation.max !== undefined && numValue > validation.max) {
            newErrors[field.name] = `최대값은 ${validation.max}입니다`;
          }
        }
        
        if (field.type === 'text' && validation.pattern) {
          const regex = new RegExp(validation.pattern);
          if (!regex.test(value)) {
            newErrors[field.name] = validation.message || '유효하지 않은 형식입니다';
          }
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleTestConnection = async () => {
    if (!validateForm()) return;
    
    setIsTestingConnection(true);
    setTestResult(null);

    try {
      const result = await databaseAPI.testConnection(connectionData);
      setTestResult(result);
      setActiveTab('test');
    } catch (error) {
      setTestResult({
        success: false,
        message: '연결 테스트 중 오류가 발생했습니다. 백엔드 서버 연결을 확인해주세요.',
        error: error instanceof Error ? error.message : String(error)
      });
      setActiveTab('test');
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleSave = () => {
    if (!validateForm()) return;
    
    const finalConnection: DatabaseConnection = {
      id: connectionData.id || crypto.randomUUID(),
      name: connectionData.name!,
      type: selectedType,
      createdAt: connectionData.createdAt || new Date(),
      updatedAt: new Date(),
      isActive: false,
      ...connectionData
    } as DatabaseConnection;

    onSave(finalConnection);
    onClose();
  };

  const renderField = (field: ConnectionField) => {
    const value = (connectionData as any)[field.name] || '';
    const error = errors[field.name];

    const fieldId = `field-${field.name}`;

    return (
      <div key={field.name} className="mb-4">
        <label htmlFor={fieldId} className="block text-sm font-medium text-gray-300 mb-1">
          {field.label}
          {field.required && <span className="text-red-400 ml-1">*</span>}
        </label>
        
        {field.type === 'text' && (
          <input
            id={fieldId}
            type="text"
            className={`w-full px-3 py-2 bg-gray-700 border rounded-md text-white focus:outline-none focus:ring-2 ${
              error ? 'border-red-500 focus:ring-red-500' : 'border-gray-600 focus:ring-blue-500'
            }`}
            value={value}
            placeholder={field.placeholder}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
          />
        )}

        {field.type === 'number' && (
          <input
            id={fieldId}
            type="number"
            className={`w-full px-3 py-2 bg-gray-700 border rounded-md text-white focus:outline-none focus:ring-2 ${
              error ? 'border-red-500 focus:ring-red-500' : 'border-gray-600 focus:ring-blue-500'
            }`}
            value={value}
            placeholder={field.placeholder}
            min={field.validation?.min}
            max={field.validation?.max}
            onChange={(e) => handleFieldChange(field.name, Number(e.target.value))}
          />
        )}

        {field.type === 'password' && (
          <input
            id={fieldId}
            type="password"
            className={`w-full px-3 py-2 bg-gray-700 border rounded-md text-white focus:outline-none focus:ring-2 ${
              error ? 'border-red-500 focus:ring-red-500' : 'border-gray-600 focus:ring-blue-500'
            }`}
            value={value}
            placeholder={field.placeholder}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
          />
        )}

        {field.type === 'boolean' && (
          <label className="flex items-center">
            <input
              id={fieldId}
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) => handleFieldChange(field.name, e.target.checked)}
              className="mr-2 w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-300">{field.description || field.label}</span>
          </label>
        )}

        {field.type === 'select' && field.options && (
          <select
            id={fieldId}
            className={`w-full px-3 py-2 bg-gray-700 border rounded-md text-white focus:outline-none focus:ring-2 ${
              error ? 'border-red-500 focus:ring-red-500' : 'border-gray-600 focus:ring-blue-500'
            }`}
            value={value}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
          >
            {field.options.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        )}

        {field.type === 'textarea' && (
          <textarea
            id={fieldId}
            rows={3}
            className={`w-full px-3 py-2 bg-gray-700 border rounded-md text-white focus:outline-none focus:ring-2 resize-none ${
              error ? 'border-red-500 focus:ring-red-500' : 'border-gray-600 focus:ring-blue-500'
            }`}
            value={value}
            placeholder={field.placeholder}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
          />
        )}

        {field.description && field.type !== 'boolean' && (
          <p className="text-xs text-gray-500 mt-1">{field.description}</p>
        )}

        {error && (
          <p className="text-xs text-red-400 mt-1">{error}</p>
        )}
      </div>
    );
  };

  if (!isOpen) return null;

  const config = DATABASE_CONFIGS[selectedType];
  const supportedTypes = getSupportedDatabaseTypes();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">
            {editConnection ? '데이터베이스 연결 수정' : '새 데이터베이스 연결'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="flex h-[600px]">
          {/* Database Type Selector */}
          <div className="w-64 bg-gray-850 border-r border-gray-700 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-300 mb-3">데이터베이스 타입</h3>
              <div className="space-y-1">
                {supportedTypes.map(type => {
                  const typeConfig = DATABASE_CONFIGS[type];
                  return (
                    <button
                      key={type}
                      className={`w-full flex items-center p-3 rounded-md transition-colors text-left ${
                        selectedType === type
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-300 hover:bg-gray-700'
                      }`}
                      onClick={() => handleTypeChange(type)}
                    >
                      <span className="text-lg mr-3">{typeConfig.icon}</span>
                      <div>
                        <div className="font-medium">{typeConfig.label}</div>
                        <div className="text-xs opacity-75">{typeConfig.description}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Configuration Form */}
          <div className="flex-1 flex flex-col">
            {/* Tabs */}
            <div className="flex border-b border-gray-700">
              <button
                className={`px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === 'basic'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
                onClick={() => setActiveTab('basic')}
              >
                기본 설정
              </button>
              <button
                className={`px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === 'test'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
                onClick={() => setActiveTab('test')}
              >
                연결 테스트
              </button>
            </div>

            {/* Form Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {activeTab === 'basic' && (
                <div>
                  {/* Connection Name */}
                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      연결 이름 <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      className={`w-full px-3 py-2 bg-gray-700 border rounded-md text-white focus:outline-none focus:ring-2 ${
                        errors.name ? 'border-red-500 focus:ring-red-500' : 'border-gray-600 focus:ring-blue-500'
                      }`}
                      value={connectionData.name || ''}
                      placeholder="연결 이름을 입력하세요"
                      onChange={(e) => handleFieldChange('name', e.target.value)}
                    />
                    {errors.name && (
                      <p className="text-xs text-red-400 mt-1">{errors.name}</p>
                    )}
                  </div>

                  {/* Database-specific fields */}
                  <div className="grid grid-cols-2 gap-4">
                    {config.fields.map(renderField)}
                  </div>

                  {/* Documentation Link */}
                  {config.documentationUrl && (
                    <div className="mt-6 p-4 bg-gray-750 rounded-md">
                      <p className="text-sm text-gray-300">
                        📚 자세한 설정 방법은{' '}
                        <a
                          href={config.documentationUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 underline"
                        >
                          {config.label} 공식 문서
                        </a>
                        를 참고하세요.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'test' && (
                <div>
                  <div className="mb-6">
                    <h3 className="text-lg font-medium text-white mb-2">연결 테스트</h3>
                    <p className="text-gray-400 text-sm">
                      데이터베이스 연결을 테스트하여 설정이 올바른지 확인합니다.
                    </p>
                  </div>

                  <button
                    onClick={handleTestConnection}
                    disabled={isTestingConnection}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-md transition-colors mb-4"
                  >
                    {isTestingConnection ? '테스트 중...' : '연결 테스트'}
                  </button>

                  {testResult && (
                    <div className={`p-4 rounded-md ${
                      testResult.success ? 'bg-green-900 border border-green-700' : 'bg-red-900 border border-red-700'
                    }`}>
                      <div className="flex items-start">
                        <span className="text-lg mr-2">
                          {testResult.success ? '✅' : '❌'}
                        </span>
                        <div className="flex-1">
                          <h4 className={`font-medium ${testResult.success ? 'text-green-300' : 'text-red-300'}`}>
                            {testResult.success ? '연결 성공' : '연결 실패'}
                          </h4>
                          <p className="text-sm mt-1 text-gray-300">{testResult.message}</p>
                          
                          {testResult.details && (
                            <div className="mt-3 text-sm">
                              {testResult.details.latency && (
                                <p>응답 시간: {testResult.details.latency}ms</p>
                              )}
                              {testResult.details.version && (
                                <p>버전: {testResult.details.version}</p>
                              )}
                              {testResult.details.schemas && (
                                <p>스키마 수: {testResult.details.schemas.length}개</p>
                              )}
                            </div>
                          )}
                          
                          {testResult.error && (
                            <div className="mt-3 p-2 bg-gray-800 rounded text-xs text-gray-300">
                              <pre className="whitespace-pre-wrap">{testResult.error}</pre>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-gray-700 flex justify-end space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleTestConnection}
                disabled={isTestingConnection}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 text-white rounded-md transition-colors"
              >
                {isTestingConnection ? '테스트 중...' : '연결 테스트'}
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
              >
                {editConnection ? '수정' : '저장'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 