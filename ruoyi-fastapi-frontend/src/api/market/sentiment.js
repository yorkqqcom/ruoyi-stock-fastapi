import request from '@/utils/request'

// 获取市场情绪数据
export function getMarketSentiment() {
  return request({
    url: '/market/sentiment',
    method: 'get'
  })
}

// 获取市场情绪历史数据
export function getMarketSentimentHistory(query) {
  return request({
    url: '/market/sentiment/history',
    method: 'get',
    params: query
  })
}

// 预测股票价格
export function predictStockPrice(data) {
  return request({
    url: '/market/sentiment/predict',
    method: 'post',
    data: data
  })
} 