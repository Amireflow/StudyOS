/**
 * Couche de persistance locale (localStorage) utilisée aux Lots 2 et 3
 * avant le branchement à l'API PostgreSQL au Lot 5.
 */

export const STORAGE_KEYS = {
  studyState: 'amireflow.studyOs.v1.state',
  learningState: 'amireflow.studyOs.v1.learning',
  aiState: 'amireflow.studyOs.v1.ai',
  authSession: 'amireflow.studyOs.v1.session',
  theme: 'amireflow.studyOs.v1.theme',
} as const;

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
