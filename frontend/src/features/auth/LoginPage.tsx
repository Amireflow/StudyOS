import { useState, type FormEvent } from 'react';
import { CloudServerIcon } from '@hugeicons/core-free-icons';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { FormField, Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { ErrorState, SuccessBanner } from '../../components/ui/StateFeedback';
import { ThemeToggleButton } from '../../components/ui/ThemeToggle';
import { extractFieldErrors } from '../../lib/validation';
import { useAuth } from '../../state/AuthContext';

const TIMEZONE_OPTIONS = [
  { value: 'Africa/Dakar', label: 'Africa/Dakar (UTC+0)' },
  { value: 'Europe/Paris', label: 'Europe/Paris (UTC+1 / UTC+2)' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Africa/Casablanca', label: 'Africa/Casablanca' },
  { value: 'America/Montreal', label: 'America/Montreal' },
  { value: 'America/New_York', label: 'America/New_York' },
] as const;

const loginSchema = z.object({
  email: z.string().trim().email('Saisissez une adresse e-mail valide.'),
  password: z.string().min(1, 'Saisissez votre mot de passe.'),
});

const registerSchema = z
  .object({
    displayName: z
      .string()
      .trim()
      .min(2, 'Le nom d’affichage doit contenir au moins 2 caractères.')
      .max(100, 'Le nom ne doit pas dépasser 100 caractères.'),
    email: z.string().trim().email('Saisissez une adresse e-mail valide.'),
    timezone: z.string().trim().min(1, 'Veuillez choisir un fuseau horaire.'),
    password: z
      .string()
      .min(8, 'Le mot de passe doit contenir au moins 8 caractères.')
      .max(128, 'Le mot de passe ne doit pas dépasser 128 caractères.'),
    confirmPassword: z.string().min(1, 'Confirmez votre mot de passe.'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Les mots de passe ne correspondent pas.',
    path: ['confirmPassword'],
  });

type LoginTab = 'login' | 'register';
type FieldName = 'email' | 'password' | 'confirmPassword' | 'displayName' | 'timezone';

/**
 * Écran d'authentification multi-comptes (AUTH-01, AUTH-02) :
 * connexion et inscription réelles adossées à la base de données via l'API Study OS.
 */
export function LoginPage() {
  const {
    isAuthenticated,
    authMessage,
    registerAccount,
    loginAccount,
    clearAuthMessage,
  } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();
  const redirectTarget = (location.state as { from?: string } | null)?.from || '/';

  const [activeTab, setActiveTab] = useState<LoginTab>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [timezone, setTimezone] = useState('Africa/Dakar');
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={activeTab === 'register' ? '/' : redirectTarget} replace />;
  }

  const switchTab = (nextTab: LoginTab) => {
    setActiveTab(nextTab);
    setFieldErrors({});
    setSubmitError(null);
    setPassword('');
    setConfirmPassword('');
  };

  const clearFieldError = (field: FieldName) => {
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    clearAuthMessage();

    if (activeTab === 'register') {
      const parsed = registerSchema.safeParse({
        displayName,
        email,
        timezone,
        password,
        confirmPassword,
      });
      if (!parsed.success) {
        setFieldErrors(extractFieldErrors<FieldName>(parsed.error));
        return;
      }
      setFieldErrors({});
      setIsSubmitting(true);
      try {
        await registerAccount({
          displayName: parsed.data.displayName,
          email: parsed.data.email,
          timezone: parsed.data.timezone,
          password: parsed.data.password,
        });
        navigate(redirectTarget, { replace: true });
      } catch (err) {
        setSubmitError(
          err instanceof Error
            ? err.message
            : 'Impossible de créer le compte pour le moment.',
        );
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    const parsed = loginSchema.safeParse({ email, password });
    if (!parsed.success) {
      setFieldErrors(extractFieldErrors<'email' | 'password'>(parsed.error));
      return;
    }

    setFieldErrors({});
    setIsSubmitting(true);
    try {
      await loginAccount(parsed.data.email, parsed.data.password);
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
    <div className="relative flex min-h-dvh flex-col items-center justify-center bg-[#f5f5f3] px-4 py-8 dark:bg-zinc-950">
      <div className="fixed right-4 top-4 z-10">
        <ThemeToggleButton />
      </div>
      <div className="my-auto w-full max-w-md space-y-5">
        <div className="text-center">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-900 text-sm font-bold tracking-tight text-white dark:bg-zinc-100 dark:text-zinc-950">
            AF
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Amireflow Study OS
          </h1>
        </div>

        {authMessage && <SuccessBanner message={authMessage} onDismiss={clearAuthMessage} />}
        {submitError && <ErrorState title="Authentification impossible" message={submitError} />}

        <Card>
          <CardHeader className="space-y-3">
            <CardTitle>
              {activeTab === 'register' ? 'Créer un compte' : 'Connexion'}
            </CardTitle>

            <div
              role="tablist"
              aria-label="Mode d’authentification"
              className="grid grid-cols-2 gap-1.5 rounded-xl bg-zinc-100/80 p-1 text-xs dark:bg-zinc-800/80"
            >
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'login'}
                onClick={() => switchTab('login')}
                className={
                  activeTab === 'login'
                    ? 'rounded-lg bg-white px-2.5 py-1.5 font-semibold text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50'
                    : 'rounded-lg px-2.5 py-1.5 font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100'
                }
              >
                Se connecter
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'register'}
                onClick={() => switchTab('register')}
                className={
                  activeTab === 'register'
                    ? 'rounded-lg bg-white px-2.5 py-1.5 font-semibold text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50'
                    : 'rounded-lg px-2.5 py-1.5 font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100'
                }
              >
                Créer un compte
              </button>
            </div>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} noValidate className="space-y-3.5">
              {activeTab === 'register' && (
                <FormField
                  id="register-display-name"
                  label="Nom d’affichage"
                  required
                  error={fieldErrors.displayName}
                >
                  <Input
                    id="register-display-name"
                    autoComplete="name"
                    value={displayName}
                    hasError={Boolean(fieldErrors.displayName)}
                    placeholder="Ex. Khadim"
                    onChange={(e) => {
                      setDisplayName(e.target.value);
                      clearFieldError('displayName');
                    }}
                  />
                </FormField>
              )}

              <FormField id="login-email" label="Adresse e-mail" required error={fieldErrors.email}>
                <Input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  hasError={Boolean(fieldErrors.email)}
                  placeholder="etudiant@exemple.com"
                  onChange={(e) => {
                    setEmail(e.target.value);
                    clearFieldError('email');
                  }}
                />
              </FormField>

              {activeTab === 'register' && (
                <FormField
                  id="register-timezone"
                  label="Fuseau horaire"
                  required
                  error={fieldErrors.timezone}
                >
                  <Select
                    id="register-timezone"
                    value={timezone}
                    hasError={Boolean(fieldErrors.timezone)}
                    onChange={(e) => {
                      setTimezone(e.target.value);
                      clearFieldError('timezone');
                    }}
                  >
                    {TIMEZONE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </Select>
                </FormField>
              )}

              <FormField
                id="login-password"
                label="Mot de passe"
                required
                error={fieldErrors.password}
              >
                <Input
                  id="login-password"
                  type="password"
                  autoComplete={activeTab === 'register' ? 'new-password' : 'current-password'}
                  value={password}
                  hasError={Boolean(fieldErrors.password)}
                  placeholder={activeTab === 'register' ? 'Au moins 8 caractères' : 'Votre mot de passe'}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    clearFieldError('password');
                  }}
                />
              </FormField>

              {activeTab === 'register' && (
                <FormField
                  id="register-confirm-password"
                  label="Confirmer le mot de passe"
                  required
                  error={fieldErrors.confirmPassword}
                >
                  <Input
                    id="register-confirm-password"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    hasError={Boolean(fieldErrors.confirmPassword)}
                    placeholder="Saisissez à nouveau le mot de passe"
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      clearFieldError('confirmPassword');
                    }}
                  />
                </FormField>
              )}

              <Button type="submit" variant="primary" className="w-full" isLoading={isSubmitting}>
                <Icon icon={CloudServerIcon} size={16} />
                {activeTab === 'register' ? 'Créer mon compte' : 'Se connecter'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
