import { useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  AiChat02Icon,
  Award02Icon,
  BookOpen01Icon,
  Calendar03Icon,
  CheckmarkCircle02Icon,
  CheckmarkSquare02Icon,
  Clock01Icon,
  FolderKanbanIcon,
  Settings02Icon,
  SparklesIcon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';
import { z } from 'zod';
import { PageHeader } from '../../components/layout/PageHeader';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, InlineConfirm, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import {
  ErrorState,
  LoadingState,
  SuccessBanner,
} from '../../components/ui/StateFeedback';
import { ThemeSegmentedControl } from '../../components/ui/ThemeToggle';
import { cn } from '../../lib/cn';
import { formatTimeInTimezone } from '../../lib/date';
import { env } from '../../lib/env';
import { extractFieldErrors } from '../../lib/validation';
import { useAuth } from '../../state/AuthContext';
import { useLearningStore } from '../../state/LearningStoreContext';
import { useStudyStore } from '../../state/StudyStoreContext';
import { AccountSecurityCard } from './AccountSecurityCard';
import { AiProviderSettingsCard } from './AiProviderSettingsCard';

const TIMEZONE_OPTIONS = [
  { value: 'Africa/Dakar', label: 'Africa/Dakar (UTC+0)' },
  { value: 'Europe/Paris', label: 'Europe/Paris (UTC+1 / UTC+2)' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Africa/Casablanca', label: 'Africa/Casablanca' },
  { value: 'America/Montreal', label: 'America/Montreal' },
  { value: 'America/New_York', label: 'America/New_York' },
] as const;

const QUICK_TIMEZONES = ['Africa/Dakar', 'Europe/Paris', 'UTC'] as const;

const AI_STYLE_PRESETS: Array<{ label: string; text: string }> = [
  {
    label: 'Concis',
    text: 'Aller droit au but avec des actions concrètes et mesurables.',
  },
  {
    label: 'Pédagogique',
    text: 'Expliquer étape par étape avec des exemples concrets de code Python et TypeScript.',
  },
  {
    label: 'Examen',
    text: 'Prioriser les échéances proches, les exercices pratiques et les bilans synthétiques.',
  },
];

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

function getInitials(name: string): string {
  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) return 'U';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

export function SettingsPage() {
  const { session } = useAuth();
  const {
    profile,
    dataMode,
    tasks,
    sessions,
    scheduleEvents,
    isLoading,
    error,
    mutationError,
    clearMutationError,
    retry,
    updateProfile,
    loadDemoData,
    clearAllData,
  } = useStudyStore();
  const { paths, skills, projects } = useLearningStore();

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

  const isDirty = useMemo(() => {
    const savedInstructions = profile.aiInstructions ?? '';
    return (
      displayName.trim() !== profile.displayName.trim() ||
      timezone !== profile.timezone ||
      aiInstructions.trim() !== savedInstructions.trim()
    );
  }, [displayName, timezone, aiInstructions, profile]);

  const localTimePreview = useMemo(() => {
    try {
      return formatTimeInTimezone(new Date().toISOString(), timezone);
    } catch {
      return '';
    }
  }, [timezone]);

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

  const handleLoadDemoData = () => {
    loadDemoData();
    setFeedback('Données de démonstration chargées dans l’espace de travail.');
  };

  const handleClearLocalData = () => {
    clearAllData();
    setFeedback('Données locales réinitialisées.');
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

  const workspaceStats = [
    { label: 'Tâches', count: tasks.length, icon: CheckmarkSquare02Icon },
    { label: 'Séances', count: sessions.length, icon: Timer02Icon },
    { label: 'Créneaux', count: scheduleEvents.length, icon: Calendar03Icon },
    { label: 'Parcours', count: paths.length, icon: BookOpen01Icon },
    { label: 'Compétences', count: skills.length, icon: Award02Icon },
    { label: 'Projets', count: projects.length, icon: FolderKanbanIcon },
  ];

  return (
    <div className="space-y-3.5 sm:space-y-5">
      <PageHeader title="Paramètres" />

      {feedback && <SuccessBanner message={feedback} onDismiss={() => setFeedback(null)} />}
      {mutationError && (
        <ErrorState message={mutationError} onRetry={clearMutationError} retryLabel="Fermer" />
      )}

      {/* Bandeau d'identité & état de la session */}
      <section
        aria-label="Identité et session active"
        className="flex flex-col gap-3 rounded-2xl bg-white p-4 sm:flex-row sm:items-center sm:justify-between dark:bg-zinc-900"
      >
        <div className="flex min-w-0 items-center gap-3">
          <div
            aria-hidden="true"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-teal-700 text-sm font-semibold text-white dark:bg-teal-500 dark:text-zinc-950"
          >
            {getInitials(displayName || profile.displayName)}
          </div>
          <div className="min-w-0 space-y-0.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-base font-semibold text-zinc-900 dark:text-zinc-50">
                {profile.displayName}
              </h2>
              {isDirty ? (
                <Badge variant="warning">Non enregistré</Badge>
              ) : (
                <Badge variant="success">Profil à jour</Badge>
              )}
            </div>
            <p className="truncate text-xs text-zinc-500 dark:text-zinc-400">
              {session?.email ?? 'Session locale'} · {timezone}
            </p>
          </div>
        </div>

        {localTimePreview && (
          <span className="inline-flex shrink-0 items-center gap-1.5 self-start rounded-xl bg-zinc-100 px-2.5 py-1 text-xs font-medium tabular-nums text-zinc-600 sm:self-center dark:bg-zinc-800 dark:text-zinc-300">
            <Icon icon={Clock01Icon} size={13} />
            {localTimePreview}
          </span>
        )}
      </section>

      {/* Formulaire Profil, Fuseau horaire & Consignes Copilote IA */}
      <section
        aria-label="Profil et préférences"
        className="space-y-4 rounded-2xl bg-white p-5 dark:bg-zinc-900"
      >
        <div className="flex items-center gap-2">
          <Icon icon={Settings02Icon} size={17} className="text-teal-700 dark:text-teal-400" />
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
            Profil et préférences
          </h2>
        </div>

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
                placeholder="Ex. Khadim"
                onChange={(e) => {
                  setDisplayName(e.target.value);
                  if (errors.displayName) {
                    setErrors((prev) => ({ ...prev, displayName: undefined }));
                  }
                }}
              />
            </FormField>

            <div className="space-y-2">
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

              <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0">
                {QUICK_TIMEZONES.map((tz) => (
                  <button
                    key={tz}
                    type="button"
                    onClick={() => setTimezone(tz)}
                    className={cn(
                      'shrink-0 rounded-lg px-2 py-0.5 text-[11px] font-medium transition-colors',
                      timezone === tz
                        ? 'bg-teal-700 text-white dark:bg-teal-500 dark:text-zinc-950'
                        : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200/80 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
                    )}
                  >
                    {tz}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="no-scrollbar flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto pb-0.5 sm:flex-wrap sm:overflow-visible sm:pb-0">
                <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-zinc-500 dark:text-zinc-400">
                  <Icon icon={AiChat02Icon} size={13} className="text-teal-700 dark:text-teal-400" />
                  Style :
                </span>
                {AI_STYLE_PRESETS.map((preset) => {
                  const isSelected = aiInstructions.trim() === preset.text;
                  return (
                    <button
                      key={preset.label}
                      type="button"
                      onClick={() => setAiInstructions(preset.text)}
                      className={cn(
                        'inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-0.5 text-[11px] font-medium transition-colors',
                        isSelected
                          ? 'bg-teal-700 text-white dark:bg-teal-500 dark:text-zinc-950'
                          : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200/80 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700',
                      )}
                    >
                      <Icon icon={SparklesIcon} size={11} />
                      {preset.label}
                    </button>
                  );
                })}
                {aiInstructions.trim().length > 0 && (
                  <button
                    type="button"
                    onClick={() => setAiInstructions('')}
                    className="shrink-0 rounded-lg bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500 transition-colors hover:bg-zinc-200/80 dark:bg-zinc-800 dark:text-zinc-400"
                  >
                    Effacer
                  </button>
                )}
              </div>
              <span className="shrink-0 text-[11px] tabular-nums text-zinc-400 dark:text-zinc-500">
                {aiInstructions.length}/2000
              </span>
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
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
            {isDirty && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setDisplayName(profile.displayName);
                  setTimezone(profile.timezone);
                  setAiInstructions(profile.aiInstructions ?? '');
                  setErrors({});
                }}
              >
                Rétablir
              </Button>
            )}
            <Button type="submit" variant="primary" isLoading={isSaving}>
              <Icon icon={CheckmarkCircle02Icon} size={15} />
              Enregistrer les paramètres
            </Button>
          </div>
        </form>
      </section>

      {/* Configuration fournisseur IA & récupération dynamique des modèles */}
      <AiProviderSettingsCard />

      {/* Compte & sécurité (affiché uniquement en session API authentifiée) */}
      <AccountSecurityCard />

      {/* Grille inférieure : Apparence & Espace de travail */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Apparence (épurée sans surcharge textuelle) */}
        <section
          aria-label="Apparence"
          className="flex flex-col justify-between gap-3 rounded-2xl bg-white p-5 sm:flex-row sm:items-center dark:bg-zinc-900"
        >
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">Apparence</h2>
          <ThemeSegmentedControl />
        </section>

        {/* Données & Espace de travail */}
        <section
          aria-label="Données et espace de travail"
          className="space-y-3 rounded-2xl bg-white p-5 dark:bg-zinc-900"
        >
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
              Espace de travail
            </h2>
            {dataMode === 'local_demo' && (
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleLoadDemoData}
                >
                  Charger des exemples
                </Button>
                <InlineConfirm
                  triggerLabel="Réinitialiser"
                  ariaLabel="Réinitialiser toutes les données locales"
                  onConfirm={handleClearLocalData}
                />
              </div>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
            {workspaceStats.map((item) => (
              <div
                key={item.label}
                className="rounded-xl bg-zinc-50/90 p-2.5 dark:bg-zinc-800/60"
              >
                <div className="flex items-center gap-1 text-zinc-500 dark:text-zinc-400">
                  <Icon icon={item.icon} size={12} />
                  <span className="truncate text-[11px] font-medium">{item.label}</span>
                </div>
                <p className="mt-1 text-base font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
                  {item.count}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Connexions API & Cloud */}
      <section
        aria-label="Connexions API & Cloud"
        className="space-y-3 rounded-2xl bg-white p-5 dark:bg-zinc-900"
      >
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
          Connexions
        </h2>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl bg-zinc-50/90 p-3 dark:bg-zinc-800/60">
            <p className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">API</p>
            <p className="mt-0.5 truncate font-mono text-xs text-zinc-800 dark:text-zinc-200">
              {env.VITE_API_BASE_URL}
            </p>
          </div>

          <div className="rounded-xl bg-zinc-50/90 p-3 dark:bg-zinc-800/60">
            <p className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">Supabase</p>
            <p className="mt-0.5 truncate font-mono text-xs text-zinc-800 dark:text-zinc-200">
              {env.VITE_SUPABASE_URL}
            </p>
          </div>

          <div className="rounded-xl bg-zinc-50/90 p-3 dark:bg-zinc-800/60">
            <p className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">
              Clé publique
            </p>
            <p className="mt-0.5 truncate font-mono text-xs text-zinc-800 dark:text-zinc-200">
              {env.VITE_SUPABASE_ANON_KEY}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
