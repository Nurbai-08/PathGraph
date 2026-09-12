import { apiRequest } from "../../shared/api/client";
import type { User } from "../../shared/types/user";

export type Credentials = {
  email: string;
  password: string;
};

export const authApi = {
  register: (credentials: Credentials) =>
    apiRequest<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(credentials),
    }),
  login: (credentials: Credentials) =>
    apiRequest<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    }),
  firebaseSession: (idToken: string) =>
    apiRequest<User>("/auth/firebase/session", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    }),
  logout: () => apiRequest<{ logged_out: boolean }>("/auth/logout", { method: "POST" }),
  me: () => apiRequest<User>("/auth/me"),
};
