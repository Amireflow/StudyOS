import type { IconSvgElement } from '@hugeicons/react';
import {
  AiChat02Icon,
  Calendar03Icon,
  DashboardSquare01Icon,
  Mortarboard02Icon,
} from '@hugeicons/core-free-icons';

export interface NavigationItem {
  id: string;
  label: string;
  shortLabel: string;
  path: string;
  icon: IconSvgElement;
  group: 'principal';
  showInMobileBar: true;
}

/**
 * Navigation principale volontairement limitée aux quatre espaces produit V2.
 * Les vues secondaires restent accessibles depuis leurs espaces, sans être
 * supprimées du routeur ni des APIs.
 */
export const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  {
    id: 'dashboard',
    label: "Aujourd'hui",
    shortLabel: "Aujourd'hui",
    path: '/',
    icon: DashboardSquare01Icon,
    group: 'principal',
    showInMobileBar: true,
  },
  {
    id: 'courses',
    label: 'Apprendre',
    shortLabel: 'Apprendre',
    path: '/courses',
    icon: Mortarboard02Icon,
    group: 'principal',
    showInMobileBar: true,
  },
  {
    id: 'planning',
    label: 'Planning',
    shortLabel: 'Planning',
    path: '/planning',
    icon: Calendar03Icon,
    group: 'principal',
    showInMobileBar: true,
  },
  {
    id: 'ai-coach',
    label: 'Copilote',
    shortLabel: 'Copilote',
    path: '/ai-coach',
    icon: AiChat02Icon,
    group: 'principal',
    showInMobileBar: true,
  },
];
