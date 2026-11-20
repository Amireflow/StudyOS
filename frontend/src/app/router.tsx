import { useState } from 'react';
import { createBrowserRouter, RouterProvider, type RouteObject } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { RequireAuth } from '../state/AuthContext';
import { AiCoachPage } from '../features/ai-coach/AiCoachPage';
import { LoginPage } from '../features/auth/LoginPage';
import { CoursesPage } from '../features/courses/CoursesPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { LearningPage } from '../features/learning/LearningPage';
import { ProjectsPage } from '../features/projects/ProjectsPage';
import { PlanningPage } from '../features/schedule/PlanningPage';
import { SessionsPage } from '../features/sessions/SessionsPage';
import { SettingsPage } from '../features/settings/SettingsPage';
import { SkillsPage } from '../features/skills/SkillsPage';
import { TasksPage } from '../features/tasks/TasksPage';
import { NotFoundPage } from './NotFoundPage';

export const appRoutes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginPage />,
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
        element: <DashboardPage />,
      },
      {
        path: 'planning',
        element: <PlanningPage />,
      },
      {
        path: 'tasks',
        element: <TasksPage />,
      },
      {
        path: 'sessions',
        element: <SessionsPage />,
      },
      {
        path: 'courses',
        element: <CoursesPage />,
      },
      {
        path: 'courses/:courseId',
        element: <CoursesPage />,
      },
      {
        path: 'learning',
        element: <LearningPage />,
      },
      {
        path: 'skills',
        element: <SkillsPage />,
      },
      {
        path: 'projects',
        element: <ProjectsPage />,
      },
      {
        path: 'objectives',
        element: <ProjectsPage />,
      },
      {
        path: 'ai-coach',
        element: <AiCoachPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
];

export function AppRouter() {
  const [router] = useState(() => createBrowserRouter(appRoutes));
  return <RouterProvider router={router} />;
}
