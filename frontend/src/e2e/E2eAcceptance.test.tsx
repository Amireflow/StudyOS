import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../app/providers';
import { appRoutes } from '../app/router';
import { STORAGE_KEYS } from '../lib/storage';
import type { AuthSession } from '../state/AuthContext';

const DEMO_SESSION: AuthSession = {
  mode: 'local_demo',
  accessToken: null,
  userId: 'local-user',
  email: 'local@amireflow.local',
  displayName: 'Khadim',
};

function renderAppAt(initialPath = '/', initialSession: AuthSession | null = DEMO_SESSION) {
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
  beforeEach(() => {
    window.localStorage.clear();
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
    const user = userEvent.setup();
    renderAppAt('/', DEMO_SESSION);

    expect(screen.getByRole('heading', { name: 'Tableau de bord' })).toBeInTheDocument();

    const sidebar = screen.getByRole('navigation', { name: 'Navigation principale' });
    await user.click(within(sidebar).getByRole('link', { name: 'Tâches' }));

    await user.click(screen.getByRole('button', { name: 'Nouvelle tâche' }));
    await user.type(screen.getByLabelText(/Titre/), 'Livrer Amireflow Study OS v1.0');
    await user.selectOptions(screen.getByLabelText('Priorité'), 'critical');
    await user.click(screen.getByRole('button', { name: 'Ajouter la tâche' }));

    const taskCard = screen.getByRole('article', { name: 'Livrer Amireflow Study OS v1.0' });
    await user.click(within(taskCard).getByRole('button', { name: 'Priorité' }));

    await user.click(within(sidebar).getByRole('link', { name: 'Tableau de bord' }));
    expect(
      screen.getAllByText('Livrer Amireflow Study OS v1.0').length,
    ).toBeGreaterThanOrEqual(1);

    await user.click(screen.getByRole('button', { name: 'Terminer cette tâche' }));

    await user.click(within(sidebar).getByRole('link', { name: 'Tâches' }));
    expect(screen.getByTestId('stat-done')).toHaveTextContent('1');
  });

  it('E2E-02 & E2E-03 : suit un parcours Python, ajoute une preuve sur une compétence, puis rejette et accepte une proposition du Copilote IA', async () => {
    const user = userEvent.setup();
    renderAppAt('/learning', DEMO_SESSION);

    const sidebar = screen.getByRole('navigation', { name: 'Navigation principale' });

    await user.click(screen.getByRole('button', { name: /Charger un parcours exemple/i }));
    expect(screen.getByText('Socle Python & FastAPI')).toBeInTheDocument();

    const finishLessonButtons = screen.getAllByRole('button', { name: 'Marquer terminée' });
    await user.click(finishLessonButtons[0]);
    expect(screen.getByText(/2\/2 leçons \(100%\)/)).toBeInTheDocument();

    await user.click(within(sidebar).getByRole('link', { name: 'Compétences' }));
    await user.click(screen.getByRole('button', { name: 'Nouvelle compétence' }));
    await user.type(screen.getByLabelText(/Nom de la compétence/), 'FastAPI & Pytest');
    await user.type(screen.getByLabelText(/Domaine/), 'Backend');
    await user.click(screen.getByRole('button', { name: 'Créer la compétence' }));

    await user.click(screen.getByRole('button', { name: 'Ajouter une preuve' }));
    await user.type(
      screen.getByLabelText(/Ce qui a été réalisé/),
      'Suite E2E complète validée sur les 8 lots',
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la preuve' }));
    expect(
      screen.getByText('Suite E2E complète validée sur les 8 lots'),
    ).toBeInTheDocument();

    await user.click(within(sidebar).getByRole('link', { name: 'Copilote IA' }));

    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Crée une tâche : « Tâche rejetée »',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));
    await user.click(screen.getByRole('button', { name: 'Rejeter' }));

    const storedAfterReject = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(storedAfterReject.tasks ?? []).toHaveLength(0);

    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Crée une tâche : « Tâche validée par E2E-03 »',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));
    await user.click(screen.getByRole('button', { name: 'Valider et exécuter' }));

    const storedAfterAccept = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(storedAfterAccept.tasks).toHaveLength(1);
    expect(storedAfterAccept.tasks[0].title).toBe('Tâche validée par E2E-03');
    expect(storedAfterAccept.tasks[0].source).toBe('ai_proposal');
  });
});
