import { Globe, Plus, Wifi, WifiOff } from "lucide-react";
import React from "react";
import { RefreshButton } from "../../ui/refresh-button";
import { ShimmerButton } from "../../ui/shimmer-button";
import type { ProjectListHeaderProps } from "../../../types/componentTypes";

export const ProjectListHeader: React.FC<ProjectListHeaderProps> = ({
  loading,
  loadingBulkSummaries,
  isConnected,
  onRefresh,
  onShowGlobalContext,
  onCreateProject,
}) => {
  return (
    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-2">
      {/* Title section */}
      <div className="flex items-center justify-between sm:justify-start">
        <div className="flex items-center gap-3">
          <span className="font-bold text-base sm:text-lg">Projects</span>
          {/* WebSocket Connection Status - matches TaskListHeader pattern */}
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
        {/* Refresh button on mobile - next to title */}
        <RefreshButton
          onClick={onRefresh}
          loading={loading || loadingBulkSummaries}
          className="sm:hidden"
          size="icon"
          title="Refresh projects and branch summaries"
        />
      </div>

      {/* Action buttons - responsive layout */}
      <div className="flex gap-2 justify-end sm:w-auto">
        {/* Hidden refresh on desktop (shown in different position) */}
        <RefreshButton
          onClick={onRefresh}
          loading={loading || loadingBulkSummaries}
          className="hidden sm:flex lg:hidden"
          size="icon"
          title="Refresh projects and branch summaries"
        />
        <RefreshButton
          onClick={onRefresh}
          loading={loading || loadingBulkSummaries}
          className="hidden lg:flex"
          size="sm"
          title="Refresh projects and branch summaries"
        />

        {/* Global context button */}
        <ShimmerButton
          size="sm"
          variant="outline"
          onClick={() => onShowGlobalContext && onShowGlobalContext()}
          aria-label="View/Edit Global Context"
          title="View and Edit Global Context"
          className="flex-1 sm:flex-initial min-w-0"
        >
          <Globe className="w-4 h-4 lg:mr-2" />
          <span className="hidden lg:inline">Global</span>
        </ShimmerButton>

        {/* New project button */}
        <ShimmerButton
          size="sm"
          variant="default"
          onClick={onCreateProject}
          className="flex-1 sm:flex-initial min-w-0"
          title="Create New Project"
        >
          <Plus className="w-4 h-4 lg:mr-2" />
          <span className="hidden lg:inline">New Project</span>
        </ShimmerButton>
      </div>
    </div>
  );
};