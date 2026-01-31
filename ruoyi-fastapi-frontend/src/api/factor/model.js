import request from '@/utils/request'

// ==================== 模型训练任务管理 ====================

// 查询模型训练任务列表
export function listModelTrainTask(query) {
  return request({
    url: '/factor/model/task/list',
    method: 'get',
    params: query
  })
}

// 获取模型训练任务详情
export function getModelTrainTask(taskId) {
  return request({
    url: '/factor/model/task/' + taskId,
    method: 'get'
  })
}

// 创建并执行模型训练任务
export function trainModel(data) {
  return request({
    url: '/factor/model/train',
    method: 'post',
    data: data
  })
}

// 编辑模型训练任务
export function editModelTrainTask(data) {
  return request({
    url: '/factor/model/task',
    method: 'put',
    data: data
  })
}

// 执行模型训练任务
export function executeModelTrainTask(taskId) {
  return request({
    url: '/factor/model/task/execute/' + taskId,
    method: 'post'
  })
}

// 删除模型训练任务
export function delModelTrainTask(taskIds) {
  return request({
    url: '/factor/model/task/' + taskIds,
    method: 'delete'
  })
}

// ==================== 模型训练结果管理 ====================

// 查询模型训练结果列表
export function listModelTrainResult(query) {
  return request({
    url: '/factor/model/result/list',
    method: 'get',
    params: query
  })
}

// 按训练任务获取该任务下的所有训练结果（包含版本号），不分页
export function listModelTrainResultByTask(taskId) {
  return request({
    url: '/factor/model/task/' + taskId + '/results',
    method: 'get'
  })
}

// 获取模型训练结果详情
export function getModelTrainResult(resultId) {
  return request({
    url: '/factor/model/result/' + resultId,
    method: 'get'
  })
}

// 绑定模型场景（为指定任务+场景绑定一个训练结果/版本）
export function bindModelScene(data) {
  return request({
    url: '/factor/model/scene/bind',
    method: 'post',
    data: data
  })
}

// ==================== 模型预测管理 ====================

// 执行模型预测
export function predictModel(data) {
  return request({
    url: '/factor/model/predict',
    method: 'post',
    data: data
  })
}

// 查询模型预测结果列表
export function listModelPredictResult(query) {
  return request({
    url: '/factor/model/predict/list',
    method: 'get',
    params: query
  })
}
