// SubtaskRowBadges - Status and priority badges
// Single responsibility: Display status badges

import React from 'react';
import { HolographicStatusBadge, HolographicPriorityBadge } from "../../ui/holographic-badges";
import { Badge } from "../../ui/badge";
import type { SubtaskRowBadgesProps } from '../../../types/subtaskTypes';

export const SubtaskRowBadges: React.FC<SubtaskRowBadgesProps> = ({
  status,
  priority,
  progressPercentage
}) => {
  return (
    <>
      <HolographicStatusBadge
        status={status as "done" | "todo" | "in_progress" | "blocked" | "review" | "testing" | "cancelled"}
        className="mr-2 text-xs"
      />

      <HolographicPriorityBadge
        priority={priority as "critical" | "low" | "medium" | "high" | "urgent"}
        className="mr-2 text-xs"
      />

      {progressPercentage !== undefined && progressPercentage > 0 && (
        <Badge
          variant="secondary"
          className="mr-2 text-xs bg-surface/50 text-base-primary border-surface-border"
        >
          {progressPercentage}%
        </Badge>
      )}
    </>
  );
};