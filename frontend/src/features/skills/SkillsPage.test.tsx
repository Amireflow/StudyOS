import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { installMockStudyApi, TEST_API_SESSION, TEST_USER_ID } from '../../test/mockStudyApi';
import { SkillsPage } from './SkillsPage';

function renderSkillsPage(initialEntry = '/skills') {
  return render(
    <AppProviders initialSession={TEST_API_SESSION}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <SkillsPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('SkillsPage — Verrou pédagogique et processus d’évaluation', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('supprime toute modification directe du niveau, bloque les preuves déclaratives et exécute le flux complet d’évaluation (échec puis exercice correctif validé)', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderSkillsPage();

    await user.click(await screen.findByRole('button', { name: 'Nouvelle compétence' }));
    expect(screen.queryByLabelText(/Niveau actuel/i)).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/Nom de la compétence/), 'Python & FastAPI');
    await user.type(screen.getByLabelText(/Domaine/), 'Backend');
    await user.selectOptions(screen.getByLabelText(/Niveau cible/), '3');
    await user.click(screen.getByRole('button', { name: 'Créer la compétence' }));

    expect(
      await screen.findByText(/Niveau vérifié : 0 \/ 5 — Non évalué/),
    ).toBeInTheDocument();
    expect(screen.getAllByText('Non évaluée').length).toBeGreaterThanOrEqual(1);
    expect(
      screen.queryByRole('combobox', { name: /Niveau actuel de Python & FastAPI/i }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Ajouter une preuve' }));
    await user.type(
      screen.getByLabelText(/Ce qui a été réalisé/),
      "J'ai compris Python et j'ai lu la leçon",
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la preuve' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/Preuve insuffisante/i);

    await user.click(screen.getByRole('button', { name: 'Évaluer cette compétence' }));
    const configSection = screen.getByRole('region', {
      name: /Nouvelle évaluation pédagogique — Python & FastAPI/i,
    });
    await within(configSection).findByText(/Niveau actuel vérifié : 0\/5/i);
    await user.click(within(configSection).getByRole('button', { name: 'Générer l’épreuve' }));

    const activeSection = await screen.findByRole('region', {
      name: /Évaluation en cours pour Python & FastAPI/i,
    });
    await user.click(
      within(activeSection).getByRole('button', { name: /Afficher un indice \(1\/3\)/i }),
    );
    expect(await within(activeSection).findByText(/Indice 1 — Cadrage/i)).toBeInTheDocument();

    await user.type(
      within(activeSection).getByLabelText(/Votre production et explication du raisonnement/i),
      'Je ne sais pas encore gérer les cas limites, réponse incorrecte pour cet essai.',
    );
    await user.click(
      within(activeSection).getByRole('button', { name: 'Soumettre ma production' }),
    );

    await user.click(
      await within(activeSection).findByRole('button', { name: 'Évaluer ma soumission' }),
    );
    expect(
      await within(activeSection).findByText(/Niveau non atteint — renforcement requis/i),
    ).toBeInTheDocument();
    expect(within(activeSection).getByText(/Lacunes identifiées/i)).toBeInTheDocument();
    expect(
      within(activeSection).getByText(/Verrou actif : le niveau actuel reste à 0\/5/i),
    ).toBeInTheDocument();

    await user.click(
      within(activeSection).getByRole('button', { name: 'Faire un exercice correctif' }),
    );
    expect(
      await within(activeSection).findByText(/Exercice correctif — Python & FastAPI/i),
    ).toBeInTheDocument();

    await user.type(
      within(activeSection).getByLabelText(/Votre production et explication du raisonnement/i),
      "J'ai implémenté un endpoint FastAPI typé avec Pydantic parce que cela valide les entrées et renvoie une erreur 422 explicite sur les cas limites.",
    );
    await user.type(
      within(activeSection).getByLabelText(/Code source, requête ou commande exécutée/i),
      'def create_item(payload: ItemCreate) -> ItemResponse:\n    return service.create(payload)',
    );
    await user.type(
      within(activeSection).getByLabelText(/Description concrète de la preuve produite/i),
      'Endpoint FastAPI validé avec 6 tests Pytest couvrant cas nominal et erreurs 422',
    );
    await user.type(
      within(activeSection).getByLabelText(/Résultat mesurable/i),
      '6 passed in 0.08s',
    );
    await user.click(
      within(activeSection).getByRole('button', { name: 'Soumettre ma production' }),
    );
    await user.click(
      await within(activeSection).findByRole('button', { name: 'Évaluer ma soumission' }),
    );

    expect(await within(activeSection).findByText(/Niveau visé atteint/i)).toBeInTheDocument();
    await user.click(
      within(activeSection).getByRole('button', {
        name: /Valider et appliquer le niveau 1\/5/i,
      }),
    );

    expect(await screen.findByText(/Niveau vérifié : 1 \/ 5 — Découverte/)).toBeInTheDocument();
    expect(screen.getAllByText('Validée').length).toBeGreaterThanOrEqual(2);

    await user.click(
      screen.getByRole('button', { name: /Historique des évaluations \(2\)/i }),
    );
    expect(screen.getAllByText('Non validée').length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByText(
        'Endpoint FastAPI validé avec 6 tests Pytest couvrant cas nominal et erreurs 422',
      ),
    ).toBeInTheDocument();
  }, 30000);

  it('préserve les compétences historiques déjà enregistrées à un niveau >= 3 et signale SKILL-03 tant qu’aucune preuve n’est associée', async () => {
    const nowIso = new Date().toISOString();
    installMockStudyApi({
      skills: [
        {
          id: 'legacy-skill-3',
          user_id: TEST_USER_ID,
          name: 'React TypeScript',
          domain: 'Frontend',
          description: 'Compétence historique importée avant le verrou',
          current_level: 3,
          target_level: 4,
          last_assessed_at: nowIso,
          created_at: nowIso,
          updated_at: nowIso,
        },
      ],
    });

    const user = userEvent.setup();
    renderSkillsPage();

    expect(await screen.findByText(/Niveau vérifié : 3 \/ 5 — Autonome/)).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Alerte SKILL-03');

    await user.click(screen.getByRole('button', { name: 'Ajouter une preuve' }));
    await user.selectOptions(screen.getByLabelText(/Type de preuve/), 'code');
    await user.type(
      screen.getByLabelText(/Ce qui a été réalisé/),
      'Implémentation du module Apprentissage & Compétences en TypeScript strict avec tests Vitest',
    );
    await user.type(screen.getByLabelText(/Résultat/), 'Build Vite + tests Vitest OK');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la preuve' }));

    await waitFor(() => {
      expect(screen.queryByText(/Alerte SKILL-03/)).not.toBeInTheDocument();
    });
    expect(
      screen.getByText(
        'Implémentation du module Apprentissage & Compétences en TypeScript strict avec tests Vitest',
      ),
    ).toBeInTheDocument();
  });

  it('regroupe par domaine et filtre par pilule de domaine et recherche', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    renderSkillsPage();

    await user.click(await screen.findByRole('button', { name: 'Nouvelle compétence' }));
    await user.type(screen.getByLabelText(/Nom de la compétence/), 'FastAPI');
    await user.type(screen.getByLabelText(/Domaine/), 'Backend');
    await user.click(screen.getByRole('button', { name: 'Créer la compétence' }));
    expect(await screen.findByRole('article', { name: 'FastAPI' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Nouvelle compétence' }));
    await user.type(screen.getByLabelText(/Nom de la compétence/), 'Tailwind CSS');
    await user.type(screen.getByLabelText(/Domaine/), 'Frontend');
    await user.click(screen.getByRole('button', { name: 'Créer la compétence' }));
    expect(await screen.findByRole('article', { name: 'Tailwind CSS' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Backend' }));
    expect(screen.getByRole('article', { name: 'FastAPI' })).toBeInTheDocument();
    expect(screen.queryByRole('article', { name: 'Tailwind CSS' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Tous' }));
    expect(screen.getByRole('article', { name: 'Tailwind CSS' })).toBeInTheDocument();

    await user.type(screen.getByLabelText('Rechercher une compétence'), 'Kubernetes');
    expect(
      screen.getByText('Aucune compétence ne correspond aux filtres'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByRole('article', { name: 'FastAPI' })).toBeInTheDocument();
  });
});
