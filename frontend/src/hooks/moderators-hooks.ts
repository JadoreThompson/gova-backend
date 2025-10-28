import { queryClient } from "@/lib/query/query-client";
import { queryKeys } from "@/lib/query/query-keys";
import { handleApi } from "@/lib/utils/base";
import {
  createModeratorModeratorsPost,
  deleteModeratorModeratorsModeratorIdDelete,
  deployModeratorModeratorsModeratorIdDeployPost,
  getDeploymentsModeratorsModeratorIdDeploymentsGet,
  getModeratorModeratorsModeratorIdGet,
  getModeratorStatsModeratorsModeratorIdStatsGet,
  listModeratorsModeratorsGet,
  updateModeratorModeratorsModeratorIdPut,
  type DeploymentCreate,
  type DeploymentResponse,
  type GetDeploymentsModeratorsModeratorIdDeploymentsGetParams,
  type ListModeratorsModeratorsGetParams,
  type ModeratorCreate,
  type ModeratorResponse,
  type ModeratorStats,
  type ModeratorUpdate,
  type PaginatedResponseModeratorResponse,
} from "@/openapi";
import { useMutation, useQuery } from "@tanstack/react-query";

export function useModeratorsQuery(params: ListModeratorsModeratorsGetParams) {
  return useQuery<PaginatedResponseModeratorResponse>({
    queryKey: queryKeys.moderators(params),
    queryFn: async () => handleApi(await listModeratorsModeratorsGet(params)),
    enabled: !!params.page,
  });
}

export function useModeratorQuery(moderatorId?: string) {
  return useQuery<ModeratorResponse>({
    queryKey: queryKeys.moderator(moderatorId!),
    queryFn: async () =>
      handleApi(await getModeratorModeratorsModeratorIdGet(moderatorId!)),
    enabled: !!moderatorId,
  });
}

export function useCreateModeratorMutation() {
  return useMutation<ModeratorResponse, Error, ModeratorCreate>({
    mutationFn: async (data) =>
      handleApi(await createModeratorModeratorsPost(data)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.moderators() });
    },
  });
}

export function useModeratorStatsQuery(moderatorId?: string) {
  return useQuery<ModeratorStats>({
    queryKey: queryKeys.moderatorStats(moderatorId!),
    queryFn: async () =>
      handleApi(
        await getModeratorStatsModeratorsModeratorIdStatsGet(moderatorId!),
      ),
  });
}

export function useModeratorDeploymentsQuery(
  moderatorId?: string,
  params?: GetDeploymentsModeratorsModeratorIdDeploymentsGetParams,
) {
  return useQuery({
    queryKey: queryKeys.moderatorDeployments(moderatorId!, params!),
    queryFn: async () =>
      handleApi(
        await getDeploymentsModeratorsModeratorIdDeploymentsGet(
          moderatorId!,
          params,
        ),
      ),
  });
}

export function useUpdateModeratorMutation() {
  return useMutation<
    unknown,
    Error,
    { moderatorId: string; data: ModeratorUpdate }
  >({
    mutationFn: async (params) =>
      handleApi(
        await updateModeratorModeratorsModeratorIdPut(
          params.moderatorId,
          params.data,
        ),
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.moderators() });
      queryClient.invalidateQueries({
        queryKey: queryKeys.moderator(variables.moderatorId),
      });
    },
  });
}

export function useDeleteModeratorMutation() {
  return useMutation({
    mutationFn: async (moderatorId: string) =>
      handleApi(await deleteModeratorModeratorsModeratorIdDelete(moderatorId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.moderators() });
    },
  });
}

export function useDeployModeratorMutation() {
  return useMutation<
    DeploymentResponse,
    Error,
    { moderatorId: string; data: DeploymentCreate }
  >({
    mutationFn: async (params) =>
      handleApi(
        await deployModeratorModeratorsModeratorIdDeployPost(
          params.moderatorId,
          params.data,
        ),
      ),
    onSuccess: (newDeployment, _) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.moderators() });
      queryClient.invalidateQueries({ queryKey: queryKeys.deployments() });

      queryClient.setQueryData(
        queryKeys.deployment(newDeployment.deployment_id),
        newDeployment,
      );
    },
  });
}
