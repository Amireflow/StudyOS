import { lazy, Suspense, useState, type ComponentType, type LazyExoticComponent } from 'react';
import { createBrowserRouter, RouterProvider, type RouteObject } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { RequireAuth } from '../state/AuthContext';

const AiCoachPage = lazy(() =>
  import('../features/ai-coach/AiCoachPage').then((module) => ({ default: module.AiCoachPage })),
);
const LoginPage = lazy(() =>
  import('../features/auth/LoginPage').then((module) => ({ default: module.LoginPage })),
);
const CoursesPage = lazy(() =>
  import('../features/courses/CoursesPage').then((module) => ({ default: module.CoursesPage })),
);
const DashboardPage = lazy(() =>
  import('../features/dashboard/DashboardPage').then((module) => ({ default: module.DashboardPage })),
);
const LearningPage = lazy(() =>
  import('../features/learning/LearningPage').then((module) => ({ default: module.LearningPage })),
);
const ProjectsPage = lazy(() =>
  import('../features/projects/ProjectsPage').then((module) => ({ default: module.ProjectsPage })),
);
const PlanningPage = lazy(() =>
  import('../features/schedule/PlanningPage').then((module) => ({ default: module.PlanningPage })),
);
const SessionsPage = lazy(() =>
  import('../features/sessions/SessionsPage').then((module) => ({ default: module.SessionsPage })),
);
const SettingsPage = lazy(() =>
  import('../features/settings/SettingsPage').then((module) => ({ default: module.SettingsPage })),
);
const SkillsPage = lazy(() =>
  import('../features/skills/SkillsPage').then((module) => ({ default: module.SkillsPage })),
);
const TasksPage = lazy(() =>
  import('../features/tasks/TasksPage').then((module) => ({ default: module.TasksPage })),
);
const NotFoundPage = lazy(() =>
  import('./NotFoundPage').then((module) => ({ default: module.NotFoundPage })),
);

type LazyPage = LazyExoticComponent<ComponentType>;

function RouteLoadingFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-[35vh] items-center justify-center px-4 text-sm text-zinc-500 dark:text-zinc-400"
    >
      Chargement de la page…
    </div>
  );
}

function lazyRoute(Component: LazyPage) {
  return (
    <Suspense fallback={<RouteLoadingFallback />}>
      <Component />
    </Suspense>
  );
}

export const appRoutes: RouteObject[] = [
  {
    path: '/login',
    element: lazyRoute(LoginPage),
  },
  {
    path: '/',
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      {
        index: true,
        element: lazyRoute(DashboardPage),
      },
      {
        path: 'planning',
        element: lazyRoute(PlanningPage),
      },
      {
        path: 'tasks',
        element: lazyRoute(TasksPage),
      },
      {
        path: 'sessions',
        element: lazyRoute(SessionsPage),
      },
      {
        path: 'courses',
        element: lazyRoute(CoursesPage),
      },
      {
        path: 'courses/:courseId',
        element: lazyRoute(CoursesPage),
      },
      {
        path: 'learning',
        element: lazyRoute(LearningPage),
      },
      {
        path: 'skills',
        element: lazyRoute(SkillsPage),
      },
      {
        path: 'projects',
        element: lazyRoute(ProjectsPage),
      },
      {
        path: 'objectives',
        element: lazyRoute(ProjectsPage),
      },
      {
        path: 'ai-coach',
        element: lazyRoute(AiCoachPage),
      },
      {
        path: 'settings',
        element: lazyRoute(SettingsPage),
      },
      {
        path: '*',
        element: lazyRoute(NotFoundPage),
      },
    ],
  },
];

export function AppRouter() {
  const [router] = useState(() => createBrowserRouter(appRoutes));
  return <RouterProvider router={router} />;
}
