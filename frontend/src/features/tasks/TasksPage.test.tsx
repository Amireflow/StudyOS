import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { STORAGE_KEYS } from '../../lib/storage';
import { TasksPage } from './TasksPage';

function renderTasksPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <TasksPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('TasksPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('valide les champs obligatoires puis crée, modifie et termine une tâche (TASK-01)', async () => {
    const user = userEvent.setup();
    renderTasksPage();

    await user.click(screen.getByRole('button', { name: 'Nouvelle tâche' }));
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Le titre doit contenir au moins 2 caractères.',
    );

    await user.type(screen.getByLabelText(/Titre/), 'Apprendre Pydantic');
    await user.selectOptions(screen.getByLabelText('Priorité'), 'high');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));

    expect(screen.getByRole('status')).toHaveTextContent('Apprendre Pydantic');
    expect(screen.getByTestId('stat-active')).toHaveTextContent('1');

    const card = screen.getByRole('article', { name: 'Apprendre Pydantic' });
    await user.click(within(card).getByRole('button', { name: 'Modifier' }));
    const titleInput = screen.getByLabelText(/Titre/);
    await user.clear(titleInput);
    await user.type(titleInput, 'Apprendre Pydantic v2');
    await user.click(screen.getByRole('button', { name: 'Enregistrer les modifications' }));

    const updatedCard = screen.getByRole('article', { name: 'Apprendre Pydantic v2' });
    await user.click(within(updatedCard).getByRole('button', { name: 'Terminer' }));

    expect(screen.getByTestId('stat-done')).toHaveTextContent('1');
    expect(screen.getByTestId('stat-active')).toHaveTextContent('0');
    expect(within(updatedCard).getByText(/Terminée le/)).toBeInTheDocument();
  });

  it('ne compte pas une tâche annulée comme terminée (TASK-02) et supporte le parking + filtres combinés (TASK-03)', async () => {
    const user = userEvent.setup();
    renderTasksPage();

    // Créer 2 tâches
    await user.click(screen.getByRole('button', { name: 'Nouvelle tâche' }));
    await user.type(screen.getByLabelText(/Titre/), 'Tâche à annuler');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));

    await user.click(screen.getByRole('button', { name: 'Nouvelle tâche' }));
    await user.type(screen.getByLabelText(/Titre/), 'Idée future');
    await user.selectOptions(screen.getByLabelText('Priorité'), 'low');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));

    // Annuler la première
    const cancelCard = screen.getByRole('article', { name: 'Tâche à annuler' });
    await user.click(within(cancelCard).getByRole('button', { name: 'Annuler' }));
    expect(screen.getByTestId('stat-done')).toHaveTextContent('0');

    // Mettre la seconde au parking
    const parkedCard = screen.getByRole('article', { name: 'Idée future' });
    await user.click(within(parkedCard).getByRole('button', { name: 'Parking' }));
    expect(screen.getByTestId('stat-parked')).toHaveTextContent('1');

    // Combiner filtres statut=parked + priorité=low
    await user.selectOptions(screen.getByLabelText('Filtrer par statut'), 'parked');
    await user.selectOptions(screen.getByLabelText('Filtrer par priorité'), 'low');
    expect(screen.getByRole('article', { name: 'Idée future' })).toBeInTheDocument();
    expect(screen.queryByRole('article', { name: 'Tâche à annuler' })).not.toBeInTheDocument();

    // Combiner avec priorité=high -> aucune correspondance
    await user.selectOptions(screen.getByLabelText('Filtrer par priorité'), 'high');
    expect(screen.getByText('Aucune tâche ne correspond aux filtres')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByRole('article', { name: 'Tâche à annuler' })).toBeInTheDocument();

    // Suppression confirmée en deux clics
    await user.click(
      within(screen.getByRole('article', { name: 'Tâche à annuler' })).getByRole('button', {
        name: 'Supprimer Tâche à annuler',
      }),
    );
    await user.click(screen.getByRole('button', { name: 'Confirmer' }));
    expect(screen.queryByRole('article', { name: 'Tâche à annuler' })).not.toBeInTheDocument();
  });

  it('affiche une tâche issue d’une proposition sans badge IA (UI épurée)', () => {
    window.localStorage.setItem(
      STORAGE_KEYS.studyState,
      JSON.stringify({
        activePriorityTitle: null,
        activePriorityTaskId: null,
        tasks: [
          {
            id: 'ai-1',
            userId: 'local-user',
            title: 'Relire le cours SQL',
            description: null,
            status: 'todo',
            priority: 'normal',
            dueAt: null,
            completedAt: null,
            source: 'ai_proposal',
            proposalId: 'prop-1',
            projectId: null,
            moduleId: null,
            createdAt: '2026-11-19T10:00:00.000Z',
            updatedAt: '2026-11-19T10:00:00.000Z',
          },
        ],
        sessions: [],
      }),
    );

    renderTasksPage();

    const card = screen.getByRole('article', { name: 'Relire le cours SQL' });
    expect(card).toBeInTheDocument();
    expect(within(card).queryByText('Origine IA')).not.toBeInTheDocument();
  });

  it('permet la capture rapide, le filtrage par tuile KPI et la bascule Liste / Tableau', async () => {
    const user = userEvent.setup();
    renderTasksPage();

    // Capture rapide en ligne
    await user.type(screen.getByLabelText('Capture rapide de tâche'), 'Réviser React Query');
    await user.click(screen.getByRole('button', { name: 'Ajouter' }));

    expect(screen.getByRole('article', { name: 'Réviser React Query' })).toBeInTheDocument();
    expect(screen.getByTestId('stat-active')).toHaveTextContent('1');

    // Bascule en vue Tableau Kanban puis retour en Liste
    await user.click(screen.getByRole('button', { name: 'Tableau' }));
    const board = screen.getByRole('region', { name: 'Tableau des tâches' });
    expect(within(board).getByRole('article', { name: 'Réviser React Query' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Liste' }));
    expect(screen.queryByRole('region', { name: 'Tableau des tâches' })).not.toBeInTheDocument();

    // Filtre via tuile KPI Parking puis réinitialisation
    await user.click(screen.getByRole('button', { name: /Parking \(0\)/ }));
    expect(screen.getByText('Aucune tâche ne correspond aux filtres')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByRole('article', { name: 'Réviser React Query' })).toBeInTheDocument();
  });
});
