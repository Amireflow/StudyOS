import { env } from './env';

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
}

/**
 * Erreur HTTP normalisée correspondant au contrat d'erreur de l'API FastAPI (CdC §7.1).
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(status: number, code: string, message: string, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  accessToken?: string;
  skipAuthRefresh?: boolean;
}

export interface ApiAuthHandlers {
  refreshAccessToken?: () => Promise<string | null>;
  onSessionExpired?: (reason?: string) => void;
}

let authHandlers: ApiAuthHandlers = {};
let inflightRefresh: Promise<string | null> | null = null;

export function configureApiAuthHandlers(handlers: ApiAuthHandlers): void {
  authHandlers = handlers;
}

/**
 * Client HTTP de base (connexion backend FastAPI avec cookies HttpOnly & refresh single-flight).
 */
export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, accessToken, headers, skipAuthRefresh = false, ...rest } = options;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${env.VITE_API_BASE_URL}${normalizedPath}`;

  const response = await fetch(url, {
    ...rest,
    credentials: rest.credentials ?? 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (
    response.status === 401 &&
    !skipAuthRefresh &&
    accessToken &&
    !normalizedPath.startsWith('/auth/') &&
    authHandlers.refreshAccessToken
  ) {
    if (!inflightRefresh) {
      inflightRefresh = authHandlers.refreshAccessToken().finally(() => {
        inflightRefresh = null;
      });
    }
    const nextToken = await inflightRefresh;
    if (nextToken) {
      return apiRequest<T>(path, {
        ...options,
        accessToken: nextToken,
        skipAuthRefresh: true,
      });
    }
    authHandlers.onSessionExpired?.('Votre session a expiré. Reconnectez-vous.');
  }

  if (!response.ok) {
    let payload: ApiErrorPayload | null = null;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = null;
    }

    throw new ApiError(
      response.status,
      payload?.error?.code ?? 'HTTP_ERROR',
      payload?.error?.message ?? `Erreur serveur (${response.status}).`,
      payload?.error?.request_id,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
