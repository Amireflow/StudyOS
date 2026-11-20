import { useMemo, useState, type FormEvent } from 'react';
import {
  Add01Icon,
  BookOpen02Icon,
  CodeIcon,
  File02Icon,
  LinkSquare02Icon,
  Video01Icon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, InlineConfirm, Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { EmptyState } from '../../components/ui/StateFeedback';
import type { CourseResourceInput } from '../../lib/coursesApi';
import type { CourseResource, CourseResourceType } from '../../types/domain';

type ResourceFilter = 'all' | 'documentation' | 'video' | 'practice';

const RESOURCE_FILTERS: Array<{ value: ResourceFilter; label: string }> = [
  { value: 'all', label: 'Toutes' },
  { value: 'documentation', label: 'Documentation' },
  { value: 'video', label: 'Vidéos' },
  { value: 'practice', label: 'Pratique' },
];

const TYPE_META: Record<
  CourseResourceType,
  { label: string; icon: typeof BookOpen02Icon }
> = {
  documentation: { label: 'Documentation', icon: BookOpen02Icon },
  video: { label: 'Vidéo', icon: Video01Icon },
  article: { label: 'Article', icon: File02Icon },
  interactive: { label: 'Interactif', icon: CodeIcon },
  book: { label: 'Livre / Guide', icon: BookOpen02Icon },
};

interface CourseResourcesPanelProps {
  resources: CourseResource[];
  activeLevelId: string;
  onAddResource: (input: CourseResourceInput) => Promise<CourseResource | null>;
  onDeleteResource: (resourceId: string) => Promise<boolean>;
}

export function CourseResourcesPanel({
  resources,
  activeLevelId,
  onAddResource,
  onDeleteResource,
}: CourseResourcesPanelProps) {
  const [filter, setFilter] = useState<ResourceFilter>('all');
  const [isFormOpen, setIsFormOpen] = useState(false);

  const [title, setTitle] = useState('');
  const [url, setUrl] = useState('');
  const [resourceType, setResourceType] = useState<CourseResourceType>('documentation');
  const [language, setLanguage] = useState<'fr' | 'en'>('fr');
  const [sourceName, setSourceName] = useState('');
  const [notes, setNotes] = useState('');
  const [isOfficial, setIsOfficial] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const uniqueResources = useMemo(() => {
    const map = new Map<string, CourseResource>();
    for (const r of resources) {
      const key = r.url.trim().toLowerCase() || r.id;
      if (!map.has(key)) {
        map.set(key, r);
      }
    }
    return Array.from(map.values());
  }, [resources]);

  const filteredResources = useMemo(() => {
    return uniqueResources.filter((r) => {
      if (filter === 'all') return true;
      if (filter === 'documentation') {
        return (
          r.resourceType === 'documentation' ||
          r.resourceType === 'article' ||
          r.resourceType === 'book'
        );
      }
      if (filter === 'video') return r.resourceType === 'video';
      return r.resourceType === 'interactive';
    });
  }, [filter, uniqueResources]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (title.trim().length < 2) {
      setFormError('Le titre doit contenir au moins 2 caractères.');
      return;
    }
    if (!/^https?:\/\/\S+$/i.test(url.trim())) {
      setFormError('L’URL doit commencer par http:// ou https://.');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await onAddResource({
        title: title.trim(),
        url: url.trim(),
        resourceType,
        language,
        isOfficial,
        sourceName: sourceName.trim() || undefined,
        notes: notes.trim() || undefined,
        levelId: activeLevelId,
      });
      if (created) {
        setTitle('');
        setUrl('');
        setSourceName('');
        setNotes('');
        setIsOfficial(false);
        setIsFormOpen(false);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-2xl bg-white p-4 sm:p-5 dark:bg-zinc-900">
        <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filtrer les ressources">
          {RESOURCE_FILTERS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              aria-pressed={filter === opt.value}
              onClick={() => setFilter(opt.value)}
              className={
                filter === opt.value
                  ? 'rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white dark:bg-zinc-100 dark:text-zinc-950 cursor-pointer'
                  : 'rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 cursor-pointer'
              }
            >
              {opt.label}
            </button>
          ))}
        </div>

        <Button
          type="button"
          variant={isFormOpen ? 'secondary' : 'primary'}
          size="sm"
          onClick={() => setIsFormOpen((open) => !open)}
        >
          <Icon icon={Add01Icon} size={15} />
          {isFormOpen ? 'Fermer le formulaire' : 'Ajouter une ressource'}
        </Button>
      </div>

      {isFormOpen && (
        <form
          onSubmit={(e) => void handleSubmit(e)}
          className="space-y-4 rounded-2xl bg-white p-5 dark:bg-zinc-900"
        >
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Ajouter une documentation ou vidéo
          </h3>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="resource-title"
              label="Titre de la ressource"
              required
              error={formError ?? undefined}
            >
              <Input
                id="resource-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex. Guide AsyncIO officiel"
              />
            </FormField>

            <FormField id="resource-url" label="URL (http/https)" required>
              <Input
                id="resource-url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://docs.python.org/3/library/asyncio.html"
              />
            </FormField>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <FormField id="resource-type" label="Type">
              <Select
                id="resource-type"
                value={resourceType}
                onChange={(e) => setResourceType(e.target.value as CourseResourceType)}
              >
                <option value="documentation">Documentation</option>
                <option value="video">Vidéo</option>
                <option value="interactive">Atelier interactif</option>
                <option value="article">Article</option>
                <option value="book">Livre / Guide</option>
              </Select>
            </FormField>

            <FormField id="resource-language" label="Langue">
              <Select
                id="resource-language"
                value={language}
                onChange={(e) => setLanguage(e.target.value as 'fr' | 'en')}
              >
                <option value="fr">Français</option>
                <option value="en">Anglais</option>
              </Select>
            </FormField>

            <FormField id="resource-source" label="Éditeur / chaîne">
              <Input
                id="resource-source"
                value={sourceName}
                onChange={(e) => setSourceName(e.target.value)}
                placeholder="Ex. Python Docs, MDN, Grafikart"
              />
            </FormField>
          </div>

          <FormField id="resource-notes" label="Notes d’usage (optionnel)">
            <Input
              id="resource-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Quand consulter cette ressource dans le niveau…"
            />
          </FormField>

          <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
            <input
              id="resource-official"
              type="checkbox"
              checked={isOfficial}
              onChange={(e) => setIsOfficial(e.target.checked)}
              className="h-4 w-4 rounded accent-teal-600"
            />
            <span>Source officielle</span>
          </label>

          <div className="flex items-center gap-2">
            <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
              Enregistrer la ressource
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsFormOpen(false)}
            >
              Annuler
            </Button>
          </div>
        </form>
      )}

      {filteredResources.length === 0 ? (
        <EmptyState
          title="Aucune ressource dans ce filtre"
          description="Ajoutez une documentation officielle ou sélectionnez un autre filtre."
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {filteredResources.map((res) => {
            const meta = TYPE_META[res.resourceType] ?? TYPE_META.documentation;
            return (
              <article
                key={res.id}
                className="flex flex-col justify-between gap-3 rounded-2xl bg-white p-4 dark:bg-zinc-900"
              >
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-700 dark:text-teal-400">
                      <Icon icon={meta.icon} size={15} />
                      {meta.label}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {res.isOfficial && <Badge variant="primary">Officiel</Badge>}
                      <Badge variant="neutral">{res.language.toUpperCase()}</Badge>
                    </div>
                  </div>

                  <div>
                    <h4 className="line-clamp-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {res.title}
                    </h4>
                    {res.sourceName && (
                      <p className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">
                        {res.sourceName}
                      </p>
                    )}
                    {res.notes && (
                      <p className="mt-1 line-clamp-2 text-xs text-zinc-600 dark:text-zinc-400">
                        {res.notes}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between gap-2 pt-1">
                  <a
                    href={res.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-800 transition-colors hover:bg-teal-50 hover:text-teal-800 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-teal-950/60 dark:hover:text-teal-300"
                  >
                    <Icon icon={LinkSquare02Icon} size={13} />
                    Ouvrir
                  </a>

                  <InlineConfirm
                    triggerLabel="Supprimer"
                    confirmLabel="Confirmer"
                    ariaLabel={`Supprimer la ressource ${res.title}`}
                    onConfirm={() => void onDeleteResource(res.id)}
                  />
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
