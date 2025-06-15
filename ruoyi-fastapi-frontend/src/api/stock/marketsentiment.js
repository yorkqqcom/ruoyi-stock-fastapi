import request from '@/utils/request'

// 获取市场情绪分析
export function getMarketSentiment() {
  return request({
    url: '/api/market/sentiment/analysis',
    method: 'get'
  })
}

// 预测股票价格
export function predictStockPrice(data) {
  return request({
    url: '/api/market/sentiment/predict',
    method: 'get',
    params: data
  })
}

// 训练模型
export function trainModel(data) {
  return request({
    url: '/api/market/sentiment/train',
    method: 'get',
    params: data
  })
} 