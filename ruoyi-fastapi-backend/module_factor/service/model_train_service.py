import json
import os
import re
import time
from datetime import datetime
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel
from config.env import AppConfig
from module_factor.dao.factor_dao import (
    ModelDataDao,
    ModelPredictResultDao,
    ModelSceneBindingDao,
    ModelTrainResultDao,
    ModelTrainTaskDao,
)
from module_factor.entity.do.factor_do import ModelPredictResult, ModelTrainResult
from module_factor.entity.vo.factor_vo import (
    EditModelTrainTaskModel,
    ModelPredictRequestModel,
    ModelPredictResultPageQueryModel,
    ModelSceneBindRequestModel,
    ModelTrainRequestModel,
    ModelTrainResultPageQueryModel,
)
from utils.log_util import logger


class ModelTrainService:
    """
    模型训练服务
    """

    # 模型存储目录
    MODEL_STORAGE_DIR = 'models'

    @classmethod
    def _ensure_model_dir(cls) -> str:
        """
        确保模型存储目录存在

        :return: 模型存储目录路径
        """
        # 使用项目根目录下的 models 目录
        import pathlib
        project_root = pathlib.Path(__file__).parent.parent.parent.parent
        model_dir = project_root / cls.MODEL_STORAGE_DIR
        if not model_dir.exists():
            model_dir.mkdir(parents=True, exist_ok=True)
        return str(model_dir)

    @classmethod
    async def prepare_training_data(
        cls,
        db: AsyncSession,
        factor_codes: list[str],
        symbol_universe: list[str] | None,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        准备训练数据：从数据库获取数据并转换为 DataFrame

        :param db: orm对象
        :param factor_codes: 因子代码列表
        :param symbol_universe: 股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 训练数据 DataFrame
        """
        logger.info(f'开始准备训练数据：因子={factor_codes}, 日期范围={start_date}~{end_date}')

        # 获取原始数据
        raw_data = await ModelDataDao.get_training_data(db, factor_codes, symbol_universe, start_date, end_date)

        if not raw_data:
            raise ValueError('未找到训练数据，请检查因子代码和日期范围')

        # 转换为 DataFrame
        df = pd.DataFrame(raw_data)

        # 按日期和股票代码排序
        df = df.sort_values(['trade_date', 'ts_code']).reset_index(drop=True)

        logger.info(f'数据准备完成，共 {len(df)} 条记录')
        return df

    @classmethod
    def generate_labels(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成标签：预测未来1天的涨跌方向

        :param df: 包含价格数据的 DataFrame
        :return: 添加了标签列的 DataFrame
        """
        logger.info('开始生成标签')

        # 按股票代码分组
        df = df.copy()
        df['next_close'] = df.groupby('ts_code')['close'].shift(-1)

        # 生成标签：1=涨，0=跌
        df['label'] = (df['next_close'] > df['close']).astype(int)

        # 删除没有下一交易日数据的行（最后一行）
        df = df.dropna(subset=['label'])

        logger.info(f'标签生成完成，涨跌分布：{df["label"].value_counts().to_dict()}')
        return df

    @classmethod
    def prepare_features(cls, df: pd.DataFrame, factor_codes: list[str]) -> tuple[pd.DataFrame, list[str]]:
        """
        准备特征：选择特征列并处理缺失值

        :param df: 数据 DataFrame
        :param factor_codes: 因子代码列表
        :return: (特征 DataFrame, 特征列名列表)
        """
        logger.info('开始准备特征')

        # 选择特征列
        feature_cols = []
        # 添加因子特征
        for code in factor_codes:
            if code in df.columns:
                feature_cols.append(code)
        # 添加价格相关特征
        price_features = ['open', 'high', 'low', 'close', 'pre_close', 'pct_chg', 'vol', 'amount']
        for feat in price_features:
            if feat in df.columns:
                feature_cols.append(feat)

        if not feature_cols:
            raise ValueError('未找到任何特征列')

        # 提取特征和标签
        X = df[feature_cols].copy()
        y = df['label'].copy()

        # 处理缺失值：用前一个值填充，如果还是缺失则用0填充
        X = X.ffill().fillna(0)

        logger.info(f'特征准备完成，特征数量：{len(feature_cols)}')
        return X, feature_cols

    @classmethod
    def train_model(
        cls, X_train: pd.DataFrame, y_train: pd.DataFrame, model_params: dict[str, Any]
    ) -> RandomForestClassifier:
        """
        训练随机森林模型

        :param X_train: 训练特征
        :param y_train: 训练标签
        :param model_params: 模型参数
        :return: 训练好的模型
        """
        logger.info('开始训练模型')

        # 默认参数
        default_params = {
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 2,
            'min_samples_leaf': 1,
            'random_state': 42,
        }
        default_params.update(model_params)

        # 创建模型
        model = RandomForestClassifier(**default_params)

        # 训练模型
        model.fit(X_train, y_train)

        logger.info('模型训练完成')
        return model

    @classmethod
    def evaluate_model(
        cls, model: RandomForestClassifier, X_test: pd.DataFrame, y_test: pd.DataFrame
    ) -> dict[str, Any]:
        """
        评估模型性能

        :param model: 训练好的模型
        :param X_test: 测试特征
        :param y_test: 测试标签
        :return: 评估指标字典
        """
        logger.info('开始评估模型')

        # 预测
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]  # 涨的概率

        # 计算指标
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        # 混淆矩阵
        cm = confusion_matrix(y_test, y_pred)
        cm_dict = {'tn': int(cm[0, 0]), 'fp': int(cm[0, 1]), 'fn': int(cm[1, 0]), 'tp': int(cm[1, 1])}

        # 特征重要性
        feature_importance = dict(zip(X_test.columns, model.feature_importances_.tolist()))

        metrics = {
            'accuracy': float(accuracy),
            'precision_score': float(precision),
            'recall_score': float(recall),
            'f1_score': float(f1),
            'confusion_matrix': cm_dict,
            'feature_importance': feature_importance,
        }

        logger.info(f'模型评估完成：准确率={accuracy:.4f}, F1={f1:.4f}')
        return metrics

    @classmethod
    def save_model(cls, model: RandomForestClassifier, task_id: int, version: int) -> str:
        """
        保存模型到文件系统

        :param model: 训练好的模型
        :param task_id: 任务ID
        :param version: 模型版本号
        :return: 模型文件路径
        """
        model_dir = cls._ensure_model_dir()
        timestamp = int(time.time())
        model_filename = f'model_{task_id}_v{version}_{timestamp}.pkl'
        model_path = os.path.join(model_dir, model_filename)

        joblib.dump(model, model_path)
        logger.info(f'模型已保存到：{model_path}')

        return model_path

    @classmethod
    async def train_model_service(
        cls, db: AsyncSession, request: ModelTrainRequestModel, task_id: int
    ) -> CrudResponseModel:
        """
        执行模型训练服务

        :param db: orm对象
        :param request: 训练请求
        :param task_id: 任务ID
        :return: 响应结果
        """
        start_time = time.time()

        try:
            # 更新任务状态为训练中
            await ModelTrainTaskDao.update_task_status_dao(db, task_id, '1')
            await db.commit()

            # 解析参数（支持逗号或换行分隔，与配置文件格式一致）
            factor_codes = [code.strip() for code in re.split(r'[,\n]+', request.factor_codes) if code.strip()]
            symbol_universe = None
            if request.symbol_universe:
                try:
                    symbol_universe = json.loads(request.symbol_universe)
                except json.JSONDecodeError:
                    symbol_universe = [s.strip() for s in request.symbol_universe.split(',') if s.strip()]

            model_params = {}
            if request.model_params:
                try:
                    model_params = json.loads(request.model_params)
                except json.JSONDecodeError:
                    logger.warning(f'模型参数解析失败，使用默认参数：{request.model_params}')

            # 1. 准备数据
            df = await cls.prepare_training_data(
                db, factor_codes, symbol_universe, request.start_date, request.end_date
            )

            # 2. 生成标签
            df = cls.generate_labels(df)

            # 3. 准备特征
            X, feature_cols = cls.prepare_features(df, factor_codes)
            y = df['label']

            # 4. 划分训练集和测试集
            train_size = int(len(X) * request.train_test_split)
            X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
            y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

            logger.info(f'训练集大小：{len(X_train)}, 测试集大小：{len(X_test)}')

            # 5. 训练模型
            model = cls.train_model(X_train, y_train, model_params)

            # 6. 评估模型
            metrics = cls.evaluate_model(model, X_test, y_test)

            # 7. 计算本次训练的模型版本号
            next_version = await ModelTrainResultDao.get_next_version_for_task(db, task_id)

            # 8. 保存模型
            model_path = cls.save_model(model, task_id, next_version)

            # 9. 保存训练结果到数据库
            train_duration = int(time.time() - start_time)
            result = ModelTrainResult(
                task_id=task_id,
                version=next_version,
                task_name=request.task_name,
                model_file_path=model_path,
                accuracy=metrics['accuracy'],
                precision_score=metrics['precision_score'],
                recall_score=metrics['recall_score'],
                f1_score=metrics['f1_score'],
                confusion_matrix=json.dumps(metrics['confusion_matrix']),
                feature_importance=json.dumps(metrics['feature_importance']),
                train_samples=len(X_train),
                test_samples=len(X_test),
                train_duration=train_duration,
                status='0',
            )
            await ModelTrainResultDao.add_result_dao(db, result)

            # 更新任务状态为训练完成
            await ModelTrainTaskDao.update_task_status_dao(db, task_id, '2')
            await ModelTrainTaskDao.update_task_run_stats_dao(db, task_id, True, datetime.now())
            await db.commit()

            logger.info(f'模型训练成功完成，任务ID：{task_id}')
            return CrudResponseModel(is_success=True, message='模型训练成功')

        except Exception as e:
            logger.error(f'模型训练失败：{str(e)}', exc_info=True)
            # 更新任务状态为训练失败
            await ModelTrainTaskDao.update_task_status_dao(db, task_id, '3')
            await ModelTrainTaskDao.update_task_run_stats_dao(db, task_id, False, datetime.now())
            await db.commit()
            return CrudResponseModel(is_success=False, message=f'模型训练失败：{str(e)}')

    @classmethod
    async def get_result_list_services(
        cls, db: AsyncSession, query_model: ModelTrainResultPageQueryModel, is_page: bool = True
    ):
        """
        获取训练结果列表

        :param db: orm对象
        :param query_model: 查询模型
        :param is_page: 是否分页
        :return: 结果列表
        """
        return await ModelTrainResultDao.get_result_list(db, query_model, is_page)

    @classmethod
    async def predict_service(cls, db: AsyncSession, request: ModelPredictRequestModel) -> CrudResponseModel:
        """
        执行预测服务

        :param db: orm对象
        :param request: 预测请求
        :return: 响应结果
        """
        try:
            # 根据传入参数选择要使用的训练结果：
            # 1）优先使用显式指定的 resultId；
            # 2）否则若提供了 taskId + sceneCode，则按场景绑定选择模型；
            # 3）否则报错。
            result: ModelTrainResult | None = None
            if request.result_id is not None:
                result = await ModelTrainResultDao.get_result_by_id(db, request.result_id)
            elif request.task_id is not None and request.scene_code:
                result = await cls.get_scene_active_model(db, request.task_id, request.scene_code)
            else:
                return CrudResponseModel(
                    is_success=False,
                    message='必须提供 resultId 或 (taskId + sceneCode) 才能执行预测',
                )

            if not result:
                return CrudResponseModel(is_success=False, message='训练结果不存在或不可用')

            if result.status != '0':
                return CrudResponseModel(is_success=False, message='训练结果状态异常')

            # 加载模型
            if not os.path.exists(result.model_file_path):
                return CrudResponseModel(is_success=False, message='模型文件不存在')

            model = joblib.load(result.model_file_path)

            # 获取特征重要性（用于确定需要的特征）
            feature_importance = json.loads(result.feature_importance)
            feature_cols = list(feature_importance.keys())

            # 准备预测数据
            ts_codes = [code.strip() for code in request.ts_codes.split(',')] if request.ts_codes else None

            # 从数据库获取预测日期的因子值和价格数据；若无当日数据则使用最近有因子数据的交易日
            predict_data = await ModelDataDao.get_training_data(
                db, feature_cols, ts_codes, request.trade_date, request.trade_date
            )
            trade_date_used = request.trade_date
            used_latest_fallback = False

            if not predict_data:
                latest_date = await ModelDataDao.get_latest_factor_date(db, feature_cols, ts_codes)
                if not latest_date:
                    return CrudResponseModel(
                        is_success=False,
                        message='未找到该股票在任何日期的因子数据，无法执行实时预测。请先在「因子管理」中执行因子计算任务后再试。'
                    )
                predict_data = await ModelDataDao.get_training_data(
                    db, feature_cols, ts_codes, latest_date, latest_date
                )
                if not predict_data:
                    return CrudResponseModel(
                        is_success=False,
                        message=f'未找到该股票在最近因子日期 {latest_date} 的完整数据（需同时有因子与行情），无法执行预测。'
                    )
                trade_date_used = latest_date
                used_latest_fallback = True

            # 转换为 DataFrame
            df = pd.DataFrame(predict_data)

            # 准备特征
            X = df[feature_cols].copy()
            X = X.ffill().fillna(0)

            # 预测
            predictions = model.predict(X)
            probabilities = model.predict_proba(X)[:, 1]

            # 保存预测结果（使用实际用到的交易日）
            predict_records = []
            for idx, row in df.iterrows():
                predict_records.append(
                    {
                        'result_id': int(result.id),
                        'ts_code': row['ts_code'],
                        'trade_date': trade_date_used,
                        'predict_label': int(predictions[idx]),
                        'predict_prob': float(probabilities[idx]),
                        'actual_label': None,
                        'is_correct': None,
                    }
                )

            await ModelPredictResultDao.bulk_insert_predictions_dao(db, predict_records)
            await db.commit()

            logger.info(f'预测完成，共 {len(predict_records)} 条记录，使用交易日: {trade_date_used}')
            if used_latest_fallback:
                return CrudResponseModel(
                    is_success=True,
                    message=f'当日无因子数据，已使用最近可用日期 {trade_date_used} 的因子进行预测，共 {len(predict_records)} 条。'
                )
            return CrudResponseModel(is_success=True, message=f'预测完成，共 {len(predict_records)} 条记录')

        except Exception as e:
            logger.error(f'预测失败：{str(e)}', exc_info=True)
            return CrudResponseModel(is_success=False, message=f'预测失败：{str(e)}')

    @classmethod
    async def get_predict_list_services(
        cls, db: AsyncSession, query_model: ModelPredictResultPageQueryModel, is_page: bool = True
    ):
        """
        获取预测结果列表

        :param db: orm对象
        :param query_model: 查询模型
        :param is_page: 是否分页
        :return: 结果列表
        """
        return await ModelPredictResultDao.get_predict_list(db, query_model, is_page)

    # ==================== 场景绑定相关服务 ====================

    @classmethod
    async def bind_scene_model_service(
        cls, db: AsyncSession, request: ModelSceneBindRequestModel
    ) -> CrudResponseModel:
        """
        为指定任务和场景绑定一个训练结果（模型版本）

        :param db: orm对象
        :param request: 绑定请求（taskId, sceneCode, resultId）
        :return: 响应结果
        """
        # 校验任务是否存在
        task = await ModelTrainTaskDao.get_task_by_id(db, request.task_id)
        if not task:
            return CrudResponseModel(is_success=False, message='训练任务不存在')

        # 校验训练结果是否存在且属于该任务
        result = await ModelTrainResultDao.get_result_by_id(db, request.result_id)
        if not result:
            return CrudResponseModel(is_success=False, message='训练结果不存在')
        if int(result.task_id) != request.task_id:
            return CrudResponseModel(is_success=False, message='训练结果不属于该训练任务')
        if result.status != '0':
            return CrudResponseModel(is_success=False, message='训练结果状态异常，无法绑定')

        try:
            await ModelSceneBindingDao.upsert_binding(
                db,
                task_id=request.task_id,
                scene_code=request.scene_code,
                result_id=request.result_id,
            )
            await db.commit()
            logger.info(
                f'模型场景绑定成功，task_id={request.task_id}, scene_code={request.scene_code}, result_id={request.result_id}'
            )
            return CrudResponseModel(is_success=True, message='场景绑定成功')
        except Exception as e:
            await db.rollback()
            logger.error(f'模型场景绑定失败：{str(e)}', exc_info=True)
            return CrudResponseModel(is_success=False, message=f'场景绑定失败：{str(e)}')

    @classmethod
    async def get_scene_active_model(
        cls, db: AsyncSession, task_id: int, scene_code: str
    ) -> ModelTrainResult | None:
        """
        根据任务ID和场景编码获取当前生效的模型训练结果：
        1）优先使用场景绑定表中 is_active='1' 的记录；
        2）若无绑定，则回退为该任务最新的成功版本。
        """
        # 优先按场景绑定查找
        binding = await ModelSceneBindingDao.get_active_binding(db, task_id, scene_code)
        if binding:
            result = await ModelTrainResultDao.get_result_by_id(db, int(binding.result_id))
            if result and result.status == '0':
                return result

        # 回退为该任务最新成功结果
        return await ModelTrainResultDao.get_latest_success_result_by_task(db, task_id)

    @classmethod
    async def edit_task_service(cls, db: AsyncSession, edit_task: EditModelTrainTaskModel) -> CrudResponseModel:
        """
        编辑模型训练任务服务

        :param db: orm对象
        :param edit_task: 编辑任务模型
        :return: 响应结果
        """
        if not edit_task.id:
            return CrudResponseModel(is_success=False, message='任务ID不能为空')

        # 检查任务是否存在
        task = await ModelTrainTaskDao.get_task_by_id(db, edit_task.id)
        if not task:
            return CrudResponseModel(is_success=False, message='训练任务不存在')

        # 检查任务状态，训练中的任务不允许编辑
        if task.status == '1':
            return CrudResponseModel(is_success=False, message='训练中的任务不允许编辑')

        try:
            result_count = await ModelTrainTaskDao.edit_task_dao(db, edit_task)
            await db.commit()
            
            if result_count > 0:
                logger.info(f'编辑模型训练任务成功，任务ID：{edit_task.id}')
                return CrudResponseModel(is_success=True, message='编辑成功')
            else:
                return CrudResponseModel(is_success=False, message='编辑失败，请检查数据')
        except Exception as e:
            await db.rollback()
            logger.error(f'编辑模型训练任务失败：{str(e)}', exc_info=True)
            return CrudResponseModel(is_success=False, message=f'编辑失败：{str(e)}')

    @classmethod
    async def execute_train_task_service(cls, db: AsyncSession, task_id: int) -> CrudResponseModel:
        """
        手动执行训练任务服务

        :param db: orm对象
        :param task_id: 任务ID
        :return: 响应结果
        """
        from module_factor.entity.vo.factor_vo import ModelTrainRequestModel

        # 获取任务信息
        task = await ModelTrainTaskDao.get_task_by_id(db, task_id)
        if not task:
            return CrudResponseModel(is_success=False, message='训练任务不存在')

        # 检查任务状态
        if task.status == '1':
            return CrudResponseModel(is_success=False, message='任务正在训练中，请勿重复执行')

        # 构建训练请求模型
        # 使用关键字参数，字段名使用 Python 字段名（下划线命名）
        # 注意：虽然使用了 alias_generator=to_camel，但关键字参数仍应使用 Python 字段名
        request = ModelTrainRequestModel(
            task_name=task.task_name,
            factor_codes=task.factor_codes or '',
            symbol_universe=task.symbol_universe,
            start_date=task.start_date or '',
            end_date=task.end_date or '',
            model_params=task.model_params,
            train_test_split=float(task.train_test_split) if task.train_test_split else 0.8,
        )

        # 异步执行训练任务
        from module_factor.task.model_train_task import execute_model_train_task
        from config.database import AsyncSessionLocal

        execute_model_train_task(AsyncSessionLocal, task_id, request)

        logger.info(f'训练任务已提交后台执行，任务ID：{task_id}')
        return CrudResponseModel(is_success=True, message='训练任务已提交后台执行')
