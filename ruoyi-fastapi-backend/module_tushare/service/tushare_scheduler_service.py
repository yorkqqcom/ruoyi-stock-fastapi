from datetime import datetime
from typing import Any

from module_tushare.entity.vo.tushare_vo import TushareDownloadTaskModel
from module_tushare.task.tushare_download_task import download_tushare_data_sync
from utils.log_util import logger


class TushareSchedulerService:
    """
    Tushare下载任务调度器服务
    用于管理下载任务的定时调度
    支持单个接口任务和流程配置任务的区分管理
    """

    @classmethod
    def register_task_scheduler(cls, task_model: TushareDownloadTaskModel) -> None:
        """
        注册任务到调度器

        :param task_model: 任务模型对象
        :return: None
        """
        # 延迟导入，避免循环导入
        from config.get_scheduler import MyCronTrigger, scheduler

        # 检查任务是否有效
        if not task_model.task_id:
            logger.warning('任务ID为空，无法注册到调度器')
            return

        # 检查任务状态
        if task_model.status != '0':
            logger.info(f'任务 {task_model.task_name} (ID: {task_model.task_id}) 已暂停，不注册到调度器')
            return

        # 检查是否有cron表达式
        if not task_model.cron_expression or not task_model.cron_expression.strip():
            logger.info(f'任务 {task_model.task_name} (ID: {task_model.task_id}) 没有配置cron表达式，不注册到调度器')
            return

        try:
            # 移除已存在的任务（如果存在）
            job_id = f'tushare_task_{task_model.task_id}'
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.remove_job(job_id)
                logger.info(f'移除已存在的任务调度: {job_id}')

            # 创建任务函数（包装器，用于传递task_id）
            def task_wrapper():
                """任务包装器，用于调用下载函数"""
                try:
                    logger.info(f'🔄 调度器开始执行任务 {task_model.task_name} (ID: {task_model.task_id})')
                    download_tushare_data_sync(task_model.task_id)
                    logger.info(f'✅ 调度器执行任务 {task_model.task_name} (ID: {task_model.task_id}) 完成')
                except Exception as e:
                    logger.exception(f'❌ 调度器执行任务 {task_model.task_name} (ID: {task_model.task_id}) 失败: {e}')

            # 解析cron表达式
            cron_expr = task_model.cron_expression.strip()
            try:
                trigger = MyCronTrigger.from_crontab(cron_expr)
                logger.debug(f'解析cron表达式成功: {cron_expr} -> {trigger}')
            except Exception as e:
                logger.error(f'❌ 解析cron表达式失败: {cron_expr}, 错误: {e}')
                raise

            # 注册任务到调度器
            # 注意：使用默认执行器（AsyncIOExecutor），它可以执行同步函数
            job = scheduler.add_job(
                func=task_wrapper,
                trigger=trigger,
                id=job_id,
                name=f'tushare_task_{task_model.task_name}',
                max_instances=1,  # 同一任务只能有一个实例在运行
                coalesce=True,  # 如果任务错过了执行时间，合并执行
                misfire_grace_time=300,  # 允许错过执行时间300秒
            )

            # 验证任务是否成功注册
            registered_job = scheduler.get_job(job_id)
            if not registered_job:
                raise RuntimeError(f'任务注册后无法在调度器中找到: {job_id}')

            # 记录下一次执行时间
            next_run_time = registered_job.next_run_time
            next_run_str = next_run_time.strftime('%Y-%m-%d %H:%M:%S') if next_run_time else '未安排'
            
            logger.info(
                f'✅ 任务 {task_model.task_name} (ID: {task_model.task_id}) 已注册到调度器，'
                f'cron表达式: {cron_expr}, 下次执行时间: {next_run_str}'
            )
        except Exception as e:
            logger.exception(
                f'❌ 注册任务 {task_model.task_name} (ID: {task_model.task_id}) 到调度器失败: {e}'
            )
            raise

    @classmethod
    def update_task_scheduler(
        cls, updated_task_model: TushareDownloadTaskModel, old_task_model: TushareDownloadTaskModel
    ) -> None:
        """
        更新任务调度器

        :param updated_task_model: 更新后的任务模型对象
        :param old_task_model: 更新前的任务模型对象
        :return: None
        """
        # 延迟导入，避免循环导入
        from config.get_scheduler import scheduler

        job_id = f'tushare_task_{updated_task_model.task_id}'

        # 检查任务是否被删除或状态变更
        if updated_task_model.status != '0':
            # 任务已暂停，移除调度器中的任务
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.remove_job(job_id)
                logger.info(f'任务 {updated_task_model.task_name} (ID: {updated_task_model.task_id}) 已暂停，已从调度器移除')
            return

        # 检查cron表达式是否变更
        old_cron = old_task_model.cron_expression.strip() if old_task_model.cron_expression else None
        new_cron = updated_task_model.cron_expression.strip() if updated_task_model.cron_expression else None

        # 如果新任务没有cron表达式，移除调度器中的任务
        if not new_cron:
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.remove_job(job_id)
                logger.info(f'任务 {updated_task_model.task_name} (ID: {updated_task_model.task_id}) 已移除cron表达式，已从调度器移除')
            return

        # 检查任务是否在调度器中存在
        existing_job = scheduler.get_job(job_id)
        
        # 如果cron表达式或状态有变更，或者任务不在调度器中，重新注册任务
        cron_changed = old_cron != new_cron
        status_changed = old_task_model.status != updated_task_model.status
        
        if cron_changed or status_changed or not existing_job:
            # 先移除旧任务（如果存在）
            if existing_job:
                scheduler.remove_job(job_id)
                logger.info(f'移除旧的任务调度: {job_id}')

            # 重新注册任务（使用最新的任务配置）
            cls.register_task_scheduler(updated_task_model)
            
            change_reason = []
            if cron_changed:
                change_reason.append(f'cron表达式变更: {old_cron} -> {new_cron}')
            if status_changed:
                change_reason.append(f'状态变更: {old_task_model.status} -> {updated_task_model.status}')
            if not existing_job:
                change_reason.append('任务不在调度器中')
            
            logger.info(
                f'✅ 任务 {updated_task_model.task_name} (ID: {updated_task_model.task_id}) 调度器已更新，'
                f'原因: {", ".join(change_reason) if change_reason else "其他配置变更"}'
            )
        else:
            # cron表达式和状态都没有变更，但其他配置可能已变更
            # 为了确保任务使用最新配置，也重新注册任务
            # 这样可以确保 task_wrapper 闭包捕获的是最新的 task_model
            scheduler.remove_job(job_id)
            cls.register_task_scheduler(updated_task_model)
            logger.info(
                f'✅ 任务 {updated_task_model.task_name} (ID: {updated_task_model.task_id}) 调度器已更新，'
                f'原因: 其他配置已变更（cron表达式和状态未变更）'
            )

    @classmethod
    def remove_task_scheduler(cls, task_id: int) -> None:
        """
        从调度器中移除任务

        :param task_id: 任务ID
        :return: None
        """
        # 延迟导入，避免循环导入
        from config.get_scheduler import scheduler

        job_id = f'tushare_task_{task_id}'
        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.remove_job(job_id)
            logger.info(f'✅ 任务 (ID: {task_id}) 已从调度器移除')
        else:
            logger.debug(f'任务 (ID: {task_id}) 在调度器中不存在，无需移除')

    @classmethod
    def get_task_scheduler_status(cls, task_id: int) -> dict[str, Any] | None:
        """
        获取任务在调度器中的状态

        :param task_id: 任务ID
        :return: 任务调度状态信息，如果任务不在调度器中则返回None
        """
        # 延迟导入，避免循环导入
        from config.get_scheduler import scheduler

        job_id = f'tushare_task_{task_id}'
        job = scheduler.get_job(job_id)
        if not job:
            return None

        return {
            'job_id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
        }

    @classmethod
    def get_all_scheduled_tasks(cls) -> list[dict[str, Any]]:
        """
        获取所有已调度的任务信息

        :return: 任务调度信息列表
        """
        # 延迟导入，避免循环导入
        from config.get_scheduler import scheduler

        jobs = scheduler.get_jobs()
        task_list = []
        for job in jobs:
            if job.id and job.id.startswith('tushare_task_'):
                task_id = int(job.id.replace('tushare_task_', ''))
                task_list.append({
                    'task_id': task_id,
                    'job_id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                })
        return task_list

    @classmethod
    def debug_task_scheduler(cls, task_id: int) -> dict[str, Any]:
        """
        调试任务调度器状态

        :param task_id: 任务ID
        :return: 调试信息
        """
        # 延迟导入，避免循环导入
        from config.get_scheduler import scheduler, MyCronTrigger

        job_id = f'tushare_task_{task_id}'
        job = scheduler.get_job(job_id)
        
        debug_info = {
            'task_id': task_id,
            'job_id': job_id,
            'job_exists': job is not None,
            'scheduler_running': scheduler.running if hasattr(scheduler, 'running') else None,
        }
        
        if job:
            debug_info.update({
                'job_name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'trigger_repr': repr(job.trigger),
                'max_instances': job.max_instances,
                'coalesce': job.coalesce,
                'misfire_grace_time': job.misfire_grace_time,
            })
            
            # 尝试解析trigger的详细信息
            if hasattr(job.trigger, 'fields'):
                debug_info['trigger_fields'] = {
                    'second': str(job.trigger.fields[0]) if len(job.trigger.fields) > 0 else None,
                    'minute': str(job.trigger.fields[1]) if len(job.trigger.fields) > 1 else None,
                    'hour': str(job.trigger.fields[2]) if len(job.trigger.fields) > 2 else None,
                    'day': str(job.trigger.fields[3]) if len(job.trigger.fields) > 3 else None,
                    'month': str(job.trigger.fields[4]) if len(job.trigger.fields) > 4 else None,
                    'day_of_week': str(job.trigger.fields[5]) if len(job.trigger.fields) > 5 else None,
                }
        
        return debug_info
