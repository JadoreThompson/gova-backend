import { cn } from "@/lib/utils";
import type { ModeratorDeploymentStatus } from "@/openapi";
import type { FC } from "react";

const DeploymentStatusBadge: FC<{ status: ModeratorDeploymentStatus }> = ({
  status,
}) => {
  const getClassName = (value: ModeratorDeploymentStatus) => {
    switch (value) {
      case "offline":
        return `
        bg-gray-500/10 text-gray-500 border-gray-500
        dark:bg-gray-500/20 dark:text-gray-300 dark:border-gray-300
      `;
      case "pending":
        return `
        bg-yellow-500/10 text-yellow-500 border-yellow-500
        dark:bg-yellow-500/20 dark:text-yellow-300 dark:border-yellow-300
      `;
      case "online":
        return `
        bg-green-500/10 text-green-500 border-green-500
        dark:bg-green-500/20 dark:text-green-300 dark:border-green-300
      `;
      default:
        return `
        bg-gray-100 text-gray-700 border-gray-300
        dark:bg-gray-500/20 dark:text-gray-300 dark:border-gray-300
      `;
    }
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium select-none",
        getClassName(status),
      )}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

export default DeploymentStatusBadge;
