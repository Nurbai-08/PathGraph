import { FirebaseError, getApp, getApps, initializeApp } from "firebase/app";
import {
  createUserWithEmailAndPassword,
  getAuth,
  inMemoryPersistence,
  setPersistence,
  signInWithEmailAndPassword,
  signOut,
  type Auth,
  type UserCredential,
} from "firebase/auth";

import type { User } from "../../shared/types/user";
import { authApi, type Credentials } from "./api";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

export class FirebaseAuthentication {
  async login(credentials: Credentials): Promise<User> {
    return this.authenticate("login", credentials);
  }

  async register(credentials: Credentials): Promise<User> {
    return this.authenticate("register", credentials);
  }

  private async authenticate(mode: "login" | "register", credentials: Credentials): Promise<User> {
    const firebaseAuth = this.getAuth();
    await setPersistence(firebaseAuth, inMemoryPersistence);
    try {
      const result = await this.createCredential(firebaseAuth, mode, credentials);
      const idToken = await result.user.getIdToken(true);
      return await authApi.firebaseSession(idToken);
    } catch (error) {
      throw readableAuthError(error);
    } finally {
      await signOut(firebaseAuth).catch(() => undefined);
    }
  }

  private createCredential(
    firebaseAuth: Auth,
    mode: "login" | "register",
    credentials: Credentials,
  ): Promise<UserCredential> {
    if (mode === "register") {
      return createUserWithEmailAndPassword(firebaseAuth, credentials.email, credentials.password);
    }
    return signInWithEmailAndPassword(firebaseAuth, credentials.email, credentials.password);
  }

  private getAuth(): Auth {
    const requiredConfig = Object.entries(firebaseConfig).slice(0, 4);
    const missingKey = requiredConfig.find(([, value]) => !value)?.[0];
    if (missingKey) {
      throw new Error(`Firebase is not configured: ${missingKey} is missing.`);
    }
    const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
    return getAuth(app);
  }
}

function readableAuthError(error: unknown): Error {
  if (!(error instanceof FirebaseError)) {
    return error instanceof Error ? error : new Error("Firebase sign-in failed.");
  }
  const messages: Record<string, string> = {
    "auth/email-already-in-use": "An account with this email already exists.",
    "auth/invalid-credential": "Email or password is incorrect.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/too-many-requests": "Too many attempts. Try again later.",
    "auth/weak-password": "Choose a stronger password.",
  };
  return new Error(messages[error.code] ?? "Firebase sign-in failed.");
}

export const firebaseAuthentication = new FirebaseAuthentication();
