from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.constant import CommonConstant
from common.vo import CrudResponseModel
from exceptions.exception import ServiceException
from module_tushare.dao.tushare_dao import (
    TushareApiConfigDao,
    TushareDownloadLogDao,
    TushareDownloadTaskDao,
    TushareWorkflowConfigDao,
    TushareWorkflowStepDao,
)
from module_tushare.entity.do.tushare_do import TushareDownloadLog
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
    TushareDownloadTaskPageQueryModel,
    TushareWorkflowConfigModel,
    TushareWorkflowConfigPageQueryModel,
    TushareWorkflowConfigWithStepsModel,
    TushareWorkflowStepModel,
    TushareWorkflowStepPageQueryModel,
)
from utils.common_util import CamelCaseUtil
from utils.excel_util import ExcelUtil
from utils.log_util import logger


class TushareApiConfigService:
    """
    Tushare接口配置管理模块服务层
    """

    @classmethod
    async def get_config_list_services(
        cls, query_db: AsyncSession, query_object: TushareApiConfigPageQueryModel, is_page: bool = False
    ) -> Any:
        """
        获取接口配置列表信息service

        :param query_db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 接口配置列表信息对象
        """
        config_list_result = await TushareApiConfigDao.get_config_list(query_db, query_object, is_page)

        return config_list_result

    @classmethod
    async def check_config_unique_services(
        cls, query_db: AsyncSession, page_object: TushareApiConfigModel
    ) -> bool:
        """
        校验接口配置是否存在service

        :param query_db: orm对象
        :param page_object: 接口配置对象
        :return: 校验结果
        """
        config_id = -1 if page_object.config_id is None else page_object.config_id
        config = await TushareApiConfigDao.get_config_detail_by_info(query_db, page_object)
        if config and config.config_id != config_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_config_services(
        cls, query_db: AsyncSession, page_object: TushareApiConfigModel
    ) -> CrudResponseModel:
        """
        新增接口配置信息service

        :param query_db: orm对象
        :param page_object: 新增接口配置对象
        :return: 新增接口配置校验结果
        """
        if not await cls.check_config_unique_services(query_db, page_object):
            raise ServiceException(message=f'新增接口配置{page_object.api_name}失败，接口代码已存在')
        try:
            add_config = await TushareApiConfigDao.add_config_dao(query_db, page_object)
            await query_db.commit()
            result = {'is_success': True, 'message': '新增成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    def _deal_edit_config(cls, page_object: EditTushareApiConfigModel, edit_config: dict[str, Any]) -> None:
        """
        处理编辑接口配置字典

        :param page_object: 编辑接口配置对象
        :param edit_config: 编辑接口配置字典
        """
        if page_object.type == 'status':
            # 只更新状态字段
            edit_config.clear()
            edit_config['status'] = page_object.status
        else:
            # model_dump已经包含了所有字段，这里主要处理特殊逻辑
            # 处理主键字段：空字符串转换为None，确保能正确保存和清空
            if 'primary_key_fields' in edit_config:
                primary_key_value = edit_config['primary_key_fields']
                if primary_key_value is not None and isinstance(primary_key_value, str) and primary_key_value.strip() == '':
                    edit_config['primary_key_fields'] = None
            elif hasattr(page_object, 'primary_key_fields'):
                # 如果不在字典中，尝试从page_object获取
                if page_object.primary_key_fields is not None and isinstance(page_object.primary_key_fields, str) and page_object.primary_key_fields.strip() == '':
                    edit_config['primary_key_fields'] = None
                else:
                    edit_config['primary_key_fields'] = page_object.primary_key_fields
            # 确保关键字段被正确设置（覆盖model_dump的结果，确保使用page_object的最新值）
            # 这样可以确保即使前端没有发送某些字段，也能使用page_object中的值
            edit_config['api_name'] = page_object.api_name
            edit_config['api_code'] = page_object.api_code
            edit_config['api_desc'] = page_object.api_desc
            edit_config['api_params'] = page_object.api_params
            edit_config['data_fields'] = page_object.data_fields
            edit_config['status'] = page_object.status
            edit_config['remark'] = page_object.remark
            # 确保更新时间和更新者被设置
            if hasattr(page_object, 'update_by') and page_object.update_by:
                edit_config['update_by'] = page_object.update_by
            if hasattr(page_object, 'update_time') and page_object.update_time:
                edit_config['update_time'] = page_object.update_time

    @classmethod
    async def edit_config_services(
        cls, query_db: AsyncSession, page_object: EditTushareApiConfigModel
    ) -> CrudResponseModel:
        """
        编辑接口配置信息service

        :param query_db: orm对象
        :param page_object: 编辑接口配置对象
        :return: 编辑接口配置校验结果
        """
        # 验证config_id是否存在
        if not page_object.config_id:
            logger.error(f'config_id为空或无效: {page_object.config_id}')
            raise ServiceException(message='接口配置ID不能为空，无法执行更新操作')
        
        old_config = await TushareApiConfigDao.get_config_detail_by_id(query_db, page_object.config_id)
        if not old_config:
            raise ServiceException(message='接口配置不存在')
        if page_object.type != 'status':
            check_config = TushareApiConfigModel(
                config_id=page_object.config_id,
                api_code=page_object.api_code,
            )
            if not await cls.check_config_unique_services(query_db, check_config):
                raise ServiceException(message=f'编辑接口配置{page_object.api_name}失败，接口代码已存在')
        try:
            # 验证config_id不为None
            if page_object.config_id is None:
                raise ServiceException(message='接口配置ID不能为空，无法执行更新操作')
            
            # 处理主键字段：空字符串转换为None，确保能正确保存和清空
            primary_key_fields_value = page_object.primary_key_fields
            if primary_key_fields_value is not None and isinstance(primary_key_fields_value, str) and primary_key_fields_value.strip() == '':
                primary_key_fields_value = None
            
            # 使用model_dump获取所有字段值，使用by_alias=False确保使用snake_case字段名
            # 排除type字段，因为它只是操作类型标识，不需要保存到数据库
            edit_config_dict = page_object.model_dump(
                exclude={'type'},
                exclude_none=False,
                by_alias=False
            )
            
            # 确保config_id在字典中
            edit_config_dict['config_id'] = page_object.config_id
            
            # 处理需要特殊处理的字段
            edit_config_dict['primary_key_fields'] = primary_key_fields_value
            # 保留原有的创建信息
            edit_config_dict['create_by'] = old_config.create_by if old_config.create_by else None
            edit_config_dict['create_time'] = old_config.create_time if old_config.create_time else None
            
            # 调用_deal_edit_config处理编辑逻辑
            cls._deal_edit_config(page_object, edit_config_dict)
            
            # 验证config_id在字典中且不为None
            config_id = edit_config_dict.get('config_id')
            if config_id is None:
                logger.error(f'edit_config_dict中config_id为None。edit_config_dict: {edit_config_dict}')
                raise ServiceException(message='接口配置ID验证失败，edit_config_dict中config_id为None')
            
            # 直接使用字典更新，避免模型对象创建时的字段映射问题
            await TushareApiConfigDao.edit_config_dao(query_db, config_id, edit_config_dict)
            await query_db.commit()
            result = {'is_success': True, 'message': '编辑成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def delete_config_services(
        cls, query_db: AsyncSession, page_object: DeleteTushareApiConfigModel
    ) -> CrudResponseModel:
        """
        删除接口配置信息service

        :param query_db: orm对象
        :param page_object: 删除接口配置对象
        :return: 删除接口配置校验结果
        """
        config_ids = [int(config_id) for config_id in page_object.config_ids.split(',')]
        try:
            await TushareApiConfigDao.delete_config_dao(query_db, config_ids)
            await query_db.commit()
            result = {'is_success': True, 'message': '删除成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def config_detail_services(cls, query_db: AsyncSession, config_id: int) -> TushareApiConfigModel:
        """
        获取接口配置详细信息service

        :param query_db: orm对象
        :param config_id: 接口配置id
        :return: 接口配置详细信息对象
        """
        config = await TushareApiConfigDao.get_config_detail_by_id(query_db, config_id)
        result = TushareApiConfigModel(**CamelCaseUtil.transform_result(config)) if config else TushareApiConfigModel()

        return result

    @classmethod
    async def export_config_list_services(cls, request: Request, config_list: list) -> bytes:
        """
        导出接口配置列表信息service

        :param request: Request对象
        :param config_list: 接口配置列表信息
        :return: 接口配置列表excel文件流
        """
        excel_data = [
            ['配置ID', '接口名称', '接口代码', '接口描述', '状态', '创建时间', '备注'],
        ]
        for config_item in config_list:
            excel_data.append(
                [
                    config_item.get('config_id'),
                    config_item.get('api_name'),
                    config_item.get('api_code'),
                    config_item.get('api_desc'),
                    '正常' if config_item.get('status') == '0' else '停用',
                    config_item.get('create_time'),
                    config_item.get('remark'),
                ]
            )
        excel_stream = ExcelUtil.create_excel(excel_data=excel_data, sheet_name='接口配置列表')

        return excel_stream


class TushareDownloadTaskService:
    """
    Tushare下载任务管理模块服务层
    """

    @classmethod
    async def get_task_list_services(
        cls, query_db: AsyncSession, query_object: TushareDownloadTaskPageQueryModel, is_page: bool = False
    ) -> Any:
        """
        获取下载任务列表信息service

        :param query_db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 下载任务列表信息对象
        """
        task_list_result = await TushareDownloadTaskDao.get_task_list(query_db, query_object, is_page)

        # 为每个任务添加任务类型信息
        if isinstance(task_list_result, dict) and 'rows' in task_list_result:
            # 分页结果
            for task in task_list_result['rows']:
                if isinstance(task, dict):
                    task['task_type'] = 'workflow' if task.get('workflow_id') else 'single'
        elif isinstance(task_list_result, list):
            # 列表结果
            for task in task_list_result:
                if isinstance(task, dict):
                    task['task_type'] = 'workflow' if task.get('workflow_id') else 'single'

        return task_list_result

    @classmethod
    async def check_task_unique_services(
        cls, query_db: AsyncSession, page_object: TushareDownloadTaskModel
    ) -> bool:
        """
        校验下载任务是否存在service

        :param query_db: orm对象
        :param page_object: 下载任务对象
        :return: 校验结果
        """
        task_id = -1 if page_object.task_id is None else page_object.task_id
        task = await TushareDownloadTaskDao.get_task_detail_by_info(query_db, page_object)
        if task and task.task_id != task_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_task_services(
        cls, query_db: AsyncSession, page_object: TushareDownloadTaskModel
    ) -> CrudResponseModel:
        """
        新增下载任务信息service

        :param query_db: orm对象
        :param page_object: 新增下载任务对象
        :return: 新增下载任务校验结果
        """
        if not await cls.check_task_unique_services(query_db, page_object):
            raise ServiceException(message=f'新增下载任务{page_object.task_name}失败，任务名称已存在')
        try:
            # 验证必要字段
            if not page_object.task_name or (isinstance(page_object.task_name, str) and not page_object.task_name.strip()):
                raise ServiceException(message='任务名称不能为空')
            
            # 处理cron_expression：空字符串转换为None
            if page_object.cron_expression:
                page_object.cron_expression = (
                    page_object.cron_expression.strip()
                    if page_object.cron_expression.strip()
                    else None
                )
            else:
                page_object.cron_expression = None
            
            logger.info(f'[新增任务] 处理后的task_name: {page_object.task_name}, 类型: {type(page_object.task_name)}')
            
            # 再次确保 task_name 不为空
            if not page_object.task_name or (isinstance(page_object.task_name, str) and not page_object.task_name.strip()):
                raise ServiceException(message='任务名称不能为空')
            
            # 直接使用原始模型对象，避免重新创建导致字段丢失
            # 使用DAO层方法添加任务
            add_task = await TushareDownloadTaskDao.add_task_dao(query_db, page_object)
            await query_db.commit()
            
            # 如果任务配置了cron表达式且状态为启用，注册到调度器
            # 从原始 page_object 中获取值，避免访问 ORM 对象的延迟加载属性导致 greenlet 错误
            cron_expr = page_object.cron_expression
            task_status = page_object.status
            if cron_expr and cron_expr.strip() and task_status == '0':
                # 延迟导入，避免循环导入
                from module_tushare.service.tushare_scheduler_service import TushareSchedulerService
                # 直接使用原始的 page_object，确保所有字段都正确
                TushareSchedulerService.register_task_scheduler(page_object)
            
            result = {'is_success': True, 'message': '新增成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    def _deal_edit_task(cls, page_object: EditTushareDownloadTaskModel, edit_task: dict[str, Any]) -> None:
        """
        处理编辑下载任务字典

        :param page_object: 编辑下载任务对象
        :param edit_task: 编辑下载任务字典
        """
        logger.info(f'[_deal_edit_task] 开始处理，type: {page_object.type}')
        logger.info(f'[_deal_edit_task] page_object.cron_expression: {page_object.cron_expression}, 类型: {type(page_object.cron_expression)}')
        
        if page_object.type == 'status':
            edit_task['status'] = page_object.status
            logger.info(f'[_deal_edit_task] 只更新状态: {page_object.status}')
        else:
            edit_task['task_name'] = page_object.task_name
            edit_task['config_id'] = page_object.config_id
            # 处理cron_expression：空字符串转换为None
            original_cron = page_object.cron_expression
            if original_cron and isinstance(original_cron, str) and original_cron.strip():
                edit_task['cron_expression'] = original_cron.strip()
                logger.info(f'[_deal_edit_task] cron_expression处理: "{original_cron}" -> "{edit_task["cron_expression"]}"')
            else:
                edit_task['cron_expression'] = None
                logger.info(f'[_deal_edit_task] cron_expression处理: "{original_cron}" -> None')
            
            edit_task['start_date'] = page_object.start_date
            edit_task['end_date'] = page_object.end_date
            edit_task['task_params'] = page_object.task_params
            edit_task['save_path'] = page_object.save_path
            edit_task['save_format'] = page_object.save_format
            edit_task['save_to_db'] = page_object.save_to_db
            edit_task['data_table_name'] = page_object.data_table_name
            edit_task['status'] = page_object.status
            edit_task['remark'] = page_object.remark
            
            logger.info(f'[_deal_edit_task] 处理完成，cron_expression最终值: {edit_task.get("cron_expression")}')

    @classmethod
    async def edit_task_services(
        cls, query_db: AsyncSession, page_object: EditTushareDownloadTaskModel
    ) -> CrudResponseModel:
        """
        编辑下载任务信息service

        :param query_db: orm对象
        :param page_object: 编辑下载任务对象
        :return: 编辑下载任务校验结果
        """
        logger.info(f'[编辑任务] 开始编辑任务，task_id: {page_object.task_id}, type: {page_object.type}')
        logger.info(f'[编辑任务] 接收到的数据: {page_object.model_dump(by_alias=True)}')
        
        old_task = await TushareDownloadTaskDao.get_task_detail_by_id(query_db, page_object.task_id)
        if not old_task:
            logger.error(f'[编辑任务] 任务不存在，task_id: {page_object.task_id}')
            raise ServiceException(message='下载任务不存在')
        
        # 刷新对象以确保所有属性都已加载，避免延迟加载导致的 greenlet 错误
        await query_db.refresh(old_task)
        logger.info(f'[编辑任务] 原始任务数据: task_name={old_task.task_name}, cron_expression={old_task.cron_expression}')
        
        # 检测主键匹配问题（如果 config_id 或 data_table_name 发生变化）
        if page_object.type != 'status':
            config_changed = page_object.config_id is not None and page_object.config_id != old_task.config_id
            table_name_changed = page_object.data_table_name is not None and page_object.data_table_name != old_task.data_table_name
            
            if config_changed or table_name_changed:
                # 延迟导入，避免循环导入
                from module_tushare.dao.tushare_dao import TushareApiConfigDao, TushareDataDao
                from sqlalchemy import text
                from config.env import DataBaseConfig
                
                # 获取新接口配置
                new_config = None
                if config_changed and page_object.config_id:
                    new_config = await TushareApiConfigDao.get_config_detail_by_id(query_db, page_object.config_id)
                
                # 确定要检查的表名
                check_table_name = page_object.data_table_name if table_name_changed else old_task.data_table_name
                if not check_table_name or check_table_name.strip() == '':
                    if new_config:
                        check_table_name = f'tushare_{new_config.api_code}'
                    elif old_task.config_id:
                        old_config = await TushareApiConfigDao.get_config_detail_by_id(query_db, old_task.config_id)
                        if old_config:
                            check_table_name = f'tushare_{old_config.api_code}'
                
                # 检查表是否存在
                if check_table_name:
                    table_exists = False
                    if DataBaseConfig.db_type == 'postgresql':
                        check_sql = """
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name = :table_name
                            )
                        """
                    else:
                        check_sql = """
                            SELECT COUNT(*) as count
                            FROM information_schema.tables 
                            WHERE table_schema = DATABASE()
                            AND table_name = :table_name
                        """
                    
                    result = await query_db.execute(text(check_sql), {'table_name': check_table_name})
                    if DataBaseConfig.db_type == 'postgresql':
                        table_exists = result.scalar()
                    else:
                        table_exists = result.scalar() > 0
                    
                    # 如果表已存在，检测主键匹配
                    if table_exists and new_config:
                        table_pk = await TushareDataDao.detect_unique_keys(query_db, check_table_name)
                        config_pk = None
                        if new_config.primary_key_fields:
                            import json
                            try:
                                config_pk = json.loads(new_config.primary_key_fields)
                                if not isinstance(config_pk, list):
                                    config_pk = None
                            except (json.JSONDecodeError, TypeError):
                                config_pk = None
                        
                        # 如果表主键与接口配置主键不匹配，给出警告
                        if config_pk and table_pk:
                            # 转换为集合进行比较（忽略顺序）
                            if set(config_pk) != set(table_pk):
                                logger.warning(
                                    f'[编辑任务] 表 {check_table_name} 的主键 ({table_pk}) 与接口配置的主键 ({config_pk}) 不匹配。'
                                    f'系统将使用表实际主键进行数据更新操作。'
                                )
                        elif config_pk and not table_pk:
                            logger.warning(
                                f'[编辑任务] 接口配置了主键字段 ({config_pk})，但表 {check_table_name} 没有主键。'
                                f'系统将使用接口配置的主键进行数据更新操作。'
                            )
                        elif not config_pk and table_pk:
                            logger.info(
                                f'[编辑任务] 表 {check_table_name} 有主键 ({table_pk})，但接口配置未指定主键字段。'
                                f'系统将使用表实际主键进行数据更新操作。'
                            )
        
        if page_object.type != 'status':
            check_task = TushareDownloadTaskModel(
                task_id=page_object.task_id,
                task_name=page_object.task_name,
            )
            if not await cls.check_task_unique_services(query_db, check_task):
                logger.error(f'[编辑任务] 任务名称已存在: {page_object.task_name}')
                raise ServiceException(message=f'编辑下载任务{page_object.task_name}失败，任务名称已存在')
        try:
            # 先获取所有字段（包括None值），使用by_alias=False确保使用snake_case键名
            # 排除不应该在编辑时更新的字段：统计字段和创建相关字段
            edit_task_dict = page_object.model_dump(
                exclude={
                    'task_id', 'type',
                    'last_run_time', 'next_run_time', 'run_count', 'success_count', 'fail_count',
                    'create_by', 'create_time'
                },
                exclude_none=False,
                by_alias=False
            )
            logger.info(f'[编辑任务] model_dump后的字典: {edit_task_dict}')
            
            cls._deal_edit_task(page_object, edit_task_dict)
            logger.info(f'[编辑任务] _deal_edit_task处理后的字典: {edit_task_dict}')
            
            # 添加 update_by 和 update_time 到字典中
            edit_task_dict['update_by'] = page_object.update_by
            edit_task_dict['update_time'] = page_object.update_time
            # 添加 task_id 用于更新条件
            edit_task_dict['task_id'] = page_object.task_id
            logger.info(f'[编辑任务] 最终更新字典: {edit_task_dict}')
            logger.info(f'[编辑任务] 准备直接使用字典更新，task_id: {page_object.task_id}')
            
            # 直接使用字典更新，避免模型转换时的字段名问题
            result_id = await TushareDownloadTaskDao.edit_task_dao(query_db, page_object.task_id, edit_task_dict)
            logger.info(f'[编辑任务] DAO更新返回的task_id: {result_id}')
            
            await query_db.commit()
            logger.info(f'[编辑任务] 事务提交成功')
            
            # 验证更新结果
            updated_task = await TushareDownloadTaskDao.get_task_detail_by_id(query_db, page_object.task_id)
            if updated_task:
                # 刷新对象以确保所有属性都已加载，避免延迟加载导致的 greenlet 错误
                await query_db.refresh(updated_task)
                logger.info(f'[编辑任务] 更新后的任务数据: task_name={updated_task.task_name}, cron_expression={updated_task.cron_expression}')
                
                # 更新调度器中的任务
                # 延迟导入，避免循环导入
                from module_tushare.service.tushare_scheduler_service import TushareSchedulerService
                # 使用刷新后的对象创建模型，确保所有属性都已加载
                updated_task_model = TushareDownloadTaskModel(**CamelCaseUtil.transform_result(updated_task))
                old_task_model = TushareDownloadTaskModel(**CamelCaseUtil.transform_result(old_task))
                TushareSchedulerService.update_task_scheduler(updated_task_model, old_task_model)
            else:
                logger.warning(f'[编辑任务] 更新后无法获取任务数据，task_id: {page_object.task_id}')
            
            result = {'is_success': True, 'message': '编辑成功'}
        except Exception as e:
            logger.exception(f'[编辑任务] 编辑任务失败，task_id: {page_object.task_id}, 错误: {str(e)}')
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def delete_task_services(
        cls, query_db: AsyncSession, page_object: DeleteTushareDownloadTaskModel
    ) -> CrudResponseModel:
        """
        删除下载任务信息service

        :param query_db: orm对象
        :param page_object: 删除下载任务对象
        :return: 删除下载任务校验结果
        """
        task_ids = [int(task_id) for task_id in page_object.task_ids.split(',')]
        try:
            # 在删除前，先从调度器移除任务
            # 延迟导入，避免循环导入
            from module_tushare.service.tushare_scheduler_service import TushareSchedulerService
            for task_id in task_ids:
                TushareSchedulerService.remove_task_scheduler(task_id)
            
            await TushareDownloadTaskDao.delete_task_dao(query_db, task_ids)
            await query_db.commit()
            result = {'is_success': True, 'message': '删除成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def task_detail_services(cls, query_db: AsyncSession, task_id: int) -> TushareDownloadTaskModel:
        """
        获取下载任务详细信息service

        :param query_db: orm对象
        :param task_id: 下载任务id
        :return: 下载任务详细信息对象
        """
        from module_tushare.entity.vo.tushare_vo import TushareDownloadTaskDetailModel
        
        task = await TushareDownloadTaskDao.get_task_detail_by_id(query_db, task_id)
        if not task:
            return TushareDownloadTaskModel()
        
        task_dict = CamelCaseUtil.transform_result(task)
        
        # 判断任务类型并获取关联信息
        if task.workflow_id:
            # 流程配置任务
            workflow = await TushareWorkflowConfigDao.get_workflow_detail_by_id(query_db, task.workflow_id)
            steps = await TushareWorkflowStepDao.get_steps_by_workflow_id(query_db, task.workflow_id)
            
            task_dict['task_type'] = 'workflow'
            if workflow:
                task_dict['workflow_name'] = workflow.workflow_name
                task_dict['workflow_desc'] = workflow.workflow_desc
            task_dict['step_count'] = len(steps) if steps else 0
            if steps:
                from module_tushare.entity.vo.tushare_vo import TushareWorkflowStepModel
                task_dict['steps'] = [
                    TushareWorkflowStepModel(**CamelCaseUtil.transform_result(step)).model_dump()
                    for step in steps
                ]
        else:
            # 单个接口任务
            config = await TushareApiConfigDao.get_config_detail_by_id(query_db, task.config_id)
            task_dict['task_type'] = 'single'
            if config:
                task_dict['api_name'] = config.api_name
                task_dict['api_code'] = config.api_code
        
        result = TushareDownloadTaskDetailModel(**task_dict)
        return result

    @classmethod
    async def execute_task_services(cls, query_db: AsyncSession, task_id: int) -> CrudResponseModel:
        """
        执行下载任务service

        :param query_db: orm对象
        :param task_id: 下载任务id
        :return: 执行任务结果
        """
        from fastapi import BackgroundTasks
        from module_tushare.task.tushare_download_task import download_tushare_data_sync
        
        # 检查任务是否存在
        task = await TushareDownloadTaskDao.get_task_detail_by_id(query_db, task_id)
        if not task:
            raise ServiceException(message='下载任务不存在')
        
        if task.status != '0':
            raise ServiceException(message='任务已暂停，无法执行')
        
        try:
            # 异步执行任务（使用同步包装函数，在后台线程中执行）
            import threading
            import traceback
            
            def run_task():
                try:
                    download_tushare_data_sync(task_id)
                except Exception as e:
                    error_traceback = traceback.format_exc()
                    logger.exception(f'执行任务 {task_id} 失败: {e}')
                    logger.error(f'任务执行异常堆栈:\n{error_traceback}')
            
            # 在后台线程中执行任务
            thread = threading.Thread(target=run_task, daemon=True)
            thread.start()
            
            result = {'is_success': True, 'message': '任务已提交执行，请稍后查看执行日志'}
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.exception(f'提交任务执行失败: {e}')
            logger.error(f'提交任务异常堆栈:\n{error_traceback}')
            raise ServiceException(message=f'提交任务执行失败: {str(e)}')

        return CrudResponseModel(**result)

    @classmethod
    async def get_task_statistics_services(
        cls, query_db: AsyncSession, task_id: int
    ) -> dict[str, Any]:
        """
        获取任务执行统计信息service（区分单个接口和流程配置）

        :param query_db: orm对象
        :param task_id: 任务ID
        :return: 任务执行统计信息
        """
        from sqlalchemy import func, select, Integer, cast
        from module_tushare.entity.do.tushare_do import TushareDownloadLog
        
        # 获取任务信息
        task = await TushareDownloadTaskDao.get_task_detail_by_id(query_db, task_id)
        if not task:
            raise ServiceException(message='任务不存在')
        
        # 判断任务类型
        task_type = 'workflow' if task.workflow_id else 'single'
        
        # 获取日志统计
        log_stats_query = (
            select(
                func.count(TushareDownloadLog.log_id).label('total_count'),
                func.sum(cast(TushareDownloadLog.status == '0', Integer)).label('success_count'),
                func.sum(cast(TushareDownloadLog.status == '1', Integer)).label('fail_count'),
                func.sum(TushareDownloadLog.record_count).label('total_records'),
                func.avg(TushareDownloadLog.duration).label('avg_duration'),
            )
            .where(TushareDownloadLog.task_id == task_id)
        )
        
        log_stats_result = await query_db.execute(log_stats_query)
        log_stats = log_stats_result.first()
        
        statistics = {
            'task_id': task_id,
            'task_name': task.task_name,
            'task_type': task_type,
            'run_count': task.run_count or 0,
            'success_count': task.success_count or 0,
            'fail_count': task.fail_count or 0,
            'last_run_time': task.last_run_time.isoformat() if task.last_run_time else None,
            'log_statistics': {
                'total_logs': log_stats.total_count or 0,
                'success_logs': log_stats.success_count or 0,
                'fail_logs': log_stats.fail_count or 0,
                'total_records': log_stats.total_records or 0,
                'avg_duration': round(log_stats.avg_duration, 2) if log_stats.avg_duration else 0,
            },
        }
        
        # 如果是流程配置任务，获取步骤统计
        if task_type == 'workflow' and task.workflow_id:
            from module_tushare.dao.tushare_dao import TushareWorkflowStepDao
            steps = await TushareWorkflowStepDao.get_steps_by_workflow_id(query_db, task.workflow_id)
            
            step_statistics = []
            for step in steps:
                step_log_query = (
                    select(
                        func.count(TushareDownloadLog.log_id).label('count'),
                        func.sum(cast(TushareDownloadLog.status == '0', Integer)).label('success'),
                        func.sum(cast(TushareDownloadLog.status == '1', Integer)).label('fail'),
                        func.sum(TushareDownloadLog.record_count).label('records'),
                    )
                    .where(
                        TushareDownloadLog.task_id == task_id,
                        TushareDownloadLog.task_name.like(f'%[{step.step_name}]%')
                    )
                )
                step_log_result = await query_db.execute(step_log_query)
                step_log = step_log_result.first()
                
                step_statistics.append({
                    'step_id': step.step_id,
                    'step_name': step.step_name,
                    'step_order': step.step_order,
                    'log_count': step_log.count or 0,
                    'success_count': step_log.success or 0,
                    'fail_count': step_log.fail or 0,
                    'total_records': step_log.records or 0,
                })
            
            statistics['step_statistics'] = step_statistics
        
        return statistics


class TushareDownloadLogService:
    """
    Tushare下载日志管理模块服务层
    """

    @classmethod
    async def get_log_list_services(
        cls, query_db: AsyncSession, query_object: TushareDownloadLogPageQueryModel, is_page: bool = False
    ) -> Any:
        """
        获取下载日志列表信息service

        :param query_db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 下载日志列表信息对象
        """
        log_list_result = await TushareDownloadLogDao.get_log_list(query_db, query_object, is_page)

        # 为每个日志添加任务类型信息（通过task_name判断：包含[的是流程配置任务）
        if isinstance(log_list_result, dict) and 'rows' in log_list_result:
            # 分页结果
            for log in log_list_result['rows']:
                if isinstance(log, dict):
                    task_name = log.get('task_name', '')
                    log['task_type'] = 'workflow' if '[' in task_name else 'single'
                    # 如果是流程配置任务，提取步骤名称
                    if '[' in task_name and ']' in task_name:
                        step_name = task_name[task_name.index('[') + 1:task_name.index(']')]
                        log['step_name'] = step_name
        elif isinstance(log_list_result, list):
            # 列表结果
            for log in log_list_result:
                if isinstance(log, dict):
                    task_name = log.get('task_name', '')
                    log['task_type'] = 'workflow' if '[' in task_name else 'single'
                    # 如果是流程配置任务，提取步骤名称
                    if '[' in task_name and ']' in task_name:
                        step_name = task_name[task_name.index('[') + 1:task_name.index(']')]
                        log['step_name'] = step_name

        return log_list_result

    @classmethod
    async def add_log_services(cls, query_db: AsyncSession, log: TushareDownloadLog) -> CrudResponseModel:
        """
        新增下载日志信息service

        :param query_db: orm对象
        :param log: 下载日志对象
        :return: 新增下载日志校验结果
        """
        try:
            add_log = await TushareDownloadLogDao.add_log_dao(query_db, log)
            await query_db.commit()
            result = {'is_success': True, 'message': '新增成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def delete_log_services(
        cls, query_db: AsyncSession, page_object: DeleteTushareDownloadLogModel
    ) -> CrudResponseModel:
        """
        删除下载日志信息service

        :param query_db: orm对象
        :param page_object: 删除下载日志对象
        :return: 删除下载日志校验结果
        """
        log_ids = [int(log_id) for log_id in page_object.log_ids.split(',')]
        try:
            await TushareDownloadLogDao.delete_log_dao(query_db, log_ids)
            await query_db.commit()
            result = {'is_success': True, 'message': '删除成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def clear_log_services(cls, query_db: AsyncSession) -> CrudResponseModel:
        """
        清空下载日志信息service

        :param query_db: orm对象
        :return: 清空下载日志校验结果
        """
        try:
            await TushareDownloadLogDao.clear_log_dao(query_db)
            await query_db.commit()
            result = {'is_success': True, 'message': '清空成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)


class TushareWorkflowConfigService:
    """
    Tushare流程配置管理模块服务层
    """

    @classmethod
    async def get_workflow_list_services(
        cls, query_db: AsyncSession, query_object: TushareWorkflowConfigPageQueryModel, is_page: bool = False
    ) -> Any:
        """
        获取流程配置列表信息service

        :param query_db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 流程配置列表信息对象
        """
        workflow_list_result = await TushareWorkflowConfigDao.get_workflow_list(query_db, query_object, is_page)

        return workflow_list_result

    @classmethod
    async def check_workflow_unique_services(
        cls, query_db: AsyncSession, page_object: TushareWorkflowConfigModel
    ) -> bool:
        """
        校验流程配置是否存在service

        :param query_db: orm对象
        :param page_object: 流程配置对象
        :return: 校验结果
        """
        workflow_id = -1 if page_object.workflow_id is None else page_object.workflow_id
        workflow = await TushareWorkflowConfigDao.get_workflow_detail_by_info(query_db, page_object)
        if workflow and workflow.workflow_id != workflow_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_workflow_services(
        cls, query_db: AsyncSession, page_object: TushareWorkflowConfigModel
    ) -> CrudResponseModel:
        """
        新增流程配置信息service

        :param query_db: orm对象
        :param page_object: 新增流程配置对象
        :return: 新增流程配置校验结果
        """
        if not await cls.check_workflow_unique_services(query_db, page_object):
            raise ServiceException(message=f'新增流程配置{page_object.workflow_name}失败，流程名称已存在')
        try:
            add_workflow = await TushareWorkflowConfigDao.add_workflow_dao(query_db, page_object)
            await query_db.commit()
            result = {'is_success': True, 'message': '新增成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    def _deal_edit_workflow(
        cls, page_object: EditTushareWorkflowConfigModel, edit_workflow: dict[str, Any]
    ) -> None:
        """
        处理编辑流程配置字典

        :param page_object: 编辑流程配置对象
        :param edit_workflow: 编辑流程配置字典
        """
        if page_object.workflow_name is not None:
            edit_workflow['workflow_name'] = page_object.workflow_name
        if page_object.workflow_desc is not None:
            edit_workflow['workflow_desc'] = page_object.workflow_desc
        if page_object.status is not None:
            edit_workflow['status'] = page_object.status
        if page_object.remark is not None:
            edit_workflow['remark'] = page_object.remark

    @classmethod
    async def edit_workflow_services(
        cls, query_db: AsyncSession, page_object: EditTushareWorkflowConfigModel
    ) -> CrudResponseModel:
        """
        编辑流程配置信息service

        :param query_db: orm对象
        :param page_object: 编辑流程配置对象
        :return: 编辑流程配置校验结果
        """
        # 校验ID是否存在
        if not page_object.workflow_id:
            raise ServiceException(message='流程配置ID不能为空，无法执行更新操作')

        old_workflow = await TushareWorkflowConfigDao.get_workflow_detail_by_id(query_db, page_object.workflow_id)
        if not old_workflow:
            raise ServiceException(message='流程配置不存在')

        # 如果名称发生变化，做唯一性校验，保证“不允许重名”
        if page_object.workflow_name and page_object.workflow_name != old_workflow.workflow_name:
            check_workflow = TushareWorkflowConfigModel(
                workflowId=page_object.workflow_id,
                workflowName=page_object.workflow_name,
            )
            if not await cls.check_workflow_unique_services(query_db, check_workflow):
                raise ServiceException(message=f'编辑流程配置{page_object.workflow_name}失败，流程名称已存在')

        try:
            # 使用model_dump获取所有字段值，使用by_alias=False确保使用snake_case字段名
            # 排除type字段，因为它只是操作类型标识，不需要保存到数据库
            edit_workflow_dict = page_object.model_dump(
                exclude={'type'},
                exclude_none=False,
                by_alias=False,
            )

            # 确保workflow_id在字典中
            workflow_id = edit_workflow_dict.get('workflow_id')
            if workflow_id is None:
                raise ServiceException(message='流程配置ID验证失败，edit_workflow_dict中workflow_id为None')

            # 保留原有的创建信息
            edit_workflow_dict['create_by'] = old_workflow.create_by if old_workflow.create_by else None
            edit_workflow_dict['create_time'] = old_workflow.create_time if old_workflow.create_time else None

            # 应用字段精细更新逻辑（只覆盖明确允许编辑的字段）
            cls._deal_edit_workflow(page_object, edit_workflow_dict)

            # 直接使用字典更新，避免模型对象创建时的字段映射问题
            await TushareWorkflowConfigDao.edit_workflow_dao(query_db, workflow_id, edit_workflow_dict)
            await query_db.commit()
            result = {'is_success': True, 'message': '编辑成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def delete_workflow_services(
        cls, query_db: AsyncSession, page_object: DeleteTushareWorkflowConfigModel
    ) -> CrudResponseModel:
        """
        删除流程配置信息service

        :param query_db: orm对象
        :param page_object: 删除流程配置对象
        :return: 删除流程配置校验结果
        """
        workflow_ids = [int(workflow_id) for workflow_id in page_object.workflow_ids.split(',')]
        try:
            # 先删除关联的步骤
            for workflow_id in workflow_ids:
                await TushareWorkflowStepDao.delete_steps_by_workflow_id(query_db, workflow_id)
            # 再删除流程配置
            await TushareWorkflowConfigDao.delete_workflow_dao(query_db, workflow_ids)
            await query_db.commit()
            result = {'is_success': True, 'message': '删除成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def workflow_base_detail_services(
        cls, query_db: AsyncSession, workflow_id: int
    ) -> TushareWorkflowConfigModel:
        """
        获取流程配置基础信息service（不包含步骤列表，主要用于前端表单编辑回显）

        :param query_db: orm对象
        :param workflow_id: 流程配置id
        :return: 流程配置基础信息对象
        """
        workflow = await TushareWorkflowConfigDao.get_workflow_detail_by_id(query_db, workflow_id)
        if not workflow:
            return TushareWorkflowConfigModel()

        workflow_model = TushareWorkflowConfigModel(**CamelCaseUtil.transform_result(workflow))
        return workflow_model

    @classmethod
    async def workflow_detail_services(
        cls, query_db: AsyncSession, workflow_id: int
    ) -> TushareWorkflowConfigWithStepsModel:
        """
        获取流程配置详细信息service（包含步骤列表）

        :param query_db: orm对象
        :param workflow_id: 流程配置id
        :return: 流程配置详细信息对象
        """
        workflow = await TushareWorkflowConfigDao.get_workflow_detail_by_id(query_db, workflow_id)
        if not workflow:
            return TushareWorkflowConfigWithStepsModel()

        # 先构建基础流程模型
        workflow_model = TushareWorkflowConfigModel(**CamelCaseUtil.transform_result(workflow))

        # 获取步骤列表，这里增加保护，避免数据库或异步环境异常导致整个详情接口直接500
        step_models: list[TushareWorkflowStepModel] = []
        try:
            steps = await TushareWorkflowStepDao.get_steps_by_workflow_id(query_db, workflow_id)
            step_models = [
                TushareWorkflowStepModel(**CamelCaseUtil.transform_result(step)) for step in steps
            ]
        except Exception as e:
            # 记录错误日志，但不影响基础流程信息返回
            from utils.log_util import logger

            logger.exception(f'获取流程 {workflow_id} 步骤列表失败: {e}')
            step_models = []

        return TushareWorkflowConfigWithStepsModel(**workflow_model.model_dump(), steps=step_models)


class TushareWorkflowStepService:
    """
    Tushare流程步骤管理模块服务层
    """

    @classmethod
    async def get_step_list_services(
        cls, query_db: AsyncSession, query_object: TushareWorkflowStepPageQueryModel, is_page: bool = False
    ) -> Any:
        """
        获取流程步骤列表信息service

        :param query_db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 流程步骤列表信息对象
        """
        step_list_result = await TushareWorkflowStepDao.get_step_list(query_db, query_object, is_page)

        return step_list_result

    @classmethod
    def _normalize_step_params(cls, step_params: str | dict | None) -> str | None:
        """
        规范化步骤参数，确保是有效的JSON字符串或None
        
        :param step_params: 步骤参数（可能是字符串、字典或None）
        :return: 规范化后的JSON字符串或None
        """
        import json
        from utils.log_util import logger
        
        if step_params is None:
            return None
        
        # 如果是空字符串，返回None
        if isinstance(step_params, str) and not step_params.strip():
            return None
        
        # 如果是字典，转换为JSON字符串
        if isinstance(step_params, dict):
            try:
                return json.dumps(step_params, ensure_ascii=False)
            except Exception as e:
                logger.error(f'步骤参数字典转换为JSON失败: {e}')
                raise ServiceException(message=f'步骤参数格式错误: {str(e)}')
        
        # 如果是字符串，验证是否为有效的JSON
        if isinstance(step_params, str):
            try:
                # 验证JSON格式
                parsed = json.loads(step_params)
                # 确保解析后是字典（步骤参数应该是对象）
                if not isinstance(parsed, dict):
                    logger.warning(f'步骤参数不是对象格式: {type(parsed)}')
                    raise ServiceException(message='步骤参数必须是JSON对象格式')
                # 重新序列化以确保格式正确
                return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError as e:
                logger.error(f'步骤参数JSON格式错误: {e}, 内容: {step_params[:100]}')
                raise ServiceException(message=f'步骤参数JSON格式错误: {str(e)}')
            except Exception as e:
                logger.error(f'步骤参数验证失败: {e}')
                raise ServiceException(message=f'步骤参数验证失败: {str(e)}')
        
        # 其他类型不支持
        logger.error(f'步骤参数类型不支持: {type(step_params)}')
        raise ServiceException(message=f'步骤参数类型不支持: {type(step_params)}')

    @classmethod
    async def add_step_services(
        cls, query_db: AsyncSession, page_object: TushareWorkflowStepModel
    ) -> CrudResponseModel:
        """
        新增流程步骤信息service

        :param query_db: orm对象
        :param page_object: 新增流程步骤对象
        :return: 新增流程步骤校验结果
        """
        try:
            # 规范化步骤参数（无论是否为 None 都要处理）
            if hasattr(page_object, 'step_params'):
                # 规范化会处理 None、空字符串、字典、字符串等各种情况
                page_object.step_params = cls._normalize_step_params(page_object.step_params)
            
            add_step = await TushareWorkflowStepDao.add_step_dao(query_db, page_object)
            await query_db.commit()
            result = {'is_success': True, 'message': '新增成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def edit_step_services(
        cls, query_db: AsyncSession, page_object: EditTushareWorkflowStepModel
    ) -> CrudResponseModel:
        """
        编辑流程步骤信息service

        :param query_db: orm对象
        :param page_object: 编辑流程步骤对象
        :return: 编辑流程步骤校验结果
        """
        try:
            # 规范化步骤参数
            if hasattr(page_object, 'step_params') and page_object.step_params is not None:
                page_object.step_params = cls._normalize_step_params(page_object.step_params)
            
            result_id = await TushareWorkflowStepDao.edit_step_dao(query_db, page_object)
            await query_db.commit()
            result = {'is_success': True, 'message': '编辑成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def delete_step_services(
        cls, query_db: AsyncSession, page_object: DeleteTushareWorkflowStepModel
    ) -> CrudResponseModel:
        """
        删除流程步骤信息service

        :param query_db: orm对象
        :param page_object: 删除流程步骤对象
        :return: 删除流程步骤校验结果
        """
        step_ids = [int(step_id) for step_id in page_object.step_ids.split(',')]
        try:
            await TushareWorkflowStepDao.delete_step_dao(query_db, step_ids)
            await query_db.commit()
            result = {'is_success': True, 'message': '删除成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)

    @classmethod
    async def batch_save_step_services(
        cls, query_db: AsyncSession, batch_data: BatchSaveWorkflowStepModel, user_name: str
    ) -> CrudResponseModel:
        """
        批量保存流程步骤信息service（创建、更新、删除）

        :param query_db: orm对象
        :param batch_data: 批量数据对象，包含 create, update, delete 三个列表
        :param user_name: 用户名
        :return: 批量保存结果
        """
        from datetime import datetime
        
        try:
            create_list = batch_data.create or []
            update_list = batch_data.update or []
            delete_ids = batch_data.delete or []
            
            # 删除步骤
            if delete_ids and len(delete_ids) > 0:
                await TushareWorkflowStepDao.delete_step_dao(query_db, delete_ids)
            
            # 创建步骤
            for step_model in create_list:
                # 规范化步骤参数（包括 None 和空字符串的处理）
                if hasattr(step_model, 'step_params'):
                    step_model.step_params = cls._normalize_step_params(step_model.step_params)
                
                step_model.create_by = user_name
                step_model.create_time = datetime.now()
                step_model.update_by = user_name
                step_model.update_time = datetime.now()
                await TushareWorkflowStepDao.add_step_dao(query_db, step_model)
            
            # 更新步骤
            for step_model in update_list:
                # 规范化步骤参数（包括 None 和空字符串的处理）
                # 注意：即使 step_params 是 None，也要规范化（确保是 None 而不是空字符串）
                if hasattr(step_model, 'step_params'):
                    step_model.step_params = cls._normalize_step_params(step_model.step_params)
                
                step_model.update_by = user_name
                step_model.update_time = datetime.now()
                await TushareWorkflowStepDao.edit_step_dao(query_db, step_model)
            
            await query_db.commit()
            result = {'is_success': True, 'message': '批量保存成功'}
        except Exception as e:
            await query_db.rollback()
            raise e

        return CrudResponseModel(**result)
