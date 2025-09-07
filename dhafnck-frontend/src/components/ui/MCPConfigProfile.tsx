import React from "react";

interface MCPConfigData {
  serverName: string;
  protocol: string;
  version: string;
  host: string;
  port: number;
  authentication: string;
  capabilities: string[];
  token?: string;
  expiresAt?: string;
}

interface MCPConfigProfileProps {
  configData: MCPConfigData;
  showToken?: boolean;
}

export default function MCPConfigProfile({ configData, showToken = false }: MCPConfigProfileProps) {
  return (
    <div className="flex items-center justify-center p-4 font-sans bg-white dark:bg-zinc-950">
      <MCPConfigCard configData={configData} showToken={showToken} />
    </div>
  );
}

const MCPConfigCard = ({ configData, showToken }: MCPConfigProfileProps) => {
  const getLineCount = () => {
    let lines = 8; // Base structure lines
    lines += configData.capabilities.length; // Capabilities array lines
    if (showToken) lines += 2; // Token lines
    return lines;
  };

  return (
    <div className="max-w-4xl w-full mx-auto bg-gradient-to-r from-zinc-100 to-zinc-200 dark:from-[#000000] dark:to-[#0a0d37] border-zinc-300 dark:border-[#1b2c68a0] relative rounded-lg border shadow-lg">
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
          mcp-config.json
        </div>
      </div>

      <div className="overflow-hidden border-t-[2px] border-zinc-300 dark:border-indigo-900 px-4 lg:px-8 py-4 lg:py-8 relative">
        <div className="absolute -top-24 -left-24 w-56 h-56 bg-blue-600 rounded-full opacity-10 filter blur-3xl"></div>
        <div className="absolute -bottom-24 -right-24 w-56 h-56 bg-cyan-600 rounded-full opacity-10 filter blur-3xl"></div>

        <div className="relative flex">
          <div className="hidden md:flex flex-col items-end pr-4 text-zinc-600 dark:text-gray-500 font-mono text-xs">
            {Array.from({ length: getLineCount() }, (_, i) => (
              <div key={i} className="leading-relaxed select-none opacity-70">
                {i + 1}
              </div>
            ))}
          </div>

          <code className="font-mono text-xs md:text-sm lg:text-base w-full">
            <div>
              <span className="mr-2 text-pink-500 dark:text-pink-400">
                const
              </span>
              <span className="mr-2 text-violet-500 dark:text-violet-400">
                mcpConfig
              </span>
              <span className="mr-2 text-pink-500 dark:text-pink-400">=</span>
              <span className="text-zinc-600 dark:text-gray-400">{"{"}</span>
            </div>
            
            <div className="pl-6">
              <span className="text-zinc-800 dark:text-white">serverName:</span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;</span>
              <span className="text-green-600 dark:text-green-400">
                {configData.serverName}
              </span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;,</span>
            </div>
            
            <div className="pl-6">
              <span className="text-zinc-800 dark:text-white">protocol:</span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;</span>
              <span className="text-green-600 dark:text-green-400">
                {configData.protocol}
              </span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;,</span>
            </div>
            
            <div className="pl-6">
              <span className="text-zinc-800 dark:text-white">version:</span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;</span>
              <span className="text-green-600 dark:text-green-400">
                {configData.version}
              </span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;,</span>
            </div>
            
            <div className="pl-6">
              <span className="text-zinc-800 dark:text-white">endpoint:</span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;</span>
              <span className="text-green-600 dark:text-green-400">
                {configData.host}:{configData.port}
              </span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;,</span>
            </div>
            
            <div className="pl-6">
              <span className="text-zinc-800 dark:text-white">authentication:</span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;</span>
              <span className="text-green-600 dark:text-green-400">
                {configData.authentication}
              </span>
              <span className="text-zinc-600 dark:text-gray-400">&#39;,</span>
            </div>
            
            {showToken && configData.token && (
              <>
                <div className="pl-6">
                  <span className="text-zinc-800 dark:text-white">token:</span>
                  <span className="text-zinc-600 dark:text-gray-400">&#39;</span>
                  <span className="text-amber-600 dark:text-amber-400 break-all">
                    {configData.token.length > 50 
                      ? `${configData.token.substring(0, 50)}...`
                      : configData.token
                    }
                  </span>
                  <span className="text-zinc-600 dark:text-gray-400">&#39;,</span>
                </div>
                {configData.expiresAt && (
                  <div className="pl-6">
                    <span className="text-zinc-800 dark:text-white">expiresAt:</span>
                    <span className="text-zinc-600 dark:text-gray-400">&#39;</span>
                    <span className="text-orange-600 dark:text-orange-400">
                      {configData.expiresAt}
                    </span>
                    <span className="text-zinc-600 dark:text-gray-400">&#39;,</span>
                  </div>
                )}
              </>
            )}
            
            <div className="pl-6">
              <span className="text-zinc-800 dark:text-white">capabilities:</span>
              <span className="text-zinc-600 dark:text-gray-400">{"["}</span>
              <div className="pl-6 flex flex-wrap">
                {configData.capabilities.map((capability, index) => (
                  <span key={capability} className="mr-1">
                    <span className="text-zinc-600 dark:text-gray-400">
                      &#39;
                    </span>
                    <span className="text-cyan-600 dark:text-cyan-400">
                      {capability}
                    </span>
                    <span className="text-zinc-600 dark:text-gray-400">
                      &#39;
                    </span>
                    {index < configData.capabilities.length - 1 && (
                      <span className="text-zinc-600 dark:text-gray-400">
                        ,{" "}
                      </span>
                    )}
                  </span>
                ))}
              </div>
              <span className="text-zinc-600 dark:text-gray-400">{"],"}</span>
            </div>
            
            <div>
              <span className="text-zinc-600 dark:text-gray-400">{"};"}</span>
            </div>
          </code>
        </div>
      </div>

      <div className="px-4 lg:px-8 pb-4 mt-4 border-t border-zinc-300 dark:border-gray-800 pt-3 text-xs text-zinc-600 dark:text-gray-500 flex justify-between items-center">
        <span>UTF-8</span>
        <span>JSON</span>
        <span>Ln {getLineCount()}, Col 2</span>
      </div>
    </div>
  );
};

// Example usage component
export const MCPConfigExample = () => {
  const sampleConfig: MCPConfigData = {
    serverName: "DhafnckMCP",
    protocol: "HTTP",
    version: "1.0.0",
    host: "localhost",
    port: 8000,
    authentication: "JWT Bearer",
    capabilities: [
      "task-management",
      "context-sharing",
      "agent-orchestration",
      "file-operations",
      "real-time-sync",
      "multi-tenant"
    ],
    token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZjBkZTRjNWQtMmE5Ny00MzI0LWFiY2QtOWRhZTM5MjI3NjFlIiwic2NvcGVzIjpbIm9wZW5pZCIsInRhc2s6cmVhZCIsInRhc2s6d3JpdGUiXSwiZXhwIjoxNzI1ODE3NDIxfQ",
    expiresAt: "2025-09-08T18:37:01Z"
  };

  return (
    <MCPConfigProfile 
      configData={sampleConfig} 
      showToken={true}
    />
  );
};