// src/api/stock/market.js
import request from '@/utils/request'
import dayjs from 'dayjs'

/**
 * 获取每日市场复盘数据
 * @returns {Promise} 返回市场复盘数据
 */
export function getDailyReview() {
  return request({
    url: '/api/market/daily-review',
    method: 'get'
  })
}

/**
 * 获取大盘指数数据
 * @param {Object} params 查询参数
 * @param {string} params.start_date 开始日期
 * @param {string} params.end_date 结束日期
 * @returns {Promise} 返回大盘指数数据
 */
export function getIndexData(params) {
  const processedParams = {
    ...(params?.start_date && {
      start_date: dayjs(params.start_date).format('YYYY-MM-DD')
    }),
    ...(params?.end_date && {
      end_date: dayjs(params.end_date).format('YYYY-MM-DD')
    })
  }

  return request({
    url: '/api/market/index-data',
    method: 'get',
    params: processedParams
  })
}

/**
 * 获取市场情绪数据
 * @param {Object} params 查询参数
 * @param {string} params.date 日期
 * @returns {Promise} 返回市场情绪数据
 */
export function getMarketSentiment(params) {
  const processedParams = {
    ...(params?.date && {
      date: dayjs(params.date).format('YYYY-MM-DD')
    })
  }

  return request({
    url: '/api/market/market-sentiment',
    method: 'get',
    params: processedParams
  })
}

/**
 * 获取北向资金数据
 * @param {Object} params 查询参数
 * @param {string} params.start_date 开始日期
 * @param {string} params.end_date 结束日期
 * @returns {Promise} 返回北向资金数据
 */
export function getNorthMoney(params) {
  const processedParams = {
    ...(params?.start_date && {
      start_date: dayjs(params.start_date).format('YYYY-MM-DD')
    }),
    ...(params?.end_date && {
      end_date: dayjs(params.end_date).format('YYYY-MM-DD')
    })
  }

  return request({
    url: '/api/market/north-money',
    method: 'get',
    params: processedParams
  })
}

/**
 * 获取主力资金流向数据
 * @param {Object} params 查询参数
 * @param {string} params.date 日期
 * @returns {Promise} 返回主力资金流向数据
 */
export function getFundFlow(params) {
  const processedParams = {
    ...(params?.date && {
      date: dayjs(params.date).format('YYYY-MM-DD')
    })
  }

  return request({
    url: '/api/market/fund-flow',
    method: 'get',
    params: processedParams
  })
}

/**
 * 获取市场热点数据
 * @param {Object} params 查询参数
 * @param {string} params.date 日期
 * @returns {Promise} 返回市场热点数据
 */
export function getMarketHotspots(params) {
  const processedParams = {
    ...(params?.date && {
      date: dayjs(params.date).format('YYYY-MM-DD')
    })
  }

  return request({
    url: '/api/market/hotspots',
    method: 'get',
    params: processedParams
  })
}

/**
 * 获取行业板块数据
 * @param {Object} params 查询参数
 * @param {string} params.date 日期
 * @returns {Promise} 返回行业板块数据
 */
export function getIndustrySectors(params) {
  const processedParams = {
    ...(params?.date && {
      date: dayjs(params.date).format('YYYY-MM-DD')
    })
  }

  return request({
    url: '/api/market/industry-sectors',
    method: 'get',
    params: processedParams
  })
}

/**
 * 获取市场预警数据
 * @param {Object} params 查询参数
 * @param {string} params.date 日期
 * @returns {Promise} 返回市场预警数据
 */
export function getMarketAlerts(params) {
  const processedParams = {
    ...(params?.date && {
      date: dayjs(params.date).format('YYYY-MM-DD')
    })
  }

  return request({
    url: '/api/market/alerts',
    method: 'get',
    params: processedParams
  })
}

/**
 * 获取市场统计数据
 * @param {Object} params 查询参数
 * @param {string} params.start_date 开始日期
 * @param {string} params.end_date 结束日期
 * @returns {Promise} 返回市场统计数据
 */
export function getMarketStats(params) {
  const processedParams = {
    ...(params?.start_date && {
      start_date: dayjs(params.start_date).format('YYYY-MM-DD')
    }),
    ...(params?.end_date && {
      end_date: dayjs(params.end_date).format('YYYY-MM-DD')
    })
  }

  return request({
    url: '/api/market/stats',
    method: 'get',
    params: processedParams
  })
}

/**
 * 获取指数分时行情数据
 * @param {Object} params 查询参数
 * @param {string} params.symbol 指数代码，如"000001"表示上证指数
 * @param {string} params.period 周期，可选值：'1', '5', '15', '30', '60'
 * @returns {Promise} 返回分时行情数据
 */
export function getIndexMinData(params) {
  return request({
    url: '/api/market/index-min-data',
    method: 'get',
    params: {
      symbol: params?.symbol || '000001',
      period: params?.period || '1'
    }
  })
}

/**
 * 获取主要指数分时数据
 * @param {Object} params 查询参数
 * @param {string} params.symbol 指数代码，如"000001"表示上证指数
 * @param {string} params.period 周期，可选值：'1', '5', '15', '30', '60'
 * @returns {Promise} 返回主要指数分时数据
 */
export function getMainIndicesMinData(params) {
  return request({
    url: '/api/market/main-indices-min-data',
    method: 'get',
    params: {
      symbol: params?.symbol || '000001',
      period: params?.period || '1'
    }
  })
}

/**
 * 获取概念板块数据
 * @returns {Promise} 返回概念板块数据
 */
export function getConceptBoardData() {
  return request({
    url: '/api/market/concept-board',
    method: 'get'
  })
}

/**
 * 获取板块资金流向数据
 * @returns {Promise} 返回板块资金流向数据
 */
export function getSectorFundFlow() {
  return request({
    url: '/api/market/sector-fund-flow',
    method: 'get'
  })
}

/**
 * 获取涨停跌停股票数据
 * @returns {Promise} 返回涨停跌停股票数据
 */
export function getLimitStocks() {
  return request({
    url: '/api/market/limit-stocks',
    method: 'get'
  })
}

/**
 * 获取龙虎榜数据
 * @returns {Promise} 返回龙虎榜数据
 */
export function getLhbData() {
  return request({
    url: '/api/market/lhb-data',
    method: 'get'
  })
}

/**
 * 获取市场分析数据
 * @returns {Promise} 返回市场分析数据
 */
export function getMarketAnalysis() {
  return request({
    url: '/api/market/market-analysis',
    method: 'get'
  })
} 