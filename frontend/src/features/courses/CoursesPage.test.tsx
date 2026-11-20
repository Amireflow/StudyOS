import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { STORAGE_KEYS } from '../../lib/storage';
import { AiCoachPage } from '../ai-coach/AiCoachPage';
import { CoursesPage } from './CoursesPage';

function renderCoursesApp(initialPath = '/courses') {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/courses" element={<CoursesPage />} />
          <Route path="/courses/:courseId" element={<CoursesPage />} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('CoursesPage & verrou pédagogique multi-niveaux', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('prévisualise et crée un cours Python complet au Niveau 1, puis applique le verrou pédagogique avant de débloquer le Niveau 2', async () => {
    const user = userEvent.setup();
    renderCoursesApp();

    await user.click(screen.getByRole('button', { name: 'Nouveau cours' }));

    const subjectInput = screen.getByLabelText(/Sujet ou langage/);
    await user.type(subjectInput, 'Python');

    await user.click(screen.getByRole('button', { name: 'Prévisualiser le plan' }));
    expect(screen.getByText(/Programme des niveaux/)).toBeInTheDocument();
    expect(screen.getByText(/Aperçu du Niveau 1 \(4 chapitres \+ projet\)/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Créer le cours complet' }));

    // Détail du cours créé : Niveau 1/3 débloqué avec 4 chapitres et code copiable
    expect(await screen.findByRole('tab', { name: 'Chapitres (4)' })).toBeInTheDocument();
    expect(screen.getByText('Niveau 1/3')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Copier le code' }).length).toBeGreaterThanOrEqual(1);

    // Le Niveau 2 est verrouillé dès le départ
    const level2Nav = screen.getByRole('button', { name: /Niveau 2 :/ });
    await user.click(level2Nav);
    expect(screen.getByText(/Niveau 2 verrouillé/)).toBeInTheDocument();

    // Retour au Niveau 1 et marquer un chapitre lu ne débloque PAS le niveau suivant
    await user.click(screen.getByRole('button', { name: /Aller au projet du Niveau 1/ }));
    expect(screen.getByRole('tab', { name: 'Projet & validation' })).toHaveAttribute(
      'aria-selected',
      'true',
    );

    const validateBtnLocked = screen.getByRole('button', {
      name: 'Valider le niveau 1 et débloquer le niveau 2',
    });
    expect(validateBtnLocked).toBeDisabled();

    // Soumission purement déclarative -> refusée (< 70/100)
    const explanationBox = screen.getByLabelText(/Explication technique et démarche/);
    await user.type(explanationBox, 'J’ai bien compris tout le niveau 1, c’est acquis.');
    await user.click(screen.getByRole('button', { name: 'Soumettre le projet pour correction' }));

    expect(screen.getByText('Insuffisant')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Valider le niveau 1 et débloquer le niveau 2' }),
    ).toBeDisabled();

    // Soumission technique concrète + code -> réussie (>= 70/100)
    await user.clear(explanationBox);
    await user.click(explanationBox);
    await user.paste(
      'J’ai implémenté analyser_sessions avec validation explicite des durées invalides (ValueError si <= 0), agrégation par dictionnaire typé dict[str, int] et jeu de tests unitaires assert.',
    );
    const codeBox = screen.getByLabelText(/Code ou extrait livrable/);
    await user.click(codeBox);
    await user.paste(
      [
        'def analyser_sessions(entrees: list[tuple[str, int]]) -> dict[str, int]:',
        '    if not entrees:',
        '        raise ValueError("Aucune session fournie")',
        '    total: dict[str, int] = {}',
        '    for sujet, duree in entrees:',
        '        if duree <= 0:',
        '            continue',
        '        total[sujet] = total.get(sujet, 0) + duree',
        '    return total',
        'assert analyser_sessions([("Python", 40)]) == {"Python": 40}',
      ].join('\n'),
    );
    await user.click(screen.getByRole('button', { name: 'Soumettre le projet pour correction' }));

    expect(screen.getByText('Seuil atteint')).toBeInTheDocument();
    const validateBtnReady = screen.getByRole('button', {
      name: 'Valider le niveau 1 et débloquer le niveau 2',
    });
    expect(validateBtnReady).toBeEnabled();

    // Valider le Niveau 1 -> débloque et génère automatiquement les 4 chapitres du Niveau 2
    await user.click(validateBtnReady);
    expect(await screen.findByText('Niveau 2/3')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Chapitres (4)' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        level: 2,
        name: /Manipulation sûre de fichiers avec pathlib/,
      }),
    ).toBeInTheDocument();

    // Compétence liée créée à 0/5 avec preuve de projet (aucune augmentation directe du niveau)
    const learningState = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.learningState) ?? '{}',
    );
    expect(learningState.skills).toHaveLength(1);
    expect(learningState.skills[0].name).toBe('Python');
    expect(learningState.skills[0].currentLevel).toBe(0);
    expect(learningState.evidence).toHaveLength(1);
    expect(learningState.evidence[0].type).toBe('project');

    // Vérifier l'onglet Docs & vidéos + ajout/suppression de ressource
    await user.click(screen.getByRole('tab', { name: 'Docs & vidéos' }));
    expect(screen.getByText(/Documentation officielle Python/)).toBeInTheDocument();
    expect(screen.getByText(/Graven \/ YouTube/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Ajouter une ressource' }));
    await user.type(screen.getByLabelText(/Titre de la ressource/), 'Guide Pathlib Python');
    await user.type(
      screen.getByLabelText(/URL \(http\/https\)/),
      'https://docs.python.org/fr/3/library/pathlib.html',
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la ressource' }));

    expect(screen.getByText('Guide Pathlib Python')).toBeInTheDocument();

    const deleteResBtn = screen.getByRole('button', {
      name: 'Supprimer la ressource Guide Pathlib Python',
    });
    await user.click(deleteResBtn);
    await user.click(
      within(screen.getByRole('group', { name: 'Confirmation : Supprimer' })).getByRole(
        'button',
        { name: 'Confirmer' },
      ),
    );
    expect(screen.queryByText('Guide Pathlib Python')).not.toBeInTheDocument();
  });

  it('permet de créer un cours depuis le Copilote IA uniquement après validation explicite', async () => {
    const user = userEvent.setup();
    render(
      <AppProviders>
        <MemoryRouter initialEntries={['/ai-coach']}>
          <Routes>
            <Route path="/ai-coach" element={<AiCoachPage />} />
            <Route path="/courses/:courseId" element={<CoursesPage />} />
          </Routes>
        </MemoryRouter>
      </AppProviders>,
    );

    await user.type(
      screen.getByLabelText(/Votre message au Copilote/),
      'Crée un cours complet pour apprendre Python',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(screen.getByText('Nouveau cours complet')).toBeInTheDocument();
    expect(screen.getByText('En attente de validation')).toBeInTheDocument();

    const beforeAccept = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.coursesState) ?? '{"courses":[]}',
    );
    expect(beforeAccept.courses).toHaveLength(0);

    await user.click(screen.getByRole('button', { name: 'Valider et exécuter' }));
    expect(screen.getByText('Exécutée')).toBeInTheDocument();

    const afterAccept = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.coursesState) ?? '{"courses":[]}',
    );
    expect(afterAccept.courses).toHaveLength(1);
    expect(afterAccept.courses[0].subject).toBe('Python');
    expect(afterAccept.courses[0].currentLevel).toBe(1);
    expect(screen.getByRole('link', { name: 'Ouvrir le cours' })).toBeInTheDocument();
  });
});
