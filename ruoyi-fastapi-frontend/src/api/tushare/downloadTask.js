import request from '@/utils/request'

// 查询Tushare下载任务列表
export function listDownloadTask(query) {
  return request({
    url: '/tushare/downloadTask/list',
    method: 'get',
    params: query
  })
}

// 查询Tushare下载任务详细
export function getDownloadTask(taskId) {
  return request({
    url: '/tushare/downloadTask/' + taskId,
    method: 'get'
  })
}

// 新增Tushare下载任务
export function addDownloadTask(data) {
  return request({
    url: '/tushare/downloadTask',
    method: 'post',
    data: data
  })
}

// 修改Tushare下载任务
export function updateDownloadTask(data) {
  return request({
    url: '/tushare/downloadTask',
    method: 'put',
    data: data
  })
}

// 删除Tushare下载任务
export function delDownloadTask(taskIds) {
  return request({
    url: '/tushare/downloadTask/' + taskIds,
    method: 'delete'
  })
}

// 修改Tushare下载任务状态
export function changeDownloadTaskStatus(taskId, status) {
  const data = {
    taskId,
    status
  }
  return request({
    url: '/tushare/downloadTask/changeStatus',
    method: 'put',
    data: data
  })
}

// 执行Tushare下载任务
export function executeDownloadTask(taskId) {
  return request({
    url: '/tushare/downloadTask/execute/' + taskId,
    method: 'post'
  })
}

// 获取Tushare下载任务统计信息
export function getDownloadTaskStatistics(taskId) {
  return request({
    url: '/tushare/downloadTask/statistics/' + taskId,
    method: 'get'
  })
}