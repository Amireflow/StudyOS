import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../app/providers';
import { appRoutes } from '../app/router';
import type { AuthSession } from '../state/AuthContext';
import { installMockStudyApi, TEST_API_SESSION } from '../test/mockStudyApi';

function renderAppAt(initialPath = '/', initialSession: AuthSession | null = TEST_API_SESSION) {
  const router = createMemoryRouter(appRoutes, {
    initialEntries: [initialPath],
  });
  return render(
    <AppProviders initialSession={initialSession}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

describe('Scénarios d’acceptation E2E (CdC §11.3 — Lot 8)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('E2E-04 : redirige vers /login sans session et ne propose aucun mode démo local', () => {
    renderAppAt('/', null);

    expect(
      screen.getByRole('heading', { name: 'Connexion' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Continuer en mode local/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Se connecter' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Créer un compte' })).toBeInTheDocument();
  });

  it('E2E-01 : crée une tâche prioritaire visible sur le dashboard et la termine', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderAppAt('/', TEST_API_SESSION);

    expect(await screen.findByRole('heading', { name: 'Tableau de bord' })).toBeInTheDocument();

    const sidebar = screen.getByRole('navigation', { name: 'Navigation principale' });
    await user.click(within(sidebar).getByRole('link', { name: 'Planning' }));
    const planningNav = screen.getByRole('navigation', { name: 'Navigation Planning' });
    await user.click(within(planningNav).getByRole('link', { name: 'Tâches' }));

    await user.click(await screen.findByRole('button', { name: 'Nouvelle tâche' }));
    await user.type(screen.getByLabelText(/Titre/), 'Livrer Amireflow Study OS v1.0');
    await user.selectOptions(screen.getByLabelText('Priorité'), 'critical');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));

    const taskCard = await screen.findByRole('article', { name: 'Livrer Amireflow Study OS v1.0' });
    await user.click(within(taskCard).getByRole('button', { name: 'Priorité' }));

    await user.click(within(sidebar).getByRole('link', { name: "Aujourd'hui" }));
    await waitFor(() => {
      expect(
        screen.getAllByText('Livrer Amireflow Study OS v1.0').length,
      ).toBeGreaterThanOrEqual(1);
    });

    await user.click(await screen.findByRole('button', { name: 'Terminer cette tâche' }));

    await user.click(within(sidebar).getByRole('link', { name: 'Planning' }));
    await user.click(within(screen.getByRole('navigation', { name: 'Navigation Planning' })).getByRole('link', { name: 'Tâches' }));
    await waitFor(() => {
      expect(screen.getByTestId('stat-done')).toHaveTextContent('1');
    });
  });

  it('E2E-02 & E2E-03 : suit un parcours Python, ajoute une preuve sur une compétence, puis rejette et accepte une proposition du Copilote IA', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderAppAt('/learning', TEST_API_SESSION);

    const sidebar = screen.getByRole('navigation', { name: 'Navigation principale' });

    expect(
      await screen.findByRole('button', { name: 'Nouveau parcours' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Charger un parcours exemple/i }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Nouveau parcours' }));
    await user.type(screen.getByLabelText(/Titre du parcours/), 'Socle Python & FastAPI');
    await user.type(screen.getByLabelText(/Objectif mesurable/), 'Concevoir une API REST');
    await user.click(screen.getByRole('button', { name: 'Créer le parcours' }));
    expect(await screen.findByText('Socle Python & FastAPI')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Ajouter un module' }));
    await user.type(screen.getByLabelText(/Titre du module/), 'Fondamentaux Python');
    await user.click(screen.getByRole('button', { name: 'Enregistrer le module' }));
    expect(await screen.findByText('Fondamentaux Python')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Ajouter une leçon' }));
    await user.type(screen.getByLabelText(/Titre de la leçon/), 'Schémas Pydantic v2');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la leçon' }));
    expect(await screen.findByText('Schémas Pydantic v2')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Marquer terminée' }));
    expect(await screen.findByText(/1\/1 leçon \(100%\)/)).toBeInTheDocument();

    const learningNav = screen.getByRole('navigation', { name: 'Navigation Apprendre' });
    await user.click(within(learningNav).getByRole('link', { name: 'Compétences' }));
    await user.click(await screen.findByRole('button', { name: 'Nouvelle compétence' }));
    await user.type(screen.getByLabelText(/Nom de la compétence/), 'FastAPI & Pytest');
    await user.type(screen.getByLabelText(/Domaine/), 'Backend');
    await user.click(screen.getByRole('button', { name: 'Créer la compétence' }));

    await user.click(await screen.findByRole('button', { name: 'Ajouter une preuve' }));
    await user.type(
      screen.getByLabelText(/Ce qui a été réalisé/),
      'Suite E2E complète validée sur les 8 lots',
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la preuve' }));
    expect(
      await screen.findByText('Suite E2E complète validée sur les 8 lots'),
    ).toBeInTheDocument();

    await user.click(within(sidebar).getByRole('link', { name: 'Copilote' }));

    await user.type(
      await screen.findByLabelText(/Votre message au Copilote/),
      'Crée une tâche : « Tâche rejetée »',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));
    await user.click(await screen.findByRole('button', { name: 'Rejeter' }));

    await waitFor(() => {
      expect(api.state.tasks).toHaveLength(0);
    });

    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Crée une tâche : « Tâche validée par E2E-03 »',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));
    await user.click(await screen.findByRole('button', { name: 'Valider et exécuter' }));

    await waitFor(() => {
      expect(api.state.tasks).toHaveLength(1);
    });
    expect(api.state.tasks[0].title).toBe('Tâche validée par E2E-03');
    expect(api.state.tasks[0].source).toBe('ai_proposal');
  });
});
