import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { STORAGE_KEYS } from '../../lib/storage';
import { SettingsPage } from './SettingsPage';

function renderSettingsPage() {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={['/settings']}>
        <SettingsPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('SettingsPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('permet d’appliquer un fuseau rapide, un préréglage de consignes Copilote, d’enregistrer le profil et de gérer les données locales', async () => {
    const user = userEvent.setup();
    renderSettingsPage();

    // État initial à jour
    expect(screen.getByText('Profil à jour')).toBeInTheDocument();

    // Validation sur nom d'affichage trop court
    const nameInput = screen.getByLabelText(/Nom d’affichage/);
    await user.clear(nameInput);
    await user.type(nameInput, 'A');
    await user.click(screen.getByRole('button', { name: 'Enregistrer les paramètres' }));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Le nom d’affichage doit contenir au moins 2 caractères.',
    );

    // Saisie valide + pilule de fuseau rapide + préréglage Copilote
    await user.clear(nameInput);
    await user.type(nameInput, 'Khadim');
    await user.click(screen.getByRole('button', { name: 'Europe/Paris' }));
    await user.click(screen.getByRole('button', { name: 'Concis' }));

    expect(screen.getByText('Non enregistré')).toBeInTheDocument();
    expect(screen.getByLabelText(/Consignes pour le copilote IA/)).toHaveValue(
      'Aller droit au but avec des actions concrètes et mesurables.',
    );

    await user.click(screen.getByRole('button', { name: 'Enregistrer les paramètres' }));
    expect(screen.getByRole('status')).toHaveTextContent('Paramètres du profil enregistrés.');
    expect(screen.getByText('Profil à jour')).toBeInTheDocument();

    // Chargement des données d'exemple puis réinitialisation locale
    await user.click(screen.getByRole('button', { name: 'Charger des exemples' }));
    expect(screen.getByRole('status')).toHaveTextContent(
      'Données de démonstration chargées dans l’espace de travail.',
    );

    const studyAfterSeed = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect((studyAfterSeed.tasks ?? []).length).toBeGreaterThan(0);

    await user.click(
      screen.getByRole('button', { name: 'Réinitialiser toutes les données locales' }),
    );
    await user.click(screen.getByRole('button', { name: 'Confirmer' }));

    const studyAfterClear = JSON.parse(
      window.localStorage.getItem(STORAGE_KEYS.studyState) ?? '{}',
    );
    expect(studyAfterClear.tasks ?? []).toHaveLength(0);
  });

  it('sélectionne River AI (console.river.ai), récupère automatiquement les modèles disponibles via la clé API et permet de choisir un modèle', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          data: [
            { id: 'gpt-4o', owned_by: 'openai', context_window: 128000 },
            {
              id: 'claude-3-7-sonnet',
              display_name: 'Claude 3.7 Sonnet',
              owned_by: 'anthropic',
              context_window: 200000,
            },
          ],
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );

    const user = userEvent.setup();
    renderSettingsPage();

    const providerSelect = screen.getByLabelText('Fournisseur IA');
    await user.selectOptions(providerSelect, 'river');

    expect(screen.getByRole('link', { name: 'console.river.ai' })).toBeInTheDocument();
    expect(screen.getByLabelText('URL de base API')).toHaveValue('https://api.river.ai/v1');

    const apiKeyInput = screen.getByLabelText('Clé API du fournisseur');
    await user.type(apiKeyInput, 'rk_live_test_key_1234');

    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledWith(
          'https://api.river.ai/v1/models',
          expect.objectContaining({
            method: 'GET',
            headers: expect.objectContaining({
              Authorization: 'Bearer rk_live_test_key_1234',
            }),
          }),
        );
      },
      { timeout: 2500 },
    );

    expect(await screen.findByText(/2 modèle\(s\) disponible\(s\) récupéré\(s\)/)).toBeInTheDocument();

    const modelSelect = screen.getByLabelText(/Modèle disponible \(2\)/);
    expect(modelSelect).toHaveValue('claude-3-7-sonnet');
    await user.selectOptions(modelSelect, 'gpt-4o');
    expect(modelSelect).toHaveValue('gpt-4o');
  });
});
