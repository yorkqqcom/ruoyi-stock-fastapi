"""
回测任务 VO 解析回归测试：验证前端驼峰 JSON（resultId、signalSourceType 等）能正确映射到 BacktestTaskCreateRequestModel，
保证 model_scene_binding_id、predict_task_id、result_id 能正确落库。
"""
import pytest

from module_backtest.entity.vo.backtest_vo import (
    BacktestTaskCreateRequestModel,
    BacktestTaskUpdateRequestModel,
)


def test_create_request_parses_camel_case_result_id_and_signal_source_type():
    """前端传入 taskName、resultId、signalSourceType 等驼峰字段时，应正确解析为 Python 属性。"""
    body = {
        'taskName': '回测1',
        'signalSourceType': 'online_model',
        'resultId': 1,
        'predictTaskId': None,
        'symbolList': '',
        'startDate': '20250201',
        'endDate': '20260131',
        'initialCash': 1000000.0,
        'maxPosition': 1.0,
        'commissionRate': 0.0003,
        'slippageBp': 0,
        'signalBuyThreshold': 0.6,
        'signalSellThreshold': 0.4,
        'positionMode': 'equal_weight',
    }
    model = BacktestTaskCreateRequestModel.model_validate(body)
    assert model.task_name == '回测1'
    assert model.signal_source_type == 'online_model'
    assert model.result_id == 1
    assert model.predict_task_id is None
    assert model.model_scene_binding_id is None


def test_create_request_parses_result_id_as_string_number():
    """前端可能传 resultId 为字符串数字，应被 coerce 为 int。"""
    body = {
        'taskName': '回测2',
        'signalSourceType': 'predict_table',
        'resultId': '2',
        'predictTaskId': None,
        'symbolList': '',
        'startDate': '20250201',
        'endDate': '20260131',
    }
    model = BacktestTaskCreateRequestModel.model_validate(body)
    assert model.result_id == 2
    assert model.signal_source_type == 'predict_table'


def test_create_request_parses_predict_task_id_and_model_scene_binding_id():
    """predictTaskId、modelSceneBindingId 驼峰键应正确解析。"""
    body = {
        'taskName': '回测3',
        'signalSourceType': 'predict_table',
        'resultId': 1,
        'predictTaskId': 10,
        'modelSceneBindingId': 5,
        'symbolList': '',
        'startDate': '20250201',
        'endDate': '20260131',
    }
    model = BacktestTaskCreateRequestModel.model_validate(body)
    assert model.result_id == 1
    assert model.predict_task_id == 10
    assert model.model_scene_binding_id == 5


def test_update_request_parses_camel_case():
    """更新请求使用 to_camel alias_generator，应接受驼峰键。"""
    body = {
        'resultId': 3,
        'predictTaskId': 20,
        'modelSceneBindingId': 6,
    }
    model = BacktestTaskUpdateRequestModel.model_validate(body)
    assert model.result_id == 3
    assert model.predict_task_id == 20
    assert model.model_scene_binding_id == 6
