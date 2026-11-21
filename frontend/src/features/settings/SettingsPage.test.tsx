import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '../../app/providers';
import { installMockStudyApi, TEST_API_SESSION } from '../../test/mockStudyApi';
import { SettingsPage } from './SettingsPage';

function renderSettingsPage() {
  return render(
    <AppProviders initialSession={TEST_API_SESSION}>
      <MemoryRouter initialEntries={['/settings']}>
        <SettingsPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe('SettingsPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('propose une navigation interne par intention entre les sections de paramètres', async () => {
    installMockStudyApi();
    renderSettingsPage();

    const nav = await screen.findByRole('navigation', { name: 'Sections des paramètres' });
    expect(within(nav).getByRole('link', { name: 'Profil' })).toHaveAttribute('href', '#settings-profile');
    expect(within(nav).getByRole('link', { name: 'Fournisseur IA' })).toHaveAttribute('href', '#settings-ai-provider');
    expect(within(nav).getByRole('link', { name: 'Sécurité' })).toHaveAttribute('href', '#settings-security');
    expect(document.getElementById('settings-security')).toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: 'Apparence' })).toHaveAttribute('href', '#settings-appearance');
    expect(within(nav).getByRole('link', { name: 'Espace de travail' })).toHaveAttribute('href', '#settings-workspace');
    expect(within(nav).getByRole('link', { name: 'Connexions' })).toHaveAttribute('href', '#settings-connections');
    expect(document.getElementById('settings-profile')).toBeInTheDocument();
    expect(document.getElementById('settings-ai-provider')).toBeInTheDocument();
    expect(document.getElementById('settings-appearance')).toBeInTheDocument();
    expect(document.getElementById('settings-workspace')).toBeInTheDocument();
    expect(document.getElementById('settings-connections')).toBeInTheDocument();
  });

  it('permet d’appliquer un fuseau rapide, un préréglage de consignes Copilote et d’enregistrer le profil via l’API sans boutons d’exemple', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderSettingsPage();

    expect(await screen.findByText('Profil à jour')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Charger des exemples' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Réinitialiser toutes les données locales' }),
    ).not.toBeInTheDocument();

    const nameInput = screen.getByLabelText(/Nom d’affichage/);
    await user.clear(nameInput);
    await user.type(nameInput, 'A');
    await user.click(screen.getByRole('button', { name: 'Enregistrer les paramètres' }));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Le nom d’affichage doit contenir au moins 2 caractères.',
    );

    await user.clear(nameInput);
    await user.type(nameInput, 'Khadim Ndiaye');
    await user.click(screen.getByRole('button', { name: 'Europe/Paris' }));
    await user.click(screen.getByRole('button', { name: 'Concis' }));

    expect(screen.getByText('Non enregistré')).toBeInTheDocument();
    expect(screen.getByLabelText(/Consignes pour le copilote IA/)).toHaveValue(
      'Aller droit au but avec des actions concrètes et mesurables.',
    );

    await user.click(screen.getByRole('button', { name: 'Enregistrer les paramètres' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Paramètres du profil enregistrés.');
    expect(await screen.findByText('Profil à jour')).toBeInTheDocument();
    expect(api.state.profile.display_name).toBe('Khadim Ndiaye');
    expect(api.state.profile.timezone).toBe('Europe/Paris');
  });

  it('sélectionne River AI (console.river.ai), récupère automatiquement les modèles disponibles via le relais backend et permet de choisir un modèle', async () => {
    const api = installMockStudyApi();
    const user = userEvent.setup();
    renderSettingsPage();

    const providerSelect = await screen.findByLabelText('Fournisseur IA');
    await user.selectOptions(providerSelect, 'river');

    expect(screen.getByRole('link', { name: 'console.river.ai' })).toBeInTheDocument();
    expect(screen.getByLabelText('URL de base API')).toHaveValue('https://api.river.ai/v1');

    const apiKeyInput = screen.getByLabelText('Clé API du fournisseur');
    await user.type(apiKeyInput, 'rk_live_test_key_1234');

    await waitFor(
      () => {
        expect(api.requests).toContainEqual(
          expect.objectContaining({
            method: 'POST',
            url: 'http://localhost:8000/api/v1/ai/provider/models',
            body: expect.objectContaining({
              provider: 'river',
              api_key: 'rk_live_test_key_1234',
              base_url: 'https://api.river.ai/v1',
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
