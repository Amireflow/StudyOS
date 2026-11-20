import { useEffect, useState, type FormEvent } from 'react';
import { ShieldCheckIcon } from '@hugeicons/core-free-icons';
import { z } from 'zod';
import { PageHeader } from '../../components/layout/PageHeader';
import { Button } from '../../components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/Card';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { ErrorState, LoadingState, SuccessBanner } from '../../components/ui/StateFeedback';
import { ThemeSegmentedControl } from '../../components/ui/ThemeToggle';
import { env } from '../../lib/env';
import { extractFieldErrors } from '../../lib/validation';
import { useStudyStore } from '../../state/StudyStoreContext';

const TIMEZONE_OPTIONS = [
  { value: 'Africa/Dakar', label: 'Africa/Dakar (UTC+0)' },
  { value: 'Europe/Paris', label: 'Europe/Paris (UTC+1 / UTC+2)' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Africa/Casablanca', label: 'Africa/Casablanca' },
  { value: 'America/Montreal', label: 'America/Montreal' },
  { value: 'America/New_York', label: 'America/New_York' },
] as const;

const settingsSchema = z.object({
  displayName: z
    .string()
    .trim()
    .min(2, 'Le nom d’affichage doit contenir au moins 2 caractères.')
    .max(100, 'Le nom d’affichage ne doit pas dépasser 100 caractères.'),
  timezone: z.string().trim().min(1, 'Veuillez choisir un fuseau horaire.'),
  aiInstructions: z
    .string()
    .trim()
    .max(2000, 'Les consignes ne doivent pas dépasser 2000 caractères.')
    .optional()
    .or(z.literal('')),
});

type SettingsField = 'displayName' | 'timezone' | 'aiInstructions';

/**
 * Écran Paramètres P0 (AUTH-03, CdC §4.10) : nom d'affichage, fuseau horaire et consignes IA.
 */
export function SettingsPage() {
  const {
    profile,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    updateProfile,
  } = useStudyStore();

  const [displayName, setDisplayName] = useState(profile.displayName);
  const [timezone, setTimezone] = useState(profile.timezone);
  const [aiInstructions, setAiInstructions] = useState(profile.aiInstructions ?? '');
  const [errors, setErrors] = useState<Partial<Record<SettingsField, string>>>({});
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setDisplayName(profile.displayName);
    setTimezone(profile.timezone);
    setAiInstructions(profile.aiInstructions ?? '');
  }, [profile.displayName, profile.timezone, profile.aiInstructions]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearMutationError();
    setFeedback(null);

    const parsed = settingsSchema.safeParse({
      displayName,
      timezone,
      aiInstructions,
    });
    if (!parsed.success) {
      setErrors(extractFieldErrors<SettingsField>(parsed.error));
      return;
    }

    setErrors({});
    setIsSaving(true);
    try {
      const ok = await updateProfile({
        displayName: parsed.data.displayName,
        timezone: parsed.data.timezone,
        aiInstructions: parsed.data.aiInstructions?.trim() || null,
      });
      if (ok) {
        setFeedback('Paramètres du profil enregistrés.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-5">
        <PageHeader title="Paramètres" />
        <LoadingState message="Chargement…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-5">
        <PageHeader title="Paramètres" />
        <ErrorState message={error} onRetry={retry} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader title="Paramètres" />

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Profil et préférences</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                id="settings-display-name"
                label="Nom d’affichage"
                required
                error={errors.displayName}
              >
                <Input
                  id="settings-display-name"
                  value={displayName}
                  hasError={Boolean(errors.displayName)}
                  onChange={(e) => {
                    setDisplayName(e.target.value);
                    if (errors.displayName) {
                      setErrors((prev) => ({ ...prev, displayName: undefined }));
                    }
                  }}
                />
              </FormField>

              <FormField
                id="settings-timezone"
                label="Fuseau horaire"
                required
                error={errors.timezone}
              >
                <Select
                  id="settings-timezone"
                  value={timezone}
                  hasError={Boolean(errors.timezone)}
                  onChange={(e) => setTimezone(e.target.value)}
                >
                  {TIMEZONE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                  {!TIMEZONE_OPTIONS.some((opt) => opt.value === timezone) && (
                    <option value={timezone}>{timezone}</option>
                  )}
                </Select>
              </FormField>
            </div>

            <FormField
              id="settings-ai-instructions"
              label="Consignes pour le copilote IA"
              error={errors.aiInstructions}
            >
              <Textarea
                id="settings-ai-instructions"
                rows={3}
                value={aiInstructions}
                hasError={Boolean(errors.aiInstructions)}
                placeholder="Ex. Aller droit au but avec des exemples concrets."
                onChange={(e) => setAiInstructions(e.target.value)}
              />
            </FormField>

            <div className="flex justify-end pt-1">
              <Button type="submit" variant="primary" isLoading={isSaving}>
                Enregistrer les paramètres
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Apparence</CardTitle>
          <CardDescription>
            Choisissez le thème clair, sombre ou aligné sur votre système.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-zinc-600 dark:text-zinc-400">
            Le thème s’applique immédiatement et reste mémorisé sur cet appareil.
          </p>
          <ThemeSegmentedControl />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Connexions API &amp; Cloud</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs text-zinc-700 dark:text-zinc-300">
          <p>
            <strong>Backend FastAPI :</strong> <code>{env.VITE_API_BASE_URL}</code>
          </p>
          <p>
            <strong>Supabase Cloud :</strong> <code>{env.VITE_SUPABASE_URL}</code>
          </p>
          <p>
            <strong>Clé publique Supabase :</strong> <code>{env.VITE_SUPABASE_ANON_KEY}</code>
          </p>
          <div className="flex items-center gap-2 pt-1.5 text-zinc-500 dark:text-zinc-400">
            <Icon
              icon={ShieldCheckIcon}
              size={16}
              className="shrink-0 text-emerald-700 dark:text-emerald-400"
            />
            <p>Clés secrètes IA gérées uniquement côté serveur.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
