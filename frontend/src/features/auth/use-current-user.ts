import { useQuery } from "@tanstack/react-query";

import { authApi } from "./api";

export function useCurrentUser() {
  return useQuery({
    queryKey: ["current-user"],
    queryFn: authApi.me,
    retry: false,
    staleTime: 60_000,
  });
}

