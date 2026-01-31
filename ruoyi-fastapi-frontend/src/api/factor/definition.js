import request from '@/utils/request'

// 查询因子定义列表
export function listFactorDefinition(query) {
  return request({
    url: '/factor/definition/list',
    method: 'get',
    params: query
  })
}

// 新增因子定义
export function addFactorDefinition(data) {
  return request({
    url: '/factor/definition',
    method: 'post',
    data: data
  })
}

// 修改因子定义
export function updateFactorDefinition(data) {
  return request({
    url: '/factor/definition',
    method: 'put',
    data: data
  })
}

// 删除因子定义
export function delFactorDefinition(factorIds) {
  return request({
    url: '/factor/definition/' + factorIds,
    method: 'delete'
  })
}

