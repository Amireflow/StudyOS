import { useState, type FormEvent } from 'react';
import { CloudServerIcon } from '@hugeicons/core-free-icons';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { FormField, Input } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { ErrorState, SuccessBanner } from '../../components/ui/StateFeedback';
import { ThemeToggleButton } from '../../components/ui/ThemeToggle';
import { isSupabaseConfigured } from '../../lib/env';
import { extractFieldErrors } from '../../lib/validation';
import { useAuth } from '../../state/AuthContext';

const localLoginSchema = z.object({
  email: z.string().trim().email('Saisissez une adresse e-mail valide.'),
  displayName: z
    .string()
    .trim()
    .max(100, 'Le nom ne doit pas dépasser 100 caractères.')
    .optional()
    .or(z.literal('')),
});

const supabaseLoginSchema = z.object({
  email: z.string().trim().email('Saisissez une adresse e-mail valide.'),
  password: z.string().min(6, 'Le mot de passe doit contenir au moins 6 caractères.'),
});

/**
 * Écran de connexion (AUTH-01, AUTH-02) :
 * propose la connexion cloud Supabase (si configurée), la connexion locale FastAPI (JWT)
 * ou l'utilisation hors serveur en mode local.
 */
export function LoginPage() {
  const {
    isAuthenticated,
    authMessage,
    loginLocalServer,
    loginSupabase,
    enterLocalDemoMode,
    clearAuthMessage,
  } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();
  const redirectTarget = (location.state as { from?: string } | null)?.from || '/';

  const [email, setEmail] = useState('etudiant@amireflow.local');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [authMethod, setAuthMethod] = useState<'backend_jwt' | 'supabase'>('backend_jwt');
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string;
    displayName?: string;
    password?: string;
  }>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={redirectTarget} replace />;
  }

  const useSupabasePasswordAuth = isSupabaseConfigured && authMethod === 'supabase';

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    clearAuthMessage();

    if (useSupabasePasswordAuth) {
      const parsed = supabaseLoginSchema.safeParse({ email, password });
      if (!parsed.success) {
        setFieldErrors(extractFieldErrors<'email' | 'password'>(parsed.error));
        return;
      }
      setFieldErrors({});
      setIsSubmitting(true);
      try {
        await loginSupabase(parsed.data.email, parsed.data.password);
        navigate(redirectTarget, { replace: true });
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : 'Impossible de se connecter à Supabase.',
        );
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    const parsed = localLoginSchema.safeParse({ email, displayName });
    if (!parsed.success) {
      setFieldErrors(extractFieldErrors<'email' | 'displayName'>(parsed.error));
      return;
    }

    setFieldErrors({});
    setIsSubmitting(true);
    try {
      await loginLocalServer(parsed.data.email, parsed.data.displayName || undefined);
      navigate(redirectTarget, { replace: true });
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : 'Impossible de joindre le serveur API. Vérifiez que FastAPI est démarré.',
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-dvh items-center justify-center bg-[#f5f5f3] px-4 py-10 dark:bg-zinc-950">
      <div className="fixed right-4 top-4 z-10">
        <ThemeToggleButton />
      </div>
      <div className="w-full max-w-md space-y-5">
        <div className="text-center">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-900 text-sm font-bold tracking-tight text-white dark:bg-zinc-100 dark:text-zinc-950">
            AF
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Amireflow Study OS
          </h1>
        </div>

        {authMessage && <SuccessBanner message={authMessage} onDismiss={clearAuthMessage} />}
        {submitError && <ErrorState title="Connexion impossible" message={submitError} />}

        <Card>
          <CardHeader>
            <CardTitle>Connexion</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isSupabaseConfigured && (
              <div className="grid grid-cols-2 gap-1.5 rounded-xl bg-zinc-100/80 p-1 text-xs dark:bg-zinc-800/80">
                <button
                  type="button"
                  onClick={() => {
                    setAuthMethod('backend_jwt');
                    setFieldErrors({});
                    setSubmitError(null);
                  }}
                  className={
                    authMethod === 'backend_jwt'
                      ? 'rounded-lg bg-white px-2.5 py-1.5 font-semibold text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50'
                      : 'rounded-lg px-2.5 py-1.5 font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100'
                  }
                >
                  API Backend (JWT)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthMethod('supabase');
                    setFieldErrors({});
                    setSubmitError(null);
                  }}
                  className={
                    authMethod === 'supabase'
                      ? 'rounded-lg bg-white px-2.5 py-1.5 font-semibold text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50'
                      : 'rounded-lg px-2.5 py-1.5 font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100'
                  }
                >
                  Supabase Cloud
                </button>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              <FormField id="login-email" label="Adresse e-mail" required error={fieldErrors.email}>
                <Input
                  id="login-email"
                  type="email"
                  value={email}
                  hasError={Boolean(fieldErrors.email)}
                  placeholder="etudiant@amireflow.local"
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (fieldErrors.email) {
                      setFieldErrors((prev) => ({ ...prev, email: undefined }));
                    }
                  }}
                />
              </FormField>

              {useSupabasePasswordAuth ? (
                <FormField
                  id="login-password"
                  label="Mot de passe"
                  required
                  error={fieldErrors.password}
                >
                  <Input
                    id="login-password"
                    type="password"
                    value={password}
                    hasError={Boolean(fieldErrors.password)}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </FormField>
              ) : (
                <FormField
                  id="login-display-name"
                  label="Nom d’affichage (facultatif)"
                  error={fieldErrors.displayName}
                >
                  <Input
                    id="login-display-name"
                    value={displayName}
                    hasError={Boolean(fieldErrors.displayName)}
                    placeholder="Ex. Khadim"
                    onChange={(e) => setDisplayName(e.target.value)}
                  />
                </FormField>
              )}

              <Button type="submit" variant="primary" className="w-full" isLoading={isSubmitting}>
                <Icon icon={CloudServerIcon} size={16} />
                {useSupabasePasswordAuth ? 'Se connecter via Supabase' : 'Se connecter au backend'}
              </Button>
            </form>

            <div className="pt-2">
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => {
                  enterLocalDemoMode(displayName || 'Mode local');
                  navigate(redirectTarget, { replace: true });
                }}
              >
                Continuer en mode local (sans serveur)
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
