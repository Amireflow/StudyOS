import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { installMockStudyApi, TEST_API_SESSION, TEST_USER_ID } from '../../test/mockStudyApi';
import { TasksPage } from './TasksPage';

async function openManualTaskForm(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Options des tâches' }));
  await user.click(screen.getByRole('button', { name: 'Créer manuellement' }));
}

function renderTasksPage() {
  return render(
    <AppProviders initialSession={TEST_API_SESSION}>
      <MemoryRouter>
        <TasksPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('TasksPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('valide les champs obligatoires puis crée, modifie et termine une tâche (TASK-01) sans bouton d’exemple', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderTasksPage();

    expect(
      await screen.findByRole('link', { name: 'Demander au Copilote' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Charger des données d’exemple/i }),
    ).not.toBeInTheDocument();

    await openManualTaskForm(user);
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Le titre doit contenir au moins 2 caractères.',
    );

    await user.type(screen.getByLabelText(/Titre/), 'Apprendre Pydantic');
    await user.selectOptions(screen.getByLabelText('Priorité'), 'high');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));

    expect(await screen.findByRole('article', { name: 'Apprendre Pydantic' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Apprendre Pydantic');
    expect(screen.getByTestId('stat-active')).toHaveTextContent('1');

    const card = screen.getByRole('article', { name: 'Apprendre Pydantic' });
    await user.click(within(card).getByRole('button', { name: 'Modifier' }));
    const titleInput = screen.getByLabelText(/Titre/);
    await user.clear(titleInput);
    await user.type(titleInput, 'Apprendre Pydantic v2');
    await user.click(screen.getByRole('button', { name: 'Enregistrer les modifications' }));

    const updatedCard = await screen.findByRole('article', { name: 'Apprendre Pydantic v2' });
    await user.click(within(updatedCard).getByRole('button', { name: 'Terminer' }));

    await waitFor(() => {
      expect(screen.getByTestId('stat-done')).toHaveTextContent('1');
      expect(screen.getByTestId('stat-active')).toHaveTextContent('0');
    });
    expect(
      within(screen.getByRole('article', { name: 'Apprendre Pydantic v2' })).getByText(/Terminée le/),
    ).toBeInTheDocument();
  });

  it('ne compte pas une tâche annulée comme terminée (TASK-02) et supporte le parking + filtres combinés (TASK-03)', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderTasksPage();

    await openManualTaskForm(user);
    await user.type(screen.getByLabelText(/Titre/), 'Tâche à annuler');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));
    expect(await screen.findByRole('article', { name: 'Tâche à annuler' })).toBeInTheDocument();

    await openManualTaskForm(user);
    await user.type(screen.getByLabelText(/Titre/), 'Idée future');
    await user.selectOptions(screen.getByLabelText('Priorité'), 'low');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));
    expect(await screen.findByRole('article', { name: 'Idée future' })).toBeInTheDocument();

    const cancelCard = screen.getByRole('article', { name: 'Tâche à annuler' });
    await user.click(within(cancelCard).getByRole('button', { name: 'Annuler' }));
    await waitFor(() => {
      expect(screen.getByTestId('stat-done')).toHaveTextContent('0');
    });

    const parkedCard = screen.getByRole('article', { name: 'Idée future' });
    await user.click(within(parkedCard).getByRole('button', { name: 'Parking' }));
    await waitFor(() => {
      expect(screen.getByTestId('stat-parked')).toHaveTextContent('1');
    });

    await user.selectOptions(screen.getByLabelText('Filtrer par statut'), 'parked');
    await user.selectOptions(screen.getByLabelText('Filtrer par priorité'), 'low');
    expect(screen.getByRole('article', { name: 'Idée future' })).toBeInTheDocument();
    expect(screen.queryByRole('article', { name: 'Tâche à annuler' })).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Filtrer par priorité'), 'high');
    expect(screen.getByText('Aucune tâche ne correspond aux filtres')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByRole('article', { name: 'Tâche à annuler' })).toBeInTheDocument();

    await user.click(
      within(screen.getByRole('article', { name: 'Tâche à annuler' })).getByRole('button', {
        name: 'Supprimer Tâche à annuler',
      }),
    );
    await user.click(screen.getByRole('button', { name: 'Confirmer' }));
    await waitFor(() => {
      expect(screen.queryByRole('article', { name: 'Tâche à annuler' })).not.toBeInTheDocument();
    });
  });

  it('affiche une tâche issue d’une proposition sans badge IA (UI épurée)', async () => {
    installMockStudyApi({
      tasks: [
        {
          id: 'ai-1',
          user_id: TEST_USER_ID,
          title: 'Relire le cours SQL',
          description: null,
          status: 'todo',
          priority: 'normal',
          due_at: null,
          completed_at: null,
          source: 'ai_proposal',
          proposal_id: 'prop-1',
          project_id: null,
          module_id: null,
          created_at: '2026-11-19T10:00:00.000Z',
          updated_at: '2026-11-19T10:00:00.000Z',
        },
      ],
    });

    renderTasksPage();

    const card = await screen.findByRole('article', { name: 'Relire le cours SQL' });
    expect(card).toBeInTheDocument();
    expect(within(card).queryByText('Origine IA')).not.toBeInTheDocument();
  });

  it('permet la capture rapide, le filtrage par tuile KPI et la bascule Liste / Tableau', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderTasksPage();

    await user.type(
      await screen.findByLabelText('Capture rapide de tâche'),
      'Réviser React Query',
    );
    await user.click(screen.getByRole('button', { name: 'Ajouter' }));

    expect(await screen.findByRole('article', { name: 'Réviser React Query' })).toBeInTheDocument();
    expect(screen.getByTestId('stat-active')).toHaveTextContent('1');

    await user.click(screen.getByRole('button', { name: 'Tableau' }));
    const board = screen.getByRole('region', { name: 'Tableau des tâches' });
    expect(within(board).getByRole('article', { name: 'Réviser React Query' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Liste' }));
    expect(screen.queryByRole('region', { name: 'Tableau des tâches' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Parking \(0\)/ }));
    expect(screen.getByText('Aucune tâche ne correspond aux filtres')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByRole('article', { name: 'Réviser React Query' })).toBeInTheDocument();
  });
});
