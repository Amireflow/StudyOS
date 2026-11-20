import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { STORAGE_KEYS } from '../../lib/storage';
import { ProjectsPage } from './ProjectsPage';

function renderProjectsPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <ProjectsPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('ProjectsPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('exige une prochaine action pour un projet actif (PROJ-02), avertit au-delà de 3 actifs (PROJ-01) et définit le projet prioritaire (PROJ-03)', async () => {
    const user = userEvent.setup();

    // 3 projets actifs préexistants
    const now = new Date().toISOString();
    window.localStorage.setItem(
      STORAGE_KEYS.learningState,
      JSON.stringify({
        paths: [],
        modules: [],
        lessons: [],
        skills: [],
        evidence: [],
        projects: [1, 2, 3].map((idx) => ({
          id: `proj-${idx}`,
          userId: 'local-user',
          name: `Projet actif ${idx}`,
          description: null,
          goal: `Objectif ${idx}`,
          status: 'active',
          priority: 'normal',
          nextAction: `Action concrète ${idx}`,
          deliverables: null,
          targetDate: null,
          createdAt: now,
          updatedAt: now,
        })),
      }),
    );

    renderProjectsPage();

    // Tenter de créer un 4e projet actif sans prochaine action -> erreur PROJ-02
    await user.click(screen.getByRole('button', { name: 'Nouveau projet' }));
    await user.type(screen.getByLabelText(/Nom du projet/), 'Amireflow OS');
    await user.type(screen.getByLabelText(/Objectif mesurable/), 'Livrer le Lot 6');
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Une prochaine action concrète est obligatoire pour un projet actif.',
    );

    // Renseigner la prochaine action et créer le 4e projet actif -> alerte anti-dispersion PROJ-01
    await user.type(screen.getByLabelText(/Prochaine action concrète/), 'Lancer les tests finaux');
    await user.type(screen.getByLabelText(/Livrables/), 'Backend Lot 6\nFrontend Lot 6');
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Attention à la dispersion (4 projets actifs)');
    expect(screen.getByText('Backend Lot 6')).toBeInTheDocument();

    // Définir comme priorité principale (PROJ-03)
    const prioButtons = screen.getAllByRole('button', { name: 'Définir comme priorité' });
    await user.click(prioButtons[0]);

    const studyStored = JSON.parse(window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}');
    expect(studyStored.activePriorityProjectId).toBeTruthy();
  });

  it('convertit la prochaine action en tâche liée, filtre par recherche/statut et bascule entre Liste et Tableau', async () => {
    const user = userEvent.setup();
    renderProjectsPage();

    await user.click(screen.getByRole('button', { name: 'Nouveau projet' }));
    await user.type(screen.getByLabelText(/Nom du projet/), 'Refonte API');
    await user.type(screen.getByLabelText(/Objectif mesurable/), '100% des endpoints couverts');
    await user.type(
      screen.getByLabelText(/Prochaine action concrète/),
      'Écrire les tests Pytest des projets',
    );
    await user.click(screen.getByRole('button', { name: '+14 j' }));
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    // Conversion 1-clic de la prochaine action en tâche liée
    await user.click(
      screen.getByRole('button', {
        name: 'Convertir la prochaine action de Refonte API en tâche',
      }),
    );
    expect(screen.getByText('Tâche liée')).toBeInTheDocument();

    const studyStored = JSON.parse(window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}');
    expect(studyStored.tasks).toHaveLength(1);
    expect(studyStored.tasks[0].title).toBe('Écrire les tests Pytest des projets');

    // Bascule en vue Tableau puis retour Liste
    await user.click(screen.getByRole('button', { name: 'Tableau' }));
    expect(screen.getByRole('heading', { name: 'Planifiés' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Liste' }));

    // Recherche sans résultat puis réinitialisation
    await user.type(screen.getByLabelText('Rechercher un projet'), 'Inexistant');
    expect(
      screen.getByText('Aucun projet ne correspond aux filtres'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByRole('article', { name: 'Refonte API' })).toBeInTheDocument();
  });
});
