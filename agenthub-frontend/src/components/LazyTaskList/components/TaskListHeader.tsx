import React from 'react';
import { Plus, RefreshCw } from "lucide-react";
import { ShimmerButton } from "../../ui/shimmer-button";
import { SocketStateBadge } from "../../ui/SocketStateBadge";

interface TaskListHeaderProps {
  totalTasks: number;
  /** Rows left after the seat filter; omitted by callers that show every task. */
  visibleTasks?: number;
  /** The selected seat key ('@<seat_key>'), or 'all'. */
  seatFilter?: string;
  seatOptions?: string[];
  onSeatFilterChange?: (assignee: string) => void;
  isConnected: boolean;
  loading: boolean;
  onRefresh: () => Promise<void>;
  onCreateNew: () => void;
}

export const TaskListHeader: React.FC<TaskListHeaderProps> = ({
  totalTasks,
  visibleTasks,
  seatFilter,
  seatOptions,
  onSeatFilterChange,
  isConnected,
  loading,
  onRefresh,
  onCreateNew
}) => {
  // "N of M" only while a filter actually hides rows; an unfiltered board keeps its plain count.
  const countLabel = visibleTasks !== undefined && visibleTasks !== totalTasks
    ? `${visibleTasks} of ${totalTasks}`
    : `${totalTasks}`;

  return (
    <div className="space-y-2">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 mb-2">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">
            Tasks ({countLabel})
          </h2>
          {/* WebSocket Connection Status */}
          <SocketStateBadge isConnected={isConnected} />
        </div>
        <div className="flex gap-2">
          {seatOptions && seatOptions.length > 0 && onSeatFilterChange && (
            <select
              aria-label="Filter by seat"
              className="h-9 rounded-md border border-input-border bg-background px-2 text-sm text-base-primary focus:outline-none focus:ring-1 focus:ring-primary"
              value={seatFilter ?? 'all'}
              onChange={(event) => onSeatFilterChange(event.target.value)}
            >
              <option value="all">All seats</option>
              {seatOptions.map(seat => (
                <option key={seat} value={seat}>{seat}</option>
              ))}
            </select>
          )}
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
