// src/api/stock/lstm.js
import request from '@/utils/request'

/**
 * 获取LSTM训练可用的因子列表
 */
export function getLstmFeatures() {
  return request({
    url: '/api/stock/lstm/features',
    method: 'get'
  })
}

/**
 * 训练LSTM模型
 * @param {Object} params 训练参数
 * @param {string} params.symbol 股票代码
 * @param {string} params.start_date 开始日期
 * @param {string} params.end_date 结束日期
 * @param {Array<number>} params.lookback_options 回顾窗口选项
 * @param {number} params.epochs 训练轮次
 * @param {number} params.batch_size 批次大小
 * @param {number} params.learning_rate 学习率
 * @param {number} params.test_size 测试集比例
 * @param {number} params.validation_split 验证集比例
 * @param {boolean} params.use_sample_weights 是否使用样本权重
 * @param {number} params.sample_weight_decay 样本权重衰减率
 * @param {Array<string>} params.selected_features 选择的特征列表
 */
export function trainLstmModel(params) {
  return request({
    url: '/api/stock/lstm/train',
    method: 'post',
    data: params,
    timeout: 600000  // 10分钟超时（训练可能需要较长时间）
  })
}

/**
 * 预测未来股价
 * @param {Object} params 预测参数
 * @param {string} params.symbol 股票代码
 * @param {number} params.future_steps 预测未来天数
 */
export function predictFuture(params) {
  return request({
    url: '/api/stock/lstm/predict',
    method: 'post',
    data: params,
    timeout: 120000  // 2分钟超时
  })
}

/**
 * 获取模型信息
 * @param {string} symbol 股票代码
 */
export function getModelInfo(symbol) {
  return request({
    url: `/api/stock/lstm/model-info/${symbol}`,
    method: 'get'
  })
}

