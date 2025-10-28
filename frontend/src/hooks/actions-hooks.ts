import { queryClient } from "@/lib/query/query-client";
import { queryKeys } from "@/lib/query/query-keys";
import { handleApi } from "@/lib/utils/base";
import {
  getDeploymentActionsDeploymentsDeploymentIdActionsGet,
  updateActionStatusActionsLogIdPatch,
  type ActionUpdate,
  type GetDeploymentActionsDeploymentsDeploymentIdActionsGetParams,
  type PaginatedResponseDeploymentAction,
} from "@/openapi";
import { useMutation, useQuery } from "@tanstack/react-query";

/**
 * Hook to fetch paginated actions for a specific deployment.
 * @param deploymentId The ID of the deployment.
 * @param params Pagination parameters.
 */
export function useDeploymentActionsQuery(
  deploymentId: string,
  params: GetDeploymentActionsDeploymentsDeploymentIdActionsGetParams,
) {
  return useQuery<PaginatedResponseDeploymentAction>({
    queryKey: queryKeys.deploymentActions(deploymentId, params),
    queryFn: async () =>
      handleApi(
        await getDeploymentActionsDeploymentsDeploymentIdActionsGet(
          deploymentId,
          params,
        ),
      ),
    enabled: !!deploymentId,
  });
}

export function useUpdateActionStatusMutation() {
  return useMutation({
    mutationFn: async (params: {
      logId: string;
      deploymentId: string;
      data: ActionUpdate;
    }) => {
      return handleApi(
        await updateActionStatusActionsLogIdPatch(params.logId, params.data),
      );
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.deploymentActions(variables.deploymentId),
      });
    },
  });
}
