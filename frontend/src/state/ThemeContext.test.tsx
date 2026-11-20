import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../app/providers';
import { appRoutes } from '../app/router';
import { ThemeToggleButton } from '../components/ui/ThemeToggle';
import { STORAGE_KEYS } from '../lib/storage';
import { installMockStudyApi, TEST_API_SESSION } from '../test/mockStudyApi';
import { ThemeProvider, useTheme } from './ThemeContext';

const originalMatchMedia = window.matchMedia;

function installMatchMediaMock(initialMatches: boolean) {
  let matches = initialMatches;
  const listeners = new Set<(event: MediaQueryListEvent) => void>();

  const mql = {
    get matches() {
      return matches;
    },
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addEventListener: vi.fn((type: string, cb: EventListenerOrEventListenerObject) => {
      if (type === 'change' && typeof cb === 'function') {
        listeners.add(cb as (event: MediaQueryListEvent) => void);
      }
    }),
    removeEventListener: vi.fn((type: string, cb: EventListenerOrEventListenerObject) => {
      if (type === 'change' && typeof cb === 'function') {
        listeners.delete(cb as (event: MediaQueryListEvent) => void);
      }
    }),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  } as unknown as MediaQueryList;

  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn(() => mql),
  });

  return {
    setMatches(next: boolean) {
      matches = next;
      const event = { matches: next, media: '(prefers-color-scheme: dark)' } as MediaQueryListEvent;
      for (const listener of listeners) {
        listener(event);
      }
    },
  };
}

function ThemeProbe() {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme-pref">{theme}</span>
      <span data-testid="theme-resolved">{resolvedTheme}</span>
      <button type="button" onClick={() => setTheme('dark')}>
        Forcer sombre
      </button>
      <button type="button" onClick={() => setTheme('light')}>
        Forcer clair
      </button>
      <button type="button" onClick={() => setTheme('system')}>
        Forcer système
      </button>
      <button type="button" onClick={toggleTheme}>
        Basculer
      </button>
    </div>
  );
}

  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: originalMatchMedia,
    });
  });

describe('ThemeContext et contrôles de thème', () => {
  it('utilise le mode système par défaut et suit prefers-color-scheme sans matchMedia ou avec matchMedia', () => {
    const controller = installMatchMediaMock(true);

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByTestId('theme-pref')).toHaveTextContent('system');
    expect(screen.getByTestId('theme-resolved')).toHaveTextContent('dark');
    expect(document.documentElement).toHaveClass('dark');
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(document.documentElement.style.colorScheme).toBe('dark');

    act(() => {
      controller.setMatches(false);
    });

    expect(screen.getByTestId('theme-resolved')).toHaveTextContent('light');
    expect(document.documentElement).not.toHaveClass('dark');
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(document.documentElement.style.colorScheme).toBe('light');
  });

  it('persiste la préférence dans localStorage et met à jour la classe .dark', async () => {
    const user = userEvent.setup();
    installMatchMediaMock(false);

    render(
      <ThemeProvider>
        <ThemeProbe />
        <ThemeToggleButton />
      </ThemeProvider>,
    );

    const quickToggle = screen.getByRole('button', { name: 'Passer en mode sombre' });
    expect(quickToggle).toHaveAttribute('aria-pressed', 'false');

    await user.click(quickToggle);

    expect(screen.getByTestId('theme-pref')).toHaveTextContent('dark');
    expect(screen.getByTestId('theme-resolved')).toHaveTextContent('dark');
    expect(document.documentElement).toHaveClass('dark');
    expect(JSON.parse(window.localStorage.getItem(STORAGE_KEYS.theme) ?? 'null')).toBe('dark');

    const switchToLight = screen.getByRole('button', { name: 'Passer en mode clair' });
    expect(switchToLight).toHaveAttribute('aria-pressed', 'true');

    await user.click(switchToLight);

    expect(screen.getByTestId('theme-pref')).toHaveTextContent('light');
    expect(screen.getByTestId('theme-resolved')).toHaveTextContent('light');
    expect(document.documentElement).not.toHaveClass('dark');
    expect(JSON.parse(window.localStorage.getItem(STORAGE_KEYS.theme) ?? 'null')).toBe('light');
  });

  it('recharge une préférence enregistrée et ignore une valeur invalide', () => {
    window.localStorage.setItem(STORAGE_KEYS.theme, JSON.stringify('dark'));
    installMatchMediaMock(false);

    const { unmount } = render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByTestId('theme-pref')).toHaveTextContent('dark');
    expect(screen.getByTestId('theme-resolved')).toHaveTextContent('dark');
    expect(document.documentElement).toHaveClass('dark');
    unmount();

    window.localStorage.setItem(STORAGE_KEYS.theme, JSON.stringify('valeur-inconnue'));
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByTestId('theme-pref')).toHaveTextContent('system');
    expect(screen.getByTestId('theme-resolved')).toHaveTextContent('light');
    expect(document.documentElement).not.toHaveClass('dark');
  });

  it('permet de piloter Clair / Sombre / Système depuis la page Paramètres et la barre latérale', async () => {
    installMockStudyApi();
    const user = userEvent.setup();
    installMatchMediaMock(false);

    const router = createMemoryRouter(appRoutes, {
      initialEntries: ['/settings'],
    });

    render(
      <AppProviders initialSession={TEST_API_SESSION}>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    const group = await screen.findByRole('group', { name: 'Choix du thème d’affichage' });
    const lightBtn = within(group).getByRole('button', { name: 'Clair' });
    const darkBtn = within(group).getByRole('button', { name: 'Sombre' });
    const systemBtn = within(group).getByRole('button', { name: 'Système' });

    expect(systemBtn).toHaveAttribute('aria-pressed', 'true');

    await user.click(darkBtn);
    expect(darkBtn).toHaveAttribute('aria-pressed', 'true');
    expect(document.documentElement).toHaveClass('dark');
    expect(JSON.parse(window.localStorage.getItem(STORAGE_KEYS.theme) ?? 'null')).toBe('dark');

    const sidebarAside = screen.getByLabelText('Navigation principale').closest('aside');
    expect(sidebarAside).not.toBeNull();
    const sidebarToggle = within(sidebarAside!).getByRole('button', {
      name: 'Passer en mode clair',
    });

    await user.click(sidebarToggle);
    expect(lightBtn).toHaveAttribute('aria-pressed', 'true');
    expect(document.documentElement).not.toHaveClass('dark');

    await user.click(systemBtn);
    expect(systemBtn).toHaveAttribute('aria-pressed', 'true');
    expect(JSON.parse(window.localStorage.getItem(STORAGE_KEYS.theme) ?? 'null')).toBe('system');
  });
});
