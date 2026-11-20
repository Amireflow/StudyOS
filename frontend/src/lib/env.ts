import { z } from 'zod';

export const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';
export const DEFAULT_SUPABASE_URL = 'https://rzjjcqmsepxtpmqwzwmf.supabase.co';
export const DEFAULT_SUPABASE_ANON_KEY = 'sb_publishable_hGTCEH3pCjQcY_M-t3snyA_FvUSCBac';

const envSchema = z.object({
  VITE_API_BASE_URL: z.string().url().default(DEFAULT_API_BASE_URL),
  VITE_SUPABASE_URL: z.string().default(DEFAULT_SUPABASE_URL),
  VITE_SUPABASE_ANON_KEY: z.string().default(DEFAULT_SUPABASE_ANON_KEY),
});

const parsedEnv = envSchema.safeParse({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL,
  VITE_SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL || DEFAULT_SUPABASE_URL,
  VITE_SUPABASE_ANON_KEY: import.meta.env.VITE_SUPABASE_ANON_KEY || DEFAULT_SUPABASE_ANON_KEY,
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
