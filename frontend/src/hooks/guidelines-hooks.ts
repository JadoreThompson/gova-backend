import { queryClient } from "@/lib/query/query-client";
import { queryKeys } from "@/lib/query/query-keys";
import { handleApi } from "@/lib/utils/base";
import {
  createGuidelineGuidelinesPost,
  deleteGuidelineGuidelinesGuidelineIdDelete,
  getGuidelineGuidelinesGuidelineIdGet,
  listGuidelinesGuidelinesGet,
  updateGuidelineGuidelinesGuidelineIdPut,
  type GuidelineCreate,
  type GuidelineResponse,
  type GuidelineUpdate,
  type ListGuidelinesGuidelinesGetParams,
  type PaginatedResponseGuidelineResponse,
} from "@/openapi";
import { useMutation, useQuery } from "@tanstack/react-query";

export function useGuidelinesQuery(params: ListGuidelinesGuidelinesGetParams) {
  return useQuery<PaginatedResponseGuidelineResponse>({
    queryKey: queryKeys.guidelines(params),
    queryFn: async () => handleApi(await listGuidelinesGuidelinesGet(params)),
    enabled: !!params.page,
  });
}


export function useGuidelineQuery(guidelineId?: string) {
  return useQuery<GuidelineResponse>({
    queryKey: queryKeys.guideline(guidelineId || "placeholder"),
    queryFn: async () =>
      handleApi(await getGuidelineGuidelinesGuidelineIdGet(guidelineId!)),
    enabled: !!guidelineId,
  });
}

export function useCreateGuidelineMutation() {
  return useMutation({
    mutationFn: async (data: GuidelineCreate) =>
      handleApi(await createGuidelineGuidelinesPost(data)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.guidelines() });
    },
  });
}

export function useUpdateGuidelineMutation() {
  return useMutation({
    mutationFn: async (params: {
      guidelineId: string;
      data: GuidelineUpdate;
    }) =>
      handleApi(
        await updateGuidelineGuidelinesGuidelineIdPut(
          params.guidelineId,
          params.data,
        ),
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.guidelines() });
      queryClient.invalidateQueries({
        queryKey: queryKeys.guideline(variables.guidelineId),
      });
    },
  });
}

export function useDeleteGuidelineMutation() {
  return useMutation({
    mutationFn: async (guidelineId: string) =>
      handleApi(await deleteGuidelineGuidelinesGuidelineIdDelete(guidelineId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.guidelines() });
    },
  });
}
