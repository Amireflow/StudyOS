import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { installMockStudyApi, TEST_API_SESSION, TEST_USER_ID } from '../../test/mockStudyApi';
import { ProjectsPage } from './ProjectsPage';

async function openManualProjectForm(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Options des projets' }));
  await user.click(screen.getByRole('button', { name: 'Nouveau projet manuel' }));
}

function renderProjectsPage() {
  return render(
    <AppProviders initialSession={TEST_API_SESSION}>
      <MemoryRouter>
        <ProjectsPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('ProjectsPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('exige une prochaine action pour un projet actif (PROJ-02), avertit au-delà de 3 actifs (PROJ-01) et définit le projet prioritaire (PROJ-03)', async () => {
    const now = new Date().toISOString();
    const api = installMockStudyApi({
      projects: [1, 2, 3].map((idx) => ({
        id: `proj-${idx}`,
        user_id: TEST_USER_ID,
        name: `Projet actif ${idx}`,
        description: null,
        goal: `Objectif ${idx}`,
        status: 'active',
        priority: 'normal',
        next_action: `Action concrète ${idx}`,
        deliverables: null,
        target_date: null,
        created_at: now,
        updated_at: now,
      })),
    });

    const user = userEvent.setup();
    renderProjectsPage();

    await openManualProjectForm(user);
    await user.type(screen.getByLabelText(/Nom du projet/), 'Amireflow OS');
    await user.type(screen.getByLabelText(/Objectif mesurable/), 'Livrer le Lot 6');
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Une prochaine action concrète est obligatoire pour un projet actif.',
    );

    await user.type(screen.getByLabelText(/Prochaine action concrète/), 'Lancer les tests finaux');
    await user.type(screen.getByLabelText(/Livrables/), 'Backend Lot 6\nFrontend Lot 6');
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Limite de 3 projets actifs atteinte');

    await user.selectOptions(screen.getByLabelText('Statut du projet Projet actif 1'), 'paused');
    await waitFor(() => {
      expect(api.state.projects.find((p) => p.id === 'proj-1')?.status).toBe('paused');
    });
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    expect(await screen.findByText('Backend Lot 6')).toBeInTheDocument();

    const prioButtons = screen.getAllByRole('button', { name: 'Définir comme priorité' });
    await user.click(prioButtons[0]);

    await waitFor(() => {
      expect(api.state.profile.active_priority_project_id).toBeTruthy();
    });
  });

  it('convertit la prochaine action en tâche liée, filtre par recherche/statut et bascule entre Liste et Tableau', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderProjectsPage();

    await openManualProjectForm(user);
    await user.type(screen.getByLabelText(/Nom du projet/), 'Refonte API');
    await user.type(screen.getByLabelText(/Objectif mesurable/), '100% des endpoints couverts');
    await user.type(
      screen.getByLabelText(/Prochaine action concrète/),
      'Écrire les tests Pytest des projets',
    );
    await user.click(screen.getByRole('button', { name: '+14 j' }));
    await user.click(screen.getByRole('button', { name: 'Créer le projet' }));

    await user.click(
      await screen.findByRole('button', {
        name: 'Convertir la prochaine action de Refonte API en tâche',
      }),
    );
    expect(await screen.findByText('Tâche liée')).toBeInTheDocument();

    expect(api.state.tasks).toHaveLength(1);
    expect(api.state.tasks[0].title).toBe('Écrire les tests Pytest des projets');

    const statusFilters = screen.getByRole('group', { name: 'Filtrer les projets par statut' });
    const allFilter = within(statusFilters).getByRole('button', { name: 'Tous' });
    const plannedFilter = within(statusFilters).getByRole('button', { name: 'Planifiés' });
    expect(allFilter).toHaveAttribute('aria-pressed', 'true');
    await user.click(plannedFilter);
    expect(plannedFilter).toHaveAttribute('aria-pressed', 'true');
    expect(allFilter).toHaveAttribute('aria-pressed', 'false');

    const activeFilter = within(statusFilters).getByRole('button', { name: 'Actifs' });
    await user.click(activeFilter);
    expect(activeFilter).toHaveAttribute('aria-pressed', 'true');
    expect(plannedFilter).toHaveAttribute('aria-pressed', 'false');

    await user.click(screen.getByRole('button', { name: 'Tableau' }));
    expect(screen.getByRole('heading', { name: 'Planifiés' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Liste' }));

    await user.type(screen.getByLabelText('Rechercher un projet'), 'Inexistant');
    expect(
      screen.getByText('Aucun projet ne correspond aux filtres'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }));
    expect(screen.getByRole('article', { name: 'Refonte API' })).toBeInTheDocument();
  });

  it('ajoute des objectifs personnels (React, Python), permet de les suspendre/reprendre et isole les cours universitaires', async () => {
    const nowIso = new Date().toISOString();
    const endIso = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();

    installMockStudyApi({
      scheduleEvents: [
        {
          id: 'acad-1',
          user_id: TEST_USER_ID,
          title: 'Génie Logiciel L3',
          type: 'course',
          source: 'timetable_import',
          starts_at: nowIso,
          ends_at: endIso,
          notes: null,
          created_at: nowIso,
          updated_at: nowIso,
        },
      ],
    });

    const user = userEvent.setup();
    renderProjectsPage();

    expect(await screen.findByText(/1 cours ou examen fixe/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Options des projets' }));
    await user.click(screen.getByRole('button', { name: 'Nouvel objectif manuel' }));
    await user.type(screen.getByLabelText(/Titre de l’objectif/), 'React');
    await user.selectOptions(screen.getByLabelText(/Catégorie d’objectif/), 'framework');
    await user.click(screen.getByRole('button', { name: 'Créer l’objectif' }));

    expect(await screen.findByRole('article', { name: 'Objectif React' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Options des projets' }));
    await user.click(screen.getByRole('button', { name: 'Nouvel objectif manuel' }));
    await user.type(screen.getByLabelText(/Titre de l’objectif/), 'Python');
    await user.selectOptions(screen.getByLabelText(/Catégorie d’objectif/), 'language');
    await user.click(screen.getByRole('button', { name: 'Créer l’objectif' }));

    expect(await screen.findByRole('article', { name: 'Objectif Python' })).toBeInTheDocument();
    expect(screen.getByText(/1 cours ou examen fixe/i)).toBeInTheDocument();
    expect(screen.getByText(/2 objectifs d’apprentissage/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Suspendre React' }));
    await waitFor(() => {
      expect(screen.getByRole('article', { name: 'Objectif React' })).toHaveTextContent('En pause');
    });

    await user.click(screen.getByRole('button', { name: 'Reprendre React' }));
    await waitFor(() => {
      expect(screen.getByRole('article', { name: 'Objectif React' })).toHaveTextContent('Actif');
    });
  });

  it('collecte les besoins en langage naturel sans inventer les champs manquants et attend la confirmation avant enregistrement', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderProjectsPage();

    await user.click(await screen.findByRole('button', { name: 'Décrire à l’IA' }));
    await user.type(
      screen.getByLabelText(/Décrire vos objectifs en langage naturel/),
      'Je veux continuer Python, apprendre React, améliorer mes compétences en développement web et construire des projets pratiques.',
    );
    await user.click(screen.getByRole('button', { name: 'Analyser mes besoins' }));

    const intakeSection = screen.getByRole('region', { name: 'Décrire mes besoins à l’IA' });
    await waitFor(() => {
      expect(intakeSection).toHaveTextContent(/React/);
    });
    expect(intakeSection).toHaveTextContent(/Python/);
    expect(intakeSection).toHaveTextContent(/Développement web/);
    expect(intakeSection).toHaveTextContent(/Niveau actuel\s*:\s*Non renseigné/i);
    expect(intakeSection).toHaveTextContent(/Temps disponible\s*:\s*Non renseigné/i);

    expect(api.state.personalGoals).toHaveLength(0);

    await user.type(screen.getByLabelText(/Préciser niveau actuel/), '2');
    await user.type(screen.getByLabelText(/Temps disponible/), '300');
    await user.selectOptions(screen.getByLabelText(/Priorité principale/), 'React');
    await user.click(screen.getByRole('button', { name: 'Actualiser le récapitulatif' }));

    await waitFor(() => {
      expect(intakeSection).toHaveTextContent('2/5');
      expect(intakeSection).toHaveTextContent('300 min / semaine');
    });

    await user.click(screen.getByRole('button', { name: 'Confirmer et enregistrer' }));

    await waitFor(() => {
      expect(api.state.personalGoals.length).toBeGreaterThanOrEqual(3);
      expect(api.state.projects.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('génère et applique un programme unifié combinant cours fixe, objectif personnel et projet sans chevauchement', async () => {
    const now = new Date();
    const dayOffset = (now.getDay() + 6) % 7;
    const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - dayOffset);
    const pad = (n: number) => String(n).padStart(2, '0');
    const mondayKey = `${monday.getFullYear()}-${pad(monday.getMonth() + 1)}-${pad(monday.getDate())}`;

    const acadStart = new Date(`${mondayKey}T08:30:00`).toISOString();
    const acadEnd = new Date(`${mondayKey}T10:30:00`).toISOString();

    const api = installMockStudyApi({
      profile: {
        active_priority_title: 'React',
      },
      scheduleEvents: [
        {
          id: 'acad-mon',
          user_id: TEST_USER_ID,
          title: 'Algorithmique avancée',
          type: 'course',
          source: 'timetable_import',
          starts_at: acadStart,
          ends_at: acadEnd,
          notes: null,
          created_at: acadStart,
          updated_at: acadStart,
        },
      ],
      projects: [
        {
          id: 'proj-web-1',
          user_id: TEST_USER_ID,
          name: 'Portfolio StudyOS',
          description: null,
          goal: 'Livrer une application React',
          status: 'active',
          priority: 'high',
          next_action: 'Coder la page des projets',
          deliverables: ['Vitrine React'],
          target_date: null,
          created_at: acadStart,
          updated_at: acadStart,
        },
      ],
      personalGoals: [
        {
          id: 'goal-react',
          user_id: TEST_USER_ID,
          category: 'framework',
          title: 'React',
          description: null,
          goal: 'Maîtriser composants et hooks',
          current_level: 1,
          target_level: 4,
          priority: 'high',
          is_primary: true,
          motivation: 'Construire des interfaces',
          start_date: acadStart,
          target_date: null,
          weekly_target_minutes: 180,
          status: 'active',
          steps: [],
          deliverables: ['Mini-app React'],
          next_action: 'Étudier composants et props',
          success_criteria: ['Tests unitaires passants'],
          progress_history: [],
          skill_id: null,
          learning_path_id: null,
          course_id: null,
          completed_minutes_last_7d: 0,
          sessions_count: 0,
          is_behind_schedule: false,
          delay_reason: null,
          created_at: acadStart,
          updated_at: acadStart,
        },
      ],
    });

    const user = userEvent.setup();
    renderProjectsPage();

    await user.click(await screen.findByRole('button', { name: 'Programme unifié' }));
    await user.click(screen.getByRole('button', { name: 'Générer le programme unifié' }));

    const planRegion = screen.getByRole('region', {
      name: 'Programme unifié hors et dans emploi du temps',
    });
    await waitFor(() => {
      expect(planRegion).toHaveTextContent('Algorithmique avancée');
    });
    expect(planRegion).toHaveTextContent(/React/);
    expect(planRegion).toHaveTextContent(/Portfolio StudyOS/);
    expect(planRegion).toHaveTextContent('7 plages protégées');

    await user.click(screen.getByRole('button', { name: 'Valider et appliquer au planning' }));

    await waitFor(() => {
      expect(api.state.scheduleEvents.length).toBeGreaterThanOrEqual(3);
    });
    const fixed = api.state.scheduleEvents.find((ev) => ev.id === 'acad-mon');
    expect(fixed).toBeTruthy();
    const fixedStartMs = new Date(fixed!.starts_at).getTime();
    const fixedEndMs = new Date(fixed!.ends_at).getTime();
    for (const ev of api.state.scheduleEvents) {
      if (ev.id === 'acad-mon') continue;
      const s = new Date(ev.starts_at).getTime();
      const e = new Date(ev.ends_at).getTime();
      expect(s < fixedEndMs && fixedStartMs < e).toBe(false);
    }
    expect(api.state.tasks.length).toBeGreaterThanOrEqual(2);
  });
});
