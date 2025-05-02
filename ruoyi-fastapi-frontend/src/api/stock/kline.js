// src/api/stock/kline.js
import request from '@/utils/request'
import dayjs from 'dayjs'

export function getanalyzer(params) {
  return request({
    url: '/api/stock/analyze',  // 修正为正确的路由
    method: 'post',
    data: params  // POST请求使用data传递参数
  })
}

export function getKline(params) {
  // 参数校验前置处理（避免传递 undefined）
  const processedParams = {
    symbol: params.symbol?.trim(), // 去除前后空格
    adjust_type: params.adjustType,
    ...(params.dateRange?.[0] && {
      start_date: dayjs(params.dateRange[0]).format('YYYY-MM-DD')
    }),
    ...(params.dateRange?.[1] && {
      end_date: dayjs(params.dateRange[1]).format('YYYY-MM-DD')
    })
  }

  // 添加请求参数验证
  if (!processedParams.symbol) {
    return Promise.reject(new Error('股票代码为必填项'))
  }

  return request({
    url: '/api/stock/kline',  // 确保使用/kline接口
    method: 'get',
    params: {
      symbol: processedParams.symbol,
      start_date: processedParams.start_date,
      end_date: processedParams.end_date,
      adjust: processedParams.adjust_type
    }
  })
}
