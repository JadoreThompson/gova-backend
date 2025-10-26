import { queryClient } from "@/lib/query/query-client";
import { queryKeys } from "@/lib/query/query-keys";
import { handleApi } from "@/lib/utils/base";
import {
  changePasswordAuthChangePasswordPost,
  changeUsernameAuthChangeUsernamePost,
  discordCallbackAuthDiscordOauthGet,
  getMeAuthMeGet,
  loginAuthLoginPost,
  logoutAuthLogoutPost,
  registerAuthRegisterPost,
  requestEmailVerificationAuthRequestEmailVerificationPost,
  verifyActionAuthVerifyActionPost,
  verifyEmailAuthVerifyEmailPost,
  type DiscordCallbackAuthDiscordOauthGetParams,
  type UpdatePassword,
  type UpdateUsername,
  type UserCreate,
  type UserLogin,
  type VerifyAction,
  type VerifyCode,
} from "@/openapi";
import { useMutation, useQuery } from "@tanstack/react-query";

/**
 * Handles user registration. On success, the user will receive a verification email.
 */
export function useRegisterMutation() {
  return useMutation({
    mutationFn: async (data: UserCreate) =>
      handleApi(await registerAuthRegisterPost(data)),
  });
}

/**
 * Handles user login. On success, invalidates the `me` query to fetch the user's data.
 */
export function useLoginMutation() {
  return useMutation({
    mutationFn: async (data: UserLogin) =>
      handleApi(await loginAuthLoginPost(data)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.me() });
    },
  });
}

/**
 * Handles user logout. On success, invalidates all queries to clear user-specific data.
 */
export function useLogoutMutation() {
  return useMutation({
    mutationFn: async () => handleApi(await logoutAuthLogoutPost()),
    onSuccess: () => queryClient.invalidateQueries(),
  });
}

/**
 * For an authenticated user to request a new email verification code.
 */
export function useRequestEmailVerificationMutation() {
  return useMutation({
    mutationFn: async () =>
      handleApi(await requestEmailVerificationAuthRequestEmailVerificationPost()),
  });
}

/**
 * Handles the submission of an email verification code.
 * On success, invalidates the `me` query to update the user's authenticated status.
 */
export function useVerifyEmailMutation() {
  return useMutation({
    mutationFn: async (data: VerifyCode) =>
      handleApi(await verifyEmailAuthVerifyEmailPost(data)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.me() });
    },
  });
}

/**
 * Fetches the current authenticated user's data.
 */
export function useMeQuery() {
  return useQuery({
    queryKey: queryKeys.me(),
    queryFn: async () => handleApi(await getMeAuthMeGet()),
  });
}

/**
 * A version of useMeQuery with fewer retries, suitable for route guards
 * to quickly determine authentication status without excessive network requests.
 */
export function useMeQueryAuthGuard() {
  return useQuery({
    queryKey: queryKeys.me(),
    queryFn: async () => handleApi(await getMeAuthMeGet()),
    retry: 1,
  });
}

/**
 * Handles the OAuth callback from Discord to link a user's account.
 */
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

/**
 * Initiates a username change by sending a verification email to the user.
 * The actual change is finalized with `useVerifyActionMutation`.
 */
export function useChangeUsernameMutation() {
  return useMutation({
    mutationFn: async (params: UpdateUsername) =>
      handleApi(await changeUsernameAuthChangeUsernamePost(params)),
  });
}

/**
 * Initiates a password change by sending a verification email to the user.
 * The actual change is finalized with `useVerifyActionMutation`.
 */
export function useChangePasswordMutation() {
  return useMutation({
    mutationFn: async (params: UpdatePassword) =>
      handleApi(await changePasswordAuthChangePasswordPost(params)),
  });
}

/**
 * Verifies a sensitive action (like changing username or password) using a code.
 * On success, it invalidates the `me` query to reflect the updated user data.
 */
export function useVerifyActionMutation() {
  return useMutation({
    mutationFn: async (params: VerifyAction) =>
      handleApi(await verifyActionAuthVerifyActionPost(params)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.me() });
    },
  });
}