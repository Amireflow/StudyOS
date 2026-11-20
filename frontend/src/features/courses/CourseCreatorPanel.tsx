import { useState, type FormEvent } from 'react';
import {
  BookOpen01Icon,
  CheckmarkCircle02Icon,
  Mortarboard02Icon,
  Rocket01Icon,
  SparklesIcon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select, Textarea } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import type { CourseCreateInput, CoursePreviewInput } from '../../lib/coursesApi';
import type { CourseLanguage, CoursePreview } from '../../types/domain';

const PRESET_SUBJECTS = ['Python', 'TypeScript', 'React', 'SQL', 'Rust', 'Java'] as const;

interface CourseCreatorPanelProps {
  onPreview: (input: CoursePreviewInput) => Promise<CoursePreview | null>;
  onCreate: (input: CourseCreateInput) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
}

export function CourseCreatorPanel({
  onPreview,
  onCreate,
  onCancel,
  isSubmitting,
}: CourseCreatorPanelProps) {
  const [subject, setSubject] = useState('');
  const [title, setTitle] = useState('');
  const [language, setLanguage] = useState<CourseLanguage>('fr');
  const [totalLevels, setTotalLevels] = useState<number>(3);
  const [goal, setGoal] = useState('');
  const [linkSkill, setLinkSkill] = useState(true);
  const [preview, setPreview] = useState<CoursePreview | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handlePreviewClick = async () => {
    setLocalError(null);
    if (subject.trim().length < 2) {
      setLocalError('Indiquez d’abord un langage ou sujet (ex. Python, TypeScript, SQL).');
      return;
    }
    setIsPreviewLoading(true);
    try {
      const result = await onPreview({
        subject: subject.trim(),
        title: title.trim() || undefined,
        language,
        totalLevels,
        goal: goal.trim() || undefined,
      });
      if (result) {
        setPreview(result);
      }
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (subject.trim().length < 2) {
      setLocalError('Le langage ou sujet doit contenir au moins 2 caractères.');
      return;
    }
    await onCreate({
      subject: subject.trim(),
      title: title.trim() || undefined,
      language,
      totalLevels,
      goal: goal.trim() || undefined,
      linkSkill,
    });
  };

  return (
    <section
      aria-label="Créer un cours intelligent"
      className="rounded-2xl bg-white p-5 sm:p-6 dark:bg-zinc-900"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300">
            <Icon icon={Mortarboard02Icon} size={19} />
          </span>
          <h2 className="text-base font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Créer un cours structuré
          </h2>
        </div>
      </div>

      <form onSubmit={(e) => void handleSubmit(e)} className="mt-5 space-y-4">
        <div className="space-y-2">
          <FormField
            id="course-subject"
            label="Sujet ou langage"
            required
            error={localError ?? undefined}
          >
            <Input
              id="course-subject"
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value);
                setPreview(null);
              }}
              placeholder="Ex. Python, TypeScript, SQL, Rust…"
              maxLength={120}
            />
          </FormField>
          <div className="flex flex-wrap items-center gap-1.5" aria-label="Langages suggérés">
            <span className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">
              Suggestions :
            </span>
            {PRESET_SUBJECTS.map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => {
                  setSubject(preset);
                  setLocalError(null);
                  setPreview(null);
                }}
                className="rounded-lg bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-700 transition-colors hover:bg-teal-50 hover:text-teal-800 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-teal-950/60 dark:hover:text-teal-300 cursor-pointer"
              >
                {preset}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <FormField id="course-title" label="Titre personnalisé (optionnel)">
            <Input
              id="course-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Généré automatiquement si vide"
              maxLength={160}
            />
          </FormField>

          <FormField id="course-language" label="Langue du cours">
            <Select
              id="course-language"
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value as CourseLanguage);
                setPreview(null);
              }}
            >
              <option value="fr">Français</option>
              <option value="en">English</option>
              <option value="bilingual">Bilingue FR / EN</option>
            </Select>
          </FormField>

          <FormField id="course-levels" label="Nombre de niveaux">
            <Select
              id="course-levels"
              value={String(totalLevels)}
              onChange={(e) => {
                setTotalLevels(Number(e.target.value));
                setPreview(null);
              }}
            >
              <option value="2">2 niveaux</option>
              <option value="3">3 niveaux</option>
              <option value="4">4 niveaux</option>
              <option value="5">5 niveaux</option>
            </Select>
          </FormField>
        </div>

        <FormField id="course-goal" label="Objectif personnel (optionnel)">
          <Textarea
            id="course-goal"
            rows={2}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Ex. Automatiser mes scripts et réussir mes évaluations backend."
            maxLength={300}
          />
        </FormField>

        <label className="inline-flex cursor-pointer items-center gap-2.5 rounded-xl bg-zinc-50 px-3.5 py-2.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800/70 dark:text-zinc-300">
          <input
            id="course-link-skill"
            type="checkbox"
            checked={linkSkill}
            onChange={(e) => setLinkSkill(e.target.checked)}
            className="h-4 w-4 rounded accent-teal-600"
          />
          <span>Associer une compétence liée (0/5 au départ, évolue sur projets validés)</span>
        </label>

        <div className="flex flex-wrap items-center gap-2.5 pt-1">
          <Button
            type="button"
            variant="secondary"
            size="md"
            isLoading={isPreviewLoading}
            disabled={isSubmitting}
            onClick={() => void handlePreviewClick()}
          >
            <Icon icon={SparklesIcon} size={16} />
            Prévisualiser le plan
          </Button>
          <Button type="submit" variant="primary" size="md" isLoading={isSubmitting}>
            <Icon icon={Rocket01Icon} size={16} />
            Créer le cours complet
          </Button>
          <Button type="button" variant="ghost" size="md" onClick={onCancel}>
            Annuler
          </Button>
        </div>
      </form>

      {preview && (
        <div className="mt-6 space-y-4 rounded-2xl bg-zinc-50 p-4 sm:p-5 dark:bg-zinc-800/70">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {preview.title}
              </h3>
              <p className="mt-0.5 text-xs text-zinc-600 dark:text-zinc-400">
                {preview.description}
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              <Badge variant="primary">{preview.domain}</Badge>
              <Badge variant="neutral">{preview.totalLevels} niveaux</Badge>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2 rounded-xl bg-white p-3.5 dark:bg-zinc-900">
              <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                Programme des niveaux
              </p>
              <ul className="space-y-1.5 text-xs text-zinc-700 dark:text-zinc-300">
                {preview.levelsRoadmap.map((lv) => (
                  <li key={lv.levelNumber} className="flex items-start gap-2">
                    <Badge variant={lv.levelNumber === 1 ? 'success' : 'neutral'}>
                      Niv. {lv.levelNumber}
                    </Badge>
                    <div className="min-w-0">
                      <p className="font-medium text-zinc-900 dark:text-zinc-100">{lv.title}</p>
                      {lv.projectTitle && (
                        <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                          Projet : {lv.projectTitle}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div className="space-y-2 rounded-xl bg-white p-3.5 dark:bg-zinc-900">
              <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                Aperçu du Niveau 1 ({preview.firstLevelLessons.length} chapitres + projet)
              </p>
              <ul className="space-y-1 text-xs text-zinc-700 dark:text-zinc-300">
                {preview.firstLevelLessons.map((lesson) => (
                  <li key={lesson.position} className="flex items-center gap-1.5">
                    <Icon
                      icon={CheckmarkCircle02Icon}
                      size={13}
                      className="shrink-0 text-teal-600 dark:text-teal-400"
                    />
                    <span className="truncate">
                      Ch. {lesson.position} : {lesson.title}
                    </span>
                  </li>
                ))}
              </ul>
              <div className="rounded-lg bg-teal-50/75 px-3 py-2 text-xs text-teal-950 dark:bg-teal-950/40 dark:text-teal-100">
                <span className="inline-flex items-center gap-1.5 font-semibold">
                  <Icon icon={BookOpen01Icon} size={13} />
                  Projet Niveau 1 : {preview.firstLevelProjectTitle}
                </span>
                <p className="mt-0.5 text-[11px] opacity-90">
                  {preview.firstLevelResources.length} documentations & vidéos curées incluses.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
