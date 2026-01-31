import request from '@/utils/request'

// 按关键字搜索股票基础信息（代码 / 中文名 / 英文名）
export function searchStockBasic(query) {
  return request({
    url: '/tushare/stock/search',
    method: 'get',
    params: query
  })
}

// 获取日K线数据
export function getDailyKline(query) {
  return request({
    url: '/tushare/stock/daily',
    method: 'get',
    params: query
  })
}

