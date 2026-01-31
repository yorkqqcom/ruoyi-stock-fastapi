from datetime import datetime
from typing import Annotated

from fastapi import Form, Path, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_validation_decorator import ValidateFields
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import CurrentUserDependency, PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel, PageResponseModel, ResponseBaseModel
from module_tushare.entity.do.tushare_do import TushareData, TushareProBar
from module_tushare.entity.vo.tushare_vo import (
    BatchSaveWorkflowStepModel,
    DeleteTushareApiConfigModel,
    DeleteTushareDownloadLogModel,
    DeleteTushareDownloadTaskModel,
    DeleteTushareWorkflowConfigModel,
    DeleteTushareWorkflowStepModel,
    EditTushareApiConfigModel,
    EditTushareDownloadTaskModel,
    EditTushareWorkflowConfigModel,
    EditTushareWorkflowStepModel,
    TushareApiConfigModel,
    TushareApiConfigPageQueryModel,
    TushareDownloadLogPageQueryModel,
    TushareDownloadTaskModel,
    TushareDownloadTaskDetailModel,
    TushareDownloadTaskPageQueryModel,
    TushareWorkflowConfigModel,
    TushareWorkflowConfigPageQueryModel,
    TushareWorkflowConfigWithStepsModel,
    TushareWorkflowStepModel,
    TushareWorkflowStepPageQueryModel,
)
from module_tushare.service.tushare_service import (
    TushareApiConfigService,
    TushareDownloadLogService,
    TushareDownloadTaskService,
    TushareWorkflowConfigService,
    TushareWorkflowStepService,
)
from module_admin.entity.vo.user_vo import CurrentUserModel
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.response_util import ResponseUtil

tushare_controller = APIRouterPro(
    prefix='/tushare', order_num=20, tags=['Tushare数据管理'], dependencies=[PreAuthDependency()]
)


class StockSearchResultModel(BaseModel):
    """
    股票基础信息搜索结果模型（基于 stock_basic 数据）
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    ts_code: str | None = Field(default=None, description='股票代码')
    symbol: str | None = Field(default=None, description='股票简称代码')
    name: str | None = Field(default=None, description='股票名称')
    area: str | None = Field(default=None, description='所在地域')
    industry: str | None = Field(default=None, description='所属行业')
    list_date: str | None = Field(default=None, description='上市日期（YYYYMMDD）')


@tushare_controller.get(
    '/stock/search',
    summary='按关键字搜索股票基础信息接口',
    description='优先从物理表 tushare_stock_basic 中按代码/中文名/英文名模糊搜索股票，若无该表则回退到通用表 tushare_data 中的 stock_basic 数据',
    response_model=DataResponseModel[list[StockSearchResultModel]],
    dependencies=[UserInterfaceAuthDependency('tushare:apiConfig:list')],
)
async def search_stock_basic(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    keyword: Annotated[str, Query(description='代码/中文名/英文名关键字')],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Response:
    """
    优先从物理表 tushare_stock_basic 中查询，
    若该表不存在或查询出错，则回退到通用表 tushare_data 中 api_code = 'stock_basic' 的最新数据。
    """
    from sqlalchemy import desc, select, text

    kw = keyword.strip().lower()
    if not kw:
        return ResponseUtil.success(data=[])

    results: list[StockSearchResultModel] = []

    # 1. 优先尝试从物理表 tushare_stock_basic 查询
    try:
        # 简单检测表是否存在（不同数据库略有差异，这里使用 information_schema）
        from config.env import DataBaseConfig

        if DataBaseConfig.db_type == 'postgresql':
            check_sql = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'tushare_stock_basic'
                )
            """
        else:
            check_sql = """
                SELECT COUNT(*) AS count
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_name = 'tushare_stock_basic'
            """

        check_result = await query_db.execute(text(check_sql))
        table_exists = check_result.scalar()
        if DataBaseConfig.db_type != 'postgresql':
            table_exists = table_exists > 0

        if table_exists:
            # 直接从 tushare_stock_basic 表按代码/名称模糊查询
            search_sql = """
                SELECT ts_code, symbol, name, area, industry, list_date
                FROM tushare_stock_basic
                WHERE LOWER(CONCAT(COALESCE(ts_code, ''), ' ', COALESCE(symbol, ''), ' ', COALESCE(name, ''))) LIKE :kw
                ORDER BY ts_code
                LIMIT :limit
            """
            db_res = await query_db.execute(
                text(search_sql),
                {'kw': f'%{kw}%', 'limit': limit},
            )
            rows = db_res.fetchall()
            for row in rows:
                # row 可能是 Row 对象，按下标或键名访问
                ts_code = str(row[0] or '')
                symbol = str(row[1] or '')
                name = str(row[2] or '')
                results.append(
                    StockSearchResultModel(
                        ts_code=ts_code or None,
                        symbol=symbol or None,
                        name=name or None,
                        area=row[3],
                        industry=row[4],
                        list_date=row[5],
                    )
                )

            if results:
                return ResponseUtil.success(data=results)
    except Exception as e:
        # 表不存在或查询失败时，记录日志并回退到通用表逻辑
        logger.warning(f'从 tushare_stock_basic 查询股票失败，将回退到 tushare_data。错误: {e}')

    # 2. 回退：从通用表 tushare_data 中获取最近的 stock_basic 数据
    stmt = (
        select(TushareData)
        .where(TushareData.api_code == 'stock_basic')
        .order_by(desc(TushareData.download_date), desc(TushareData.data_id))
    ).limit(5000)

    data_rows = (await query_db.execute(stmt)).scalars().all()

    for row in data_rows:
        data_content = row.data_content or {}

        # 正常情况下，每条记录是一行数据的 dict
        if isinstance(data_content, list):
            candidates = data_content
        else:
            candidates = [data_content]

        for item in candidates:
            if not isinstance(item, dict):
                continue

            ts_code = str(item.get('ts_code', '') or '')
            symbol = str(item.get('symbol', '') or '')
            name = str(item.get('name', '') or '')

            text_val = f'{ts_code} {symbol} {name}'.lower()
            if kw in text_val:
                results.append(
                    StockSearchResultModel(
                        ts_code=ts_code or None,
                        symbol=symbol or None,
                        name=name or None,
                        area=item.get('area'),
                        industry=item.get('industry'),
                        list_date=item.get('list_date'),
                    )
                )
                if len(results) >= limit:
                    return ResponseUtil.success(data=results)

    return ResponseUtil.success(data=results)


class StockDailyKlinePointModel(BaseModel):
    """
    股票日线K线点数据模型（基于 tushare_pro_bar 表）
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    ts_code: str | None = Field(default=None, description='股票代码')
    trade_date: str | None = Field(default=None, description='交易日期（YYYYMMDD）')
    open: float | None = Field(default=None, description='开盘价')
    high: float | None = Field(default=None, description='最高价')
    low: float | None = Field(default=None, description='最低价')
    close: float | None = Field(default=None, description='收盘价')
    pct_chg: float | None = Field(default=None, description='涨跌幅')


@tushare_controller.get(
    '/stock/daily',
    summary='按股票和日期区间查询本地日线数据接口',
    description='从本地 tushare_pro_bar 表中，按股票代码和日期范围查询日线K线数据（不直接调用外部Tushare接口）',
    response_model=DataResponseModel[list[StockDailyKlinePointModel]],
    dependencies=[PreAuthDependency()],
)
async def get_stock_daily_kline(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    ts_code: Annotated[str, Query(alias='tsCode', description='股票代码，例如：000001.SZ')],
    start_date: Annotated[str | None, Query(alias='startDate', description='开始日期（YYYYMMDD）')] = None,
    end_date: Annotated[str | None, Query(alias='endDate', description='结束日期（YYYYMMDD）')] = None,
) -> Response:
    """
    使用本地 tushare_pro_bar 表中已下载的日线数据，
    按 ts_code 和日期范围查询，并按 trade_date 正序返回。
    """
    from sqlalchemy import select, func

    # 清理参数：去除前后空格，统一大小写
    ts_code = ts_code.strip() if ts_code else ''
    logger.info(f'查询日线数据：ts_code={repr(ts_code)}, start_date={start_date}, end_date={end_date}')

    # 兼容两种写法：
    # 1. 标准 Tushare 代码：如 000001.SZ -> 精确匹配
    # 2. 只输入数字代码：如 000001、301428 -> 按前缀匹配（000001.%）
    # 显式指定需要的字段，避免选择所有字段时可能出现的字段名问题
    if '.' in ts_code:
        # 精确匹配：去除空格后精确匹配
        stmt = (
            select(
                TushareProBar.ts_code,
                TushareProBar.trade_date,
                TushareProBar.open,
                TushareProBar.high,
                TushareProBar.low,
                TushareProBar.close,
                TushareProBar.pct_chg,
            )
            .where(TushareProBar.ts_code == ts_code)
        )
    else:
        # 前缀匹配：如 001300 -> 匹配 001300.SZ, 001300.SH 等
        like_pattern = f'{ts_code}.%'
        stmt = (
            select(
                TushareProBar.ts_code,
                TushareProBar.trade_date,
                TushareProBar.open,
                TushareProBar.high,
                TushareProBar.low,
                TushareProBar.close,
                TushareProBar.pct_chg,
            )
            .where(TushareProBar.ts_code.like(like_pattern))
        )
    if start_date:
        stmt = stmt.where(TushareProBar.trade_date >= start_date)
    if end_date:
        stmt = stmt.where(TushareProBar.trade_date <= end_date)
    stmt = stmt.order_by(TushareProBar.trade_date)

    result_proxy = await query_db.execute(stmt)
    # 使用 mappings() 得到字典形式行，键为列名，避免 Row 下标/属性取不到 ts_code/trade_date
    rows = result_proxy.mappings().all()
    logger.info(f'查询结果：找到 {len(rows)} 条记录，ts_code={repr(ts_code)}')

    # ========== 详细调试：第一条 RowMapping 的完整信息 ==========
    if rows:
        first_row = rows[0]
        logger.info(f'[调试] 第一条 RowMapping 类型: {type(first_row)}')
        logger.info(f'[调试] 第一条 RowMapping 所有键: {list(first_row.keys())}')
        logger.info(f'[调试] 第一条 RowMapping 所有键值对: {dict(first_row)}')
        logger.info(f'[调试] 第一条 RowMapping values() 顺序: {list(first_row.values())}')
        logger.info(f'[调试] 第一条 RowMapping 键值类型: {[(k, type(v).__name__, repr(v)[:50]) for k, v in first_row.items()]}')

    if not rows and '.' in ts_code:
        logger.warning(f'精确匹配未找到数据，尝试模糊匹配：ts_code={repr(ts_code)}')
        code_prefix = ts_code.split('.')[0]
        like_pattern = f'{code_prefix}.%'
        stmt_fallback = (
            select(
                TushareProBar.ts_code,
                TushareProBar.trade_date,
                TushareProBar.open,
                TushareProBar.high,
                TushareProBar.low,
                TushareProBar.close,
                TushareProBar.pct_chg,
            )
            .where(TushareProBar.ts_code.like(like_pattern))
        )
        if start_date:
            stmt_fallback = stmt_fallback.where(TushareProBar.trade_date >= start_date)
        if end_date:
            stmt_fallback = stmt_fallback.where(TushareProBar.trade_date <= end_date)
        stmt_fallback = stmt_fallback.order_by(TushareProBar.trade_date)
        result_fallback = await query_db.execute(stmt_fallback)
        rows_fallback = result_fallback.mappings().all()
        if rows_fallback:
            logger.info(f'模糊匹配找到 {len(rows_fallback)} 条记录')
            rows = rows_fallback

    # RowMapping 的 values() 顺序可能是键名字母序，不是 select 顺序，故按键名匹配取值
    def _to_str(v):
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if hasattr(v, 'strftime'):  # date/datetime
            return v.strftime('%Y%m%d')
        return str(v)

    def get_by_key(row, key_suffix: str, debug: bool = False):
        """按键名匹配：key 等于 key_suffix 或以 _key_suffix 结尾（如 tushare_pro_bar_ts_code）"""
        matched_key = None
        matched_value = None
        for k, v in row.items():
            if k == key_suffix or (k.endswith('_' + key_suffix) and len(k) > len(key_suffix)):
                matched_key = k
                matched_value = v
                if debug:
                    logger.info(f'[调试] get_by_key("{key_suffix}") 匹配到键: {k}, 值: {repr(v)[:50]}, 类型: {type(v).__name__}')
                return v
        if debug:
            logger.warning(f'[调试] get_by_key("{key_suffix}") 未找到匹配键，可用键: {list(row.keys())}')
        return None

    def row_to_model(row, is_first: bool = False):
        # 第一条记录打印详细调试信息
        ts_code = get_by_key(row, 'ts_code', debug=is_first)
        trade_date = get_by_key(row, 'trade_date', debug=is_first)
        open_ = get_by_key(row, 'open', debug=is_first)
        high = get_by_key(row, 'high', debug=is_first)
        low = get_by_key(row, 'low', debug=is_first)
        close = get_by_key(row, 'close', debug=is_first)
        pct_chg = get_by_key(row, 'pct_chg', debug=is_first)

        if is_first:
            logger.info(f'[调试] 第一条记录提取结果:')
            logger.info(f'  ts_code: {repr(ts_code)} (类型: {type(ts_code).__name__})')
            logger.info(f'  trade_date: {repr(trade_date)} (类型: {type(trade_date).__name__})')
            logger.info(f'  open: {repr(open_)} (类型: {type(open_).__name__})')
            logger.info(f'  high: {repr(high)} (类型: {type(high).__name__})')
            logger.info(f'  low: {repr(low)} (类型: {type(low).__name__})')
            logger.info(f'  close: {repr(close)} (类型: {type(close).__name__})')
            logger.info(f'  pct_chg: {repr(pct_chg)} (类型: {type(pct_chg).__name__})')

        # 转换字符串字段
        ts_code_str = _to_str(ts_code)
        trade_date_str = _to_str(trade_date)
        
        if is_first:
            logger.info(f'[调试] _to_str 转换结果:')
            logger.info(f'  ts_code: {repr(ts_code)} -> {repr(ts_code_str)}')
            logger.info(f'  trade_date: {repr(trade_date)} -> {repr(trade_date_str)}')

        # 创建模型实例：Pydantic v2 在 alias_generator=to_camel 时解析可能只认别名，用 camelCase 键传入
        model_kwargs = {
            'tsCode': ts_code_str,
            'tradeDate': trade_date_str,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'pctChg': pct_chg,
        }
        
        if is_first:
            logger.info(f'[调试] 创建 StockDailyKlinePointModel 的参数 (camelCase):')
            logger.info(f'  {model_kwargs}')

        try:
            model_data = StockDailyKlinePointModel(**model_kwargs)
            if is_first:
                logger.info(f'[调试] 模型创建成功，原始字段值:')
                logger.info(f'  model_data.ts_code = {repr(model_data.ts_code)}')
                logger.info(f'  model_data.trade_date = {repr(model_data.trade_date)}')
        except Exception as e:
            logger.error(f'[调试] 模型创建失败: {e}', exc_info=True)
            raise

        dumped = model_data.model_dump(by_alias=True)

        if is_first:
            logger.info(f'[调试] 第一条记录序列化后 (model_dump by_alias=True):')
            logger.info(f'  {dumped}')
            logger.info(f'[调试] 序列化前模型字段: ts_code={repr(model_data.ts_code)}, trade_date={repr(model_data.trade_date)}')
            logger.info(f'[调试] 序列化后字典: tsCode={repr(dumped.get("tsCode"))}, tradeDate={repr(dumped.get("tradeDate"))}')

        return dumped

    result = [row_to_model(row, is_first=(idx == 0)) for idx, row in enumerate(rows)]

    if result:
        logger.info(f'[调试] 最终返回结果统计: 共 {len(result)} 条')
        logger.info(f'[调试] 第一条最终数据: tsCode={result[0].get("tsCode")}, tradeDate={result[0].get("tradeDate")}')
        logger.info(f'[调试] 第一条完整数据: {result[0]}')
        if len(result) > 1:
            logger.info(f'[调试] 最后一条最终数据: tsCode={result[-1].get("tsCode")}, tradeDate={result[-1].get("tradeDate")}')

    return ResponseUtil.success(data=result)


# ==================== Tushare接口配置管理 ====================

@tushare_controller.get(
    '/apiConfig/list',
    summary='获取Tushare接口配置分页列表接口',
    description='用于获取Tushare接口配置分页列表',
    response_model=PageResponseModel[TushareApiConfigModel],
    dependencies=[UserInterfaceAuthDependency('tushare:apiConfig:list')],
)
async def get_tushare_api_config_list(
    request: Request,
    api_config_page_query: Annotated[TushareApiConfigPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    # 获取分页数据
    api_config_page_query_result = await TushareApiConfigService.get_config_list_services(
        query_db, api_config_page_query, is_page=True
    )
    logger.info('获取成功')

    return ResponseUtil.success(model_content=api_config_page_query_result)


@tushare_controller.post(
    '/apiConfig',
    summary='新增Tushare接口配置接口',
    description='用于新增Tushare接口配置',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:apiConfig:add')],
)
@ValidateFields(validate_model='add_api_config')
@Log(title='Tushare接口配置', business_type=BusinessType.INSERT)
async def add_tushare_api_config(
    request: Request,
    add_api_config: TushareApiConfigModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    add_api_config.create_by = current_user.user.user_name
    add_api_config.create_time = datetime.now()
    add_api_config.update_by = current_user.user.user_name
    add_api_config.update_time = datetime.now()
    add_api_config_result = await TushareApiConfigService.add_config_services(query_db, add_api_config)
    logger.info(add_api_config_result.message)

    return ResponseUtil.success(msg=add_api_config_result.message)


@tushare_controller.put(
    '/apiConfig',
    summary='编辑Tushare接口配置接口',
    description='用于编辑Tushare接口配置',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:apiConfig:edit')],
)
@ValidateFields(validate_model='edit_api_config')
@Log(title='Tushare接口配置', business_type=BusinessType.UPDATE)
async def edit_tushare_api_config(
    request: Request,
    edit_api_config: EditTushareApiConfigModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    # 记录接收到的数据，用于调试
    logger.info(f'接收到的编辑接口配置数据 - config_id: {edit_api_config.config_id}, api_name: {edit_api_config.api_name}, api_code: {edit_api_config.api_code}')
    logger.info(f'完整数据(by_alias=True): {edit_api_config.model_dump(by_alias=True)}')
    logger.info(f'完整数据(by_alias=False): {edit_api_config.model_dump(by_alias=False)}')
    
    # 验证config_id是否存在
    if not edit_api_config.config_id:
        logger.error(f'config_id为空！接收到的数据: {edit_api_config.model_dump(by_alias=True)}')
        return ResponseUtil.failure(msg='接口配置ID不能为空')
    
    edit_api_config.update_by = current_user.user.user_name
    edit_api_config.update_time = datetime.now()
    edit_api_config_result = await TushareApiConfigService.edit_config_services(query_db, edit_api_config)
    logger.info(edit_api_config_result.message)

    return ResponseUtil.success(msg=edit_api_config_result.message)


@tushare_controller.put(
    '/apiConfig/changeStatus',
    summary='修改Tushare接口配置状态接口',
    description='用于修改Tushare接口配置状态',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:apiConfig:changeStatus')],
)
@Log(title='Tushare接口配置', business_type=BusinessType.UPDATE)
async def change_tushare_api_config_status(
    request: Request,
    change_api_config: EditTushareApiConfigModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    edit_api_config = EditTushareApiConfigModel(
        configId=change_api_config.config_id,
        status=change_api_config.status,
        updateBy=current_user.user.user_name,
        updateTime=datetime.now(),
        type='status',
    )
    edit_api_config_result = await TushareApiConfigService.edit_config_services(query_db, edit_api_config)
    logger.info(edit_api_config_result.message)

    return ResponseUtil.success(msg=edit_api_config_result.message)


@tushare_controller.delete(
    '/apiConfig/{config_ids}',
    summary='删除Tushare接口配置接口',
    description='用于删除Tushare接口配置',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:apiConfig:remove')],
)
@Log(title='Tushare接口配置', business_type=BusinessType.DELETE)
async def delete_tushare_api_config(
    request: Request,
    config_ids: Annotated[str, Path(description='需要删除的接口配置ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    delete_api_config = DeleteTushareApiConfigModel(configIds=config_ids)
    delete_api_config_result = await TushareApiConfigService.delete_config_services(query_db, delete_api_config)
    logger.info(delete_api_config_result.message)

    return ResponseUtil.success(msg=delete_api_config_result.message)


@tushare_controller.get(
    '/apiConfig/{config_id}',
    summary='获取Tushare接口配置详情接口',
    description='用于获取指定Tushare接口配置的详情信息',
    response_model=DataResponseModel[TushareApiConfigModel],
    dependencies=[UserInterfaceAuthDependency('tushare:apiConfig:query')],
)
async def query_detail_tushare_api_config(
    request: Request,
    config_id: Annotated[int, Path(description='配置ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    api_config_detail_result = await TushareApiConfigService.config_detail_services(query_db, config_id)
    logger.info(f'获取config_id为{config_id}的信息成功')

    return ResponseUtil.success(data=api_config_detail_result)


@tushare_controller.post(
    '/apiConfig/export',
    summary='导出Tushare接口配置列表接口',
    description='用于导出当前符合查询条件的Tushare接口配置列表数据',
    response_class=StreamingResponse,
    responses={
        200: {
            'description': '流式返回Tushare接口配置列表excel文件',
            'content': {
                'application/octet-stream': {},
            },
        }
    },
    dependencies=[UserInterfaceAuthDependency('tushare:apiConfig:export')],
)
@Log(title='Tushare接口配置', business_type=BusinessType.EXPORT)
async def export_tushare_api_config_list(
    request: Request,
    api_config_page_query: Annotated[TushareApiConfigPageQueryModel, Form()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    # 获取全量数据
    api_config_query_result = await TushareApiConfigService.get_config_list_services(
        query_db, api_config_page_query, is_page=False
    )
    api_config_export_result = await TushareApiConfigService.export_config_list_services(
        request, api_config_query_result
    )
    logger.info('导出成功')

    return ResponseUtil.streaming(data=bytes2file_response(api_config_export_result))


# ==================== Tushare下载任务管理 ====================

@tushare_controller.get(
    '/downloadTask/list',
    summary='获取Tushare下载任务分页列表接口',
    description='用于获取Tushare下载任务分页列表',
    response_model=PageResponseModel[TushareDownloadTaskModel],
    dependencies=[UserInterfaceAuthDependency('tushare:downloadTask:list')],
)
async def get_tushare_download_task_list(
    request: Request,
    download_task_page_query: Annotated[TushareDownloadTaskPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    # 获取分页数据
    download_task_page_query_result = await TushareDownloadTaskService.get_task_list_services(
        query_db, download_task_page_query, is_page=True
    )
    logger.info('获取成功')

    return ResponseUtil.success(model_content=download_task_page_query_result)


@tushare_controller.post(
    '/downloadTask',
    summary='新增Tushare下载任务接口',
    description='用于新增Tushare下载任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:downloadTask:add')],
)
@ValidateFields(validate_model='add_download_task')
@Log(title='Tushare下载任务', business_type=BusinessType.INSERT)
async def add_tushare_download_task(
    request: Request,
    add_download_task: TushareDownloadTaskModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    logger.info(f'[控制器] 接收到新增任务请求')
    logger.info(f'[控制器] 请求数据(by_alias=True): {add_download_task.model_dump(by_alias=True)}')
    logger.info(f'[控制器] 请求数据(by_alias=False): {add_download_task.model_dump(by_alias=False)}')
    logger.info(f'[控制器] task_name值: {add_download_task.task_name}, 类型: {type(add_download_task.task_name)}')
    logger.info(f'[控制器] 模型字段: {list(add_download_task.model_fields.keys())}')
    logger.info(f'[控制器] 模型别名: {[field.alias for field in add_download_task.model_fields.values()]}')
    
    # 验证必要字段 - 如果为空，尝试从原始数据中恢复
    if not add_download_task.task_name:
        logger.error(f'[控制器] task_name为空，尝试从原始数据恢复')
        logger.error(f'[控制器] 完整模型数据: {add_download_task.model_dump(by_alias=False, exclude_none=False)}')
        logger.error(f'[控制器] 完整模型数据(by_alias=True): {add_download_task.model_dump(by_alias=True, exclude_none=False)}')
        
        # 尝试从 by_alias=True 的字典中获取 taskName
        alias_dict = add_download_task.model_dump(by_alias=True, exclude_none=False)
        if 'taskName' in alias_dict and alias_dict['taskName']:
            logger.info(f'[控制器] 从别名字典中找到taskName: {alias_dict["taskName"]}')
            add_download_task.task_name = alias_dict['taskName']
        else:
            logger.error(f'[控制器] 无法找到taskName，拒绝请求')
            return ResponseUtil.error(msg='任务名称不能为空')
    
    add_download_task.create_by = current_user.user.user_name
    add_download_task.create_time = datetime.now()
    add_download_task.update_by = current_user.user.user_name
    add_download_task.update_time = datetime.now()
    
    logger.info(f'[控制器] 设置创建信息后的task_name: {add_download_task.task_name}')
    
    add_download_task_result = await TushareDownloadTaskService.add_task_services(query_db, add_download_task)
    logger.info(add_download_task_result.message)

    return ResponseUtil.success(msg=add_download_task_result.message)


@tushare_controller.put(
    '/downloadTask',
    summary='编辑Tushare下载任务接口',
    description='用于编辑Tushare下载任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:downloadTask:edit')],
)
@ValidateFields(validate_model='edit_download_task')
@Log(title='Tushare下载任务', business_type=BusinessType.UPDATE)
async def edit_tushare_download_task(
    request: Request,
    edit_download_task: EditTushareDownloadTaskModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    logger.info(f'[控制器] 接收到编辑任务请求，task_id: {edit_download_task.task_id}')
    logger.info(f'[控制器] 请求数据: {edit_download_task.model_dump(by_alias=True)}')
    
    edit_download_task.update_by = current_user.user.user_name
    edit_download_task.update_time = datetime.now()
    logger.info(f'[控制器] 设置更新信息: update_by={edit_download_task.update_by}, update_time={edit_download_task.update_time}')
    
    edit_download_task_result = await TushareDownloadTaskService.edit_task_services(query_db, edit_download_task)
    logger.info(f'[控制器] 编辑结果: {edit_download_task_result.message}')

    return ResponseUtil.success(msg=edit_download_task_result.message)


@tushare_controller.put(
    '/downloadTask/changeStatus',
    summary='修改Tushare下载任务状态接口',
    description='用于修改Tushare下载任务状态',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:downloadTask:changeStatus')],
)
@Log(title='Tushare下载任务', business_type=BusinessType.UPDATE)
async def change_tushare_download_task_status(
    request: Request,
    change_download_task: EditTushareDownloadTaskModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    edit_download_task = EditTushareDownloadTaskModel(
        taskId=change_download_task.task_id,
        status=change_download_task.status,
        updateBy=current_user.user.user_name,
        updateTime=datetime.now(),
        type='status',
    )
    edit_download_task_result = await TushareDownloadTaskService.edit_task_services(query_db, edit_download_task)
    logger.info(edit_download_task_result.message)

    return ResponseUtil.success(msg=edit_download_task_result.message)


@tushare_controller.delete(
    '/downloadTask/{task_ids}',
    summary='删除Tushare下载任务接口',
    description='用于删除Tushare下载任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:downloadTask:remove')],
)
@Log(title='Tushare下载任务', business_type=BusinessType.DELETE)
async def delete_tushare_download_task(
    request: Request,
    task_ids: Annotated[str, Path(description='需要删除的下载任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    delete_download_task = DeleteTushareDownloadTaskModel(taskIds=task_ids)
    delete_download_task_result = await TushareDownloadTaskService.delete_task_services(query_db, delete_download_task)
    logger.info(delete_download_task_result.message)

    return ResponseUtil.success(msg=delete_download_task_result.message)


@tushare_controller.get(
    '/downloadTask/{task_id}',
    summary='获取Tushare下载任务详情接口',
    description='用于获取指定Tushare下载任务的详情信息（包含任务类型、关联接口/流程信息）',
    response_model=DataResponseModel[TushareDownloadTaskDetailModel],
    dependencies=[UserInterfaceAuthDependency('tushare:downloadTask:query')],
)
async def query_detail_tushare_download_task(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    download_task_detail_result = await TushareDownloadTaskService.task_detail_services(query_db, task_id)
    logger.info(f'获取task_id为{task_id}的信息成功')

    return ResponseUtil.success(data=download_task_detail_result)


@tushare_controller.post(
    '/downloadTask/execute/{task_id}',
    summary='执行Tushare下载任务接口',
    description='用于手动执行指定的Tushare下载任务',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:downloadTask:execute')],
)
@Log(title='Tushare下载任务', business_type=BusinessType.OTHER)
async def execute_tushare_download_task(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    execute_task_result = await TushareDownloadTaskService.execute_task_services(query_db, task_id)
    logger.info(execute_task_result.message)

    return ResponseUtil.success(msg=execute_task_result.message)


@tushare_controller.get(
    '/downloadTask/statistics/{task_id}',
    summary='获取Tushare下载任务统计信息接口',
    description='用于获取指定任务的执行统计信息（区分单个接口和流程配置）',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:downloadTask:query')],
)
async def get_tushare_download_task_statistics(
    request: Request,
    task_id: Annotated[int, Path(description='任务ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    statistics_result = await TushareDownloadTaskService.get_task_statistics_services(query_db, task_id)
    logger.info(f'获取task_id为{task_id}的统计信息成功')

    return ResponseUtil.success(data=statistics_result)


# ==================== Tushare下载日志管理 ====================

@tushare_controller.get(
    '/downloadLog/list',
    summary='获取Tushare下载日志分页列表接口',
    description='用于获取Tushare下载日志分页列表',
    response_model=PageResponseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:downloadLog:list')],
)
async def get_tushare_download_log_list(
    request: Request,
    download_log_page_query: Annotated[TushareDownloadLogPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    # 获取分页数据
    download_log_page_query_result = await TushareDownloadLogService.get_log_list_services(
        query_db, download_log_page_query, is_page=True
    )
    logger.info('获取成功')

    return ResponseUtil.success(model_content=download_log_page_query_result)


@tushare_controller.delete(
    '/downloadLog/clean',
    summary='清空Tushare下载日志接口',
    description='用于清空所有Tushare下载日志',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:downloadLog:remove')],
)
@Log(title='Tushare下载日志', business_type=BusinessType.CLEAN)
async def clear_tushare_download_log(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    clear_download_log_result = await TushareDownloadLogService.clear_log_services(query_db)
    logger.info(clear_download_log_result.message)

    return ResponseUtil.success(msg=clear_download_log_result.message)


@tushare_controller.delete(
    '/downloadLog/{log_ids}',
    summary='删除Tushare下载日志接口',
    description='用于删除Tushare下载日志',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:downloadLog:remove')],
)
@Log(title='Tushare下载日志', business_type=BusinessType.DELETE)
async def delete_tushare_download_log(
    request: Request,
    log_ids: Annotated[str, Path(description='需要删除的下载日志ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    delete_download_log = DeleteTushareDownloadLogModel(logIds=log_ids)
    delete_download_log_result = await TushareDownloadLogService.delete_log_services(query_db, delete_download_log)
    logger.info(delete_download_log_result.message)

    return ResponseUtil.success(msg=delete_download_log_result.message)


# ==================== Tushare流程配置管理 ====================

@tushare_controller.get(
    '/workflowConfig/list',
    summary='获取Tushare流程配置分页列表接口',
    description='用于获取Tushare流程配置分页列表',
    response_model=PageResponseModel[TushareWorkflowConfigModel],
    dependencies=[UserInterfaceAuthDependency('tushare:workflowConfig:list')],
)
async def get_tushare_workflow_config_list(
    request: Request,
    workflow_config_page_query: Annotated[TushareWorkflowConfigPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    workflow_config_page_query_result = await TushareWorkflowConfigService.get_workflow_list_services(
        query_db, workflow_config_page_query, is_page=True
    )
    logger.info('获取成功')

    return ResponseUtil.success(model_content=workflow_config_page_query_result)


@tushare_controller.post(
    '/workflowConfig',
    summary='新增Tushare流程配置接口',
    description='用于新增Tushare流程配置',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:workflowConfig:add')],
)
@ValidateFields(validate_model='add_workflow_config')
@Log(title='Tushare流程配置', business_type=BusinessType.INSERT)
async def add_tushare_workflow_config(
    request: Request,
    add_workflow_config: TushareWorkflowConfigModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    add_workflow_config.create_by = current_user.user.user_name
    add_workflow_config.create_time = datetime.now()
    add_workflow_config.update_by = current_user.user.user_name
    add_workflow_config.update_time = datetime.now()
    add_workflow_config_result = await TushareWorkflowConfigService.add_workflow_services(query_db, add_workflow_config)
    logger.info(add_workflow_config_result.message)

    return ResponseUtil.success(msg=add_workflow_config_result.message)


@tushare_controller.put(
    '/workflowConfig',
    summary='编辑Tushare流程配置接口',
    description='用于编辑Tushare流程配置',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:workflowConfig:edit')],
)
@ValidateFields(validate_model='edit_workflow_config')
@Log(title='Tushare流程配置', business_type=BusinessType.UPDATE)
async def edit_tushare_workflow_config(
    request: Request,
    edit_workflow_config: EditTushareWorkflowConfigModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    edit_workflow_config.update_by = current_user.user.user_name
    edit_workflow_config.update_time = datetime.now()
    edit_workflow_config_result = await TushareWorkflowConfigService.edit_workflow_services(query_db, edit_workflow_config)
    logger.info(edit_workflow_config_result.message)

    return ResponseUtil.success(msg=edit_workflow_config_result.message)


@tushare_controller.delete(
    '/workflowConfig/{workflow_ids}',
    summary='删除Tushare流程配置接口',
    description='用于删除Tushare流程配置',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:workflowConfig:remove')],
)
@Log(title='Tushare流程配置', business_type=BusinessType.DELETE)
async def delete_tushare_workflow_config(
    request: Request,
    workflow_ids: Annotated[str, Path(description='需要删除的流程配置ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    delete_workflow_config = DeleteTushareWorkflowConfigModel(workflowIds=workflow_ids)
    delete_workflow_config_result = await TushareWorkflowConfigService.delete_workflow_services(
        query_db, delete_workflow_config
    )
    logger.info(delete_workflow_config_result.message)

    return ResponseUtil.success(msg=delete_workflow_config_result.message)


@tushare_controller.get(
    '/workflowConfig/{workflow_id}',
    summary='获取Tushare流程配置详情接口',
    description='用于获取指定Tushare流程配置的详情信息（包含步骤列表）',
    response_model=DataResponseModel[TushareWorkflowConfigWithStepsModel],
    dependencies=[UserInterfaceAuthDependency('tushare:workflowConfig:query')],
)
async def query_detail_tushare_workflow_config(
    request: Request,
    workflow_id: Annotated[int, Path(description='流程配置ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    workflow_config_detail_result = await TushareWorkflowConfigService.workflow_detail_services(query_db, workflow_id)

    return ResponseUtil.success(data=workflow_config_detail_result)


@tushare_controller.get(
    '/workflowConfig/base/{workflow_id}',
    summary='获取Tushare流程配置基础信息接口',
    description='用于获取指定Tushare流程配置的基础信息（不包含步骤列表），主要用于表单编辑回显',
    response_model=DataResponseModel[TushareWorkflowConfigModel],
    dependencies=[UserInterfaceAuthDependency('tushare:workflowConfig:query')],
)
async def query_base_tushare_workflow_config(
    request: Request,
    workflow_id: Annotated[int, Path(description='流程配置ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    """
    获取流程配置基础信息（不包含步骤），用于前端编辑表单回显
    """
    workflow_config_detail_result = await TushareWorkflowConfigService.workflow_base_detail_services(
        query_db, workflow_id
    )

    return ResponseUtil.success(data=workflow_config_detail_result)


# ==================== Tushare流程步骤管理 ====================

@tushare_controller.get(
    '/workflowStep/list',
    summary='获取Tushare流程步骤分页列表接口',
    description='用于获取Tushare流程步骤分页列表',
    response_model=PageResponseModel[TushareWorkflowStepModel],
    dependencies=[UserInterfaceAuthDependency('tushare:workflowStep:list')],
)
async def get_tushare_workflow_step_list(
    request: Request,
    workflow_step_page_query: Annotated[TushareWorkflowStepPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    workflow_step_page_query_result = await TushareWorkflowStepService.get_step_list_services(
        query_db, workflow_step_page_query, is_page=True
    )
    logger.info('获取成功')

    return ResponseUtil.success(model_content=workflow_step_page_query_result)


@tushare_controller.post(
    '/workflowStep',
    summary='新增Tushare流程步骤接口',
    description='用于新增Tushare流程步骤',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:workflowStep:add')],
)
@ValidateFields(validate_model='add_workflow_step')
@Log(title='Tushare流程步骤', business_type=BusinessType.INSERT)
async def add_tushare_workflow_step(
    request: Request,
    add_workflow_step: TushareWorkflowStepModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    add_workflow_step.create_by = current_user.user.user_name
    add_workflow_step.create_time = datetime.now()
    add_workflow_step.update_by = current_user.user.user_name
    add_workflow_step.update_time = datetime.now()
    add_workflow_step_result = await TushareWorkflowStepService.add_step_services(query_db, add_workflow_step)
    logger.info(add_workflow_step_result.message)

    return ResponseUtil.success(msg=add_workflow_step_result.message)


@tushare_controller.put(
    '/workflowStep',
    summary='编辑Tushare流程步骤接口',
    description='用于编辑Tushare流程步骤',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:workflowStep:edit')],
)
@ValidateFields(validate_model='edit_workflow_step')
@Log(title='Tushare流程步骤', business_type=BusinessType.UPDATE)
async def edit_tushare_workflow_step(
    request: Request,
    edit_workflow_step: EditTushareWorkflowStepModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    edit_workflow_step.update_by = current_user.user.user_name
    edit_workflow_step.update_time = datetime.now()
    edit_workflow_step_result = await TushareWorkflowStepService.edit_step_services(query_db, edit_workflow_step)
    logger.info(edit_workflow_step_result.message)

    return ResponseUtil.success(msg=edit_workflow_step_result.message)


@tushare_controller.delete(
    '/workflowStep/{step_ids}',
    summary='删除Tushare流程步骤接口',
    description='用于删除Tushare流程步骤',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:workflowStep:remove')],
)
@Log(title='Tushare流程步骤', business_type=BusinessType.DELETE)
async def delete_tushare_workflow_step(
    request: Request,
    step_ids: Annotated[str, Path(description='需要删除的流程步骤ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    delete_workflow_step = DeleteTushareWorkflowStepModel(stepIds=step_ids)
    delete_workflow_step_result = await TushareWorkflowStepService.delete_step_services(query_db, delete_workflow_step)
    logger.info(delete_workflow_step_result.message)

    return ResponseUtil.success(msg=delete_workflow_step_result.message)


@tushare_controller.post(
    '/workflowStep/batch',
    summary='批量保存Tushare流程步骤接口',
    description='用于批量创建、更新、删除流程步骤',
    response_model=ResponseBaseModel,
    dependencies=[UserInterfaceAuthDependency('tushare:workflowStep:edit')],
)
@Log(title='Tushare流程步骤', business_type=BusinessType.UPDATE)
async def batch_save_workflow_steps(
    request: Request,
    batch_data: BatchSaveWorkflowStepModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
) -> Response:
    batch_save_result = await TushareWorkflowStepService.batch_save_step_services(
        query_db, batch_data, current_user.user.user_name
    )
    logger.info(batch_save_result.message)

    return ResponseUtil.success(msg=batch_save_result.message)
