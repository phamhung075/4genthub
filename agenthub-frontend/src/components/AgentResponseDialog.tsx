import React from "react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";

interface AgentResponse {
  agent: string;
  task: string;
  response?: any;
  error?: string;
  timestamp: string;
}

interface AgentResponseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentResponse: AgentResponse | null;
  onClose: () => void;
}

export const AgentResponseDialog: React.FC<AgentResponseDialogProps> = ({
  open,
  onOpenChange,
  agentResponse,
  onClose
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl text-left flex items-center gap-2">
            <Badge variant="default" className="bg-green-600">
              {agentResponse?.agent}
            </Badge>
            Agent Response
          </DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 overflow-y-auto">
          {agentResponse && (
            <div className="space-y-4">
              {/* Task Info */}
              <div className="bg-gray-50 p-3 rounded">
                <p className="text-sm font-medium text-gray-700">Task: {agentResponse.task}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Called at: {new Date(agentResponse.timestamp).toLocaleString()}
                </p>
              </div>

              {/* Response Content */}
              <div>
                {agentResponse.error ? (
                  <div className="bg-red-50 border border-red-200 rounded p-4">
                    <h4 className="text-red-800 font-medium text-sm mb-2">Error:</h4>
                    <pre className="text-red-700 text-sm whitespace-pre-wrap font-mono bg-white p-3 rounded border overflow-x-auto">
                      {agentResponse.error}
                    </pre>
                  </div>
                ) : (
                  <div className="bg-green-50 border border-green-200 rounded p-4">
                    <h4 className="text-green-800 font-medium text-sm mb-2">Agent Response (Raw JSON):</h4>
                    <pre className="text-gray-800 text-sm whitespace-pre-wrap font-mono bg-white p-3 rounded border overflow-x-auto max-h-96">
                      {JSON.stringify(agentResponse.response, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default AgentResponseDialog;