import { describe, expect, it } from 'vitest';
import { DEFAULT_API_BASE_URL, normalizeApiBaseUrl } from './env';

describe('normalizeApiBaseUrl', () => {
  it('retourne l’URL par défaut si la valeur est vide ou invalide', () => {
    expect(normalizeApiBaseUrl(undefined)).toBe(DEFAULT_API_BASE_URL);
    expect(normalizeApiBaseUrl('')).toBe(DEFAULT_API_BASE_URL);
    expect(normalizeApiBaseUrl('   ')).toBe(DEFAULT_API_BASE_URL);
    expect(normalizeApiBaseUrl('not a valid url')).toBe(DEFAULT_API_BASE_URL);
    expect(normalizeApiBaseUrl('ftp://api.example.com/api/v1')).toBe(DEFAULT_API_BASE_URL);
  });

  it('supprime les slashs finaux d’une URL complète avec /api/v1', () => {
    expect(normalizeApiBaseUrl('https://amireflow-study-os-api.onrender.com/api/v1/')).toBe(
      'https://amireflow-study-os-api.onrender.com/api/v1',
    );
    expect(normalizeApiBaseUrl('https://amireflow-study-os-api.onrender.com/api/v1///')).toBe(
      'https://amireflow-study-os-api.onrender.com/api/v1',
    );
  });

  it('ajoute /api/v1 automatiquement pour une URL Render racine', () => {
    expect(normalizeApiBaseUrl('https://amireflow-study-os-api.onrender.com')).toBe(
      'https://amireflow-study-os-api.onrender.com/api/v1',
    );
    expect(normalizeApiBaseUrl('https://amireflow-study-os-api.onrender.com/')).toBe(
      'https://amireflow-study-os-api.onrender.com/api/v1',
    );
  });

  it('ajoute https:// et /api/v1 si seul un nom d’hôte nu est fourni', () => {
    expect(normalizeApiBaseUrl('amireflow-study-os-api.onrender.com')).toBe(
      'https://amireflow-study-os-api.onrender.com/api/v1',
    );
  });

  it('supporte les chemins relatifs de proxy et préserve un préfixe personnalisé', () => {
    expect(normalizeApiBaseUrl('/api/v1/')).toBe('/api/v1');
    expect(normalizeApiBaseUrl('/')).toBe('/api/v1');
    expect(normalizeApiBaseUrl('https://api.example.com/study/api/v1/')).toBe(
      'https://api.example.com/study/api/v1',
    );
  });
});
