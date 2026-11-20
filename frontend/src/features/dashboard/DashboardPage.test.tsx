import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { DashboardPage } from './DashboardPage';

function renderDashboardPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('DashboardPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('affiche les états vides guidés au départ (DASH-02) et permet de définir la priorité principale', async () => {
    const user = userEvent.setup();
    renderDashboardPage();

    expect(screen.getByText('Aucune priorité principale active')).toBeInTheDocument();
    expect(screen.getByText('Aucune tâche enregistrée')).toBeInTheDocument();
    expect(screen.getByText('Aucune séance achevée')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Définir une priorité' }));
    await user.type(
      screen.getByLabelText(/Intitulé de la priorité principale/),
      'Boucler le Lot 2 frontend',
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la priorité' }));

    expect(screen.getByText('Boucler le Lot 2 frontend')).toBeInTheDocument();
  });

  it('calcule en temps réel la progression après chargement d’exemples et achèvement d’une tâche (DASH-01, DASH-03)', async () => {
    const user = userEvent.setup();
    renderDashboardPage();

    await user.click(screen.getByRole('button', { name: 'Charger des données d’exemple' }));

    // Dans les données d'exemple : 2 actives, 1 done, 1 parked -> completionRate = 33 % ; 2 séances achevées = 2 h 05 ; planning du jour visible
    expect(screen.getByTestId('dashboard-completion-rate')).toHaveTextContent('33 %');
    expect(screen.getByTestId('dashboard-sessions-count')).toHaveTextContent('2');
    expect(screen.getByTestId('dashboard-sessions-time')).toHaveTextContent('2 h 05');
    expect(screen.getByText('Cours d’algorithmique')).toBeInTheDocument();

    await user.click(
      screen.getByRole('button', {
        name: 'Terminer Consolider les formulaires React et la validation Zod',
      }),
    );

    // Maintenant 1 active, 2 done -> completionRate = 67 %
    expect(screen.getByTestId('dashboard-completion-rate')).toHaveTextContent('67 %');
  });

  it('permet de capturer une tâche rapide et de démarrer une séance depuis la priorité principale', async () => {
    const user = userEvent.setup();
    renderDashboardPage();

    // Capture rapide d'une tâche
    await user.click(screen.getByRole('button', { name: 'Nouvelle tâche' }));
    await user.type(screen.getByLabelText('Nouvelle tâche rapide'), 'Préparer le TP SQL');
    await user.click(screen.getByRole('button', { name: 'Ajouter' }));

    expect(screen.getByText('Préparer le TP SQL')).toBeInTheDocument();

    // Définir une priorité puis lancer une séance directe
    await user.click(screen.getByRole('button', { name: 'Définir une priorité' }));
    await user.type(
      screen.getByLabelText(/Intitulé de la priorité principale/),
      'Boucler la refonte UI',
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la priorité' }));

    await user.click(screen.getByRole('button', { name: 'Lancer une séance' }));

    const activeBanner = screen.getByText(/Séance en cours :/).closest('div');
    expect(activeBanner).toHaveTextContent('Boucler la refonte UI');
    expect(screen.getByRole('link', { name: 'Clôturer' })).toHaveAttribute('href', '/sessions');
  });
});
