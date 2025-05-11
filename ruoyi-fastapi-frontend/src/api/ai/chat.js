import request from '@/utils/request'

export function postChat(params) {
  return request({
    url: '/api/ai/chat',
    method: 'post',
    data: {
      query: params.query  // 确保参数名与后端匹配
    }
  })
}
