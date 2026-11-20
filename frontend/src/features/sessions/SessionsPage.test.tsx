import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { SessionsPage } from './SessionsPage';

function renderSessionsPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <SessionsPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('SessionsPage', () => {
  it('permet de démarrer puis clôturer une séance avec un résultat obligatoire (SESSION-02)', async () => {
    const user = userEvent.setup();
    renderSessionsPage();

    await user.click(screen.getAllByRole('button', { name: 'Démarrer une séance' })[0]);
    await user.type(screen.getByLabelText(/Titre de la séance/), 'Pratique React Hooks');
    await user.click(screen.getByRole('button', { name: 'Lancer la séance' }));

    expect(screen.getByTestId('sessions-in-progress-count')).toHaveTextContent('1');
    expect(screen.getByTestId('sessions-completed-count')).toHaveTextContent('0');

    // Validation résultat obligatoire
    await user.click(screen.getByRole('button', { name: 'Terminer la séance' }));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Notez brièvement ce qui a été produit ou appris.',
    );

    await user.type(
      screen.getByLabelText(/Résultat ou note de fin/),
      'Formulaire de séance connecté au store local.',
    );
    await user.click(screen.getByRole('button', { name: 'Terminer la séance' }));

    expect(screen.getByTestId('sessions-in-progress-count')).toHaveTextContent('0');
    expect(screen.getByTestId('sessions-completed-count')).toHaveTextContent('1');
    expect(
      screen.getByText('Formulaire de séance connecté au store local.'),
    ).toBeInTheDocument();
  });

  it('exclut une séance annulée des totaux achevés (SESSION-03)', async () => {
    const user = userEvent.setup();
    renderSessionsPage();

    await user.click(screen.getAllByRole('button', { name: 'Démarrer une séance' })[0]);
    await user.type(screen.getByLabelText(/Titre de la séance/), 'Séance interrompue');
    await user.click(screen.getByRole('button', { name: 'Lancer la séance' }));

    await user.click(screen.getByRole('button', { name: 'Annuler la séance' }));
    await user.click(screen.getByRole('button', { name: 'Confirmer' }));

    expect(screen.getByTestId('sessions-in-progress-count')).toHaveTextContent('0');
    expect(screen.getByTestId('sessions-completed-count')).toHaveTextContent('0');
    expect(screen.getByTestId('sessions-total-time')).toHaveTextContent('0 min');
  });

  it('rejette une fin antérieure au début puis calcule la durée en saisie manuelle (SESSION-01)', async () => {
    const user = userEvent.setup();
    renderSessionsPage();

    await user.click(screen.getByRole('button', { name: 'Enregistrer une séance passée' }));
    await user.type(screen.getByLabelText(/Titre de la séance/), 'TP PostgreSQL');

    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '2026-11-19T14:00' } });
    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '2026-11-19T13:30' } });
    await user.type(screen.getByLabelText(/Résultat ou note de fin/), 'Requêtes SQL testées.');

    await user.click(screen.getByRole('button', { name: 'Enregistrer la séance' }));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'La date de fin doit être strictement postérieure au début.',
    );

    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '2026-11-19T15:30' } });
    expect(screen.getByText('Durée calculée : 1 h 30')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Enregistrer la séance' }));
    expect(screen.getByTestId('sessions-completed-count')).toHaveTextContent('1');
    expect(screen.getByTestId('sessions-total-time')).toHaveTextContent('1 h 30');
  });
});
