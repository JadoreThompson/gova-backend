import type {
  GetDeploymentsModeratorsModeratorIdDeploymentsGetParams,
  ListGuidelinesGuidelinesGetParams,
  ListModeratorsModeratorsGetParams,
} from "@/openapi";

export const queryKeys = {
  // Auth
  auth: () => ["auth"] as const,
  me: () => ["me"] as const,

  // Connections
  discordGuilds: () => ["connections", "guilds"] as const,

  // Guidelines
  guidelines: (params?: ListGuidelinesGuidelinesGetParams) =>
    ["guidelines", params] as const,
  guideline: (guidelineId: string) =>
    [...queryKeys.guidelines(), guidelineId] as const,

  // Moderators
  moderators: (params?: ListModeratorsModeratorsGetParams) =>
    ["moderators", params] as const,
  moderator: (moderatorId: string) =>
    [...queryKeys.moderators(), moderatorId] as const,
  moderatorStats: (moderatorId: string) =>
    [...queryKeys.moderators(), "stats", moderatorId] as const,
  moderatorDeployments: (
    moderatorId: string,
    params: GetDeploymentsModeratorsModeratorIdDeploymentsGetParams,
  ) => [...queryKeys.moderators(), "deployments", moderatorId, params] as const,

  // Deployments (Global list)
  deployments: (params?: unknown) => ["deployments", params] as const,
  deployment: (deploymentId: string) =>
    [...queryKeys.deployments(), deploymentId] as const,
  deploymentStats: (deploymentId: string) =>
    [...queryKeys.deployments(), "stats", deploymentId] as const,
};
