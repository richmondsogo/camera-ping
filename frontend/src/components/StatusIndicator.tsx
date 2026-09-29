import React from "react";
import { cn } from "@/lib/utils";

export type StatusType = "online" | "offline" | "unknown";

interface StatusIndicatorProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: StatusType;
  label?: string;
}

const statusConfig: Record<
  StatusType,
  { dotClass: string; defaultLabel: string }
> = {
  online: {
    dotClass: "bg-status-online",
    defaultLabel: "Online",
  },
  offline: {
    dotClass: "bg-status-offline",
    defaultLabel: "Offline",
  },
  unknown: {
    dotClass: "bg-status-unknown",
    defaultLabel: "Unknown",
  },
};

export function StatusIndicator({
  status,
  label,
  className,
  ...props
}: StatusIndicatorProps) {
  const config = statusConfig[status];
  const displayLabel = label ?? config.defaultLabel;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 text-sm text-foreground",
        className
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn("size-2 rounded-full shrink-0", config.dotClass)}
      />
      <span>{displayLabel}</span>
    </span>
  );
}

export default StatusIndicator;
