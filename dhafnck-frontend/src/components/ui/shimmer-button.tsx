'use client'
import React from 'react';
import { cn } from '../../lib/utils';

interface ShimmerButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'default' | 'ghost' | 'outline' | 'secondary' | 'destructive' | 'link';
  size?: 'sm' | 'md' | 'lg' | 'icon' | 'default';
  shimmerColor?: string;
}

export const ShimmerButton: React.FC<ShimmerButtonProps> = ({ 
  children, 
  className = '',
  variant = 'default',
  size = 'default',
  shimmerColor = '#06b6d4',
  ...props 
}) => {
  const customCss = `
    @property --angle {
      syntax: '<angle>';
      initial-value: 0deg;
      inherits: false;
    }

    @keyframes shimmer-spin {
      to {
        --angle: 360deg;
      }
    }
  `;

  const sizeClasses = {
    sm: 'px-3 py-1 text-sm h-8',
    md: 'px-6 py-2 h-10',
    lg: 'px-8 py-3 h-11',
    icon: 'h-9 w-9',
    default: 'px-4 py-2 h-9'
  };

  const variantClasses = {
    default: 'bg-gray-300 dark:bg-black',
    ghost: 'bg-transparent',
    outline: 'bg-transparent border border-gray-300 dark:border-gray-700',
    secondary: 'bg-gray-200 dark:bg-gray-800',
    destructive: 'bg-red-500 dark:bg-red-600',
    link: 'bg-transparent underline-offset-4 hover:underline'
  };

  const innerVariantClasses = {
    default: 'bg-primary text-primary-foreground hover:bg-primary/90',
    ghost: 'bg-transparent hover:bg-accent hover:text-accent-foreground',
    outline: 'bg-background hover:bg-accent hover:text-accent-foreground',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
    destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    link: 'text-primary underline-offset-4 hover:underline'
  };

  return (
    <>
      <style>{customCss}</style>
      <button 
        className={cn(
          "relative inline-flex items-center justify-center p-[1.5px] rounded-full overflow-hidden group transition-all",
          variantClasses[variant],
          className
        )}
        {...props}
      >
        {(variant === 'default' || variant === 'destructive') && (
          <div 
            className="absolute inset-0"
            style={{
              background: `conic-gradient(from var(--angle), transparent 25%, ${shimmerColor}, transparent 50%)`,
              animation: 'shimmer-spin 2.5s linear infinite',
            }}
          />
        )}
        <span className={cn(
          "relative z-10 inline-flex items-center justify-center w-full h-full rounded-full transition-colors duration-300",
          sizeClasses[size],
          innerVariantClasses[variant]
        )}>
          {children}
        </span>
      </button>
    </>
  );
};

export default ShimmerButton;