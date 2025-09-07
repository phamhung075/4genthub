'use client'
import React from 'react';
import { cn } from '../../lib/utils';

interface ShimmerBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'default' | 'secondary' | 'destructive' | 'outline';
  shimmerColor?: string;
}

export const ShimmerBadge: React.FC<ShimmerBadgeProps> = ({ 
  children, 
  className = '',
  variant = 'default',
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

  const variantClasses = {
    default: 'bg-gray-300 dark:bg-black',
    secondary: 'bg-gray-200 dark:bg-gray-800',
    destructive: 'bg-red-500 dark:bg-red-600',
    outline: 'bg-transparent border border-gray-300 dark:border-gray-700'
  };

  const innerVariantClasses = {
    default: 'bg-primary text-primary-foreground',
    secondary: 'bg-secondary text-secondary-foreground',
    destructive: 'bg-destructive text-destructive-foreground',
    outline: 'bg-background text-foreground'
  };

  return (
    <>
      <style>{customCss}</style>
      <div 
        className={cn(
          "relative inline-flex items-center p-[1.5px] rounded-full overflow-hidden group",
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
          "relative z-10 inline-flex items-center justify-center px-2.5 py-0.5 text-xs font-semibold rounded-full transition-colors",
          innerVariantClasses[variant]
        )}>
          {children}
        </span>
      </div>
    </>
  );
};

export default ShimmerBadge;