import { ComputerIcon, Moon02Icon, Sun02Icon } from '@hugeicons/core-free-icons';
import { cn } from '../../lib/cn';
import { useTheme, type ThemePreference } from '../../state/ThemeContext';
import { Icon } from './Icon';

export interface ThemeToggleButtonProps {
  className?: string;
}

/**
 * Bouton compact de bascule rapide Clair / Sombre (barre latérale, en-tête mobile, connexion).
 */
export function ThemeToggleButton({ className }: ThemeToggleButtonProps) {
  const { resolvedTheme, toggleTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const label = isDark ? 'Passer en mode clair' : 'Passer en mode sombre';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      aria-pressed={isDark}
      title={label}
      className={cn(
        'inline-flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700 transition-colors hover:bg-zinc-200/80 hover:text-zinc-950 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700 dark:hover:text-white cursor-pointer',
        className,
      )}
    >
      <Icon icon={isDark ? Sun02Icon : Moon02Icon} size={17} />
    </button>
  );
}

const THEME_OPTIONS: ReadonlyArray<{
  value: ThemePreference;
  label: string;
  icon: typeof Sun02Icon;
}> = [
  { value: 'light', label: 'Clair', icon: Sun02Icon },
  { value: 'dark', label: 'Sombre', icon: Moon02Icon },
  { value: 'system', label: 'Système', icon: ComputerIcon },
];

/**
 * Sélecteur segmenté à 3 choix (Clair / Sombre / Système) pour les Paramètres.
 */
export function ThemeSegmentedControl({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="group"
      aria-label="Choix du thème d’affichage"
      className={cn(
        'inline-grid w-full grid-cols-3 gap-1 rounded-xl bg-zinc-100/80 p-1 sm:w-auto dark:bg-zinc-800/80',
        className,
      )}
    >
      {THEME_OPTIONS.map((option) => {
        const isSelected = theme === option.value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={isSelected}
            onClick={() => setTheme(option.value)}
            className={cn(
              'inline-flex min-h-9 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer',
              isSelected
                ? 'bg-white text-zinc-950 dark:bg-zinc-900 dark:text-zinc-50'
                : 'text-zinc-600 hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-100',
            )}
          >
            <Icon
              icon={option.icon}
              size={15}
              className={isSelected ? 'text-teal-700 dark:text-teal-400' : undefined}
            />
            <span>{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
