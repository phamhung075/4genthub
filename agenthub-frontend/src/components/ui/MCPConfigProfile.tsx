
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
    let lines = 9; // Base structure lines (without Authorization)
    if (showToken && configData.token) {
      // Authorization takes 3 visual lines when token is shown
      lines += 3;
    }
    return lines;
  };

  // Generate the proper MCP config format
  // Don't show port if it's 80 (default HTTP) or if host is a domain (production)
  const shouldShowPort = configData.port !== 80 && !configData.host.includes('.com');
  const urlBase = shouldShowPort
    ? `http://${configData.host}:${configData.port}`
    : `http://${configData.host}`;

  const mcpConfig = {
    agenthub_http: {
      type: "http",
      url: `${urlBase}/mcp`,
      headers: {
        Accept: "application/json, text/event-stream",
        ...(showToken && configData.token ? { Authorization: `Bearer ${configData.token}` } : {})
      }
    }
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
          [project-folder]/.mcp.json
        </div>
      </div>

      <div className="border-t-[2px] border-zinc-300 dark:border-indigo-900 px-4 lg:px-8 py-4 lg:py-8 relative">
        <div className="absolute -top-24 -left-24 w-56 h-56 bg-blue-600 rounded-full opacity-10 filter blur-3xl"></div>
        <div className="absolute -bottom-24 -right-24 w-56 h-56 bg-cyan-600 rounded-full opacity-10 filter blur-3xl"></div>

        <div className="relative flex overflow-x-auto">
          <code className="font-mono text-xs md:text-sm lg:text-base w-full">
                       
            <div className="h-6 md:h-7 lg:h-8 flex items-center">
              <span className="text-blue-600 dark:text-blue-400">"agenthub_http"</span>
              <span className="text-zinc-600 dark:text-gray-400">: {"{"}</span>
            </div>
            
            <div className="h-6 md:h-7 lg:h-8 flex items-center pl-4">
              <span className="text-blue-600 dark:text-blue-400">"type"</span>
              <span className="text-zinc-600 dark:text-gray-400">: </span>
              <span className="text-green-600 dark:text-green-400">"http"</span>
              <span className="text-zinc-600 dark:text-gray-400">,</span>
            </div>
            
            <div className="h-6 md:h-7 lg:h-8 flex items-center pl-4">
              <span className="text-blue-600 dark:text-blue-400">"url"</span>
              <span className="text-zinc-600 dark:text-gray-400">: </span>
              <span className="text-green-600 dark:text-green-400">
                "http://{configData.host}{shouldShowPort ? `:${configData.port}` : ''}/mcp"
              </span>
              <span className="text-zinc-600 dark:text-gray-400">,</span>
            </div>
            
            <div className="h-6 md:h-7 lg:h-8 flex items-center pl-4">
              <span className="text-blue-600 dark:text-blue-400">"headers"</span>
              <span className="text-zinc-600 dark:text-gray-400">: {"{"}</span>
            </div>
            
            <div className="h-6 md:h-7 lg:h-8 flex items-center pl-8">
              <span className="text-blue-600 dark:text-blue-400">"Accept"</span>
              <span className="text-zinc-600 dark:text-gray-400">: </span>
              <span className="text-green-600 dark:text-green-400">
                "application/json, text/event-stream"
              </span>
              {showToken && configData.token && (
                <span className="text-zinc-600 dark:text-gray-400">,</span>
              )}
            </div>
            
            {showToken && configData.token && (
              <div className="pl-8">
                <div className="flex items-start">
                  <span className="text-blue-600 dark:text-blue-400 whitespace-nowrap">"Authorization"</span>
                  <span className="text-zinc-600 dark:text-gray-400">: </span>
                  <span className="text-green-600 dark:text-green-400">"Bearer </span>
                </div>
                <div className="pl-4 py-1">
                  <span className="text-amber-600 dark:text-amber-400 break-all text-xs font-mono bg-amber-50 dark:bg-amber-950/20 px-2 py-1 rounded block">
                    {configData.token}
                  </span>
                </div>
                <div className="pl-4">
                  <span className="text-green-600 dark:text-green-400">"</span>
                </div>
              </div>
            )}
            
            <div className="h-6 md:h-7 lg:h-8 flex items-center pl-4">
              <span className="text-zinc-600 dark:text-gray-400">{"}"}</span>
            </div>
            
            <div className="h-6 md:h-7 lg:h-8 flex items-center">
              <span className="text-zinc-600 dark:text-gray-400">{"}"}</span>
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
    serverName: "agenthub",
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
    token: "your-jwt-token-here", // SECURITY: Never use real tokens in code - use environment variables
    expiresAt: "2025-12-31T23:59:59Z" // Example expiration date
  };

  return (
    <MCPConfigProfile 
      configData={sampleConfig} 
      showToken={true}
    />
  );
};