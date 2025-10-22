
import { queryKeys } from "@/lib/query/query-keys";
import { handleApi } from "@/lib/utils/base";
import {
    getOwnedDiscordGuildsConnectionsDiscordGuildsGet,
    type Guild,
} from "@/openapi";
import { useQuery } from "@tanstack/react-query";

export function useOwnedDiscordGuildsQuery() {
  return useQuery<Guild[]>({
    queryKey: queryKeys.discordGuilds(),
    queryFn: async () =>
      handleApi(
        await getOwnedDiscordGuildsConnectionsDiscordGuildsGet(),
      ),
  });
}