import request from '@/utils/request'

// 获取MCP服务器列表
export function getMcpServers() {
  return request({
    url: '/ai/mcp/servers',
    method: 'get'
  })
}

// 获取MCP服务器状态
export function getMcpServerStatus(serverId) {
  return request({
    url: `/ai/mcp/servers/${serverId}/status`,
    method: 'get'
  })
}

// 更新MCP服务器状态
export function updateMcpServerStatus(serverId, status) {
  return request({
    url: `/ai/mcp/servers/${serverId}/status`,
    method: 'put',
    data: { status }
  })
} 