import { cn } from "@/lib/utils";
import type { ModeratorDeploymentStatus } from "@/openapi";
import type { FC } from "react";

const DeploymentStatusCircle: FC<{ status: ModeratorDeploymentStatus }> = ({
  status,
}) => {
  const getColorClass = (value: ModeratorDeploymentStatus) => {
    switch (value) {
      case "online":
        return {
          base: "bg-green-500 dark:bg-green-400",
          ring: "bg-green-400/30 dark:bg-green-300/20",
        };
      case "pending":
        return {
          base: "bg-yellow-500 dark:bg-yellow-400",
          ring: "bg-yellow-400/30 dark:bg-yellow-300/20",
        };
      case "offline":
        return {
          base: "bg-gray-400 dark:bg-gray-500",
          ring: "bg-gray-300/30 dark:bg-gray-400/20",
        };
      default:
        return {
          base: "bg-gray-400 dark:bg-gray-500",
          ring: "bg-gray-300/30 dark:bg-gray-400/20",
        };
    }
  };

  const { base, ring } = getColorClass(status);

  return (
    <span className="relative inline-flex h-3 w-3">
      {/* Pulsing ring */}
      <span
        className={cn(
          "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
          ring,
        )}
      />
      {/* Solid center */}
      <span className={cn("relative inline-flex h-3 w-3 rounded-full", base)} />
    </span>
  );
};

export default DeploymentStatusCircle;
