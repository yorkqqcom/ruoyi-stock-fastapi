import request from '@/utils/request'

// 查询Tushare流程步骤列表
export function listWorkflowStep(query) {
  return request({
    url: '/tushare/workflowStep/list',
    method: 'get',
    params: query
  })
}

// 查询Tushare流程步骤详细
export function getWorkflowStep(stepId) {
  return request({
    url: '/tushare/workflowStep/' + stepId,
    method: 'get'
  })
}

// 新增Tushare流程步骤
export function addWorkflowStep(data) {
  return request({
    url: '/tushare/workflowStep',
    method: 'post',
    data: data
  })
}

// 修改Tushare流程步骤
export function updateWorkflowStep(data) {
  return request({
    url: '/tushare/workflowStep',
    method: 'put',
    data: data
  })
}

// 删除Tushare流程步骤
export function delWorkflowStep(stepIds) {
  return request({
    url: '/tushare/workflowStep/' + stepIds,
    method: 'delete'
  })
}

// 批量保存Tushare流程步骤
export function batchSaveWorkflowStep(data) {
  return request({
    url: '/tushare/workflowStep/batch',
    method: 'post',
    data: data
  })
}
