import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AiChat02Icon,
  Cancel01Icon,
  CheckmarkCircle02Icon,
  SparklesIcon,
} from '@hugeicons/core-free-icons';
import { Button } from '../../components/ui/Button';
import { FormField, Input, Select } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import {
  fetchAiProviderConfigApi,
  fetchAiProviderModelsApi,
  updateAiProviderConfigApi,
} from '../../lib/aiApi';
import { ApiError } from '../../lib/api-client';
import { useAuth } from '../../state/AuthContext';
import type {
  AiProviderCatalogItem,
  AiProviderConfig,
  AiProviderKind,
  AiProviderModel,
} from '../../types/domain';

const DEFAULT_PROVIDER_CATALOG: AiProviderCatalogItem[] = [
  {
    id: 'river',
    label: 'River AI (console.river.ai)',
    consoleUrl: 'https://console.river.ai',
    defaultBaseUrl: 'https://api.river.ai/v1',
    requiresApiKey: true,
  },
  {
    id: 'local',
    label: 'Local (déterministe, sans clé API)',
    consoleUrl: null,
    defaultBaseUrl: '',
    requiresApiKey: false,
  },
  {
    id: 'openai_compatible',
    label: 'OpenAI / Compatible',
    consoleUrl: 'https://platform.openai.com',
    defaultBaseUrl: 'https://api.openai.com/v1',
    requiresApiKey: true,
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    consoleUrl: 'https://aistudio.google.com',
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    requiresApiKey: true,
  },
];

function defaultModelForProvider(provider: AiProviderKind): string {
  if (provider === 'local') return 'local-coach-v1';
  if (provider === 'gemini') return 'gemini-2.5-flash';
  return 'gpt-4o-mini';
}

function normalizeClientBaseUrl(provider: AiProviderKind, rawUrl: string): string {
  const trimmed = rawUrl.trim();
  if (provider === 'local') return '';
  const withScheme =
    trimmed && !trimmed.includes('://') ? `https://${trimmed}` : trimmed;

  if (provider === 'river') {
    if (!withScheme) return 'https://api.river.ai/v1';
    try {
      const parsed = new URL(withScheme);
      const host = parsed.hostname.toLowerCase();
      const path = parsed.pathname.replace(/\/+$/, '');
      if (host === 'console.river.ai' || host === 'river.ai' || host === 'www.river.ai') {
        return 'https://api.river.ai/v1';
      }
      if (host === 'api.river.ai' && (path === '' || path === '/')) {
        return 'https://api.river.ai/v1';
      }
    } catch {
      return withScheme.replace(/\/+$/, '');
    }
    return withScheme.replace(/\/+$/, '');
  }

  if (provider === 'gemini') {
    return (withScheme || 'https://generativelanguage.googleapis.com/v1beta').replace(/\/+$/, '');
  }

  return (withScheme || 'https://api.openai.com/v1').replace(/\/+$/, '');
}

async function fetchModelsDirectClient(
  provider: AiProviderKind,
  apiKey: string,
  baseUrl: string,
): Promise<{ baseUrl: string; models: AiProviderModel[] }> {
  if (provider === 'local') {
    return {
      baseUrl: '',
      models: [
        {
          id: 'local-coach-v1',
          label: 'Local Coach v1 (déterministe, hors-ligne)',
          ownedBy: 'study-os',
          contextWindow: null,
        },
      ],
    };
  }

  const trimmedKey = apiKey.trim();
  if (!trimmedKey) {
    throw new Error('Veuillez saisir une clé API pour récupérer les modèles disponibles.');
  }

  const resolvedUrl = normalizeClientBaseUrl(provider, baseUrl);
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(resolvedUrl);
  } catch {
    throw new Error('L’URL du fournisseur IA est invalide.');
  }
  const hostname = parsedUrl.hostname.toLowerCase();
  const isLoopback =
    hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]';
  const isPrivateIpv4 =
    /^10\./.test(hostname) ||
    /^192\.168\./.test(hostname) ||
    /^169\.254\./.test(hostname) ||
    /^127\./.test(hostname) ||
    /^0\./.test(hostname) ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname);
  const isForbiddenHost =
    isPrivateIpv4 ||
    hostname.endsWith('.local') ||
    hostname.endsWith('.internal') ||
    hostname === 'metadata.google.internal' ||
    hostname === '[::1]';

  if (isForbiddenHost && !(isLoopback && import.meta.env.DEV)) {
    throw new Error('Destination réseau privée ou interne interdite.');
  }
  if (parsedUrl.protocol !== 'https:' && !(parsedUrl.protocol === 'http:' && isLoopback && import.meta.env.DEV)) {
    throw new Error('L’URL du fournisseur IA doit utiliser HTTPS (ou http://localhost en développement local).');
  }

  const headers: Record<string, string> =
    provider === 'gemini'
      ? { 'x-goog-api-key': trimmedKey, Accept: 'application/json' }
      : { Authorization: `Bearer ${trimmedKey}`, Accept: 'application/json' };

  let response: Response;
  try {
    response = await fetch(`${resolvedUrl}/models`, { method: 'GET', headers });
  } catch {
    throw new Error(
      'Impossible de contacter le fournisseur directement depuis le navigateur (réseau ou CORS). Connectez le serveur backend API pour relayer la requête.',
    );
  }

  if (response.status === 401 || response.status === 403) {
    throw new Error(
      provider === 'river'
        ? 'Clé API refusée par River AI (console.river.ai). Vérifiez votre clé.'
        : 'Clé API refusée par le fournisseur IA.',
    );
  }
  if (!response.ok) {
    throw new Error(`Erreur HTTP ${response.status} lors de la récupération des modèles.`);
  }

  const payload = (await response.json()) as Record<string, unknown>;
  const seen = new Set<string>();
  const collected: AiProviderModel[] = [];

  if (provider === 'gemini') {
    const items = Array.isArray(payload.models) ? payload.models : [];
    for (const rawItem of items) {
      if (!rawItem || typeof rawItem !== 'object') continue;
      const item = rawItem as Record<string, unknown>;
      const methods = Array.isArray(item.supportedGenerationMethods)
        ? item.supportedGenerationMethods
        : null;
      if (methods && !methods.includes('generateContent')) continue;
      const rawName = typeof item.name === 'string' ? item.name.trim() : '';
      const id = rawName.replace(/^models\//, '').trim();
      if (!id || seen.has(id)) continue;
      seen.add(id);
      collected.push({
        id,
        label: (typeof item.displayName === 'string' && item.displayName.trim()) || id,
        ownedBy: 'google',
        contextWindow: typeof item.inputTokenLimit === 'number' ? item.inputTokenLimit : null,
      });
    }
  } else {
    const rawItems = Array.isArray(payload)
      ? payload
      : Array.isArray(payload.data)
        ? payload.data
        : Array.isArray(payload.models)
          ? payload.models
          : [];

    for (const rawItem of rawItems) {
      if (typeof rawItem === 'string') {
        const id = rawItem.trim();
        if (!id || seen.has(id)) continue;
        seen.add(id);
        collected.push({
          id,
          label: id,
          ownedBy: provider === 'river' ? 'river' : null,
          contextWindow: null,
        });
        continue;
      }
      if (!rawItem || typeof rawItem !== 'object') continue;
      const item = rawItem as Record<string, unknown>;
      const id =
        typeof item.id === 'string'
          ? item.id.trim()
          : typeof item.name === 'string'
            ? item.name.trim()
            : '';
      if (!id || seen.has(id)) continue;
      seen.add(id);
      const label =
        (typeof item.display_name === 'string' && item.display_name.trim()) ||
        (typeof item.label === 'string' && item.label.trim()) ||
        id;
      const ownedBy = typeof item.owned_by === 'string' && item.owned_by.trim() ? item.owned_by.trim() : null;
      const contextWindow =
        typeof item.context_window === 'number'
          ? item.context_window
          : typeof item.context_length === 'number'
            ? item.context_length
            : null;
      collected.push({ id, label, ownedBy, contextWindow });
    }
  }

  collected.sort((a, b) => a.id.localeCompare(b.id));
  return { baseUrl: resolvedUrl, models: collected };
}

export function AiProviderSettingsCard() {
  const { session } = useAuth();
  const isApiMode = session?.mode === 'api' && Boolean(session.accessToken);

  const [savedConfig, setSavedConfig] = useState<AiProviderConfig | null>(null);
  const [provider, setProvider] = useState<AiProviderKind>('local');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [selectedModel, setSelectedModel] = useState('local-coach-v1');
  const [models, setModels] = useState<AiProviderModel[]>([]);

  const [isLoadingConfig, setIsLoadingConfig] = useState(false);
  const [isFetchingModels, setIsFetchingModels] = useState(false);
  const [isSavingConfig, setIsSavingConfig] = useState(false);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const lastAutoFetchedSignatureRef = useRef<string>('');
  const fetchRequestIdRef = useRef<number>(0);

  const catalog = useMemo(
    () =>
      savedConfig?.availableProviders.length
        ? savedConfig.availableProviders
        : DEFAULT_PROVIDER_CATALOG,
    [savedConfig],
  );

  const selectedCatalogItem = useMemo(
    () => catalog.find((item) => item.id === provider) ?? DEFAULT_PROVIDER_CATALOG[0],
    [catalog, provider],
  );

  const hasSavedKeyForSelectedProvider = Boolean(
    isApiMode && savedConfig?.hasApiKey && savedConfig.provider === provider,
  );

  useEffect(() => {
    if (!isApiMode || !session?.accessToken) {
      return;
    }
    let cancelled = false;
    setIsLoadingConfig(true);
    fetchAiProviderConfigApi(session.accessToken)
      .then((cfg) => {
        if (cancelled) return;
        setSavedConfig(cfg);
        setProvider(cfg.provider ?? 'local');
        setBaseUrl(cfg.baseUrl ?? '');
        setSelectedModel(cfg.model || defaultModelForProvider(cfg.provider ?? 'local'));
      })
      .catch(() => {
        // Garde l'état local silencieux si la config distante est indisponible au montage.
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingConfig(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isApiMode, session?.accessToken]);

  const handleFetchModels = useCallback(
    async (explicitKey?: string) => {
      const keyToUse = (explicitKey ?? apiKeyInput).trim();
      if (provider !== 'local' && !keyToUse && !hasSavedKeyForSelectedProvider) {
        setErrorMessage('Veuillez saisir une clé API pour récupérer les modèles disponibles.');
        return;
      }

      const requestId = ++fetchRequestIdRef.current;
      setIsFetchingModels(true);
      setErrorMessage(null);

      try {
        let result: { baseUrl: string; models: AiProviderModel[] };
        if (isApiMode && session?.accessToken) {
          const apiRes = await fetchAiProviderModelsApi(session.accessToken, {
            provider,
            apiKey: keyToUse || null,
            baseUrl: baseUrl.trim() || null,
          });
          result = { baseUrl: apiRes.baseUrl, models: apiRes.models };
        } else {
          result = await fetchModelsDirectClient(provider, keyToUse, baseUrl);
        }

        if (requestId !== fetchRequestIdRef.current) return;

        setModels(result.models);
        if (result.baseUrl) {
          setBaseUrl(result.baseUrl);
        }

        if (result.models.length > 0) {
          const alreadyValid = result.models.some((m) => m.id === selectedModel);
          if (!alreadyValid) {
            setSelectedModel(result.models[0].id);
          }
          setStatusMessage(
            `${result.models.length} modèle(s) disponible(s) récupéré(s) pour ${selectedCatalogItem.label}.`,
          );
        } else {
          setStatusMessage('Aucun modèle retourné par le fournisseur.');
        }
      } catch (err) {
        if (requestId !== fetchRequestIdRef.current) return;
        const message =
          err instanceof ApiError || err instanceof Error
            ? err.message
            : 'Impossible de récupérer les modèles disponibles.';
        setErrorMessage(message);
      } finally {
        if (requestId === fetchRequestIdRef.current) {
          setIsFetchingModels(false);
        }
      }
    },
    [
      apiKeyInput,
      baseUrl,
      hasSavedKeyForSelectedProvider,
      isApiMode,
      provider,
      selectedCatalogItem.label,
      selectedModel,
      session?.accessToken,
    ],
  );

  // Déclenchement automatique lors de la saisie/collage d'une clé API.
  useEffect(() => {
    const trimmedKey = apiKeyInput.trim();
    if (provider === 'local' || trimmedKey.length < 8) {
      return;
    }
    const normalizedUrl = normalizeClientBaseUrl(provider, baseUrl);
    const signature = `${provider}|${normalizedUrl}|${trimmedKey}`;
    if (lastAutoFetchedSignatureRef.current === signature) {
      return;
    }

    const timer = window.setTimeout(() => {
      lastAutoFetchedSignatureRef.current = signature;
      void handleFetchModels(trimmedKey);
    }, 600);

    return () => {
      window.clearTimeout(timer);
    };
  }, [apiKeyInput, baseUrl, handleFetchModels, provider]);

  const handleProviderChange = (nextProvider: AiProviderKind) => {
    const item = catalog.find((entry) => entry.id === nextProvider);
    setProvider(nextProvider);
    setBaseUrl(item?.defaultBaseUrl ?? '');
    setSelectedModel(defaultModelForProvider(nextProvider));
    setModels([]);
    setApiKeyInput('');
    setErrorMessage(null);
    setStatusMessage(null);
    lastAutoFetchedSignatureRef.current = '';
  };

  const handleSaveProviderConfig = async () => {
    setErrorMessage(null);
    setStatusMessage(null);

    const trimmedKey = apiKeyInput.trim();
    if (provider !== 'local' && !trimmedKey && !hasSavedKeyForSelectedProvider) {
      setErrorMessage('Veuillez saisir une clé API valide avant d’enregistrer.');
      return;
    }

    if (!isApiMode || !session?.accessToken) {
      setStatusMessage(
        provider === 'local'
          ? 'Mode local actif : le copilote utilise le moteur déterministe hors-ligne.'
          : `Modèle « ${selectedModel} » sélectionné pour ${selectedCatalogItem.label}. Connectez-vous au serveur API pour enregistrer la clé côté serveur.`,
      );
      return;
    }

    setIsSavingConfig(true);
    try {
      const updated = await updateAiProviderConfigApi(session.accessToken, {
        provider,
        baseUrl: baseUrl.trim() || null,
        model: selectedModel.trim() || null,
        apiKey: trimmedKey || null,
      });
      setSavedConfig(updated);
      setProvider(updated.provider);
      setBaseUrl(updated.baseUrl);
      setSelectedModel(updated.model);
      setApiKeyInput('');
      lastAutoFetchedSignatureRef.current = '';
      setStatusMessage(
        `Fournisseur IA enregistré : ${selectedCatalogItem.label} (${updated.model}).`,
      );
    } catch (err) {
      const message =
        err instanceof ApiError || err instanceof Error
          ? err.message
          : 'Impossible d’enregistrer la configuration IA.';
      setErrorMessage(message);
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleClearApiKey = async () => {
    if (!isApiMode || !session?.accessToken) {
      setApiKeyInput('');
      setModels([]);
      setProvider('local');
      setBaseUrl('');
      setSelectedModel('local-coach-v1');
      return;
    }

    setIsSavingConfig(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const updated = await updateAiProviderConfigApi(session.accessToken, {
        provider: 'local',
        model: 'local-coach-v1',
        clearApiKey: true,
      });
      setSavedConfig(updated);
      setProvider(updated.provider);
      setBaseUrl(updated.baseUrl);
      setSelectedModel(updated.model);
      setApiKeyInput('');
      setModels([]);
      lastAutoFetchedSignatureRef.current = '';
      setStatusMessage('Clé API supprimée côté serveur. Repli sur le moteur local.');
    } catch (err) {
      const message =
        err instanceof ApiError || err instanceof Error
          ? err.message
          : 'Impossible de supprimer la clé API.';
      setErrorMessage(message);
    } finally {
      setIsSavingConfig(false);
    }
  };

  const modelOptions = useMemo(() => {
    const items = [...models];
    if (selectedModel && !items.some((m) => m.id === selectedModel)) {
      items.unshift({
        id: selectedModel,
        label: selectedModel,
        ownedBy: null,
        contextWindow: null,
      });
    }
    return items;
  }, [models, selectedModel]);

  return (
    <section
      aria-label="Fournisseur IA et modèles"
      className="space-y-4 rounded-2xl bg-white p-5 dark:bg-zinc-900"
    >
      <div className="flex items-center gap-2">
        <Icon icon={AiChat02Icon} size={17} className="text-teal-700 dark:text-teal-400" />
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
          Fournisseur IA & Modèles
        </h2>
      </div>

      {statusMessage && (
        <div
          role="status"
          className="flex items-center justify-between gap-2 rounded-xl bg-emerald-50/90 px-3.5 py-2.5 text-xs font-medium text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200"
        >
          <span>{statusMessage}</span>
          <button
            type="button"
            onClick={() => setStatusMessage(null)}
            aria-label="Fermer le message fournisseur IA"
            className="rounded p-0.5 hover:bg-emerald-100 dark:hover:bg-emerald-900"
          >
            <Icon icon={Cancel01Icon} size={13} />
          </button>
        </div>
      )}

      {errorMessage && (
        <div
          role="alert"
          className="flex items-center justify-between gap-2 rounded-xl bg-rose-50/90 px-3.5 py-2.5 text-xs font-medium text-rose-900 dark:bg-rose-950/50 dark:text-rose-200"
        >
          <span>{errorMessage}</span>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            aria-label="Fermer l’erreur fournisseur IA"
            className="rounded p-0.5 hover:bg-rose-100 dark:hover:bg-rose-900"
          >
            <Icon icon={Cancel01Icon} size={13} />
          </button>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField id="ai-provider-select" label="Fournisseur IA">
          <Select
            id="ai-provider-select"
            value={provider}
            disabled={isLoadingConfig}
            onChange={(e) => handleProviderChange(e.target.value as AiProviderKind)}
          >
            {catalog.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </Select>
          {selectedCatalogItem.consoleUrl && (
            <p className="pt-1 text-xs text-zinc-500 dark:text-zinc-400">
              <a
                href={selectedCatalogItem.consoleUrl}
                target="_blank"
                rel="noreferrer"
                className="font-medium text-teal-700 underline hover:text-teal-800 dark:text-teal-400"
              >
                {selectedCatalogItem.consoleUrl.replace(/^https?:\/\//, '')}
              </a>
            </p>
          )}
        </FormField>

        <FormField id="ai-provider-base-url" label="URL de base API">
          <Input
            id="ai-provider-base-url"
            value={baseUrl}
            disabled={provider === 'local'}
            placeholder={
              provider === 'local'
                ? 'Mode local'
                : selectedCatalogItem.defaultBaseUrl
            }
            onChange={(e) => {
              setBaseUrl(e.target.value);
              lastAutoFetchedSignatureRef.current = '';
            }}
          />
        </FormField>
      </div>

      {provider !== 'local' && (
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField id="ai-provider-api-key" label="Clé API du fournisseur">
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                id="ai-provider-api-key"
                type="password"
                autoComplete="off"
                value={apiKeyInput}
                placeholder={
                  hasSavedKeyForSelectedProvider && savedConfig?.apiKeyPreview
                    ? `Clé active (${savedConfig.apiKeyPreview})`
                    : provider === 'river'
                      ? 'Clé API River AI'
                      : 'Clé API'
                }
                onChange={(e) => {
                  setApiKeyInput(e.target.value);
                  setErrorMessage(null);
                }}
              />
              <Button
                type="button"
                variant="secondary"
                isLoading={isFetchingModels}
                onClick={() => void handleFetchModels()}
                className="shrink-0"
              >
                <Icon icon={SparklesIcon} size={14} />
                Récupérer les modèles
              </Button>
            </div>
          </FormField>

          <FormField
            id="ai-provider-model"
            label={
              models.length > 0
                ? `Modèle disponible (${models.length})`
                : 'Modèle actif'
            }
          >
            <Select
              id="ai-provider-model"
              value={selectedModel}
              disabled={isFetchingModels || modelOptions.length === 0}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {modelOptions.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label !== m.id ? `${m.label} (${m.id})` : m.id}
                  {m.ownedBy ? ` · ${m.ownedBy}` : ''}
                </option>
              ))}
            </Select>
          </FormField>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
        {savedConfig?.hasApiKey && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={isSavingConfig}
            onClick={() => void handleClearApiKey()}
          >
            Supprimer la clé
          </Button>
        )}
        <Button
          type="button"
          variant="primary"
          isLoading={isSavingConfig}
          onClick={() => void handleSaveProviderConfig()}
        >
          <Icon icon={CheckmarkCircle02Icon} size={15} />
          Enregistrer le fournisseur IA
        </Button>
      </div>
    </section>
  );
}
