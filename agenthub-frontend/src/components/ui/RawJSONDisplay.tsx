import { CheckCircle, Copy } from 'lucide-react';
import React, { useState } from "react";
import { Button } from './button';

interface RawJSONDisplayProps {
  jsonData: any;
  title?: string;
  fileName?: string;
}

export default function RawJSONDisplay({ jsonData, title = "Global Context Management", fileName = "context.json" }: RawJSONDisplayProps) {
  const [copied, setCopied] = useState(false);

  // Handle null/undefined data
  const safeJsonData = jsonData ?? {};

  const copyToClipboard = () => {
    const jsonString = JSON.stringify(safeJsonData, null, 2);
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLineCount = () => {
    const jsonString = JSON.stringify(safeJsonData, null, 2);
    return jsonString.split('\n').length;
  };

  const formatJSON = (data: any, indent: number = 0, path: string = 'root'): JSX.Element[] => {
    const elements: JSX.Element[] = [];
    const spacing = '  '.repeat(indent);

    if (Array.isArray(data)) {
      elements.push(
        <div key={`${path}-array-open`} className="min-h-6 md:min-h-7 lg:min-h-8 flex items-start">
          <span className="text-zinc-600 dark:text-gray-400 whitespace-pre">{spacing}[</span>
        </div>
      );
      data.forEach((item, index) => {
        const itemPath = `${path}[${index}]`;
        if (typeof item === 'object' && item !== null) {
          elements.push(...formatJSON(item, indent + 1, itemPath));
        } else {
          elements.push(
            <div key={itemPath} className="min-h-6 md:min-h-7 lg:min-h-8 flex items-start">
              <span className="text-zinc-600 dark:text-gray-400 whitespace-pre">{spacing}  </span>
              {typeof item === 'string' ? (
                <span className="text-green-600 dark:text-green-400 break-all">"{item}"</span>
              ) : (
                <span className="text-amber-600 dark:text-amber-400">{String(item)}</span>
              )}
              {index < data.length - 1 && <span className="text-zinc-600 dark:text-gray-400">,</span>}
            </div>
          );
        }
      });
      elements.push(
        <div key={`${path}-array-close`} className="min-h-6 md:min-h-7 lg:min-h-8 flex items-start">
          <span className="text-zinc-600 dark:text-gray-400 whitespace-pre">{spacing}]</span>
        </div>
      );
    } else if (typeof data === 'object' && data !== null) {
      elements.push(
        <div key={`${path}-object-open`} className="min-h-6 md:min-h-7 lg:min-h-8 flex items-start">
          <span className="text-zinc-600 dark:text-gray-400 whitespace-pre">{spacing}{"{"}</span>
        </div>
      );
      const entries = Object.entries(data);
      entries.forEach(([key, value], index) => {
        const keyPath = `${path}.${key}`;
        if (typeof value === 'object' && value !== null) {
          elements.push(
            <div key={`${keyPath}-key`} className="min-h-6 md:min-h-7 lg:min-h-8 flex items-start">
              <span className="text-zinc-600 dark:text-gray-400 whitespace-pre">{spacing}  </span>
              <span className="text-blue-600 dark:text-blue-400">"{key}"</span>
              <span className="text-zinc-600 dark:text-gray-400">: </span>
              <span className="text-zinc-600 dark:text-gray-400">{Array.isArray(value) ? '[' : '{'}</span>
            </div>
          );
          elements.push(...formatJSON(value, indent + 2, keyPath));
          // Add comma after closing bracket/brace if not last item
          if (index < entries.length - 1) {
            const lastIdx = elements.length - 1;
            const lastElement = elements[lastIdx];
            // Create a new element with comma appended
            elements[lastIdx] = (
              <div key={`${lastElement.key}-comma`} className={lastElement.props.className}>
                {lastElement.props.children}
                <span className="text-zinc-600 dark:text-gray-400">,</span>
              </div>
            );
          }
        } else {
          // Handle long strings differently
          if (typeof value === 'string' && value.length > 100) {
            elements.push(
              <div key={keyPath} className="my-1">
                <div className="flex items-start">
                  <span className="text-zinc-600 dark:text-gray-400 whitespace-pre">{spacing}  </span>
                  <span className="text-blue-600 dark:text-blue-400">"{key}"</span>
                  <span className="text-zinc-600 dark:text-gray-400">: </span>
                </div>
                <div className="ml-8 mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded">
                  <pre className="text-green-600 dark:text-green-400 text-xs whitespace-pre-wrap break-words">
                    "{value}"
                  </pre>
                </div>
                {index < entries.length - 1 && <span className="text-zinc-600 dark:text-gray-400 ml-8">,</span>}
              </div>
            );
          } else {
            elements.push(
              <div key={keyPath} className="min-h-6 md:min-h-7 lg:min-h-8 flex items-start flex-wrap">
                <span className="text-zinc-600 dark:text-gray-400 whitespace-pre">{spacing}  </span>
                <span className="text-blue-600 dark:text-blue-400">"{key}"</span>
                <span className="text-zinc-600 dark:text-gray-400">: </span>
                {typeof value === 'string' ? (
                  <span className="text-green-600 dark:text-green-400 break-all">"{value}"</span>
                ) : typeof value === 'boolean' ? (
                  <span className="text-purple-600 dark:text-purple-400">{String(value)}</span>
                ) : value === null ? (
                  <span className="text-gray-600 dark:text-gray-400">null</span>
                ) : (
                  <span className="text-amber-600 dark:text-amber-400">{String(value)}</span>
                )}
                {index < entries.length - 1 && <span className="text-zinc-600 dark:text-gray-400">,</span>}
              </div>
            );
          }
        }
      });
      elements.push(
        <div key={`${path}-object-close`} className="min-h-6 md:min-h-7 lg:min-h-8 flex items-start">
          <span className="text-zinc-600 dark:text-gray-400 whitespace-pre">{spacing}{"}"}</span>
        </div>
      );
    }

    return elements;
  };

  return (
    <div className="w-full font-sans bg-white dark:bg-zinc-950">
      <div className="w-full bg-gradient-to-r from-zinc-100 to-zinc-200 dark:from-[#000000] dark:to-[#0a0d37] border-zinc-300 dark:border-[#1b2c68a0] relative rounded-lg border shadow-lg">
        <div className="flex flex-row">
          <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-blue-500 to-cyan-600"></div>
          <div className="h-[2px] w-full bg-gradient-to-r from-cyan-600 to-transparent"></div>
        </div>

        <div className="px-4 lg:px-8 py-5 flex justify-between items-center bg-zinc-200 dark:bg-[#000000]">
          <div className="flex flex-row space-x-2">
            <div className="h-3 w-3 rounded-full bg-red-500"></div>
            <div className="h-3 w-3 rounded-full bg-orange-400"></div>
            <div className="h-3 w-3 rounded-full bg-green-400"></div>
          </div>
          <div className="text-xs text-zinc-600 dark:text-gray-400 font-mono">
            {fileName}
          </div>
        </div>

        <div className="border-t-[2px] border-zinc-300 dark:border-indigo-900 px-4 lg:px-8 py-4 lg:py-8 relative">
          <div className="absolute -top-24 -left-24 w-56 h-56 bg-blue-600 rounded-full opacity-10 filter blur-3xl"></div>
          <div className="absolute -bottom-24 -right-24 w-56 h-56 bg-cyan-600 rounded-full opacity-10 filter blur-3xl"></div>

          {/* Title and Copy Button */}
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-zinc-800 dark:text-white">{title}</h3>
            <Button
              variant="outline"
              size="sm"
              onClick={copyToClipboard}
              className={copied ? 'bg-green-50 border-green-500 text-green-700' : ''}
            >
              {copied ? (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-2" />
                  Copy JSON
                </>
              )}
            </Button>
          </div>

          <div className="relative flex overflow-x-auto">
            <code className="font-mono text-xs md:text-sm lg:text-base w-full">
              {formatJSON(safeJsonData)}
            </code>
          </div>
        </div>

        <div className="px-4 lg:px-8 pb-4 mt-4 border-t border-zinc-300 dark:border-gray-800 pt-3 text-xs text-zinc-600 dark:text-gray-500 flex justify-between items-center">
          <span>UTF-8</span>
          <span>JSON</span>
          <span>Ln {getLineCount()}, Col 2</span>
        </div>
      </div>
    </div>
  );
}