from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from app.api.deps import get_learning_service
from app.core.security import get_current_user_id
from app.schemas.learning import (
    LearningModuleCreate,
    LearningModuleResponse,
    LearningModuleUpdate,
    LearningOverviewResponse,
    LearningPathCreate,
    LearningPathResponse,
    LearningPathUpdate,
    LessonCreate,
    LessonResponse,
    LessonUpdate,
)
from app.services.learning_service import LearningService

router = APIRouter(prefix="/learning", tags=["Apprentissage"])


@router.get(
    "/overview",
    response_model=LearningOverviewResponse,
    summary="Récupérer l'ensemble des parcours, modules et leçons",
)
def get_learning_overview(
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningOverviewResponse:
    return learning_service.get_overview(user_id)


@router.get("/paths", response_model=list[LearningPathResponse], summary="Lister les parcours")
def list_paths(
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> list[LearningPathResponse]:
    return learning_service.list_paths(user_id)


@router.post(
    "/paths",
    response_model=LearningPathResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un parcours d'apprentissage",
)
def create_path(
    payload: LearningPathCreate,
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningPathResponse:
    return learning_service.create_path(user_id, payload)


@router.patch(
    "/paths/{path_id}",
    response_model=LearningPathResponse,
    summary="Modifier un parcours d'apprentissage",
)
def update_path(
    path_id: UUID,
    payload: LearningPathUpdate,
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningPathResponse:
    return learning_service.update_path(user_id, path_id, payload)


@router.delete(
    "/paths/{path_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un parcours d'apprentissage",
)
def delete_path(
    path_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> Response:
    learning_service.delete_path(user_id, path_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/modules", response_model=list[LearningModuleResponse], summary="Lister les modules")
def list_modules(
    path_id: UUID | None = Query(default=None),
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> list[LearningModuleResponse]:
    return learning_service.list_modules(user_id, path_id=path_id)


@router.post(
    "/modules",
    response_model=LearningModuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un module dans un parcours",
)
def create_module(
    payload: LearningModuleCreate,
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningModuleResponse:
    return learning_service.create_module(user_id, payload)


@router.patch(
    "/modules/{module_id}",
    response_model=LearningModuleResponse,
    summary="Modifier un module d'apprentissage",
)
def update_module(
    module_id: UUID,
    payload: LearningModuleUpdate,
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningModuleResponse:
    return learning_service.update_module(user_id, module_id, payload)


@router.delete(
    "/modules/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un module d'apprentissage",
)
def delete_module(
    module_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> Response:
    learning_service.delete_module(user_id, module_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/lessons", response_model=list[LessonResponse], summary="Lister les leçons")
def list_lessons(
    module_id: UUID | None = Query(default=None),
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> list[LessonResponse]:
    return learning_service.list_lessons(user_id, module_id=module_id)


@router.post(
    "/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une leçon dans un module",
)
def create_lesson(
    payload: LessonCreate,
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> LessonResponse:
    return learning_service.create_lesson(user_id, payload)


@router.patch(
    "/lessons/{lesson_id}",
    response_model=LessonResponse,
    summary="Modifier une leçon (sans validation automatique de compétence)",
)
def update_lesson(
    lesson_id: UUID,
    payload: LessonUpdate,
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> LessonResponse:
    return learning_service.update_lesson(user_id, lesson_id, payload)


@router.delete(
    "/lessons/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une leçon",
)
def delete_lesson(
    lesson_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    learning_service: LearningService = Depends(get_learning_service),
) -> Response:
    learning_service.delete_lesson(user_id, lesson_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
