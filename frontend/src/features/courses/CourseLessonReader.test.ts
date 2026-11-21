import { describe, expect, it } from 'vitest';
import { splitLessonIntoSteps } from './CourseLessonReader';

describe('splitLessonIntoSteps', () => {
  it('separates lesson sections and keeps introductory text with the first step', () => {
    const steps = splitLessonIntoSteps(
      [
        'Objectif général du chapitre.',
        '',
        '## 1. Variables',
        'Une variable stocke une valeur.',
        '',
        '## Fonctions',
        'Une fonction regroupe des instructions.',
      ].join('\n'),
      'Leçon',
    );

    expect(steps).toHaveLength(2);
    expect(steps[0].title).toBe('Variables');
    expect(steps[0].markdown).toContain('Objectif général du chapitre.');
    expect(steps[1].title).toBe('Fonctions');
  });

  it('does not split headings that are inside fenced code blocks', () => {
    const steps = splitLessonIntoSteps(
      ['## Exemple', '```ts', '## Ceci est un commentaire de code', '```', 'Fin.'].join('\n'),
      'Leçon',
    );

    expect(steps).toHaveLength(1);
    expect(steps[0].markdown).toContain('## Ceci est un commentaire de code');
  });

  it('returns one step when the lesson has no second-level headings', () => {
    const steps = splitLessonIntoSteps('Un chapitre simple.', 'Introduction');

    expect(steps).toEqual([{ title: 'Introduction', markdown: 'Un chapitre simple.' }]);
  });
});
