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
      gradient: 'from-gray-400/40 via-gray-300/40 to-gray-400/40',
      borderColor: 'border-gray-400/50',
      textColor: 'text-gray-700 dark:text-gray-300',
      glow: 'shadow-gray-400/30',
      label: 'To Do'
    },
    in_progress: {
      gradient: 'from-blue-500/40 via-cyan-400/40 to-blue-500/40',
      borderColor: 'border-blue-400/50',
      textColor: 'text-blue-700 dark:text-blue-300',
      glow: 'shadow-blue-400/30',
      label: 'In Progress'
    },
    blocked: {
      gradient: 'from-red-500/40 via-orange-400/40 to-red-500/40',
      borderColor: 'border-red-400/50',
      textColor: 'text-red-700 dark:text-red-300',
      glow: 'shadow-red-400/30',
      label: 'Blocked'
    },
    review: {
      gradient: 'from-purple-500/40 via-pink-400/40 to-purple-500/40',
      borderColor: 'border-purple-400/50',
      textColor: 'text-purple-700 dark:text-purple-300',
      glow: 'shadow-purple-400/30',
      label: 'Review'
    },
    testing: {
      gradient: 'from-yellow-500/40 via-amber-400/40 to-yellow-500/40',
      borderColor: 'border-yellow-400/50',
      textColor: 'text-yellow-700 dark:text-yellow-300',
      glow: 'shadow-yellow-400/30',
      label: 'Testing'
    },
    done: {
      gradient: 'from-green-500/40 via-emerald-400/40 to-green-500/40',
      borderColor: 'border-green-400/50',
      textColor: 'text-green-700 dark:text-green-300',
      glow: 'shadow-green-400/30',
      label: 'Done'
    },
    cancelled: {
      gradient: 'from-gray-500/40 via-gray-400/40 to-gray-500/40',
      borderColor: 'border-gray-500/50',
      textColor: 'text-gray-600 dark:text-gray-400',
      glow: 'shadow-gray-500/30',
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
      gradient: 'from-slate-400/40 via-gray-300/40 to-slate-400/40',
      borderColor: 'border-slate-400/50',
      textColor: 'text-slate-700 dark:text-slate-300',
      glow: 'shadow-slate-400/30',
      label: 'Low',
      icon: '▽'
    },
    medium: {
      gradient: 'from-blue-400/40 via-sky-300/40 to-blue-400/40',
      borderColor: 'border-blue-400/50',
      textColor: 'text-blue-700 dark:text-blue-300',
      glow: 'shadow-blue-400/30',
      label: 'Medium',
      icon: '◇'
    },
    high: {
      gradient: 'from-amber-500/40 via-yellow-400/40 to-amber-500/40',
      borderColor: 'border-amber-400/50',
      textColor: 'text-amber-700 dark:text-amber-300',
      glow: 'shadow-amber-400/30',
      label: 'High',
      icon: '△'
    },
    urgent: {
      gradient: 'from-orange-500/40 via-red-400/40 to-orange-500/40',
      borderColor: 'border-orange-400/50',
      textColor: 'text-orange-700 dark:text-orange-300',
      glow: 'shadow-orange-400/30',
      label: 'Urgent',
      icon: '⚠'
    },
    critical: {
      gradient: 'from-red-600/40 via-pink-500/40 to-red-600/40',
      borderColor: 'border-red-500/50',
      textColor: 'text-red-700 dark:text-red-300',
      glow: 'shadow-red-500/30',
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