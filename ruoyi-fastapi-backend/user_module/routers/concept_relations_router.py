from fastapi import APIRouter, Request
from user_module.services.concept_relations_service import get_concept_model, get_concept_correlation_by_name, get_concept_name, get_concept_model_by_name


from utils.response_util import ResponseUtil

router = APIRouter(prefix="/concept_relations", tags=["概念板块关系"])

@router.get("/list")
def list_concept_relations(min_overlap: float = 0.4, max_overlap: float = 1.0):
    model = get_concept_model(min_overlap=min_overlap, max_overlap=max_overlap)
    return ResponseUtil.success(data=model)

@router.get("/boardlist")
async def get_concept_boardlist(request: Request):
    redis = request.app.state.redis
    model = await get_concept_name(redis)
    return ResponseUtil.success(data=model)

@router.get("/correlation")
def get_concept_correlation_api(concept_name: str):
    data = get_concept_correlation_by_name(concept_name)
    return ResponseUtil.success(data={"data": data})

@router.get("/model_by_name")
def get_concept_model_by_name_api(concept_name: str, min_overlap: float = 0.4, max_overlap: float = 1.0):
    data = get_concept_model_by_name(concept_name, min_overlap, max_overlap)
    return ResponseUtil.success(data=data)