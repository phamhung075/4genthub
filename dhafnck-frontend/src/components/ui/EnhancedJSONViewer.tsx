import { ChevronDown, ChevronRight } from 'lucide-react';
import React, { useEffect, useState } from 'react';

interface EnhancedJSONViewerProps {
  data: any;
  defaultExpanded?: boolean;
  maxHeight?: string;
  viewerId?: string;
}

export const EnhancedJSONViewer: React.FC<EnhancedJSONViewerProps> = ({ 
  data, 
  defaultExpanded = false,
  maxHeight = 'max-h-96',
  viewerId = 'default'
}) => {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(
    defaultExpanded ? new Set(['root']) : new Set()
  );

  // Listen for expand/collapse all events
  useEffect(() => {
    const handleExpandAll = (event: CustomEvent) => {
      if (event.detail.viewerId === viewerId || event.detail.viewerId === 'all') {
        // Expand all paths
        const allPaths = new Set<string>();
        const collectPaths = (obj: any, path: string = 'root') => {
          allPaths.add(path);
          if (obj && typeof obj === 'object') {
            if (Array.isArray(obj)) {
              obj.forEach((_, index) => {
                collectPaths(obj[index], `${path}[${index}]`);
              });
            } else {
              Object.keys(obj).forEach(key => {
                collectPaths(obj[key], path ? `${path}.${key}` : key);
              });
            }
          }
        };
        collectPaths(data);
        setExpandedPaths(allPaths);
      }
    };

    const handleCollapseAll = (event: CustomEvent) => {
      if (event.detail.viewerId === viewerId || event.detail.viewerId === 'all') {
        setExpandedPaths(new Set());
      }
    };

    window.addEventListener('json-expand-all' as any, handleExpandAll as any);
    window.addEventListener('json-collapse-all' as any, handleCollapseAll as any);

    return () => {
      window.removeEventListener('json-expand-all' as any, handleExpandAll as any);
      window.removeEventListener('json-collapse-all' as any, handleCollapseAll as any);
    };
  }, [data, viewerId]);

  const togglePath = (path: string) => {
    setExpandedPaths(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const renderValue = (value: any, path: string = '', depth: number = 0): JSX.Element => {
    // Handle null/undefined
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">null</span>;
    }

    // Handle primitives
    if (typeof value === 'string') {
      // Check for special string patterns
      if (value.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)) {
        return <span className="text-purple-600 dark:text-purple-400 font-mono text-xs">"{value}"</span>;
      }
      if (value.match(/^\d{4}-\d{2}-\d{2}/) || value.includes('T')) {
        try {
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            return <span className="text-blue-600 dark:text-blue-400">"{value}"</span>;
          }
        } catch {}
      }
      return <span className="text-emerald-600 dark:text-emerald-400">"{value}"</span>;
    }

    if (typeof value === 'number') {
      return <span className="text-orange-600 dark:text-orange-400 font-semibold">{value}</span>;
    }

    if (typeof value === 'boolean') {
      return (
        <span className={`font-semibold ${value ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
          {String(value)}
        </span>
      );
    }

    // Handle arrays
    if (Array.isArray(value)) {
      const isExpanded = expandedPaths.has(path);
      const isEmpty = value.length === 0;

      if (isEmpty) {
        return <span className="text-gray-500">[]</span>;
      }

      return (
        <span>
          <button
            onClick={() => togglePath(path)}
            className="inline-flex items-center gap-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded px-1 py-0.5"
          >
            {isExpanded ? 
              <ChevronDown className="w-3 h-3 text-gray-500" /> : 
              <ChevronRight className="w-3 h-3 text-gray-500" />
            }
            <span className="text-gray-600 dark:text-gray-400 text-xs">
              [{value.length} items]
            </span>
          </button>
          {isExpanded && (
            <div className="ml-4 mt-1">
              {value.map((item, index) => (
                <div key={index} className="flex items-start py-0.5">
                  <span className="text-gray-500 text-xs mr-2 min-w-[20px]">{index}:</span>
                  {renderValue(item, `${path}[${index}]`, depth + 1)}
                </div>
              ))}
            </div>
          )}
        </span>
      );
    }

    // Handle objects
    if (typeof value === 'object') {
      const entries = Object.entries(value);
      const isExpanded = expandedPaths.has(path);
      const isEmpty = entries.length === 0;

      if (isEmpty) {
        return <span className="text-gray-500">{'{}'}</span>;
      }

      // Color coding for different depth levels
      const depthColors = [
        'border-blue-500',
        'border-green-500',
        'border-purple-500',
        'border-orange-500',
        'border-pink-500'
      ];
      const borderColor = depthColors[depth % depthColors.length];

      return (
        <div className={depth === 0 ? '' : 'inline-block w-full'}>
          <button
            onClick={() => togglePath(path)}
            className="inline-flex items-center gap-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded px-1 py-0.5"
          >
            {isExpanded ? 
              <ChevronDown className="w-3 h-3 text-gray-500" /> : 
              <ChevronRight className="w-3 h-3 text-gray-500" />
            }
            <span className="text-gray-600 dark:text-gray-400 text-xs">
              {'{'}
              {!isExpanded && `... ${entries.length} properties`}
              {!isExpanded && '}'}
            </span>
          </button>
          {isExpanded && (
            <div className={`ml-4 mt-1 ${depth > 0 ? `border-l-2 ${borderColor} pl-3` : ''}`}>
              {entries.map(([key, val], index) => {
                const currentPath = path ? `${path}.${key}` : key;
                const isLast = index === entries.length - 1;
                
                // Special formatting for certain keys
                let keyColor = 'text-blue-700 dark:text-blue-300';
                if (key.includes('id') || key.includes('_id')) {
                  keyColor = 'text-purple-700 dark:text-purple-300';
                } else if (key.includes('date') || key.includes('_at')) {
                  keyColor = 'text-cyan-700 dark:text-cyan-300';
                } else if (key.includes('status') || key.includes('state')) {
                  keyColor = 'text-green-700 dark:text-green-300';
                } else if (key.includes('error') || key.includes('failed')) {
                  keyColor = 'text-red-700 dark:text-red-300';
                }

                return (
                  <div key={key} className={`flex items-start py-1 ${!isLast ? 'border-b border-gray-100 dark:border-gray-800' : ''}`}>
                    <span className={`${keyColor} font-medium text-sm mr-2`}>
                      {key}:
                    </span>
                    <div className="flex-1">
                      {renderValue(val, currentPath, depth + 1)}
                    </div>
                  </div>
                );
              })}
              {isExpanded && <span className="text-gray-600 dark:text-gray-400 text-xs">{'}'}</span>}
            </div>
          )}
        </div>
      );
    }

    return <span className="text-gray-700 dark:text-gray-300">{String(value)}</span>;
  };

  return (
    <div className={`${maxHeight} overflow-y-auto overflow-x-auto bg-gray-50 dark:bg-gray-900 rounded-lg p-4`}>
      <div className="font-mono text-sm">
        {renderValue(data, 'root')}
      </div>
    </div>
  );
};

export default EnhancedJSONViewer;