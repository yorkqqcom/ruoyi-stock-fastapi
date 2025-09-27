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

export function fetchConceptCorrelation(concept_name) {
  return request({
    url: `/concept_relations/correlation?concept_name=${encodeURIComponent(concept_name)}`,
    method: 'get'
  })
}

export function fetchConceptModelByName(concept_name, min_overlap = 0.4, max_overlap = 1.0) {
  return request({
    url: `/concept_relations/model_by_name?concept_name=${encodeURIComponent(concept_name)}&min_overlap=${min_overlap}&max_overlap=${max_overlap}`,
    method: 'get'
  })
}
