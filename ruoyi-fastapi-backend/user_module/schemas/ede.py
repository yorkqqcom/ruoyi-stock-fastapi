# -- coding: utf-8 --
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EDERuntimeControl(BaseModel):
    paginate: bool = False
    page: Optional[int] = Field(default=1, ge=1)
    page_size: Optional[int] = Field(default=500, ge=1, le=5000)
    timeout_ms: Optional[int] = 20000
    filter_symbols: Optional[List[str]] = Field(default=None, description="根据个股代码过滤数据")


class EDERequest(BaseModel):
    key: str = Field(..., description="后端注册的EDE配置key")
    params: Dict[str, Any] = Field(default_factory=dict)
    control: Optional[EDERuntimeControl] = None


class EDEResponse(BaseModel):
    code: int
    msg: str
    data: Any


