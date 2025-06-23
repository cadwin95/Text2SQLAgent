'use client';

import React, { useState } from 'react';
// 간단한 아이콘 문자 사용 (Heroicons 의존성 제거)

interface TopBarProps {
  onToggleDBExplorer?: () => void;
  onToggleAIPanel?: () => void;
  onToggleResultPanel?: () => void;
  onOpenConnectionManager?: () => void;
  showDBExplorer?: boolean;
  showAIPanel?: boolean;
  showResultPanel?: boolean;
  currentConnection?: string;
}

export default function TopBar({ 
  onToggleDBExplorer,
  onToggleAIPanel, 
  onToggleResultPanel,
  onOpenConnectionManager,
  showDBExplorer = true,
  showAIPanel = true, 
  showResultPanel = true,
  currentConnection
}: TopBarProps) {
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  const menuItems = [
    {
      name: 'File',
      items: [
        { label: 'New Query', shortcut: 'Ctrl+N' },
        { label: 'Open File', shortcut: 'Ctrl+O' },
        { label: 'Save', shortcut: 'Ctrl+S' },
        { label: 'Save As', shortcut: 'Ctrl+Shift+S' },
        '---',
        { label: 'Recent Files', shortcut: '' }
      ]
    },
    {
      name: 'Edit',
      items: [
        { label: 'Undo', shortcut: 'Ctrl+Z' },
        { label: 'Redo', shortcut: 'Ctrl+Y' },
        '---',
        { label: 'Cut', shortcut: 'Ctrl+X' },
        { label: 'Copy', shortcut: 'Ctrl+C' },
        { label: 'Paste', shortcut: 'Ctrl+V' },
        '---',
        { label: 'Find', shortcut: 'Ctrl+F' },
        { label: 'Replace', shortcut: 'Ctrl+H' }
      ]
    },
    {
      name: 'Database',
      items: [
        { label: 'Connection Manager', shortcut: 'Ctrl+Shift+C' },
        { label: 'New Connection', shortcut: 'Ctrl+N' },
        '---',
        { label: 'Refresh Schema', shortcut: 'F5' },
        { label: 'Export Data', shortcut: '' },
        { label: 'Import Data', shortcut: '' }
      ]
    },
    {
      name: 'Query',
      items: [
        { label: 'Execute', shortcut: 'F5' },
        { label: 'Execute Selection', shortcut: 'Ctrl+Enter' },
        '---',
        { label: 'Explain Plan', shortcut: 'Ctrl+E' },
        { label: 'Format SQL', shortcut: 'Ctrl+Shift+F' }
      ]
    },
    {
      name: 'View',
      items: [
        { label: 'Toggle DB Explorer', shortcut: 'Ctrl+0' },
        { label: 'Toggle AI Panel', shortcut: 'Ctrl+1' },
        { label: 'Toggle Result Panel', shortcut: 'Ctrl+2' },
        '---',
        { label: 'Zoom In', shortcut: 'Ctrl++' },
        { label: 'Zoom Out', shortcut: 'Ctrl+-' }
      ]
    },
    {
      name: 'Help',
      items: [
        { label: 'Documentation', shortcut: 'F1' },
        { label: 'Keyboard Shortcuts', shortcut: 'Ctrl+K' },
        '---',
        { label: 'About', shortcut: '' }
      ]
    }
  ];

  const handleMenuAction = (item: any) => {
    setOpenMenu(null);
    
    const label = typeof item === 'string' ? item : item.label;
    
    switch (label) {
      case 'Connection Manager':
        onOpenConnectionManager?.();
        break;
      case 'New Connection':
        onOpenConnectionManager?.();
        break;
      case 'Toggle DB Explorer':
        onToggleDBExplorer?.();
        break;
      case 'Toggle AI Panel':
        onToggleAIPanel?.();
        break;
      case 'Toggle Result Panel':
        onToggleResultPanel?.();
        break;
      default:
        console.log(`Menu action: ${label}`);
    }
  };

  const renderMenuItem = (item: any, index: number) => {
    if (item === '---') {
      return <div key={index} className="border-t border-gray-600 my-1" />;
    }

    const label = typeof item === 'string' ? item : item.label;
    const shortcut = typeof item === 'object' ? item.shortcut : '';

    return (
      <button
        key={index}
        className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-700 transition-colors group"
        onClick={() => handleMenuAction(item)}
      >
        <span>{label}</span>
        {shortcut && (
          <span className="text-xs text-gray-500 group-hover:text-gray-400">
            {shortcut}
          </span>
        )}
      </button>
    );
  };

  return (
    <div className="h-12 bg-gray-800 border-b border-gray-700 flex items-center px-4">
      {/* Logo and Title */}
      <div className="flex items-center space-x-3 mr-8">
        <span className="text-blue-400 text-xl">🗃️</span>
        <span className="font-semibold text-white">SQL IDE</span>
        <span className="text-xs text-gray-400 bg-gray-700 px-2 py-1 rounded">
          v1.0
        </span>
      </div>

      {/* Menu Items */}
      <div className="flex items-center space-x-1">
        {menuItems.map((menu) => (
          <div key={menu.name} className="relative">
            <button
              className={`px-3 py-2 text-sm rounded hover:bg-gray-700 transition-colors ${
                openMenu === menu.name ? 'bg-gray-700' : ''
              }`}
              onClick={() => setOpenMenu(openMenu === menu.name ? null : menu.name)}
            >
              {menu.name}
            </button>
            
            {/* Dropdown Menu */}
            {openMenu === menu.name && (
              <div className="absolute top-full left-0 mt-1 w-56 bg-gray-800 border border-gray-600 rounded-md shadow-lg z-50">
                {menu.items.map((item, index) => renderMenuItem(item, index))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Connection Status */}
      <div className="flex items-center space-x-4 ml-auto mr-4">
        {currentConnection ? (
          <div className="flex items-center space-x-2 px-3 py-1 bg-green-900/30 border border-green-600 rounded-md">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-sm text-green-300">{currentConnection}</span>
            <button
              onClick={onOpenConnectionManager}
              className="text-xs text-green-400 hover:text-green-300 ml-2"
              title="연결 관리"
            >
              ⚙️
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenConnectionManager}
            className="flex items-center space-x-2 px-3 py-1 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded-md transition-colors"
            title="데이터베이스 연결"
          >
            <div className="w-2 h-2 bg-red-400 rounded-full"></div>
            <span className="text-sm text-gray-300">연결 없음</span>
            <span className="text-xs">🔌</span>
          </button>
        )}
      </div>

      {/* Toolbar Buttons */}
      <div className="flex items-center space-x-2">
        <button
          className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors"
          title="New Query (Ctrl+N)"
        >
          <span className="text-lg">📄</span>
        </button>
        
        <button
          className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors"
          title="Save (Ctrl+S)"
        >
          <span className="text-lg">💾</span>
        </button>
        
        <div className="w-px h-6 bg-gray-600 mx-2" />
        
        <button
          className="p-2 text-green-400 hover:text-green-300 hover:bg-gray-700 rounded transition-colors"
          title="Execute Query (F5)"
        >
          <span className="text-lg">▶️</span>
        </button>
        
        <div className="w-px h-6 bg-gray-600 mx-2" />

        {/* Panel Toggle Buttons */}
        <button
          className={`p-2 rounded transition-colors ${
            showDBExplorer 
              ? 'text-blue-400 bg-gray-700 hover:bg-gray-600' 
              : 'text-gray-500 hover:text-gray-300 hover:bg-gray-700'
          }`}
          onClick={onToggleDBExplorer}
          title="Toggle DB Explorer (Ctrl+0)"
        >
          <span className="text-lg">📂</span>
        </button>

        <button
          className={`p-2 rounded transition-colors ${
            showAIPanel 
              ? 'text-blue-400 bg-gray-700 hover:bg-gray-600' 
              : 'text-gray-500 hover:text-gray-300 hover:bg-gray-700'
          }`}
          onClick={onToggleAIPanel}
          title="Toggle AI Panel (Ctrl+1)"
        >
          <span className="text-lg">🤖</span>
        </button>

        <button
          className={`p-2 rounded transition-colors ${
            showResultPanel 
              ? 'text-blue-400 bg-gray-700 hover:bg-gray-600' 
              : 'text-gray-500 hover:text-gray-300 hover:bg-gray-700'
          }`}
          onClick={onToggleResultPanel}
          title="Toggle Result Panel (Ctrl+2)"
        >
          <span className="text-lg">📊</span>
        </button>
        
        <div className="w-px h-6 bg-gray-600 mx-2" />
        
        <button
          onClick={onOpenConnectionManager}
          className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors"
          title="Connection Manager (Ctrl+Shift+C)"
        >
          <span className="text-lg">🔌</span>
        </button>
      </div>

      {/* Click outside to close menu */}
      {openMenu && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setOpenMenu(null)}
        />
      )}
    </div>
  );
} 