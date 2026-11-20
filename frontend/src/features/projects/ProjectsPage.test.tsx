import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { AppProviders } from '../../app/providers';
import { STORAGE_KEYS } from '../../lib/storage';
import { ProjectsPage } from './ProjectsPage';

function renderProjectsPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <ProjectsPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('ProjectsPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('exige une prochaine action pour un projet actif (PROJ-02), avertit au-delà de 3 actifs (PROJ-01) et définit le projet prioritaire (PROJ-03)', async () => {
    const user = userEvent.setup();

    // 3 projets actifs préexistants
    const now = new Date().toISOString();
    window.localStorage.setItem(
      STORAGE_KEYS.learningState,
      JSON.stringify({
        paths: [],
        modules: [],
        lessons: [],
        skills: [],
        evidence: [],
        projects: [1, 2, 3].map((idx) => ({
          id: `proj-${idx}`,
          userId: 'local-user',
          name: `Projet actif ${idx}`,
          description: null,
          goal: `Objectif ${idx}`,
          status: 'active',
          priority: 'normal',
          nextAction: `Action concrète ${idx}`,
          deliverables: null,
          targetDate: null,
          createdAt: now,
          updatedAt: now,
        })),
      }),
    );

    renderProjectsPage();

    // Tenter de créer un 4e projet actif sans prochaine action -> erreur PROJ-02
    await user.click(screen.getByRole('button', { name: 'Nouveau projet' }));
    await user.type(screen.getByLabelText(/Nom du projet/), 'Amireflow OS');
    await user.type(screen.getByLabelText(/Objectif mesurable/), 'Livrer le Lot 6');
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Une prochaine action concrète est obligatoire pour un projet actif.',
    );

    // Renseigner la prochaine action et tenter de créer le 4e projet actif -> blocage à 3 actifs max (PROJ-01)
    await user.type(screen.getByLabelText(/Prochaine action concrète/), 'Lancer les tests finaux');
    await user.type(screen.getByLabelText(/Livrables/), 'Backend Lot 6\nFrontend Lot 6');
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Limite de 3 projets actifs atteinte');

    // Mettre un projet existant en pause libère une place, permettant de créer le 4e projet actif
    await user.selectOptions(screen.getByLabelText('Statut du projet Projet actif 1'), 'paused');
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    expect(screen.getByText('Backend Lot 6')).toBeInTheDocument();

    // Définir comme priorité principale (PROJ-03)
    const prioButtons = screen.getAllByRole('button', { name: 'Définir comme priorité' });
    await user.click(prioButtons[0]);

    const studyStored = JSON.parse(window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}');
    expect(studyStored.activePriorityProjectId).toBeTruthy();
  });

  it('convertit la prochaine action en tâche liée, filtre par recherche/statut et bascule entre Liste et Tableau', async () => {
    const user = userEvent.setup();
    renderProjectsPage();

    await user.click(screen.getByRole('button', { name: 'Nouveau projet' }));
    await user.type(screen.getByLabelText(/Nom du projet/), 'Refonte API');
    await user.type(screen.getByLabelText(/Objectif mesurable/), '100% des endpoints couverts');
    await user.type(
      screen.getByLabelText(/Prochaine action concrète/),
      'Écrire les tests Pytest des projets',
    );
    await user.click(screen.getByRole('button', { name: '+14 j' }));
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    // Conversion 1-clic de la prochaine action en tâche liée
    await user.click(
      screen.getByRole('button', {
        name: 'Convertir la prochaine action de Refonte API en tâche',
      }),
    );
    expect(screen.getByText('Tâche liée')).toBeInTheDocument();

    const studyStored = JSON.parse(window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}');
    expect(studyStored.tasks).toHaveLength(1);
    expect(studyStored.tasks[0].title).toBe('Écrire les tests Pytest des projets');

    // Bascule en vue Tableau puis retour Liste
    await user.click(screen.getByRole('button', { name: 'Tableau' }));
    expect(screen.getByRole('heading', { name: 'Planifiés' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Liste' }));

    // Recherche sans résultat puis réinitialisation
    await user.type(screen.getByLabelText('Rechercher un projet'), 'Inexistant');
    expect(
      screen.getByText('Aucun projet ne correspond aux filtres'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByRole('article', { name: 'Refonte API' })).toBeInTheDocument();
  });

  it('ajoute des objectifs personnels (React, Python), permet de les suspendre/reprendre et isole les cours universitaires', async () => {
    const user = userEvent.setup();
    const nowIso = new Date().toISOString();
    const endIso = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();

    window.localStorage.setItem(
      STORAGE_KEYS.studyState,
      JSON.stringify({
        profile: { displayName: 'Khadim', timezone: 'Africa/Dakar', aiInstructions: null },
        activePriorityTitle: null,
        activePriorityTaskId: null,
        activePriorityProjectId: null,
        tasks: [],
        sessions: [],
        scheduleEvents: [
          {
            id: 'acad-1',
            userId: 'local-user',
            title: 'Génie Logiciel L3',
            type: 'course',
            source: 'timetable_import',
            startsAt: nowIso,
            endsAt: endIso,
            notes: null,
            createdAt: nowIso,
            updatedAt: nowIso,
          },
        ],
      }),
    );

    renderProjectsPage();

    expect(screen.getByText(/1 cours ou examen fixe/i)).toBeInTheDocument();

    // Ajout guidé de React (seul le titre requis au départ)
    await user.click(screen.getByRole('button', { name: 'Nouvel objectif' }));
    await user.type(screen.getByLabelText(/Titre de l’objectif/), 'React');
    await user.selectOptions(screen.getByLabelText(/Catégorie d’objectif/), 'framework');
    await user.click(screen.getByRole('button', { name: 'Créer l’objectif' }));

    expect(screen.getByRole('article', { name: 'Objectif React' })).toBeInTheDocument();

    // Ajout de Python
    await user.click(screen.getByRole('button', { name: 'Nouvel objectif' }));
    await user.type(screen.getByLabelText(/Titre de l’objectif/), 'Python');
    await user.selectOptions(screen.getByLabelText(/Catégorie d’objectif/), 'language');
    await user.click(screen.getByRole('button', { name: 'Créer l’objectif' }));

    expect(screen.getByRole('article', { name: 'Objectif Python' })).toBeInTheDocument();
    // L'obligation académique reste à 1 et n'a pas absorbé React ou Python
    expect(screen.getByText(/1 cours ou examen fixe/i)).toBeInTheDocument();
    expect(screen.getByText(/2 objectifs d’apprentissage/i)).toBeInTheDocument();

    // Suspendre puis reprendre React
    await user.click(screen.getByRole('button', { name: 'Suspendre React' }));
    expect(screen.getByRole('article', { name: 'Objectif React' })).toHaveTextContent('En pause');

    await user.click(screen.getByRole('button', { name: 'Reprendre React' }));
    expect(screen.getByRole('article', { name: 'Objectif React' })).toHaveTextContent('Actif');
  });

  it('collecte les besoins en langage naturel sans inventer les champs manquants et attend la confirmation avant enregistrement', async () => {
    const user = userEvent.setup();
    renderProjectsPage();

    await user.click(screen.getByRole('button', { name: 'Décrire à l’IA' }));
    await user.type(
      screen.getByLabelText(/Décrire vos objectifs en langage naturel/),
      'Je veux continuer Python, apprendre React, améliorer mes compétences en développement web et construire des projets pratiques.',
    );
    await user.click(screen.getByRole('button', { name: 'Analyser mes besoins' }));

    const intakeSection = screen.getByRole('region', { name: 'Décrire mes besoins à l’IA' });
    expect(intakeSection).toHaveTextContent(/React/);
    expect(intakeSection).toHaveTextContent(/Python/);
    expect(intakeSection).toHaveTextContent(/Développement web/);
    // Ne doit rien inventer sur le niveau ou le temps disponible
    expect(intakeSection).toHaveTextContent(/Niveau actuel\s*:\s*Non renseigné/i);
    expect(intakeSection).toHaveTextContent(/Temps disponible\s*:\s*Non renseigné/i);

    // Rien n'est enregistré avant confirmation explicite
    expect(window.localStorage.getItem(STORAGE_KEYS.objectivesState)).toBeNull();

    // Compléter progressivement niveau et temps hebdomadaire puis confirmer
    await user.type(screen.getByLabelText(/Préciser niveau actuel/), '2');
    await user.type(screen.getByLabelText(/Temps disponible/), '300');
    await user.selectOptions(screen.getByLabelText(/Priorité principale/), 'React');
    await user.click(screen.getByRole('button', { name: 'Actualiser le récapitulatif' }));

    expect(intakeSection).toHaveTextContent('2/5');
    expect(intakeSection).toHaveTextContent('300 min / semaine');

    await user.click(screen.getByRole('button', { name: 'Confirmer et enregistrer' }));

    const savedGoals = JSON.parse(window.localStorage.getItem(STORAGE_KEYS.objectivesState) ?? '[]');
    expect(savedGoals.length).toBeGreaterThanOrEqual(3);
    const savedLearning = JSON.parse(window.localStorage.getItem(STORAGE_KEYS.learningState) ?? '{}');
    expect(savedLearning.projects.length).toBeGreaterThanOrEqual(1);
  });

  it('génère et applique un programme unifié combinant cours fixe, objectif personnel et projet sans chevauchement', async () => {
    const user = userEvent.setup();
    const now = new Date();
    const dayOffset = (now.getDay() + 6) % 7;
    const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - dayOffset);
    const pad = (n: number) => String(n).padStart(2, '0');
    const mondayKey = `${monday.getFullYear()}-${pad(monday.getMonth() + 1)}-${pad(monday.getDate())}`;

    const acadStart = new Date(`${mondayKey}T08:30:00`).toISOString();
    const acadEnd = new Date(`${mondayKey}T10:30:00`).toISOString();

    window.localStorage.setItem(
      STORAGE_KEYS.studyState,
      JSON.stringify({
        profile: { displayName: 'Khadim', timezone: 'Africa/Dakar', aiInstructions: null },
        activePriorityTitle: 'React',
        activePriorityTaskId: null,
        activePriorityProjectId: null,
        tasks: [],
        sessions: [],
        scheduleEvents: [
          {
            id: 'acad-mon',
            userId: 'local-user',
            title: 'Algorithmique avancée',
            type: 'course',
            source: 'timetable_import',
            startsAt: acadStart,
            endsAt: acadEnd,
            notes: null,
            createdAt: acadStart,
            updatedAt: acadStart,
          },
        ],
      }),
    );

    window.localStorage.setItem(
      STORAGE_KEYS.learningState,
      JSON.stringify({
        paths: [],
        modules: [],
        lessons: [],
        skills: [],
        evidence: [],
        assessments: [],
        projects: [
          {
            id: 'proj-web-1',
            userId: 'local-user',
            name: 'Portfolio StudyOS',
            description: null,
            goal: 'Livrer une application React',
            status: 'active',
            priority: 'high',
            nextAction: 'Coder la page des projets',
            deliverables: ['Vitrine React'],
            targetDate: null,
            createdAt: acadStart,
            updatedAt: acadStart,
          },
        ],
      }),
    );

    window.localStorage.setItem(
      STORAGE_KEYS.objectivesState,
      JSON.stringify([
        {
          id: 'goal-react',
          userId: 'local-user',
          category: 'framework',
          title: 'React',
          description: null,
          goal: 'Maîtriser composants et hooks',
          currentLevel: 1,
          targetLevel: 4,
          priority: 'high',
          isPrimary: true,
          motivation: 'Construire des interfaces',
          startDate: acadStart,
          targetDate: null,
          weeklyTargetMinutes: 180,
          status: 'active',
          steps: [],
          deliverables: ['Mini-app React'],
          nextAction: 'Étudier composants et props',
          successCriteria: ['Tests unitaires passants'],
          progressHistory: [],
          skillId: null,
          learningPathId: null,
          courseId: null,
          completedMinutesLast7d: 0,
          sessionsCount: 0,
          isBehindSchedule: false,
          delayReason: null,
          createdAt: acadStart,
          updatedAt: acadStart,
        },
      ]),
    );

    renderProjectsPage();

    await user.click(screen.getByRole('button', { name: 'Programme unifié' }));
    await user.click(screen.getByRole('button', { name: 'Générer le programme unifié' }));

    const planRegion = screen.getByRole('region', {
      name: 'Programme unifié hors et dans emploi du temps',
    });
    expect(planRegion).toHaveTextContent('Algorithmique avancée');
    expect(planRegion).toHaveTextContent(/React/);
    expect(planRegion).toHaveTextContent(/Portfolio StudyOS/);
    expect(planRegion).toHaveTextContent('7 plages protégées');

    await user.click(screen.getByRole('button', { name: 'Valider et appliquer au planning' }));

    const storedAfter = JSON.parse(window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}');
    expect(storedAfter.scheduleEvents.length).toBeGreaterThanOrEqual(3);
    // Le cours fixe est intact et aucun bloc flexible généré ne chevauche Lundi 08:30-10:30
    const fixed = storedAfter.scheduleEvents.find((ev: { id: string }) => ev.id === 'acad-mon');
    expect(fixed).toBeTruthy();
    const fixedStartMs = new Date(fixed.startsAt).getTime();
    const fixedEndMs = new Date(fixed.endsAt).getTime();
    for (const ev of storedAfter.scheduleEvents) {
      if (ev.id === 'acad-mon') continue;
      const s = new Date(ev.startsAt).getTime();
      const e = new Date(ev.endsAt).getTime();
      expect(s < fixedEndMs && fixedStartMs < e).toBe(false);
    }
    expect(storedAfter.tasks.length).toBeGreaterThanOrEqual(2);
  });
});
