import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, Pencil, Trash2, Users } from 'lucide-react';
import { ShimmerButton } from '../../ui/shimmer-button';
import { TaskRowActionsProps } from '../../../types/taskTypes';

export const TaskRowActions: React.FC<TaskRowActionsProps> = ({
  taskId,
  projectId,
  taskTreeId,
  onOpenDialog,
  variant = 'desktop'
}) => {
  const navigate = useNavigate();

  const handleView = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/dashboard/project/${projectId}/branch/${taskTreeId}/task/${taskId}`);
  };

  const handleAssign = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpenDialog('assign', taskId);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpenDialog('edit', taskId);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpenDialog('delete', taskId);
  };

  const buttonClassName = variant === 'mobile' ? 'h-8 w-8' : 'h-8 w-8';
  const assignButtonClassName = variant === 'mobile'
    ? 'h-8 w-8 hidden xs:inline-flex'
    : 'h-8 w-8 hidden sm:inline-flex';

  return (
    <div className="flex gap-1">
      <ShimmerButton
        variant="ghost"
        size="icon"
        onClick={handleView}
        title="View details"
        className={buttonClassName}
      >
        <Eye className="w-4 h-4" />
      </ShimmerButton>

      <ShimmerButton
        variant="ghost"
        size="icon"
        onClick={handleAssign}
        title="Assign agents"
        className={assignButtonClassName}
      >
        <Users className="w-4 h-4" />
      </ShimmerButton>

      <ShimmerButton
        variant="ghost"
        size="icon"
        onClick={handleEdit}
        title="Edit task"
        className={buttonClassName}
      >
        <Pencil className="w-4 h-4" />
      </ShimmerButton>

      <ShimmerButton
        variant="ghost"
        size="icon"
        onClick={handleDelete}
        title="Delete task"
        className={buttonClassName}
      >
        <Trash2 className="w-4 h-4" />
      </ShimmerButton>
    </div>
  );
};