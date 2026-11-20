/**
 * Stockage technique minimal côté navigateur (thème d'affichage et indicateur
 * de session API HTTP-only). Aucune donnée métier n'est stockée localement.
 */

export const STORAGE_KEYS = {
  apiSessionHint: 'amireflow.studyos.api_session_hint',
  theme: 'amireflow.studyOs.v1.theme',
} as const;

export const LEGACY_LOCAL_DATA_KEYS = [
  'amireflow.studyOs.v1.state',
  'amireflow.studyOs.v1.learning',
  'amireflow.studyOs.v1.courses',
  'amireflow.study_os.objectives.v1',
  'amireflow.studyOs.v1.ai',
  'amireflow.studyOs.v1.session',
] as const;

export function purgeLegacyLocalBusinessStorage(): void {
  try {
    for (const key of LEGACY_LOCAL_DATA_KEYS) {
      window.localStorage.removeItem(key);
    }
  } catch {
    // Ignore les erreurs de stockage en navigation privée stricte.
  }
}

export function readFromStorage<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function writeToStorage<T>(key: string, value: T): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore les erreurs de quota ou de stockage indisponible (ex. navigation privée stricte).
  }
}

export function generateId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
