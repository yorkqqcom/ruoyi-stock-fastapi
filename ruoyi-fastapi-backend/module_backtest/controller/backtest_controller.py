from typing import Annotated

from fastapi import Body, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import CurrentUserDependency, PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel, PageResponseModel, ResponseBaseModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_backtest.entity.vo.backtest_vo import (
    BacktestTaskCreateRequestModel,
    BacktestTaskPageQueryModel,
    BacktestTaskUpdateRequestModel,
    BacktestTradePageQueryModel,
)
from module_backtest.service.backtest_service import BacktestService
from utils.log_util import logger
from utils.response_util import ResponseUtil

backtest_controller = APIRouterPro(
    prefix='/backtest', order_num=50, tags=['回测管理'], dependencies=[PreAuthDependency()]
)


@backtest_controller.post(
    '/task/create',
    summary='创建回测任务接口',
    description='用于创建回测任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('backtest:task:create')],
)
@Log(title='回测任务', business_type=BusinessType.INSERT)
async def create_backtest_task(
    request: Request,
    create_request: BacktestTaskCreateRequestModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
):
    """创建回测任务。使用 FastAPI 注入的 create_request 作为唯一数据源。"""
    # 记录原始请求体与解析后的关键字段，定位 model_scene_binding_id / predict_task_id / result_id 丢失问题
    try:
        body = await request.json()
    except Exception:
        body = None

    # 注意：项目日志使用 loguru，需使用 {} 或 f-string，而不是标准 logging 的 %s 占位符
    logger.info('[BacktestTask] /backtest/task/create 原始请求体: {}', body)
    logger.info(
        '[BacktestTask] 解析后的模型字段: task_name={} signal_source_type={} '
        'result_id={} predict_task_id={} model_scene_binding_id={}',
        create_request.task_name,
        create_request.signal_source_type,
        create_request.result_id,
        create_request.predict_task_id,
        create_request.model_scene_binding_id,
    )
    result = await BacktestService.create_task_service(
        query_db, create_request, current_user.user.user_name
    )
    return ResponseUtil.success(msg=result.message) if result.is_success else ResponseUtil.failure(msg=result.message)


@backtest_controller.post(
    '/task/page',
    summary='获取回测任务分页列表接口',
    description='用于获取回测任务分页列表',
    response_model=PageResponseModel,
    dependencies=[UserInterfaceAuthDependency('backtest:task:list')],
)
async def get_backtest_task_page(
    request: Request,
    query: Annotated[BacktestTaskPageQueryModel, Body()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    """获取回测任务分页列表"""
    result = await BacktestService.get_task_page_service(query_db, query)
    return ResponseUtil.success(model_content=result)


@backtest_controller.put(
    '/task/{task_id}',
    summary='更新回测任务',
    description='仅支持对待执行或失败任务更新（如补填模型、预测任务等）',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('backtest:task:create')],
)
@Log(title='回测任务', business_type=BusinessType.UPDATE)
async def update_backtest_task(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    update_request: BacktestTaskUpdateRequestModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    """更新回测任务"""
    result = await BacktestService.update_task_service(query_db, task_id, update_request)
    return ResponseUtil.success(msg=result.message) if result.is_success else ResponseUtil.failure(msg=result.message)


@backtest_controller.delete(
    '/task/{task_id}',
    summary='删除回测任务',
    description='删除回测任务及其关联的交易明细、净值、结果',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('backtest:task:remove')],
)
@Log(title='回测任务', business_type=BusinessType.DELETE)
async def delete_backtest_task(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    """删除回测任务"""
    result = await BacktestService.delete_task_service(query_db, task_id)
    return ResponseUtil.success(msg=result.message) if result.is_success else ResponseUtil.failure(msg=result.message)


@backtest_controller.post(
    '/task/execute/{task_id}',
    summary='执行/重新执行回测任务',
    description='对待执行或失败的任务触发执行',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('backtest:task:create')],
)
@Log(title='回测任务', business_type=BusinessType.UPDATE)
async def execute_backtest_task_api(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    """执行/重新执行回测任务"""
    result = await BacktestService.execute_task_service(query_db, task_id)
    return ResponseUtil.success(msg=result.message) if result.is_success else ResponseUtil.failure(msg=result.message)


@backtest_controller.get(
    '/task/detail/{task_id}',
    summary='获取回测任务详情接口',
    description='用于获取回测任务详情',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('backtest:task:query')],
)
async def get_backtest_task_detail(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    """获取回测任务详情"""
    try:
        result = await BacktestService.get_task_detail_service(query_db, task_id)
        logger.info(f'获取回测任务详情成功，任务ID：{task_id}')
        return ResponseUtil.success(data=result)
    except ValueError as e:
        logger.warning(f'获取回测任务详情失败：{str(e)}')
        return ResponseUtil.failure(msg=str(e))


@backtest_controller.get(
    '/result/detail/{task_id}',
    summary='获取回测结果详情接口',
    description='用于获取回测结果详情',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('backtest:result:query')],
)
async def get_backtest_result_detail(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    """获取回测结果详情"""
    try:
        result = await BacktestService.get_result_detail_service(query_db, task_id)
        logger.info(f'获取回测结果详情成功，任务ID：{task_id}')
        return ResponseUtil.success(data=result)
    except ValueError as e:
        logger.warning(f'获取回测结果详情失败：{str(e)}')
        return ResponseUtil.failure(msg=str(e))


@backtest_controller.post(
    '/trade/page',
    summary='获取回测交易明细分页列表接口',
    description='用于获取回测交易明细分页列表',
    response_model=PageResponseModel,
    dependencies=[UserInterfaceAuthDependency('backtest:trade:list')],
)
async def get_backtest_trade_page(
    request: Request,
    query: Annotated[BacktestTradePageQueryModel, Body()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    """获取回测交易明细分页列表"""
    result = await BacktestService.get_trade_page_service(query_db, query)
    logger.info('获取回测交易明细列表成功')
    return ResponseUtil.success(model_content=result)
