import { RefreshCw } from "lucide-react";
import React from "react";
import { Button } from "./button";
import { cn } from "../../lib/utils";

interface RefreshButtonProps {
  onClick: () => void | Promise<void>;
  loading?: boolean;
  className?: string;
  size?: "default" | "sm" | "lg" | "icon";
  variant?: "default" | "outline" | "secondary" | "ghost" | "link";
  title?: string;
}

export const RefreshButton: React.FC<RefreshButtonProps> = ({
  onClick,
  loading = false,
  className,
  size = "icon",
  variant = "ghost",
  title = "Refresh data"
}) => {
  const handleClick = async () => {
    if (!loading) {
      await onClick();
    }
  };

  return (
    <Button
      onClick={handleClick}
      disabled={loading}
      size={size}
      variant={variant}
      className={cn("gap-2", className)}
      title={title}
    >
      <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
      {size !== "icon" && "Refresh"}
    </Button>
  );
};