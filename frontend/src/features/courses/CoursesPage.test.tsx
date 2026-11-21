import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { installMockStudyApi, TEST_API_SESSION } from '../../test/mockStudyApi';
import { AiCoachPage } from '../ai-coach/AiCoachPage';
import { CoursesPage } from './CoursesPage';

function renderCoursesApp(initialPath = '/courses') {
  return render(
    <AppProviders initialSession={TEST_API_SESSION}>
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
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('bloque toute création tant que le programme IA n’a pas été prévisualisé', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderCoursesApp();

    await user.click(await screen.findByRole('button', { name: 'Nouveau cours' }));
    const createButton = screen.getByRole('button', { name: 'Valider et créer le cours' });
    expect(createButton).toBeDisabled();

    await user.type(screen.getByLabelText(/Sujet ou domaine/), 'Python');
    await user.type(
      screen.getByLabelText(/Quel résultat veux-tu atteindre/),
      'Développer une API backend et réussir mes exercices pratiques.',
    );
    expect(createButton).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Analyser et construire le programme' }));
    expect(await screen.findByText(/Programme des niveaux/)).toBeInTheDocument();
    expect(api.state.courses).toHaveLength(0);
    expect(createButton).toBeEnabled();

    await user.click(createButton);
    expect(await screen.findByRole('tab', { name: /Chapitres/ })).toBeInTheDocument();
    expect(api.state.courses).toHaveLength(1);
  });

  it('prévisualise et crée un cours Python complet au Niveau 1, puis applique le verrou pédagogique avant de débloquer le Niveau 2', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderCoursesApp();

    await user.click(await screen.findByRole('button', { name: 'Nouveau cours' }));

    const subjectInput = screen.getByLabelText(/Sujet ou domaine/);
    await user.type(subjectInput, 'Python');

    await user.click(screen.getByRole('button', { name: 'Analyser et construire le programme' }));
    expect(await screen.findByText(/Programme des niveaux/)).toBeInTheDocument();
    expect(screen.getByText(/Aperçu du Niveau 1 \(4 chapitres \+ projet\)/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Valider et créer le cours' }));

    expect(await screen.findByRole('tab', { name: 'Chapitres (4)' })).toBeInTheDocument();
    expect(screen.getByText('Niveau 1/3')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Copier le code' }).length).toBeGreaterThanOrEqual(1);

    const level2Nav = screen.getByRole('button', { name: /Niveau 2 :/ });
    await user.click(level2Nav);
    expect(screen.getByText(/Niveau 2 verrouillé/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Aller au projet du Niveau 1/ }));
    expect(screen.getByRole('tab', { name: 'Projet & validation' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(
      screen.getByRole('button', {
        name: 'Valider le niveau 1 et débloquer le niveau 2',
      }),
    ).toBeDisabled();

    await user.click(screen.getByRole('tab', { name: 'Chapitres (4)' }));

    const exAnswer = screen.getAllByLabelText(/Votre explication technique/)[0];
    await user.click(exAnswer);
    await user.paste(
      'J’ai validé les bornes avec ValueError parce qu’une note négative ou supérieure à 100 est invalide, puis vérifié avec assert.',
    );
    const exCode = screen.getAllByLabelText(/Code de votre solution/)[0];
    await user.clear(exCode);
    await user.click(exCode);
    await user.paste(
      [
        'def classify_score(score: int) -> str:',
        '    if score < 0 or score > 100:',
        '        raise ValueError("invalide")',
        '    return "Acquis" if score >= 85 else "En cours"',
        'assert classify_score(90) == "Acquis"',
      ].join('\n'),
    );
    await user.click(screen.getAllByRole('button', { name: 'Corriger l’exercice' })[0]);
    expect(await screen.findByText('Exercice validé')).toBeInTheDocument();

    for (let idx = 0; idx < 4; idx += 1) {
      await user.click(screen.getByRole('button', { name: 'Marquer lu' }));
      if (idx < 3) {
        await user.click(screen.getByRole('button', { name: 'Chapitre suivant' }));
      } else {
        await user.click(screen.getByRole('button', { name: 'Passer au projet du niveau' }));
      }
    }

    const validateBtnLocked = screen.getByRole('button', {
      name: 'Valider le niveau 1 et débloquer le niveau 2',
    });
    expect(validateBtnLocked).toBeDisabled();

    const explanationBox = screen.getByLabelText(/Explication technique et démarche/);
    await user.type(explanationBox, 'J’ai bien compris tout le niveau 1, c’est acquis.');
    await user.click(screen.getByRole('button', { name: 'Soumettre le projet pour correction' }));

    expect(await screen.findByText('Insuffisant')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Valider le niveau 1 et débloquer le niveau 2' }),
    ).toBeDisabled();

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

    expect(await screen.findByText('Seuil atteint')).toBeInTheDocument();
    const validateBtnReady = screen.getByRole('button', {
      name: 'Valider le niveau 1 et débloquer le niveau 2',
    });
    await waitFor(() => expect(validateBtnReady).toBeEnabled());

    await user.click(validateBtnReady);
    expect(await screen.findByText('Niveau 2/3')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Chapitres (4)' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        level: 2,
        name: /Manipulation sûre de fichiers avec pathlib/,
      }),
    ).toBeInTheDocument();

    expect(api.state.skills).toHaveLength(1);
    expect(api.state.skills[0].name).toBe('Python');
    expect(api.state.skills[0].current_level).toBe(0);
    expect(api.state.evidence).toHaveLength(1);
    expect(api.state.evidence[0].type).toBe('project');

    await user.click(screen.getByRole('tab', { name: 'Docs & vidéos' }));
    expect(screen.getByText(/Documentation officielle Python/)).toBeInTheDocument();
    expect(screen.getByText(/Harvard CS50/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Ajouter une ressource' }));
    await user.type(screen.getByLabelText(/Titre de la ressource/), 'Guide Pathlib Python');
    await user.type(
      screen.getByLabelText(/URL \(http\/https\)/),
      'https://docs.python.org/fr/3/library/pathlib.html',
    );
    await user.click(screen.getByRole('button', { name: 'Enregistrer la ressource' }));

    expect(await screen.findByText('Guide Pathlib Python')).toBeInTheDocument();

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
    await waitFor(() => {
      expect(screen.queryByText('Guide Pathlib Python')).not.toBeInTheDocument();
    });
  });

  it('permet de poser une question au tuteur du chapitre et affiche sa réponse', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderCoursesApp();

    await user.click(await screen.findByRole('button', { name: 'Nouveau cours' }));
    await user.type(screen.getByLabelText(/Sujet ou domaine/), 'Python');
    await user.click(screen.getByRole('button', { name: 'Analyser et construire le programme' }));
    await user.click(await screen.findByRole('button', { name: 'Valider et créer le cours' }));

    expect(await screen.findByRole('region', { name: 'Tuteur du chapitre' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Explique plus simplement/ }));

    expect(await screen.findByText(/Réponse du tuteur/)).toBeInTheDocument();
    const askReq = api.requests.find((r) => r.url.endsWith('/ask'));
    expect(askReq?.body).toMatchObject({ quick_action: 'simplify' });

    await user.type(screen.getByLabelText('Question au tuteur'), 'Pourquoi ValueError ?');
    await user.click(screen.getByRole('button', { name: 'Envoyer la question au tuteur' }));
    expect(await screen.findByText('Pourquoi ValueError ?')).toBeInTheDocument();
  });

  it('permet de créer un cours depuis le Copilote IA uniquement après validation explicite', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    render(
      <AppProviders initialSession={TEST_API_SESSION}>
        <MemoryRouter initialEntries={['/ai-coach']}>
          <Routes>
            <Route path="/ai-coach" element={<AiCoachPage />} />
            <Route path="/courses/:courseId" element={<CoursesPage />} />
          </Routes>
        </MemoryRouter>
      </AppProviders>,
    );

    await user.type(
      await screen.findByLabelText(/Votre message au Copilote/),
      'Crée un cours complet pour apprendre Python',
    );
    await user.click(screen.getByRole('button', { name: 'Envoyer au Copilote' }));

    expect(await screen.findByText('Nouveau cours complet')).toBeInTheDocument();
    expect(screen.getByText('En attente de validation')).toBeInTheDocument();
    expect(api.state.courses).toHaveLength(0);

    await user.click(screen.getByRole('button', { name: 'Valider et exécuter' }));
    expect(await screen.findByText('Exécutée')).toBeInTheDocument();

    expect(api.state.courses).toHaveLength(1);
    expect(api.state.courses[0].subject).toBe('Python');
    expect(api.state.courses[0].current_level).toBe(1);
    expect(screen.getByRole('link', { name: 'Ouvrir le cours' })).toBeInTheDocument();
  });
});
