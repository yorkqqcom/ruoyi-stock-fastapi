import request from '@/utils/request'

// 查询Tushare接口配置列表
export function listApiConfig(query) {
  return request({
    url: '/tushare/apiConfig/list',
    method: 'get',
    params: query
  })
}

// 查询Tushare接口配置详细
export function getApiConfig(configId) {
  return request({
    url: '/tushare/apiConfig/' + configId,
    method: 'get'
  })
}

// 新增Tushare接口配置
export function addApiConfig(data) {
  return request({
    url: '/tushare/apiConfig',
    method: 'post',
    data: data
  })
}

// 修改Tushare接口配置
export function updateApiConfig(data) {
  return request({
    url: '/tushare/apiConfig',
    method: 'put',
    data: data
  })
}

// 删除Tushare接口配置
export function delApiConfig(configIds) {
  return request({
    url: '/tushare/apiConfig/' + configIds,
    method: 'delete'
  })
}

// 修改Tushare接口配置状态
export function changeApiConfigStatus(configId, status) {
  const data = {
    configId,
    status
  }
  return request({
    url: '/tushare/apiConfig/changeStatus',
    method: 'put',
    data: data
  })
}

// 导出Tushare接口配置
export function exportApiConfig(query) {
  return request({
    url: '/tushare/apiConfig/export',
    method: 'post',
    data: query
  })
}
