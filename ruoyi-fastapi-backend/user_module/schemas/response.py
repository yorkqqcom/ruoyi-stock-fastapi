from pydantic import BaseModel, Field

class ResponseBase(BaseModel):
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="返回信息")

class Response200(ResponseBase):
    data: list = Field(default_factory=list, description="业务数据")

class Response400(ResponseBase):
    code: int = 400
    message: str = "请求参数错误"