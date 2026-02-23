import asyncio
from types import SimpleNamespace

import pytest

from module_backtest.service.backtest_service import (
    BacktestService,
    _has_valid_online_model_config,
    _has_valid_predict_table_config,
)


def test_has_valid_predict_table_config_accepts_result_or_task_id():
    # 只传 result_id
    assert _has_valid_predict_table_config(1, None) is True
    assert _has_valid_predict_table_config("2", "") is True
    # 只传 predict_task_id
    assert _has_valid_predict_table_config(None, 3) is True
    assert _has_valid_predict_table_config("", "4") is True
    # 都为空或无效
    assert _has_valid_predict_table_config(None, None) is False
    assert _has_valid_predict_table_config("", "") is False
    assert _has_valid_predict_table_config("abc", "def") is False


def test_has_valid_online_model_config_accepts_result_or_binding_id():
    # 只传 result_id
    assert _has_valid_online_model_config(1, None) is True
    assert _has_valid_online_model_config("2", "") is True
    # 只传 model_scene_binding_id
    assert _has_valid_online_model_config(None, 3) is True
    assert _has_valid_online_model_config("", "4") is True
    # 都为空或无效
    assert _has_valid_online_model_config(None, None) is False
    assert _has_valid_online_model_config("", "") is False
    assert _has_valid_online_model_config("abc", "def") is False


@pytest.mark.asyncio
async def test_execute_task_service_returns_clear_message_for_missing_offline_model(monkeypatch):
    """当离线模式任务缺少 resultId/predictTaskId 时，应返回与前端 tooltip 对齐的中文错误。"""

    class DummyTask:
        id = 1
        status = "0"
        signal_source_type = "predict_table"
        result_id = None
        predict_task_id = None
        model_scene_binding_id = None

    async def fake_get_task_by_id(db, task_id):
        return DummyTask()

    async def fake_commit():
        return None

    class DummySession:
        async def commit(self):
            await fake_commit()

    monkeypatch.setattr(
        "module_backtest.dao.backtest_dao.BacktestTaskDao.get_task_by_id",
        fake_get_task_by_id,
    )

    db = DummySession()
    result = await BacktestService.execute_task_service(db, 1)
    assert result.is_success is False
    assert "未配置模型或预测任务" in result.message


@pytest.mark.asyncio
async def test_execute_task_service_returns_clear_message_for_missing_online_model(monkeypatch):
    """当在线模式任务缺少 resultId/modelSceneBindingId 时，应返回对应的中文错误。"""

    class DummyTask:
        id = 2
        status = "0"
        signal_source_type = "online_model"
        result_id = None
        predict_task_id = None
        model_scene_binding_id = None

    async def fake_get_task_by_id(db, task_id):
        return DummyTask()

    class DummySession:
        async def commit(self):
            return None

    monkeypatch.setattr(
        "module_backtest.dao.backtest_dao.BacktestTaskDao.get_task_by_id",
        fake_get_task_by_id,
    )

    db = DummySession()
    result = await BacktestService.execute_task_service(db, 2)
    assert result.is_success is False
    assert "未配置模型或场景绑定" in result.message

