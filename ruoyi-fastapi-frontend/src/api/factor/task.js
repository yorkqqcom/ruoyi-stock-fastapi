import request from '@/utils/request'

// 查询因子任务列表
export function listFactorTask(query) {
  return request({
    url: '/factor/task/list',
    method: 'get',
    params: query
  })
}

// 新增因子任务
export function addFactorTask(data) {
  return request({
    url: '/factor/task',
    method: 'post',
    data: data
  })
}

// 修改因子任务
export function updateFactorTask(data) {
  return request({
    url: '/factor/task',
    method: 'put',
    data: data
  })
}

// 删除因子任务
export function delFactorTask(taskIds) {
  return request({
    url: '/factor/task/' + taskIds,
    method: 'delete'
  })
}

// 修改因子任务状态
export function changeFactorTaskStatus(taskId, status) {
  const params = {
    taskId,
    status
  }
  return request({
    url: '/factor/task/changeStatus',
    method: 'put',
    params: params
  })
}

// 执行因子任务
export function executeFactorTask(taskId) {
  return request({
    url: '/factor/task/execute/' + taskId,
    method: 'post'
  })
}


