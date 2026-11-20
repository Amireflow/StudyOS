import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App';
import { initPwaSupport } from './lib/pwa';
import './index.css';

initPwaSupport();

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Élément racine #root introuvable dans index.html.');
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
