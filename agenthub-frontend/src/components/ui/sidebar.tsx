import * as React from "react";
import { cn } from "../../lib/utils";

export interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {}

export const Sidebar = React.forwardRef<HTMLDivElement, SidebarProps>(
  ({ className, ...props }, ref) => (
    <aside
      ref={ref}
      className={cn(
        "h-screen flex flex-col bg-muted text-muted-foreground shadow-sm", className
      )}
      {...props}
    />
  )
);
Sidebar.displayName = "Sidebar"; 