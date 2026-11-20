import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { AiStoreProvider } from '../state/AiStoreContext';
import { AuthProvider, useAuth, type AuthSession } from '../state/AuthContext';
import { CoursesStoreProvider } from '../state/CoursesStoreContext';
import { LearningStoreProvider } from '../state/LearningStoreContext';
import { StudyStoreProvider } from '../state/StudyStoreContext';
import { ThemeProvider } from '../state/ThemeContext';

export interface AppProvidersProps {
  children: ReactNode;
  initialSession?: AuthSession | null;
}

/**
 * Réinitialise intégralement les stores métier lorsqu'un autre compte se connecte
 * ou après déconnexion afin d'éviter toute fuite d'état en mémoire.
 */
function UserScopedStores({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const scopeKey = session?.userId ?? 'guest';

  return (
    <StudyStoreProvider key={scopeKey}>
      <LearningStoreProvider>
        <CoursesStoreProvider>
          <AiStoreProvider>{children}</AiStoreProvider>
        </CoursesStoreProvider>
      </LearningStoreProvider>
    </StudyStoreProvider>
  );
}

/**
 * Fournisseurs globaux de l'application (TanStack Query, authentification, store métier).
 */
export function AppProviders({ children, initialSession }: AppProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            retry: false,
          },
        },
      }),
  );

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider initialSession={initialSession}>
          <UserScopedStores>{children}</UserScopedStores>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
