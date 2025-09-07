import * as React from "react";
import { cn } from "../../lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

const buttonVariants = {
  default: "theme-btn-primary",
  outline: "theme-btn-outline",
  secondary: "theme-btn-secondary",
  ghost: "theme-btn-ghost",
  link: "underline-offset-4 hover:underline text-primary"
};

const sizeVariants = {
  default: "h-10 px-4 py-2",
  sm: "h-9 px-3",
  lg: "h-11 px-8",
  icon: "h-10 w-10 p-0 flex items-center justify-center"
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background",
        buttonVariants[variant],
        sizeVariants[size],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button"; 