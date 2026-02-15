import request from '@/utils/request'

// ==================== 回测任务管理 ====================

// 创建回测任务
export function createBacktestTask(data) {
  return request({
    url: '/backtest/task/create',
    method: 'post',
    data: data
  })
}

// 获取回测任务分页列表
export function listBacktestTask(query) {
  return request({
    url: '/backtest/task/page',
    method: 'post',
    data: query
  })
}

// 获取回测任务详情
export function getBacktestTaskDetail(taskId) {
  return request({
    url: `/backtest/task/detail/${taskId}`,
    method: 'get'
  })
}

// 获取回测结果详情
export function getBacktestResultDetail(taskId) {
  return request({
    url: `/backtest/result/detail/${taskId}`,
    method: 'get'
  })
}

// 获取回测交易明细分页列表
export function listBacktestTrade(query) {
  return request({
    url: '/backtest/trade/page',
    method: 'post',
    data: query
  })
}
