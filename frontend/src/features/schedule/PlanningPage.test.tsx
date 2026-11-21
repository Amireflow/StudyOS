import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { installMockStudyApi, TEST_API_SESSION } from '../../test/mockStudyApi';
import { PlanningPage } from './PlanningPage';

function renderPlanningPage() {
  return render(
    <AppProviders initialSession={TEST_API_SESSION}>
      <MemoryRouter>
        <PlanningPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('PlanningPage', () => {
  beforeEach(() => {
    installMockStudyApi();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('valide fin > début (SCHED-01), crée et modifie un créneau sans bouton d’exemple', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    await user.click(screen.getByText('Plus'));
    await user.click(await screen.findByRole('button', { name: 'Ajouter un événement ponctuel' }));
    expect(
      screen.queryByRole('button', { name: /Charger des données d’exemple/i }),
    ).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/Titre/), 'Cours de Python');

    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '14:00' } });
    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '13:00' } });
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'L’heure de fin doit être strictement postérieure à l’heure de début.',
    );

    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '16:00' } });
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));

    expect(
      await screen.findByRole('heading', { level: 3, name: 'Cours de Python' }),
    ).toBeInTheDocument();
    expect(screen.getByTestId('planning-conflicts-count')).toHaveTextContent('0');

    await user.click(screen.getByRole('button', { name: 'Modifier' }));
    const titleInput = screen.getByLabelText(/Titre/);
    await user.clear(titleInput);
    await user.type(titleInput, 'Cours de Python avancé');
    await user.click(screen.getByRole('button', { name: 'Enregistrer les modifications' }));

    expect(
      await screen.findByRole('heading', { level: 3, name: 'Cours de Python avancé' }),
    ).toBeInTheDocument();
  });

  it('expose les sept jours comme boutons accessibles et les filtres comme états pressés', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    const dayButtons = await screen.findAllByRole('button', { name: /^Sélectionner / });
    expect(dayButtons).toHaveLength(7);
    expect(dayButtons[0]).toHaveAttribute('aria-pressed', 'false');

    await user.click(dayButtons[0]);
    expect(dayButtons[0]).toHaveAttribute('aria-pressed', 'true');

    await user.click(screen.getByText('Plus'));
    await user.click(await screen.findByRole('button', { name: 'Ajouter un événement ponctuel' }));
    await user.type(screen.getByLabelText(/Titre/), 'Atelier filtre');
    await user.selectOptions(screen.getByLabelText(/Type/), 'project');
    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '09:00' } });
    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '10:00' } });
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));

    const typeFilters = screen.getByRole('group', { name: 'Filtrer les créneaux par type' });
    const projectFilter = within(typeFilters).getByRole('button', { name: 'Projet' });
    await user.click(projectFilter);
    expect(projectFilter).toHaveAttribute('aria-pressed', 'true');
    const allFilter = within(typeFilters).getByRole('button', { name: 'Tous' });
    await user.click(allFilter);
    expect(allFilter).toHaveAttribute('aria-pressed', 'true');

    const viewSwitcher = screen.getByRole('group', { name: 'Choisir la vue du planning' });
    expect(within(viewSwitcher).getByRole('button', { name: 'Agenda' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('signale un conflit avant enregistrement (SCHED-03), duplique vers la semaine suivante (SCHED-04) et supprime', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    await user.click(screen.getByText('Plus'));
    await user.click(await screen.findByRole('button', { name: 'Ajouter un événement ponctuel' }));
    await user.type(screen.getByLabelText(/Titre/), 'Cours de Python');
    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '09:00' } });
    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '11:00' } });
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));
    expect(
      await screen.findByRole('heading', { level: 3, name: 'Cours de Python' }),
    ).toBeInTheDocument();

    await user.click(screen.getByText('Plus'));
    await user.click(screen.getByRole('button', { name: 'Ajouter un événement ponctuel' }));
    await user.type(screen.getByLabelText(/Titre/), 'TD Bases de données');
    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '10:00' } });
    fireEvent.change(screen.getByLabelText(/Fin/), { target: { value: '12:00' } });

    expect(screen.getByRole('alert')).toHaveTextContent('Conflit horaire détecté');
    expect(screen.getByRole('alert')).toHaveTextContent('Cours de Python');

    await user.click(screen.getByRole('button', { name: 'Enregistrer malgré le conflit' }));

    await waitFor(() => {
      expect(screen.getByTestId('planning-conflicts-count')).toHaveTextContent('2');
    });
    expect(screen.getAllByText('Conflit')).toHaveLength(2);

    await user.click(screen.getByRole('button', { name: 'Dupliquer vers la semaine suivante' }));
    expect(await screen.findByRole('status')).toHaveTextContent(
      '2 créneaux dupliqués vers la semaine suivante.',
    );

    await user.click(screen.getByRole('button', { name: 'Supprimer TD Bases de données' }));
    await user.click(screen.getByRole('button', { name: 'Confirmer' }));

    await waitFor(() => {
      expect(
        screen.queryByRole('heading', { level: 3, name: 'TD Bases de données' }),
      ).not.toBeInTheDocument();
      expect(screen.getByTestId('planning-conflicts-count')).toHaveTextContent('0');
    });
  });

  it('propose des raccourcis de durée, filtre par catégorie et bascule entre Agenda et Grille', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    await user.click(screen.getByText('Plus'));
    await user.click(await screen.findByRole('button', { name: 'Ajouter un événement ponctuel' }));
    await user.type(screen.getByLabelText(/Titre/), 'Atelier UI');
    await user.selectOptions(screen.getByLabelText(/Type/), 'project');
    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '09:00' } });
    await user.click(screen.getByRole('button', { name: '1 h 30' }));
    expect(screen.getByLabelText(/Fin/)).toHaveValue('10:30');
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));
    expect(await screen.findByRole('heading', { level: 3, name: 'Atelier UI' })).toBeInTheDocument();

    await user.click(screen.getByText('Plus'));
    await user.click(screen.getByRole('button', { name: 'Ajouter un événement ponctuel' }));
    await user.type(screen.getByLabelText(/Titre/), 'Cours SQL');
    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '14:00' } });
    await user.click(screen.getByRole('button', { name: '1 h' }));
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));
    expect(await screen.findByRole('heading', { level: 3, name: 'Cours SQL' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Projet' }));
    expect(screen.getByRole('heading', { level: 3, name: 'Atelier UI' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { level: 3, name: 'Cours SQL' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Tous' }));
    expect(screen.getByRole('heading', { level: 3, name: 'Cours SQL' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Grille' }));
    expect(screen.getByRole('region', { name: 'Grille hebdomadaire' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'Atelier UI' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: 'Cours SQL' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Agenda' }));
    expect(screen.queryByRole('region', { name: 'Grille hebdomadaire' })).not.toBeInTheDocument();
  });

  it('permet d’importer un emploi du temps, détecte les anomalies/chevauchements, corrige, annule puis valide sans doublons', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    const importBtns = await screen.findAllByRole('button', { name: /Importer mon emploi du temps/i });
    await user.click(importBtns[0]);
    expect(
      screen.getByRole('region', { name: 'Importer mon emploi du temps' }),
    ).toBeInTheDocument();

    const fileInput = screen.getByTestId('timetable-file-input') as HTMLInputElement;

    const badFile = new File(['MZ-binary'], 'virus.exe', { type: 'application/octet-stream' });
    fireEvent.change(fileInput, { target: { files: [badFile] } });
    expect(await screen.findByRole('alert')).toHaveTextContent(/Format non pris en charge/i);

    const pdfContent = [
      '%PDF-1.4',
      'Lundi 08:00 - 10:30 Programmation Java - Cours - Pr. Diallo - Amphi A',
      'Lundi 09:30 - 11:30 Algorithmique - TD - M. Ndiaye - Salle 204',
      'Mardi ??:?? - 16:00 Bases de Données - TP - Salle 102',
    ].join('\n');
    const pdfFile = new File([pdfContent], 'emploi_du_temps.pdf', {
      type: 'application/pdf',
    });
    fireEvent.change(fileInput, { target: { files: [pdfFile] } });

    const anomaliesPanel = await screen.findByTestId('timetable-anomalies-panel');
    expect(anomaliesPanel).toHaveTextContent(/Horaire de début ou de fin manquant/i);
    expect(anomaliesPanel).toHaveTextContent(/Chevauchement horaire/i);

    const confirmBtn = screen.getByRole('button', { name: 'Enregistrer mon emploi du temps' });
    expect(confirmBtn).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Annuler l’importation' }));
    expect(await screen.findByRole('status')).toHaveTextContent(
      /Importation annulée : aucun cours n’a été enregistré/i,
    );
    expect(screen.queryByRole('heading', { level: 3, name: 'Programmation Java' })).not.toBeInTheDocument();

    await user.click(screen.getAllByRole('button', { name: /Importer mon emploi du temps/i })[0]);
    const fileInput2 = screen.getByTestId('timetable-file-input') as HTMLInputElement;
    fireEvent.change(fileInput2, { target: { files: [pdfFile] } });

    await screen.findByTestId('timetable-anomalies-panel');

    fireEvent.change(screen.getByLabelText('Heure de début ligne 2'), {
      target: { value: '10:30' },
    });
    fireEvent.change(screen.getByLabelText('Heure de fin ligne 2'), {
      target: { value: '12:30' },
    });
    fireEvent.change(screen.getByLabelText('Heure de début ligne 3'), {
      target: { value: '14:00' },
    });

    const confirmBtn2 = screen.getByRole('button', { name: 'Enregistrer mon emploi du temps' });
    expect(confirmBtn2).not.toBeDisabled();
    await user.click(confirmBtn2);

    expect(await screen.findByRole('status')).toHaveTextContent(
      /Emploi du temps validé : 3 cours enregistrés dans votre calendrier/i,
    );
    expect(await screen.findByRole('heading', { level: 3, name: 'Programmation Java' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: '[TD] Algorithmique' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: '[TP] Bases de Données' })).toBeInTheDocument();
  });

  it('génère un programme intelligent, rejette sans muter puis applique réellement au calendrier', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    await user.click(await screen.findByRole('button', { name: 'Construire mon programme' }));
    expect(
      screen.getByRole('region', { name: 'Moteur intelligent de planification' }),
    ).toBeInTheDocument();

    await user.click(screen.getByText('Contraintes et disponibilités'));
    const labelInput = screen.getByLabelText('Libellé de disponibilité');
    await user.clear(labelInput);
    await user.type(labelInput, 'Mercredi bloqué');
    await user.click(screen.getByRole('button', { name: 'Ajouter la règle' }));
    expect(await screen.findByText('Mercredi bloqué')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Construire mon programme' }));
    expect(await screen.findByText('Version v1')).toBeInTheDocument();
    expect(screen.getByText(/Programme généré/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Rejeter sans modifier' }));
    expect(
      await screen.findByText(/Proposition v1 rejetée sans modifier le calendrier/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { level: 3, name: /Session 1/i }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Construire mon programme' }));
    expect(await screen.findByText('Version v2')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Appliquer au calendrier' }));

    expect(await screen.findByRole('status')).toHaveTextContent(/Programme v2 appliqué/i);
    await waitFor(() => {
      expect(
        screen.getAllByRole('heading', { level: 3, name: /Session 1/i }).length,
      ).toBeGreaterThanOrEqual(1);
    });
  });
});
