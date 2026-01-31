import request from '@/utils/request'

// 查询Tushare流程配置列表
export function listWorkflowConfig(query) {
  return request({
    url: '/tushare/workflowConfig/list',
    method: 'get',
    params: query
  })
}

// 查询Tushare流程配置详细（包含步骤列表）
export function getWorkflowConfig(workflowId) {
  return request({
    url: '/tushare/workflowConfig/' + workflowId,
    method: 'get'
  })
}

// 查询Tushare流程配置基础信息（不包含步骤列表），用于编辑表单回显
export function getWorkflowConfigBase(workflowId) {
  return request({
    url: '/tushare/workflowConfig/base/' + workflowId,
    method: 'get'
  })
}

// 新增Tushare流程配置
export function addWorkflowConfig(data) {
  return request({
    url: '/tushare/workflowConfig',
    method: 'post',
    data: data
  })
}

// 修改Tushare流程配置
export function updateWorkflowConfig(data) {
  return request({
    url: '/tushare/workflowConfig',
    method: 'put',
    data: data
  })
}

// 删除Tushare流程配置
export function delWorkflowConfig(workflowIds) {
  return request({
    url: '/tushare/workflowConfig/' + workflowIds,
    method: 'delete'
  })
}

// 修改Tushare流程配置状态
export function changeWorkflowConfigStatus(workflowId, status) {
  const data = {
    workflowId,
    status
  }
  return request({
    url: '/tushare/workflowConfig/changeStatus',
    method: 'put',
    data: data
  })
}
