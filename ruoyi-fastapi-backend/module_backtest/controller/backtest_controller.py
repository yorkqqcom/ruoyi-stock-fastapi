from typing import Annotated

from fastapi import Path, Query, Request
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
    """创建回测任务"""
    result = await BacktestService.create_task_service(
        query_db, create_request, current_user.user.user_name
    )
    logger.info(result.message)
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
    query: Annotated[BacktestTaskPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    """获取回测任务分页列表"""
    result = await BacktestService.get_task_page_service(query_db, query)
    logger.info('获取回测任务列表成功')
    return ResponseUtil.success(model_content=result)


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
    query: Annotated[BacktestTradePageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
):
    """获取回测交易明细分页列表"""
    result = await BacktestService.get_trade_page_service(query_db, query)
    logger.info('获取回测交易明细列表成功')
    return ResponseUtil.success(model_content=result)
