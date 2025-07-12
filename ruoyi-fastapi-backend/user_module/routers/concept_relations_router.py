from fastapi import APIRouter
from user_module.services.concept_relations_service import get_concept_model
import akshare as ak

from utils.response_util import ResponseUtil

router = APIRouter(prefix="/concept_relations", tags=["概念板块关系"])

@router.get("/list")
def list_concept_relations(min_overlap: float = 0.4, max_overlap: float = 1.0):
    model = get_concept_model(min_overlap=min_overlap, max_overlap=max_overlap)
    return ResponseUtil.success(data=model)

@router.get("/boardlist")
def get_concept_boardlist():
    df = ak.stock_board_concept_name_em()
    return {
        "data": [
            {
                "name": row["板块名称"],
                "code": row["板块代码"]
            }
            for _, row in df.iterrows()
        ]
    } 