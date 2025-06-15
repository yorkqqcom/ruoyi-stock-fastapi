import request from '@/utils/request'
import dayjs from 'dayjs'

/**
 * 获取AI市场情绪分析数据
 * @param {Object} params 可选参数，如{symbol}
 * @returns {Promise} 返回市场情绪分析数据
 */
export function getSentimentAnalysis(params = {}) {
  return request({
    url: '/api/ai-market/sentiment-analysis',
    method: 'get',
    params
  })
}

/**
 * 获取市场预测数据
 * @param {Object} params 可选参数，如{symbol}
 * @returns {Promise} 返回市场预测数据
 */
export function getMarketPrediction(params = {}) {
  return request({
    url: '/api/ai-market/prediction',
    method: 'get',
    params
  })
}

/**
 * 获取新闻分析数据
 * @param {Object} params 可选参数，如{symbol}
 * @returns {Promise} 返回新闻分析数据
 */
export function getNewsAnalysis(params = {}) {
  return request({
    url: '/api/ai-market/news-analysis',
    method: 'get',
    params
  })
}

/**
 * 获取技术指标分析数据
 * @param {Object} params 可选参数，如{symbol}
 * @returns {Promise} 返回技术指标分析数据
 */
export function getTechnicalIndicators(params = {}) {
  return request({
    url: '/api/ai-market/technical-indicators',
    method: 'get',
    params
  })
}

/**
 * 获取均值回归分析数据
 * @param {Object} params 可选参数，如{symbol}
 * @returns {Promise} 返回均值回归分析数据
 */
export function getMeanReversionAnalysis(params = {}) {
  return request({
    url: '/api/ai-market/mean-reversion',
    method: 'get',
    params
  })
} 