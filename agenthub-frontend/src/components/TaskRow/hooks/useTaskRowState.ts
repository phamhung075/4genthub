import { useState } from 'react';

export function useTaskRowState() {
  const [isVisible, setIsVisible] = useState(true);

  const getBaseClasses = (isHighlighted: boolean, isHovered: boolean) => {
    const baseClasses = 'transition-all duration-200';

    return baseClasses + (
      isHighlighted
        ? ' border-blue-400 bg-orange-100 dark:bg-blue-950 shadow-md'
        : isHovered
        ? ' border-violet-400 shadow-lg bg-violet-200 dark:bg-violet-950'
        : ' border-surface-border dark:border-gray-700'
    );
  };

  return {
    isVisible,
    setIsVisible,
    getBaseClasses
  };
}