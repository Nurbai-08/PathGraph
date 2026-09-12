import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "../lib/cn";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-12 w-full rounded-2xl border border-ink/15 bg-white px-4 text-sm text-ink outline-none transition placeholder:text-ink/35 focus:border-moss focus:ring-4 focus:ring-moss/10",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

