import { queryClient } from "@/lib/query/query-client";
import { queryKeys } from "@/lib/query/query-keys";
import { handleApi } from "@/lib/utils/base";
import {
  deleteConnectionAuthConnectionsPlatformDelete,
  discordCallbackAuthDiscordOauthGet,
  getMeAuthMeGet,
  loginAuthLoginPost,
  MessagePlatformType,
  registerAuthRegisterPost,
  type DiscordCallbackAuthDiscordOauthGetParams,
  type UserCreate,
  type UserLogin,
} from "@/openapi";
import { useMutation, useQuery } from "@tanstack/react-query";

export function useRegisterMutation() {
  return useMutation({
    mutationFn: async (data: UserCreate) =>
      handleApi(await registerAuthRegisterPost(data)),
  });
}

export function useLoginMutation() {
  return useMutation({
    mutationFn: async (data: UserLogin) =>
      handleApi(await loginAuthLoginPost(data)),
  });
}

export function useMeQuery() {
  return useQuery({
    queryKey: queryKeys.me(),
    queryFn: async () => handleApi(await getMeAuthMeGet()),
  });
}

export function useDiscordCallbackQuery(
  params: DiscordCallbackAuthDiscordOauthGetParams,
  enabled: boolean = true,
) {
  return useQuery({
    queryKey: queryKeys.auth(),
    queryFn: async () =>
      handleApi(await discordCallbackAuthDiscordOauthGet(params)),
    enabled: enabled && !!params.code,
    staleTime: 0,
    gcTime: 0,
  });
}

export function useDeleteConnectionMutation() {
  return useMutation({
    mutationFn: async (platform: MessagePlatformType) =>
      handleApi(await deleteConnectionAuthConnectionsPlatformDelete(platform)),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.me() }),
  });
}
