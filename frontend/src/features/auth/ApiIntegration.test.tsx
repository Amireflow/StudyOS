import { render, screen, waitFor, within } from '@testing-library/react';
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
    window.localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  it('connecte via /login, envoie le jeton Bearer, crée une tâche API et gère la déconnexion (AUTH-01)', async () => {
    const user = userEvent.setup();
    const tasksStore: Array<Record<string, unknown>> = [];

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? 'GET').toUpperCase();
      const headers = (init?.headers ?? {}) as Record<string, string>;

      if (url.endsWith('/auth/login') && method === 'POST') {
        return jsonResponse({
          access_token: 'jwt-abc-123',
          token_type: 'bearer',
          expires_in: 604800,
          email: 'khadim@amireflow.local',
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

    await user.type(screen.getByLabelText(/Adresse e-mail/), 'khadim@amireflow.local');
    await user.type(screen.getByLabelText(/Mot de passe/), 'MonMotDePasse123!');
    await user.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Tableau de bord' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Khadim')).toBeInTheDocument();
    expect(screen.getByText('khadim@amireflow.local')).toBeInTheDocument();

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

  it('permet de créer des comptes distincts et isole totalement les données, paramètres et thèmes entre deux utilisateurs', async () => {
    const user = userEvent.setup();
    const accountsByToken = new Map<
      string,
      {
        email: string;
        profile: {
          id: string;
          display_name: string;
          timezone: string;
          active_priority_title: string | null;
          active_priority_task_id: string | null;
          active_priority_project_id: string | null;
          preferences: Record<string, unknown>;
          ai_instructions: string | null;
          created_at: string;
          updated_at: string;
        };
        tasks: Array<Record<string, unknown>>;
      }
    >();

    let userCounter = 0;
    let taskCounter = 0;

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? 'GET').toUpperCase();
      const headers = (init?.headers ?? {}) as Record<string, string>;

      if (url.endsWith('/auth/register') && method === 'POST') {
        const body = JSON.parse(String(init?.body ?? '{}')) as Record<string, unknown>;
        userCounter += 1;
        const userId = `user-0000-0000-0000-00000000000${userCounter}`;
        const token = `token-user-${userCounter}`;
        const profile = {
          id: userId,
          display_name: String(body.display_name ?? 'Utilisateur'),
          timezone: String(body.timezone ?? 'Africa/Dakar'),
          active_priority_title: null,
          active_priority_task_id: null,
          active_priority_project_id: null,
          preferences: { theme: 'system' },
          ai_instructions: null,
          created_at: '2026-11-20T04:00:00Z',
          updated_at: '2026-11-20T04:00:00Z',
        };
        accountsByToken.set(token, {
          email: String(body.email),
          profile,
          tasks: [],
        });
        return jsonResponse(
          {
            access_token: token,
            token_type: 'bearer',
            expires_in: 604800,
            email: body.email,
            profile,
          },
          201,
        );
      }

      const authHeader = headers.Authorization ?? '';
      const token = authHeader.replace(/^Bearer\s+/i, '').trim();
      const account = accountsByToken.get(token);
      if (!account) {
        return jsonResponse(
          { error: { code: 'UNAUTHORIZED', message: 'Non autorisé', request_id: 'req_u' } },
          401,
        );
      }

      if (url.endsWith('/profile') && method === 'GET') {
        return jsonResponse(account.profile);
      }
      if (url.endsWith('/profile') && method === 'PATCH') {
        const body = JSON.parse(String(init?.body ?? '{}')) as Record<string, unknown>;
        account.profile = {
          ...account.profile,
          ...(typeof body.display_name === 'string' ? { display_name: body.display_name } : {}),
          ...(typeof body.timezone === 'string' ? { timezone: body.timezone } : {}),
          ...(body.preferences && typeof body.preferences === 'object'
            ? { preferences: body.preferences as Record<string, unknown> }
            : {}),
        };
        return jsonResponse(account.profile);
      }
      if (url.endsWith('/tasks') && method === 'GET') {
        return jsonResponse(account.tasks);
      }
      if (url.endsWith('/tasks') && method === 'POST') {
        const body = JSON.parse(String(init?.body ?? '{}')) as Record<string, unknown>;
        taskCounter += 1;
        const created = {
          id: `task-${taskCounter}`,
          user_id: account.profile.id,
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
          created_at: '2026-11-20T04:10:00Z',
          updated_at: '2026-11-20T04:10:00Z',
        };
        account.tasks.push(created);
        return jsonResponse(created, 201);
      }
      if (url.endsWith('/ai/provider/config') && method === 'GET') {
        return jsonResponse({
          provider: 'local',
          base_url: '',
          model: 'local-coach-v1',
          has_api_key: false,
          api_key_preview: null,
          source: 'default',
          available_providers: [],
        });
      }

      return jsonResponse([]);
    });

    renderWithRouter('/login', null);

    // 1. Inscription d'Alice
    await user.click(screen.getByRole('tab', { name: 'Créer un compte' }));
    await user.type(screen.getByLabelText(/Nom d’affichage/), 'Alice');
    await user.type(screen.getByLabelText(/Adresse e-mail/), 'alice@amireflow.local');
    await user.selectOptions(screen.getByLabelText(/Fuseau horaire/), 'Europe/Paris');
    await user.type(screen.getByLabelText(/^Mot de passe/), 'AlicePass123!');
    await user.type(screen.getByLabelText(/Confirmer le mot de passe/), 'AlicePass123!');
    await user.click(screen.getByRole('button', { name: 'Créer mon compte' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Tableau de bord' }),
    ).toBeInTheDocument();
    expect(screen.getByText('alice@amireflow.local')).toBeInTheDocument();

    // Alice crée sa tâche privée et passe en thème sombre
    const navAlice = screen.getByRole('navigation', { name: 'Navigation principale' });
    await user.click(within(navAlice).getByRole('link', { name: 'Tâches' }));
    await user.click(screen.getByRole('button', { name: 'Nouvelle tâche' }));
    await user.type(screen.getByLabelText(/Titre/), 'Tâche confidentielle Alice');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));
    expect(
      await screen.findByRole('article', { name: 'Tâche confidentielle Alice' }),
    ).toBeInTheDocument();

    await user.click(within(navAlice).getByRole('link', { name: 'Paramètres' }));
    const themeGroup = screen.getByRole('group', { name: 'Choix du thème d’affichage' });
    await user.click(within(themeGroup).getByRole('button', { name: 'Sombre' }));
    expect(document.documentElement).toHaveClass('dark');

    // Déconnexion d'Alice
    await user.click(screen.getByRole('button', { name: 'Déconnexion' }));
    expect(await screen.findByRole('heading', { level: 2, name: 'Connexion' })).toBeInTheDocument();

    // 2. Inscription de Bob
    await user.click(screen.getByRole('tab', { name: 'Créer un compte' }));
    await user.type(screen.getByLabelText(/Nom d’affichage/), 'Bob');
    await user.type(screen.getByLabelText(/Adresse e-mail/), 'bob@amireflow.local');
    await user.selectOptions(screen.getByLabelText(/Fuseau horaire/), 'Africa/Dakar');
    await user.type(screen.getByLabelText(/^Mot de passe/), 'BobPass123!');
    await user.type(screen.getByLabelText(/Confirmer le mot de passe/), 'BobPass123!');
    await user.click(screen.getByRole('button', { name: 'Créer mon compte' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Tableau de bord' }),
    ).toBeInTheDocument();
    expect(screen.getByText('bob@amireflow.local')).toBeInTheDocument();
    expect(screen.queryByText('alice@amireflow.local')).not.toBeInTheDocument();

    // Bob récupère son propre thème (system / non dark) et ne voit aucune tâche d'Alice
    await waitFor(() => {
      expect(document.documentElement).not.toHaveClass('dark');
    });

    const navBob = screen.getByRole('navigation', { name: 'Navigation principale' });
    await user.click(within(navBob).getByRole('link', { name: 'Tâches' }));
    expect(screen.queryByText('Tâche confidentielle Alice')).not.toBeInTheDocument();

    await user.click(within(navBob).getByRole('link', { name: 'Paramètres' }));
    expect(await screen.findByLabelText(/Nom d’affichage/)).toHaveValue('Bob');
    expect(screen.getByLabelText(/Fuseau horaire/)).toHaveValue('Africa/Dakar');
  });
});
