import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { PlanningPage } from './PlanningPage';

function renderPlanningPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <PlanningPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('PlanningPage', () => {
  it('valide fin > début (SCHED-01), crée et modifie un créneau', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    await user.click(screen.getByRole('button', { name: 'Nouveau créneau' }));
    await user.type(screen.getByLabelText(/Titre/), 'Cours de Python');

    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '14:00' } });
    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '13:00' } });
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'L’heure de fin doit être strictement postérieure à l’heure de début.',
    );

    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '16:00' } });
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));

    expect(screen.getByRole('heading', { level: 3, name: 'Cours de Python' })).toBeInTheDocument();
    expect(screen.getByTestId('planning-conflicts-count')).toHaveTextContent('0');

    await user.click(screen.getByRole('button', { name: 'Modifier' }));
    const titleInput = screen.getByLabelText(/Titre/);
    await user.clear(titleInput);
    await user.type(titleInput, 'Cours de Python avancé');
    await user.click(screen.getByRole('button', { name: 'Enregistrer les modifications' }));

    expect(
      screen.getByRole('heading', { level: 3, name: 'Cours de Python avancé' }),
    ).toBeInTheDocument();
  });

  it('signale un conflit avant enregistrement (SCHED-03), duplique vers la semaine suivante (SCHED-04) et supprime', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    // Créneau 1 : 09:00 - 11:00
    await user.click(screen.getByRole('button', { name: 'Nouveau créneau' }));
    await user.type(screen.getByLabelText(/Titre/), 'Cours de Python');
    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '09:00' } });
    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '11:00' } });
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));

    // Créneau 2 chevauchant : 10:00 - 12:00
    await user.click(screen.getByRole('button', { name: 'Nouveau créneau' }));
    await user.type(screen.getByLabelText(/Titre/), 'TD Bases de données');
    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '10:00' } });
    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '12:00' } });

    expect(screen.getByRole('alert')).toHaveTextContent('Conflit horaire détecté');
    expect(screen.getByRole('alert')).toHaveTextContent('Cours de Python');

    await user.click(screen.getByRole('button', { name: 'Enregistrer malgré le conflit' }));

    expect(screen.getByTestId('planning-conflicts-count')).toHaveTextContent('2');
    expect(screen.getAllByText('Conflit')).toHaveLength(2);

    // Duplication vers la semaine suivante
    await user.click(screen.getByRole('button', { name: 'Dupliquer vers la semaine suivante' }));
    expect(screen.getByRole('status')).toHaveTextContent(
      '2 créneaux dupliqués vers la semaine suivante.',
    );
    expect(screen.getByRole('heading', { level: 3, name: 'Cours de Python' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 3, name: 'TD Bases de données' }),
    ).toBeInTheDocument();

    // Suppression confirmée en deux clics
    await user.click(screen.getByRole('button', { name: 'Supprimer TD Bases de données' }));
    await user.click(screen.getByRole('button', { name: 'Confirmer' }));

    expect(
      screen.queryByRole('heading', { level: 3, name: 'TD Bases de données' }),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId('planning-conflicts-count')).toHaveTextContent('0');
  });
});
