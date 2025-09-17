'use client'
import React from 'react';
import { cn } from '../../lib/utils';

interface ShimmerButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'default' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  shimmerColor?: string;
}

export default function ShimmerButton({ 
  children, 
  className,
  variant = 'default',
  size = 'md',
  shimmerColor = '#06b6d4',
  ...props 
}: ShimmerButtonProps) {
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
    sm: 'px-3 py-1 text-sm',
    md: 'px-6 py-2',
    lg: 'px-8 py-3',
    icon: 'p-2'
  };

  const variantClasses = {
    default: 'bg-gray-300 dark:bg-black',
    ghost: 'bg-transparent',
    outline: 'bg-transparent border border-gray-300 dark:border-gray-700'
  };

  const innerVariantClasses = {
    default: 'bg-white dark:bg-gray-900 group-hover:bg-gray-100 dark:group-hover:bg-gray-800',
    ghost: 'bg-transparent group-hover:bg-gray-100 dark:group-hover:bg-gray-800',
    outline: 'bg-white dark:bg-gray-900 group-hover:bg-gray-100 dark:group-hover:bg-gray-800'
  };

  return (
    <>
      <style>{customCss}</style>
      <button 
        className={cn(
          "relative inline-flex items-center justify-center p-[1.5px] rounded-full overflow-hidden group",
          variantClasses[variant],
          className
        )}
        {...props}
      >
        {variant === 'default' && (
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
          innerVariantClasses[variant],
          "text-gray-900 dark:text-white"
        )}>
          {children}
        </span>
      </button>
    </>
  );
}