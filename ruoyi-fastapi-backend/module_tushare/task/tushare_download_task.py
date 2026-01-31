import json
import os
import re
import traceback
from datetime import datetime, timedelta
from itertools import product
from typing import Any

import pandas as pd
import tushare as ts
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal
from config.env import DataBaseConfig, TushareConfig
from module_tushare.dao.tushare_dao import (
    TushareApiConfigDao,
    TushareDataDao,
    TushareDownloadLogDao,
    TushareDownloadRunDao,
    TushareDownloadTaskDao,
    TushareWorkflowConfigDao,
    TushareWorkflowStepDao,
)
from module_tushare.entity.do.tushare_do import TushareData, TushareDownloadLog
from module_tushare.entity.vo.tushare_vo import TushareDownloadTaskModel
from utils.log_util import logger


def pandas_dtype_to_db_type(dtype, db_type: str = 'postgresql') -> str:
    """
    将 pandas 数据类型转换为数据库类型

    :param dtype: pandas 数据类型
    :param db_type: 数据库类型 ('postgresql' 或 'mysql')
    :return: 数据库类型字符串
    """
    import pandas as pd
    import numpy as np
    
    dtype_str = str(dtype)
    
    # 整数类型
    if pd.api.types.is_integer_dtype(dtype):
        if 'int64' in dtype_str or 'Int64' in dtype_str:
            return 'BIGINT' if db_type == 'postgresql' else 'BIGINT'
        elif 'int32' in dtype_str or 'Int32' in dtype_str:
            return 'INTEGER' if db_type == 'postgresql' else 'INT'
        elif 'int16' in dtype_str or 'Int16' in dtype_str:
            return 'SMALLINT' if db_type == 'postgresql' else 'SMALLINT'
        else:
            return 'INTEGER' if db_type == 'postgresql' else 'INT'
    
    # 浮点数类型
    elif pd.api.types.is_float_dtype(dtype):
        if 'float64' in dtype_str or 'Float64' in dtype_str:
            return 'DOUBLE PRECISION' if db_type == 'postgresql' else 'DOUBLE'
        elif 'float32' in dtype_str or 'Float32' in dtype_str:
            return 'REAL' if db_type == 'postgresql' else 'FLOAT'
        else:
            return 'DOUBLE PRECISION' if db_type == 'postgresql' else 'DOUBLE'
    
    # 布尔类型
    elif pd.api.types.is_bool_dtype(dtype):
        return 'BOOLEAN' if db_type == 'postgresql' else 'TINYINT(1)'
    
    # 日期时间类型
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return 'TIMESTAMP(0)' if db_type == 'postgresql' else 'DATETIME'
    
    # 日期类型（pandas 中没有单独的日期类型，通常使用 datetime64）
    # 注意：pandas 的 is_date_dtype 在新版本中已移除，这里通过检查是否为 datetime64[ns] 的日期部分来判断
    # 实际上，pandas 中日期通常存储为 datetime64，所以这里可以省略
    
    # 字符串类型
    elif pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
        # 默认使用 VARCHAR，可以根据实际数据长度调整
        return 'VARCHAR(500)' if db_type == 'postgresql' else 'VARCHAR(500)'
    
    # 默认返回文本类型
    else:
        return 'TEXT' if db_type == 'postgresql' else 'TEXT'


async def ensure_table_exists(session: AsyncSession, table_name: str, api_code: str, df: pd.DataFrame | None = None, config=None, primary_key_fields_str: str | None = None) -> None:
    """
    确保表存在，如果不存在则根据 DataFrame 结构创建

    :param session: 数据库会话
    :param table_name: 表名
    :param api_code: 接口代码（用于注释）
    :param df: DataFrame，用于确定表结构
    :param config: 接口配置对象（可选，用于向后兼容，但优先使用 primary_key_fields_str）
    :param primary_key_fields_str: 主键字段JSON字符串（可选，优先使用此参数避免访问 config 对象）
    :return: None
    """
    import re
    
    # 验证表名，只允许字母、数字和下划线
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        raise ValueError(f'无效的表名: {table_name}')
    
    # 检查表是否存在
    if DataBaseConfig.db_type == 'postgresql':
        check_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
            )
        """
        # PostgreSQL 表名和索引名需要用双引号转义
        table_name_escaped = f'"{table_name}"'
    else:
        check_sql = """
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = DATABASE()
            AND table_name = :table_name
        """
        # MySQL 表名和索引名需要用反引号转义
        table_name_escaped = f'`{table_name}`'
    
    result = await session.execute(text(check_sql), {'table_name': table_name})
    
    if DataBaseConfig.db_type == 'postgresql':
        table_exists = result.scalar()
    else:
        table_exists = result.scalar() > 0
    
    if not table_exists:
        if df is None or df.empty:
            raise ValueError(f'无法创建表 {table_name}：DataFrame 为空，无法确定表结构')
        
        # 解析接口配置的主键字段
        # 优先使用传入的 primary_key_fields_str，避免访问 config 对象导致延迟加载
        primary_key_fields = None
        if primary_key_fields_str:
            try:
                primary_key_fields = json.loads(primary_key_fields_str)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f'解析主键字段字符串失败: {e}，将使用默认 data_id 主键')
                primary_key_fields = None
        
        # 如果 primary_key_fields_str 为空，尝试从 config 对象获取（向后兼容，但可能触发延迟加载）
        if not primary_key_fields and config and hasattr(config, 'primary_key_fields') and config.primary_key_fields:
            try:
                primary_key_fields = json.loads(config.primary_key_fields)
                if not isinstance(primary_key_fields, list) or len(primary_key_fields) == 0:
                    primary_key_fields = None
                else:
                    # 验证主键字段是否在 DataFrame 中
                    df_columns_lower = [str(col).lower() for col in df.columns]
                    valid_pk_fields = []
                    for pk_field in primary_key_fields:
                        # 检查原始列名或安全列名
                        safe_pk_field = re.sub(r'[^a-zA-Z0-9_]', '_', str(pk_field))
                        if pk_field in df.columns or safe_pk_field in df_columns_lower:
                            valid_pk_fields.append(safe_pk_field)
                        else:
                            logger.warning(f'主键字段 {pk_field} 不在 DataFrame 列中，将忽略。可用列: {list(df.columns)}')
                    if valid_pk_fields:
                        primary_key_fields = valid_pk_fields
                    else:
                        logger.warning(f'接口配置的主键字段都不在 DataFrame 中，将使用默认 data_id 主键')
                        primary_key_fields = None
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f'解析接口配置的主键字段失败: {e}，将使用默认 data_id 主键')
                primary_key_fields = None
        
        # 根据 DataFrame 的列和数据类型创建表结构
        columns = []
        primary_key_columns = []
        
        # 如果配置了主键字段，不创建 data_id 作为主键，否则创建
        if primary_key_fields:
            # 创建 data_id 但不设为主键（用于兼容性）
            if DataBaseConfig.db_type == 'postgresql':
                columns.append('data_id BIGSERIAL NOT NULL')
            else:
                columns.append('data_id BIGINT NOT NULL AUTO_INCREMENT')
        else:
            # 使用默认主键
            if DataBaseConfig.db_type == 'postgresql':
                columns.append('data_id BIGSERIAL NOT NULL PRIMARY KEY')
            else:
                columns.append('data_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY')
        
        columns.append('task_id BIGINT NOT NULL')
        columns.append('config_id BIGINT NOT NULL')
        columns.append('api_code VARCHAR(100) NOT NULL')
        columns.append('download_date VARCHAR(20)')
        columns.append('create_time TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP' if DataBaseConfig.db_type == 'postgresql' else 'create_time DATETIME DEFAULT CURRENT_TIMESTAMP')
        
        # 添加 DataFrame 的列，并收集主键字段
        col_mapping = {}  # 原始列名 -> 安全列名的映射
        for col_name in df.columns:
            # 验证列名，只允许字母、数字和下划线
            safe_col_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(col_name))
            if not safe_col_name or safe_col_name[0].isdigit():
                safe_col_name = f'col_{safe_col_name}'
            
            col_mapping[col_name] = safe_col_name
            
            # 获取列的数据类型
            col_dtype = df[col_name].dtype
            db_type_str = pandas_dtype_to_db_type(col_dtype, DataBaseConfig.db_type)
            
            # 检查是否为主键字段
            is_primary_key = False
            if primary_key_fields and safe_col_name in primary_key_fields:
                is_primary_key = True
                # 主键字段不能为 NULL
                if DataBaseConfig.db_type == 'postgresql':
                    col_def = f'"{safe_col_name}" {db_type_str} NOT NULL'
                else:
                    col_def = f'`{safe_col_name}` {db_type_str} NOT NULL'
                primary_key_columns.append(safe_col_name)
            else:
                # PostgreSQL 需要转义列名
                if DataBaseConfig.db_type == 'postgresql':
                    col_def = f'"{safe_col_name}" {db_type_str}'
                else:
                    col_def = f'`{safe_col_name}` {db_type_str}'
            
            columns.append(col_def)
        
        # 生成简短的索引名称（避免名称过长）
        idx_suffix = table_name[-20:] if len(table_name) > 20 else table_name
        # 生成简短的索引名称（避免名称过长）
        idx_suffix = table_name[-20:] if len(table_name) > 20 else table_name
        
        # 创建表（PostgreSQL 需要分开执行多个 SQL 语句）
        if DataBaseConfig.db_type == 'postgresql':
            # 如果有配置的主键字段，添加主键约束
            if primary_key_fields and primary_key_columns:
                pk_cols_escaped = ', '.join([f'"{col}"' for col in primary_key_columns])
                columns.append(f'PRIMARY KEY ({pk_cols_escaped})')
            
            # 创建表
            create_table_sql = f"CREATE TABLE {table_name_escaped} (\n    " + ",\n    ".join(columns) + "\n)"
            await session.execute(text(create_table_sql))
            await session.flush()
            
            # 创建索引（分开执行）
            index_sqls = [
                f'CREATE INDEX idx_tid_{idx_suffix} ON {table_name_escaped}(task_id)',
                f'CREATE INDEX idx_cid_{idx_suffix} ON {table_name_escaped}(config_id)',
                f'CREATE INDEX idx_ac_{idx_suffix} ON {table_name_escaped}(api_code)',
                f'CREATE INDEX idx_dd_{idx_suffix} ON {table_name_escaped}(download_date)',
                f'CREATE INDEX idx_ct_{idx_suffix} ON {table_name_escaped}(create_time)',
            ]
            
            for index_sql in index_sqls:
                await session.execute(text(index_sql))
                await session.flush()
            
            # 添加注释（分开执行）
            comment_sqls = [
                f"COMMENT ON TABLE {table_name_escaped} IS 'Tushare数据存储表（{api_code}）'",
                f"COMMENT ON COLUMN {table_name_escaped}.data_id IS '数据ID'",
                f"COMMENT ON COLUMN {table_name_escaped}.task_id IS '任务ID'",
                f"COMMENT ON COLUMN {table_name_escaped}.config_id IS '接口配置ID'",
                f"COMMENT ON COLUMN {table_name_escaped}.api_code IS '接口代码'",
                f"COMMENT ON COLUMN {table_name_escaped}.download_date IS '下载日期（YYYYMMDD）'",
                f"COMMENT ON COLUMN {table_name_escaped}.create_time IS '创建时间'",
            ]
            
            # 为 DataFrame 的列添加注释
            for col_name in df.columns:
                safe_col_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(col_name))
                if not safe_col_name or safe_col_name[0].isdigit():
                    safe_col_name = f'col_{safe_col_name}'
                comment_sqls.append(f"COMMENT ON COLUMN {table_name_escaped}.\"{safe_col_name}\" IS '{col_name}'")
            
            for comment_sql in comment_sqls:
                await session.execute(text(comment_sql))
                await session.flush()
        else:
            # MySQL 可以在一个语句中执行
            # 如果有配置的主键字段，添加主键约束
            if primary_key_fields and primary_key_columns:
                pk_cols_escaped = ', '.join([f'`{col}`' for col in primary_key_columns])
                columns.append(f'PRIMARY KEY ({pk_cols_escaped})')
            
            # 创建索引定义
            index_defs = [
                f'INDEX idx_tid_{idx_suffix} (task_id)',
                f'INDEX idx_cid_{idx_suffix} (config_id)',
                f'INDEX idx_ac_{idx_suffix} (api_code)',
                f'INDEX idx_dd_{idx_suffix} (download_date)',
                f'INDEX idx_ct_{idx_suffix} (create_time)',
            ]
            
            create_sql = f"CREATE TABLE {table_name_escaped} (\n    " + ",\n    ".join(columns + index_defs) + f"\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Tushare数据存储表（{api_code}）';"
            await session.execute(text(create_sql))
            await session.flush()
        
        if primary_key_fields and primary_key_columns:
            logger.info(f'已创建数据表: {table_name}，包含 {len(df.columns)} 个数据列，主键字段: {primary_key_columns}')
        else:
            logger.info(f'已创建数据表: {table_name}，包含 {len(df.columns)} 个数据列，使用默认 data_id 主键')


async def execute_single_api(session: AsyncSession, task, download_date: str) -> None:
    """
    执行单个接口下载

    :param session: 数据库会话
    :param task: 任务对象
    :param download_date: 下载日期
    :return: None
    """
    start_time = datetime.now()
    
    # 提前提取 task 对象的所有属性，避免在 commit 后访问 ORM 对象导致延迟加载问题
    try:
        await session.refresh(task)
    except Exception as refresh_error:
        logger.debug(f'刷新任务对象时出错（可能对象未过期）: {refresh_error}')
    
    # 直接从对象的 __dict__ 中提取属性，避免触发任何延迟加载
    task_dict = task.__dict__.copy()
    task_dict.pop('_sa_instance_state', None)
    
    # 提取需要的 task 属性
    task_name = task_dict.get('task_name') or '未知任务'
    task_task_id = task_dict.get('task_id')
    task_config_id = task_dict.get('config_id')
    task_save_to_db = task_dict.get('save_to_db', '0') or '0'
    task_data_table_name = task_dict.get('data_table_name')
    task_save_path = task_dict.get('save_path')
    task_save_format = task_dict.get('save_format')
    task_task_params = task_dict.get('task_params')
    task_run_count = task_dict.get('run_count', 0) or 0
    task_success_count = task_dict.get('success_count', 0) or 0
    
    config = await TushareApiConfigDao.get_config_detail_by_id(session, task_config_id)
    if not config:
        logger.error(f'接口配置ID {task_config_id} 不存在')
        return

    # 立即提取 config 的所有属性，避免在 commit 后访问 ORM 对象导致延迟加载
    config_dict = config.__dict__.copy()
    config_dict.pop('_sa_instance_state', None)
    config_status = config_dict.get('status', '0') or '0'
    config_api_name = config_dict.get('api_name') or '未知接口'
    config_api_code = config_dict.get('api_code') or ''
    config_api_params = config_dict.get('api_params')
    config_config_id = config_dict.get('config_id')
    config_data_fields = config_dict.get('data_fields')
    config_primary_key_fields = config_dict.get('primary_key_fields')

    if config_status != '0':
        logger.warning(f'接口配置 {config_api_name} 已停用')
        return

    # 解析参数
    api_params = {}
    if config_api_params:
        api_params = json.loads(config_api_params)

    # 任务参数覆盖接口默认参数
    if task_task_params:
        try:
            task_params = json.loads(task_task_params)
            if isinstance(task_params, dict):
                api_params.update(task_params)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f'任务 {task_name} 任务参数解析失败: {e}，将跳过任务参数')

    # 注意：不再自动添加日期参数，所有参数必须从配置中获取
    # 如果需要在参数中使用日期，请在接口配置或步骤参数中明确指定

    # 创建运行记录（PENDING -> RUNNING）
    # 注意：这里立即缓存 run_id，后续不再访问 ORM 对象属性，避免在 commit 之后触发延迟加载
    run_record = await TushareDownloadRunDao.create_run_record(session, task, initial_status='PENDING')
    run_id = run_record.run_id
    await TushareDownloadRunDao.update_run_status(
        session,
        run_id,
        status='RUNNING',
        set_start_time=True,
    )

    # 调用tushare接口
    logger.info(f'开始下载任务: {task_name}, 接口: {config_api_code}, 参数: {api_params}')

    # 获取tushare pro接口
    ts_token = TushareConfig.tushare_token or os.getenv('TUSHARE_TOKEN', '')
    if not ts_token:
        raise ValueError(
            'TUSHARE_TOKEN未设置，请在.env.dev文件中配置TUSHARE_TOKEN环境变量。'
            '例如：TUSHARE_TOKEN=your_tushare_token_here'
        )

    pro = ts.pro_api(ts_token)

    # 动态调用接口
    # 某些接口（如 pro_bar）是 ts 模块的函数，不是 pro 对象的方法
    api_func = getattr(pro, config_api_code, None)
    if not api_func:
        # 尝试从 ts 模块获取（如 pro_bar）
        api_func = getattr(ts, config_api_code, None)
        if not api_func:
            raise ValueError(f'接口 {config_api_code} 不存在（在 pro 对象和 ts 模块中都未找到）')

    # 调用接口获取数据
    try:
        df = api_func(**api_params)
    except Exception as api_error:
        error_detail = f'Tushare接口调用失败: {str(api_error)}\n参数: {api_params}'
        logger.exception(f'任务 {task_name} Tushare接口调用异常: {error_detail}')
        # 更新运行记录为 FAILED
        await TushareDownloadRunDao.update_run_status(
            session,
            run_record.run_id,
            status='FAILED',
            error_message=error_detail,
            set_end_time=True,
        )
        # 更新任务统计
        await TushareDownloadTaskDao.edit_task_dao(
            session,
            task_task_id,
            {
                'run_count': task_run_count + 1,
                'fail_count': (task.fail_count or 0) + 1,
                'last_run_time': datetime.now(),
            },
        )
        await session.commit()
        return

    if df is None or df.empty:
        logger.warning(f'任务 {task_name} 下载数据为空')
        record_count = 0
        file_path = None
    else:
        record_count = len(df)

        # 如果指定了数据字段，只保留指定字段
        # 使用提前提取的 config_data_fields，避免在 commit 后访问 ORM 对象导致延迟加载
        if config_data_fields:
            data_fields = json.loads(config_data_fields)
            if isinstance(data_fields, list):
                available_fields = [field for field in data_fields if field in df.columns]
                if available_fields:
                    df = df[available_fields]

        # 保存到数据库（如果启用）
        if task_save_to_db == '1':
            try:
                table_name = task_data_table_name if task_data_table_name and task_data_table_name.strip() else None
                if not table_name:
                    table_name = f'tushare_{config_api_code}'

                await ensure_table_exists(session, table_name, config_api_code, df, config)

                # 获取唯一键字段（优先级：如果表已存在且接口配置的主键字段也有，则优先使用接口配置 > 表实际主键 > 接口配置 > 自动检测）
                unique_key_fields = await TushareDataDao.get_unique_key_fields(
                    session, table_name, config=config, step_unique_key_fields=None
                )

                inserted_count = await TushareDataDao.add_dataframe_to_table_dao(
                    session, table_name, df, task_task_id, config_config_id, config_api_code, download_date,
                    update_mode='0', unique_key_fields=unique_key_fields, config=config
                )
                logger.info(f'已保存 {inserted_count} 条数据到数据库表 {table_name}')
            except Exception as db_error:
                error_detail = f'保存数据到数据库失败: {str(db_error)}'
                logger.exception(f'任务 {task_name} 保存数据到数据库异常: {error_detail}')
                # 更新运行记录为 FAILED
                await TushareDownloadRunDao.update_run_status(
                    session,
                    run_record.run_id,
                    status='FAILED',
                    error_message=error_detail,
                    set_end_time=True,
                )
                # 更新任务统计
                await TushareDownloadTaskDao.edit_task_dao(
                    session,
                    task_task_id,
                    {
                        'run_count': task_run_count + 1,
                        'fail_count': (task.fail_count or 0) + 1,
                        'last_run_time': datetime.now(),
                    },
                )
                await session.commit()
                return

        # 保存到文件（如果配置了保存路径）
        file_path = None
        if task_save_path:
            try:
                save_path = task_save_path
                os.makedirs(save_path, exist_ok=True)
                file_name = f"{config_api_code}_{download_date}_{datetime.now().strftime('%H%M%S')}"
                save_format = task_save_format or 'csv'

                if save_format == 'csv':
                    file_path = os.path.join(save_path, f'{file_name}.csv')
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')
                elif save_format == 'excel':
                    file_path = os.path.join(save_path, f'{file_name}.xlsx')
                    df.to_excel(file_path, index=False, engine='openpyxl')
                elif save_format == 'json':
                    file_path = os.path.join(save_path, f'{file_name}.json')
                    df.to_json(file_path, orient='records', force_ascii=False, indent=2)
                else:
                    file_path = os.path.join(save_path, f'{file_name}.csv')
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')

                logger.info(f'数据已保存到文件: {file_path}')
            except Exception as file_error:
                error_detail = f'保存数据到文件失败: {str(file_error)}'
                logger.exception(f'任务 {task_name} 保存数据到文件异常: {error_detail}')
                raise Exception(error_detail) from file_error

    # 计算执行时长
    duration = int((datetime.now() - start_time).total_seconds())

    # 创建下载日志
    # 使用提前提取的 config 和 task 属性，避免在 commit 后访问 ORM 对象导致延迟加载
    log = TushareDownloadLog(
        task_id=task_task_id,
        task_name=task_name,
        config_id=config_config_id,
        api_name=config_api_name,
        download_date=download_date,
        record_count=record_count,
        file_path=file_path,
        status='0',
        duration=duration,
        create_time=datetime.now(),
    )

    await TushareDownloadLogDao.add_log_dao(session, log)

    # 更新运行记录为 SUCCESS
    await TushareDownloadRunDao.update_run_status(
        session,
        run_record.run_id,
        status='SUCCESS',
        total_records=record_count,
        success_records=record_count,
        set_end_time=True,
    )

    # 更新任务统计（使用字典方式，避免被排除列表影响）
    update_stats_dict = {
        'run_count': task_run_count + 1,
        'success_count': task_success_count + 1,
        'last_run_time': datetime.now()
    }
    await TushareDownloadTaskDao.edit_task_dao(session, task_task_id, update_stats_dict)

    await session.commit()
    logger.info(f'任务 {task_name} 执行成功，记录数: {record_count}, 耗时: {duration}秒')


def evaluate_date_expression(expr: str, base_date: datetime | None = None) -> str | None:
    """
    评估日期表达式，返回 YYYYMMDD 格式的日期字符串
    
    支持的表达式：
    - today: 当天
    - today+N: N天后（如 today+1 表示明天）
    - today-N: N天前（如 today-1 表示昨天）
    
    :param expr: 日期表达式字符串
    :param base_date: 基准日期（默认为当前日期）
    :return: YYYYMMDD 格式的日期字符串，如果不是日期表达式则返回 None
    """
    if not isinstance(expr, str):
        return None
    
    # 去除首尾空格并转换为小写
    expr = expr.strip().lower()
    
    # 匹配日期表达式模式：today 或 today+N 或 today-N
    pattern = r'^today([+-]\d+)?$'
    match = re.match(pattern, expr)
    
    if not match:
        return None
    
    # 如果没有提供基准日期，使用当前日期
    if base_date is None:
        base_date = datetime.now()
    
    # 提取偏移天数
    offset_str = match.group(1) if match.group(1) else ''
    if offset_str:
        # 解析偏移量（+1, -1, +7, -30 等）
        offset_days = int(offset_str)
    else:
        offset_days = 0
    
    # 计算目标日期
    target_date = base_date + timedelta(days=offset_days)
    
    # 格式化为 YYYYMMDD
    return target_date.strftime('%Y%m%d')


def parse_step_params(step_params: dict, previous_results: dict, loop_mode: bool) -> dict:
    """
    解析步骤参数，识别参数类型（固定值/变量/遍历变量）
    
    :param step_params: 步骤参数字典
    :param previous_results: 前一步的结果数据
    :param loop_mode: 是否开启遍历模式
    :return: 参数配置字典，格式为：
        {
            'param_name': {
                'type': 'fixed' | 'variable' | 'loop',
                'value': ... 或 'source': 'step_name.field'
            }
        }
    """
    param_config = {}
    
    for key, value in step_params.items():
        # 如果是对象格式，检查是否有 type 字段
        if isinstance(value, dict) and 'type' in value:
            param_type = value.get('type')
            if param_type == 'loop':
                # 遍历变量
                source = value.get('source', '')
                param_config[key] = {
                    'type': 'loop',
                    'source': source
                }
            elif param_type == 'fixed':
                # 固定值
                fixed_value = value.get('value')
                # 检查是否为日期表达式并计算
                date_result = evaluate_date_expression(fixed_value) if isinstance(fixed_value, str) else None
                param_config[key] = {
                    'type': 'fixed',
                    'value': date_result if date_result is not None else fixed_value
                }
            elif param_type == 'variable':
                # 变量（第一条记录）
                source = value.get('source', '')
                param_config[key] = {
                    'type': 'variable',
                    'source': source
                }
            else:
                # 未知类型，作为固定值处理
                param_config[key] = {
                    'type': 'fixed',
                    'value': value
                }
        # 如果是字符串且以 ${ 开头，} 结尾，是变量格式
        elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            expr = value[2:-1]
            if loop_mode:
                # 遍历模式下，自动转换为遍历变量
                param_config[key] = {
                    'type': 'loop',
                    'source': expr
                }
            else:
                # 非遍历模式，作为变量（第一条记录）
                param_config[key] = {
                    'type': 'variable',
                    'source': expr
                }
        else:
            # 其他情况作为固定值
            # 检查是否为日期表达式并计算
            date_result = evaluate_date_expression(value) if isinstance(value, str) else None
            param_config[key] = {
                'type': 'fixed',
                'value': date_result if date_result is not None else value
            }
    
    return param_config


def sanitize_dict_values(data: Any) -> Any:
    """
    清理字典值，确保所有值都是基本类型（str, int, float, bool, None, datetime）
    避免在序列化或访问时触发 SQLAlchemy ORM 对象的延迟加载
    
    :param data: 需要清理的数据（可以是字典、列表或基本类型）
    :return: 清理后的数据，所有值都是基本类型
    """
    # 基本类型直接返回
    if data is None:
        return None
    if isinstance(data, (str, int, float, bool)):
        return data
    
    # 处理 numpy 和 pandas 的特殊类型
    try:
        import numpy as np
        if isinstance(data, (np.integer, np.floating)):
            # numpy 整数和浮点数转换为 Python 基本类型
            return data.item() if hasattr(data, 'item') else int(data) if isinstance(data, np.integer) else float(data)
        if isinstance(data, np.bool_):
            return bool(data)
    except ImportError:
        pass
    
    # 处理 datetime 对象（包括 pandas Timestamp）
    if isinstance(data, datetime):
        return data.isoformat() if hasattr(data, 'isoformat') else str(data)
    
    # 处理 pandas Timestamp
    try:
        import pandas as pd
        if isinstance(data, pd.Timestamp):
            return data.isoformat()
    except (ImportError, AttributeError):
        pass
    
    # 处理字典
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # 跳过 SQLAlchemy 内部属性
            if key == '_sa_instance_state':
                continue
            sanitized[key] = sanitize_dict_values(value)
        return sanitized
    
    # 处理列表
    if isinstance(data, list):
        return [sanitize_dict_values(item) for item in data]
    
    # 处理可能的 ORM 对象
    if hasattr(data, '_sa_instance_state'):
        # 如果是 ORM 对象，尝试提取主键或字符串表示
        # 但为了避免触发延迟加载，直接返回字符串表示
        try:
            # 尝试获取主键
            state = data._sa_instance_state
            if hasattr(state, 'key') and state.key:
                # 如果有主键，返回主键值
                pk_value = state.key[1] if isinstance(state.key, tuple) else state.key
                return sanitize_dict_values(pk_value)
        except Exception:
            pass
        # 如果无法获取主键，返回字符串表示（但不访问属性，避免触发延迟加载）
        return f'<ORM Object: {type(data).__name__}>'
    
    # 其他类型，尝试转换为字符串
    try:
        return str(data)
    except Exception:
        return '<Unserializable Object>'


def generate_param_combinations(param_config: dict, previous_results: dict, previous_step_name: str = None) -> list[dict]:
    """
    生成所有参数组合（笛卡尔积）
    
    :param param_config: 参数配置字典（来自 parse_step_params）
    :param previous_results: 前一步的结果数据
    :param previous_step_name: 前一步的步骤名，用于解析 previous_step 占位符
    :return: 参数组合列表，例如：[{'ts_code': '000001.SZ', 'trade_date': '20240101'}, ...]
    """
    # 收集所有参数的值列表
    param_values = {}
    loop_params = []
    
    for param_name, config in param_config.items():
        param_type = config.get('type')
        
        if param_type == 'loop':
            # 遍历变量：从前一步结果中提取所有值
            source = config.get('source', '')
            
            # 支持 previous_step 占位符，自动替换为前一步的实际步骤名
            if previous_step_name and source.startswith('previous_step'):
                if source == 'previous_step':
                    # 如果只是 previous_step，替换为前一步步骤名
                    source = previous_step_name
                elif source.startswith('previous_step.'):
                    # 如果是 previous_step.field，替换为 前一步步骤名.field
                    field = source[len('previous_step.'):]
                    source = f'{previous_step_name}.{field}'
            
            values = []
            
            if '.' in source:
                step_name, field = source.split('.', 1)
                # 从前一步的结果列表中提取所有记录的该字段值
                if step_name in previous_results:
                    records = previous_results[step_name]
                    if isinstance(records, list):
                        if len(records) == 0:
                            logger.warning(f'参数 {param_name} (遍历变量, source: {source}): 前一步 {step_name} 的结果列表为空')
                        else:
                            found_count = 0
                            for record in records:
                                if isinstance(record, dict) and field in record:
                                    value = record[field]
                                    # 检查是否为日期表达式并计算
                                    if isinstance(value, str):
                                        date_result = evaluate_date_expression(value)
                                        if date_result is not None:
                                            value = date_result
                                    if value not in values:  # 去重
                                        values.append(value)
                                    found_count += 1
                            if found_count == 0:
                                logger.warning(f'参数 {param_name} (遍历变量, source: {source}): 前一步 {step_name} 的 {len(records)} 条记录中都没有字段 {field}，可用字段: {list(records[0].keys()) if records and isinstance(records[0], dict) else "N/A"}')
                    else:
                        logger.warning(f'参数 {param_name} (遍历变量, source: {source}): 前一步 {step_name} 的结果不是列表类型: {type(records)}')
                else:
                    available_steps = list(previous_results.keys())
                    logger.warning(f'参数 {param_name} (遍历变量, source: {source}): 前一步结果中找不到步骤 {step_name}，可用步骤: {available_steps}')
            else:
                # 如果没有点号，尝试直接从前一步结果中获取
                if source in previous_results:
                    result = previous_results[source]
                    if isinstance(result, list):
                        # 对列表中的每个值检查日期表达式
                        values = []
                        for item in result:
                            if isinstance(item, str):
                                date_result = evaluate_date_expression(item)
                                values.append(date_result if date_result is not None else item)
                            else:
                                values.append(item)
                    else:
                        # 单个值，检查日期表达式
                        if isinstance(result, str):
                            date_result = evaluate_date_expression(result)
                            values = [date_result if date_result is not None else result]
                        else:
                            values = [result]
                else:
                    available_keys = list(previous_results.keys())
                    logger.warning(f'参数 {param_name} (遍历变量, source: {source}): 前一步结果中找不到键 {source}，可用键: {available_keys}')
            
            if values:
                param_values[param_name] = values
                loop_params.append(param_name)
                logger.debug(f'参数 {param_name} (遍历变量): 找到 {len(values)} 个值')
            else:
                # 如果没有找到值，使用空列表（会导致没有组合）
                param_values[param_name] = []
                loop_params.append(param_name)
        elif param_type == 'variable':
            # 变量：从前一步第一条记录获取
            source = config.get('source', '')
            
            # 支持 previous_step 占位符，自动替换为前一步的实际步骤名
            if previous_step_name and source.startswith('previous_step'):
                if source == 'previous_step':
                    # 如果只是 previous_step，替换为前一步步骤名
                    source = previous_step_name
                elif source.startswith('previous_step.'):
                    # 如果是 previous_step.field，替换为 前一步步骤名.field
                    field = source[len('previous_step.'):]
                    source = f'{previous_step_name}.{field}'
            
            value = None
            
            if '.' in source:
                step_name, field = source.split('.', 1)
                # 使用正确的键名格式
                value = previous_results.get(f'{step_name}.{field}')
                if value is None:
                    # 如果使用点号格式找不到，尝试从步骤结果列表中获取第一条记录
                    if step_name in previous_results:
                        records = previous_results[step_name]
                        if isinstance(records, list) and len(records) > 0:
                            first_record = records[0]
                            if isinstance(first_record, dict) and field in first_record:
                                value = first_record[field]
                            else:
                                available_fields = list(first_record.keys()) if isinstance(first_record, dict) else "N/A"
                                logger.warning(f'参数 {param_name} (变量, source: {source}): 前一步 {step_name} 的第一条记录中没有字段 {field}，可用字段: {available_fields}')
                        else:
                            logger.warning(f'参数 {param_name} (变量, source: {source}): 前一步 {step_name} 的结果列表为空或不是列表类型')
                    else:
                        available_steps = list(previous_results.keys())
                        logger.warning(f'参数 {param_name} (变量, source: {source}): 前一步结果中找不到步骤 {step_name}，可用步骤: {available_steps}')
            else:
                value = previous_results.get(source)
                if value is None:
                    available_keys = list(previous_results.keys())
                    logger.warning(f'参数 {param_name} (变量, source: {source}): 前一步结果中找不到键 {source}，可用键: {available_keys}')
            
            # 检查是否为日期表达式并计算
            if isinstance(value, str):
                date_result = evaluate_date_expression(value)
                if date_result is not None:
                    value = date_result
            
            # 如果找不到值，使用 None
            if value is not None:
                param_values[param_name] = [value]
            else:
                param_values[param_name] = []
        else:
            # 固定值：直接使用（已在 parse_step_params 中处理日期表达式）
            value = config.get('value')
            # 再次检查日期表达式（以防万一）
            if isinstance(value, str):
                date_result = evaluate_date_expression(value)
                if date_result is not None:
                    value = date_result
            param_values[param_name] = [value]
    
    # 如果没有遍历参数，返回单一组合
    if not loop_params:
        single_combo = {}
        for param_name, values in param_values.items():
            if values:
                single_combo[param_name] = values[0]
        # 清理字典值，确保所有值都是基本类型，避免触发 ORM 延迟加载
        sanitized_combo = sanitize_dict_values(single_combo) if single_combo else {}
        return [sanitized_combo] if sanitized_combo else []
    
    # 生成笛卡尔积
    param_names = list(param_values.keys())
    value_lists = [param_values[name] for name in param_names]
    
    # 过滤掉空列表
    empty_params = []
    for param_name, values in param_values.items():
        if not values:
            config = param_config.get(param_name, {})
            param_type = config.get('type', 'unknown')
            source = config.get('source', config.get('value', 'N/A'))
            empty_params.append(f'{param_name} (类型: {param_type}, source: {source})')
    
    if empty_params:
        logger.warning(f'以下参数没有值，无法生成参数组合: {", ".join(empty_params)}')
        logger.debug(f'前一步结果可用键: {list(previous_results.keys())}')
        return []
    
    combinations = []
    for combo in product(*value_lists):
        combination_dict = dict(zip(param_names, combo))
        # 清理字典值，确保所有值都是基本类型，避免触发 ORM 延迟加载
        sanitized_dict = sanitize_dict_values(combination_dict)
        combinations.append(sanitized_dict)
    
    return combinations


async def execute_single_step(
    session: AsyncSession,
    step,
    config,
    api_params: dict,
    task,
    task_name: str,
    download_date: str,
    pro: Any,
    previous_results: dict[str, Any],
    step_start_time: datetime,
    combination_index: int | None = None,
    immediate_commit: bool = False,
    step_data_table_name: str | None = None,
    step_update_mode: str = '0',
    step_unique_key_fields: str | None = None,
    step_name: str | None = None,  # 提前提取的步骤名称，避免 commit 后访问 ORM 对象
    step_order: int | None = None,  # 提前提取的步骤顺序，避免 commit 后访问 ORM 对象
    config_api_code: str | None = None,  # 提前提取的接口代码，避免 commit 后访问 ORM 对象
    config_api_name: str | None = None,  # 提前提取的接口名称，避免 commit 后访问 ORM 对象
    config_config_id: int | None = None,  # 提前提取的配置ID，避免 commit 后访问 ORM 对象
    config_data_fields: str | None = None,  # 提前提取的数据字段，避免 commit 后访问 ORM 对象
    config_primary_key_fields: str | None = None,  # 提前提取的主键字段，避免 commit 后访问 ORM 对象
    task_task_id: int | None = None,  # 提前提取的任务ID，避免 commit 后访问 ORM 对象
    task_save_to_db: str = '0',  # 提前提取的是否保存到数据库，避免 commit 后访问 ORM 对象
    task_data_table_name: str | None = None,  # 提前提取的任务数据表名，避免 commit 后访问 ORM 对象
    task_save_path: str | None = None,  # 提前提取的保存路径，避免 commit 后访问 ORM 对象
    task_save_format: str | None = None,  # 提前提取的保存格式，避免 commit 后访问 ORM 对象
    log_detail: bool = True,  # 是否记录明细级下载日志（遍历模式下可关闭，仅保留汇总）
) -> tuple[int, pd.DataFrame | None]:
    """
    执行单个步骤（单次API调用）
    
    :param session: 数据库会话
    :param step: 步骤对象
    :param config: 接口配置对象
    :param api_params: API参数字典
    :param task: 任务对象
    :param task_name: 任务名称
    :param download_date: 下载日期
    :param pro: Tushare pro API对象
    :param previous_results: 前一步的结果数据
    :param step_start_time: 步骤开始时间
    :param combination_index: 参数组合索引（遍历模式下使用，None表示非遍历模式）
    :param immediate_commit: 是否立即提交（循环模式下使用）
    :param step_data_table_name: 步骤数据表名（提前提取，避免延迟加载）
    :param step_update_mode: 步骤更新模式（提前提取，避免延迟加载）
    :param step_unique_key_fields: 步骤唯一键字段（提前提取，避免延迟加载）
    :param step_name: 步骤名称（提前提取，避免延迟加载）
    :param step_order: 步骤顺序（提前提取，避免延迟加载）
    :param config_api_code: 接口代码（提前提取，避免延迟加载）
    :param config_api_name: 接口名称（提前提取，避免延迟加载）
    :param config_config_id: 配置ID（提前提取，避免延迟加载）
    :param config_data_fields: 数据字段（提前提取，避免延迟加载）
    :param config_primary_key_fields: 主键字段（提前提取，避免延迟加载）
    :return: (record_count, df) 记录数和DataFrame
    """
    # 使用传入的参数，避免访问已过期的 ORM 对象属性
    # 注意：所有参数都应该在调用前提前提取，不再从 config 对象获取（避免延迟加载）
    current_step_name = step_name if step_name is not None else '未知步骤'
    current_step_order = step_order if step_order is not None else 0
    
    # 使用传入的参数，不再从 config 对象获取（避免在 commit 后访问 ORM 对象导致延迟加载）
    # 如果参数为 None，使用默认值，不再访问 config 对象
    current_config_api_code = config_api_code if config_api_code is not None else ''
    current_config_api_name = config_api_name if config_api_name is not None else '未知接口'
    current_config_config_id = config_config_id if config_config_id is not None else None
    current_config_data_fields = config_data_fields if config_data_fields is not None else None
    current_config_primary_key_fields = config_primary_key_fields if config_primary_key_fields is not None else None
    
    # 动态调用接口
    # pro_bar 是 ts 模块的函数，需要特殊处理
    if current_config_api_code == 'pro_bar':
        # pro_bar 是 ts 模块的函数，不是 pro 对象的方法
        # 需要先设置 token，然后直接调用 ts.pro_bar
        ts_token = TushareConfig.tushare_token or os.getenv('TUSHARE_TOKEN', '')
        if ts_token:
            ts.set_token(ts_token)
        api_func = ts.pro_bar
    else:
        # 其他接口从 pro 对象获取
        api_func = getattr(pro, current_config_api_code, None)
        if not api_func:
            # 尝试从 ts 模块获取
            api_func = getattr(ts, current_config_api_code, None)
            if not api_func:
                logger.error(f'步骤 {current_step_name} 的接口 {current_config_api_code} 不存在（在 pro 对象和 ts 模块中都未找到）')
                return (0, None)

    # 调用接口获取数据
    try:
        # 记录接口调用信息（用于调试）
        logger.debug(f'步骤 {current_step_name} 调用接口 {current_config_api_code}，函数类型: {type(api_func)}，参数: {api_params}')
        
        # 检查 api_func 是否是 functools.partial（某些接口可能返回 partial 对象）
        import functools
        if isinstance(api_func, functools.partial):
            logger.debug(f'接口 {current_config_api_code} 返回的是 partial 对象: {api_func}')
            # partial 对象可以直接调用，但需要确保参数正确
            df = api_func(**api_params)
        else:
            df = api_func(**api_params)
    except Exception as api_error:
        # 获取完整的错误信息（包括堆栈跟踪）
        full_error = ''.join(traceback.format_exception(type(api_error), api_error, api_error.__traceback__))
        error_detail = f'步骤 {current_step_name} Tushare接口调用失败: {full_error}\n参数: {api_params}\n接口代码: {current_config_api_code}\n接口名称: {current_config_api_name}'
        
        # 限制错误信息长度（但保留更多字符，避免过度截断）
        max_error_length = 5000  # 增加到5000字符
        if len(error_detail) > max_error_length:
            error_detail = error_detail[:max_error_length] + '\n... (错误信息过长，已截断)'
        
        logger.exception(f'步骤 {current_step_name} Tushare接口调用失败: {str(api_error)}')
        # 记录错误日志（可按需关闭明细日志）
        step_duration = int((datetime.now() - step_start_time).total_seconds())
        # 使用提前提取的 task_task_id，避免在 commit 后访问 ORM 对象导致延迟加载
        current_task_task_id = task_task_id if task_task_id is not None else None
        if log_detail:
            log = TushareDownloadLog(
                task_id=current_task_task_id,
                task_name=f'{task_name}[{current_step_name}]' + (f'[组合{combination_index}]' if combination_index is not None else ''),
                config_id=current_config_config_id,
                api_name=current_config_api_name,
                download_date=download_date,
                record_count=0,
                file_path=None,
                status='1',
                error_message=error_detail[:5000] if len(error_detail) > 5000 else error_detail,  # 限制长度但保留更多
                duration=step_duration,
                create_time=datetime.now(),
            )
            await TushareDownloadLogDao.add_log_dao(session, log)
        return (0, None)

    if df is None or df.empty:
        logger.warning(f'步骤 {current_step_name} 下载数据为空' + (f' (组合{combination_index})' if combination_index is not None else ''))
        record_count = 0
        file_path = None
    else:
        record_count = len(df)

        # 如果指定了数据字段，只保留指定字段
        # 使用提前提取的 current_config_data_fields，避免在 commit 后访问 ORM 对象导致延迟加载
        if current_config_data_fields:
            data_fields = json.loads(current_config_data_fields)
            if isinstance(data_fields, list):
                available_fields = [field for field in data_fields if field in df.columns]
                if available_fields:
                    df = df[available_fields]

        # 保存到数据库（如果启用）
        # 使用提前提取的 task_save_to_db，避免在 commit 后访问 ORM 对象导致延迟加载
        # 使用传入的参数，不再访问 task 对象属性，避免在异步上下文中触发延迟加载
        current_task_save_to_db = task_save_to_db if task_save_to_db is not None else '0'
        if current_task_save_to_db == '1':
            try:
                # 优先使用传入的表名参数，其次使用任务配置的表名，最后使用默认表名
                # 注意：不再从 step 或 task 对象获取，因为可能在 commit 后访问，使用传入的参数
                table_name = step_data_table_name if step_data_table_name and step_data_table_name.strip() else None
                if not table_name:
                    table_name = task_data_table_name if task_data_table_name and task_data_table_name.strip() else None
                # 如果传入的参数都为空，直接使用默认表名，不再尝试从 task 对象获取（避免异步上下文中的延迟加载问题）
                if not table_name or table_name.strip() == '':
                    table_name = f'tushare_{current_config_api_code}'
                
                await ensure_table_exists(session, table_name, current_config_api_code, df, config, current_config_primary_key_fields)
                
                # 使用传入的更新模式参数
                # 注意：不再从 step 对象获取，因为可能在 commit 后访问
                update_mode = step_update_mode if step_update_mode else '0'
                
                # 解析步骤配置的唯一键字段（JSON格式）
                step_unique_key_fields_parsed = None
                if step_unique_key_fields and step_unique_key_fields.strip():
                    try:
                        step_unique_key_fields_parsed = json.loads(step_unique_key_fields)
                        if not isinstance(step_unique_key_fields_parsed, list):
                            step_unique_key_fields_parsed = None
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f'步骤 {current_step_name} 的唯一键字段配置格式错误，将使用自动检测')
                        step_unique_key_fields_parsed = None
                # 注意：不再从 step 对象获取 unique_key_fields，因为可能在 commit 后访问
                # 如果传入的 step_unique_key_fields 为空，则使用 None（将触发自动检测）
                
                # 使用新的唯一键获取逻辑（优先级：步骤配置 > 如果表已存在且接口配置的主键字段也有，则优先使用接口配置 > 表实际主键 > 接口配置 > 自动检测）
                # 传递提前提取的 primary_key_fields_str，避免访问 config 对象导致延迟加载
                unique_key_fields = await TushareDataDao.get_unique_key_fields(
                    session, table_name, config=config, step_unique_key_fields=step_unique_key_fields_parsed, primary_key_fields_str=current_config_primary_key_fields
                )
                
                # 记录数据保存前的详细信息（用于调试重复数据问题）
                logger.debug(
                    f'步骤 {current_step_name}' + (f' 组合{combination_index}' if combination_index is not None else '') +
                    f' 准备保存数据到表 {table_name}，记录数: {len(df)}，更新模式: {update_mode}，唯一键字段: {unique_key_fields}'
                )
                
                # 如果启用了唯一键字段，记录前几条数据的唯一键值（用于识别重复数据）
                if unique_key_fields and len(df) > 0:
                    sample_keys = []
                    for idx, row in df.head(5).iterrows():
                        key_values = {k: row.get(k) for k in unique_key_fields if k in row.index}
                        if key_values:
                            sample_keys.append(key_values)
                    if sample_keys:
                        logger.debug(
                            f'步骤 {current_step_name}' + (f' 组合{combination_index}' if combination_index is not None else '') +
                            f' 数据唯一键值示例（前5条）: {sample_keys}'
                        )
                
                # 保存数据
                # 使用提前提取的 task_task_id，避免在 commit 后访问 ORM 对象导致延迟加载
                current_task_task_id = task_task_id if task_task_id is not None else None
                if current_task_task_id is None:
                    raise ValueError('任务ID不能为空')
                # 传递提前提取的 primary_key_fields_str，避免访问 config 对象导致延迟加载
                inserted_count = await TushareDataDao.add_dataframe_to_table_dao(
                    session, table_name, df, current_task_task_id, current_config_config_id, current_config_api_code, download_date,
                    update_mode=update_mode, unique_key_fields=unique_key_fields, config=config, primary_key_fields_str=current_config_primary_key_fields
                )
                
                # 记录保存结果
                if inserted_count < len(df) and update_mode in ['1', '2']:
                    skipped_count = len(df) - inserted_count
                    logger.warning(
                        f'步骤 {current_step_name}' + (f' 组合{combination_index}' if combination_index is not None else '') +
                        f' 保存数据到表 {table_name}：尝试插入 {len(df)} 条，实际插入 {inserted_count} 条，跳过 {skipped_count} 条重复数据'
                    )
                else:
                    logger.info(
                        f'步骤 {current_step_name}' + (f' 组合{combination_index}' if combination_index is not None else '') +
                        f' 已保存 {inserted_count} 条数据到数据库表 {table_name}，更新模式: {update_mode}'
                    )
            except Exception as db_error:
                # 获取完整的错误信息（包括堆栈跟踪）
                full_error = ''.join(traceback.format_exception(type(db_error), db_error, db_error.__traceback__))
                error_detail = f'步骤 {current_step_name} 保存数据到数据库失败: {full_error}'
                
                # 限制错误信息长度（但保留更多字符，避免过度截断）
                max_error_length = 5000  # 增加到5000字符
                if len(error_detail) > max_error_length:
                    error_detail = error_detail[:max_error_length] + '\n... (错误信息过长，已截断)'
                
                logger.exception(f'步骤 {current_step_name} 保存数据到数据库失败: {str(db_error)}')
                
                # 记录更详细的错误信息，包括数据的前几条记录（用于识别问题数据）
                if df is not None and not df.empty:
                    try:
                        sample_data = df.head(3).to_dict('records')
                        logger.error(
                            f'步骤 {current_step_name}' + (f' 组合{combination_index}' if combination_index is not None else '') +
                            f' 保存失败的数据示例（前3条）: {json.dumps(sample_data, ensure_ascii=False, default=str)}'
                        )
                    except Exception as sample_error:
                        logger.debug(f'无法记录数据示例: {sample_error}')
                
                # 记录错误但继续执行后续步骤
                step_duration = int((datetime.now() - step_start_time).total_seconds())
                # 使用提前提取的 task_task_id，避免在 commit 后访问 ORM 对象导致延迟加载
                current_task_task_id = task_task_id if task_task_id is not None else None
                if log_detail:
                    log = TushareDownloadLog(
                        task_id=current_task_task_id,
                        task_name=f'{task_name}[{current_step_name}]' + (f'[组合{combination_index}]' if combination_index is not None else ''),
                        config_id=current_config_config_id,
                        api_name=current_config_api_name,
                        download_date=download_date,
                        record_count=record_count,
                        file_path=None,
                        status='1',
                        error_message=error_detail[:5000] if len(error_detail) > 5000 else error_detail,  # 限制长度但保留更多
                        duration=step_duration,
                        create_time=datetime.now(),
                    )
                
                # 在循环模式下，不应该回滚主事务，应该抛出异常让调用者处理保存点回滚
                if not immediate_commit:
                    # 尝试记录错误日志（使用新会话，避免影响主事务）
                    if log_detail:
                        try:
                            async with AsyncSessionLocal() as new_session:
                                await TushareDownloadLogDao.add_log_dao(new_session, log)
                                await new_session.commit()
                        except Exception as new_session_error:
                            logger.error(f'使用新会话记录错误日志失败: {str(new_session_error)}')
                    # 抛出异常，让调用者处理保存点回滚
                    raise
                else:
                    # 非循环模式下，回滚并记录日志
                    try:
                        await session.rollback()
                        if log_detail:
                            await TushareDownloadLogDao.add_log_dao(session, log)
                            await session.commit()
                    except Exception as log_error:
                        logger.error(f'记录错误日志失败: {str(log_error)}')
                        # 如果回滚后仍然失败，尝试创建新会话记录日志
                        if log_detail:
                            try:
                                async with AsyncSessionLocal() as new_session:
                                    await TushareDownloadLogDao.add_log_dao(new_session, log)
                                    await new_session.commit()
                            except Exception as new_session_error:
                                logger.error(f'使用新会话记录错误日志也失败: {str(new_session_error)}')
                    return (record_count, df)

        # 保存到文件（如果配置了保存路径）
        # 使用提前提取的 task_save_path 和 task_save_format，避免在 commit 后访问 ORM 对象导致延迟加载
        file_path = None
        # 使用传入的参数，不再访问 task 对象属性，避免在异步上下文中触发延迟加载
        if task_save_path:
            try:
                save_path = task_save_path
                os.makedirs(save_path, exist_ok=True)
                combo_suffix = f'_combo{combination_index}' if combination_index is not None else ''
                file_name = f"{current_config_api_code}_{current_step_order}_{download_date}_{datetime.now().strftime('%H%M%S')}{combo_suffix}"
                # 使用传入的参数，不再访问 task 对象属性，避免在异步上下文中触发延迟加载
                save_format = task_save_format or 'csv'

                if save_format == 'csv':
                    file_path = os.path.join(save_path, f'{file_name}.csv')
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')
                elif save_format == 'excel':
                    file_path = os.path.join(save_path, f'{file_name}.xlsx')
                    df.to_excel(file_path, index=False, engine='openpyxl')
                elif save_format == 'json':
                    file_path = os.path.join(save_path, f'{file_name}.json')
                    df.to_json(file_path, orient='records', force_ascii=False, indent=2)
                else:
                    file_path = os.path.join(save_path, f'{file_name}.csv')
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')

                logger.info(f'步骤 {current_step_name} 数据已保存到文件: {file_path}')
            except Exception as file_error:
                # 获取完整的错误信息（包括堆栈跟踪）
                full_error = ''.join(traceback.format_exception(type(file_error), file_error, file_error.__traceback__))
                error_detail = f'步骤 {current_step_name} 保存数据到文件失败: {full_error}'
                
                # 限制错误信息长度（但保留更多字符，避免过度截断）
                max_error_length = 5000  # 增加到5000字符
                if len(error_detail) > max_error_length:
                    error_detail = error_detail[:max_error_length] + '\n... (错误信息过长，已截断)'
                
                logger.exception(f'步骤 {current_step_name} 保存数据到文件失败: {str(file_error)}')
                # 记录错误但继续执行后续步骤

    # 计算步骤执行时长
    step_duration = int((datetime.now() - step_start_time).total_seconds())

    # 创建步骤下载日志（可按需关闭明细日志）
    # 使用提前提取的 task_task_id，避免在 commit 后访问 ORM 对象导致延迟加载
    current_task_task_id = task_task_id if task_task_id is not None else None
    if log_detail:
        log = TushareDownloadLog(
            task_id=current_task_task_id,
            task_name=f'{task_name}[{current_step_name}]' + (f'[组合{combination_index}]' if combination_index is not None else ''),
            config_id=current_config_config_id,
            api_name=current_config_api_name,
            download_date=download_date,
            record_count=record_count,
            file_path=file_path,
            status='0',
            duration=step_duration,
            create_time=datetime.now(),
        )
        await TushareDownloadLogDao.add_log_dao(session, log)

    return (record_count, df)


async def execute_workflow(session: AsyncSession, task, download_date: str, task_params_str: str = None) -> None:
    """
    执行流程配置，串联多个接口

    :param session: 数据库会话
    :param task: 任务对象
    :param download_date: 下载日期
    :param task_params_str: 任务参数字符串（JSON格式），避免延迟加载问题
    :return: None
    """
    start_time = datetime.now()
    workflow_failed = False
    last_error_message: str | None = None
    # 提前提取 task 对象的所有属性，避免在 commit 后访问 ORM 对象导致延迟加载问题
    # 这是关键优化：一次性加载所有属性，后续不再访问 task 对象
    try:
        # 使用 refresh 确保所有属性都已加载到内存中
        await session.refresh(task)
    except Exception as refresh_error:
        logger.debug(f'刷新任务对象时出错（可能对象未过期）: {refresh_error}')
    
    # 直接从对象的 __dict__ 中提取属性，避免触发任何延迟加载
    task_dict = task.__dict__.copy()
    task_dict.pop('_sa_instance_state', None)
    
    # 提取需要的 task 属性
    task_name = task_dict.get('task_name') or '未知任务'
    task_task_id = task_dict.get('task_id')
    task_save_to_db = task_dict.get('save_to_db', '0') or '0'
    task_data_table_name = task_dict.get('data_table_name')
    task_save_path = task_dict.get('save_path')
    task_save_format = task_dict.get('save_format')
    task_workflow_id = task_dict.get('workflow_id')
    
    # 获取流程配置
    workflow = await TushareWorkflowConfigDao.get_workflow_detail_by_id(session, task_workflow_id)
    if not workflow:
        logger.error(f'流程配置ID {task.workflow_id} 不存在')
        return

    if workflow.status != '0':
        logger.warning(f'流程配置 {workflow.workflow_name} 已停用')
        return

    # 创建运行记录（PENDING -> RUNNING）
    # 注意：这里立即缓存 run_id，后续不再访问 ORM 对象属性，避免在 commit 之后触发延迟加载
    run_record = await TushareDownloadRunDao.create_run_record(session, task, initial_status='PENDING')
    run_id = run_record.run_id
    await TushareDownloadRunDao.update_run_status(
        session,
        run_id,
        status='RUNNING',
        set_start_time=True,
    )

    # 获取流程步骤（按顺序）
    steps = await TushareWorkflowStepDao.get_steps_by_workflow_id(session, task_workflow_id)
    if not steps:
        logger.warning(f'流程配置 {workflow.workflow_name} 没有配置步骤')
        return

    # 获取tushare pro接口
    ts_token = TushareConfig.tushare_token or os.getenv('TUSHARE_TOKEN', '')
    if not ts_token:
        raise ValueError(
            'TUSHARE_TOKEN未设置，请在.env.dev文件中配置TUSHARE_TOKEN环境变量。'
            '例如：TUSHARE_TOKEN=your_tushare_token_here'
        )
    pro = ts.pro_api(ts_token)

    # 用于存储前一步的结果数据，供后续步骤使用
    previous_results: dict[str, Any] = {}
    total_record_count = 0
    previous_step_name: str = None  # 记录前一步的步骤名，用于支持 previous_step 占位符

    # 提前提取所有步骤的属性并缓存，避免在 commit 后访问 ORM 对象导致延迟加载问题
    # 这是关键优化：一次性加载所有属性，后续不再访问 step 对象
    step_cache: list[dict[str, Any]] = []
    for step in steps:
        try:
            # 使用 refresh 确保所有属性都已加载到内存中
            await session.refresh(step)
        except Exception as refresh_error:
            logger.debug(f'刷新步骤对象时出错（可能对象未过期）: {refresh_error}')
        
        # 直接从对象的 __dict__ 中提取属性，避免触发任何延迟加载
        # 这是最安全的方式，因为直接从实例字典中读取，不会触发 SQLAlchemy 的属性访问器
        step_dict = step.__dict__.copy()
        # 移除 SQLAlchemy 的内部属性
        step_dict.pop('_sa_instance_state', None)
        
        # 提取需要的属性，使用字典访问而不是属性访问，避免触发延迟加载
        cached_step = {
            'step': step,  # 保留原始对象引用（用于向后兼容，但后续不应再访问）
            'step_id': step_dict.get('step_id'),
            'status': step_dict.get('status', '0') or '0',
            'step_name': step_dict.get('step_name') or '未知步骤',
            'node_type': step_dict.get('node_type', 'task') or 'task',
            'step_order': step_dict.get('step_order'),
            'config_id': step_dict.get('config_id'),
            'step_params': step_dict.get('step_params'),
            'condition_expr': step_dict.get('condition_expr'),
            'data_table_name': step_dict.get('data_table_name'),
            'update_mode': step_dict.get('update_mode', '0') or '0',
            'unique_key_fields': step_dict.get('unique_key_fields'),
            'loop_mode': step_dict.get('loop_mode', '0') or '0',
        }
        step_cache.append(cached_step)
    
    # 按顺序执行每个步骤（使用缓存的属性，不再访问 step 对象）
    for cached_step in step_cache:
        # 从缓存中获取所有属性，避免访问 ORM 对象
        step = cached_step['step']  # 保留用于向后兼容，但不应再访问其属性
        step_status = cached_step['status']
        step_name = cached_step['step_name']
        step_node_type = cached_step['node_type']
        step_order = cached_step['step_order']
        step_config_id = cached_step['config_id']
        step_step_params = cached_step['step_params']
        step_condition_expr = cached_step['condition_expr']
        step_data_table_name = cached_step['data_table_name']
        step_update_mode = cached_step['update_mode']
        step_unique_key_fields = cached_step['unique_key_fields']
        step_loop_mode = cached_step['loop_mode']
        
        # 使用提取的值进行判断
        if step_status != '0':
            logger.warning(f'步骤 {step_name} 已停用，跳过')
            continue

        # 跳过开始和结束节点（这些节点不需要接口配置）
        if step_node_type in ['start', 'end']:
            logger.info(f'步骤 {step_name} 是{step_node_type}节点，跳过执行')
            continue

        step_start_time = datetime.now()
        logger.info(f'开始执行步骤: {step_name} (顺序: {step_order})')

        # 获取接口配置
        config = await TushareApiConfigDao.get_config_detail_by_id(session, step_config_id)
        if config is None:
            logger.error(f'步骤 {step_name} 的接口配置ID {step_config_id} 不存在')
            continue

        # 立即提取 config 的所有属性，避免在 commit 后访问 ORM 对象导致延迟加载
        config_dict = config.__dict__.copy()
        config_dict.pop('_sa_instance_state', None)
        config_status = config_dict.get('status', '0') or '0'
        config_api_name = config_dict.get('api_name') or '未知接口'
        config_api_code = config_dict.get('api_code') or ''
        config_api_params = config_dict.get('api_params')
        config_config_id = config_dict.get('config_id')
        config_data_fields = config_dict.get('data_fields')
        config_primary_key_fields = config_dict.get('primary_key_fields')

        if config_status != '0':
            logger.warning(f'步骤 {step_name} 的接口配置 {config_api_name} 已停用')
            continue

        # 解析步骤参数（可以从前一步获取数据）
        base_api_params = {}
        if config_api_params:
            base_api_params = json.loads(config_api_params)

        # 步骤参数覆盖接口默认参数
        step_params = {}
        if step_step_params:
            try:
                step_params = json.loads(step_step_params)
                # 确保解析后是字典
                if not isinstance(step_params, dict):
                    logger.warning(f'步骤 {step_name} 的参数不是对象格式，将使用空字典')
                    step_params = {}
            except json.JSONDecodeError as e:
                logger.error(f'步骤 {step_name} 的参数JSON解析失败: {e}, 内容: {step_step_params[:100] if step_step_params else "None"}')
                step_params = {}
            except Exception as e:
                logger.error(f'步骤 {step_name} 的参数解析异常: {e}')
                step_params = {}

        # 检查是否开启遍历模式
        loop_mode = step_loop_mode == '1'
        
        # 解析参数配置
        param_config = parse_step_params(step_params, previous_results, loop_mode)
        
        # 检查是否有遍历参数
        has_loop_params = any(config.get('type') == 'loop' for config in param_config.values())
        
        # 生成参数组合
        if loop_mode or has_loop_params:
            # 遍历模式：生成所有参数组合
            param_combinations = generate_param_combinations(param_config, previous_results, previous_step_name)
            
            if not param_combinations:
                logger.warning(f'步骤 {step_name} 没有有效的参数组合，跳过')
                continue
            
            total_combinations = len(param_combinations)
            
            # 提取遍历参数信息（用于日志记录）
            loop_params_summary = {}
            for param_name, param_config_item in param_config.items():
                if param_config_item.get('type') == 'loop':
                    source = param_config_item.get('source', '')
                    loop_params_summary[param_name] = {
                        'type': 'loop',
                        'source': source,
                        'value_count': len([c for c in param_combinations if param_name in c])
                    }
            
            logger.info(
                f'步骤 {step_name} 开启遍历模式，将执行 {total_combinations} 次API调用，'
                f'遍历参数: {list(loop_params_summary.keys())}'
            )
            
            # 用于合并所有组合的结果（仅用于后续步骤使用，不用于保存）
            all_dfs = []
            step_total_records = 0
            # 遍历执行统计
            loop_success_count = 0
            loop_fail_count = 0
            loop_skip_count = 0
            loop_execution_details = []  # 记录每个组合的执行详情
            
            # 对每个参数组合执行步骤
            for combo_index, combo_params in enumerate(param_combinations, 1):
                # 清理 combo_params，确保所有值都是基本类型，避免触发 ORM 延迟加载
                sanitized_combo_params = sanitize_dict_values(combo_params)
                
                # 合并基础参数和组合参数
                api_params = base_api_params.copy()
                api_params.update(sanitized_combo_params)
                
                # 任务参数覆盖步骤参数
                if task_params_str:
                    try:
                        task_params = json.loads(task_params_str)
                        if isinstance(task_params, dict):
                            api_params.update(task_params)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f'步骤 {step_name} 组合{combo_index} 任务参数解析失败: {e}，将跳过任务参数')
                
                # 注意：不再自动添加日期参数，所有参数必须从配置中获取
                # 如果需要在参数中使用日期，请在接口配置或步骤参数中明确指定
                
                # 检查执行条件（可选）- 使用提前提取的值
                if step_condition_expr:
                    try:
                        condition = json.loads(step_condition_expr)
                        should_execute = True
                        if 'field' in condition and 'value' in condition:
                            field = condition['field']
                            expected_value = condition['value']
                            if field in previous_results:
                                actual_value = previous_results[field]
                                if condition.get('operator') == 'eq':
                                    should_execute = actual_value == expected_value
                                elif condition.get('operator') == 'ne':
                                    should_execute = actual_value != expected_value
                        if not should_execute:
                            # 降低日志级别，避免遍历模式下产生过多 INFO 日志
                            logger.debug(f'步骤 {step_name} 组合{combo_index} 不满足执行条件，跳过')
                            loop_skip_count += 1
                            # 使用清理后的参数，避免触发 ORM 延迟加载
                            loop_execution_details.append({
                                'combo_index': combo_index,
                                'params': sanitized_combo_params,
                                'status': 'skipped',
                                'reason': '不满足执行条件'
                            })
                            continue
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f'步骤 {step_name} 组合{combo_index} 条件表达式解析失败: {e}，将执行')
                
                # 执行单次步骤（循环模式下，使用保存点隔离每个组合，先保存数据，最后统一commit）
                # 使用保存点可以确保某个组合失败时只回滚该组合，不影响其他组合
                combo_start_time = datetime.now()
                # 创建保存点，隔离每个组合的事务
                savepoint = await session.begin_nested()
                try:
                    # 传递提前提取的 config 和 task 属性，避免在 commit 后访问 ORM 对象
                    # 遍历模式下关闭明细日志，仅依赖后续的步骤级汇总日志
                    record_count, df = await execute_single_step(
                        session, step, config, api_params, task, task_name,
                        download_date, pro, previous_results, combo_start_time, combo_index,
                        immediate_commit=False,  # 循环模式下不立即提交，统一在循环结束后提交
                        step_data_table_name=step_data_table_name,
                        step_update_mode=step_update_mode,
                        step_unique_key_fields=step_unique_key_fields,
                        step_name=step_name,  # 传递提前提取的步骤名称
                        step_order=step_order,  # 传递提前提取的步骤顺序
                        config_api_code=config_api_code,  # 传递提前提取的接口代码
                        config_api_name=config_api_name,  # 传递提前提取的接口名称
                        config_config_id=config_config_id,  # 传递提前提取的配置ID
                        config_data_fields=config_data_fields,  # 传递提前提取的数据字段
                        config_primary_key_fields=config_primary_key_fields,  # 传递提前提取的主键字段
                        task_task_id=task_task_id,  # 传递提前提取的任务ID
                        task_save_to_db=task_save_to_db,  # 传递提前提取的是否保存到数据库
                        task_data_table_name=task_data_table_name,  # 传递提前提取的任务数据表名
                        task_save_path=task_save_path,  # 传递提前提取的保存路径
                        task_save_format=task_save_format,  # 传递提前提取的保存格式
                        log_detail=False,  # 关闭组合级明细日志
                    )
                    
                    # 提交保存点（但不提交主事务）
                    await savepoint.commit()
                    # 循环模式下不立即提交，统一在循环结束后提交，避免频繁 commit 导致的异步上下文问题
                    logger.debug(f'步骤 {step_name} 组合{combo_index} 数据已保存（待统一提交），记录数: {record_count}')
                except Exception as step_error:
                    # 回滚保存点，不影响其他组合
                    try:
                        await savepoint.rollback()
                        logger.debug(f'步骤 {step_name} 组合{combo_index} 保存点已回滚')
                    except Exception as rollback_error:
                        logger.error(f'步骤 {step_name} 组合{combo_index} 回滚保存点失败: {rollback_error}')
                        # 如果保存点回滚失败，回滚整个事务
                        try:
                            await session.rollback()
                            logger.warning(f'步骤 {step_name} 组合{combo_index} 保存点回滚失败，已回滚整个事务，之前成功的组合数据可能丢失')
                        except Exception as full_rollback_error:
                            logger.error(f'步骤 {step_name} 组合{combo_index} 回滚整个事务也失败: {full_rollback_error}')
                    
                    # 异常处理：使用提前提取的 step_name，不访问 step 对象
                    logger.error(f'步骤 {step_name} 组合{combo_index} 执行失败: {step_error}')
                    workflow_failed = True
                    last_error_message = str(step_error)
                    record_count = 0
                    df = None
                
                # 记录执行结果
                combo_status = 'success' if df is not None and not df.empty else 'empty'
                if df is not None and not df.empty:
                    all_dfs.append(df)
                    step_total_records += record_count
                    loop_success_count += 1
                else:
                    if record_count == 0 and df is None:
                        loop_fail_count += 1
                        combo_status = 'failed'
                    else:
                        loop_success_count += 1  # 空数据也算成功执行
                
                # 记录组合执行详情
                combo_duration = int((datetime.now() - combo_start_time).total_seconds())
                # 使用清理后的参数，避免触发 ORM 延迟加载
                loop_execution_details.append({
                    'combo_index': combo_index,
                    'params': sanitized_combo_params,
                    'status': combo_status,
                    'record_count': record_count,
                    'duration': combo_duration
                })
            
            # 计算步骤总耗时
            step_duration = int((datetime.now() - step_start_time).total_seconds())
            
            # 合并所有组合的结果
            if all_dfs:
                combined_df = pd.concat(all_dfs, ignore_index=True)
                # 去重（如果需要）
                combined_df = combined_df.drop_duplicates()
                
                # 保存前一步的结果（供后续步骤使用）
                previous_results[step_name] = combined_df.to_dict('records')
                if len(previous_results[step_name]) > 0:
                    # 保存第一条记录的主要字段，方便条件判断
                    first_record = previous_results[step_name][0]
                    for key, value in first_record.items():
                        previous_results[f'{step_name}.{key}'] = value
                
                # 更新前一步步骤名，用于支持 previous_step 占位符
                previous_step_name = step_name
                
                total_record_count += step_total_records
                
                # 记录遍历调度的统计式监控日志（仅输出一条 INFO，避免遍历模式下日志过多）
                loop_summary_message = (
                    f'步骤 {step_name} 遍历执行统计: '
                    f'总组合数={total_combinations}, '
                    f'成功={loop_success_count}, '
                    f'失败={loop_fail_count}, '
                    f'跳过={loop_skip_count}, '
                    f'总记录数={len(combined_df)}, '
                    f'总耗时={step_duration}秒'
                )
                logger.info(loop_summary_message)
                
                # 创建遍历调度的汇总监控日志（仅保留少量执行详情，避免日志记录过多过长）
                max_detail_items = 5
                trimmed_execution_details = loop_execution_details[:max_detail_items]
                loop_summary_data = {
                    'type': 'loop_summary',
                    'total_combinations': total_combinations,
                    'success_count': loop_success_count,
                    'fail_count': loop_fail_count,
                    'skip_count': loop_skip_count,
                    'total_records': len(combined_df),
                    'loop_params': loop_params_summary,
                    'execution_details': trimmed_execution_details,
                }
                # 将汇总信息压缩到合理长度，避免 error_message 过长
                loop_summary_json = json.dumps(loop_summary_data, ensure_ascii=False)
                max_summary_length = 3000
                if len(loop_summary_json) > max_summary_length:
                    loop_summary_json = loop_summary_json[:max_summary_length] + '... (已截断)'
                
                # 使用提前提取的 config 和 task 属性，避免在 commit 后访问 ORM 对象
                loop_log = TushareDownloadLog(
                    task_id=task_task_id,
                    task_name=f'{task_name}[{step_name}][遍历汇总]',
                    config_id=config_config_id,
                    api_name=config_api_name,
                    download_date=download_date,
                    record_count=len(combined_df),
                    file_path=None,
                    status='0' if loop_fail_count == 0 else '1',
                    error_message=loop_summary_json,  # 始终保存精简后的汇总信息
                    duration=step_duration,
                    create_time=datetime.now(),
                )
                await TushareDownloadLogDao.add_log_dao(session, loop_log)
                
                # 循环模式下，所有组合执行完成后统一 commit，避免频繁 commit 导致的异步上下文问题
                # 注意：commit 失败时不抛出异常，只记录错误并继续执行
                try:
                    await session.commit()
                    logger.debug(f'步骤 {step_name} 遍历模式执行完成并已统一提交（共 {total_combinations} 个组合），准备执行下一个步骤')
                except Exception as commit_error:
                    logger.error(f'步骤 {step_name} 遍历模式提交事务失败: {commit_error}，将跳过 commit 继续执行')
                    try:
                        await session.rollback()
                    except Exception as rollback_error:
                        logger.warning(f'步骤 {step_name} 遍历模式回滚事务也失败: {rollback_error}')
                    # 继续执行下一个步骤，不抛出异常
            else:
                logger.warning(f'步骤 {step_name} 遍历执行完成，但没有获取到任何数据')
                
                # 即使没有数据，也记录统计式监控日志（单条 WARNING）
                loop_summary_message = (
                    f'步骤 {step_name} 遍历执行统计: '
                    f'总组合数={total_combinations}, '
                    f'成功={loop_success_count}, '
                    f'失败={loop_fail_count}, '
                    f'跳过={loop_skip_count}, '
                    f'总记录数=0, '
                    f'总耗时={step_duration}秒'
                )
                logger.warning(loop_summary_message)
                
                # 创建遍历调度的汇总监控日志（无数据情况，同样精简执行详情）
                max_detail_items = 5
                trimmed_execution_details = loop_execution_details[:max_detail_items]
                loop_summary_data = {
                    'type': 'loop_summary',
                    'total_combinations': total_combinations,
                    'success_count': loop_success_count,
                    'fail_count': loop_fail_count,
                    'skip_count': loop_skip_count,
                    'total_records': 0,
                    'loop_params': loop_params_summary,
                    'execution_details': trimmed_execution_details,
                    'warning': '遍历执行完成但没有获取到任何数据',
                }
                loop_summary_json = json.dumps(loop_summary_data, ensure_ascii=False)
                max_summary_length = 3000
                if len(loop_summary_json) > max_summary_length:
                    loop_summary_json = loop_summary_json[:max_summary_length] + '... (已截断)'
                
                # 使用提前提取的 config 和 task 属性，避免在 commit 后访问 ORM 对象
                loop_log = TushareDownloadLog(
                    task_id=task_task_id,
                    task_name=f'{task_name}[{step_name}][遍历汇总]',
                    config_id=config_config_id,
                    api_name=config_api_name,
                    download_date=download_date,
                    record_count=0,
                    file_path=None,
                    status='1' if loop_fail_count > 0 else '0',
                    error_message=loop_summary_json,
                    duration=step_duration,
                    create_time=datetime.now(),
                )
                await TushareDownloadLogDao.add_log_dao(session, loop_log)
                
                # 循环模式下，所有组合执行完成后统一 commit（即使没有数据也要提交日志）
                # 注意：commit 失败时不抛出异常，只记录错误并继续执行
                try:
                    await session.commit()
                    logger.debug(f'步骤 {step_name} 遍历模式执行完成并已统一提交（无数据，共 {total_combinations} 个组合），准备执行下一个步骤')
                except Exception as commit_error:
                    logger.error(f'步骤 {step_name} 遍历模式提交事务失败: {commit_error}，将跳过 commit 继续执行')
                    try:
                        await session.rollback()
                    except Exception as rollback_error:
                        logger.warning(f'步骤 {step_name} 遍历模式回滚事务也失败: {rollback_error}')
                    # 继续执行下一个步骤，不抛出异常
        else:
            # 非遍历模式：使用原有逻辑（向后兼容）
            api_params = base_api_params.copy()
            
            # 解析步骤参数（向后兼容的旧格式）
            if step_params and isinstance(step_params, dict):
                for key, value in step_params.items():
                    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                        # 支持 ${previous_step.field} 格式，从前一步结果中获取
                        expr = value[2:-1]
                        if '.' in expr:
                            step_name, field = expr.split('.', 1)
                            # 使用正确的键名格式：step_name.field
                            api_params[key] = previous_results.get(f'{step_name}.{field}', value)
                        else:
                            api_params[key] = previous_results.get(expr, value)
                    else:
                        # 检查是否为日期表达式并计算
                        date_result = evaluate_date_expression(value) if isinstance(value, str) else None
                        api_params[key] = date_result if date_result is not None else value
            
            # 任务参数覆盖步骤参数
            if task_params_str:
                try:
                    task_params = json.loads(task_params_str)
                    if isinstance(task_params, dict):
                        api_params.update(task_params)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f'步骤 {step_name} 任务参数解析失败: {e}，将跳过任务参数')
            
            # 注意：不再自动添加日期参数，所有参数必须从配置中获取
            # 如果需要在参数中使用日期，请在接口配置或步骤参数中明确指定
            
            # 检查执行条件（可选）- 使用提前提取的值
            if step_condition_expr:
                try:
                    condition = json.loads(step_condition_expr)
                    should_execute = True
                    if 'field' in condition and 'value' in condition:
                        field = condition['field']
                        expected_value = condition['value']
                        if field in previous_results:
                            actual_value = previous_results[field]
                            if condition.get('operator') == 'eq':
                                should_execute = actual_value == expected_value
                            elif condition.get('operator') == 'ne':
                                should_execute = actual_value != expected_value
                    if not should_execute:
                        logger.info(f'步骤 {step_name} 不满足执行条件，跳过')
                        continue
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f'步骤 {step_name} 条件表达式解析失败: {e}，将执行')
            
            # 执行单次步骤（非循环模式，不需要立即提交）
            # 传递提前提取的 config 和 task 属性，避免在 commit 后访问 ORM 对象
            record_count, df = await execute_single_step(
                session, step, config, api_params, task, task_name,
                download_date, pro, previous_results, step_start_time, None,
                immediate_commit=False,
                step_data_table_name=step_data_table_name,
                step_update_mode=step_update_mode,
                step_unique_key_fields=step_unique_key_fields,
                step_name=step_name,  # 传递提前提取的步骤名称
                step_order=step_order,  # 传递提前提取的步骤顺序
                config_api_code=config_api_code,  # 传递提前提取的接口代码
                config_api_name=config_api_name,  # 传递提前提取的接口名称
                config_config_id=config_config_id,  # 传递提前提取的配置ID
                config_data_fields=config_data_fields,  # 传递提前提取的数据字段
                config_primary_key_fields=config_primary_key_fields,  # 传递提前提取的主键字段
                task_task_id=task_task_id,  # 传递提前提取的任务ID
                task_save_to_db=task_save_to_db,  # 传递提前提取的是否保存到数据库
                task_data_table_name=task_data_table_name,  # 传递提前提取的任务数据表名
                task_save_path=task_save_path,  # 传递提前提取的保存路径
                task_save_format=task_save_format  # 传递提前提取的保存格式
            )
            
            if df is not None and not df.empty:
                # 保存前一步的结果（供后续步骤使用）
                previous_results[step_name] = df.to_dict('records')
                if len(previous_results[step_name]) > 0:
                    # 保存第一条记录的主要字段，方便条件判断
                    first_record = previous_results[step_name][0]
                    for key, value in first_record.items():
                        previous_results[f'{step_name}.{key}'] = value
                
                # 更新前一步步骤名，用于支持 previous_step 占位符
                previous_step_name = step_name
                
                total_record_count += record_count
            else:
                # 单步执行失败（df 为 None 且没有数据）
                if df is None:
                    workflow_failed = True
                    last_error_message = f'步骤 {step_name} 执行失败或未返回数据'
            
            # 步骤执行完成后立即 commit，然后再执行下一个步骤
            # 注意：commit 失败时不抛出异常，只记录错误并继续执行
            try:
                await session.commit()
                logger.debug(f'步骤 {step_name} 执行完成并已提交，准备执行下一个步骤')
            except Exception as commit_error:
                logger.error(f'步骤 {step_name} 提交事务失败: {commit_error}，将跳过 commit 继续执行')
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    logger.warning(f'步骤 {step_name} 回滚事务也失败: {rollback_error}')
                # 继续执行下一个步骤，不抛出异常

    # 计算总执行时长
    duration = int((datetime.now() - start_time).total_seconds())

    # 更新运行记录和任务统计
    # 重新获取任务以保证统计字段最新
    current_task = await TushareDownloadTaskDao.get_task_detail_by_id(session, task_task_id)
    run_update_status = 'FAILED' if workflow_failed else 'SUCCESS'

    await TushareDownloadRunDao.update_run_status(
        session,
        run_id,
        status=run_update_status,
        total_records=total_record_count,
        success_records=total_record_count if not workflow_failed else 0,
        fail_records=0 if not workflow_failed else 1,
        error_message=last_error_message,
        set_end_time=True,
    )

    if current_task:
        if workflow_failed:
            update_stats_dict = {
                'run_count': (current_task.run_count or 0) + 1,
                'fail_count': (current_task.fail_count or 0) + 1,
                'last_run_time': datetime.now(),
            }
        else:
            update_stats_dict = {
                'run_count': (current_task.run_count or 0) + 1,
                'success_count': (current_task.success_count or 0) + 1,
                'last_run_time': datetime.now(),
            }
        await TushareDownloadTaskDao.edit_task_dao(session, task_task_id, update_stats_dict)

    await session.commit()
    logger.info(
        f'流程任务 {task_name} 执行{"失败" if workflow_failed else "完成"}，'
        f'总记录数: {total_record_count}, 总耗时: {duration}秒'
    )


async def download_tushare_data(task_id: int, download_date: str | None = None, session: AsyncSession | None = None) -> None:
    """
    下载Tushare数据的异步任务函数

    :param task_id: 任务ID
    :param download_date: 下载日期（YYYYMMDD格式），如果为None则使用当前日期
    :param session: 可选的数据库会话，如果为None则创建新会话
    :return: None
    """
    start_time = datetime.now()
    task = None
    config = None
    log = None
    use_external_session = session is not None
    # 保存任务名称和配置信息，避免在异常处理中访问 ORM 对象导致延迟加载问题
    task_name = None
    config_id = None
    api_name = None

    try:
        if session is None:
            session_context = AsyncSessionLocal()
            session = await session_context.__aenter__()
        else:
            session_context = None
        
        try:
            # 获取任务信息
            task = await TushareDownloadTaskDao.get_task_detail_by_id(session, task_id)
            if not task:
                logger.error(f'任务ID {task_id} 不存在')
                return
            
            # 提前提取 task 对象的所有属性，避免在 commit 后访问 ORM 对象导致延迟加载问题
            try:
                await session.refresh(task)
            except Exception as refresh_error:
                logger.debug(f'刷新任务对象时出错（可能对象未过期）: {refresh_error}')
            
            # 直接从对象的 __dict__ 中提取属性，避免触发任何延迟加载
            task_dict = task.__dict__.copy()
            task_dict.pop('_sa_instance_state', None)
            
            # 保存任务名称和相关信息，避免在异常处理中访问 ORM 对象
            task_name = task_dict.get('task_name') or '未知任务'
            task_workflow_id = task_dict.get('workflow_id')
            # 提取任务参数，避免延迟加载问题
            task_params_str = task_dict.get('task_params')

            # 确定下载日期
            if download_date is None:
                download_date = datetime.now().strftime('%Y%m%d')

            # 如果任务有流程配置ID，执行流程；否则执行单个接口
            if task_workflow_id:
                await execute_workflow(session, task, download_date, task_params_str)
            else:
                await execute_single_api(session, task, download_date)

            logger.info(f'任务 {task_name} 执行完成')
        finally:
            # 如果使用的是外部会话，不关闭它；否则关闭内部创建的会话
            if session_context is not None:
                await session_context.__aexit__(None, None, None)

    except Exception as e:
        # 获取完整的异常堆栈信息
        error_traceback = traceback.format_exc()
        error_message = str(e)
        # 组合错误消息和堆栈信息，但限制长度（数据库字段可能有限制）
        full_error_message = f'{error_message}\n\n堆栈跟踪:\n{error_traceback}'
        # 限制错误消息长度（Text字段通常可以存储很大，但为了安全限制在5000字符）
        max_error_length = 5000
        if len(full_error_message) > max_error_length:
            full_error_message = full_error_message[:max_error_length] + '\n... (错误信息过长，已截断)'
        
        # 记录完整的异常信息到日志
        # 使用保存的 task_name，避免访问 ORM 对象导致延迟加载问题
        logger.exception(f'任务 {task_name if task_name else task_id} 执行失败: {error_message}')
        logger.error(f'任务异常堆栈:\n{error_traceback}')

        # 记录错误日志
        # 注意：如果在后台线程中，使用当前会话记录错误（如果可用）
        # 如果会话不可用或已关闭，则跳过错误日志记录（避免事件循环冲突）
        try:
            # 只有在会话可用时才记录错误日志
            # 检查会话是否可用：尝试访问会话的内部属性
            session_available = False
            if session is not None:
                try:
                    # 尝试访问会话的 bind 属性来检查会话是否可用
                    _ = session.bind
                    session_available = True
                except (AttributeError, RuntimeError):
                    session_available = False
            
            if session_available:
                try:
                    # 先回滚事务，确保可以执行新的操作
                    try:
                        await session.rollback()
                    except Exception as rollback_error:
                        logger.warning(f'回滚事务失败: {rollback_error}')
                    
                    # 使用保存的值，避免访问 ORM 对象
                    if task_name and config_id and api_name:
                        duration = int((datetime.now() - start_time).total_seconds())
                        
                        # 更新任务统计（使用字典方式，避免被排除列表影响）
                        error_task = await TushareDownloadTaskDao.get_task_detail_by_id(session, task_id)
                        if error_task:
                            update_stats_dict = {
                                'run_count': (error_task.run_count or 0) + 1,
                                'fail_count': (error_task.fail_count or 0) + 1,
                                'last_run_time': datetime.now()
                            }
                            await TushareDownloadTaskDao.edit_task_dao(session, task_id, update_stats_dict)

                        log = TushareDownloadLog(
                            task_id=task_id,
                            task_name=task_name,  # 使用保存的值
                            config_id=config_id,  # 使用保存的值
                            api_name=api_name,  # 使用保存的值
                            download_date=download_date,
                            record_count=0,
                            file_path=None,
                            status='1',
                            error_message=full_error_message,
                            duration=duration,
                            create_time=datetime.now(),
                        )

                        await TushareDownloadLogDao.add_log_dao(session, log)
                        await session.commit()
                except Exception as session_error:
                    # 如果使用当前会话失败，尝试创建新会话记录日志
                    logger.warning(f'使用当前会话记录错误日志失败: {session_error}')
                    try:
                        async with AsyncSessionLocal() as new_session:
                            if task_name and config_id and api_name:
                                duration = int((datetime.now() - start_time).total_seconds())
                                log = TushareDownloadLog(
                                    task_id=task_id,
                                    task_name=task_name,
                                    config_id=config_id,
                                    api_name=api_name,
                                    download_date=download_date,
                                    record_count=0,
                                    file_path=None,
                                    status='1',
                                    error_message=full_error_message,
                                    duration=duration,
                                    create_time=datetime.now(),
                                )
                                await TushareDownloadLogDao.add_log_dao(new_session, log)
                                await new_session.commit()
                    except Exception as new_session_error:
                        logger.error(f'使用新会话记录错误日志也失败: {new_session_error}')
            else:
                # 会话不可用，只记录到日志文件
                logger.warning('会话不可用，跳过数据库错误日志记录，错误信息已记录到日志文件')
        except Exception as log_error:
            logger.exception(f'记录错误日志失败: {log_error}')
            logger.error(f'记录错误日志异常堆栈:\n{traceback.format_exc()}')


def download_tushare_data_sync(task_id: int, download_date: str | None = None) -> None:
    """
    下载Tushare数据的同步任务函数（用于定时任务调度）
    在新线程中创建新的事件循环和数据库连接

    :param task_id: 任务ID
    :param download_date: 下载日期（YYYYMMDD格式），如果为None则使用当前日期
    :return: None
    """
    import asyncio
    from urllib.parse import quote_plus
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from config.env import DataBaseConfig
    
    # 在新线程中创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 在新线程中创建新的数据库引擎和会话
        # 这样可以避免事件循环冲突
        async_db_url = (
            f'mysql+asyncmy://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
            f'{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
        )
        if DataBaseConfig.db_type == 'postgresql':
            async_db_url = (
                f'postgresql+asyncpg://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
                f'{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
            )
        
        # 创建新的引擎，绑定到当前线程的事件循环
        thread_engine = create_async_engine(
            async_db_url,
            echo=DataBaseConfig.db_echo,
            max_overflow=DataBaseConfig.db_max_overflow,
            pool_size=DataBaseConfig.db_pool_size,
            pool_recycle=DataBaseConfig.db_pool_recycle,
            pool_timeout=DataBaseConfig.db_pool_timeout,
        )
        ThreadSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=thread_engine)
        
        # 使用新会话运行下载任务
        async def download_with_new_session():
            async with ThreadSessionLocal() as session:
                await download_tushare_data(task_id, download_date, session=session)
        
        # 运行异步函数
        loop.run_until_complete(download_with_new_session())
        
        # 清理引擎
        loop.run_until_complete(thread_engine.dispose())
    finally:
        # 清理事件循环
        loop.close()
