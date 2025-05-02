import request from '@/utils/request'

export function getConceptList(params) {
  return request({
    url: '/api/concept/list',
    method: 'get',
    params
  })
}

export function getConceptDetail(conceptName) {
  return request({
    url: `/api/concept/detail/${conceptName}`,
    method: 'get'
  })
}
export function getConceptLeaders(conceptName, params) {
  return request({
    url: `/api/leaders/${encodeURIComponent(conceptName)}`, // 添加编码
    method: 'get',
      params
  })
}
// 前端API增强（src/api/concept.js）


export function getConceptLists() {
  return request({
    url: '/api/concept/listconcept',
    method: 'get'
  })
}

export function getConceptHistory(params) {
  return request({
    url: '/api/stock/history',
    method: 'get',
    params
  })
}
