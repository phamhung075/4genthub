import * as React from "react";
import { cn } from "../../lib/utils";

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>;

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <select
      className={cn(
        "theme-input flex min-h-[2.5rem] py-2 px-3 leading-normal w-full text-sm disabled:opacity-50 disabled:pointer-events-none cursor-pointer",
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
