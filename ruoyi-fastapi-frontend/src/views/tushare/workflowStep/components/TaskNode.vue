<template>
  <!-- 四个方向的输入连接点 -->
  <Handle type="target" :position="Position.Top" id="target-top" />
  <Handle type="target" :position="Position.Right" id="target-right" />
  <Handle type="target" :position="Position.Bottom" id="target-bottom" />
  <Handle type="target" :position="Position.Left" id="target-left" />
  <div class="task-node" :class="{ selected: selected }">
    <div class="node-header">
      <div class="node-icon">
        <el-icon><Document /></el-icon>
      </div>
      <div class="node-title">{{ data.stepName || '任务节点' }}</div>
    </div>
    <div class="node-body" v-if="apiConfig">
      <div class="node-info">{{ apiConfig.apiName }}</div>
    </div>
  </div>
  <!-- 四个方向的输出连接点 -->
  <Handle type="source" :position="Position.Top" id="source-top" />
  <Handle type="source" :position="Position.Right" id="source-right" />
  <Handle type="source" :position="Position.Bottom" id="source-bottom" />
  <Handle type="source" :position="Position.Left" id="source-left" />
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Document } from '@element-plus/icons-vue'

const props = defineProps({
  data: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  }
})

const apiConfig = computed(() => {
  if (!props.data.configId || !props.data.apiConfigs) {
    return null
  }
  return props.data.apiConfigs.find(config => config.configId === props.data.configId)
})
</script>

<style scoped lang="scss">
.task-node {
  min-width: 160px;
  background: white;
  border: 2px solid #3b82f6;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
  transition: all 0.2s;
  cursor: pointer;
  overflow: hidden;

  &:hover {
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    transform: translateY(-2px);
  }

  &.selected {
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
  }

  .node-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;

    .node-icon {
      font-size: 18px;
    }

    .node-title {
      flex: 1;
      font-size: 14px;
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .node-body {
    padding: 8px 12px;
    background: #f9fafb;

    .node-info {
      font-size: 12px;
      color: #6b7280;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

// 增大连接点尺寸，使其更容易点击
:deep(.vue-flow__handle) {
  width: 16px !important;
  height: 16px !important;
  border-radius: 50% !important;
  background: #3b82f6 !important;
  border: 3px solid white !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2) !important;
  cursor: crosshair !important;
  transition: all 0.2s !important;

  &:hover {
    width: 20px !important;
    height: 20px !important;
    background: #2563eb !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3) !important;
  }
}
</style>
