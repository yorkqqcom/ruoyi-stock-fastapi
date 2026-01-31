<template>
  <!-- 四个方向的输入连接点 -->
  <Handle type="target" :position="Position.Top" id="top" />
  <Handle type="target" :position="Position.Right" id="right" />
  <Handle type="target" :position="Position.Bottom" id="bottom" />
  <Handle type="target" :position="Position.Left" id="left" />
  <div class="end-node" :class="{ selected: selected }">
    <div class="node-content">
      <div class="node-icon">
        <el-icon><CircleCheck /></el-icon>
      </div>
      <div class="node-label">{{ data.stepName || '结束' }}</div>
    </div>
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'
import { CircleCheck } from '@element-plus/icons-vue'

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
</script>

<style scoped lang="scss">
.end-node {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
  transition: all 0.2s;
  cursor: pointer;

  &:hover {
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
    transform: scale(1.05);
  }

  &.selected {
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.5);
  }

  .node-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;

    .node-icon {
      font-size: 24px;
    }

    .node-label {
      font-size: 12px;
      font-weight: 500;
      text-align: center;
      max-width: 80px;
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
