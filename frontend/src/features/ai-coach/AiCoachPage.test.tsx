import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { installMockStudyApi, TEST_API_SESSION } from '../../test/mockStudyApi';
import { AiCoachPage } from './AiCoachPage';

function renderAiCoachPage(initialEntry = '/') {
  return render(
    <AppProviders initialSession={TEST_API_SESSION}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <AiCoachPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('AiCoachPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('propose une tâche sans mutation immédiate (AI-01), permet de l’ajuster puis de la valider (AI-07) ou de la rejeter, et génère briefing/bilan (AI-06)', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderAiCoachPage();

    await user.type(
      await screen.findByLabelText(/Votre message au Copilote/),
      'Crée une tâche : « Réviser les index PostgreSQL »',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(await screen.findByText('En attente de validation')).toBeInTheDocument();
    expect(screen.getByText(/Indication AI-06/)).toBeInTheDocument();
    expect(api.state.tasks).toHaveLength(0);

    await user.click(screen.getByRole('button', { name: 'Ajuster' }));
    const titleInput = screen.getByLabelText(/Ajuster le titre avant validation/);
    await user.clear(titleInput);
    await user.type(titleInput, 'Réviser les index PostgreSQL et plans EXPLAIN');
    await user.selectOptions(screen.getByLabelText(/Ajuster la priorité/), 'high');

    await user.click(screen.getByRole('button', { name: 'Valider et exécuter' }));

    expect(await screen.findByText('Exécutée')).toBeInTheDocument();
    await waitFor(() => {
      expect(api.state.tasks).toHaveLength(1);
    });
    expect(api.state.tasks[0].title).toBe('Réviser les index PostgreSQL et plans EXPLAIN');
    expect(api.state.tasks[0].priority).toBe('high');
    expect(api.state.tasks[0].source).toBe('ai_proposal');

    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Mets cette tâche au parking',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    const rejectButtons = await screen.findAllByRole('button', { name: 'Rejeter' });
    await user.click(rejectButtons[0]);
    expect(await screen.findByText('Rejetée')).toBeInTheDocument();
    expect(api.state.tasks[0].status).toBe('todo');

    await user.click(screen.getByText('Plus'));
    await user.click(screen.getByRole('button', { name: 'Briefing du jour' }));
    expect(await screen.findByText('Briefing quotidien')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Bilan hebdo' }));
    expect(await screen.findByText('Bilan hebdomadaire')).toBeInTheDocument();
  });

  it('préremplit la demande transmise par un autre espace sans l’envoyer automatiquement', async () => {
    installMockStudyApi();
    const prompt = 'Construis un parcours React adapté à mes compétences actuelles.';
    renderAiCoachPage('/ai-coach?prompt=' + encodeURIComponent(prompt));

    const input = await screen.findByLabelText(/Votre message au Copilote/);
    await waitFor(() => expect(input).toHaveValue(prompt));
    expect(screen.queryByText(prompt)).not.toBeInTheDocument();
  });

  it('annonce les trois vues mobiles du Copilote comme états pressés exclusifs', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderAiCoachPage();

    const nav = await screen.findByRole('navigation', { name: 'Vues mobiles du copilote' });
    const discussion = within(nav).getByRole('button', { name: 'Discussion' });
    const actions = within(nav).getByRole('button', { name: 'Actions' });
    const syntheses = within(nav).getByRole('button', { name: /Synthèses/ });

    expect(discussion).toHaveAttribute('aria-pressed', 'true');
    expect(actions).toHaveAttribute('aria-pressed', 'false');
    expect(syntheses).toHaveAttribute('aria-pressed', 'false');

    await user.click(actions);
    expect(discussion).toHaveAttribute('aria-pressed', 'false');
    expect(actions).toHaveAttribute('aria-pressed', 'true');
    expect(syntheses).toHaveAttribute('aria-pressed', 'false');

    await user.click(syntheses);
    expect(actions).toHaveAttribute('aria-pressed', 'false');
    expect(syntheses).toHaveAttribute('aria-pressed', 'true');
  });

  it('propose des amorces rapides, envoie avec Entrée, et permet d’ouvrir les outils et l’historique', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderAiCoachPage();

    expect(await screen.findByText('Que souhaitez-vous organiser ?')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Planifier ma journée/i }));

    const promptInput = screen.getByLabelText(/Votre message au Copilote/);
    expect(promptInput).toHaveValue(
      'Planifie ma journée autour de ma priorité active et de mes créneaux disponibles.',
    );

    await user.keyboard('{Enter}');
    expect(promptInput).toHaveValue('');
    expect(
      await screen.findByText(
        'Planifie ma journée autour de ma priorité active et de mes créneaux disponibles.',
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByText('Plus'));
    await user.click(screen.getByRole('button', { name: /Outils \(/i }));
    expect(screen.getByText(/Outils autorisés/)).toBeInTheDocument();
    expect(screen.getByText('Lire les tâches')).toBeInTheDocument();
    expect(screen.getByText('Proposer une évaluation de compétence')).toBeInTheDocument();
    expect(screen.getByText('Recommander une progression vérifiée')).toBeInTheDocument();
    expect(screen.queryByText('Proposer un niveau de compétence')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Nouvelle conversation' }));
    await user.click(await screen.findByRole('button', { name: 'Historique des conversations' }));
    await waitFor(() => {
      expect(screen.getByText(/Historique des conversations \(2\)/)).toBeInTheDocument();
    });
  });

  it('gère la planification conversationnelle stratégique (proposition, modification et acceptation)', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderAiCoachPage();

    await user.click(await screen.findByRole('button', { name: /Apprendre une compétence/i }));
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(
      await screen.findByText(/Voici ma proposition pour/i),
    ).toBeInTheDocument();
    expect(screen.getByText('Acceptable')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Accepter et programmer' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Modifier la proposition' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Refuser' })).toBeInTheDocument();

    expect(api.state.scheduleEvents).toHaveLength(0);

    await user.click(screen.getByRole('button', { name: 'Modifier la proposition' }));
    const titleInput = screen.getByLabelText(/Modifier le titre de l’activité/);
    await user.clear(titleInput);
    await user.type(titleInput, 'React 19 & TypeScript');
    await user.click(screen.getByRole('button', { name: 'Accepter et programmer' }));

    expect(await screen.findByText('Exécutée')).toBeInTheDocument();
    await waitFor(() => {
      expect(api.state.scheduleEvents.length).toBeGreaterThanOrEqual(1);
    });
    expect(api.state.tasks).toHaveLength(1);
    expect(api.state.paths).toHaveLength(1);
    expect(api.state.paths[0].title).toBe('React 19 & TypeScript');
  });

  it('déclenche STOP — DISPERSION DÉTECTÉE lorsqu’une priorité active divergente existe', async () => {
    installMockStudyApi({
      profile: {
        active_priority_title: 'Réussir l’examen d’Algorithmique',
      },
    });

    const user = userEvent.setup();
    renderAiCoachPage();

    await user.type(
      await screen.findByLabelText(/Votre message au Copilote/),
      'Je voudrais apprendre la photographie argentique.',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(await screen.findByText(/STOP — DISPERSION DÉTECTÉE\./)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Placer au Parking' }),
    ).toBeInTheDocument();
  });

  it('affiche immédiatement le message utilisateur et les étapes de réflexion du Copilote pendant l’attente réseau', async () => {
    let resolveTurn = null as ((res: Response) => void) | null;
    let turnCompleted = false;

    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input);
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/ai/conversations') && method === 'POST') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: 'conv-stream-1',
              user_id: 'u-1',
              title: 'Bonjour',
              created_at: '2026-11-20T05:00:00Z',
              updated_at: '2026-11-20T05:00:00Z',
            }),
            { status: 201, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }

      if (url.includes('/ai/conversations/conv-stream-1/messages') && method === 'POST') {
        return new Promise<Response>((resolve) => {
          resolveTurn = (res) => {
            turnCompleted = true;
            resolve(res);
          };
        });
      }

      if (url.includes('/ai/conversations/conv-stream-1') && method === 'GET') {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              conversation: {
                id: 'conv-stream-1',
                user_id: 'u-1',
                title: 'Bonjour',
                created_at: '2026-11-20T05:00:00Z',
                updated_at: '2026-11-20T05:00:01Z',
              },
              messages: turnCompleted
                ? [
                    {
                      id: 'm-user-1',
                      user_id: 'u-1',
                      conversation_id: 'conv-stream-1',
                      role: 'user',
                      content: 'Organise ma semaine',
                      metadata: {},
                      created_at: '2026-11-20T05:00:00Z',
                    },
                    {
                      id: 'm-assistant-1',
                      user_id: 'u-1',
                      conversation_id: 'conv-stream-1',
                      role: 'assistant',
                      content: 'Voici ton programme structuré pour la semaine.',
                      metadata: { is_estimate: false, missing_data: [] },
                      created_at: '2026-11-20T05:00:01Z',
                    },
                  ]
                : [],
              proposals: [],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        );
      }

      return Promise.resolve(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });

    const user = userEvent.setup();
    render(
      <AppProviders
        initialSession={{
          mode: 'api',
          accessToken: 'jwt-token',
          userId: 'u-1',
          email: 'khadim@amireflow.local',
          displayName: 'Khadim',
        }}
      >
        <MemoryRouter>
          <AiCoachPage />
        </MemoryRouter>
      </AppProviders>,
    );

    const promptInput = await screen.findByLabelText(/Votre message au Copilote/);
    await user.type(promptInput, 'Organise ma semaine');
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(promptInput).toHaveValue('');
    expect(screen.getByText('Organise ma semaine')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'Le Copilote réfléchit' })).toBeInTheDocument();
    expect(screen.getAllByText('Analyse de votre demande').length).toBeGreaterThan(0);

    resolveTurn?.(
      new Response(
        JSON.stringify({
          user_message: {
            id: 'm-user-1',
            user_id: 'u-1',
            conversation_id: 'conv-stream-1',
            role: 'user',
            content: 'Organise ma semaine',
            metadata: {},
            created_at: '2026-11-20T05:00:00Z',
          },
          assistant_message: {
            id: 'm-assistant-1',
            user_id: 'u-1',
            conversation_id: 'conv-stream-1',
            role: 'assistant',
            content: 'Voici ton programme structuré pour la semaine.',
            metadata: { is_estimate: false, missing_data: [] },
            created_at: '2026-11-20T05:00:01Z',
          },
          proposals: [],
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    expect(
      await screen.findByText('Voici ton programme structuré pour la semaine.'),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('status', { name: 'Le Copilote réfléchit' }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByText('Plus'));
    await user.click(screen.getByRole('button', { name: 'Importer mon emploi du temps' }));
    expect(
      screen.getByRole('region', { name: 'Importer mon emploi du temps' }),
    ).toBeInTheDocument();
  });

  it('permet de consulter et modifier la mémoire IA et le mode d’exécution simple automatique', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderAiCoachPage();

    await user.click(await screen.findByText('Plus'));
    await user.click(screen.getByRole('button', { name: 'Mémoire IA' }));
    expect(
      screen.getByRole('region', { name: 'Mémoire IA persistante' }),
    ).toBeInTheDocument();

    const hoursInput = screen.getByLabelText('Heures disponibles / semaine');
    await user.clear(hoursInput);
    await user.type(hoursInput, '8');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la mémoire' }));

    await waitFor(() => {
      expect(api.state.aiMemory.weekly_study_hours).toBe(8);
    });

    const autoSwitch = screen.getByRole('switch', { name: 'Actions simples automatiques' });
    expect(autoSwitch).toHaveAttribute('aria-checked', 'false');
    await user.click(autoSwitch);
    await waitFor(() => {
      expect(autoSwitch).toHaveAttribute('aria-checked', 'true');
    });

    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Crée une tâche : « Préparer les tests React »',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(await screen.findByText('Exécutée')).toBeInTheDocument();
    await waitFor(() => {
      expect(api.state.tasks.some((t) => t.title === 'Préparer les tests React')).toBe(true);
    });
  });
});
