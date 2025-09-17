import { AlertTriangle, CheckCircle2 } from "lucide-react";
import React, { useEffect, useState } from "react";
import { Alert } from "./ui/alert";
import { Badge } from "./ui/badge";
import { RefreshButton } from "./ui/refresh-button";

interface HealthStatus {
  success: boolean;
  status?: string;
  server_name?: string;
  version?: string;
  error?: string | { code?: any; message?: string; data?: any };
}

const HealthCheck: React.FC = () => {
  const [status, setStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const checkHealth = () => {
    setLoading(true);
    // Call manage_connection tool for health check
    fetch("/mcp", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "manage_connection",
          arguments: {
            action: "health_check",
            include_details: true
          }
        }
      })
    })
      .then((res) => res.json())
      .then((data) => {
        // Extract tool result from MCP wrapper if present
        if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
          try {
            const toolResult = JSON.parse(data.result.content[0].text);
            setStatus(toolResult);
          } catch (e) {
            setStatus({ success: false, error: "Invalid JSON in tool response" });
          }
        } else if (data.error) {
          setStatus({ success: false, error: data.error });
        } else {
          setStatus({ success: false, error: "Unknown response format" });
        }
      })
      .catch((e) => setStatus({ success: false, error: e.message }))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    checkHealth();
  }, []);

  if (loading) return <div className="text-xs text-muted-foreground px-2 py-1">Checking server health...</div>;

  let errorMsg = "Server not healthy";
  if (status && !status.success) {
    if (typeof status.error === "object" && status.error !== null) {
      errorMsg = status.error.message || JSON.stringify(status.error);
    } else if (typeof status.error === "string") {
      errorMsg = status.error;
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between items-center mb-2">
        <h2 className="text-lg font-semibold">Server Health</h2>
        <RefreshButton 
          onClick={checkHealth} 
          loading={loading}
          size="sm"
        />
      </div>
      {status && status.success ? (
        <Alert variant="default" className="flex items-center gap-4 border-green-400 bg-green-50 text-green-900 p-6 dark:bg-green-950 dark:text-green-100 dark:border-green-700">
          <CheckCircle2 className="w-8 h-8 text-green-500" />
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Badge variant="default" className="bg-green-500 text-white">Healthy</Badge>
              <span className="font-semibold">{status.status}</span>
            </div>
            <div className="flex flex-wrap gap-4 mt-2 text-sm">
              <div><span className="font-semibold">Server:</span> {status.server_name}</div>
              <div><span className="font-semibold">Version:</span> {status.version}</div>
            </div>
          </div>
        </Alert>
      ) : (
        <Alert variant="destructive" className="flex items-center gap-4 p-6 dark:bg-red-950 dark:text-red-100 dark:border-red-700">
          <AlertTriangle className="w-8 h-8 text-destructive" />
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Badge variant="destructive">Error</Badge>
              <span className="font-semibold">{errorMsg}</span>
            </div>
          </div>
        </Alert>
      )}
    </div>
  );
};

export default HealthCheck; 