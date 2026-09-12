import { forwardRef, type TextareaHTMLAttributes } from "react";

import { cn } from "../lib/cn";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "min-h-28 w-full resize-none rounded-2xl border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink/35 focus:border-moss focus:ring-4 focus:ring-moss/10",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";

