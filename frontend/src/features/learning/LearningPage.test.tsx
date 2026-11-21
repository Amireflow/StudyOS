import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { installMockStudyApi, TEST_API_SESSION, TEST_USER_ID } from '../../test/mockStudyApi';
import { LearningPage } from './LearningPage';

function renderLearningPage() {
  return render(
    <AppProviders initialSession={TEST_API_SESSION}>
      <MemoryRouter>
        <LearningPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('LearningPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('crée un parcours, un module et une leçon, valide l’URL et respecte LEARN-03 sans bouton d’exemple', async () => {
    const nowIso = new Date().toISOString();
    const api = installMockStudyApi({
      skills: [
        {
          id: 'skill-1',
          user_id: TEST_USER_ID,
          name: 'FastAPI',
          domain: 'Backend',
          description: null,
          current_level: 0,
          target_level: 4,
          last_assessed_at: null,
          created_at: nowIso,
          updated_at: nowIso,
        },
      ],
    });

    const user = userEvent.setup();
    renderLearningPage();

    await user.click(await screen.findByText('Plus'));
    await user.click(await screen.findByRole('button', { name: 'Créer manuellement' }));
    expect(
      screen.queryByRole('button', { name: /Charger un parcours exemple/i }),
    ).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/Titre du parcours/), 'Backend Python');
    await user.type(screen.getByLabelText(/Objectif mesurable/), 'Maîtriser FastAPI et SQLAlchemy 2');
    await user.click(screen.getByRole('button', { name: 'Créer le parcours' }));

    expect(await screen.findByText('Backend Python')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Ajouter un module' }));
    await user.type(screen.getByLabelText(/Titre du module/), 'Pydantic & API');
    await user.click(screen.getByRole('button', { name: 'Enregistrer le module' }));

    expect(await screen.findByText('Pydantic & API')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Ajouter une leçon' }));
    await user.type(screen.getByLabelText(/Titre de la leçon/), 'Validateurs Pydantic');
    await user.type(screen.getByLabelText(/Ressource \(URL/), 'javascript:alert(1)');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la leçon' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'L’URL doit commencer par http:// ou https://.',
    );

    const urlInput = screen.getByLabelText(/Ressource \(URL/);
    await user.clear(urlInput);
    await user.type(urlInput, 'https://docs.pydantic.dev/latest/');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la leçon' }));

    expect(await screen.findByText('Validateurs Pydantic')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Marquer terminée' }));
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('aucune compétence validée automatiquement');
    });
    expect(screen.getByText(/1\/1 leçon \(100%\)/)).toBeInTheDocument();
    expect(screen.getByTestId('learning-completed-lessons')).toHaveTextContent('1 / 1');
    expect(screen.getByTestId('learning-studied-lessons')).toHaveTextContent('1 leçon étudiée');
    expect(screen.getByTestId('learning-validated-skills')).toHaveTextContent('0 / 0');

    expect(api.state.skills[0].current_level).toBe(0);
    expect(api.state.skills[0].last_assessed_at).toBeNull();
  });

  it('affiche la prochaine leçon d’un parcours API, replie un module et filtre par recherche', async () => {
    const nowIso = new Date().toISOString();
    installMockStudyApi({
      paths: [
        {
          id: 'path-1',
          user_id: TEST_USER_ID,
          title: 'Socle Python & FastAPI',
          description: 'Parcours progressif axé sur la pratique et les tests automatisés.',
          goal: 'Concevoir et tester une API REST typée avec persistance SQL',
          status: 'active',
          created_at: nowIso,
          updated_at: nowIso,
        },
      ],
      modules: [
        {
          id: 'mod-1',
          user_id: TEST_USER_ID,
          path_id: 'path-1',
          title: 'Fondamentaux Python & Pydantic',
          description: 'Typage strict et gestion des erreurs.',
          position: 1,
          status: 'active',
          created_at: nowIso,
          updated_at: nowIso,
        },
      ],
      lessons: [
        {
          id: 'les-1',
          user_id: TEST_USER_ID,
          module_id: 'mod-1',
          title: 'Schémas Pydantic v2 & validateurs',
          content: 'Normaliser les textes.',
          resource_url: 'https://docs.pydantic.dev/latest/',
          position: 1,
          status: 'completed',
          created_at: nowIso,
          updated_at: nowIso,
        },
        {
          id: 'les-2',
          user_id: TEST_USER_ID,
          module_id: 'mod-1',
          title: 'Requêtes SQLAlchemy 2 & isolation user_id',
          content: 'Filtrer par utilisateur.',
          resource_url: null,
          position: 2,
          status: 'active',
          created_at: nowIso,
          updated_at: nowIso,
        },
      ],
    });

    const user = userEvent.setup();
    renderLearningPage();

    expect(await screen.findByText('Socle Python & FastAPI')).toBeInTheDocument();
    expect(screen.getByText('Prochaine leçon')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Charger un parcours exemple/i }),
    ).not.toBeInTheDocument();

    const toggleModuleButtons = screen.getAllByRole('button', {
      name: /Replier ou déplier le module/i,
    });
    expect(toggleModuleButtons[0]).toHaveAttribute('aria-expanded', 'true');

    await user.click(toggleModuleButtons[0]);
    expect(toggleModuleButtons[0]).toHaveAttribute('aria-expanded', 'false');

    await user.click(toggleModuleButtons[0]);
    expect(toggleModuleButtons[0]).toHaveAttribute('aria-expanded', 'true');

    await user.type(screen.getByLabelText('Rechercher un parcours'), 'introuvable');
    expect(screen.getByText('Aucun parcours ne correspond aux filtres')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByText('Socle Python & FastAPI')).toBeInTheDocument();
  });
});
