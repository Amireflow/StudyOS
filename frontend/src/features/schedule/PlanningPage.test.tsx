import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
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
  beforeEach(() => {
    window.localStorage.clear();
  });

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

  it('propose des raccourcis de durée, filtre par catégorie et bascule entre Agenda et Grille', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    // Créneau 1 via raccourci de durée 1 h 30
    await user.click(screen.getByRole('button', { name: 'Nouveau créneau' }));
    await user.type(screen.getByLabelText(/Titre/), 'Atelier UI');
    await user.selectOptions(screen.getByLabelText(/Type/), 'project');
    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '09:00' } });
    await user.click(screen.getByRole('button', { name: '1 h 30' }));
    expect(screen.getByLabelText(/Fin/)).toHaveValue('10:30');
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));

    // Créneau 2 de type cours (par défaut)
    await user.click(screen.getByRole('button', { name: 'Nouveau créneau' }));
    await user.type(screen.getByLabelText(/Titre/), 'Cours SQL');
    fireEvent.change(screen.getByLabelText(/Début/), { target: { value: '14:00' } });
    await user.click(screen.getByRole('button', { name: '1 h' }));
    await user.click(screen.getByRole('button', { name: 'Ajouter le créneau' }));

    // Filtrage par catégorie
    await user.click(screen.getByRole('button', { name: 'Projet' }));
    expect(screen.getByRole('heading', { level: 3, name: 'Atelier UI' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { level: 3, name: 'Cours SQL' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Tous' }));
    expect(screen.getByRole('heading', { level: 3, name: 'Cours SQL' })).toBeInTheDocument();

    // Bascule en vue Grille puis retour Agenda
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

    // Ouverture du panneau d'import
    await user.click(
      screen.getAllByRole('button', { name: /Importer mon emploi du temps/i })[0],
    );
    expect(
      screen.getByRole('region', { name: 'Importer mon emploi du temps' }),
    ).toBeInTheDocument();

    const fileInput = screen.getByTestId('timetable-file-input') as HTMLInputElement;

    // 1. Rejet d'un fichier non pris en charge (.exe)
    const badFile = new File(['MZ-binary'], 'virus.exe', { type: 'application/octet-stream' });
    fireEvent.change(fileInput, { target: { files: [badFile] } });
    expect(await screen.findByRole('alert')).toHaveTextContent(/Format non pris en charge/i);

    // 2. Import d'un PDF contenant un chevauchement et un horaire illisible
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

    // Vérifie la détection des 3 cours et des anomalies (horaire manquant + chevauchement)
    const anomaliesPanel = await screen.findByTestId('timetable-anomalies-panel');
    expect(anomaliesPanel).toHaveTextContent(/Horaire de début ou de fin manquant/i);
    expect(anomaliesPanel).toHaveTextContent(/Chevauchement horaire/i);

    // Le bouton Enregistrer est désactivé tant qu'une anomalie bloquante subsiste
    const confirmBtn = screen.getByRole('button', { name: 'Enregistrer mon emploi du temps' });
    expect(confirmBtn).toBeDisabled();

    // 3. Annulation de l'import -> aucun cours ne doit être enregistré dans le calendrier
    await user.click(screen.getByRole('button', { name: 'Annuler l’importation' }));
    expect(screen.getByRole('status')).toHaveTextContent(
      /Importation annulée : aucun cours n’a été enregistré/i,
    );
    expect(screen.queryByRole('heading', { level: 3, name: 'Programmation Java' })).not.toBeInTheDocument();

    // 4. Nouvel import, correction manuelle de l'horaire illisible et du chevauchement, puis validation
    await user.click(
      screen.getAllByRole('button', { name: /Importer mon emploi du temps/i })[0],
    );
    const fileInput2 = screen.getByTestId('timetable-file-input') as HTMLInputElement;
    fireEvent.change(fileInput2, { target: { files: [pdfFile] } });

    await screen.findByTestId('timetable-anomalies-panel');

    // Corrige le chevauchement de la ligne 2 (Algorithmique -> 10:30 - 12:30)
    fireEvent.change(screen.getByLabelText('Heure de début ligne 2'), {
      target: { value: '10:30' },
    });
    fireEvent.change(screen.getByLabelText('Heure de fin ligne 2'), {
      target: { value: '12:30' },
    });

    // Corrige l'horaire illisible de la ligne 3 (Bases de Données -> 14:00 - 16:00)
    fireEvent.change(screen.getByLabelText('Heure de début ligne 3'), {
      target: { value: '14:00' },
    });

    // Plus aucune anomalie bloquante : validation et enregistrement dans le calendrier
    const confirmBtn2 = screen.getByRole('button', { name: 'Enregistrer mon emploi du temps' });
    expect(confirmBtn2).not.toBeDisabled();
    await user.click(confirmBtn2);

    expect(screen.getByRole('status')).toHaveTextContent(
      /Emploi du temps validé : 3 cours enregistrés dans votre calendrier/i,
    );
    expect(screen.getByRole('heading', { level: 3, name: 'Programmation Java' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 3, name: '[TD] Algorithmique' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 3, name: '[TP] Bases de Données' }),
    ).toBeInTheDocument();
  });

  it('génère un programme intelligent, rejette sans muter puis applique réellement au calendrier', async () => {
    const user = userEvent.setup();
    renderPlanningPage();

    // Ouvre le studio Programme intelligent
    await user.click(screen.getByRole('button', { name: 'Programme intelligent' }));
    expect(
      screen.getByRole('region', { name: 'Moteur intelligent de planification' }),
    ).toBeInTheDocument();

    // Ajoute une règle d'indisponibilité personnelle
    const labelInput = screen.getByLabelText('Libellé de disponibilité');
    await user.clear(labelInput);
    await user.type(labelInput, 'Mercredi bloqué');
    await user.click(screen.getByRole('button', { name: 'Ajouter la règle' }));
    expect(screen.getByText('Mercredi bloqué')).toBeInTheDocument();

    // Génère un programme intelligent (v1) sans muter le calendrier
    await user.click(screen.getByRole('button', { name: 'Générer le programme' }));
    expect(screen.getByText('Version v1')).toBeInTheDocument();
    expect(screen.getByText(/Programme généré/i)).toBeInTheDocument();

    // Rejet sans modification du calendrier
    await user.click(screen.getByRole('button', { name: 'Rejeter sans modifier' }));
    expect(
      screen.getByText(/Proposition v1 rejetée sans modifier le calendrier/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { level: 3, name: /Session 1/i }),
    ).not.toBeInTheDocument();

    // Nouvelle génération (v2) puis application réelle au calendrier
    await user.click(screen.getByRole('button', { name: 'Générer le programme' }));
    expect(screen.getByText('Version v2')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Appliquer au calendrier' }));

    expect(screen.getByRole('status')).toHaveTextContent(/Programme v2 appliqué/i);
    expect(
      screen.getAllByRole('heading', { level: 3, name: /Session 1/i }).length,
    ).toBeGreaterThanOrEqual(1);
  });
});
