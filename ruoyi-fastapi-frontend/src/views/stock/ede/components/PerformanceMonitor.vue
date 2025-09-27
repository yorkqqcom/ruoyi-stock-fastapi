<template>
  <div class="performance-monitor" v-if="showMonitor">
    <div class="monitor-header">
      <i class="el-icon-data-analysis"></i>
      性能监控
      <el-button size="mini" type="text" @click="toggleMonitor">
        {{ collapsed ? '展开' : '收起' }}
      </el-button>
    </div>
    
    <div v-show="!collapsed" class="monitor-content">
      <div class="metric-item">
        <span class="metric-label">股票数量:</span>
        <span class="metric-value">{{ stockCount }}</span>
      </div>
      
      <div class="metric-item">
        <span class="metric-label">选中股票:</span>
        <span class="metric-value">{{ selectedStockCount }}</span>
      </div>
      
      <div class="metric-item">
        <span class="metric-label">选中指标:</span>
        <span class="metric-value">{{ selectedMetricCount }}</span>
      </div>
      
      <div class="metric-item">
        <span class="metric-label">数据行数:</span>
        <span class="metric-value">{{ dataRowCount }}</span>
      </div>
      
      <div class="metric-item">
        <span class="metric-label">渲染时间:</span>
        <span class="metric-value">{{ renderTime }}ms</span>
      </div>
      
      <div class="metric-item">
        <span class="metric-label">内存使用:</span>
        <span class="metric-value">{{ memoryUsage }}MB</span>
      </div>
      
      <div class="metric-item">
        <span class="metric-label">缓存命中率:</span>
        <span class="metric-value">{{ cacheHitRate }}%</span>
      </div>
      
      <div class="metric-item">
        <span class="metric-label">API响应时间:</span>
        <span class="metric-value">{{ apiResponseTime }}ms</span>
      </div>
      
      <div class="actions">
        <el-button size="mini" @click="clearCache">清空缓存</el-button>
        <el-button size="mini" @click="refreshStats">刷新统计</el-button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PerformanceMonitor',
  props: {
    showMonitor: {
      type: Boolean,
      default: false
    },
    stockCount: {
      type: Number,
      default: 0
    },
    selectedStockCount: {
      type: Number,
      default: 0
    },
    selectedMetricCount: {
      type: Number,
      default: 0
    },
    dataRowCount: {
      type: Number,
      default: 0
    }
  },
  data() {
    return {
      collapsed: false,
      renderTime: 0,
      memoryUsage: 0,
      cacheHitRate: 0,
      apiResponseTime: 0,
      renderStartTime: 0
    }
  },
  mounted() {
    this.startRenderTimer()
    this.updateMemoryUsage()
    this.loadCacheStats()
  },
  methods: {
    toggleMonitor() {
      this.collapsed = !this.collapsed
    },
    
    startRenderTimer() {
      this.renderStartTime = performance.now()
      this.$nextTick(() => {
        this.renderTime = Math.round(performance.now() - this.renderStartTime)
      })
    },
    
    updateMemoryUsage() {
      if (performance.memory) {
        this.memoryUsage = Math.round(performance.memory.usedJSHeapSize / 1024 / 1024)
      }
    },
    
    async loadCacheStats() {
      try {
        // 这里可以调用后端API获取缓存统计
        // const res = await fetchCacheStats()
        // this.cacheHitRate = res.data.cacheHitRate || 0
        // this.apiResponseTime = res.data.avgResponseTime || 0
      } catch (error) {
        console.warn('获取缓存统计失败:', error)
      }
    },
    
    clearCache() {
      this.$emit('clear-cache')
    },
    
    refreshStats() {
      this.updateMemoryUsage()
      this.loadCacheStats()
      this.startRenderTimer()
    }
  },
  watch: {
    stockCount() {
      this.startRenderTimer()
    },
    selectedStockCount() {
      this.startRenderTimer()
    },
    selectedMetricCount() {
      this.startRenderTimer()
    },
    dataRowCount() {
      this.startRenderTimer()
    }
  }
}
</script>

<style scoped>
.performance-monitor {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 200px;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  z-index: 1000;
  backdrop-filter: blur(10px);
}

.monitor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-weight: bold;
}

.monitor-header i {
  margin-right: 6px;
  color: #409eff;
}

.monitor-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 0;
}

.metric-label {
  color: #ccc;
  font-size: 11px;
}

.metric-value {
  color: #409eff;
  font-weight: bold;
  font-size: 11px;
}

.actions {
  margin-top: 8px;
  display: flex;
  gap: 4px;
}

.actions .el-button {
  padding: 4px 8px;
  font-size: 10px;
}
</style>
