import importlib
import json
from asyncio import iscoroutinefunction
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from apscheduler.events import EVENT_ALL, SchedulerEvent
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.job import Job
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

import module_task  # noqa: F401
from config.database import AsyncSessionLocal, quote_plus
from config.env import DataBaseConfig, RedisConfig
from module_admin.dao.job_dao import JobDao
from module_admin.entity.vo.job_vo import JobLogModel, JobModel
from module_admin.service.job_log_service import JobLogService
from module_tushare.dao.tushare_dao import TushareDownloadTaskDao
from module_tushare.entity.vo.tushare_vo import TushareDownloadTaskModel
from utils.common_util import CamelCaseUtil
from utils.log_util import logger


# 重写Cron定时
class MyCronTrigger(CronTrigger):
    CRON_EXPRESSION_LENGTH_MIN = 6
    CRON_EXPRESSION_LENGTH_MAX = 7
    WEEKDAY_COUNT = 5

    @classmethod
    def from_crontab(cls, expr: str, timezone: str | None = None) -> 'MyCronTrigger':
        values = expr.split()
        if len(values) != cls.CRON_EXPRESSION_LENGTH_MIN and len(values) != cls.CRON_EXPRESSION_LENGTH_MAX:
            raise ValueError(f'Wrong number of fields; got {len(values)}, expected 6 or 7')

        second = values[0]
        minute = values[1]
        hour = values[2]
        
        # 解析日期字段
        if '?' in values[3]:
            # 日期字段是?，表示按星期执行，日期设为None
            day = None
        elif 'L' in values[5]:
            # 星期字段包含L，表示最后一天
            day = f'last {values[5].replace("L", "")}'
        elif 'W' in values[3]:
            # 日期字段包含W，表示工作日
            day = cls.__find_recent_workday(int(values[3].split('W')[0]))
        else:
            # 日期字段是*或具体值
            day_str = values[3].replace('L', 'last')
            # APScheduler支持day='*'表示每天
            day = day_str
        
        month = values[4]
        
        # 解析星期字段
        if '?' in values[5] or 'L' in values[5]:
            week = None
            day_of_week = None
        elif '#' in values[5]:
            # 格式：1#2 表示第2周的星期1
            week = int(values[5].split('#')[1])
            day_of_week = int(values[5].split('#')[0]) - 1
        else:
            # 星期字段是*或具体值
            if values[5] == '*':
                week = None
                day_of_week = None
            else:
                week = None
                # 解析星期值（1-7，1=周日，7=周六）
                # APScheduler使用0-6，0=周一，6=周日
                # 需要转换：Quartz的1(周日) -> APScheduler的6，Quartz的2-7 -> APScheduler的0-5
                try:
                    week_values = [int(x) - 1 for x in values[5].split(',')]
                    # 转换：1->6, 2->0, 3->1, 4->2, 5->3, 6->4, 7->5
                    day_of_week = [(6 if x == 0 else x - 1) for x in week_values]
                    if len(day_of_week) == 1:
                        day_of_week = day_of_week[0]
                except ValueError:
                    day_of_week = None
        
        year = values[6] if len(values) == cls.CRON_EXPRESSION_LENGTH_MAX else None
        
        # 记录解析结果用于调试
        logger.debug(
            f'解析cron表达式: {expr} -> '
            f'second={second}, minute={minute}, hour={hour}, '
            f'day={day}, month={month}, week={week}, day_of_week={day_of_week}, year={year}'
        )
        
        return cls(
            second=second,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            week=week,
            day_of_week=day_of_week,
            year=year,
            timezone=timezone,
        )

    @classmethod
    def __find_recent_workday(cls, day: int) -> int:
        now = datetime.now()
        date = datetime(now.year, now.month, day)
        if date.weekday() < cls.WEEKDAY_COUNT:
            return date.day
        diff = 1
        while True:
            previous_day = date - timedelta(days=diff)
            if previous_day.weekday() < cls.WEEKDAY_COUNT:
                return previous_day.day
            diff += 1


SQLALCHEMY_DATABASE_URL = (
    f'mysql+pymysql://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
    f'{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
)
if DataBaseConfig.db_type == 'postgresql':
    SQLALCHEMY_DATABASE_URL = (
        f'postgresql+psycopg2://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
        f'{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
    )
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=DataBaseConfig.db_echo,
    max_overflow=DataBaseConfig.db_max_overflow,
    pool_size=DataBaseConfig.db_pool_size,
    pool_recycle=DataBaseConfig.db_pool_recycle,
    pool_timeout=DataBaseConfig.db_pool_timeout,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
redis_config = {
    'host': RedisConfig.redis_host,
    'port': RedisConfig.redis_port,
    'username': RedisConfig.redis_username,
    'password': RedisConfig.redis_password,
    'db': RedisConfig.redis_database,
}
job_stores = {
    'default': MemoryJobStore(),
    'sqlalchemy': SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URL, engine=engine),
    'redis': RedisJobStore(**redis_config),
}
executors = {'default': AsyncIOExecutor(), 'processpool': ProcessPoolExecutor(5)}
job_defaults = {'coalesce': False, 'max_instance': 1}
scheduler = AsyncIOScheduler()
scheduler.configure(jobstores=job_stores, executors=executors, job_defaults=job_defaults)


class SchedulerUtil:
    """
    定时任务相关方法
    """

    @classmethod
    async def init_system_scheduler(cls) -> None:
        """
        应用启动时初始化定时任务

        :return:
        """
        logger.info('🔎 开始启动定时任务...')
        
        # 启动调度器
        if not scheduler.running:
            scheduler.start()
            logger.info('✅️ 调度器已启动')
        else:
            logger.warning('⚠️ 调度器已经在运行中')
        
        async with AsyncSessionLocal() as session:
            # 加载系统定时任务（sys_job）
            job_list = await JobDao.get_job_list_for_scheduler(session)
            logger.info(f'📋 系统定时任务数量: {len(job_list)}')
            for item in job_list:
                cls.remove_scheduler_job(job_id=str(item.job_id))
                cls.add_scheduler_job(item)
            
            # 加载下载任务定时调度
            logger.info('🔎 开始加载 Tushare 下载任务定时调度...')
            # 延迟导入，避免循环导入
            from module_tushare.service.tushare_scheduler_service import TushareSchedulerService
            
            download_tasks = await TushareDownloadTaskDao.get_tasks_for_scheduler(session)
            logger.info(f'📋 从数据库查询到 {len(download_tasks)} 个 Tushare 下载任务')
            
            success_count = 0
            fail_count = 0
            skip_count = 0
            
            for task in download_tasks:
                try:
                    task_model = TushareDownloadTaskModel(**CamelCaseUtil.transform_result(task))
                    
                    # 检查任务状态和cron表达式
                    if task_model.status != '0':
                        logger.info(
                            f'⏭️ 跳过任务 {task_model.task_name} (ID: {task_model.task_id}): '
                            f'任务状态为暂停 (status={task_model.status})'
                        )
                        skip_count += 1
                        continue
                    
                    if not task_model.cron_expression or not task_model.cron_expression.strip():
                        logger.info(
                            f'⏭️ 跳过任务 {task_model.task_name} (ID: {task_model.task_id}): '
                            f'未配置 cron 表达式'
                        )
                        skip_count += 1
                        continue
                    
                    # 注册任务到调度器
                    TushareSchedulerService.register_task_scheduler(task_model)
                    success_count += 1
                    
                except Exception as e:
                    logger.exception(
                        f'❌ 加载下载任务定时调度失败: task_id={task.task_id}, '
                        f'task_name={task.task_name}, 错误: {str(e)}'
                    )
                    fail_count += 1
            
            logger.info(
                f'✅️ Tushare 下载任务定时调度加载完成: '
                f'总计 {len(download_tasks)} 个, '
                f'成功 {success_count} 个, '
                f'失败 {fail_count} 个, '
                f'跳过 {skip_count} 个'
            )
            
            # 验证调度器中的任务数量
            all_jobs = scheduler.get_jobs()
            tushare_jobs = [job for job in all_jobs if job.id and job.id.startswith('tushare_task_')]
            logger.info(f'📊 调度器中当前 Tushare 任务数量: {len(tushare_jobs)}')
            
            # 列出所有已注册的 Tushare 任务
            if tushare_jobs:
                logger.info('📝 已注册的 Tushare 任务列表:')
                for job in tushare_jobs:
                    next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else '未安排'
                    logger.info(f'  - {job.name} (ID: {job.id}), 下次执行: {next_run}')
        
        scheduler.add_listener(cls.scheduler_event_listener, EVENT_ALL)
        
        # 验证调度器状态
        cls._verify_scheduler_status()
        
        logger.info('✅️ 系统初始定时任务加载成功')
    
    @classmethod
    def _verify_scheduler_status(cls) -> None:
        """
        验证调度器状态
        
        :return:
        """
        logger.info('🔍 验证调度器状态...')
        
        # 检查调度器是否运行
        is_running = scheduler.running if hasattr(scheduler, 'running') else False
        logger.info(f'  调度器运行状态: {"✅ 运行中" if is_running else "❌ 未运行"}')
        
        # 统计所有任务
        all_jobs = scheduler.get_jobs()
        logger.info(f'  调度器中总任务数: {len(all_jobs)}')
        
        # 统计 Tushare 任务
        tushare_jobs = [job for job in all_jobs if job.id and job.id.startswith('tushare_task_')]
        logger.info(f'  Tushare 任务数: {len(tushare_jobs)}')
        
        # 统计系统任务
        system_jobs = [job for job in all_jobs if not (job.id and job.id.startswith('tushare_task_'))]
        logger.info(f'  系统任务数: {len(system_jobs)}')
        
        # 检查是否有任务没有下次执行时间
        jobs_without_next_run = [job for job in all_jobs if job.next_run_time is None]
        if jobs_without_next_run:
            logger.warning(f'  ⚠️ 有 {len(jobs_without_next_run)} 个任务没有安排下次执行时间:')
            for job in jobs_without_next_run:
                logger.warning(f'    - {job.name} (ID: {job.id})')
        
        logger.info('✅️ 调度器状态验证完成')

    @classmethod
    async def close_system_scheduler(cls) -> None:
        """
        应用关闭时关闭定时任务

        :return:
        """
        scheduler.shutdown()
        logger.info('✅️ 关闭定时任务成功')

    @classmethod
    def _import_function(cls, func_path: str) -> Callable[..., Any]:
        """
        动态导入函数

        :param func_path: 函数字符串，如module_task.scheduler_test.job
        :return: 导入的函数对象
        """
        module_path, func_name = func_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)

    @classmethod
    def get_scheduler_job(cls, job_id: str | int) -> Job:
        """
        根据任务id获取任务对象

        :param job_id: 任务id
        :return: 任务对象
        """
        query_job = scheduler.get_job(job_id=str(job_id))

        return query_job

    @classmethod
    def add_scheduler_job(cls, job_info: JobModel) -> None:
        """
        根据输入的任务对象信息添加任务

        :param job_info: 任务对象信息
        :return:
        """
        job_func = cls._import_function(job_info.invoke_target)
        job_executor = job_info.job_executor
        if iscoroutinefunction(job_func):
            job_executor = 'default'
        scheduler.add_job(
            func=job_func,
            trigger=MyCronTrigger.from_crontab(job_info.cron_expression),
            args=job_info.job_args.split(',') if job_info.job_args else None,
            kwargs=json.loads(job_info.job_kwargs) if job_info.job_kwargs else None,
            id=str(job_info.job_id),
            name=job_info.job_name,
            misfire_grace_time=1000000000000 if job_info.misfire_policy == '3' else None,
            coalesce=job_info.misfire_policy == '2',
            max_instances=3 if job_info.concurrent == '0' else 1,
            jobstore=job_info.job_group,
            executor=job_executor,
        )

    @classmethod
    def execute_scheduler_job_once(cls, job_info: JobModel) -> None:
        """
        根据输入的任务对象执行一次任务

        :param job_info: 任务对象信息
        :return:
        """
        job_func = cls._import_function(job_info.invoke_target)
        job_executor = job_info.job_executor
        if iscoroutinefunction(job_func):
            job_executor = 'default'
        job_trigger = DateTrigger()
        if job_info.status == '0':
            job_trigger = OrTrigger(triggers=[DateTrigger(), MyCronTrigger.from_crontab(job_info.cron_expression)])
        scheduler.add_job(
            func=job_func,
            trigger=job_trigger,
            args=job_info.job_args.split(',') if job_info.job_args else None,
            kwargs=json.loads(job_info.job_kwargs) if job_info.job_kwargs else None,
            id=str(job_info.job_id),
            name=job_info.job_name,
            misfire_grace_time=1000000000000 if job_info.misfire_policy == '3' else None,
            coalesce=job_info.misfire_policy == '2',
            max_instances=3 if job_info.concurrent == '0' else 1,
            jobstore=job_info.job_group,
            executor=job_executor,
        )

    @classmethod
    def remove_scheduler_job(cls, job_id: str | int) -> None:
        """
        根据任务id移除任务

        :param job_id: 任务id
        :return:
        """
        query_job = cls.get_scheduler_job(job_id=job_id)
        if query_job:
            scheduler.remove_job(job_id=str(job_id))

    @classmethod
    def scheduler_event_listener(cls, event: SchedulerEvent) -> None:
        # 获取事件类型和任务ID
        event_type = event.__class__.__name__
        # 获取任务执行异常信息
        status = '0'
        exception_info = ''
        if event_type == 'JobExecutionEvent' and event.exception:
            exception_info = str(event.exception)
            status = '1'
        if hasattr(event, 'job_id'):
            job_id = event.job_id
            query_job = cls.get_scheduler_job(job_id=job_id)
            if query_job:
                try:
                    # 尝试获取任务状态信息
                    query_job_info = query_job.__getstate__()
                    # 获取任务名称
                    job_name = query_job_info.get('name')
                    # 获取任务组名
                    job_group = query_job._jobstore_alias
                    # 获取任务执行器
                    job_executor = query_job_info.get('executor')
                    # 获取调用目标字符串
                    invoke_target = query_job_info.get('func')
                    # 获取调用函数位置参数（args 可能含 int 等，需转为 str 再 join）
                    job_args = ','.join(str(a) for a in query_job_info.get('args', []))
                    # 获取调用函数关键字参数
                    job_kwargs = json.dumps(query_job_info.get('kwargs', {}))
                    # 获取任务触发器
                    job_trigger = str(query_job_info.get('trigger'))
                except (ValueError, AttributeError) as e:
                    # 如果无法序列化（如 Tushare 任务的闭包函数），使用备用方案
                    logger.debug(f'任务 {job_id} 无法序列化，使用备用方案: {e}')
                    # 直接从 job 对象获取属性
                    job_name = query_job.name if hasattr(query_job, 'name') else str(job_id)
                    job_group = query_job._jobstore_alias if hasattr(query_job, '_jobstore_alias') else 'default'
                    job_executor = query_job._executor if hasattr(query_job, '_executor') else 'default'
                    
                    # 对于 Tushare 任务，使用特殊标识
                    if job_id and job_id.startswith('tushare_task_'):
                        invoke_target = 'module_tushare.task.tushare_download_task.download_tushare_data_sync'
                        # 尝试从 job_id 提取 task_id
                        try:
                            task_id = int(job_id.replace('tushare_task_', ''))
                            job_args = str(task_id)
                        except ValueError:
                            # 如果无法从 job_id 提取，尝试从 job.args 获取
                            if hasattr(query_job, 'args') and query_job.args:
                                job_args = ','.join(str(arg) for arg in query_job.args)
                            else:
                                job_args = ''
                    else:
                        # 尝试获取函数名
                        if hasattr(query_job, 'func') and query_job.func:
                            func = query_job.func
                            if hasattr(func, '__module__') and hasattr(func, '__name__'):
                                invoke_target = f'{func.__module__}.{func.__name__}'
                            else:
                                invoke_target = str(func)
                        else:
                            invoke_target = 'unknown'
                        # 获取参数
                        if hasattr(query_job, 'args') and query_job.args:
                            job_args = ','.join(str(arg) for arg in query_job.args)
                        else:
                            job_args = ''
                    
                    # 获取关键字参数
                    job_kwargs = json.dumps(query_job.kwargs) if hasattr(query_job, 'kwargs') and query_job.kwargs else '{}'
                    # 获取任务触发器
                    job_trigger = str(query_job.trigger) if hasattr(query_job, 'trigger') else 'unknown'
                
                # 构造日志消息
                job_message = f'事件类型: {event_type}, 任务ID: {job_id}, 任务名称: {job_name}, 执行于{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                job_log = JobLogModel(
                    jobName=job_name,
                    jobGroup=job_group,
                    jobExecutor=job_executor,
                    invokeTarget=invoke_target,
                    jobArgs=job_args,
                    jobKwargs=job_kwargs,
                    jobTrigger=job_trigger,
                    jobMessage=job_message,
                    status=status,
                    exceptionInfo=exception_info,
                    createTime=datetime.now(),
                )
                session = SessionLocal()
                JobLogService.add_job_log_services(session, job_log)
                session.close()
