import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AuthSession } from '../state/AuthContext';
import { installMockStudyApi, TEST_API_SESSION } from '../test/mockStudyApi';
import { AppProviders } from './providers';
import { appRoutes } from './router';

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

describe('Navigation principale et routage', () => {
  beforeEach(() => {
    installMockStudyApi();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('redirige vers /login sans session active (AUTH-02)', () => {
    renderAppAt('/', null);

    expect(screen.getByRole('heading', { level: 1, name: 'Amireflow Study OS' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Connexion' })).toBeInTheDocument();
  });

  it('affiche le Tableau de bord et la priorité principale au démarrage', async () => {
    renderAppAt('/');

    expect(await screen.findByRole('heading', { level: 2, name: 'Priorité principale' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Tableau de bord' })).toBeInTheDocument();

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
    expect(await screen.findByRole('heading', { level: 1, name: 'Tâches' })).toBeInTheDocument();
    expect(within(desktopNav).getByRole('link', { name: 'Tâches' })).toHaveAttribute(
      'aria-current',
      'page',
    );

    await user.click(within(desktopNav).getByRole('link', { name: 'Séances' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Séances' })).toBeInTheDocument();
    expect(within(desktopNav).getByRole('link', { name: 'Séances' })).toHaveAttribute(
      'aria-current',
      'page',
    );

    await user.click(within(desktopNav).getByRole('link', { name: 'Planning' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Planning' })).toBeInTheDocument();

    await user.click(within(desktopNav).getByRole('link', { name: 'Paramètres' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Paramètres' })).toBeInTheDocument();

    const mobileQuickNav = screen.getByRole('navigation', { name: 'Accès rapide mobile' });
    await user.click(within(mobileQuickNav).getByRole('link', { name: 'Accueil' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Tableau de bord' })).toBeInTheDocument();
  });

  it('affiche cinq entrées mobiles et les espaces regroupés avec leur sous-navigation', async () => {
    renderAppAt('/tasks');

    const desktopNav = screen.getByRole('navigation', { name: 'Navigation principale' });
    expect(within(desktopNav).getByText('APPRENTISSAGE')).toBeInTheDocument();
    expect(within(desktopNav).getByText('ORGANISATION')).toBeInTheDocument();
    expect(within(desktopNav).getByRole('link', { name: 'Cours' })).toHaveAttribute('href', '/courses');
    expect(within(desktopNav).getByRole('link', { name: 'Parcours' })).toHaveAttribute('href', '/learning');

    const mobileNav = screen.getByRole('navigation', { name: 'Accès rapide mobile' });
    expect(within(mobileNav).getAllByRole('link')).toHaveLength(5);
    expect(within(mobileNav).getByRole('link', { name: 'Organiser' })).toHaveAttribute('aria-current', 'page');

    const sectionNav = screen.getByRole('navigation', { name: 'Navigation Organisation' });
    expect(within(sectionNav).getByRole('link', { name: 'Tâches' })).toHaveAttribute('aria-current', 'page');
    expect(within(sectionNav).getByRole('link', { name: 'Planning' })).toHaveAttribute('href', '/planning');
    expect(within(sectionNav).getByRole('link', { name: 'Séances' })).toHaveAttribute('href', '/sessions');
  });

  it('ouvre et ferme le tiroir de navigation mobile', async () => {
    const user = userEvent.setup();
    renderAppAt('/');

    const openButton = await screen.findByRole('button', { name: 'Ouvrir le menu' });
    expect(openButton).toHaveAttribute('aria-expanded', 'false');

    await user.click(openButton);

    const dialog = screen.getByRole('dialog', { name: 'Menu de navigation' });
    expect(dialog).toBeInTheDocument();

    const mobileNav = within(dialog).getByRole('navigation', { name: 'Navigation mobile' });
    await user.click(within(mobileNav).getByRole('link', { name: 'Compétences' }));

    expect(screen.queryByRole('dialog', { name: 'Menu de navigation' })).not.toBeInTheDocument();
    expect(await screen.findByRole('heading', { level: 1, name: 'Compétences' })).toBeInTheDocument();
  });

  it('confine le focus dans le tiroir mobile, ferme avec Échap et restaure le déclencheur', async () => {
    const user = userEvent.setup();
    renderAppAt('/');

    const trigger = await screen.findByRole('button', { name: 'Ouvrir le menu' });
    await user.click(trigger);

    const dialog = screen.getByRole('dialog', { name: 'Menu de navigation' });
    const focusable = Array.from(
      dialog.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    expect(document.activeElement).toBe(first);
    await user.tab({ shift: true });
    expect(document.activeElement).toBe(last);
    await user.tab();
    expect(document.activeElement).toBe(first);

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog', { name: 'Menu de navigation' })).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it('affiche la page 404 pour une route inconnue', () => {
    renderAppAt('/route-inexistante');

    expect(screen.getByRole('heading', { level: 1, name: 'Page introuvable' })).toBeInTheDocument();
  });
});
