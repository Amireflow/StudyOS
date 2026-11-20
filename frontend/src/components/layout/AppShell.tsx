import { useEffect, useState } from 'react';
import {
  Cancel01Icon,
  Download01Icon,
  Logout01Icon,
  Menu01Icon,
} from '@hugeicons/core-free-icons';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { cn } from '../../lib/cn';
import { usePwaInstall } from '../../lib/pwa';
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
  const [isInstallGuideOpen, setIsInstallGuideOpen] = useState(false);
  const location = useLocation();
  const { isStandalone, canShowInstallOption, isIos, triggerInstall } = usePwaInstall();

  const principalItems = NAVIGATION_ITEMS.filter((item) => item.group === 'principal');
  const footerItems = NAVIGATION_ITEMS.filter((item) => item.group === 'pied');
  const mobileBarItems = NAVIGATION_ITEMS.filter((item) => item.showInMobileBar);

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
      <header className="pt-safe sticky top-0 z-30 bg-[#f5f5f3]/95 backdrop-blur-md lg:hidden dark:bg-zinc-950/95">
        <div className="flex h-12 items-center justify-between px-3.5 sm:h-14 sm:px-4">
          <BrandLogo />
          <div className="flex items-center gap-1.5">
            {canShowInstallOption && (
              <button
                type="button"
                onClick={() => void handleInstallClick()}
                aria-label="Installer l’application sur le téléphone"
                className="inline-flex h-8 items-center gap-1 rounded-lg bg-teal-700 px-2.5 text-xs font-semibold text-white transition-transform active:scale-95 dark:bg-teal-600"
              >
                <Icon icon={Download01Icon} size={14} />
                <span>Installer</span>
              </button>
            )}
            <ThemeToggleButton className="h-9 w-9 active:scale-95" />
            <button
              type="button"
              onClick={() => setIsMobileMenuOpen((prev) => !prev)}
              aria-expanded={isMobileMenuOpen}
              aria-controls="mobile-navigation-drawer"
              aria-label={isMobileMenuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
              className="inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg bg-zinc-100 text-zinc-700 transition-all hover:bg-zinc-200/70 active:scale-95 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
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
              <div className="mt-6 space-y-2 pt-3">
                {!isStandalone && (
                  <button
                    type="button"
                    onClick={() => void handleInstallClick()}
                    className="flex w-full items-center gap-2.5 rounded-xl bg-teal-50 px-3 py-2.5 text-left text-xs font-semibold text-teal-900 transition-colors hover:bg-teal-100/80 dark:bg-teal-950/50 dark:text-teal-200 dark:hover:bg-teal-950/80"
                  >
                    <Icon icon={Download01Icon} size={16} className="shrink-0 text-teal-700 dark:text-teal-400" />
                    <span>Installer l’app mobile (plein écran)</span>
                  </button>
                )}
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
          className="mx-auto w-full min-w-0 max-w-5xl px-3.5 pb-20 pt-3 outline-none sm:px-6 sm:pb-24 sm:pt-4 lg:px-8 lg:py-7"
        >
          <Outlet />
        </main>
      </div>

      {/* Barre de navigation basse Mobile-First */}
      <nav
        aria-label="Accès rapide mobile"
        className="pb-safe fixed inset-x-0 bottom-0 z-30 bg-[#f5f5f3]/95 px-2 pt-1.5 backdrop-blur-md lg:hidden dark:bg-zinc-950/95"
      >
        <ul className="mx-auto grid max-w-md grid-cols-5 gap-1">
          {mobileBarItems.map((item) => (
            <li key={item.id} className="min-w-0">
              <NavLink
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-11 min-w-0 flex-col items-center justify-center gap-0.5 overflow-hidden rounded-lg px-1 py-0.5 text-[11px] transition-all active:scale-95',
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
                    <span className="max-w-full truncate">{item.shortLabel}</span>
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
