import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import type { AuthSession } from '../state/AuthContext';
import { AppProviders } from './providers';
import { appRoutes } from './router';

const DEMO_SESSION: AuthSession = {
  mode: 'local_demo',
  accessToken: null,
  userId: 'local-user',
  email: 'local@amireflow.local',
  displayName: 'Mode local',
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

describe('Navigation principale et routage', () => {
  it('redirige vers /login sans session active (AUTH-02)', () => {
    renderAppAt('/', null);

    expect(screen.getByRole('heading', { level: 1, name: 'Amireflow Study OS' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Connexion' })).toBeInTheDocument();
  });

  it('affiche le Tableau de bord et la priorité principale au démarrage', () => {
    renderAppAt('/');

    expect(screen.getByRole('heading', { level: 1, name: 'Tableau de bord' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Priorité principale' })).toBeInTheDocument();

    const desktopNav = screen.getByRole('navigation', { name: 'Navigation principale' });
    expect(within(desktopNav).getByRole('link', { name: 'Tableau de bord' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('navigue vers Tâches, Séances, Planning et Paramètres via la barre latérale', async () => {
    const user = userEvent.setup();
    renderAppAt('/');

    const desktopNav = screen.getByRole('navigation', { name: 'Navigation principale' });

    await user.click(within(desktopNav).getByRole('link', { name: 'Tâches' }));
    expect(screen.getByRole('heading', { level: 1, name: 'Tâches' })).toBeInTheDocument();
    expect(within(desktopNav).getByRole('link', { name: 'Tâches' })).toHaveAttribute(
      'aria-current',
      'page',
    );

    await user.click(within(desktopNav).getByRole('link', { name: 'Séances' }));
    expect(screen.getByRole('heading', { level: 1, name: 'Séances' })).toBeInTheDocument();
    expect(within(desktopNav).getByRole('link', { name: 'Séances' })).toHaveAttribute(
      'aria-current',
      'page',
    );

    await user.click(within(desktopNav).getByRole('link', { name: 'Planning' }));
    expect(screen.getByRole('heading', { level: 1, name: 'Planning' })).toBeInTheDocument();

    await user.click(within(desktopNav).getByRole('link', { name: 'Paramètres' }));
    expect(screen.getByRole('heading', { level: 1, name: 'Paramètres' })).toBeInTheDocument();

    const mobileQuickNav = screen.getByRole('navigation', { name: 'Accès rapide mobile' });
    await user.click(within(mobileQuickNav).getByRole('link', { name: 'Accueil' }));
    expect(screen.getByRole('heading', { level: 1, name: 'Tableau de bord' })).toBeInTheDocument();
  });

  it('ouvre et ferme le tiroir de navigation mobile', async () => {
    const user = userEvent.setup();
    renderAppAt('/');

    const openButton = screen.getByRole('button', { name: 'Ouvrir le menu' });
    expect(openButton).toHaveAttribute('aria-expanded', 'false');

    await user.click(openButton);

    const dialog = screen.getByRole('dialog', { name: 'Menu de navigation' });
    expect(dialog).toBeInTheDocument();

    const mobileNav = within(dialog).getByRole('navigation', { name: 'Navigation mobile' });
    await user.click(within(mobileNav).getByRole('link', { name: 'Compétences' }));

    expect(screen.queryByRole('dialog', { name: 'Menu de navigation' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Compétences' })).toBeInTheDocument();
  });

  it('affiche la page 404 pour une route inconnue', () => {
    renderAppAt('/route-inexistante');

    expect(screen.getByRole('heading', { level: 1, name: 'Page introuvable' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Retour au tableau de bord' })).toHaveAttribute(
      'href',
      '/',
    );
  });
});
