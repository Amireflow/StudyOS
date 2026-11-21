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
  sectionLabel?: string;
  targetLot: string;
  priorityTier?: 'P0' | 'P1';
  showInMobileBar?: boolean;
}

/**
 * Source unique des destinations. Les sectionLabel structurent seulement
 * l'affichage : chaque page et chaque route historique restent indépendantes.
 */
export const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Tableau de bord',
    shortLabel: 'Accueil',
    path: '/',
    icon: DashboardSquare01Icon,
    group: 'principal',
    targetLot: 'Lot 2',
    priorityTier: 'P0',
    showInMobileBar: true,
  },
  {
    id: 'courses',
    label: 'Cours',
    shortLabel: 'Apprendre',
    path: '/courses',
    icon: Mortarboard02Icon,
    group: 'principal',
    sectionLabel: 'APPRENTISSAGE',
    targetLot: 'Lot 3',
    priorityTier: 'P0',
    showInMobileBar: true,
  },
  {
    id: 'learning',
    label: 'Parcours',
    shortLabel: 'Parcours',
    path: '/learning',
    icon: BookOpen01Icon,
    group: 'principal',
    targetLot: 'Lot 3',
    priorityTier: 'P0',
  },
  {
    id: 'skills',
    label: 'Compétences',
    shortLabel: 'Compétences',
    path: '/skills',
    icon: Award02Icon,
    group: 'principal',
    targetLot: 'Lot 3',
    priorityTier: 'P0',
  },
  {
    id: 'planning',
    label: 'Planning',
    shortLabel: 'Organiser',
    path: '/planning',
    icon: Calendar03Icon,
    group: 'principal',
    sectionLabel: 'ORGANISATION',
    targetLot: 'Lot 4',
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
    targetLot: 'Lot 4',
    priorityTier: 'P0',
  },
  {
    id: 'sessions',
    label: 'Séances',
    shortLabel: 'Séances',
    path: '/sessions',
    icon: Timer02Icon,
    group: 'principal',
    targetLot: 'Lot 4',
    priorityTier: 'P0',
  },
  {
    id: 'projects',
    label: 'Objectifs & projets',
    shortLabel: 'Projets',
    path: '/projects',
    icon: FolderKanbanIcon,
    group: 'principal',
    sectionLabel: 'PROJETS',
    targetLot: 'Lot 5',
    priorityTier: 'P1',
    showInMobileBar: true,
  },
  {
    id: 'ai-coach',
    label: 'Copilote IA',
    shortLabel: 'IA',
    path: '/ai-coach',
    icon: AiChat02Icon,
    group: 'principal',
    sectionLabel: 'ASSISTANCE',
    targetLot: 'Lot 5',
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
    targetLot: 'Lot 5',
    priorityTier: 'P0',
  },
];
