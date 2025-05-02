import request from '@/utils/request'

export function getBacktestList(params) {
  return request({
    url: '/api/backtest/list',
    method: 'get',
    params
  })
}

export function getBacktestDetail(conceptName) {
  return request({
    url: `/api/backtest/detail/${encodeURIComponent(conceptName)}`,
    method: 'get'
  })
}

export function getBacktestMetrics(conceptName) {
  return request({
    url: `/api/backtest/metrics/${encodeURIComponent(conceptName)}`,
    method: 'get'
  })
}
