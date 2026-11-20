import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { STORAGE_KEYS } from '../../lib/storage';
import { SkillsPage } from './SkillsPage';

function renderSkillsPage(initialEntry = '/skills') {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[initialEntry]}>
        <SkillsPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('SkillsPage — Verrou pédagogique et processus d’évaluation', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('supprime toute modification directe du niveau, bloque les preuves déclaratives et exécute le flux complet d’évaluation (échec puis exercice correctif validé)', async () => {
    const user = userEvent.setup();
    renderSkillsPage();

    // 1. Créer une compétence : aucun sélecteur de niveau actuel n'existe dans le formulaire
    await user.click(screen.getByRole('button', { name: 'Nouvelle compétence' }));
    expect(screen.queryByLabelText(/Niveau actuel/i)).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/Nom de la compétence/), 'Python & FastAPI');
    await user.type(screen.getByLabelText(/Domaine/), 'Backend');
    await user.selectOptions(screen.getByLabelText(/Niveau cible/), '3');
    await user.click(screen.getByRole('button', { name: 'Créer la compétence' }));

    // La compétence démarre obligatoirement à 0/5 (Non évaluée) et aucun menu déroulant de niveau n'est affiché sur la carte
    expect(screen.getByText(/Niveau vérifié : 0 \/ 5 — Non évalué/)).toBeInTheDocument();
    expect(screen.getAllByText('Non évaluée').length).toBeGreaterThanOrEqual(1);
    expect(
      screen.queryByRole('combobox', { name: /Niveau actuel de Python & FastAPI/i }),
    ).not.toBeInTheDocument();

    // 2. Tentative d'ajout d'une preuve purement déclarative (« J'ai compris Python ») -> rejetée
    await user.click(screen.getByRole('button', { name: 'Ajouter une preuve' }));
    await user.type(
      screen.getByLabelText(/Ce qui a été réalisé/),
      "J'ai compris Python et j'ai lu la leçon",
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la preuve' }));
    expect(screen.getByRole('alert')).toHaveTextContent(/Preuve insuffisante/i);

    // 3. Ouvrir le processus d'évaluation
    await user.click(screen.getByRole('button', { name: 'Évaluer cette compétence' }));
    const configSection = screen.getByRole('region', {
      name: /Nouvelle évaluation pédagogique — Python & FastAPI/i,
    });
    await within(configSection).findByText(/Niveau actuel vérifié : 0\/5/i);
    await user.click(within(configSection).getByRole('button', { name: 'Générer l’épreuve' }));

    // 4. Révéler un indice progressif puis soumettre une réponse insuffisante sans preuve
    const activeSection = screen.getByRole('region', {
      name: /Évaluation en cours pour Python & FastAPI/i,
    });
    await user.click(
      within(activeSection).getByRole('button', { name: /Afficher un indice \(1\/3\)/i }),
    );
    expect(within(activeSection).getByText(/Indice 1 — Cadrage/i)).toBeInTheDocument();

    await user.type(
      within(activeSection).getByLabelText(/Votre production et explication du raisonnement/i),
      'Je ne sais pas encore gérer les cas limites, réponse incorrecte pour cet essai.',
    );
    await user.click(
      within(activeSection).getByRole('button', { name: 'Soumettre ma production' }),
    );

    // 5. Évaluer la soumission -> échec affiché, lacunes listées, niveau maintenu à 0/5
    await user.click(
      within(activeSection).getByRole('button', { name: 'Évaluer ma soumission' }),
    );
    expect(
      within(activeSection).getByText(/Niveau non atteint — renforcement requis/i),
    ).toBeInTheDocument();
    expect(within(activeSection).getByText(/Lacunes identifiées/i)).toBeInTheDocument();
    expect(
      within(activeSection).getByText(/Verrou actif : le niveau actuel reste à 0\/5/i),
    ).toBeInTheDocument();

    // 6. Lancer un exercice correctif et soumettre une production valide avec preuve concrète
    await user.click(
      within(activeSection).getByRole('button', { name: 'Faire un exercice correctif' }),
    );
    expect(
      within(activeSection).getByText(/Exercice correctif — Python & FastAPI/i),
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
      within(activeSection).getByRole('button', { name: 'Évaluer ma soumission' }),
    );

    // 7. Résultat favorable -> valider la décision finale -> niveau passe à 1/5
    expect(within(activeSection).getByText(/Niveau visé atteint/i)).toBeInTheDocument();
    await user.click(
      within(activeSection).getByRole('button', {
        name: /Valider et appliquer le niveau 1\/5/i,
      }),
    );

    expect(screen.getByText(/Niveau vérifié : 1 \/ 5 — Découverte/)).toBeInTheDocument();
    expect(screen.getAllByText('Validée').length).toBeGreaterThanOrEqual(2);

    // 8. L'historique complet des 2 évaluations (non validée + validée) et la preuve sont consultables
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
    const user = userEvent.setup();
    const nowIso = new Date().toISOString();

    window.localStorage.setItem(
      STORAGE_KEYS.learningState,
      JSON.stringify({
        paths: [],
        modules: [],
        lessons: [],
        skills: [
          {
            id: 'legacy-skill-3',
            userId: 'local-user',
            name: 'React TypeScript',
            domain: 'Frontend',
            description: 'Compétence historique importée avant le verrou',
            currentLevel: 3,
            targetLevel: 4,
            lastAssessedAt: nowIso,
            createdAt: nowIso,
            updatedAt: nowIso,
          },
        ],
        evidence: [],
        assessments: [],
        projects: [],
      }),
    );

    renderSkillsPage();

    expect(screen.getByText(/Niveau vérifié : 3 \/ 5 — Autonome/)).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Alerte SKILL-03');

    await user.click(screen.getByRole('button', { name: 'Ajouter une preuve' }));
    await user.selectOptions(screen.getByLabelText(/Type de preuve/), 'code');
    await user.type(
      screen.getByLabelText(/Ce qui a été réalisé/),
      'Implémentation du module Apprentissage & Compétences en TypeScript strict avec tests Vitest',
    );
    await user.type(screen.getByLabelText(/Résultat/), 'Build Vite + tests Vitest OK');
    await user.click(screen.getByRole('button', { name: 'Enregistrer la preuve' }));

    expect(screen.queryByText(/Alerte SKILL-03/)).not.toBeInTheDocument();
    expect(
      screen.getByText(
        'Implémentation du module Apprentissage & Compétences en TypeScript strict avec tests Vitest',
      ),
    ).toBeInTheDocument();
  });

  it('regroupe par domaine et filtre par pilule de domaine et recherche', async () => {
    const user = userEvent.setup();
    renderSkillsPage();

    await user.click(screen.getByRole('button', { name: 'Nouvelle compétence' }));
    await user.type(screen.getByLabelText(/Nom de la compétence/), 'FastAPI');
    await user.type(screen.getByLabelText(/Domaine/), 'Backend');
    await user.click(screen.getByRole('button', { name: 'Créer la compétence' }));

    await user.click(screen.getByRole('button', { name: 'Nouvelle compétence' }));
    await user.type(screen.getByLabelText(/Nom de la compétence/), 'Tailwind CSS');
    await user.type(screen.getByLabelText(/Domaine/), 'Frontend');
    await user.click(screen.getByRole('button', { name: 'Créer la compétence' }));

    // Filtrage par domaine Backend
    await user.click(screen.getByRole('button', { name: 'Backend' }));
    expect(screen.getByRole('article', { name: 'FastAPI' })).toBeInTheDocument();
    expect(screen.queryByRole('article', { name: 'Tailwind CSS' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Tous' }));
    expect(screen.getByRole('article', { name: 'Tailwind CSS' })).toBeInTheDocument();

    // Recherche sans résultat puis réinitialisation
    await user.type(screen.getByLabelText('Rechercher une compétence'), 'Kubernetes');
    expect(
      screen.getByText('Aucune compétence ne correspond aux filtres'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByRole('article', { name: 'FastAPI' })).toBeInTheDocument();
  });
});
