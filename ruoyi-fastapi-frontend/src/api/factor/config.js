import request from '@/utils/request'

// 获取因子配置文件列表（config/train 下 .txt）
export function listFactorConfig() {
  return request({
    url: '/factor/model/config/list',
    method: 'get'
  })
}

// 获取因子配置文件内容，返回 { factorCodes }
export function getFactorConfigContent(path) {
  return request({
    url: '/factor/model/config/content',
    method: 'get',
    params: { path }
  })
}
