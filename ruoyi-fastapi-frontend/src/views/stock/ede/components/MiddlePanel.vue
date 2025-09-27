<template>
  <div class="ede-middle" :style="{ width: width + 'px' }">
    <div class="panel-header">
      <i class="el-icon-s-operation"></i>
      指标配置
    </div>

    <!-- 指标类型选择 -->
    <div class="config-selector">
      <el-select
        :value="selectedConfigKey"
        placeholder="选择指标类型"
        size="small"
        @change="handleConfigChange"
        style="width: 100%; margin-bottom: 8px;">
        <el-option-group
          v-for="group in configGroups"
          :key="group.label"
          :label="group.label">
          <el-option
            v-for="config in group.options"
            :key="config.key"
            :label="config.name"
            :value="config.key">
            <span style="float: left">{{ config.name }}</span>
            <span style="float: right; color: #8492a6; font-size: 13px">{{ config.category }}</span>
          </el-option>
        </el-option-group>
      </el-select>
    </div>

    <!-- 参数配置区 -->
    <div v-if="currentConfig" class="params-config">
      <div class="param-summary">
        <div class="summary-item" v-for="param in currentConfigParams" :key="param.key">
          <span class="param-name">{{ param.title }}:</span>
          <span class="param-value">{{ getParamDisplayValue(param) }}</span>
          <el-tag
            v-if="param.required"
            size="mini"
            type="danger"
            style="margin-left: 4px;">
            必填
          </el-tag>
        </div>
      </div>
      <el-button
        type="primary"
        size="small"
        icon="el-icon-setting"
        @click="handleParamConfig"
        style="width: 100%; margin-top: 8px;">
        配置参数
      </el-button>
    </div>

    <!-- 指标树 -->
    <div class="metrics-section">
      <div class="section-title">
        <i class="el-icon-menu"></i>
        可选指标
        <span class="selected-count">(已选{{ selectedMetricKeys.length }}个)</span>
        <el-button
          size="mini"
          type="text"
          icon="el-icon-refresh"
          @click="handleReloadCache"
          title="重新加载缓存">
        </el-button>
      </div>
      
      <el-input
        :value="metricFilter"
        placeholder="搜索指标"
        clearable
        size="small"
        prefix-icon="el-icon-search"
        style="margin-bottom: 8px;"
        @input="handleMetricFilterChange"
      />
      
      <el-tree
        ref="metricTree"
        class="metric-tree"
        :data="metricTree"
        node-key="key"
        show-checkbox
        check-strictly
        :props="{ label: 'label', children: 'children' }"
        @check-change="handleMetricCheck"
        :filter-node-method="filterNode"
      />
    </div>
  </div>
</template>

<script>
import { debounce } from 'lodash-es'

export default {
  name: 'MiddlePanel',
  props: {
    width: {
      type: Number,
      default: 320
    },
    configGroups: {
      type: Array,
      default: () => []
    },
    selectedConfigKey: {
      type: String,
      default: ''
    },
    currentConfig: {
      type: Object,
      default: null
    },
    configParams: {
      type: Object,
      default: () => ({})
    },
    metricTree: {
      type: Array,
      default: () => []
    },
    checkedMetricKeys: {
      type: Array,
      default: () => []
    },
    metricFilter: {
      type: String,
      default: ''
    }
  },
  computed: {
    currentConfigParams() {
      if (!this.currentConfig || !this.currentConfig.akshare) return []
      const params = this.currentConfig.akshare.params || {}
      return Object.keys(params).map(key => ({
        key,
        ...params[key]
      }))
    },
    selectedMetricKeys() {
      return Array.isArray(this.checkedMetricKeys) ? this.checkedMetricKeys : []
    }
  },
  created() {
    // 创建防抖函数
    this.debouncedMetricFilter = debounce((value) => {
      this.$refs.metricTree?.filter(value)
    }, 300)
  },
  methods: {
    handleConfigChange(configKey) {
      this.$emit('config-change', configKey)
    },
    
    handleParamConfig() {
      this.$emit('param-config')
    },
    
    handleMetricCheck(data, checked) {
      this.$nextTick(() => {
        if (this.$refs.metricTree) {
          const newKeys = this.$refs.metricTree.getCheckedKeys()
          this.$emit('metric-check', newKeys)
        }
      })
    },
    
    handleMetricFilterChange(value) {
      this.$emit('metric-filter', value)
      this.debouncedMetricFilter(value)
    },
    
    handleReloadCache() {
      this.$emit('reload-cache')
    },
    
    filterNode(value, data) {
      if (!value) return true
      return data.label.indexOf(value) !== -1
    },
    
    getParamDisplayValue(param) {
      const value = this.configParams[param.key]
      if (value === undefined || value === '') {
        return '未配置'
      }

      if (param.options && param.options.length > 0) {
        const option = param.options.find(opt => opt.value === value)
        return option ? option.label : value
      }

      return value
    },
    
    // 供父组件调用的方法
    filterMetrics(value) {
      this.$refs.metricTree?.filter(value)
    }
  }
}
</script>

<style scoped>
.ede-middle {
  height: 100%;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.panel-header {
  font-weight: bold;
  margin-bottom: 12px;
  color: #303133;
  font-size: 16px;
  display: flex;
  align-items: center;
}

.panel-header i {
  margin-right: 8px;
  color: #409eff;
}

.config-selector {
  margin-bottom: 12px;
}

.params-config {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}

.param-summary {
  margin-bottom: 8px;
}

.summary-item {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
}

.summary-item:last-child {
  margin-bottom: 0;
}

.param-name {
  color: #606266;
  font-weight: 500;
  min-width: 80px;
}

.param-value {
  color: #409eff;
  margin-left: 8px;
  flex: 1;
  word-break: break-all;
}

.metrics-section {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.section-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title i {
  margin-right: 6px;
  color: #909399;
}

.selected-count {
  font-size: 12px;
  color: #409eff;
  font-weight: normal;
}

.metric-tree {
  flex: 1;
  overflow: auto;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
}

/* 滚动条样式优化 */
.metric-tree::-webkit-scrollbar {
  width: 6px;
}

.metric-tree::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.metric-tree::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.metric-tree::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
