import * as React from "react";
import { cn } from "../../lib/utils";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <select
      className={cn(
        "theme-input flex h-10 w-full text-sm disabled:opacity-50 disabled:pointer-events-none",
        className
      )}
      ref={ref}
      {...props}
    >
      {children}
    </select>
  )
);
Select.displayName = "Select";

export default Select;