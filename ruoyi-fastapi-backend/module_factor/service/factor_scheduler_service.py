from datetime import datetime
from typing import Any

from module_factor.entity.vo.factor_vo import FactorTaskModel
from module_factor.task.factor_calc_task import run_factor_task_sync
from utils.log_util import logger


class FactorSchedulerService:
    """
    因子计算任务调度器服务
    """

    JOB_ID_PREFIX = 'factor_task_'

    @classmethod
    def _build_job_id(cls, task_id: int | None) -> str:
        return f'{cls.JOB_ID_PREFIX}{task_id}'

    @classmethod
    def register_task_scheduler(cls, task_model: FactorTaskModel) -> None:
        """
        注册因子任务到调度器
        """
        from config.get_scheduler import MyCronTrigger, scheduler

        if not task_model.id:
            logger.warning('因子任务ID为空，无法注册到调度器')
            return

        if task_model.status != '0':
            logger.info(
                f'因子任务 {task_model.task_name} (ID: {task_model.id}) 已暂停，不注册到调度器'
            )
            return

        if not task_model.cron_expression or not task_model.cron_expression.strip():
            logger.info(
                f'因子任务 {task_model.task_name} (ID: {task_model.id}) 没有配置cron表达式，不注册到调度器'
            )
            return

        job_id = cls._build_job_id(task_model.id)

        try:
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.remove_job(job_id)
                logger.info(f'移除已存在的因子任务调度: {job_id}')

            def task_wrapper() -> None:
                """
                任务包装器，用于调用因子计算入口
                """
                try:
                    logger.info(f'开始执行因子任务 {task_model.task_name} (ID: {task_model.id})')
                    run_factor_task_sync(task_model.id)
                    logger.info(f'因子任务 {task_model.task_name} (ID: {task_model.id}) 执行完成')
                except Exception as exc:
                    logger.exception(
                        f'因子任务 {task_model.task_name} (ID: {task_model.id}) 执行失败: {exc}'
                    )

            cron_expr = task_model.cron_expression.strip()
            try:
                trigger = MyCronTrigger.from_crontab(cron_expr)
            except Exception as exc:
                logger.error(f'解析因子任务 cron 表达式失败: {cron_expr}, 错误: {exc}')
                raise

            job = scheduler.add_job(
                func=task_wrapper,
                trigger=trigger,
                id=job_id,
                name=f'factor_task_{task_model.task_name}',
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300,
            )

            registered_job = scheduler.get_job(job_id)
            if not registered_job:
                raise RuntimeError(f'因子任务注册后无法在调度器中找到: {job_id}')

            next_run_time = registered_job.next_run_time
            next_run_str = next_run_time.strftime('%Y-%m-%d %H:%M:%S') if next_run_time else '未安排'
            logger.info(
                f'因子任务 {task_model.task_name} (ID: {task_model.id}) 已注册到调度器，'
                f'cron表达式: {cron_expr}, 下次执行时间: {next_run_str}'
            )
        except Exception as exc:
            logger.exception(
                f'注册因子任务 {task_model.task_name} (ID: {task_model.id}) 到调度器失败: {exc}'
            )
            raise

    @classmethod
    def update_task_scheduler(
        cls, updated_task_model: FactorTaskModel, old_task_model: FactorTaskModel
    ) -> None:
        """
        更新因子任务调度配置
        """
        from config.get_scheduler import scheduler

        if not updated_task_model.id:
            logger.warning('因子任务ID为空，无法更新调度配置')
            return

        job_id = cls._build_job_id(updated_task_model.id)

        if updated_task_model.status != '0':
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.remove_job(job_id)
                logger.info(
                    f'因子任务 {updated_task_model.task_name} (ID: {updated_task_model.id}) 已暂停，已从调度器移除'
                )
            return

        old_cron = old_task_model.cron_expression.strip() if old_task_model.cron_expression else None
        new_cron = (
            updated_task_model.cron_expression.strip()
            if updated_task_model.cron_expression
            else None
        )

        if not new_cron:
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.remove_job(job_id)
                logger.info(
                    f'因子任务 {updated_task_model.task_name} (ID: {updated_task_model.id}) 已移除cron表达式，已从调度器移除'
                )
            return

        existing_job = scheduler.get_job(job_id)
        cron_changed = old_cron != new_cron
        status_changed = old_task_model.status != updated_task_model.status

        if cron_changed or status_changed or not existing_job:
            if existing_job:
                scheduler.remove_job(job_id)
                logger.info(f'移除旧的因子任务调度: {job_id}')

            cls.register_task_scheduler(updated_task_model)

            change_reason: list[str] = []
            if cron_changed:
                change_reason.append(f'cron表达式变更: {old_cron} -> {new_cron}')
            if status_changed:
                change_reason.append(f'状态变更: {old_task_model.status} -> {updated_task_model.status}')
            if not existing_job:
                change_reason.append('任务不在调度器中')

            logger.info(
                f'因子任务 {updated_task_model.task_name} (ID: {updated_task_model.id}) 调度器已更新，'
                f'原因: {", ".join(change_reason) if change_reason else "其他配置变更"}'
            )
        else:
            scheduler.remove_job(job_id)
            cls.register_task_scheduler(updated_task_model)
            logger.info(
                f'因子任务 {updated_task_model.task_name} (ID: {updated_task_model.id}) 调度器已更新，'
                f'原因: 其他配置已变更（cron表达式和状态未变更）'
            )

    @classmethod
    def remove_task_scheduler(cls, task_id: int) -> None:
        """
        从调度器中移除因子任务
        """
        from config.get_scheduler import scheduler

        job_id = cls._build_job_id(task_id)
        existing_job = scheduler.get_job(job_id)
        if existing_job:
            scheduler.remove_job(job_id)
            logger.info(f'因子任务 (ID: {task_id}) 已从调度器移除')

    @classmethod
    def get_task_scheduler_status(cls, task_id: int) -> dict[str, Any] | None:
        """
        获取因子任务在调度器中的状态
        """
        from config.get_scheduler import scheduler

        job_id = cls._build_job_id(task_id)
        job = scheduler.get_job(job_id)
        if not job:
            return None

        return {
            'job_id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
        }

