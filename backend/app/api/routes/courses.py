from uuid import UUID
from fastapi import APIRouter, Depends, Response, status
from app.api.deps import get_course_service
from app.core.security import get_current_user_id
from app.schemas.courses import (
    CourseCreate,
    CourseDetailResponse,
    CourseLessonProgressUpdate,
    CourseLessonResponse,
    CourseLessonTutorAskRequest,
    CourseLessonTutorAskResponse,
    CourseLevelRegenerateRequest,
    CoursePreviewRequest,
    CoursePreviewResponse,
    CourseResourceCreate,
    CourseResourceResponse,
    CourseSubmissionCreate,
    CourseSubmissionResponse,
    CourseSummaryResponse,
    CourseUpdate,
)
from app.services.courses_service import CourseService

router = APIRouter(prefix="/courses", tags=["Cours"])


@router.get(
    "",
    response_model=list[CourseSummaryResponse],
    summary="Lister les cours de l'utilisateur",
)
def list_courses(
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> list[CourseSummaryResponse]:
    return course_service.list_courses(user_id)


@router.post(
    "/preview",
    response_model=CoursePreviewResponse,
    summary="Prévisualiser un plan de cours complet et le niveau 1 sans écriture en base",
)
def preview_course(
    payload: CoursePreviewRequest,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CoursePreviewResponse:
    return course_service.preview_course(payload, user_id=user_id)


@router.post(
    "",
    response_model=CourseDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un cours complet démarrant obligatoirement au niveau 1",
)
def create_course(
    payload: CourseCreate,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CourseDetailResponse:
    return course_service.create_course(user_id, payload)


@router.get(
    "/{course_id}",
    response_model=CourseDetailResponse,
    summary="Récupérer un cours détaillé (niveaux, chapitres, exercices, projets, ressources)",
)
def get_course_detail(
    course_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CourseDetailResponse:
    return course_service.get_course_detail(user_id, course_id)


@router.patch(
    "/{course_id}",
    response_model=CourseSummaryResponse,
    summary="Mettre à jour les métadonnées autorisées d'un cours",
)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CourseSummaryResponse:
    return course_service.update_course(user_id, course_id, payload)


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un cours",
)
def delete_course(
    course_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> Response:
    course_service.delete_course(user_id, course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{course_id}/lessons/{lesson_id}",
    response_model=CourseLessonResponse,
    summary="Mettre à jour l'avancement d'un chapitre de cours",
)
def update_course_lesson_progress(
    course_id: UUID,
    lesson_id: UUID,
    payload: CourseLessonProgressUpdate,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CourseLessonResponse:
    return course_service.update_lesson_progress(user_id, course_id, lesson_id, payload)


@router.post(
    "/{course_id}/lessons/{lesson_id}/ask",
    response_model=CourseLessonTutorAskResponse,
    summary="Poser une question interactive au tuteur IA sur l'étape active du chapitre",
)
def ask_course_lesson_tutor(
    course_id: UUID,
    lesson_id: UUID,
    payload: CourseLessonTutorAskRequest,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CourseLessonTutorAskResponse:
    return course_service.ask_lesson_tutor(user_id, course_id, lesson_id, payload)


@router.post(
    "/{course_id}/resources",
    response_model=CourseResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une documentation ou vidéo vérifiée à un cours",
)
def add_course_resource(
    course_id: UUID,
    payload: CourseResourceCreate,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CourseResourceResponse:
    return course_service.add_resource(user_id, course_id, payload)


@router.delete(
    "/{course_id}/resources/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une ressource de cours",
)
def delete_course_resource(
    course_id: UUID,
    resource_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> Response:
    course_service.delete_resource(user_id, course_id, resource_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{course_id}/levels/{level_id}/submissions",
    response_model=CourseSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Soumettre un exercice ou un projet de niveau pour correction détaillée",
)
def submit_course_work(
    course_id: UUID,
    level_id: UUID,
    payload: CourseSubmissionCreate,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CourseSubmissionResponse:
    return course_service.submit_work(user_id, course_id, level_id, payload)


@router.post(
    "/{course_id}/levels/{level_id}/validate",
    response_model=CourseDetailResponse,
    summary="Valider un niveau après complétion des chapitres, exercices et projet",
)
def validate_course_level(
    course_id: UUID,
    level_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CourseDetailResponse:
    return course_service.validate_level(user_id, course_id, level_id)


@router.post(
    "/{course_id}/levels/{level_id}/regenerate",
    response_model=CourseDetailResponse,
    summary="Régénérer le contenu d'un niveau non validé tout en archivant les versions précédentes",
)
def regenerate_course_level(
    course_id: UUID,
    level_id: UUID,
    payload: CourseLevelRegenerateRequest | None = None,
    user_id: UUID = Depends(get_current_user_id),
    course_service: CourseService = Depends(get_course_service),
) -> CourseDetailResponse:
    return course_service.regenerate_level(
        user_id,
        course_id,
        level_id,
        payload or CourseLevelRegenerateRequest(),
    )
