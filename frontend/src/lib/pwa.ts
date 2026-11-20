import { useCallback, useEffect, useState } from 'react';

export interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
  prompt(): Promise<void>;
}

let deferredInstallPrompt: BeforeInstallPromptEvent | null = null;
const listeners = new Set<() => void>();

function notifyListeners() {
  for (const listener of listeners) {
    listener();
  }
}

export function isStandalonePwa(): boolean {
  if (typeof window === 'undefined') return false;
  const isStandaloneMedia =
    typeof window.matchMedia === 'function' &&
    (window.matchMedia('(display-mode: standalone)').matches ||
      window.matchMedia('(display-mode: fullscreen)').matches ||
      window.matchMedia('(display-mode: minimal-ui)').matches);
  const isIosStandalone =
    'standalone' in window.navigator &&
    Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone);
  return Boolean(isStandaloneMedia || isIosStandalone);
}

export function isIosDevice(): boolean {
  if (typeof window === 'undefined' || typeof window.navigator === 'undefined') return false;
  const ua = window.navigator.userAgent || '';
  return /iPad|iPhone|iPod/i.test(ua) || (ua.includes('Mac') && 'ontouchend' in document);
}

export function initPwaSupport(): void {
  if (typeof window === 'undefined' || import.meta.env.MODE === 'test') {
    return;
  }

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event as BeforeInstallPromptEvent;
    notifyListeners();
  });

  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null;
    notifyListeners();
  });

  if ('serviceWorker' in window.navigator) {
    window.addEventListener('load', () => {
      void window.navigator.serviceWorker
        .register('/sw.js', { scope: '/' })
        .catch(() => {
          // Ignore registration errors in restricted or local dev environments
        });
    });
  }
}

export function usePwaInstall() {
  const [isStandalone, setIsStandalone] = useState<boolean>(() => isStandalonePwa());
  const [hasNativePrompt, setHasNativePrompt] = useState<boolean>(() =>
    Boolean(deferredInstallPrompt),
  );
  const [isIos] = useState<boolean>(() => isIosDevice());

  useEffect(() => {
    const sync = () => {
      setIsStandalone(isStandalonePwa());
      setHasNativePrompt(Boolean(deferredInstallPrompt));
    };
    listeners.add(sync);

    let mql: MediaQueryList | null = null;
    if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
      mql = window.matchMedia('(display-mode: standalone)');
      mql.addEventListener?.('change', sync);
    }

    return () => {
      listeners.delete(sync);
      mql?.removeEventListener?.('change', sync);
    };
  }, []);

  const triggerInstall = useCallback(async (): Promise<'installed' | 'dismissed' | 'ios_guide'> => {
    if (deferredInstallPrompt) {
      const promptEvent = deferredInstallPrompt;
      await promptEvent.prompt();
      const choice = await promptEvent.userChoice;
      if (choice.outcome === 'accepted') {
        deferredInstallPrompt = null;
        notifyListeners();
        return 'installed';
      }
      return 'dismissed';
    }
    return 'ios_guide';
  }, []);

  return {
    isStandalone,
    hasNativePrompt,
    isIos,
    canShowInstallOption: !isStandalone && (hasNativePrompt || isIos),
    triggerInstall,
  };
}
