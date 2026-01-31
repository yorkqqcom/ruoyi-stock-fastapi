from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_validation_decorator import FieldValidationError, NotBlank, Size


class TushareApiConfigModel(BaseModel):
    """
    Tushare接口配置表对应pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    config_id: int | None = Field(default=None, description='配置ID')
    api_name: str | None = Field(default=None, description='接口名称')
    api_code: str | None = Field(default=None, description='接口代码')
    api_desc: str | None = Field(default=None, description='接口描述')
    api_params: str | None = Field(default=None, description='接口参数（JSON格式）')
    data_fields: str | None = Field(default=None, description='数据字段（JSON格式）')
    primary_key_fields: str | None = Field(default=None, description='主键字段配置（JSON格式，为空则使用默认data_id主键）')
    status: Literal['0', '1'] | None = Field(default=None, description='状态（0正常 1停用）')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: datetime | None = Field(default=None, description='更新时间')
    remark: str | None = Field(default=None, description='备注信息')

    @NotBlank(field_name='api_name', message='接口名称不能为空')
    @Size(field_name='api_name', min_length=0, max_length=100, message='接口名称长度不能超过100个字符')
    def get_api_name(self) -> str | None:
        return self.api_name

    @NotBlank(field_name='api_code', message='接口代码不能为空')
    @Size(field_name='api_code', min_length=0, max_length=100, message='接口代码长度不能超过100个字符')
    def get_api_code(self) -> str | None:
        return self.api_code

    def validate_fields(self) -> None:
        self.get_api_name()
        self.get_api_code()


class TushareApiConfigQueryModel(TushareApiConfigModel):
    """
    Tushare接口配置查询模型
    """

    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class TushareApiConfigPageQueryModel(TushareApiConfigQueryModel):
    """
    Tushare接口配置分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class EditTushareApiConfigModel(TushareApiConfigModel):
    """
    编辑Tushare接口配置模型
    """

    type: str | None = Field(default=None, description='操作类型')


class DeleteTushareApiConfigModel(BaseModel):
    """
    删除Tushare接口配置模型
    """

    config_ids: str = Field(description='需要删除的配置ID')


class TushareDownloadTaskModel(BaseModel):
    """
    Tushare下载任务表对应pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    task_id: int | None = Field(default=None, description='任务ID')
    task_name: str | None = Field(default=None, description='任务名称')
    config_id: int | None = Field(default=None, description='接口配置ID')
    workflow_id: int | None = Field(default=None, description='流程配置ID（如果存在则执行流程，否则执行单个接口）')
    task_type: Literal['single', 'workflow'] | None = Field(default=None, description='任务类型（single:单个接口 workflow:流程配置）')
    cron_expression: str | None = Field(default=None, description='cron执行表达式')
    start_date: str | None = Field(default=None, description='开始日期')
    end_date: str | None = Field(default=None, description='结束日期')
    task_params: str | None = Field(default=None, description='任务参数（JSON格式）')
    save_path: str | None = Field(default=None, description='保存路径')
    save_format: str | None = Field(default=None, description='保存格式')
    save_to_db: Literal['0', '1'] | None = Field(default=None, description='是否保存到数据库（0否 1是）')
    data_table_name: str | None = Field(default=None, description='数据存储表名（为空则使用默认表tushare_data）')
    status: Literal['0', '1'] | None = Field(default=None, description='状态（0正常 1暂停）')
    last_run_time: datetime | None = Field(default=None, description='最后运行时间')
    next_run_time: datetime | None = Field(default=None, description='下次运行时间')
    run_count: int | None = Field(default=None, description='运行次数')
    success_count: int | None = Field(default=None, description='成功次数')
    fail_count: int | None = Field(default=None, description='失败次数')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: datetime | None = Field(default=None, description='更新时间')
    remark: str | None = Field(default=None, description='备注信息')
    
    def model_post_init(self, __context) -> None:
        """模型初始化后处理，自动计算任务类型"""
        if self.task_type is None:
            # 根据 workflow_id 自动判断任务类型
            self.task_type = 'workflow' if self.workflow_id else 'single'

    def _ensure_task_type(self) -> None:
        """确保任务类型已设置（在验证前调用）"""
        if self.task_type is None:
            # 根据 workflow_id 自动判断任务类型
            self.task_type = 'workflow' if self.workflow_id else 'single'

    @NotBlank(field_name='task_name', message='任务名称不能为空')
    @Size(field_name='task_name', min_length=0, max_length=100, message='任务名称长度不能超过100个字符')
    def get_task_name(self) -> str | None:
        return self.task_name

    def get_config_id(self) -> int | None:
        return self.config_id

    def validate_fields(self) -> None:
        # 先确保 task_type 已设置
        self._ensure_task_type()
        self.get_task_name()


class TushareDownloadTaskQueryModel(TushareDownloadTaskModel):
    """
    Tushare下载任务查询模型
    """

    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class TushareDownloadTaskPageQueryModel(TushareDownloadTaskQueryModel):
    """
    Tushare下载任务分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')
    task_type: Literal['single', 'workflow'] | None = Field(default=None, description='任务类型筛选（single:单个接口 workflow:流程配置）')


class EditTushareDownloadTaskModel(TushareDownloadTaskModel):
    """
    编辑Tushare下载任务模型
    """

    type: str | None = Field(default=None, description='操作类型')


class DeleteTushareDownloadTaskModel(BaseModel):
    """
    删除Tushare下载任务模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    task_ids: str = Field(description='需要删除的任务ID')


class TushareDownloadLogModel(BaseModel):
    """
    Tushare下载日志表对应pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    log_id: int | None = Field(default=None, description='日志ID')
    task_id: int | None = Field(default=None, description='任务ID')
    task_name: str | None = Field(default=None, description='任务名称')
    config_id: int | None = Field(default=None, description='接口配置ID')
    api_name: str | None = Field(default=None, description='接口名称')
    download_date: str | None = Field(default=None, description='下载日期')
    record_count: int | None = Field(default=None, description='记录数')
    file_path: str | None = Field(default=None, description='文件路径')
    status: Literal['0', '1'] | None = Field(default=None, description='执行状态（0成功 1失败）')
    error_message: str | None = Field(default=None, description='错误信息')
    duration: int | None = Field(default=None, description='执行时长（秒）')
    create_time: datetime | None = Field(default=None, description='创建时间')


class TushareDownloadLogQueryModel(TushareDownloadLogModel):
    """
    Tushare下载日志查询模型
    """

    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class TushareDownloadLogPageQueryModel(TushareDownloadLogQueryModel):
    """
    Tushare下载日志分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')
    task_type: Literal['single', 'workflow'] | None = Field(default=None, description='任务类型筛选（single:单个接口 workflow:流程配置）')


class DeleteTushareDownloadLogModel(BaseModel):
    """
    删除Tushare下载日志模型
    """

    log_ids: str = Field(description='需要删除的日志ID')


class TushareDataModel(BaseModel):
    """
    Tushare数据存储表对应pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    data_id: int | None = Field(default=None, description='数据ID')
    task_id: int | None = Field(default=None, description='任务ID')
    config_id: int | None = Field(default=None, description='接口配置ID')
    api_code: str | None = Field(default=None, description='接口代码')
    download_date: str | None = Field(default=None, description='下载日期（YYYYMMDD）')
    data_content: dict | list | None = Field(default=None, description='数据内容（JSON格式）')
    create_time: datetime | None = Field(default=None, description='创建时间')


class TushareDataQueryModel(TushareDataModel):
    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class TushareDataPageQueryModel(TushareDataQueryModel):
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class DeleteTushareDataModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)

    data_ids: str = Field(description='需要删除的数据ID')


class TushareWorkflowConfigModel(BaseModel):
    """
    Tushare流程配置表对应pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    workflow_id: int | None = Field(default=None, description='流程ID')
    workflow_name: str | None = Field(default=None, description='流程名称')
    workflow_desc: str | None = Field(default=None, description='流程描述')
    status: Literal['0', '1'] | None = Field(default=None, description='状态（0正常 1停用）')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: datetime | None = Field(default=None, description='更新时间')
    remark: str | None = Field(default=None, description='备注信息')

    @NotBlank(field_name='workflow_name', message='流程名称不能为空')
    @Size(field_name='workflow_name', min_length=0, max_length=100, message='流程名称长度不能超过100个字符')
    def get_workflow_name(self) -> str | None:
        return self.workflow_name

    def validate_fields(self) -> None:
        self.get_workflow_name()


class TushareWorkflowConfigQueryModel(TushareWorkflowConfigModel):
    """
    Tushare流程配置查询模型
    """

    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class TushareWorkflowConfigPageQueryModel(TushareWorkflowConfigQueryModel):
    """
    Tushare流程配置分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class EditTushareWorkflowConfigModel(TushareWorkflowConfigModel):
    """
    编辑Tushare流程配置模型
    """

    type: str | None = Field(default=None, description='操作类型')


class DeleteTushareWorkflowConfigModel(BaseModel):
    """
    删除Tushare流程配置模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    workflow_ids: str = Field(description='需要删除的流程ID')


class TushareWorkflowStepModel(BaseModel):
    """
    Tushare流程步骤表对应pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    step_id: int | None = Field(default=None, description='步骤ID')
    workflow_id: int | None = Field(default=None, description='流程ID')
    step_order: int | None = Field(default=None, description='步骤顺序（从1开始）')
    step_name: str | None = Field(default=None, description='步骤名称')
    config_id: int | None = Field(default=None, description='接口配置ID')
    step_params: str | None = Field(default=None, description='步骤参数（JSON格式，可从前一步获取数据）')
    condition_expr: str | None = Field(default=None, description='执行条件（JSON格式，可选）')
    # 可视化编辑器相关字段
    position_x: int | None = Field(default=None, description='节点X坐标（用于可视化布局）')
    position_y: int | None = Field(default=None, description='节点Y坐标（用于可视化布局）')
    node_type: str | None = Field(default='task', description='节点类型（start/end/task）')
    source_step_ids: str | None = Field(default=None, description='前置步骤ID列表（JSON格式，支持多个前置节点）')
    target_step_ids: str | None = Field(default=None, description='后置步骤ID列表（JSON格式，支持多个后置节点）')
    layout_data: dict | list | None = Field(default=None, description='完整的布局数据（JSON格式，存储节点位置、连接线等可视化信息）')
    data_table_name: str | None = Field(default=None, description='数据存储表名（为空则使用任务配置的表名或默认表名）')
    loop_mode: Literal['0', '1'] | None = Field(default='0', description='遍历模式（0否 1是，开启后所有变量参数都会遍历）')
    update_mode: Literal['0', '1', '2', '3'] | None = Field(default='0', description='数据更新方式（0仅插入 1忽略重复 2存在则更新 3先删除再插入）')
    unique_key_fields: str | None = Field(default=None, description='唯一键字段配置（JSON格式，为空则自动检测）')
    status: Literal['0', '1'] | None = Field(default=None, description='状态（0正常 1停用）')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: datetime | None = Field(default=None, description='更新时间')
    remark: str | None = Field(default=None, description='备注信息')

    @NotBlank(field_name='step_name', message='步骤名称不能为空')
    @Size(field_name='step_name', min_length=0, max_length=100, message='步骤名称长度不能超过100个字符')
    def get_step_name(self) -> str | None:
        return self.step_name

    @NotBlank(field_name='workflow_id', message='流程ID不能为空')
    def get_workflow_id(self) -> int | None:
        return self.workflow_id

    def get_config_id(self) -> int | None:
        # 开始和结束节点不需要 config_id
        if self.node_type in ['start', 'end']:
            return self.config_id
        return self.config_id

    def validate_fields(self) -> None:
        self.get_step_name()
        self.get_workflow_id()


class TushareWorkflowStepQueryModel(TushareWorkflowStepModel):
    """
    Tushare流程步骤查询模型
    """

    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class TushareWorkflowStepPageQueryModel(TushareWorkflowStepQueryModel):
    """
    Tushare流程步骤分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class EditTushareWorkflowStepModel(TushareWorkflowStepModel):
    """
    编辑Tushare流程步骤模型
    """

    type: str | None = Field(default=None, description='操作类型')


class DeleteTushareWorkflowStepModel(BaseModel):
    """
    删除Tushare流程步骤模型
    """

    step_ids: str = Field(description='需要删除的步骤ID')


class BatchSaveWorkflowStepModel(BaseModel):
    """
    批量保存Tushare流程步骤模型
    """

    create: list[TushareWorkflowStepModel] = Field(default=[], description='需要创建的步骤列表')
    update: list[TushareWorkflowStepModel] = Field(default=[], description='需要更新的步骤列表')
    delete: list[int] = Field(default=[], description='需要删除的步骤ID列表')


class TushareWorkflowConfigWithStepsModel(TushareWorkflowConfigModel):
    """
    Tushare流程配置（包含步骤列表）模型
    """

    steps: list[TushareWorkflowStepModel] | None = Field(default=None, description='步骤列表')


class TushareDownloadTaskDetailModel(TushareDownloadTaskModel):
    """
    Tushare下载任务详情模型（包含关联信息）
    """

    api_name: str | None = Field(default=None, description='接口名称（单个接口任务）')
    api_code: str | None = Field(default=None, description='接口代码（单个接口任务）')
    workflow_name: str | None = Field(default=None, description='流程名称（流程配置任务）')
    workflow_desc: str | None = Field(default=None, description='流程描述（流程配置任务）')
    step_count: int | None = Field(default=None, description='步骤数量（流程配置任务）')
    steps: list[TushareWorkflowStepModel] | None = Field(default=None, description='步骤列表（流程配置任务）')
