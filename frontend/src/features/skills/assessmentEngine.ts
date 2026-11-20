import type {
  Skill,
  SkillAssessment,
  SkillAssessmentCriterion,
  SkillAssessmentType,
  SkillEvidence,
  SkillLevel,
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

const FAILURE_REGEXES = [
  /\bje\s+ne\s+sais\s+pas\b/i,
  /\baucune\s+id[ée]e\b/i,
  /\br[ée]ponse\s+incorrecte\b/i,
  /\bexercice\s+[ée]chou[ée]\b/i,
  /\bnon\s+r[ée]solu\b/i,
  /\bpas\s+r[ée]ussi\b/i,
  /\bpas\s+encore\s+fait\b/i,
  /\bbrouillon\s+incomplet\b/i,
  /\bincomplet\s*$/i,
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

export function buildDefaultCriteriaLocal(targetLevel: SkillLevel): SkillAssessmentCriterion[] {
  return [
    {
      key: 'relevance',
      label: 'Pertinence par rapport à la compétence',
      description: `La production répond directement à l’objectif du niveau ${targetLevel}/5.`,
      weight: 25,
      maxScore: 25,
      score: 0,
      passed: false,
      feedback: '',
    },
    {
      key: 'technical_accuracy',
      label: 'Correction technique & précision',
      description: 'Exactitude du code, des concepts, des cas limites et de la terminologie.',
      weight: 30,
      maxScore: 30,
      score: 0,
      passed: false,
      feedback: '',
    },
    {
      key: 'reasoning_explanation',
      label: 'Capacité à expliquer le raisonnement',
      description: 'Justification claire des choix techniques, causes, effets ou compromis.',
      weight: 25,
      maxScore: 25,
      score: 0,
      passed: false,
      feedback: '',
    },
    {
      key: 'concrete_evidence',
      label: 'Preuve concrète et admissible',
      description: 'Production vérifiable et preuve recevable rattachées à l’utilisateur.',
      weight: 20,
      maxScore: 20,
      score: 0,
      passed: false,
      feedback: '',
    },
  ];
}

export function buildLocalAssessmentExercise(params: {
  skill: Skill;
  targetLevel: SkillLevel;
  assessmentType: SkillAssessmentType;
  previousGaps?: string[];
  lessonTitle?: string | null;
}): {
  promptTitle: string;
  promptInstructions: string;
  hints: string[];
  criteria: SkillAssessmentCriterion[];
} {
  const { skill, targetLevel, assessmentType, previousGaps = [], lessonTitle } = params;
  const isRemediation = previousGaps.length > 0;
  const prefix = isRemediation ? 'Exercice correctif' : 'Évaluation';
  const promptTitle = `${prefix} — ${skill.name} (niveau ${targetLevel}/5)`.slice(0, 180);

  const difficultyByLevel: Record<number, string> = {
    1: 'Expliquez le concept fondamental avec vos propres mots et donnez un exemple simple et fonctionnel.',
    2: 'Résolvez un exercice guidé en gérant au moins un cas nominal et un cas d’erreur.',
    3: 'Produisez une implémentation autonome complète, expliquez vos choix et documentez les tests effectués.',
    4: 'Analysez un cas complexe, traitez les cas limites/sécurité et justifiez les compromis d’architecture.',
    5: 'Démontrez une maîtrise avancée : conception robuste, optimisation, tests et retour critique documenté.',
  };

  const typeGuidance: Record<SkillAssessmentType, string> = {
    quiz: 'Répondez précisément aux questions de compréhension et justifiez chaque réponse.',
    practical_exercise: 'Fournissez la solution pratique, les étapes suivies et le résultat obtenu.',
    code_review:
      'Fournissez un extrait de code fonctionnel, analysez les erreurs potentielles et expliquez votre correction.',
    explanation: 'Expliquez clairement le mécanisme interne, les cas d’usage et les pièges à éviter.',
    deliverable:
      'Décrivez le livrable produit, son architecture, ses vérifications et les résultats mesurés.',
    mixed: 'Combinez une réponse expliquée, un exemple de code ou cas pratique et une preuve concrète.',
  };

  const scopeNote = skill.description?.trim()
    ? `Périmètre attendu : ${skill.description.trim()}.`
    : `Domaine : ${skill.domain}.`;
  const lessonNote = lessonTitle ? `\nContexte de leçon associé : « ${lessonTitle} ».` : '';
  const gapsNote =
    previousGaps.length > 0
      ? `\nPoints à corriger en priorité suite à l’essai précédent :\n- ${previousGaps.slice(0, 4).join('\n- ')}`
      : '';

  const promptInstructions = [
    `Compétence évaluée : ${skill.name} (niveau actuel vérifié : ${skill.currentLevel}/5 → niveau visé : ${targetLevel}/5).`,
    `${scopeNote}${lessonNote}`,
    `Exigence du palier ${targetLevel}/5 : ${difficultyByLevel[targetLevel] ?? difficultyByLevel[1]}`,
    `Format demandé : ${typeGuidance[assessmentType]}`,
    'Important : associez au moins une preuve concrète et expliquez votre raisonnement (une simple affirmation ou un lien non commenté ne suffit pas).' +
      gapsNote,
  ].join('\n');

  const hints = [
    `Indice 1 — Cadrage : définissez clairement l’entrée, le traitement attendu et le critère de réussite pour « ${skill.name} ».`,
    'Indice 2 — Vérification : identifiez un cas nominal et un cas d’erreur (donnée invalide, borne ou exception) et expliquez comment votre solution y répond.',
    'Indice 3 — Raisonnement & preuve : précisez pourquoi votre approche fonctionne et joignez une preuve décrivant ce qui a été exécuté ou testé.',
  ];

  return {
    promptTitle,
    promptInstructions,
    hints,
    criteria: buildDefaultCriteriaLocal(targetLevel),
  };
}

function checkInsufficientLocal(submissionText: string, submissionCode: string | null): string | null {
  const cleaned = (submissionText ?? '').trim().replace(/\s+/g, ' ');
  const lowered = cleaned.toLowerCase();
  const codeClean = (submissionCode ?? '').trim();

  if (FAILURE_REGEXES.some((rx) => rx.test(lowered))) {
    return 'La soumission exprime explicitement un blocage ou une réponse incorrecte/incomplète.';
  }
  if (SELF_DECLARATIVE_REGEXES.some((rx) => rx.test(lowered)) && cleaned.length < 55 && !codeClean) {
    return 'La réponse se limite à une affirmation sans démonstration ni explication technique.';
  }
  const words = cleaned.split(/\s+/).filter((w) => w.length >= 2);
  if (cleaned.length < 25 || (words.length < 6 && codeClean.length < 15)) {
    return 'La production soumise est trop courte pour évaluer une maîtrise réelle.';
  }
  return null;
}

export function evaluateLocalSubmission(params: {
  skill: Skill;
  assessment: SkillAssessment;
  linkedEvidences: SkillEvidence[];
}): {
  criteria: SkillAssessmentCriterion[];
  score: number;
  passed: boolean;
  proposedLevel: SkillLevel;
  feedback: string;
  masteredPoints: string[];
  gapsIdentified: string[];
  remediationRecommendation: string | null;
  externalVerificationWarning: string | null;
} {
  const { skill, assessment, linkedEvidences } = params;
  const submissionText = (assessment.submissionText ?? '').trim().replace(/\s+/g, ' ');
  const loweredText = submissionText.toLowerCase();
  const codeClean = (assessment.submissionCode ?? '').trim();
  const combinedLower = `${loweredText}\n${codeClean.toLowerCase()}`;
  const words = submissionText.split(/\s+/).filter((w) => w.length >= 2);

  const admissibleEvidences = linkedEvidences.filter(
    (ev) => validateEvidenceQualityLocal(ev.description, ev.referenceUrl, ev.result).admissible,
  );
  const hasExternalUrl =
    Boolean(assessment.submissionReferenceUrl) ||
    linkedEvidences.some((ev) => Boolean(ev.referenceUrl));

  const insufficientReason = checkInsufficientLocal(submissionText, codeClean);
  const skillTokens = `${skill.name} ${skill.domain}`
    .toLowerCase()
    .split(/[^a-zA-ZÀ-ÿ0-9_+#-]+/)
    .filter((t) => t.length >= 3);
  const hasTopicOverlap =
    skillTokens.some((tok) => combinedLower.includes(tok)) ||
    CONCRETE_KEYWORDS.some((kw) => combinedLower.includes(kw));
  const hasReasoningMarkers = [
    'car ',
    'parce que',
    'donc ',
    'afin de',
    'permet de',
    'évite',
    'cas ',
    'erreur',
    'exception',
    'avantage',
    'limite',
    'complexité',
    'test',
    'étape',
  ].some((m) => loweredText.includes(m));
  const hasCodeConstruct =
    codeClean.length >= 20 ||
    ['def ', 'class ', 'return', '=>', 'SELECT ', 'async ', '{', '('].some((t) =>
      codeClean.includes(t),
    );

  const baseCriteria =
    assessment.criteria.length > 0
      ? assessment.criteria
      : buildDefaultCriteriaLocal(assessment.targetLevel);

  const masteredPoints: string[] = [];
  const gapsIdentified: string[] = [];

  const criteria: SkillAssessmentCriterion[] = baseCriteria.map((crit) => {
    const maxScore = crit.maxScore || crit.weight || 25;
    let score = 0;
    let passed = false;
    let feedback = '';

    if (crit.key === 'concrete_evidence') {
      if (admissibleEvidences.length === 0) {
        score = 0;
        passed = false;
        feedback = 'Aucune preuve concrète et admissible liée à cette évaluation.';
      } else {
        score = maxScore;
        passed = true;
        feedback = `${admissibleEvidences.length} preuve(s) concrète(s) vérifiée(s) sur votre compte.`;
      }
    } else if (insufficientReason) {
      score = crit.key === 'relevance' && hasTopicOverlap ? Math.min(5, Math.floor(maxScore / 4)) : 0;
      passed = false;
      feedback = insufficientReason;
    } else if (crit.key === 'relevance') {
      if (submissionText.length >= 40 && hasTopicOverlap) {
        score = maxScore;
        passed = true;
        feedback = `Production alignée avec la compétence « ${skill.name} ».`;
      } else if (submissionText.length >= 35) {
        score = Math.round(maxScore * 0.68);
        passed = true;
        feedback = 'Réponse globalement pertinente mais lien explicite à renforcer.';
      } else {
        score = Math.round(maxScore * 0.35);
        passed = false;
        feedback = 'Réponse trop générique par rapport à la compétence ciblée.';
      }
    } else if (crit.key === 'technical_accuracy') {
      if (
        assessment.assessmentType === 'practical_exercise' ||
        assessment.assessmentType === 'code_review'
      ) {
        if (hasCodeConstruct && (hasReasoningMarkers || words.length >= 10)) {
          score = maxScore;
          passed = true;
          feedback = 'Code et éléments techniques cohérents avec le niveau visé.';
        } else if (hasTopicOverlap && words.length >= 12 && hasReasoningMarkers) {
          score = Math.round(maxScore * 0.8);
          passed = true;
          feedback = 'Raisonnement technique solide.';
        } else {
          score = words.length >= 8 ? Math.round(maxScore * 0.4) : Math.round(maxScore * 0.2);
          passed = false;
          feedback = 'Éléments techniques ou extrait de code insuffisants pour démontrer la correction.';
        }
      } else if (hasTopicOverlap && words.length >= 12) {
        score = hasCodeConstruct || words.length >= 18 ? maxScore : Math.round(maxScore * 0.85);
        passed = true;
        feedback = 'Contenu techniquement exact et structuré.';
      } else {
        score = Math.round(maxScore * 0.4);
        passed = false;
        feedback = 'Manque de précision technique dans la réponse.';
      }
    } else {
      if (words.length >= 12 && hasReasoningMarkers) {
        score = words.length >= 18 ? maxScore : Math.round(maxScore * 0.84);
        passed = true;
        feedback = 'Explication claire du raisonnement et des cas traités.';
      } else if (words.length >= 10) {
        score = Math.round(maxScore * 0.68);
        passed = true;
        feedback = 'Explication recevable ; justifiez davantage le pourquoi et les cas limites.';
      } else {
        score = Math.round(maxScore * 0.3);
        passed = false;
        feedback = 'Raisonnement non détaillé : expliquez comment vous obtenez ce résultat.';
      }
    }

    if (passed) {
      masteredPoints.push(`${crit.label} (${score}/${maxScore})`);
    } else {
      gapsIdentified.push(`${crit.label} : ${feedback}`);
    }

    return {
      ...crit,
      maxScore,
      score,
      passed,
      feedback,
    };
  });

  const rawTotal = criteria.reduce((acc, c) => acc + c.score, 0);
  const rawMax = criteria.reduce((acc, c) => acc + c.maxScore, 0) || 100;
  const score = Math.max(0, Math.min(100, Math.round((rawTotal / rawMax) * 100)));

  const evidenceOk = criteria.some((c) => c.key === 'concrete_evidence' && c.passed);
  const techOk = criteria.some((c) => c.key === 'technical_accuracy' && c.passed);
  const passedCount = criteria.filter((c) => c.passed).length;
  const threshold = passThresholdForLevel(assessment.targetLevel);

  const passed =
    !insufficientReason && evidenceOk && techOk && passedCount >= 3 && score >= threshold;

  let proposedLevel: SkillLevel = skill.currentLevel;
  if (passed) {
    if (score >= 85 || assessment.targetLevel <= skill.currentLevel + 1) {
      proposedLevel = assessment.targetLevel;
    } else {
      proposedLevel = Math.min(assessment.targetLevel, skill.currentLevel + 1) as SkillLevel;
    }
  }

  let remediationRecommendation: string | null = null;
  if (!passed) {
    remediationRecommendation = !evidenceOk
      ? 'Associez une preuve concrète décrivant votre exercice, code ou test exécuté, puis relancez un exercice correctif.'
      : `Réalisez un exercice correctif ciblé sur « ${skill.name} » en détaillant le raisonnement, un cas d’erreur et en joignant le code/résultat vérifié.`;
  }

  const externalVerificationWarning = hasExternalUrl ? EXTERNAL_URL_DISCLAIMER : null;
  const verdict = passed
    ? `Évaluation réussie (${score}/100, seuil ${threshold}/100). Niveau proposé : ${proposedLevel}/5.`
    : `Évaluation non validée (${score}/100, seuil requis ${threshold}/100). Le niveau reste à ${skill.currentLevel}/5.`;
  const details = criteria.map((c) => `${c.label} : ${c.score}/${c.maxScore}`).join(' · ');
  const feedback = externalVerificationWarning
    ? `${verdict}\nDétail : ${details}.\nNote : ${externalVerificationWarning}`
    : `${verdict}\nDétail : ${details}.`;

  return {
    criteria,
    score,
    passed,
    proposedLevel,
    feedback,
    masteredPoints,
    gapsIdentified,
    remediationRecommendation,
    externalVerificationWarning,
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
