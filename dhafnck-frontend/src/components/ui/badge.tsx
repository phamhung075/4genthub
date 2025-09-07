import * as React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "destructive" | "outline";
}

const badgeVariants = {
  default: "bg-green-50 text-green-700 dark:bg-green-900 dark:text-green-100 hover:bg-green-100 dark:hover:bg-green-800",
  secondary: "bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700",
  destructive: "bg-red-50 text-red-700 dark:bg-red-900 dark:text-red-100 hover:bg-red-100 dark:hover:bg-red-800",
  outline: "border border-gray-200 dark:border-gray-600 bg-transparent text-gray-600 dark:text-gray-400"
};

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => {
    // Ensure variant is a valid string value
    const safeVariant = (typeof variant === 'string' && variant in badgeVariants) 
      ? variant 
      : "default";
    
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          badgeVariants[safeVariant],
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge"; 