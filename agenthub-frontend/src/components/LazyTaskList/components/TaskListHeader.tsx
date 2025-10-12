import React from 'react';
import { Plus, RefreshCw, Wifi, WifiOff } from "lucide-react";
import { ShimmerButton } from "../../ui/shimmer-button";

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
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
            isConnected
              ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
              : 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400'
          }`}>
            {isConnected ? (
              <>
                <Wifi className="w-3 h-3" />
                <span>Live</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3" />
                <span>Offline</span>
              </>
            )}
          </div>
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