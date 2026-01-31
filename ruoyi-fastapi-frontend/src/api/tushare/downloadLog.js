import request from '@/utils/request'

// 查询Tushare下载日志列表
export function listDownloadLog(query) {
  return request({
    url: '/tushare/downloadLog/list',
    method: 'get',
    params: query
  })
}

// 删除Tushare下载日志
export function delDownloadLog(logIds) {
  return request({
    url: '/tushare/downloadLog/' + logIds,
    method: 'delete'
  })
}

// 清空Tushare下载日志
export function cleanDownloadLog() {
  return request({
    url: '/tushare/downloadLog/clean',
    method: 'delete'
  })
}
