import { t, useLocale } from "../../shared/lib/i18n";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Network } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuthStore } from "../../entities/user/store";
import { authApi, type Credentials } from "../../features/auth/api";
import { useCurrentUser } from "../../features/auth/use-current-user";
import { ApiError } from "../../shared/api/client";
import { Button } from "../../shared/ui/button";
import { Card } from "../../shared/ui/card";
import { Input } from "../../shared/ui/input";
import { ErrorMessage, PageLoader } from "../../shared/ui/status";

const credentialsSchema = z.object({
  email: z.email(t("Enter a valid email address.")),
  password: z.string().min(8, t("Password must contain at least 8 characters.")),
});

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  useLocale();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const setUser = useAuthStore((state) => state.setUser);
  const currentUser = useCurrentUser();
  const mutation = useMutation({
    mutationFn: (credentials: Credentials) => authenticate(mode, credentials),
    onSuccess: (user) => {
      setUser(user);
      queryClient.setQueryData(["current-user"], user);
      navigate("/", { replace: true });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    setValidationError(null);
    const result = credentialsSchema.safeParse({ email, password });
    if (!result.success) {
      setValidationError(result.error.issues[0]?.message ?? t("Check your details."));
      return;
    }
    mutation.mutate(result.data);
  }

  if (currentUser.isLoading) return <PageLoader />;
  if (currentUser.data) return <Navigate to="/" replace />;

  const isLogin = mode === "login";
  const requestError =
    mutation.error instanceof ApiError ? mutation.error.message : mutation.error?.message;

  return (
    <main className="grid min-h-screen bg-cream lg:grid-cols-[1.1fr_0.9fr]">
      <section className="relative hidden overflow-hidden bg-ink p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-20 top-24 h-80 w-80 rounded-full border border-lime/30" />
        <div className="absolute -right-4 top-40 h-52 w-52 rounded-full border border-lime/20" />
        <div className="relative flex items-center gap-3 font-semibold">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-lime text-ink">PG</span>
          PathGraph
        </div>
        <div className="relative max-w-xl">
          <Network className="mb-8 text-lime" size={38} />
          <h1 className="text-5xl font-semibold leading-[1.08] tracking-tight"> {t("Turn scattered learning into a path you can see.")} </h1>
          <p className="mt-6 max-w-md text-lg leading-8 text-white/60"> {t("Organize what you learn today. Connect it into knowledge tomorrow.")} </p>
        </div>
        <p className="relative text-sm text-white/35">
          {localAuthEnabled ? t("Local test authentication") : t("Secured by Firebase Authentication")}
        </p>
      </section>

      <section className="flex items-center justify-center p-5 sm:p-10">
        <Card className="w-full max-w-md p-7 sm:p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-moss">
            {isLogin ? t("Welcome back") : t("Start your path")}
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight">
            {isLogin ? t("Sign in") : t("Create your account")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-ink/55">
            {isLogin ? t("Continue building your knowledge map.") : t("Set up your learning workspace.")}
          </p>
          <form className="mt-8 space-y-5" onSubmit={submit}>
            <label className="block space-y-2 text-sm font-medium"> {t("Email")} <Input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
              />
            </label>
            <label className="block space-y-2 text-sm font-medium"> {t("Password")} <Input
                type="password"
                autoComplete={isLogin ? "current-password" : "new-password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={t("At least 8 characters")}
              />
            </label>
            {(validationError || requestError) && (
              <ErrorMessage message={validationError ?? requestError ?? t("Request failed.")} />
            )}
            <Button type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? t("Please wait…") : isLogin ? t("Sign in") : t("Create account")}
              {!mutation.isPending && <ArrowRight size={17} />}
            </Button>
          </form>
          <p className="mt-6 text-center text-sm text-ink/55">
            {isLogin ? t("New to PathGraph?") : t("Already have an account?")}{" "}
            <Link className="font-semibold text-moss hover:underline" to={isLogin ? "/register" : "/login"}>
              {isLogin ? t("Create account") : t("Sign in")}
            </Link>
          </p>
        </Card>
      </section>
    </main>
  );
}

async function authenticate(mode: "login" | "register", credentials: Credentials) {
  if (localAuthEnabled) {
    return mode === "login" ? authApi.login(credentials) : authApi.register(credentials);
  }
  const { firebaseAuthentication } = await import(
    "../../features/auth/firebase-authentication"
  );
  return mode === "login"
    ? firebaseAuthentication.login(credentials)
    : firebaseAuthentication.register(credentials);
}

const localAuthEnabled = import.meta.env.VITE_LOCAL_AUTH_ENABLED === "true";
