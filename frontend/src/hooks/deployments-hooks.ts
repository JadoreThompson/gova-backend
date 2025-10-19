import { queryClient } from "@/lib/query/query-client";
import { queryKeys } from "@/lib/query/query-keys";
import { handleApi } from "@/lib/utils/base";
import {
  deleteDeploymentDeploymentsDeploymentIdDelete,
  getDeploymentDeploymentsDeploymentIdGet,
  listDeploymentsDeploymentsGet,
  updateDeploymentDeploymentsDeploymentIdPut,
  type BodyListDeploymentsDeploymentsGet,
  type DeploymentResponse,
  type DeploymentUpdate,
  type ListDeploymentsDeploymentsGetParams,
  type PaginatedResponseDeploymentResponse,
} from "@/openapi";
import { useMutation, useQuery } from "@tanstack/react-query";

export function useDeploymentsQuery(
  params: ListDeploymentsDeploymentsGetParams &
    BodyListDeploymentsDeploymentsGet,
) {
  return useQuery<PaginatedResponseDeploymentResponse>({
    queryKey: queryKeys.deployments(params),
    queryFn: async () => handleApi(await listDeploymentsDeploymentsGet({status: params.status, platform: params.platform}, params)),
    enabled: !!params.page,
  });
}

export function useDeploymentQuery(deploymentId?: string) {
  return useQuery<DeploymentResponse>({
    queryKey: queryKeys.deployment(deploymentId || "placeholder"),
    queryFn: async () =>
      handleApi(await getDeploymentDeploymentsDeploymentIdGet(deploymentId!)),
    enabled: !!deploymentId,
  });
}

// --- Deployment Mutations ---

export function useUpdateDeploymentMutation() {
  return useMutation({
    mutationFn: async (params: {
      deploymentId: string;
      data: DeploymentUpdate;
    }) =>
      handleApi(
        await updateDeploymentDeploymentsDeploymentIdPut(
          params.deploymentId,
          params.data,
        ),
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.deployments() });
      queryClient.invalidateQueries({
        queryKey: queryKeys.deployment(variables.deploymentId),
      });
    },
  });
}

export function useDeleteDeploymentMutation() {
  return useMutation({
    mutationFn: async (deploymentId: string) =>
      handleApi(
        await deleteDeploymentDeploymentsDeploymentIdDelete(deploymentId),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.deployments() });
    },
  });
}
