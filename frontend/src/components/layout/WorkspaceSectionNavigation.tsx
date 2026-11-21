import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../lib/cn';

type WorkspaceSection = 'learning' | 'organization';

const SECTION_LINKS: Record<WorkspaceSection, Array<{ label: string; path: string }>> = {
  learning: [
    { label: 'Mes cours', path: '/courses' },
    { label: 'Parcours', path: '/learning' },
    { label: 'Compétences', path: '/skills' },
  ],
  organization: [
    { label: 'Planning', path: '/planning' },
    { label: 'Tâches', path: '/tasks' },
    { label: 'Séances', path: '/sessions' },
  ],
};

function getWorkspaceSection(pathname: string): WorkspaceSection | null {
  if (pathname === '/courses' || pathname.startsWith('/courses/') || pathname === '/learning' || pathname === '/skills') {
    return 'learning';
  }
  if (pathname === '/planning' || pathname === '/tasks' || pathname === '/sessions') {
    return 'organization';
  }
  return null;
}

/**
 * Sous-navigation partagée : navigation vers une page, jamais un onglet
 * qui masque ou détruit le contexte de la page précédente.
 */
export function WorkspaceSectionNavigation() {
  const { pathname } = useLocation();
  const section = getWorkspaceSection(pathname);

  if (!section) return null;

  const isCourseDetail = section === 'learning' && pathname.startsWith('/courses/');
  const title = section === 'learning' ? 'Apprentissage' : 'Organisation';

  return (
    <nav
      aria-label={'Navigation ' + title}
      className={cn(
        'mb-4 flex min-w-0 items-center gap-2 overflow-x-auto rounded-xl border border-zinc-200/80 bg-white/80 p-1.5 dark:border-zinc-800 dark:bg-zinc-900/80',
        isCourseDetail ? 'sm:mb-3' : 'sm:mb-5',
      )}
    >
      <span className="hidden shrink-0 px-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 sm:inline">
        {title}
      </span>
      <div className="flex min-w-0 items-center gap-1">
        {SECTION_LINKS[section].map((link) => (
          <NavLink
            key={link.path}
            to={link.path}
            end={link.path !== '/courses'}
            className={({ isActive }) =>
              cn(
                'inline-flex min-h-10 shrink-0 items-center justify-center rounded-lg px-3 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:focus-visible:outline-teal-400',
                isActive
                  ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950'
                  : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800 dark:hover:text-zinc-50',
                isCourseDetail && 'min-h-9 text-xs',
              )
            }
          >
            {link.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
