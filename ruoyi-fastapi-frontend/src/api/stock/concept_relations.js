import request from '@/utils/request'

export function fetchConceptRelations() {
  return request({
    url: '/concept_relations/list',
    method: 'get'
  })
}

export function fetchConceptBoardList() {
  return request({
    url: '/concept_relations/boardlist',
    method: 'get'
  })
}
