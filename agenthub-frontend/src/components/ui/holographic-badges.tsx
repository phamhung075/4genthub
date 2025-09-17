'use client'
import React from 'react'

// Status Badge Component with holographic effects
interface HolographicStatusBadgeProps {
  status: 'todo' | 'in_progress' | 'blocked' | 'review' | 'testing' | 'done' | 'cancelled'
  className?: string
  size?: 'xs' | 'sm' | 'md' | 'lg'
}

export const HolographicStatusBadge: React.FC<HolographicStatusBadgeProps> = ({ 
  status, 
  className = '', 
  size = 'sm' 
}) => {
  const statusConfig = {
    todo: {
      gradient: 'from-slate-100/80 via-slate-50/80 to-slate-100/80 dark:from-slate-800/40 dark:via-slate-700/40 dark:to-slate-800/40',
      borderColor: 'border-slate-300 dark:border-slate-600',
      textColor: 'text-slate-600 dark:text-slate-300',
      glow: 'shadow-slate-200/50 dark:shadow-slate-600/30',
      label: 'To Do'
    },
    in_progress: {
      gradient: 'from-sky-100/80 via-blue-50/80 to-sky-100/80 dark:from-blue-800/40 dark:via-sky-700/40 dark:to-blue-800/40',
      borderColor: 'border-sky-300 dark:border-sky-600',
      textColor: 'text-sky-700 dark:text-sky-300',
      glow: 'shadow-sky-200/50 dark:shadow-sky-600/30',
      label: 'In Progress'
    },
    blocked: {
      gradient: 'from-rose-100/80 via-red-50/80 to-rose-100/80 dark:from-red-900/40 dark:via-rose-800/40 dark:to-red-900/40',
      borderColor: 'border-rose-300 dark:border-rose-600',
      textColor: 'text-rose-700 dark:text-rose-300',
      glow: 'shadow-rose-200/50 dark:shadow-rose-600/30',
      label: 'Blocked'
    },
    review: {
      gradient: 'from-violet-100/80 via-purple-50/80 to-violet-100/80 dark:from-purple-900/40 dark:via-violet-800/40 dark:to-purple-900/40',
      borderColor: 'border-violet-300 dark:border-violet-600',
      textColor: 'text-violet-700 dark:text-violet-300',
      glow: 'shadow-violet-200/50 dark:shadow-violet-600/30',
      label: 'Review'
    },
    testing: {
      gradient: 'from-amber-100/80 via-yellow-50/80 to-amber-100/80 dark:from-yellow-900/40 dark:via-amber-800/40 dark:to-yellow-900/40',
      borderColor: 'border-amber-300 dark:border-amber-600',
      textColor: 'text-amber-700 dark:text-amber-300',
      glow: 'shadow-amber-200/50 dark:shadow-amber-600/30',
      label: 'Testing'
    },
    done: {
      gradient: 'from-emerald-100/80 via-green-50/80 to-emerald-100/80 dark:from-green-900/40 dark:via-emerald-800/40 dark:to-green-900/40',
      borderColor: 'border-emerald-300 dark:border-emerald-600',
      textColor: 'text-emerald-700 dark:text-emerald-300',
      glow: 'shadow-emerald-200/50 dark:shadow-emerald-600/30',
      label: 'Done'
    },
    cancelled: {
      gradient: 'from-gray-100/80 via-gray-50/80 to-gray-100/80 dark:from-gray-800/40 dark:via-gray-700/40 dark:to-gray-800/40',
      borderColor: 'border-gray-300 dark:border-gray-600',
      textColor: 'text-gray-600 dark:text-gray-400',
      glow: 'shadow-gray-200/50 dark:shadow-gray-600/30',
      label: 'Cancelled'
    }
  }

  const sizeClasses = {
    xs: 'px-2 py-0.5 text-xs',
    sm: 'px-2.5 py-1 text-sm',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base'
  }

  const config = statusConfig[status]

  return (
    <div
      className={`
        inline-flex items-center font-medium rounded-full 
        backdrop-blur-md bg-gradient-to-r ${config.gradient}
        border ${config.borderColor} ${config.textColor}
        shadow-lg ${config.glow} hover:shadow-xl 
        transition-all duration-300 hover:scale-105 
        animate-gradient-x ${sizeClasses[size]} ${className}
      `}
      style={{
        backgroundSize: '200% 200%',
        animation: 'holographic 3s ease infinite'
      }}
    >
      <span className="relative z-10">{config.label}</span>
    </div>
  )
}

// Priority Badge Component with holographic effects
interface HolographicPriorityBadgeProps {
  priority: 'low' | 'medium' | 'high' | 'urgent' | 'critical'
  className?: string
  size?: 'xs' | 'sm' | 'md' | 'lg'
  showIcon?: boolean
}

export const HolographicPriorityBadge: React.FC<HolographicPriorityBadgeProps> = ({ 
  priority, 
  className = '', 
  size = 'sm',
  showIcon = true 
}) => {
  const priorityConfig = {
    low: {
      gradient: 'from-gray-100/60 via-gray-50/60 to-gray-100/60 dark:from-gray-800/30 dark:via-gray-700/30 dark:to-gray-800/30',
      borderColor: 'border-gray-200 dark:border-gray-700',
      textColor: 'text-gray-500 dark:text-gray-400',
      glow: 'shadow-gray-100/30 dark:shadow-gray-700/20',
      label: 'Low',
      icon: '▽'
    },
    medium: {
      gradient: 'from-teal-100/70 via-cyan-50/70 to-teal-100/70 dark:from-teal-900/35 dark:via-cyan-800/35 dark:to-teal-900/35',
      borderColor: 'border-teal-300 dark:border-teal-700',
      textColor: 'text-teal-700 dark:text-teal-300',
      glow: 'shadow-teal-200/40 dark:shadow-teal-700/25',
      label: 'Medium',
      icon: '◇'
    },
    high: {
      gradient: 'from-orange-100/80 via-amber-50/80 to-orange-100/80 dark:from-orange-900/40 dark:via-amber-800/40 dark:to-orange-900/40',
      borderColor: 'border-orange-400 dark:border-orange-600',
      textColor: 'text-orange-700 dark:text-orange-300',
      glow: 'shadow-orange-300/50 dark:shadow-orange-600/30',
      label: 'High',
      icon: '△'
    },
    urgent: {
      gradient: 'from-red-100/85 via-orange-50/85 to-red-100/85 dark:from-red-900/45 dark:via-orange-800/45 dark:to-red-900/45',
      borderColor: 'border-red-400 dark:border-red-600',
      textColor: 'text-red-700 dark:text-red-300',
      glow: 'shadow-red-300/60 dark:shadow-red-600/35',
      label: 'Urgent',
      icon: '⚠'
    },
    critical: {
      gradient: 'from-rose-200/90 via-red-100/90 to-rose-200/90 dark:from-red-950/50 dark:via-rose-900/50 dark:to-red-950/50',
      borderColor: 'border-red-500 dark:border-red-500',
      textColor: 'text-red-800 dark:text-red-200',
      glow: 'shadow-red-400/70 dark:shadow-red-500/40',
      label: 'Critical',
      icon: '🔥'
    }
  }

  const sizeClasses = {
    xs: 'px-2 py-0.5 text-xs gap-1',
    sm: 'px-2.5 py-1 text-sm gap-1',
    md: 'px-3 py-1.5 text-sm gap-1.5',
    lg: 'px-4 py-2 text-base gap-2'
  }

  const config = priorityConfig[priority]

  return (
    <div
      className={`
        inline-flex items-center font-medium rounded-full 
        backdrop-blur-md bg-gradient-to-r ${config.gradient}
        border ${config.borderColor} ${config.textColor}
        shadow-lg ${config.glow} hover:shadow-xl 
        transition-all duration-300 hover:scale-105 
        animate-gradient-x ${sizeClasses[size]} ${className}
      `}
      style={{
        backgroundSize: '200% 200%',
        animation: 'holographic 3s ease infinite'
      }}
    >
      {showIcon && <span className="relative z-10">{config.icon}</span>}
      <span className="relative z-10">{config.label}</span>
    </div>
  )
}

// Combined Status and Priority Badge for compact display
interface HolographicTaskBadgeProps {
  status?: 'todo' | 'in_progress' | 'blocked' | 'review' | 'testing' | 'done' | 'cancelled'
  priority?: 'low' | 'medium' | 'high' | 'urgent' | 'critical'
  className?: string
  size?: 'xs' | 'sm' | 'md' | 'lg'
}

export const HolographicTaskBadge: React.FC<HolographicTaskBadgeProps> = ({ 
  status, 
  priority, 
  className = '', 
  size = 'sm' 
}) => {
  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      {status && <HolographicStatusBadge status={status} size={size} />}
      {priority && <HolographicPriorityBadge priority={priority} size={size} />}
    </div>
  )
}

// Add CSS animation for holographic effect
if (typeof document !== 'undefined') {
  const style = document.createElement('style')
  style.textContent = `
    @keyframes holographic {
      0% {
        background-position: 0% 50%;
        filter: hue-rotate(0deg);
      }
      50% {
        background-position: 100% 50%;
        filter: hue-rotate(10deg);
      }
      100% {
        background-position: 0% 50%;
        filter: hue-rotate(0deg);
      }
    }
    
    @keyframes gradient-x {
      0%, 100% {
        background-position: 0% 50%;
      }
      50% {
        background-position: 100% 50%;
      }
    }
  `
  document.head.appendChild(style)
}

export default {
  HolographicStatusBadge,
  HolographicPriorityBadge,
  HolographicTaskBadge
}