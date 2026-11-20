import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { STORAGE_KEYS } from '../../lib/storage';
import { AiCoachPage } from './AiCoachPage';

function renderAiCoachPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <AiCoachPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('AiCoachPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('propose une tâche sans mutation immédiate (AI-01), permet de l’ajuster puis de la valider (AI-07) ou de la rejeter, et génère briefing/bilan (AI-06)', async () => {
    const user = userEvent.setup();
    renderAiCoachPage();

    // Demander la création d'une tâche -> proposition en attente, aucune tâche créée tant que non validée
    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Crée une tâche : « Réviser les index PostgreSQL »',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(screen.getByText('En attente de validation')).toBeInTheDocument();
    expect(screen.getByText(/Indication AI-06/)).toBeInTheDocument();

    const beforeAcceptState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(beforeAcceptState.tasks ?? []).toHaveLength(0);

    // Ajuster le titre et la priorité avant de valider
    await user.click(screen.getByRole('button', { name: 'Ajuster' }));
    const titleInput = screen.getByLabelText(/Ajuster le titre avant validation/);
    await user.clear(titleInput);
    await user.type(titleInput, 'Réviser les index PostgreSQL et plans EXPLAIN');
    await user.selectOptions(screen.getByLabelText(/Ajuster la priorité/), 'high');

    await user.click(screen.getByRole('button', { name: 'Valider et exécuter' }));

    expect(screen.getByText('Exécutée')).toBeInTheDocument();

    const afterAcceptState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(afterAcceptState.tasks).toHaveLength(1);
    expect(afterAcceptState.tasks[0].title).toBe(
      'Réviser les index PostgreSQL et plans EXPLAIN',
    );
    expect(afterAcceptState.tasks[0].priority).toBe('high');
    expect(afterAcceptState.tasks[0].source).toBe('ai_proposal');

    // Demander de mettre la tâche au parking puis rejeter la proposition
    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Mets cette tâche au parking',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    await user.click(screen.getByRole('button', { name: 'Rejeter' }));
    expect(screen.getByText('Rejetée')).toBeInTheDocument();

    const afterRejectState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(afterRejectState.tasks[0].status).toBe('todo');

    // Générer un briefing quotidien et un bilan hebdomadaire (P1)
    await user.click(screen.getByRole('button', { name: 'Briefing du jour' }));
    expect(screen.getByText('Briefing quotidien')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Bilan hebdo' }));
    expect(screen.getByText('Bilan hebdomadaire')).toBeInTheDocument();
  });

  it('propose des amorces rapides, envoie avec Entrée, et permet d’ouvrir les outils et l’historique', async () => {
    const user = userEvent.setup();
    renderAiCoachPage();

    // État initial épuré + amorce rapide
    expect(screen.getByText('Que souhaitez-vous organiser ?')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Planifier ma journée/i }));

    const promptInput = screen.getByLabelText(/Votre message au Copilote/);
    expect(promptInput).toHaveValue(
      'Planifie ma journée autour de ma priorité active et de mes créneaux disponibles.',
    );

    // Envoi au clavier via la touche Entrée
    await user.keyboard('{Enter}');
    expect(promptInput).toHaveValue('');
    expect(
      await screen.findByText(
        'Planifie ma journée autour de ma priorité active et de mes créneaux disponibles.',
      ),
    ).toBeInTheDocument();

    // Inspecteur d'outils
    await user.click(screen.getByRole('button', { name: /Outils \(/i }));
    expect(screen.getByText(/Outils autorisés/)).toBeInTheDocument();
    expect(screen.getByText('Lire les tâches')).toBeInTheDocument();

    // Nouvelle conversation et tiroir historique
    await user.click(screen.getByRole('button', { name: 'Nouvelle conversation' }));
    await user.click(screen.getByRole('button', { name: 'Historique des conversations' }));
    expect(screen.getByText(/Historique des conversations \(2\)/)).toBeInTheDocument();
  });
});
