import request from '@/utils/request'

export function getTradingSignalList(params) {
  return request({
    url: '/api/signals',
    method: 'get',
    params
  })
}

export function getSignalDetail(id) {
  return request({
    url: `/api/signals/${id}`,
    method: 'get'
  })
}

export function updateSignal(data) {
  return request({
    url: '/api/signals',
    method: 'put',
    data
  })
}
