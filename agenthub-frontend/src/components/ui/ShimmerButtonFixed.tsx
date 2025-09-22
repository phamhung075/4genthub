'use client'
import React, { useEffect, useState } from 'react';
import { cn } from '../../lib/utils';

interface ShimmerButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'default' | 'ghost' | 'outline' | 'secondary' | 'destructive' | 'link';
  size?: 'sm' | 'md' | 'lg' | 'icon' | 'default';
  shimmerColor?: string;
}

export const ShimmerButtonFixed: React.FC<ShimmerButtonProps> = ({
  children,
  className = '',
  variant = 'default',
  size = 'default',
  shimmerColor = '#06b6d4',
  ...props
}) => {
  const [supportsProperty, setSupportsProperty] = useState(false);

  useEffect(() => {
    // Check CSS @property support
    const checkPropertySupport = () => {
      try {
        // @ts-ignore
        return CSS && CSS.supports && CSS.supports('@property', '--test');
      } catch {
        return false;
      }
    };
    setSupportsProperty(checkPropertySupport());
  }, []);

  // Generate dynamic CSS for custom shimmer colors
  const dynamicStyle = supportsProperty ? {
    background: `conic-gradient(from var(--shimmer-angle), transparent 15%, ${shimmerColor}, transparent 60%)`,
    animation: 'shimmer-modern 2.5s linear infinite'
  } : {
    background: `linear-gradient(90deg, transparent 0%, transparent 40%, ${shimmerColor}88 50%, transparent 60%, transparent 100%)`,
    backgroundSize: '200% 100%',
    animation: 'shimmer-fallback 2.5s linear infinite'
  };

  const sizeClasses = {
    sm: 'px-3 py-1 text-sm h-8',
    md: 'px-6 py-2 h-10',
    lg: 'px-8 py-3 h-11',
    icon: 'h-9 w-9',
    default: 'px-4 py-2 h-9'
  };

  const variantClasses = {
    default: 'bg-gray-200 dark:bg-gray-900',
    ghost: 'bg-transparent',
    outline: 'bg-transparent border border-gray-200 dark:border-gray-700',
    secondary: 'bg-gray-100 dark:bg-gray-800',
    destructive: 'bg-red-500 dark:bg-red-600',
    link: 'bg-transparent underline-offset-4 hover:underline'
  };

  const innerVariantClasses = {
    default: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700',
    ghost: 'bg-transparent hover:bg-accent hover:text-accent-foreground',
    outline: 'bg-transparent text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800',
    secondary: 'bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700',
    destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    link: 'text-primary underline-offset-4 hover:underline'
  };

  const shouldShowShimmer = variant === 'default' || variant === 'destructive';

  return (
    <button
      className={cn(
        "relative inline-flex items-center justify-center p-[1.5px] rounded-full overflow-hidden group transition-all outline-none focus:outline-none focus-visible:ring-1 focus-visible:ring-gray-400 focus-visible:ring-offset-0 shimmer-button",
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {shouldShowShimmer && (
        <div
          className="absolute inset-0"
          style={dynamicStyle}
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
  );
};

export default ShimmerButtonFixed;