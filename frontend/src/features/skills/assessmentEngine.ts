import type {
  Skill,
  SkillAssessment,
  SkillPedagogicalState,
} from '../../types/domain';

export const EXTERNAL_URL_DISCLAIMER =
  'Référence externe non inspectée automatiquement par le serveur : la validation repose uniquement sur la production, les justifications et les résultats soumis.';

const SELF_DECLARATIVE_REGEXES = [
  /\bj['’]?ai\s+(bien\s+)?compris\b/i,
  /\bje\s+ma[îi]trise\b/i,
  /\bje\s+connais\b/i,
  /\bc['’]?est\s+(bon|fait|acquis|ok|compris)\b/i,
  /\bj['’]?ai\s+(lu|vu|regard[ée]|termin[ée]|fini)\b/i,
  /\bje\s+sais\s+faire\b/i,
  /\ble[çc]on\s+termin[ée]e?\b/i,
];

const CONCRETE_KEYWORDS = [
  'def ',
  'class ',
  'function',
  'return ',
  'select ',
  'create ',
  'async ',
  'import ',
  'pytest',
  'vitest',
  'test',
  'exercice',
  'script',
  'fonction',
  'requête',
  'endpoint',
  'route',
  'algorithme',
  'correction',
  'refactor',
  'module',
  'composant',
  'résultat',
  'score',
  'erreur',
  'exception',
  'validation',
  'benchmark',
  'livrable',
  'code',
];

export interface EvidenceQualityCheck {
  admissible: boolean;
  reason: string | null;
  externalReferenceVerified: boolean;
  verificationNote: string | null;
}

export function passThresholdForLevel(targetLevel: number): number {
  return targetLevel >= 4 ? 75 : 70;
}

export function validateEvidenceQualityLocal(
  description: string,
  referenceUrl?: string | null,
  result?: string | null,
): EvidenceQualityCheck {
  const cleaned = (description ?? '').trim().replace(/\s+/g, ' ');
  const lowered = cleaned.toLowerCase();
  const words = cleaned.split(/\s+/).filter((w) => w.length >= 2);
  const hasUrl = Boolean(referenceUrl && referenceUrl.trim());
  const verificationNote = hasUrl ? EXTERNAL_URL_DISCLAIMER : null;

  if (cleaned.length < 12 || words.length < 3) {
    return {
      admissible: false,
      reason:
        'Preuve refusée : décrivez précisément la production réalisée (au moins 12 caractères et 3 mots concrets, ex. exercice résolu, code écrit, résultat).',
      externalReferenceVerified: false,
      verificationNote,
    };
  }

  const isDeclarative = SELF_DECLARATIVE_REGEXES.some((rx) => rx.test(lowered));
  const hasConcreteKw = CONCRETE_KEYWORDS.some((kw) => lowered.includes(kw));
  const hasConcreteResult = Boolean(result && result.trim().length >= 4);

  if (isDeclarative && !hasConcreteKw && !hasConcreteResult) {
    return {
      admissible: false,
      reason:
        'Preuve insuffisante : une simple affirmation (« j’ai compris », « leçon terminée ») ne démontre pas la compétence. Décrivez l’exercice, le code ou le résultat obtenu.',
      externalReferenceVerified: false,
      verificationNote,
    };
  }

  if (isDeclarative && cleaned.length < 40 && !hasConcreteResult) {
    return {
      admissible: false,
      reason:
        'Preuve trop vague : détaillez ce qui a été produit, testé ou corrigé ainsi que le résultat observé.',
      externalReferenceVerified: false,
      verificationNote,
    };
  }

  return {
    admissible: true,
    reason: null,
    externalReferenceVerified: false,
    verificationNote,
  };
}

export function deriveSkillPedagogicalState(
  skill: Skill,
  skillAssessments: SkillAssessment[],
  evidenceCount: number,
  sessionsCount: number,
): SkillPedagogicalState {
  const sorted = [...skillAssessments].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
  const latest = sorted[0];

  if (
    latest &&
    (latest.status === 'pending' || latest.status === 'submitted' || latest.status === 'evaluated')
  ) {
    return 'awaiting_assessment';
  }

  if (
    (latest && (latest.status === 'rejected' || latest.passed === false)) ||
    (skill.currentLevel >= 3 && evidenceCount === 0)
  ) {
    return 'needs_reinforcement';
  }

  if (skill.currentLevel > 0 && (sorted.some((a) => a.status === 'approved') || evidenceCount > 0)) {
    return 'validated';
  }

  if (evidenceCount > 0 || sessionsCount > 0 || sorted.length > 0) {
    return 'learning';
  }

  return 'not_evaluated';
}

export function getRecommendedNextAction(
  skill: Skill,
  state: SkillPedagogicalState,
  skillAssessments: SkillAssessment[],
  evidenceCount: number,
): string {
  const sorted = [...skillAssessments].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
  const latest = sorted[0];
  const nextLvl = Math.min(5, Math.max(1, skill.currentLevel + 1));

  if (state === 'awaiting_assessment' && latest) {
    if (latest.status === 'pending') {
      return `Soumettre votre production et une preuve concrète pour l’évaluation « ${latest.promptTitle} ».`;
    }
    if (latest.status === 'submitted') {
      return 'Lancer la correction de votre soumission selon les critères pédagogiques.';
    }
    if (latest.status === 'evaluated') {
      return latest.passed
        ? `Valider la décision finale pour passer au niveau ${latest.proposedLevel ?? nextLvl}/5.`
        : 'Consulter les lacunes identifiées et lancer un exercice correctif.';
    }
  }

  if (state === 'needs_reinforcement') {
    if (skill.currentLevel >= 3 && evidenceCount === 0) {
      return 'Ajouter une preuve concrète ou lancer une évaluation pour justifier ce niveau historique.';
    }
    if (latest?.remediationRecommendation) {
      return latest.remediationRecommendation;
    }
    return `Réviser les lacunes identifiées puis relancer un exercice correctif vers le niveau ${nextLvl}/5.`;
  }

  if (state === 'validated') {
    if (skill.targetLevel && skill.currentLevel < skill.targetLevel) {
      return `Préparer l’évaluation du palier suivant (${nextLvl}/5) vers votre cible (${skill.targetLevel}/5).`;
    }
    if (skill.currentLevel < 5) {
      return `Consolider par la pratique ou viser le niveau ${nextLvl}/5 via une nouvelle évaluation.`;
    }
    return 'Maîtrise 5/5 validée : maintenir par des projets complexes et revues de code.';
  }

  if (state === 'learning') {
    return `Évaluer cette compétence pour valider le passage au niveau ${nextLvl}/5 avec vos preuves.`;
  }

  return `Lancer une première évaluation pratique pour débloquer le niveau 1/5 (verrouillé à 0 tant que non évalué).`;
}
