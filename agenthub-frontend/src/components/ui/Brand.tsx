import React, { type ElementType } from 'react';
import { SparklesText } from './SparklesText';

// Brand component variants
type BrandVariant = 'header' | 'dashboard' | 'large';

interface BrandProps {
  variant?: BrandVariant;
  className?: string;
  /**
   * The element the wordmark renders as. A brand is not a heading: it is the same
   * string on every page, and while it rendered as `h1` it was the first heading in
   * the document on every signed-in route, so no page identified itself and every
   * page had two top-level headings (F-2). A caller that genuinely wants the
   * wordmark to be a page's heading passes one explicitly.
   */
  as?: ElementType;
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
  className,
  as = 'div'
}) => {
  const config = brandConfig[variant];

  return (
    <SparklesText
      as={as}
      className={className || config.className}
      sparkleCount={config.sparkleCount}
      sparkleSize={config.sparkleSize}
    >
      4genthub
    </SparklesText>
  );
};

export default Brand;
