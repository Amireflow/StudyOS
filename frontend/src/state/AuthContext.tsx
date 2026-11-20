import { useQueryClient } from '@tanstack/react-query';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { configureApiAuthHandlers } from '../lib/api-client';
import { purgeLegacyLocalBusinessStorage, STORAGE_KEYS } from '../lib/storage';
import {
  changePasswordApi,
  loginAccountApi,
  loginSupabasePasswordApi,
  logoutAllSessionsApi,
  logoutSessionApi,
  refreshSessionApi,
  registerAccountApi,
} from '../lib/studyApi';

export interface AuthSession {
  mode: 'api';
  accessToken: string;
  userId: string;
  email: string;
  displayName: string;
  authProvider?: 'password' | 'supabase' | 'local_dev';
}

export interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  authMessage: string | null;
  registerAccount: (input: {
    email: string;
    password: string;
    displayName: string;
    timezone?: string;
  }) => Promise<void>;
  loginAccount: (email: string, password: string) => Promise<void>;
  loginSupabase: (email: string, password: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logoutAllSessions: () => Promise<void>;
  updateSessionDisplayName: (displayName: string) => void;
  logout: (reason?: string) => void;
  clearAuthMessage: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function sanitizeStoredSession(): AuthSession | null {
  purgeLegacyLocalBusinessStorage();
  return null;
}

function hasApiSessionHint(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEYS.apiSessionHint) === '1';
  } catch {
    return false;
  }
}

function setApiSessionHint(enabled: boolean): void {
  try {
    if (enabled) {
      window.localStorage.setItem(STORAGE_KEYS.apiSessionHint, '1');
    } else {
      window.localStorage.removeItem(STORAGE_KEYS.apiSessionHint);
    }
  } catch {
    // Ignore les erreurs de stockage en navigation privée stricte.
  }
}

export interface AuthProviderProps {
  children: ReactNode;
  initialSession?: AuthSession | null;
}

export function AuthProvider({ children, initialSession }: AuthProviderProps) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<AuthSession | null>(() => {
    if (initialSession !== undefined) {
      return initialSession;
    }
    return sanitizeStoredSession();
  });
  const [isBootstrapping, setIsBootstrapping] = useState<boolean>(() => {
    if (initialSession !== undefined) {
      return false;
    }
    sanitizeStoredSession();
    return hasApiSessionHint();
  });
  const [authMessage, setAuthMessage] = useState<string | null>(null);

  useEffect(() => {
    if (initialSession !== undefined) {
      return;
    }
    purgeLegacyLocalBusinessStorage();
    if (session?.mode === 'api' && session.authProvider !== 'supabase') {
      setApiSessionHint(true);
    }
  }, [session, initialSession]);

  useEffect(() => {
    if (initialSession !== undefined || !isBootstrapping) {
      return;
    }
    let active = true;
    refreshSessionApi()
      .then((res) => {
        if (!active) return;
        queryClient.setQueryData(['profile', res.profile.id], res.profile);
        setSession({
          mode: 'api',
          accessToken: res.accessToken,
          userId: res.profile.id,
          email: res.email ?? '',
          displayName: res.profile.displayName,
          authProvider: 'password',
        });
      })
      .catch((err: unknown) => {
        const status =
          typeof err === 'object' && err !== null && 'status' in err
            ? Number((err as { status?: number }).status)
            : 0;
        // Ne purger l'indice de session que sur refus d'authentification explicite (401/403), pas sur coupure réseau
        if (status === 401 || status === 403) {
          setApiSessionHint(false);
        }
      })
      .finally(() => {
        if (active) {
          setIsBootstrapping(false);
        }
      });
    return () => {
      active = false;
    };
  }, [initialSession, isBootstrapping, queryClient]);

  const registerAccount = useCallback(
    async (input: { email: string; password: string; displayName: string; timezone?: string }) => {
      const result = await registerAccountApi(input);
      queryClient.clear();
      queryClient.setQueryData(['profile', result.profile.id], result.profile);
      setAuthMessage(null);
      setSession({
        mode: 'api',
        accessToken: result.accessToken,
        userId: result.profile.id,
        email: result.email ?? input.email.trim().toLowerCase(),
        displayName: result.profile.displayName,
        authProvider: 'password',
      });
    },
    [queryClient],
  );

  const loginAccount = useCallback(
    async (email: string, password: string) => {
      const result = await loginAccountApi({ email, password });
      queryClient.clear();
      queryClient.setQueryData(['profile', result.profile.id], result.profile);
      setAuthMessage(null);
      setSession({
        mode: 'api',
        accessToken: result.accessToken,
        userId: result.profile.id,
        email: result.email ?? email.trim().toLowerCase(),
        displayName: result.profile.displayName,
        authProvider: 'password',
      });
    },
    [queryClient],
  );

  const loginSupabase = useCallback(
    async (email: string, password: string) => {
      const cleanEmail = email.trim();
      const result = await loginSupabasePasswordApi(cleanEmail, password);
      queryClient.clear();
      setAuthMessage(null);
      setSession({
        mode: 'api',
        accessToken: result.accessToken,
        userId: result.profile.id,
        email: cleanEmail.toLowerCase(),
        displayName: result.profile.displayName,
        authProvider: 'supabase',
      });
    },
    [queryClient],
  );

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      if (session?.mode !== 'api' || !session.accessToken) {
        throw new Error('Connexion API requise pour modifier le mot de passe.');
      }
      const result = await changePasswordApi(session.accessToken, {
        currentPassword,
        newPassword,
      });
      setSession((prev) =>
        prev && prev.mode === 'api'
          ? {
              ...prev,
              accessToken: result.accessToken,
              displayName: result.profile.displayName,
              email: result.email ?? prev.email,
            }
          : prev,
      );
    },
    [session],
  );

  const logout = useCallback(
    (reason?: string) => {
      if (session?.mode === 'api') {
        void logoutSessionApi(session.accessToken).catch(() => {
          // Révoque côté client même si le serveur ne répond plus ou si le jeton est expiré.
        });
      }
      setApiSessionHint(false);
      purgeLegacyLocalBusinessStorage();
      queryClient.clear();
      setSession(null);
      setAuthMessage(reason ?? null);
    },
    [session, queryClient],
  );

  const apiAuthProvider = session?.mode === 'api' ? session.authProvider : undefined;

  useEffect(() => {
    configureApiAuthHandlers({
      refreshAccessToken: async () => {
        if (session?.mode !== 'api' || apiAuthProvider === 'supabase') {
          return null;
        }
        try {
          const refreshed = await refreshSessionApi();
          setSession((prev) =>
            prev && prev.mode === 'api'
              ? {
                  ...prev,
                  accessToken: refreshed.accessToken,
                  displayName: refreshed.profile.displayName,
                  email: refreshed.email ?? prev.email,
                }
              : prev,
          );
          return refreshed.accessToken;
        } catch {
          return null;
        }
      },
      onSessionExpired: (reason?: string) => {
        setApiSessionHint(false);
        purgeLegacyLocalBusinessStorage();
        queryClient.clear();
        setSession(null);
        setAuthMessage(reason ?? 'Votre session a expiré. Reconnectez-vous.');
      },
    });
    return () => {
      configureApiAuthHandlers({});
    };
  }, [session?.mode, apiAuthProvider, queryClient]);

  const logoutAllSessions = useCallback(async () => {
    if (session?.mode === 'api' && session.accessToken) {
      try {
        await logoutAllSessionsApi(session.accessToken);
      } catch {
        // Révoque côté client même si le jeton était déjà expiré.
      }
    }
    setApiSessionHint(false);
    purgeLegacyLocalBusinessStorage();
    queryClient.clear();
    setSession(null);
    setAuthMessage('Toutes vos sessions ont été déconnectées.');
  }, [session, queryClient]);

  const updateSessionDisplayName = useCallback((displayName: string) => {
    const clean = displayName.trim();
    if (!clean) {
      return;
    }
    setSession((prev) => (prev ? { ...prev, displayName: clean } : prev));
  }, []);

  const clearAuthMessage = useCallback(() => {
    setAuthMessage(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: session !== null,
      isBootstrapping,
      authMessage,
      registerAccount,
      loginAccount,
      loginSupabase,
      changePassword,
      logoutAllSessions,
      updateSessionDisplayName,
      logout,
      clearAuthMessage,
    }),
    [
      session,
      isBootstrapping,
      authMessage,
      registerAccount,
      loginAccount,
      loginSupabase,
      changePassword,
      logoutAllSessions,
      updateSessionDisplayName,
      logout,
      clearAuthMessage,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth doit être utilisé à l’intérieur de AuthProvider.');
  }
  return ctx;
}

/**
 * Protège les routes privées contre tout accès sans session active (AUTH-02).
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isBootstrapping } = useAuth();
  const location = useLocation();

  if (isBootstrapping) {
    return (
      <div
        role="status"
        className="flex min-h-[40vh] items-center justify-center p-6 text-sm text-zinc-500 dark:text-zinc-400"
      >
        Vérification de la session...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
