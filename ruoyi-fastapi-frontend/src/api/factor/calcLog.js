import request from '@/utils/request'

// 查询因子计算日志列表
export function listFactorCalcLog(query) {
  return request({
    url: '/factor/calcLog/list',
    method: 'get',
    params: query
  })
}
