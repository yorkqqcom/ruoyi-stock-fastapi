import request from '@/utils/request'

// 分页查询因子结果
export function pageFactorValue(query) {
  return request({
    url: '/factor/value/page',
    method: 'get',
    params: query
  })
}

