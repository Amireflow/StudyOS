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
import { readFromStorage, STORAGE_KEYS, writeToStorage } from '../lib/storage';
import {
  changePasswordApi,
  loginAccountApi,
  loginLocalApi,
  loginSupabasePasswordApi,
  logoutAllSessionsApi,
  registerAccountApi,
} from '../lib/studyApi';

export type AuthSession =
  | {
      mode: 'api';
      accessToken: string;
      userId: string;
      email: string;
      displayName: string;
      authProvider?: 'password' | 'supabase' | 'local_dev';
    }
  | {
      mode: 'local_demo';
      accessToken: null;
      userId: 'local-user';
      email: 'local@amireflow.local';
      displayName: string;
    };

export interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  authMessage: string | null;
  registerAccount: (input: {
    email: string;
    password: string;
    displayName: string;
    timezone?: string;
  }) => Promise<void>;
  loginAccount: (email: string, password: string) => Promise<void>;
  loginLocalServer: (email: string, displayName?: string) => Promise<void>;
  loginSupabase: (email: string, password: string) => Promise<void>;
  enterLocalDemoMode: (displayName?: string) => void;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logoutAllSessions: () => Promise<void>;
  updateSessionDisplayName: (displayName: string) => void;
  logout: (reason?: string) => void;
  clearAuthMessage: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function sanitizeStoredSession(raw: unknown): AuthSession | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }
  const candidate = raw as Partial<AuthSession>;
  if (candidate.mode === 'local_demo') {
    return {
      mode: 'local_demo',
      accessToken: null,
      userId: 'local-user',
      email: 'local@amireflow.local',
      displayName:
        typeof candidate.displayName === 'string' && candidate.displayName.trim()
          ? candidate.displayName.trim()
          : 'Mode local',
    };
  }
  if (
    candidate.mode === 'api' &&
    typeof candidate.accessToken === 'string' &&
    candidate.accessToken &&
    typeof candidate.userId === 'string' &&
    candidate.userId
  ) {
    return {
      mode: 'api',
      accessToken: candidate.accessToken,
      userId: candidate.userId,
      email: typeof candidate.email === 'string' ? candidate.email : '',
      displayName:
        typeof candidate.displayName === 'string' && candidate.displayName.trim()
          ? candidate.displayName.trim()
          : 'Utilisateur',
      authProvider: candidate.authProvider,
    };
  }
  return null;
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
    return sanitizeStoredSession(readFromStorage<unknown>(STORAGE_KEYS.authSession, null));
  });
  const [authMessage, setAuthMessage] = useState<string | null>(null);

  useEffect(() => {
    if (initialSession !== undefined) {
      return;
    }
    if (session) {
      writeToStorage(STORAGE_KEYS.authSession, session);
    } else {
      try {
        window.localStorage.removeItem(STORAGE_KEYS.authSession);
      } catch {
        // Ignore les erreurs de stockage en navigation privée stricte.
      }
    }
  }, [session, initialSession]);

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

  const loginLocalServer = useCallback(
    async (email: string, displayName?: string) => {
      const cleanEmail = email.trim();
      const result = await loginLocalApi(cleanEmail, displayName);
      queryClient.clear();
      setAuthMessage(null);
      setSession({
        mode: 'api',
        accessToken: result.accessToken,
        userId: result.profile.id,
        email: result.email ?? cleanEmail.toLowerCase(),
        displayName: result.profile.displayName,
        authProvider: 'local_dev',
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

  const enterLocalDemoMode = useCallback(
    (displayName = 'Mode local') => {
      queryClient.clear();
      setAuthMessage(null);
      setSession({
        mode: 'local_demo',
        accessToken: null,
        userId: 'local-user',
        email: 'local@amireflow.local',
        displayName: displayName.trim() || 'Mode local',
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
      queryClient.clear();
      setSession(null);
      setAuthMessage(reason ?? null);
    },
    [queryClient],
  );

  const logoutAllSessions = useCallback(async () => {
    if (session?.mode === 'api' && session.accessToken) {
      try {
        await logoutAllSessionsApi(session.accessToken);
      } catch {
        // Révoque côté client même si le jeton était déjà expiré.
      }
    }
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
      authMessage,
      registerAccount,
      loginAccount,
      loginLocalServer,
      loginSupabase,
      enterLocalDemoMode,
      changePassword,
      logoutAllSessions,
      updateSessionDisplayName,
      logout,
      clearAuthMessage,
    }),
    [
      session,
      authMessage,
      registerAccount,
      loginAccount,
      loginLocalServer,
      loginSupabase,
      enterLocalDemoMode,
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
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
