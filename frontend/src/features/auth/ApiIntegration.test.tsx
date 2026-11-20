import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { appRoutes } from '../../app/router';
import type { AuthSession } from '../../state/AuthContext';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function renderWithRouter(initialPath: string, initialSession: AuthSession | null) {
  const router = createMemoryRouter(appRoutes, {
    initialEntries: [initialPath],
  });

  return render(
    <AppProviders initialSession={initialSession}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

const API_SESSION: AuthSession = {
  mode: 'api',
  accessToken: 'fake-jwt-token',
  userId: '11111111-1111-1111-1111-111111111111',
  email: 'khadim@amireflow.local',
  displayName: 'Khadim',
};

const BASE_PROFILE = {
  id: '11111111-1111-1111-1111-111111111111',
  display_name: 'Khadim',
  timezone: 'Africa/Dakar',
  active_priority_title: null,
  active_priority_task_id: null,
  active_priority_project_id: null,
  preferences: {},
  ai_instructions: null as string | null,
  created_at: '2026-11-19T10:00:00Z',
  updated_at: '2026-11-19T10:00:00Z',
};

describe('Intégration API FastAPI & Authentification (Lot 5)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('connecte via /login, envoie le jeton Bearer, crée une tâche API et gère la déconnexion (AUTH-01)', async () => {
    const user = userEvent.setup();
    const tasksStore: Array<Record<string, unknown>> = [];

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? 'GET').toUpperCase();
      const headers = (init?.headers ?? {}) as Record<string, string>;

      if (url.endsWith('/auth/local-login') && method === 'POST') {
        return jsonResponse({
          access_token: 'jwt-abc-123',
          token_type: 'bearer',
          expires_in: 86400,
          profile: BASE_PROFILE,
        });
      }

      if (headers.Authorization !== 'Bearer jwt-abc-123') {
        return jsonResponse(
          { error: { code: 'UNAUTHORIZED', message: 'Non autorisé', request_id: 'req_1' } },
          401,
        );
      }

      if (url.endsWith('/profile')) {
        return jsonResponse(BASE_PROFILE);
      }
      if (url.endsWith('/tasks') && method === 'GET') {
        return jsonResponse(tasksStore);
      }
      if (url.endsWith('/tasks') && method === 'POST') {
        const body = JSON.parse(String(init?.body ?? '{}')) as Record<string, unknown>;
        const created = {
          id: 'task-api-1',
          user_id: BASE_PROFILE.id,
          title: body.title,
          description: body.description ?? null,
          status: body.status ?? 'todo',
          priority: body.priority ?? 'normal',
          due_at: body.due_at ?? null,
          completed_at: null,
          source: 'manual',
          proposal_id: null,
          project_id: null,
          module_id: null,
          created_at: '2026-11-19T12:00:00Z',
          updated_at: '2026-11-19T12:00:00Z',
        };
        tasksStore.push(created);
        return jsonResponse(created, 201);
      }
      if (url.endsWith('/sessions') || url.endsWith('/schedule')) {
        return jsonResponse([]);
      }

      return jsonResponse({}, 404);
    });

    renderWithRouter('/login', null);

    await user.type(screen.getByLabelText(/Nom d’affichage/), 'Khadim');
    await user.click(screen.getByRole('button', { name: 'Se connecter au backend' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Tableau de bord' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Khadim')).toBeInTheDocument();

    const desktopNav = screen.getByRole('navigation', { name: 'Navigation principale' });
    await user.click(within(desktopNav).getByRole('link', { name: 'Tâches' }));

    await user.click(screen.getByRole('button', { name: 'Nouvelle tâche' }));
    await user.type(screen.getByLabelText(/Titre/), 'Connecter PostgreSQL');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));

    expect(
      await screen.findByRole('article', { name: 'Connecter PostgreSQL' }),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/tasks'),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer jwt-abc-123' }),
      }),
    );

    await user.click(screen.getByRole('button', { name: 'Déconnexion' }));
    expect(await screen.findByRole('heading', { level: 2, name: 'Connexion' })).toBeInTheDocument();
  });

  it('affiche ErrorState sur erreur 500 puis recharge après clic sur Réessayer', async () => {
    const user = userEvent.setup();
    let shouldFailTasks = true;

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/profile')) {
        return jsonResponse(BASE_PROFILE);
      }
      if (url.endsWith('/tasks')) {
        if (shouldFailTasks) {
          return jsonResponse(
            {
              error: {
                code: 'INTERNAL_ERROR',
                message: 'Erreur temporaire de base de données.',
                request_id: 'req_500',
              },
            },
            500,
          );
        }
        return jsonResponse([
          {
            id: 't-ok',
            user_id: BASE_PROFILE.id,
            title: 'Tâche rechargée',
            description: null,
            status: 'todo',
            priority: 'normal',
            due_at: null,
            completed_at: null,
            source: 'manual',
            proposal_id: null,
            project_id: null,
            module_id: null,
            created_at: '2026-11-19T12:00:00Z',
            updated_at: '2026-11-19T12:00:00Z',
          },
        ]);
      }
      return jsonResponse([]);
    });

    renderWithRouter('/tasks', API_SESSION);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Erreur temporaire de base de données.');

    shouldFailTasks = false;
    await user.click(screen.getByRole('button', { name: 'Réessayer' }));

    expect(await screen.findByRole('article', { name: 'Tâche rechargée' })).toBeInTheDocument();
  });

  it('redirige vers /login avec message d’expiration si l’API répond 401', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      jsonResponse(
        {
          error: {
            code: 'UNAUTHORIZED',
            message: 'Jeton expiré.',
            request_id: 'req_401',
          },
        },
        401,
      ),
    );

    renderWithRouter('/tasks', API_SESSION);

    expect(await screen.findByRole('heading', { level: 2, name: 'Connexion' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Votre session a expiré');
  });

  it('met à jour le profil et le fuseau horaire depuis Paramètres (AUTH-03)', async () => {
    const user = userEvent.setup();
    let currentProfile: typeof BASE_PROFILE & { ai_instructions: string | null } = {
      ...BASE_PROFILE,
    };

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/profile') && method === 'GET') {
        return jsonResponse(currentProfile);
      }
      if (url.endsWith('/profile') && method === 'PATCH') {
        const body = JSON.parse(String(init?.body ?? '{}')) as Record<string, unknown>;
        currentProfile = {
          ...currentProfile,
          display_name: (body.display_name as string) ?? currentProfile.display_name,
          timezone: (body.timezone as string) ?? currentProfile.timezone,
          ai_instructions:
            body.ai_instructions !== undefined
              ? (body.ai_instructions as string | null)
              : currentProfile.ai_instructions,
        };
        return jsonResponse(currentProfile);
      }
      return jsonResponse([]);
    });

    renderWithRouter('/settings', API_SESSION);

    const nameInput = await screen.findByLabelText(/Nom d’affichage/);
    await user.clear(nameInput);
    await user.type(nameInput, 'Khadim Dev');
    await user.selectOptions(screen.getByLabelText(/Fuseau horaire/), 'Europe/Paris');
    await user.type(
      screen.getByLabelText(/Consignes pour le copilote IA/),
      'Aller droit au but.',
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer les paramètres' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Paramètres du profil enregistrés.',
    );
    expect(currentProfile.timezone).toBe('Europe/Paris');
    expect(currentProfile.display_name).toBe('Khadim Dev');
  });
});
