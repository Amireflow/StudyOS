import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { AiStoreProvider } from '../state/AiStoreContext';
import { AuthProvider, type AuthSession } from '../state/AuthContext';
import { LearningStoreProvider } from '../state/LearningStoreContext';
import { StudyStoreProvider } from '../state/StudyStoreContext';
import { ThemeProvider } from '../state/ThemeContext';

export interface AppProvidersProps {
  children: ReactNode;
  initialSession?: AuthSession | null;
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
          <StudyStoreProvider>
            <LearningStoreProvider>
              <AiStoreProvider>{children}</AiStoreProvider>
            </LearningStoreProvider>
          </StudyStoreProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
