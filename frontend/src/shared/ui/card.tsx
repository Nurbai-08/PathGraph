import type { HTMLAttributes } from "react";

import { cn } from "../lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-3xl border border-ink/10 bg-white shadow-soft", className)}
      {...props}
    />
  );
}

