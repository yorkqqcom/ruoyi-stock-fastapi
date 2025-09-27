// src/api/stock/ede.js
import request from '@/utils/request'
import dayjs from 'dayjs'

export function fetchStockList() {
  return request({
    url: '/api/stock/list',
    method: 'get'
  })
}

// 获取所有可用的指标配置
export function fetchAvailableConfigs() {
  return request({
    url: '/api/stock/ede/configs',
    method: 'get'
  })
}

// 获取指标树结构
export function fetchMetricTree() {
  return request({
    url: '/api/stock/ede/metric-tree',
    method: 'get'
  })
}

// 获取指定配置详情
export function fetchConfigDetail(configKey) {
  return request({
    url: `/api/stock/ede/config/${configKey}`,
    method: 'get'
  })
}

// 验证参数配置
export function validateParams(configKey, params) {
  return request({
    url: '/api/stock/ede/validate-params',
    method: 'post',
    data: {
      key: configKey,
      params: params || {}
    }
  })
}

// 通用的数据获取接口
export function fetchDynamicData(configKey, params, control = {}) {
  const body = {
    key: configKey,
    params: params || {},
    control: { 
      paginate: false,
      ...control
    }
  }
  
  return request({
    url: '/api/stock/ede/dynamic',
    method: 'post',
    data: body
  }).then(res => {
    // 兼容旧结构：若后端按标准结构返回 { rows, total }
    if (res && res.data && res.data.rows) {
      return { data: res.data.rows, config: res.data.config }
    }
    return res
  })
}

// 带个股代码过滤的数据获取接口
export function fetchDynamicDataWithFilter(configKey, params, filterSymbols = []) {
  const control = {
    paginate: false,
    filter_symbols: filterSymbols.length > 0 ? filterSymbols : undefined
  }
  
  return fetchDynamicData(configKey, params, control)
}

// 多配置混合数据提取接口
export function fetchMultiConfigData(configRequests, filterSymbols = []) {
  return request({
    url: '/api/stock/ede/multi-config-dynamic',
    method: 'post',
    data: {
      configs: configRequests,
      filter_symbols: filterSymbols
    }
  })
}

