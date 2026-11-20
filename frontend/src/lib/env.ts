import { z } from 'zod';

export const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';
export const DEFAULT_SUPABASE_URL = 'https://rzjjcqmsepxtpmqwzwmf.supabase.co';
export const DEFAULT_SUPABASE_ANON_KEY = 'sb_publishable_hGTCEH3pCjQcY_M-t3snyA_FvUSCBac';

const BARE_HOST_PATTERN = /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(:\d+)?(\/.*)?$/;

/**
 * Normalise VITE_API_BASE_URL (ex. domaine Render nu, racine HTTPS sans /api/v1, slash final ou chemin relatif).
 */
export function normalizeApiBaseUrl(raw?: string): string {
  const trimmed = raw?.trim() ?? '';
  if (!trimmed) {
    return DEFAULT_API_BASE_URL;
  }

  if (trimmed.startsWith('/')) {
    const cleaned = trimmed.replace(/\/+$/, '');
    return cleaned || '/api/v1';
  }

  const candidate =
    !/^[a-zA-Z][a-zA-Z\d+.-]*:\/\//.test(trimmed) && BARE_HOST_PATTERN.test(trimmed)
      ? `https://${trimmed}`
      : trimmed;

  try {
    const parsed = new URL(candidate);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return DEFAULT_API_BASE_URL;
    }
    const cleanedPath = parsed.pathname.replace(/\/+$/, '');
    const normalizedPath = !cleanedPath || cleanedPath === '/' ? '/api/v1' : cleanedPath;
    return `${parsed.origin}${normalizedPath}`;
  } catch {
    return DEFAULT_API_BASE_URL;
  }
}

const envSchema = z.object({
  VITE_API_BASE_URL: z.string().min(1).default(DEFAULT_API_BASE_URL),
  VITE_SUPABASE_URL: z.string().default(DEFAULT_SUPABASE_URL),
  VITE_SUPABASE_ANON_KEY: z.string().default(DEFAULT_SUPABASE_ANON_KEY),
});

const rawSupabaseUrl = (import.meta.env.VITE_SUPABASE_URL || DEFAULT_SUPABASE_URL)
  .trim()
  .replace(/\/+$/, '');

const parsedEnv = envSchema.safeParse({
  VITE_API_BASE_URL: normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL),
  VITE_SUPABASE_URL: rawSupabaseUrl || DEFAULT_SUPABASE_URL,
  VITE_SUPABASE_ANON_KEY:
    (import.meta.env.VITE_SUPABASE_ANON_KEY || DEFAULT_SUPABASE_ANON_KEY).trim() ||
    DEFAULT_SUPABASE_ANON_KEY,
});

export const env = parsedEnv.success
  ? parsedEnv.data
  : {
      VITE_API_BASE_URL: DEFAULT_API_BASE_URL,
      VITE_SUPABASE_URL: DEFAULT_SUPABASE_URL,
      VITE_SUPABASE_ANON_KEY: DEFAULT_SUPABASE_ANON_KEY,
    };

export const isSupabaseConfigured = Boolean(
  env.VITE_SUPABASE_URL.trim() && env.VITE_SUPABASE_ANON_KEY.trim(),
);
