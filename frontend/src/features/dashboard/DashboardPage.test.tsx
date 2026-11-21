import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { installMockStudyApi, TEST_API_SESSION, TEST_USER_ID } from '../../test/mockStudyApi';
import { DashboardPage } from './DashboardPage';

function renderDashboardPage() {
  return render(
    <AppProviders initialSession={TEST_API_SESSION}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('DashboardPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('affiche les états vides guidés au départ (DASH-02) sans bouton d’exemple et permet de définir la priorité principale', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderDashboardPage();

    expect(await screen.findByText('Aucune priorité principale active')).toBeInTheDocument();
    expect(screen.getByText('Aucune tâche enregistrée')).toBeInTheDocument();
    expect(screen.getByText('Aucune séance achevée')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Charger des données d’exemple/i }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByText('Plus'));
    await user.click(screen.getByRole('button', { name: 'Définir manuellement' }));
    await user.type(
      screen.getByLabelText(/Intitulé de la priorité principale/),
      'Boucler le Lot 2 frontend',
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la priorité' }));

    expect(await screen.findByText('Boucler le Lot 2 frontend')).toBeInTheDocument();
  });

  it('calcule en temps réel la progression après achèvement d’une tâche (DASH-01, DASH-03)', async () => {
    const now = new Date();
    const nowIso = now.toISOString();
    const s1Start = new Date(now.getTime() - 5 * 60 * 60 * 1000);
    const s1End = new Date(s1Start.getTime() + 75 * 60 * 1000);
    const s2Start = new Date(now.getTime() - 26 * 60 * 60 * 1000);
    const s2End = new Date(s2Start.getTime() + 50 * 60 * 1000);
    const evStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 14, 0, 0).toISOString();
    const evEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 16, 0, 0).toISOString();

    installMockStudyApi({
      profile: {
        active_priority_title: 'Consolider les formulaires React et la validation Zod',
        active_priority_task_id: 'task-1',
      },
      tasks: [
        {
          id: 'task-1',
          user_id: TEST_USER_ID,
          title: 'Consolider les formulaires React et la validation Zod',
          description: null,
          status: 'in_progress',
          priority: 'critical',
          due_at: nowIso,
          completed_at: null,
          source: 'manual',
          proposal_id: null,
          project_id: null,
          module_id: null,
          created_at: nowIso,
          updated_at: nowIso,
        },
        {
          id: 'task-2',
          user_id: TEST_USER_ID,
          title: 'Préparer les exercices Python',
          description: null,
          status: 'todo',
          priority: 'high',
          due_at: nowIso,
          completed_at: null,
          source: 'manual',
          proposal_id: null,
          project_id: null,
          module_id: null,
          created_at: nowIso,
          updated_at: nowIso,
        },
        {
          id: 'task-3',
          user_id: TEST_USER_ID,
          title: 'Navigation React Router',
          description: null,
          status: 'done',
          priority: 'normal',
          due_at: nowIso,
          completed_at: nowIso,
          source: 'manual',
          proposal_id: null,
          project_id: null,
          module_id: null,
          created_at: nowIso,
          updated_at: nowIso,
        },
        {
          id: 'task-4',
          user_id: TEST_USER_ID,
          title: 'Idée parking',
          description: null,
          status: 'parked',
          priority: 'low',
          due_at: null,
          completed_at: null,
          source: 'manual',
          proposal_id: null,
          project_id: null,
          module_id: null,
          created_at: nowIso,
          updated_at: nowIso,
        },
      ],
      sessions: [
        {
          id: 'sess-1',
          user_id: TEST_USER_ID,
          title: 'Séance 1',
          category: 'Projet',
          status: 'completed',
          started_at: s1Start.toISOString(),
          ended_at: s1End.toISOString(),
          result: 'Terminé',
          task_id: null,
          project_id: null,
          module_id: null,
          lesson_id: null,
          skill_id: null,
          created_at: nowIso,
          updated_at: nowIso,
        },
        {
          id: 'sess-2',
          user_id: TEST_USER_ID,
          title: 'Séance 2',
          category: 'Cours',
          status: 'completed',
          started_at: s2Start.toISOString(),
          ended_at: s2End.toISOString(),
          result: 'Terminé',
          task_id: null,
          project_id: null,
          module_id: null,
          lesson_id: null,
          skill_id: null,
          created_at: nowIso,
          updated_at: nowIso,
        },
      ],
      scheduleEvents: [
        {
          id: 'ev-1',
          user_id: TEST_USER_ID,
          title: 'Cours d’algorithmique',
          type: 'course',
          starts_at: evStart,
          ends_at: evEnd,
          notes: null,
          source: 'manual',
          created_at: nowIso,
          updated_at: nowIso,
        },
      ],
    });

    const user = userEvent.setup();
    renderDashboardPage();

    expect(await screen.findByTestId('dashboard-completion-rate')).toHaveTextContent('33 %');
    expect(screen.getByTestId('dashboard-sessions-count')).toHaveTextContent('2');
    expect(screen.getByTestId('dashboard-sessions-time')).toHaveTextContent('2 h 05');
    expect(screen.getByText('Cours d’algorithmique')).toBeInTheDocument();

    await user.click(
      screen.getByRole('button', {
        name: 'Terminer Consolider les formulaires React et la validation Zod',
      }),
    );

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-completion-rate')).toHaveTextContent('67 %');
    });
  });

  it('permet de capturer une tâche rapide et de démarrer une séance depuis la priorité principale', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderDashboardPage();

    await user.click(await screen.findByRole('button', { name: 'Nouvelle tâche' }));
    await user.type(screen.getByLabelText('Nouvelle tâche rapide'), 'Préparer le TP SQL');
    await user.click(screen.getByRole('button', { name: 'Ajouter' }));

    expect(await screen.findByText('Préparer le TP SQL')).toBeInTheDocument();

    await user.click(screen.getByText('Plus'));
    await user.click(screen.getByRole('button', { name: 'Définir manuellement' }));
    await user.type(
      screen.getByLabelText(/Intitulé de la priorité principale/),
      'Boucler la refonte UI',
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la priorité' }));

    await user.click(await screen.findByRole('button', { name: 'Lancer une séance' }));

    await waitFor(() => {
      const activeBanner = screen.getByText(/Séance en cours :/).closest('div');
      expect(activeBanner).toHaveTextContent('Boucler la refonte UI');
    });
    expect(screen.getByRole('link', { name: 'Clôturer' })).toHaveAttribute('href', '/sessions');
  });
});
