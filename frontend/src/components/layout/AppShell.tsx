import { useEffect, useState } from 'react';
import { Cancel01Icon, Logout01Icon, Menu01Icon } from '@hugeicons/core-free-icons';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { cn } from '../../lib/cn';
import { useAuth } from '../../state/AuthContext';
import { Button } from '../ui/Button';
import { Icon } from '../ui/Icon';
import { ScrollArea } from '../ui/ScrollArea';
import { ThemeToggleButton } from '../ui/ThemeToggle';
import { NAVIGATION_ITEMS, type NavigationItem } from './navigation';

interface NavigationListProps {
  items: readonly NavigationItem[];
  onItemClick?: () => void;
}

function NavigationList({ items, onItemClick }: NavigationListProps) {
  return (
    <ul className="space-y-0.5">
      {items.map((item) => (
        <li key={item.id}>
          <NavLink
            to={item.path}
            end={item.path === '/'}
            onClick={onItemClick}
            className={({ isActive }) =>
              cn(
                'group flex min-h-10 items-center rounded-lg px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-zinc-900 font-semibold text-white dark:bg-zinc-100 dark:text-zinc-950'
                  : 'font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100',
              )
            }
          >
            {({ isActive }) => (
              <span className="flex items-center gap-3">
                <Icon
                  icon={item.icon}
                  size={17}
                  className={cn(
                    'shrink-0 transition-colors',
                    isActive
                      ? 'text-teal-300 dark:text-teal-700'
                      : 'text-zinc-400 group-hover:text-zinc-700 dark:text-zinc-500 dark:group-hover:text-zinc-200',
                  )}
                />
                <span>{item.label}</span>
              </span>
            )}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

function BrandLogo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900 text-xs font-bold tracking-tight text-white dark:bg-zinc-100 dark:text-zinc-950">
        AF
      </div>
      <p className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Amireflow
      </p>
    </div>
  );
}

function SessionFooter() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  if (!session) {
    return null;
  }

  return (
    <div className="mt-3 space-y-1.5 rounded-xl bg-zinc-100/70 p-2.5 dark:bg-zinc-800/70">
      <div className="px-1">
        <p className="truncate text-xs font-semibold text-zinc-800 dark:text-zinc-200">
          {session.displayName}
        </p>
        {session.email && (
          <p className="truncate text-[11px] text-zinc-500 dark:text-zinc-400">
            {session.email}
          </p>
        )}
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start text-zinc-600 dark:text-zinc-300"
        onClick={() => {
          navigate('/login', { replace: true, state: null });
          logout();
        }}
      >
        <Icon icon={Logout01Icon} size={15} />
        Déconnexion
      </Button>
    </div>
  );
}

/**
 * Gabarit principal Mobile-First épuré (zéro bordure, zéro ombre).
 */
export function AppShell() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const principalItems = NAVIGATION_ITEMS.filter((item) => item.group === 'principal');
  const footerItems = NAVIGATION_ITEMS.filter((item) => item.group === 'pied');
  const mobileBarItems = NAVIGATION_ITEMS.filter((item) => item.showInMobileBar);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isMobileMenuOpen) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsMobileMenuOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMobileMenuOpen]);

  return (
    <div className="min-h-dvh bg-[#f5f5f3] text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-zinc-900 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white dark:focus:bg-zinc-100 dark:focus:text-zinc-950"
      >
        Aller au contenu principal
      </a>

      {/* Barre latérale fixe sur ordinateur */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-60 lg:flex-col lg:bg-white dark:lg:bg-zinc-900">
        <div className="flex h-14 items-center justify-between px-4 pl-5">
          <BrandLogo />
          <ThemeToggleButton className="h-8 w-8" />
        </div>

        <ScrollArea
          as="nav"
          aria-label="Navigation principale"
          className="flex-1"
          viewportClassName="flex flex-col justify-between px-3 py-3"
        >
          <NavigationList items={principalItems} />

          <div className="mt-6 pt-3">
            <NavigationList items={footerItems} />
            <SessionFooter />
          </div>
        </ScrollArea>
      </aside>

      {/* En-tête mobile sticky */}
      <header className="sticky top-0 z-30 flex h-12 items-center justify-between bg-white/95 px-3.5 backdrop-blur-xs sm:h-14 sm:px-4 lg:hidden dark:bg-zinc-900/95">
        <BrandLogo />
        <div className="flex items-center gap-1.5">
          <ThemeToggleButton className="h-9 w-9" />
          <button
            type="button"
            onClick={() => setIsMobileMenuOpen((prev) => !prev)}
            aria-expanded={isMobileMenuOpen}
            aria-controls="mobile-navigation-drawer"
            aria-label={isMobileMenuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700 transition-colors hover:bg-zinc-200/70 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700 cursor-pointer"
          >
            <Icon icon={isMobileMenuOpen ? Cancel01Icon : Menu01Icon} size={18} />
          </button>
        </div>
      </header>

      {/* Tiroir de navigation mobile complet */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="fixed inset-0 bg-zinc-950/30 backdrop-blur-[1px] dark:bg-black/60"
            aria-hidden="true"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <div
            id="mobile-navigation-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Menu de navigation"
            className="relative flex h-full w-72 max-w-[85vw] flex-col bg-white dark:bg-zinc-900"
          >
            <div className="flex h-14 items-center justify-between px-4">
              <BrandLogo />
              <button
                type="button"
                onClick={() => setIsMobileMenuOpen(false)}
                aria-label="Fermer le menu"
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100 cursor-pointer"
              >
                <Icon icon={Cancel01Icon} size={18} />
              </button>
            </div>

            <ScrollArea
              as="nav"
              aria-label="Navigation mobile"
              className="flex-1"
              viewportClassName="flex flex-col justify-between px-3 py-3"
            >
              <NavigationList
                items={principalItems}
                onItemClick={() => setIsMobileMenuOpen(false)}
              />
              <div className="mt-6 pt-3">
                <NavigationList
                  items={footerItems}
                  onItemClick={() => setIsMobileMenuOpen(false)}
                />
                <SessionFooter />
              </div>
            </ScrollArea>
          </div>
        </div>
      )}

      {/* Contenu principal */}
      <div className="lg:pl-60">
        <main
          id="main-content"
          tabIndex={-1}
          className="mx-auto max-w-5xl px-3.5 pb-20 pt-3 outline-none sm:px-6 sm:pb-24 sm:pt-4 lg:px-8 lg:py-7"
        >
          <Outlet />
        </main>
      </div>

      {/* Barre de navigation basse Mobile-First */}
      <nav
        aria-label="Accès rapide mobile"
        className="pb-safe fixed inset-x-0 bottom-0 z-30 bg-white/95 px-2 pt-1 backdrop-blur-xs lg:hidden dark:bg-zinc-900/95"
      >
        <ul className="mx-auto grid max-w-md grid-cols-5 gap-1">
          {mobileBarItems.map((item) => (
            <li key={item.id}>
              <NavLink
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-11 flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-0.5 text-[11px] transition-colors',
                    isActive
                      ? 'font-semibold text-zinc-950 dark:text-zinc-50'
                      : 'font-medium text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={cn(
                        'flex h-6 w-9 items-center justify-center rounded-full transition-colors',
                        isActive
                          ? 'bg-zinc-900 text-teal-300 dark:bg-zinc-100 dark:text-teal-700'
                          : 'text-zinc-500 dark:text-zinc-400',
                      )}
                    >
                      <Icon icon={item.icon} size={16} />
                    </span>
                    <span className="truncate">{item.shortLabel}</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
