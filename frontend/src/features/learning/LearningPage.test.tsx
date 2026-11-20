import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { STORAGE_KEYS } from '../../lib/storage';
import { LearningPage } from './LearningPage';

function renderLearningPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <LearningPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('LearningPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('crée un parcours, un module et une leçon, valide l’URL et respecte LEARN-03', async () => {
    const user = userEvent.setup();

    // Pré-semer une compétence au niveau 0 pour vérifier que clôturer une leçon ne l'altère jamais (LEARN-03)
    window.localStorage.setItem(
      STORAGE_KEYS.learningState,
      JSON.stringify({
        paths: [],
        modules: [],
        lessons: [],
        skills: [
          {
            id: 'skill-1',
            userId: 'local-user',
            name: 'FastAPI',
            domain: 'Backend',
            description: null,
            currentLevel: 0,
            targetLevel: 4,
            lastAssessedAt: null,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
        ],
        evidence: [],
        projects: [],
      }),
    );

    renderLearningPage();

    expect(screen.getByText(/ne valide jamais automatiquement une compétence/i)).toBeInTheDocument();

    // Créer un parcours
    await user.click(screen.getByRole('button', { name: 'Nouveau parcours' }));
    await user.type(screen.getByLabelText(/Titre du parcours/), 'Backend Python');
    await user.type(
      screen.getByLabelText(/Objectif mesurable/),
      'Maîtriser les APIs FastAPI testées',
    );
    await user.click(screen.getByRole('button', { name: 'Créer le parcours' }));

    expect(screen.getByText('Backend Python')).toBeInTheDocument();

    // Ajouter un module
    await user.click(screen.getByRole('button', { name: 'Ajouter un module' }));
    await user.type(screen.getByLabelText(/Titre du module/), 'Schémas & Validation');
    await user.click(screen.getByRole('button', { name: 'Enregistrer le module' }));

    expect(screen.getByText('Schémas & Validation')).toBeInTheDocument();

    // Ajouter une leçon avec URL invalide puis valide
    await user.click(screen.getByRole('button', { name: 'Ajouter une leçon' }));
    await user.type(screen.getByLabelText(/Titre de la leçon/), 'Validateurs Pydantic');
    await user.type(screen.getByLabelText(/Ressource/), 'javascript:alert(1)');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la leçon' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'L’URL doit commencer par http:// ou https://.',
    );

    const urlInput = screen.getByLabelText(/Ressource/);
    await user.clear(urlInput);
    await user.type(urlInput, 'https://docs.pydantic.dev/latest/');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la leçon' }));

    expect(screen.getByText('Validateurs Pydantic')).toBeInTheDocument();

    // Terminer la leçon -> progression mise à jour mais compétence toujours niveau 0 (LEARN-03)
    await user.click(screen.getByRole('button', { name: 'Marquer terminée' }));
    expect(screen.getByRole('status')).toHaveTextContent('aucune compétence validée automatiquement');
    expect(screen.getByText(/1\/1 leçon \(100%\)/)).toBeInTheDocument();

    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEYS.learningState) ?? '{}');
    expect(stored.skills[0].currentLevel).toBe(0);
    expect(stored.skills[0].lastAssessedAt).toBeNull();
  });
});
