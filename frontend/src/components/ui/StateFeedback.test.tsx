import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Button } from './Button';
import { EmptyState, ErrorState, LoadingState, SuccessBanner } from './StateFeedback';

describe('Composants de retour visuel (StateFeedback)', () => {
  it('affiche LoadingState avec un rôle status accessible', () => {
    render(<LoadingState message="Chargement des tâches…" />);

    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('Chargement des tâches…');
  });

  it('affiche EmptyState avec son titre, sa description et son action cliquable', async () => {
    const user = userEvent.setup();
    const handleCreate = vi.fn();

    render(
      <EmptyState
        title="Aucune tâche"
        description="Ajoutez une première action pour démarrer."
        action={<Button onClick={handleCreate}>Créer une tâche</Button>}
      />,
    );

    expect(screen.getByRole('heading', { name: 'Aucune tâche' })).toBeInTheDocument();
    expect(screen.getByText('Ajoutez une première action pour démarrer.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Créer une tâche' }));
    expect(handleCreate).toHaveBeenCalledTimes(1);
  });

  it('affiche ErrorState avec un rôle alert et déclenche onRetry au clic', async () => {
    const user = userEvent.setup();
    const handleRetry = vi.fn();

    render(<ErrorState message="Impossible de joindre le serveur." onRetry={handleRetry} />);

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Impossible de joindre le serveur.');

    await user.click(screen.getByRole('button', { name: 'Réessayer' }));
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it('affiche SuccessBanner et permet sa fermeture', async () => {
    const user = userEvent.setup();
    const handleDismiss = vi.fn();

    render(<SuccessBanner message="Tâche enregistrée." onDismiss={handleDismiss} />);

    expect(screen.getByRole('status')).toHaveTextContent('Tâche enregistrée.');

    await user.click(screen.getByRole('button', { name: 'Fermer la confirmation' }));
    expect(handleDismiss).toHaveBeenCalledTimes(1);
  });
});
