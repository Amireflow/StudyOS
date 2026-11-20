from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.ai.context_builder import BoundedUserContext
from app.ai.prompt_manager import PromptManager
from app.ai.provider import ProviderResult
from app.schemas.ai import RawProposalCandidate


def test_skill_creation_locked_at_zero_and_direct_level_update_forbidden(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    # 1. Refus de création directe avec un niveau > 0 (422 SKILL_INITIAL_LEVEL_LOCKED)
    attempt_lvl2 = client.post(
        "/api/v1/skills",
        json={"name": "Python", "domain": "Backend", "current_level": 2, "target_level": 4},
        headers=user_a_headers,
    )
    assert attempt_lvl2.status_code == 422
    assert attempt_lvl2.json()["error"]["code"] == "SKILL_INITIAL_LEVEL_LOCKED"

    # 2. Création au niveau 0 réussie
    created = client.post(
        "/api/v1/skills",
        json={
            "name": "Python",
            "domain": "Backend",
            "description": "Structures de données, fonctions typées et tests Pytest",
            "target_level": 4,
        },
        headers=user_a_headers,
    )
    assert created.status_code == 201
    skill = created.json()
    skill_id = skill["id"]
    assert skill["current_level"] == 0
    assert skill["last_assessed_at"] is None
    assert skill["target_level"] == 4

    # 3. Modification ordinaire (nom, domaine, description, target_level) autorisée
    ordinary_patch = client.patch(
        f"/api/v1/skills/{skill_id}",
        json={"name": "Python 3.12", "target_level": 5},
        headers=user_a_headers,
    )
    assert ordinary_patch.status_code == 200
    assert ordinary_patch.json()["name"] == "Python 3.12"
    assert ordinary_patch.json()["target_level"] == 5
    assert ordinary_patch.json()["current_level"] == 0

    # 4. Refus de modification directe de current_level par PATCH (403 SKILL_ASSESSMENT_REQUIRED)
    direct_patch = client.patch(
        f"/api/v1/skills/{skill_id}",
        json={"current_level": 3},
        headers=user_a_headers,
    )
    assert direct_patch.status_code == 403
    assert direct_patch.json()["error"]["code"] == "SKILL_ASSESSMENT_REQUIRED"

    # Même une tentative avec current_level=0 ou null sur PATCH est bloquée
    zero_patch = client.patch(
        f"/api/v1/skills/{skill_id}",
        json={"current_level": 0},
        headers=user_a_headers,
    )
    assert zero_patch.status_code == 403
    assert zero_patch.json()["error"]["code"] == "SKILL_ASSESSMENT_REQUIRED"

    null_patch = client.patch(
        f"/api/v1/skills/{skill_id}",
        json={"current_level": None},
        headers=user_a_headers,
    )
    assert null_patch.status_code == 403
    assert null_patch.json()["error"]["code"] == "SKILL_ASSESSMENT_REQUIRED"

    assert client.get(f"/api/v1/skills/{skill_id}", headers=user_a_headers).json()["current_level"] == 0


def test_evidence_quality_enforcement_and_external_url_transparency(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    skill_id = client.post(
        "/api/v1/skills",
        json={"name": "PostgreSQL", "domain": "Base de données"},
        headers=user_a_headers,
    ).json()["id"]

    # Une simple auto-déclaration comme « j'ai compris Python » est rejetée (422)
    vague_ev = client.post(
        f"/api/v1/skills/{skill_id}/evidence",
        json={"type": "exercise", "description": "J'ai compris Python"},
        headers=user_a_headers,
    )
    assert vague_ev.status_code == 422
    assert vague_ev.json()["error"]["code"] == "EVIDENCE_QUALITY_INSUFFICIENT"

    too_short_ev = client.post(
        f"/api/v1/skills/{skill_id}/evidence",
        json={"type": "code", "description": "Fait ok"},
        headers=user_a_headers,
    )
    assert too_short_ev.status_code == 422

    # Une preuve concrète avec URL externe est acceptée MAIS déclare honnêtement que l'URL n'a pas été inspectée
    valid_ev = client.post(
        f"/api/v1/skills/{skill_id}/evidence",
        json={
            "type": "code",
            "description": "Écriture de 4 requêtes SQL avec index composite et plan EXPLAIN ANALYZE",
            "reference_url": "https://github.com/amireflow/study-os/pull/12",
            "result": "Temps d'exécution réduit de 45ms à 2ms",
        },
        headers=user_a_headers,
    )
    assert valid_ev.status_code == 201
    ev_data = valid_ev.json()
    assert ev_data["is_admissible"] is True
    assert ev_data["external_reference_verified"] is False
    assert "non inspectée automatiquement" in (ev_data["verification_note"] or "")


def test_pedagogical_scenario_12_steps_python_progression_and_history(
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    """Scénario pédagogique complet en 12 étapes (Section 10)."""
    # 1. Créer une compétence Python au niveau 0
    skill_res = client.post(
        "/api/v1/skills",
        json={
            "name": "Programmation Python",
            "domain": "Backend",
            "description": "Fonctions pures, gestion des exceptions et tests unitaires Pytest",
            "target_level": 3,
        },
        headers=user_a_headers,
    )
    assert skill_res.status_code == 201
    skill_id = skill_res.json()["id"]
    assert skill_res.json()["current_level"] == 0

    # 2. Demander une évaluation
    a1_res = client.post(
        f"/api/v1/skills/{skill_id}/assessments",
        json={"target_level": 1, "assessment_type": "practical_exercise"},
        headers=user_a_headers,
    )
    assert a1_res.status_code == 201
    a1 = a1_res.json()
    a1_id = a1["id"]
    assert a1["status"] == "pending"
    assert a1["starting_level"] == 0
    assert a1["target_level"] == 1
    assert a1["revealed_hints"] == []
    assert a1["hints_total"] == 3

    # 3. Recevoir l'exercice et demander un indice progressif
    assert "Programmation Python" in a1["prompt_instructions"]
    assert len(a1["criteria"]) == 4
    hint_res = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a1_id}/hint",
        headers=user_a_headers,
    )
    assert hint_res.status_code == 200
    assert len(hint_res.json()["revealed_hints"]) == 1

    # 4. Soumettre une réponse incorrecte / insuffisante sans preuve
    sub1 = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a1_id}/submit",
        json={
            "submission_text": "Je ne sais pas comment gérer le cas d'erreur, réponse incorrecte pour l'instant.",
        },
        headers=user_a_headers,
    )
    assert sub1.status_code == 200
    assert sub1.json()["status"] == "submitted"

    # 5. Recevoir un retour pédagogique (évaluation défavorable)
    eval1 = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a1_id}/evaluate",
        headers=user_a_headers,
    )
    assert eval1.status_code == 200
    eval1_data = eval1.json()
    assert eval1_data["status"] == "evaluated"
    assert eval1_data["passed"] is False
    assert eval1_data["proposed_level"] == 0
    assert len(eval1_data["gaps_identified"]) >= 2
    assert eval1_data["remediation_recommendation"] is not None

    # 6. Constater que la compétence reste au niveau 0 et que toute tentative de forcer la validation échoue
    forced_val = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a1_id}/validate",
        headers=user_a_headers,
    )
    assert forced_val.status_code == 422
    assert forced_val.json()["error"]["code"] == "ASSESSMENT_RESULT_INSUFFICIENT"

    rej1 = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a1_id}/reject",
        json={"reason": "Lacunes identifiées, passage à un exercice correctif."},
        headers=user_a_headers,
    )
    assert rej1.status_code == 200
    assert rej1.json()["status"] == "rejected"
    assert client.get(f"/api/v1/skills/{skill_id}", headers=user_a_headers).json()["current_level"] == 0

    # 7. Effectuer un exercice correctif (reprend automatiquement les lacunes de l'essai précédent)
    a2_res = client.post(
        f"/api/v1/skills/{skill_id}/assessments",
        json={"target_level": 1, "assessment_type": "practical_exercise"},
        headers=user_a_headers,
    )
    assert a2_res.status_code == 201
    a2 = a2_res.json()
    a2_id = a2["id"]
    assert "Exercice correctif" in a2["prompt_title"]
    assert "Points à corriger en priorité" in a2["prompt_instructions"]

    # 8. Soumettre une production valide accompagnée d'une preuve concrète
    sub2 = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a2_id}/submit",
        json={
            "submission_text": (
                "J'ai implémenté une fonction pure parse_positive_int(raw: str) -> int en Python "
                "parce que cela isole la validation des entrées. Le cas nominal convertit la chaîne "
                "et le cas d'erreur lève ValueError lorsque la valeur est négative ou non numérique, "
                "ce qui évite la propagation d'états invalides dans le module."
            ),
            "submission_code": (
                "def parse_positive_int(raw: str) -> int:\n"
                "    value = int(raw.strip())\n"
                "    if value <= 0:\n"
                "        raise ValueError('Entier strictement positif requis')\n"
                "    return value\n"
            ),
            "submission_reference_url": "https://github.com/amireflow/study-os",
            "new_evidence": {
                "type": "exercise",
                "description": "Exercice Python sur parse_positive_int avec 4 tests Pytest couvrant cas nominal et ValueError",
                "result": "4 passed in 0.03s",
            },
        },
        headers=user_a_headers,
    )
    assert sub2.status_code == 200
    sub2_data = sub2.json()
    assert sub2_data["status"] == "submitted"
    assert len(sub2_data["evidence_ids"]) == 1
    assert sub2_data["external_verification_warning"] is not None

    # 9. Obtenir une évaluation favorable
    eval2 = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a2_id}/evaluate",
        headers=user_a_headers,
    )
    assert eval2.status_code == 200
    eval2_data = eval2.json()
    assert eval2_data["status"] == "evaluated"
    assert eval2_data["passed"] is True
    assert eval2_data["score"] >= 70
    assert eval2_data["proposed_level"] == 1
    assert len(eval2_data["mastered_points"]) >= 3

    # Tant que l'utilisateur n'a pas validé la décision finale, le niveau officiel est toujours 0
    assert client.get(f"/api/v1/skills/{skill_id}", headers=user_a_headers).json()["current_level"] == 0

    # 10. Valider le résultat
    val2 = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a2_id}/validate",
        json={"reason": "Tous les critères du palier 1 sont remplis avec preuve Pytest."},
        headers=user_a_headers,
    )
    assert val2.status_code == 200
    val2_data = val2.json()
    assert val2_data["status"] == "approved"
    assert val2_data["applied_level_delta"] == 1
    assert val2_data["validated_at"] is not None

    # 11. Vérifier que le niveau augmente conformément au résultat
    skill_after = client.get(f"/api/v1/skills/{skill_id}", headers=user_a_headers).json()
    assert skill_after["current_level"] == 1
    assert skill_after["last_assessed_at"] is not None

    # Impossible de réutiliser la même évaluation pour augmenter une seconde fois le niveau (409)
    replay = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{a2_id}/validate",
        headers=user_a_headers,
    )
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "ASSESSMENT_ALREADY_APPROVED"
    assert client.get(f"/api/v1/skills/{skill_id}", headers=user_a_headers).json()["current_level"] == 1

    # 12. Vérifier que les évaluations (échouée + validée) et la preuve restent consultables dans l'historique
    history = client.get(f"/api/v1/skills/{skill_id}/assessments", headers=user_a_headers).json()
    assert len(history) == 2
    assert {item["status"] for item in history} == {"rejected", "approved"}
    evidences = client.get(f"/api/v1/skills/{skill_id}/evidence", headers=user_a_headers).json()
    assert len(evidences) == 1


def test_assessment_security_ownership_cross_skill_and_missing_evidence_guards(
    client: TestClient,
    user_a_headers: dict[str, str],
    user_b_headers: dict[str, str],
) -> None:
    # Compétences A1, A2 (User A) et B1 (User B)
    skill_a1 = client.post(
        "/api/v1/skills",
        json={"name": "FastAPI", "domain": "Backend"},
        headers=user_a_headers,
    ).json()["id"]
    skill_a2 = client.post(
        "/api/v1/skills",
        json={"name": "React", "domain": "Frontend"},
        headers=user_a_headers,
    ).json()["id"]
    skill_b1 = client.post(
        "/api/v1/skills",
        json={"name": "Docker", "domain": "DevOps"},
        headers=user_b_headers,
    ).json()["id"]

    # Preuve appartenant à A2 et preuve appartenant à User B
    ev_a2 = client.post(
        f"/api/v1/skills/{skill_a2}/evidence",
        json={
            "type": "code",
            "description": "Composant React avec hooks et tests Vitest complets",
            "result": "Tests OK",
        },
        headers=user_a_headers,
    ).json()["id"]
    ev_b1 = client.post(
        f"/api/v1/skills/{skill_b1}/evidence",
        json={
            "type": "deliverable",
            "description": "Image Docker multi-stage durcie avec utilisateur non-root",
            "result": "Image 65MB",
        },
        headers=user_b_headers,
    ).json()["id"]

    assessment_a1 = client.post(
        f"/api/v1/skills/{skill_a1}/assessments",
        json={"target_level": 1},
        headers=user_a_headers,
    ).json()["id"]

    # 1. Refus d'une preuve appartenant à un autre utilisateur (404 EVIDENCE_NOT_FOUND)
    cross_user_ev = client.post(
        f"/api/v1/skills/{skill_a1}/assessments/{assessment_a1}/submit",
        json={
            "submission_text": "Explication complète sur les routeurs FastAPI et l'injection Depends.",
            "evidence_ids": [ev_b1],
        },
        headers=user_a_headers,
    )
    assert cross_user_ev.status_code == 404
    assert cross_user_ev.json()["error"]["code"] == "EVIDENCE_NOT_FOUND"

    # 2. Refus d'une preuve associée à une autre compétence du même utilisateur (422 EVIDENCE_SKILL_MISMATCH)
    cross_skill_ev = client.post(
        f"/api/v1/skills/{skill_a1}/assessments/{assessment_a1}/submit",
        json={
            "submission_text": "Explication complète sur les routeurs FastAPI et l'injection Depends.",
            "evidence_ids": [ev_a2],
        },
        headers=user_a_headers,
    )
    assert cross_skill_ev.status_code == 422
    assert cross_skill_ev.json()["error"]["code"] == "EVIDENCE_SKILL_MISMATCH"

    # 3. Refus d'utiliser l'évaluation de A1 sur la route de A2 (404)
    wrong_skill_route = client.get(
        f"/api/v1/skills/{skill_a2}/assessments/{assessment_a1}",
        headers=user_a_headers,
    )
    assert wrong_skill_route.status_code == 404

    # 4. Isolation stricte vis-à-vis de User B sur toutes les opérations d'évaluation
    assert client.get("/api/v1/skills/assessments", headers=user_b_headers).json() == []
    assert (
        client.get(
            f"/api/v1/skills/{skill_a1}/assessments/{assessment_a1}",
            headers=user_b_headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/skills/{skill_a1}/assessments",
            json={"target_level": 1},
            headers=user_b_headers,
        ).status_code
        == 404
    )

    # 5. Soumission sans aucune preuve -> l'évaluation échoue sur le critère concrete_evidence et refuse la validation
    sub_no_ev = client.post(
        f"/api/v1/skills/{skill_a1}/assessments/{assessment_a1}/submit",
        json={
            "submission_text": (
                "Dans FastAPI, Depends permet d'injecter une session SQLAlchemy par requête "
                "parce que le générateur ferme proprement la transaction dans le bloc finally "
                "et gère les cas d'erreur HTTP."
            ),
            "submission_code": "def get_db():\n    db = Session()\n    try:\n        yield db\n    finally:\n        db.close()",
        },
        headers=user_a_headers,
    )
    assert sub_no_ev.status_code == 200
    eval_no_ev = client.post(
        f"/api/v1/skills/{skill_a1}/assessments/{assessment_a1}/evaluate",
        headers=user_a_headers,
    ).json()
    assert eval_no_ev["passed"] is False
    assert eval_no_ev["proposed_level"] == 0
    val_no_ev = client.post(
        f"/api/v1/skills/{skill_a1}/assessments/{assessment_a1}/validate",
        headers=user_a_headers,
    )
    assert val_no_ev.status_code == 422


def test_ai_copilot_pedagogical_lock_and_revalidation_on_accept(
    app: FastAPI,
    client: TestClient,
    user_a_headers: dict[str, str],
) -> None:
    skill_id = client.post(
        "/api/v1/skills",
        json={"name": "SQLAlchemy 2", "domain": "Backend", "target_level": 3},
        headers=user_a_headers,
    ).json()["id"]

    conv_id = client.post("/api/v1/ai/conversations", json={}, headers=user_a_headers).json()["id"]

    # 1. Demander au Copilote d'évaluer la compétence -> génère propose_skill_assessment (pas de mutation directe)
    turn1 = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Je veux évaluer ma compétence SQLAlchemy 2 pour passer un niveau"},
        headers=user_a_headers,
    )
    assert turn1.status_code == 201
    props1 = turn1.json()["proposals"]
    assert len(props1) == 1
    assert props1[0]["action_type"] == "propose_skill_assessment"

    # Accepter propose_skill_assessment crée une évaluation pending mais laisse current_level à 0
    acc1 = client.post(
        f"/api/v1/ai/proposals/{props1[0]['id']}/accept",
        headers=user_a_headers,
    )
    assert acc1.status_code == 200
    assessment_id = acc1.json()["execution_result"]["assessment_id"]
    assert client.get(f"/api/v1/skills/{skill_id}", headers=user_a_headers).json()["current_level"] == 0

    # 2. Un provider malveillant qui tente update_skill_level ou une preuve fabriquée est rejeté par ActionValidator
    class BypassAttemptProvider:
        def generate_response(
            self,
            *,
            user_message: str,
            history: list[dict[str, str]],
            context: BoundedUserContext,
            prompt_manager: PromptManager,
        ) -> ProviderResult:
            _ = (user_message, history, context, prompt_manager)
            return ProviderResult(
                reply="Tentative de contournement.",
                proposals=[
                    RawProposalCandidate(
                        action_type="update_skill_level",
                        title="Monter directement au niveau 5",
                        explanation="Contournement direct interdit",
                        payload={"skill_id": skill_id, "current_level": 5},
                    ),
                    RawProposalCandidate(
                        action_type="add_skill_evidence",
                        title="Preuve fabriquée",
                        explanation="Auto-déclaration",
                        payload={
                            "skill_id": skill_id,
                            "type": "exercise",
                            "description": "J'ai compris SQLAlchemy",
                        },
                    ),
                    RawProposalCandidate(
                        action_type="recommend_skill_progression",
                        title="Valider une évaluation non soumise",
                        explanation="Évaluation encore pending",
                        payload={
                            "skill_id": skill_id,
                            "assessment_id": assessment_id,
                            "proposed_level": 1,
                        },
                    ),
                ],
                is_estimate=False,
                missing_data=[],
                provider_name="mock",
                model_name="mock-v1",
            )

    app.state.ai_provider = BypassAttemptProvider()
    try:
        turn_bypass = client.post(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            json={"content": "Test de contournement"},
            headers=user_a_headers,
        )
        assert turn_bypass.status_code == 201
        assert turn_bypass.json()["proposals"] == []
        assert turn_bypass.json()["assistant_message"]["metadata"]["rejected_proposals_count"] == 3
    finally:
        app.state.ai_provider = None

    # 3. Soumettre et évaluer favorablement l'évaluation, puis tester la revalidation à l'acceptation d'une proposition IA
    sub = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{assessment_id}/submit",
        json={
            "submission_text": (
                "En SQLAlchemy 2, select() remplace Query parce qu'il unifie Core et ORM, "
                "et scalars().all() extrait les entités typées en gérant proprement les erreurs."
            ),
            "submission_code": "stmt = select(SkillTable).where(SkillTable.user_id == uid)\nrows = db.scalars(stmt).all()",
            "new_evidence": {
                "type": "code",
                "description": "Repository SQLAlchemy 2 complet avec filtres user_id et tests Pytest",
                "result": "Tests repository 100% OK",
            },
        },
        headers=user_a_headers,
    ).json()
    ev_id = sub["evidence_ids"][0]

    evaluated = client.post(
        f"/api/v1/skills/{skill_id}/assessments/{assessment_id}/evaluate",
        headers=user_a_headers,
    ).json()
    assert evaluated["passed"] is True

    # Le Copilote peut maintenant recommander la validation de cette évaluation évaluée
    turn_rec = client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        json={"content": "Peux-tu valider mon niveau sur cette compétence évaluée ?"},
        headers=user_a_headers,
    )
    assert turn_rec.status_code == 201
    rec_props = turn_rec.json()["proposals"]
    assert len(rec_props) == 1
    rec_prop_id = rec_props[0]["id"]
    assert rec_props[0]["action_type"] == "recommend_skill_progression"

    # Si la preuve est supprimée AVANT l'acceptation de la proposition IA, la revalidation bloque l'exécution !
    del_ev = client.delete(
        f"/api/v1/skills/{skill_id}/evidence/{ev_id}",
        headers=user_a_headers,
    )
    assert del_ev.status_code == 204

    failed_accept = client.post(
        f"/api/v1/ai/proposals/{rec_prop_id}/accept",
        headers=user_a_headers,
    )
    assert failed_accept.status_code == 404
    assert client.get(f"/api/v1/skills/{skill_id}", headers=user_a_headers).json()["current_level"] == 0
