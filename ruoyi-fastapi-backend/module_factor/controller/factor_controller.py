import json
from datetime import datetime
from typing import Annotated

from fastapi import Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.db_seesion import DBSessionDependency
from config.database import AsyncSessionLocal
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import CurrentUserDependency, PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel, PageResponseModel, ResponseBaseModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_factor.entity.vo.factor_vo import (
    DeleteFactorDefinitionModel,
    DeleteFactorTaskModel,
    EditFactorDefinitionModel,
    EditFactorTaskModel,
    EditModelTrainTaskModel,
    FactorCalcLogPageQueryModel,
    FactorDefinitionModel,
    FactorDefinitionPageQueryModel,
    FactorTaskModel,
    FactorTaskPageQueryModel,
    FactorValueQueryModel,
    ModelPredictRequestModel,
    ModelPredictResultPageQueryModel,
    ModelSceneBindRequestModel,
    ModelTrainRequestModel,
    ModelTrainResultPageQueryModel,
    ModelTrainTaskPageQueryModel,
)
from module_factor.service.factor_service import (
    FactorCalcLogService,
    FactorDefinitionService,
    FactorTaskService,
    FactorValueService,
)
from module_factor.dao.factor_dao import ModelTrainResultDao, ModelTrainTaskDao
from module_factor.service import factor_config_service
from module_factor.service.model_train_service import ModelTrainService
from module_factor.task.model_train_task import execute_model_train_task
from pydantic_validation_decorator import ValidateFields
from utils.log_util import logger
from utils.response_util import ResponseUtil


factor_controller = APIRouterPro(
    prefix='/factor', order_num=30, tags=['因子管理'], dependencies=[PreAuthDependency()]
)


# ==================== 因子定义管理 ====================


@factor_controller.get(
    '/definition/list',
    summary='获取因子定义分页列表接口',
    description='用于获取因子定义分页列表',
    response_model=PageResponseModel[FactorDefinitionModel],
    dependencies=[UserInterfaceAuthDependency('factor:definition:list')],
)
async def get_factor_definition_list(
    request: Request,
    definition_page_query: Annotated[FactorDefinitionPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await FactorDefinitionService.get_definition_list_services(
        query_db, definition_page_query, is_page=True
    )
    logger.info('获取因子定义列表成功')
    return ResponseUtil.success(model_content=result)


@factor_controller.post(
    '/definition',
    summary='新增因子定义接口',
    description='用于新增因子定义',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:definition:add')],
)
@ValidateFields(validate_model='add_factor_definition')
@Log(title='因子定义', business_type=BusinessType.INSERT)
async def add_factor_definition(
    request: Request,
    add_model: FactorDefinitionModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
):
    add_model.create_by = current_user.user.user_name
    add_model.create_time = datetime.now()
    add_model.update_by = current_user.user.user_name
    add_model.update_time = datetime.now()
    result = await FactorDefinitionService.add_definition_services(query_db, add_model)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@factor_controller.put(
    '/definition',
    summary='编辑因子定义接口',
    description='用于编辑因子定义',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:definition:edit')],
)
@ValidateFields(validate_model='edit_factor_definition')
@Log(title='因子定义', business_type=BusinessType.UPDATE)
async def edit_factor_definition(
    request: Request,
    edit_model: EditFactorDefinitionModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
):
    edit_model.update_by = current_user.user.user_name
    edit_model.update_time = datetime.now()
    result = await FactorDefinitionService.edit_definition_services(query_db, edit_model)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@factor_controller.delete(
    '/definition/{factor_ids}',
    summary='删除因子定义接口',
    description='用于删除因子定义',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:definition:remove')],
)
@Log(title='因子定义', business_type=BusinessType.DELETE)
async def delete_factor_definition(
    request: Request,
    factor_ids: Annotated[str, Path(description='需要删除的因子ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    delete_model = DeleteFactorDefinitionModel(factorIds=factor_ids)
    result = await FactorDefinitionService.delete_definition_services(query_db, delete_model)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


# ==================== 因子任务管理 ====================


@factor_controller.get(
    '/task/list',
    summary='获取因子任务分页列表接口',
    description='用于获取因子任务分页列表',
    response_model=PageResponseModel[FactorTaskModel],
    dependencies=[UserInterfaceAuthDependency('factor:task:list')],
)
async def get_factor_task_list(
    request: Request,
    task_page_query: Annotated[FactorTaskPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await FactorTaskService.get_task_list_services(query_db, task_page_query, is_page=True)
    logger.info('获取因子任务列表成功')
    return ResponseUtil.success(model_content=result)


@factor_controller.post(
    '/task',
    summary='新增因子任务接口',
    description='用于新增因子任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:task:add')],
)
@ValidateFields(validate_model='add_factor_task')
@Log(title='因子任务', business_type=BusinessType.INSERT)
async def add_factor_task(
    request: Request,
    add_task: FactorTaskModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
):
    add_task.create_by = current_user.user.user_name
    add_task.create_time = datetime.now()
    add_task.update_by = current_user.user.user_name
    add_task.update_time = datetime.now()
    result = await FactorTaskService.add_task_services(query_db, add_task)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@factor_controller.put(
    '/task',
    summary='编辑因子任务接口',
    description='用于编辑因子任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:task:edit')],
)
@ValidateFields(validate_model='edit_factor_task')
@Log(title='因子任务', business_type=BusinessType.UPDATE)
async def edit_factor_task(
    request: Request,
    edit_task: EditFactorTaskModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
):
    edit_task.update_by = current_user.user.user_name
    edit_task.update_time = datetime.now()
    result = await FactorTaskService.edit_task_services(query_db, edit_task)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@factor_controller.put(
    '/task/changeStatus',
    summary='修改因子任务状态接口',
    description='用于修改因子任务状态',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:task:changeStatus')],
)
@Log(title='因子任务', business_type=BusinessType.UPDATE)
async def change_factor_task_status(
    request: Request,
    task_id: Annotated[int, Query(description='任务ID')],
    status: Annotated[str, Query(description='状态（0正常 1暂停）')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await FactorTaskService.change_task_status_services(query_db, task_id, status)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@factor_controller.delete(
    '/task/{task_ids}',
    summary='删除因子任务接口',
    description='用于删除因子任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:task:remove')],
)
@Log(title='因子任务', business_type=BusinessType.DELETE)
async def delete_factor_task(
    request: Request,
    task_ids: Annotated[str, Path(description='需要删除的任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    delete_model = DeleteFactorTaskModel(taskIds=task_ids)
    result = await FactorTaskService.delete_task_services(query_db, delete_model)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@factor_controller.post(
    '/task/execute/{task_id}',
    summary='执行因子任务接口',
    description='用于手动执行指定的因子任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:task:execute')],
)
@Log(title='因子任务', business_type=BusinessType.OTHER)
async def execute_factor_task(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await FactorTaskService.execute_task_services(query_db, task_id)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


# ==================== 因子结果查询 ====================


@factor_controller.get(
    '/value/page',
    summary='分页查询因子结果接口',
    description='按股票、日期区间和因子代码分页查询因子结果',
    response_model=PageResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:value:list')],
)
async def get_factor_value_page(
    request: Request,
    query_model: Annotated[FactorValueQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await FactorValueService.get_factor_value_page_services(query_db, query_model)
    logger.info('获取因子结果分页数据成功')
    return ResponseUtil.success(model_content=result)


# ==================== 因子计算日志管理 ====================


@factor_controller.get(
    '/calcLog/list',
    summary='获取因子计算日志分页列表接口',
    description='用于获取因子计算日志分页列表',
    response_model=PageResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:calcLog:list')],
)
async def get_factor_calc_log_list(
    request: Request,
    log_page_query: Annotated[FactorCalcLogPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await FactorCalcLogService.get_log_list_services(query_db, log_page_query, is_page=True)
    logger.info('获取因子计算日志列表成功')
    return ResponseUtil.success(model_content=result)


# ==================== 模型训练管理 ====================


@factor_controller.get(
    '/model/config/list',
    summary='获取因子配置文件列表',
    description='扫描 config/train 下 .txt 文件，返回名称、path、因子数量',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:config:list')],
)
async def get_factor_config_list(request: Request):
    result = factor_config_service.list_configs()
    return ResponseUtil.success(data=result)


@factor_controller.get(
    '/model/config/content',
    summary='获取因子配置文件内容',
    description='根据 path 读取文件并解析为逗号分隔的 factorCodes',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:config:list')],
)
async def get_factor_config_content(
    request: Request,
    path: Annotated[str, Query(description='配置文件名或相对路径')],
):
    factor_codes, err = factor_config_service.get_content(path)
    if err:
        return ResponseUtil.failure(msg=err)
    return ResponseUtil.success(data={'factorCodes': factor_codes})


@factor_controller.post(
    '/model/train',
    summary='创建并执行模型训练任务接口',
    description='用于创建并执行模型训练任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:train')],
)
@Log(title='模型训练', business_type=BusinessType.INSERT)
async def train_model(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
):
    # 从 request 取 body：Log 装饰器已用 request.body() 读流并缓存，优先用缓存避免解析为空
    body = getattr(request.state, '_cached_json_body', None)
    body_source = '_cached_json_body'
    if not isinstance(body, dict):
        raw = getattr(request.state, '_cached_body_bytes', None)
        if raw:
            try:
                body = json.loads(raw)
                body_source = '_cached_body_bytes'
            except Exception as e:
                logger.warning('[train_model] json.loads(_cached_body_bytes) failed: %s', e)
                body = None
        else:
            try:
                body = await request.json()
                body_source = 'request.json()'
            except Exception as e:
                logger.warning('[train_model] request.json() failed: %s', e)
                body = None
    logger.info(
        '[train_model] body_source=%s, has_body=%s, body_keys=%s, body.taskName=%s',
        body_source,
        bool(body and isinstance(body, dict)),
        list(body.keys()) if isinstance(body, dict) else None,
        body.get('taskName') if isinstance(body, dict) else None,
    )
    if not body or not isinstance(body, dict):
        return ResponseUtil.failure(msg='请求体不能为空')
    try:
        train_request = ModelTrainRequestModel.model_validate(body)
    except Exception as e:
        return ResponseUtil.failure(msg=f'请求体格式错误：{e!s}')
    logger.info(
        '[train_model] train_request: task_name=%r, factor_codes=%r, start_date=%r, end_date=%r',
        getattr(train_request, 'task_name', None),
        getattr(train_request, 'factor_codes', None),
        getattr(train_request, 'start_date', None),
        getattr(train_request, 'end_date', None),
    )
    # 校验必填字段，避免 INSERT 时违反 not-null 约束
    if not (train_request.task_name and str(train_request.task_name).strip()):
        return ResponseUtil.failure(msg='任务名称不能为空')
    if not (train_request.factor_codes and str(train_request.factor_codes).strip()):
        return ResponseUtil.failure(msg='因子代码列表不能为空')
    if not (train_request.start_date and str(train_request.start_date).strip()):
        return ResponseUtil.failure(msg='训练开始日期不能为空')
    if not (train_request.end_date and str(train_request.end_date).strip()):
        return ResponseUtil.failure(msg='训练结束日期不能为空')

    # 创建训练任务
    from module_factor.entity.vo.factor_vo import ModelTrainTaskModel

    task_name_val = (train_request.task_name or '').strip()
    task_model = ModelTrainTaskModel(
        task_name=task_name_val,
        factor_codes=(train_request.factor_codes or '').strip(),
        symbol_universe=train_request.symbol_universe,
        start_date=(train_request.start_date or '').strip(),
        end_date=(train_request.end_date or '').strip(),
        model_params=train_request.model_params,
        train_test_split=train_request.train_test_split if train_request.train_test_split is not None else 0.8,
        create_by=current_user.user.user_name,
        create_time=datetime.now(),
        update_by=current_user.user.user_name,
        update_time=datetime.now(),
    )
    logger.info(
        '[train_model] task_model before add_task_dao: task_name=%r, factor_codes=%r, type=%s',
        getattr(task_model, 'task_name', None),
        getattr(task_model, 'factor_codes', None),
        type(task_model).__name__,
    )
    task_db = await ModelTrainTaskDao.add_task_dao(query_db, task_model)
    task_id = int(task_db.id)  # 在 commit 前取出 id，避免 commit 后访问过期 ORM 触发懒加载导致 MissingGreenlet
    await query_db.commit()

    # 异步执行训练任务
    execute_model_train_task(AsyncSessionLocal, task_id, train_request)

    logger.info(f'模型训练任务已创建并启动，任务ID：{task_id}')
    return ResponseUtil.success(msg=f'模型训练任务已创建并启动，任务ID：{task_id}')


@factor_controller.get(
    '/model/task/list',
    summary='获取模型训练任务分页列表接口',
    description='用于获取模型训练任务分页列表',
    response_model=PageResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:task:list')],
)
async def get_model_train_task_list(
    request: Request,
    task_page_query: Annotated[ModelTrainTaskPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await ModelTrainTaskDao.get_task_list(query_db, task_page_query, is_page=True)
    logger.info('获取模型训练任务列表成功')
    return ResponseUtil.success(model_content=result)


@factor_controller.get(
    '/model/task/{task_id}',
    summary='获取模型训练任务详情接口',
    description='用于获取模型训练任务详情',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:task:detail')],
)
async def get_model_train_task_detail(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await ModelTrainTaskDao.get_task_by_id(query_db, task_id)
    if not result:
        return ResponseUtil.failure(msg='训练任务不存在')
    from utils.common_util import CamelCaseUtil

    result_dict = CamelCaseUtil.transform_result(result)
    logger.info('获取模型训练任务详情成功')
    return ResponseUtil.success(data=result_dict)


@factor_controller.get(
    '/model/task/{task_id}/results',
    summary='获取指定训练任务的所有训练结果列表接口',
    description='根据任务ID获取该任务下的所有训练结果（包含版本号），不分页返回',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:result:list')],
)
async def get_model_train_results_by_task(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    query_model = ModelTrainResultPageQueryModel(task_id=task_id)
    result = await ModelTrainService.get_result_list_services(query_db, query_model, is_page=False)
    logger.info('按任务获取模型训练结果列表成功')
    return ResponseUtil.success(data=result)


@factor_controller.put(
    '/model/task',
    summary='编辑模型训练任务接口',
    description='用于编辑模型训练任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:task:edit')],
)
@ValidateFields(validate_model='edit_model_train_task')
@Log(title='模型训练任务', business_type=BusinessType.UPDATE)
async def edit_model_train_task(
    request: Request,
    edit_task: EditModelTrainTaskModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
):
    edit_task.update_by = current_user.user.user_name
    edit_task.update_time = datetime.now()
    result = await ModelTrainService.edit_task_service(query_db, edit_task)
    logger.info(result.message)
    
    return ResponseUtil.success(msg=result.message) if result.is_success else ResponseUtil.failure(msg=result.message)


@factor_controller.get(
    '/model/result/list',
    summary='获取模型训练结果分页列表接口',
    description='用于获取模型训练结果分页列表',
    response_model=PageResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:result:list')],
)
async def get_model_train_result_list(
    request: Request,
    result_page_query: Annotated[ModelTrainResultPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await ModelTrainService.get_result_list_services(query_db, result_page_query, is_page=True)
    logger.info('获取模型训练结果列表成功')
    return ResponseUtil.success(model_content=result)


@factor_controller.get(
    '/model/result/{result_id}',
    summary='获取模型训练结果详情接口',
    description='用于获取模型训练结果详情（包含评估指标）',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:result:detail')],
)
async def get_model_train_result_detail(
    request: Request,
    result_id: Annotated[int, Path(description='结果ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await ModelTrainResultDao.get_result_by_id(query_db, result_id)
    if not result:
        return ResponseUtil.failure(msg='训练结果不存在')
    from utils.common_util import CamelCaseUtil

    result_dict = CamelCaseUtil.transform_result(result)
    logger.info('获取模型训练结果详情成功')
    return ResponseUtil.success(data=result_dict)


@factor_controller.post(
    '/model/predict',
    summary='执行模型预测接口',
    description='用于执行模型预测',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:predict')],
)
@Log(title='模型预测', business_type=BusinessType.OTHER)
async def predict_model(
    request: Request,
    predict_request: ModelPredictRequestModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await ModelTrainService.predict_service(query_db, predict_request)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message) if result.is_success else ResponseUtil.failure(msg=result.message)


@factor_controller.post(
    '/model/scene/bind',
    summary='绑定模型场景接口',
    description='为指定训练任务和场景绑定一个训练结果（模型版本），用于按场景选择生效模型',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:scene:bind')],
)
@Log(title='模型场景绑定', business_type=BusinessType.UPDATE)
async def bind_model_scene(
    request: Request,
    bind_request: ModelSceneBindRequestModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await ModelTrainService.bind_scene_model_service(query_db, bind_request)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message) if result.is_success else ResponseUtil.failure(msg=result.message)


@factor_controller.get(
    '/model/predict/list',
    summary='获取模型预测结果分页列表接口',
    description='用于获取模型预测结果分页列表',
    response_model=PageResponseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:predict:list')],
)
async def get_model_predict_result_list(
    request: Request,
    predict_page_query: Annotated[ModelPredictResultPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await ModelTrainService.get_predict_list_services(query_db, predict_page_query, is_page=True)
    logger.info('获取模型预测结果列表成功')
    return ResponseUtil.success(model_content=result)


@factor_controller.post(
    '/model/task/execute/{task_id}',
    summary='执行模型训练任务接口',
    description='用于手动执行指定的模型训练任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:task:execute')],
)
@Log(title='模型训练任务', business_type=BusinessType.OTHER)
async def execute_model_train_task_api(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result = await ModelTrainService.execute_train_task_service(query_db, task_id)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message) if result.is_success else ResponseUtil.failure(msg=result.message)


@factor_controller.delete(
    '/model/task/{task_ids}',
    summary='删除模型训练任务接口',
    description='用于删除模型训练任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('factor:model:task:remove')],
)
@Log(title='模型训练任务', business_type=BusinessType.DELETE)
async def delete_model_train_task(
    request: Request,
    task_ids: Annotated[str, Path(description='需要删除的任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    result_count = await ModelTrainTaskDao.delete_tasks_dao(query_db, task_ids)
    await query_db.commit()
    logger.info(f'删除模型训练任务成功，共删除 {result_count} 条')
    return ResponseUtil.success(msg=f'删除成功，共删除 {result_count} 条')


