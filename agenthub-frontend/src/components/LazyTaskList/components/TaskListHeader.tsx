import React from 'react';
import { Plus, RefreshCw } from "lucide-react";
import { ShimmerButton } from "../../ui/shimmer-button";
import { SocketStateBadge } from "../../ui/SocketStateBadge";

interface TaskListHeaderProps {
  totalTasks: number;
  isConnected: boolean;
  loading: boolean;
  onRefresh: () => Promise<void>;
  onCreateNew: () => void;
}

export const TaskListHeader: React.FC<TaskListHeaderProps> = ({
  totalTasks,
  isConnected,
  loading,
  onRefresh,
  onCreateNew
}) => {
  return (
    <div className="space-y-2">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 mb-2">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">
            Tasks ({totalTasks})
          </h2>
          {/* WebSocket Connection Status */}
          <SocketStateBadge isConnected={isConnected} />
        </div>
        <div className="flex gap-2">
          <ShimmerButton
            onClick={onRefresh}
            size="sm"
            variant="outline"
            disabled={loading}
            className="flex items-center gap-1"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </ShimmerButton>
          <ShimmerButton
            onClick={onCreateNew}
            size="sm"
            variant="default"
            className="flex items-center gap-1"
          >
            <Plus className="w-4 h-4" />
            New Task
          </ShimmerButton>
        </div>
      </div>
    </div>
  );
};
