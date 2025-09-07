import React from 'react';
import { SparklesText } from './SparklesText';

// Brand component variants
type BrandVariant = 'header' | 'dashboard' | 'large';

interface BrandProps {
  variant?: BrandVariant;
  className?: string;
}

const brandConfig = {
  header: {
    sparkleCount: 15,
    sparkleSize: 8,
    className: "text-2xl font-bold text-base-primary group-hover:text-primary transition-colors"
  },
  dashboard: {
    sparkleCount: 25,
    sparkleSize: 12,
    className: "text-4xl font-bold text-base-primary"
  },
  large: {
    sparkleCount: 30,
    sparkleSize: 16,
    className: "text-6xl font-bold text-base-primary"
  }
} as const;

export const Brand: React.FC<BrandProps> = ({ 
  variant = 'header', 
  className 
}) => {
  const config = brandConfig[variant];
  
  return (
    <SparklesText 
      as="h1" 
      className={className || config.className}
      sparkleCount={config.sparkleCount}
      sparkleSize={config.sparkleSize}
    >
      DhafnckMCP
    </SparklesText>
  );
};

export default Brand;