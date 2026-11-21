import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge } from './Badge';
import { Button } from './Button';
import { Card, CardDescription, CardTitle } from './Card';
import { FormField, Input } from './FormFields';
import { PageHeader } from '../layout/PageHeader';

describe('Design System foundations', () => {
  it('exposes semantic button variants and loading state', () => {
    render(
      <Button variant="primary" size="md" isLoading>
        Enregistrer
      </Button>,
    );

    const button = screen.getByRole('button', { name: 'Enregistrer' });
    expect(button).toHaveClass('ui-button', 'ui-button--primary', 'ui-button--md');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
  });

  it('keeps form labels visible and applies the shared control class', () => {
    render(
      <FormField id="course-title" label="Titre du cours" hint="Un nom court et précis.">
        <Input id="course-title" name="course-title" />
      </FormField>,
    );

    expect(screen.getByLabelText('Titre du cours')).toHaveClass('ui-form-control');
    expect(screen.getByText('Un nom court et précis.')).toHaveClass('ui-field-help');
  });

  it('uses semantic badge and card primitives', () => {
    const { container } = render(
      <>
        <Badge variant="success">Terminé</Badge>
        <Card>
          <CardTitle>Progression</CardTitle>
          <CardDescription>Votre avancée actuelle.</CardDescription>
        </Card>
      </>,
    );

    expect(screen.getByText('Terminé')).toHaveClass('ui-badge', 'ui-badge--success');
    expect(container.querySelector('.ui-card')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Progression' })).toHaveClass('ui-card-title');
    expect(screen.getByText('Votre avancée actuelle.')).toHaveClass('ui-card-description');
  });

  it('does not truncate the page description container', () => {
    render(
      <PageHeader
        title="Planning"
        description="Une description assez longue pour rester entière et apporter le contexte nécessaire."
      />,
    );

    expect(screen.getByText(/Une description assez longue/)).toHaveClass('ui-page-description');
  });
});
