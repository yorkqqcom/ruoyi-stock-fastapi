import request from '@/utils/request'

// 获取市场情绪分析数据
export function getStockSentiment(params) {
  // 确保参数格式正确
  const requestParams = {
    symbol: params.symbol,
    start_date: params.start_date,
    end_date: params.end_date,
    params: {
      windowSize: Number(params.params.windowSize),
      nClusters: Number(params.params.nClusters),
      distanceMetric: params.params.distanceMetric
    }
  }

  return request({
    url: '/api/stock/sentiment',
    method: 'post',
    data: requestParams
  })
}

// 获取市场机制分析数据
export function getMarketRegime(params) {
  return request({
    url: '/api/stock/regime',
    method: 'post',
    data: {
      symbol: params.symbol,
      start_date: params.start_date,
      end_date: params.end_date
    }
  })
}

// 获取交易信号数据
export function getTradingSignals(params) {
  return request({
    url: '/api/stock/signals',
    method: 'post',
    data: {
      symbol: params.symbol,
      start_date: params.start_date,
      end_date: params.end_date
    }
  })
}

// 获取历史机制转换数据
export function getRegimeTransitions(params) {
  return request({
    url: '/api/stock/transitions',
    method: 'post',
    data: {
      symbol: params.symbol,
      start_date: params.start_date,
      end_date: params.end_date
    }
  })
}

// 获取相关性分析数据
export function getCorrelationAnalysis(params) {
  return request({
    url: '/api/stock/correlation',
    method: 'post',
    data: {
      symbol: params.symbol,
      start_date: params.start_date,
      end_date: params.end_date
    }
  })
} 