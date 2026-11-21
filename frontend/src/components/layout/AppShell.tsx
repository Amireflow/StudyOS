import { useEffect, useRef, useState } from 'react';
import {
  Cancel01Icon,
  Download01Icon,
  Logout01Icon,
  Menu01Icon,
  Settings02Icon,
} from '@hugeicons/core-free-icons';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { cn } from '../../lib/cn';
import { usePwaInstall } from '../../lib/pwa';
import { useAuth } from '../../state/AuthContext';
import { Button } from '../ui/Button';
import { Icon } from '../ui/Icon';
import { ScrollArea } from '../ui/ScrollArea';
import { ThemeToggleButton } from '../ui/ThemeToggle';
import { NAVIGATION_ITEMS, type NavigationItem } from './navigation';
import { WorkspaceSectionNavigation } from './WorkspaceSectionNavigation';

interface NavigationListProps {
  items: readonly NavigationItem[];
  onItemClick?: () => void;
}

function pathMatches(pathname: string, basePath: string): boolean {
  return pathname === basePath || pathname.startsWith(basePath + '/');
}

function NavigationList({ items, onItemClick }: NavigationListProps) {
  const { pathname } = useLocation();

  return (
    <ul className="space-y-0.5">
      {items.map((item) => {
        const sectionActive =
          (item.id === 'courses' &&
            ['/courses', '/learning', '/skills'].some((path) => pathMatches(pathname, path))) ||
          (item.id === 'planning' &&
            ['/planning', '/tasks', '/sessions'].some((path) => pathMatches(pathname, path)));

        return (
          <li key={item.id}>
            <Link
              to={item.path}
              onClick={onItemClick}
              aria-current={sectionActive || pathname === item.path ? 'page' : undefined}
              className={cn(
                'group flex min-h-11 items-center rounded-lg px-3 py-2 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400',
                sectionActive || pathname === item.path
                  ? 'bg-zinc-900 font-semibold text-white dark:bg-zinc-100 dark:text-zinc-950'
                  : 'font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100',
              )}
            >
              <span className="flex items-center gap-3">
                <Icon
                  icon={item.icon}
                  size={17}
                  className={cn(
                    'shrink-0 transition-colors',
                    sectionActive || pathname === item.path
                      ? 'text-teal-300 dark:text-teal-700'
                      : 'text-zinc-400 group-hover:text-zinc-700 dark:text-zinc-500 dark:group-hover:text-zinc-200',
                  )}
                />
                <span>{item.label}</span>
              </span>
            </Link>
          </li>
        );
      })}
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
      <Link
        to="/settings"
        className="flex min-h-10 w-full items-center gap-2 rounded-lg px-2.5 text-xs font-medium text-zinc-600 transition-colors hover:bg-zinc-200/70 hover:text-zinc-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:text-zinc-300 dark:hover:bg-zinc-700 dark:hover:text-zinc-50 dark:focus-visible:outline-teal-400"
      >
        <Icon icon={Settings02Icon} size={15} />
        Paramètres
      </Link>
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
  const [isInstallGuideOpen, setIsInstallGuideOpen] = useState(false);
  const mobileMenuTriggerRef = useRef<HTMLButtonElement>(null);
  const mobileDrawerRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const { isStandalone, canShowInstallOption, isIos, triggerInstall } = usePwaInstall();

  const principalItems = NAVIGATION_ITEMS;
  const mobileBarItems = NAVIGATION_ITEMS;

  async function handleInstallClick() {
    const outcome = await triggerInstall();
    if (outcome === 'ios_guide') {
      setIsMobileMenuOpen(false);
      setIsInstallGuideOpen(true);
    } else if (outcome === 'installed') {
      setIsMobileMenuOpen(false);
    }
  }

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isMobileMenuOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const focusableSelector = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const getFocusableElements = () =>
      Array.from(mobileDrawerRef.current?.querySelectorAll<HTMLElement>(focusableSelector) ?? []);

    getFocusableElements()[0]?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setIsMobileMenuOpen(false);
        return;
      }

      if (event.key !== 'Tab') return;
      const focusable = getFocusableElements();
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      mobileMenuTriggerRef.current?.focus();
    };
  }, [isMobileMenuOpen]);

  return (
    <div className="min-h-dvh overflow-x-clip bg-[#f5f5f3] text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
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
          <ThemeToggleButton className="h-10 w-10" />
        </div>

        <ScrollArea
          as="nav"
          aria-label="Navigation principale"
          className="flex-1"
          viewportClassName="px-3 py-3"
        >
          <NavigationList items={principalItems} />
        </ScrollArea>
        <div className="px-3 pb-4 pt-2">
          <SessionFooter />
        </div>
      </aside>

      {/* En-tête mobile sticky */}
      <header className="pt-safe sticky top-0 z-30 bg-[#f5f5f3]/95 backdrop-blur-md lg:hidden dark:bg-zinc-950/95">
        <div className="flex h-12 items-center justify-between px-3.5 sm:h-14 sm:px-4">
          <BrandLogo />
          <div className="flex items-center gap-1.5">
            {canShowInstallOption && (
              <button
                type="button"
                onClick={() => void handleInstallClick()}
                aria-label="Installer l’application sur le téléphone"
                className="inline-flex min-h-11 items-center gap-1 rounded-lg bg-teal-700 px-2.5 text-xs font-semibold text-white transition-transform active:scale-95 dark:bg-teal-600"
              >
                <Icon icon={Download01Icon} size={14} />
                <span>Installer</span>
              </button>
            )}
            <ThemeToggleButton className="h-11 w-11 active:scale-95" />
            <button
              type="button"
              ref={mobileMenuTriggerRef}
              onClick={() => setIsMobileMenuOpen((prev) => !prev)}
              aria-expanded={isMobileMenuOpen}
              aria-controls="mobile-navigation-drawer"
              aria-label={isMobileMenuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
              className="inline-flex h-11 w-11 cursor-pointer items-center justify-center rounded-lg bg-zinc-100 text-zinc-700 transition-all hover:bg-zinc-200/70 active:scale-95 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
            >
              <Icon icon={isMobileMenuOpen ? Cancel01Icon : Menu01Icon} size={18} />
            </button>
          </div>
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
            ref={mobileDrawerRef}
            className="relative flex h-full w-72 max-w-[85vw] flex-col bg-white dark:bg-zinc-900"
          >
            <div className="flex h-14 items-center justify-between px-4">
              <BrandLogo />
              <button
                type="button"
                onClick={() => setIsMobileMenuOpen(false)}
                aria-label="Fermer le menu"
                className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100 cursor-pointer"
              >
                <Icon icon={Cancel01Icon} size={18} />
              </button>
            </div>

            <ScrollArea
              as="nav"
              aria-label="Navigation mobile"
              className="flex-1"
              viewportClassName="px-3 py-3"
            >
              <NavigationList
                items={principalItems}
                onItemClick={() => setIsMobileMenuOpen(false)}
              />
              {!isStandalone && (
                <button
                  type="button"
                  onClick={() => void handleInstallClick()}
                  className="mt-6 flex w-full items-center gap-2.5 rounded-xl bg-teal-50 px-3 py-2.5 text-left text-xs font-semibold text-teal-900 transition-colors hover:bg-teal-100/80 dark:bg-teal-950/50 dark:text-teal-200 dark:hover:bg-teal-950/80"
                >
                  <Icon icon={Download01Icon} size={16} className="shrink-0 text-teal-700 dark:text-teal-400" />
                  <span>Installer l’app mobile (plein écran)</span>
                </button>
              )}
            </ScrollArea>
            <div className="px-3 pb-4 pt-2">
              <SessionFooter />
            </div>
          </div>
        </div>
      )}

      {isInstallGuideOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center p-3 sm:items-center">
          <div
            className="fixed inset-0 bg-zinc-950/40 backdrop-blur-[1px] dark:bg-black/65"
            aria-hidden="true"
            onClick={() => setIsInstallGuideOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Installer Amireflow sur votre téléphone"
            className="relative w-full max-w-sm space-y-3 rounded-2xl bg-white p-5 shadow-lg dark:bg-zinc-900"
          >
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Installer Amireflow en plein écran
              </h2>
              <button
                type="button"
                onClick={() => setIsInstallGuideOpen(false)}
                aria-label="Fermer l’aide d’installation"
                className="rounded-lg p-1 text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                <Icon icon={Cancel01Icon} size={16} />
              </button>
            </div>
            {isIos ? (
              <ol className="list-inside list-decimal space-y-2 text-xs leading-relaxed text-zinc-600 dark:text-zinc-300">
                <li>
                  Appuyez sur le bouton <strong>Partager</strong> en bas de Safari.
                </li>
                <li>
                  Choisissez <strong>Sur l’écran d’accueil</strong> puis validez.
                </li>
                <li>
                  Lancez <strong>Amireflow</strong> depuis votre écran d’accueil pour l’utiliser sans barre de navigateur.
                </li>
              </ol>
            ) : (
              <ol className="list-inside list-decimal space-y-2 text-xs leading-relaxed text-zinc-600 dark:text-zinc-300">
                <li>
                  Ouvrez le menu <strong>⋮</strong> de votre navigateur mobile (Chrome / Edge / Samsung).
                </li>
                <li>
                  Appuyez sur <strong>Installer l’application</strong> ou <strong>Ajouter à l’écran d’accueil</strong>.
                </li>
                <li>
                  Ouvrez <strong>Amireflow</strong> depuis votre écran d’accueil en mode plein écran natif.
                </li>
              </ol>
            )}
            <Button
              type="button"
              variant="primary"
              size="sm"
              className="w-full"
              onClick={() => setIsInstallGuideOpen(false)}
            >
              Compris
            </Button>
          </div>
        </div>
      )}

      {/* Contenu principal */}
      <div className="min-w-0 lg:pl-60">
        <main
          id="main-content"
          tabIndex={-1}
          className="mx-auto w-full min-w-0 max-w-5xl px-3.5 pb-24 pt-3 outline-none sm:px-6 sm:pb-28 sm:pt-4 lg:px-8 lg:py-7"
        >
          <WorkspaceSectionNavigation />
          <Outlet />
        </main>
      </div>

      {/* Barre de navigation basse Mobile-First */}
      <nav
        aria-label="Accès rapide mobile"
        className="pb-safe fixed inset-x-0 bottom-0 z-30 bg-[#f5f5f3]/95 px-2 pt-1.5 backdrop-blur-md lg:hidden dark:bg-zinc-950/95"
      >
        <ul className="mx-auto grid max-w-md grid-cols-4 gap-1">
          {mobileBarItems.map((item) => {
            const sectionActive =
              (item.id === 'courses' &&
                ['/courses', '/learning', '/skills'].some((path) => pathMatches(location.pathname, path))) ||
              (item.id === 'planning' &&
                ['/planning', '/tasks', '/sessions'].some((path) => pathMatches(location.pathname, path)));
            const active = location.pathname === item.path || sectionActive;

            return (
              <li key={item.id} className="min-w-0">
                <Link
                  to={item.path}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'flex min-h-12 min-w-0 flex-col items-center justify-center gap-0.5 overflow-hidden rounded-lg px-1 py-1 text-[11px] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 dark:focus-visible:outline-teal-400',
                    active
                      ? 'font-semibold text-zinc-950 dark:text-zinc-50'
                      : 'font-medium text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200',
                  )}
                >
                  <span
                    className={cn(
                      'flex h-7 w-10 items-center justify-center rounded-full transition-colors',
                      active
                        ? 'bg-zinc-900 text-teal-300 dark:bg-zinc-100 dark:text-teal-700'
                        : 'text-zinc-500 dark:text-zinc-400',
                    )}
                  >
                    <Icon icon={item.icon} size={16} />
                  </span>
                  <span className="max-w-full truncate">{item.shortLabel}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
