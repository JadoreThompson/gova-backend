import { queryClient } from "@/lib/query/query-client";
import { queryKeys } from "@/lib/query/query-keys";
import { handleApi } from "@/lib/utils/base";
import {
  createModeratorModeratorsPost,
  deleteModeratorModeratorsModeratorIdDelete,
  deployModeratorModeratorsDeployModeratorIdPost,
  getModeratorModeratorsModeratorIdGet,
  listModeratorsModeratorsGet,
  updateModeratorModeratorsModeratorIdPut,
  type ListModeratorsModeratorsGetParams,
  type ModeratorCreate,
  type ModeratorDeploymentCreate,
  type ModeratorDeploymentResponse,
  type ModeratorResponse,
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
    ModeratorDeploymentResponse,
    Error,
    { moderatorId: string; data: ModeratorDeploymentCreate }
  >({
    mutationFn: async (params) =>
      handleApi(
        await deployModeratorModeratorsDeployModeratorIdPost(
          params.moderatorId,
          params.data,
        ),
      ),
    onSuccess: (newDeployment, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.moderators() });
      queryClient.invalidateQueries({ queryKey: queryKeys.deployments() });

      queryClient.setQueryData(
        queryKeys.deployment(newDeployment.deployment_id),
        newDeployment,
      );
    },
  });
}
