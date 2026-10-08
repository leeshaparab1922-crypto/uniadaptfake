import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type { LoginRequest, LoginResponse, UserPublic } from "../types/auth";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiRequest<UserPublic>("/auth/me"),
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LoginRequest) => apiRequest<LoginResponse>("/auth/login", { method: "POST", body: payload }),
    onSuccess: (data) => {
      queryClient.setQueryData(["me"], data.user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiRequest<{ message: string }>("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      queryClient.setQueryData(["me"], null);
      queryClient.invalidateQueries();
    },
  });
}
