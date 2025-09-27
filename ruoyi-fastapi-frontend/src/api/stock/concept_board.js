import request from '@/utils/request'

// 获取概念板块列表
export function fetchConceptBoardList() {
  return request({
    url: '/api/concept/board-list',
    method: 'get'
  })
}

// 获取概念板块成分股
export function fetchConceptComponentStocks(symbol) {
  return request({
    url: `/api/concept/component-stocks?symbol=${encodeURIComponent(symbol)}`,
    method: 'get'
  })
}

// 搜索概念板块
export function searchConceptBoards(keyword) {
  return request({
    url: `/api/concept/search?keyword=${encodeURIComponent(keyword)}`,
    method: 'get'
  })
}
