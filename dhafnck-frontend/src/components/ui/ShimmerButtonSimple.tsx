'use client'
import React from 'react';
import { cn } from '../../lib/utils';

interface ShimmerButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'default' | 'ghost' | 'outline' | 'secondary' | 'destructive';
  size?: 'sm' | 'md' | 'lg' | 'icon';
}

export default function ShimmerButtonSimple({ 
  children, 
  className,
  variant = 'default',
  size = 'md',
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
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-8 py-3',
    lg: 'px-10 py-4 text-lg',
    icon: 'p-2'
  };

  const bgClasses = {
    default: 'bg-gray-300 dark:bg-black',
    ghost: 'bg-transparent',
    outline: 'bg-gray-300 dark:bg-black',
    secondary: 'bg-gray-300 dark:bg-black',
    destructive: 'bg-gray-300 dark:bg-black'
  };

  const innerClasses = {
    default: 'bg-white dark:bg-gray-900 group-hover:bg-gray-100 dark:group-hover:bg-gray-800',
    ghost: 'bg-transparent group-hover:bg-gray-100 dark:group-hover:bg-gray-800',
    outline: 'bg-white dark:bg-gray-900 group-hover:bg-gray-100 dark:group-hover:bg-gray-800',
    secondary: 'bg-gray-100 dark:bg-gray-800 group-hover:bg-gray-200 dark:group-hover:bg-gray-700',
    destructive: 'bg-red-50 dark:bg-red-950 group-hover:bg-red-100 dark:group-hover:bg-red-900'
  };

  const textClasses = {
    default: 'text-gray-900 dark:text-white',
    ghost: 'text-gray-900 dark:text-white',
    outline: 'text-gray-900 dark:text-white',
    secondary: 'text-gray-900 dark:text-white',
    destructive: 'text-red-600 dark:text-red-400'
  };

  return (
    <>
      <style>{customCss}</style>
      <button 
        className={cn(
          "relative inline-flex items-center justify-center p-[1.5px] rounded-full overflow-hidden group",
          bgClasses[variant],
          className
        )}
        {...props}
      >
        <div 
          className="absolute inset-0"
          style={{
            background: 'conic-gradient(from var(--angle), transparent 25%, #06b6d4, transparent 50%)',
            animation: 'shimmer-spin 2.5s linear infinite',
          }}
        />
        <span className={cn(
          "relative z-10 inline-flex items-center justify-center w-full h-full rounded-full transition-colors duration-300",
          sizeClasses[size],
          innerClasses[variant],
          textClasses[variant]
        )}>
          {children}
        </span>
      </button>
    </>
  );
}