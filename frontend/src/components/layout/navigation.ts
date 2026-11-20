import type { IconSvgElement } from '@hugeicons/react';
import {
  AiChat02Icon,
  Award02Icon,
  BookOpen01Icon,
  Calendar03Icon,
  CheckmarkSquare02Icon,
  DashboardSquare01Icon,
  FolderKanbanIcon,
  Mortarboard02Icon,
  Settings02Icon,
  Timer02Icon,
} from '@hugeicons/core-free-icons';

export interface NavigationItem {
  id: string;
  label: string;
  shortLabel: string;
  path: string;
  icon: IconSvgElement;
  group: 'principal' | 'pied';
  targetLot: string;
  priorityTier?: 'P0' | 'P1';
  showInMobileBar?: boolean;
}

export const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Tableau de bord',
    shortLabel: 'Accueil',
    path: '/',
    icon: DashboardSquare01Icon,
    group: 'principal',
    targetLot: 'Lot 1–2',
    priorityTier: 'P0',
    showInMobileBar: true,
  },
  {
    id: 'planning',
    label: 'Planning',
    shortLabel: 'Planning',
    path: '/planning',
    icon: Calendar03Icon,
    group: 'principal',
    targetLot: 'Lot 3',
    priorityTier: 'P0',
    showInMobileBar: true,
  },
  {
    id: 'tasks',
    label: 'Tâches',
    shortLabel: 'Tâches',
    path: '/tasks',
    icon: CheckmarkSquare02Icon,
    group: 'principal',
    targetLot: 'Lot 2',
    priorityTier: 'P0',
    showInMobileBar: true,
  },
  {
    id: 'sessions',
    label: 'Séances',
    shortLabel: 'Séances',
    path: '/sessions',
    icon: Timer02Icon,
    group: 'principal',
    targetLot: 'Lot 2',
    priorityTier: 'P0',
    showInMobileBar: true,
  },
  {
    id: 'courses',
    label: 'Cours',
    shortLabel: 'Cours',
    path: '/courses',
    icon: Mortarboard02Icon,
    group: 'principal',
    targetLot: 'Cours IA',
    priorityTier: 'P0',
  },
  {
    id: 'learning',
    label: 'Apprentissage',
    shortLabel: 'Parcours',
    path: '/learning',
    icon: BookOpen01Icon,
    group: 'principal',
    targetLot: 'Lot 6',
    priorityTier: 'P0',
  },
  {
    id: 'skills',
    label: 'Compétences',
    shortLabel: 'Compétences',
    path: '/skills',
    icon: Award02Icon,
    group: 'principal',
    targetLot: 'Lot 6',
    priorityTier: 'P0',
  },
  {
    id: 'projects',
    label: 'Mes objectifs et projets',
    shortLabel: 'Objectifs',
    path: '/projects',
    icon: FolderKanbanIcon,
    group: 'principal',
    targetLot: 'Lot 6',
    priorityTier: 'P1',
  },
  {
    id: 'ai-coach',
    label: 'Copilote IA',
    shortLabel: 'Copilote',
    path: '/ai-coach',
    icon: AiChat02Icon,
    group: 'principal',
    targetLot: 'Lot 7',
    priorityTier: 'P0',
    showInMobileBar: true,
  },
  {
    id: 'settings',
    label: 'Paramètres',
    shortLabel: 'Réglages',
    path: '/settings',
    icon: Settings02Icon,
    group: 'pied',
    targetLot: 'Lot 5–6',
    priorityTier: 'P0',
  },
];
