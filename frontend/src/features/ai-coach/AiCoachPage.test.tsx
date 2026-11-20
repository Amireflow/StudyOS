import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { STORAGE_KEYS } from '../../lib/storage';
import { AiCoachPage } from './AiCoachPage';

function renderAiCoachPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <AiCoachPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('AiCoachPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('propose une tâche sans mutation immédiate (AI-01), permet de l’ajuster puis de la valider (AI-07) ou de la rejeter, et génère briefing/bilan (AI-06)', async () => {
    const user = userEvent.setup();
    renderAiCoachPage();

    // Demander la création d'une tâche -> proposition en attente, aucune tâche créée tant que non validée
    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Crée une tâche : « Réviser les index PostgreSQL »',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(screen.getByText('En attente de validation')).toBeInTheDocument();
    expect(screen.getByText(/Indication AI-06/)).toBeInTheDocument();

    const beforeAcceptState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(beforeAcceptState.tasks ?? []).toHaveLength(0);

    // Ajuster le titre et la priorité avant de valider
    await user.click(screen.getByRole('button', { name: 'Ajuster' }));
    const titleInput = screen.getByLabelText(/Ajuster le titre avant validation/);
    await user.clear(titleInput);
    await user.type(titleInput, 'Réviser les index PostgreSQL et plans EXPLAIN');
    await user.selectOptions(screen.getByLabelText(/Ajuster la priorité/), 'high');

    await user.click(screen.getByRole('button', { name: 'Valider et exécuter' }));

    expect(screen.getByText('Exécutée')).toBeInTheDocument();

    const afterAcceptState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(afterAcceptState.tasks).toHaveLength(1);
    expect(afterAcceptState.tasks[0].title).toBe(
      'Réviser les index PostgreSQL et plans EXPLAIN',
    );
    expect(afterAcceptState.tasks[0].priority).toBe('high');
    expect(afterAcceptState.tasks[0].source).toBe('ai_proposal');

    // Demander de mettre la tâche au parking puis rejeter la proposition
    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Mets cette tâche au parking',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    await user.click(screen.getByRole('button', { name: 'Rejeter' }));
    expect(screen.getByText('Rejetée')).toBeInTheDocument();

    const afterRejectState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(afterRejectState.tasks[0].status).toBe('todo');

    // Générer un briefing quotidien et un bilan hebdomadaire (P1)
    await user.click(screen.getByRole('button', { name: 'Briefing du jour' }));
    expect(screen.getByText('Briefing quotidien')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Bilan hebdo' }));
    expect(screen.getByText('Bilan hebdomadaire')).toBeInTheDocument();
  });

  it('propose des amorces rapides, envoie avec Entrée, et permet d’ouvrir les outils et l’historique', async () => {
    const user = userEvent.setup();
    renderAiCoachPage();

    // État initial épuré + amorce rapide
    expect(screen.getByText('Que souhaitez-vous organiser ?')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Planifier ma journée/i }));

    const promptInput = screen.getByLabelText(/Votre message au Copilote/);
    expect(promptInput).toHaveValue(
      'Planifie ma journée autour de ma priorité active et de mes créneaux disponibles.',
    );

    // Envoi au clavier via la touche Entrée
    await user.keyboard('{Enter}');
    expect(promptInput).toHaveValue('');
    expect(
      await screen.findByText(
        'Planifie ma journée autour de ma priorité active et de mes créneaux disponibles.',
      ),
    ).toBeInTheDocument();

    // Inspecteur d'outils : vérifie la présence des outils d'évaluation et l'absence de mutation directe du niveau
    await user.click(screen.getByRole('button', { name: /Outils \(/i }));
    expect(screen.getByText(/Outils autorisés/)).toBeInTheDocument();
    expect(screen.getByText('Lire les tâches')).toBeInTheDocument();
    expect(screen.getByText('Proposer une évaluation de compétence')).toBeInTheDocument();
    expect(screen.getByText('Recommander une progression vérifiée')).toBeInTheDocument();
    expect(screen.queryByText('Proposer un niveau de compétence')).not.toBeInTheDocument();

    // Nouvelle conversation et tiroir historique
    await user.click(screen.getByRole('button', { name: 'Nouvelle conversation' }));
    await user.click(screen.getByRole('button', { name: 'Historique des conversations' }));
    expect(screen.getByText(/Historique des conversations \(2\)/)).toBeInTheDocument();
  });

  it('gère la planification conversationnelle stratégique (proposition, modification et acceptation)', async () => {
    const user = userEvent.setup();
    renderAiCoachPage();

    // 1. Demande conversationnelle compatible avec les disponibilités
    await user.click(screen.getByRole('button', { name: /Apprendre une compétence/i }));
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

    // Aucune mutation dans learningState ni scheduleEvents avant validation explicite
    const beforeState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(beforeState.scheduleEvents ?? []).toHaveLength(0);

    // Modification inline de la proposition puis validation
    await user.click(screen.getByRole('button', { name: 'Modifier la proposition' }));
    const titleInput = screen.getByLabelText(/Modifier le titre de l’activité/);
    await user.clear(titleInput);
    await user.type(titleInput, 'React 19 & TypeScript');
    await user.click(screen.getByRole('button', { name: 'Accepter et programmer' }));

    expect(await screen.findByText('Exécutée')).toBeInTheDocument();

    const afterStudy = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(afterStudy.scheduleEvents.length).toBeGreaterThanOrEqual(1);
    expect(afterStudy.tasks.length).toBe(1);

    const afterLearning = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.learningState) ?? '{}',
    );
    expect(afterLearning.paths).toHaveLength(1);
    expect(afterLearning.paths[0].title).toBe('React 19 & TypeScript');
  });

  it('déclenche STOP — DISPERSION DÉTECTÉE lorsqu’une priorité active divergente existe', async () => {
    window.localStorage.setItem(
      STORAGE_KEYS.studyState,
      JSON.stringify({
        profile: { displayName: 'Utilisateur', timezone: 'Africa/Dakar', aiInstructions: null },
        activePriorityTitle: 'Réussir l’examen d’Algorithmique',
        activePriorityTaskId: null,
        activePriorityProjectId: null,
        tasks: [],
        sessions: [],
        scheduleEvents: [],
      }),
    );

    const user = userEvent.setup();
    renderAiCoachPage();

    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
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

    // Le champ est vidé immédiatement, le message utilisateur et l'état de réflexion s'affichent sans attendre le serveur
    expect(promptInput).toHaveValue('');
    expect(screen.getByText('Organise ma semaine')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'Le Copilote réfléchit' })).toBeInTheDocument();
    expect(screen.getAllByText('Analyse de votre demande').length).toBeGreaterThan(0);

    // Résolution de la réponse serveur -> transition fluide vers la réponse finale
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

    // Le bouton Emploi du temps ouvre le panneau d'import directement dans le Copilote IA
    await user.click(screen.getByRole('button', { name: 'Emploi du temps' }));
    expect(
      screen.getByRole('region', { name: 'Importer mon emploi du temps' }),
    ).toBeInTheDocument();
  });

  it('permet de consulter et modifier la mémoire IA et le mode d’exécution simple automatique', async () => {
    const user = userEvent.setup();
    renderAiCoachPage();

    await user.click(screen.getByRole('button', { name: 'Mémoire IA' }));
    expect(
      screen.getByRole('region', { name: 'Mémoire IA persistante' }),
    ).toBeInTheDocument();

    const hoursInput = screen.getByLabelText('Heures disponibles / semaine');
    await user.clear(hoursInput);
    await user.type(hoursInput, '8');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la mémoire' }));

    const savedAiState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.aiState) ?? '{}',
    );
    expect(savedAiState.aiMemory.weeklyStudyHours).toBe(8);

    const autoSwitch = screen.getByRole('switch', { name: 'Actions simples automatiques' });
    expect(autoSwitch).toHaveAttribute('aria-checked', 'false');
    await user.click(autoSwitch);
    expect(autoSwitch).toHaveAttribute('aria-checked', 'true');

    // Une action simple explicitement demandée s'exécute directement lorsque l'autonomie simple est activée
    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Crée une tâche : « Préparer les tests React »',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(await screen.findByText('Exécutée')).toBeInTheDocument();
    const afterStudyState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(afterStudyState.tasks.some((t: { title: string }) => t.title === 'Préparer les tests React')).toBe(
      true,
    );
  });
});
