import * as React from "react";
import { cn } from "../../lib/utils";

export interface EnhancedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "secondary" | "ghost" | "link" | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
  animation?: "none" | "shimmer" | "glow" | "sweep" | "pulse" | "gradient" | "aurora" | "dual-rotating" | "dual-rotating-glow";
}

const buttonVariants = {
  default: "theme-btn-primary",
  outline: "border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300",
  secondary: "bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-700 dark:hover:text-gray-300",
  ghost: "theme-btn-ghost",
  link: "underline-offset-4 hover:underline text-primary",
  destructive: "bg-red-500 text-white hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700"
};

const sizeVariants = {
  default: "h-10 px-4 py-2",
  sm: "h-9 px-3",
  lg: "h-11 px-8",
  icon: "h-10 w-10 p-0 flex items-center justify-center"
};

const animationVariants = {
  none: "",
  shimmer: "shimmer-modern",
  glow: "relative overflow-hidden before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent before:translate-x-[-100%] hover:before:translate-x-[100%] before:transition-transform before:duration-1000 before:ease-in-out",
  sweep: "relative overflow-hidden before:absolute before:inset-0 before:bg-gradient-to-r before:from-blue-500/0 before:via-blue-500/30 before:to-blue-500/0 before:translate-x-[-100%] hover:before:translate-x-[100%] before:transition-transform before:duration-700 before:ease-out",
  pulse: "animate-pulse hover:animate-none transition-all duration-300",
  gradient: "bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 bg-size-200 animate-gradient-x hover:animate-none",
  aurora: "relative overflow-hidden before:absolute before:inset-0 before:bg-gradient-to-r before:from-green-400/20 before:via-blue-500/20 before:via-purple-500/20 before:to-pink-500/20 before:animate-pulse",
  "dual-rotating": "dual-rotating-border",
  "dual-rotating-glow": "dual-rotating-border-glow"
};

export const EnhancedButton = React.forwardRef<HTMLButtonElement, EnhancedButtonProps>(
  ({ className, variant = "default", size = "default", animation = "none", children, ...props }, ref) => {
    const animationClass = animationVariants[animation];

    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background",
          buttonVariants[variant],
          sizeVariants[size],
          animationClass,
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);

EnhancedButton.displayName = "EnhancedButton";