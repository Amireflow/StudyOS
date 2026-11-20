import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { SkillsPage } from './SkillsPage';

function renderSkillsPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <SkillsPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('SkillsPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('signale un niveau >= 3 sans preuve (SKILL-03) puis affiche la preuve ajoutée (SKILL-02)', async () => {
    const user = userEvent.setup();
    renderSkillsPage();

    // Créer une compétence au niveau 3 sans preuve -> alerte SKILL-03 visible
    await user.click(screen.getByRole('button', { name: 'Nouvelle compétence' }));
    await user.type(screen.getByLabelText(/Nom de la compétence/), 'React TypeScript');
    await user.type(screen.getByLabelText(/Domaine/), 'Frontend');
    await user.selectOptions(screen.getByLabelText(/Niveau actuel/), '3');
    await user.click(screen.getByRole('button', { name: 'Créer la compétence' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Alerte SKILL-03');
    expect(screen.getByText(/Aucune preuve enregistrée/)).toBeInTheDocument();

    // Ajouter une preuve directement sur la compétence -> alerte disparaît et preuve affichée
    await user.click(screen.getByRole('button', { name: 'Ajouter une preuve' }));
    await user.selectOptions(screen.getByLabelText(/Type de preuve/), 'code');
    await user.type(
      screen.getByLabelText(/Ce qui a été réalisé/),
      'Implémentation du module Apprentissage & Projets en TS strict',
    );
    await user.type(screen.getByLabelText(/Résultat/), 'Build Vite + tests Vitest OK');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la preuve' }));

    expect(screen.queryByText(/Alerte SKILL-03/)).not.toBeInTheDocument();
    expect(
      screen.getByText('Implémentation du module Apprentissage & Projets en TS strict'),
    ).toBeInTheDocument();
    expect(screen.getByText('Build Vite + tests Vitest OK')).toBeInTheDocument();
  });
});
