<template>
  <div class="ede-right" :style="{ width: width + 'px' }">
    <div class="panel-header">
      <i class="el-icon-data-analysis"></i>
      数据展示
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-button
        type="primary"
        size="small"
        icon="el-icon-download"
        @click="handleExtractData"
        :loading="loadingData"
        :disabled="!canExtractData">
        提取数据
      </el-button>
      <el-button
        size="small"
        icon="el-icon-download"
        @click="handleExportTable"
        :disabled="tableRows.length === 0">
        导出CVS
      </el-button>

      <!-- 调试开关 -->
      <el-switch
        v-model="debugStockExtraction"
        size="small"
        active-text="调试模式"
        inactive-text="正常模式"
        style="margin-left: 12px;"
        @change="handleDebugToggle">
      </el-switch>

      <el-radio-group :value="viewMode" size="small" style="margin-left: auto;" @input="handleViewModeChange">
        <el-radio-button label="table">
          <i class="el-icon-s-grid"></i> 表格
        </el-radio-button>
<!--        <el-radio-button label="chart">-->
<!--          <i class="el-icon-s-data"></i> 图表-->
<!--        </el-radio-button>-->
<!--        <el-radio-button label="kline">-->
<!--          <i class="el-icon-trend-charts"></i> K线-->
<!--        </el-radio-button>-->
      </el-radio-group>
    </div>

    <!-- 表格视图 -->
    <div v-show="viewMode === 'table'" class="table-view" :style="{ display: viewMode === 'table' ? 'block' : 'none' }">
      <!-- 有数据时显示表格 -->
      <el-table
        v-if="tableRows.length > 0"
        :key="`table-${tableKey}-${selectedMetricColumns.length}`"
        :data="tableRows"
        height="calc(100vh - 260px)"
        border
        size="mini"
        :header-cell-style="{background:'#fafafa'}"
        v-loading="loadingData">
        <el-table-column
          v-for="col in selectedMetricColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :width="col.width || 120"
          :align="col.align || 'right'"
          :fixed="col.prop === 'symbol' || col.prop === 'name'"
          :formatter="(row, column, cellValue) => formatCellDisplay(cellValue, col)"
          show-overflow-tooltip />
      </el-table>

      <!-- 无数据时显示列结构预览 -->
      <div v-else-if="selectedStocks.length > 0" class="column-preview">
        <div class="preview-header">
          <i class="el-icon-view"></i>
          列结构预览
        </div>
        <div class="preview-table">
          <!-- 表头 -->
          <div class="preview-row preview-header-row">
            <div v-for="col in selectedMetricColumns"
                 :key="col.prop"
                 class="preview-cell"
                 :style="{width: (col.width || 120) + 'px'}">
              {{ col.label }}
            </div>
            <div v-if="selectedMetricColumns.length === 0" class="preview-cell" style="width: 200px;">指标列（请选择指标）</div>
          </div>
          <!-- 显示选中的股票列表 -->
          <div v-for="stockSymbol in selectedStocks" :key="stockSymbol" class="preview-row">
            <div v-for="col in selectedMetricColumns"
                 :key="col.prop"
                 class="preview-cell"
                 :style="{width: (col.width || 120) + 'px'}">
              {{ col.prop === 'symbol' ? stockSymbol : (col.prop === 'name' ? getStockName(stockSymbol) : '-') }}
            </div>
            <div v-if="selectedMetricColumns.length === 0" class="preview-cell" style="width: 200px;">-</div>
          </div>
        </div>
      </div>

      <!-- 没有选中股票时显示提示 -->
      <div v-else class="no-data-hint">
        <div class="hint-content">
          <i class="el-icon-info"></i>
          <p>请先在左侧选择股票，然后选择指标类型和具体指标</p>
        </div>
      </div>
    </div>

    <!-- 图表视图 -->
    <div v-show="viewMode === 'chart'" class="chart-view">
      <div v-if="rawRows.length === 0" class="empty-data">
        <el-empty description="暂无数据，请点击提取数据按钮获取数据" />
      </div>
      <div v-else ref="lineChart" class="chart" />
    </div>

    <!-- K线视图 -->
    <div v-show="viewMode === 'kline'" class="kline-view">
      <div v-if="rawRows.length === 0" class="empty-data">
        <el-empty description="暂无数据，请点击提取数据按钮获取数据" />
      </div>
      <div v-else ref="klineChart" class="chart" />
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts'

export default {
  name: 'RightPanel',
  props: {
    width: {
      type: Number,
      default: 0
    },
    stocks: {
      type: Array,
      default: () => []
    },
    selectedStocks: {
      type: Array,
      default: () => []
    },
    selectedMetricKeys: {
      type: Array,
      default: () => []
    },
    selectedMetricColumns: {
      type: Array,
      default: () => []
    },
    viewMode: {
      type: String,
      default: 'table'
    },
    loadingData: {
      type: Boolean,
      default: false
    },
    rawRows: {
      type: Array,
      default: () => []
    },
    tableRows: {
      type: Array,
      default: () => []
    },
    canExtractData: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      lineChart: null,
      klineChart: null,
      tableKey: 0,
      debugStockExtraction: false
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.initCharts()
    })
  },
  beforeDestroy() {
    if (this.lineChart) this.lineChart.dispose()
    if (this.klineChart) this.klineChart.dispose()
  },
  watch: {
    viewMode(newMode) {
      if (newMode === 'chart' || newMode === 'kline') {
        this.$nextTick(() => {
          this.initCharts()
        })
      }
    },
    rawRows: {
      handler() {
        if (this.rawRows.length > 0) {
          this.$nextTick(() => {
            this.renderCharts()
          })
        }
      },
      deep: true
    },
    tableRows: {
      handler(newRows, oldRows) {
        // 更新表格key以强制重新渲染
        this.tableKey++
        // 强制更新表格显示
        this.$forceUpdate()

        // 延迟强制渲染表格
        this.$nextTick(() => {
          this.forceTableRender()
        })
      },
      deep: true,
      immediate: true
    },
    selectedMetricColumns: {
      handler(newCols, oldCols) {
        // 更新表格key以强制重新渲染
        this.tableKey++
        // 强制更新表格显示
        this.$forceUpdate()

        // 延迟再次强制更新，确保表格重新渲染
        this.$nextTick(() => {
          this.$forceUpdate()
          // 强制表格重新渲染
          this.forceTableRender()
        })
      },
      deep: true,
      immediate: true
    }
  },
  methods: {
    handleExtractData() {
      this.$emit('extract-data')
    },

    handleExportTable() {
      this.$emit('export-table')
    },

    handleViewModeChange(mode) {
      this.$emit('view-mode-change', mode)
    },

    handleDebugToggle(value) {
      this.$emit('debug-toggle', value)
    },

    // 强制表格重新渲染
    forceTableRender() {
      // 确保表格容器可见
      const tableContainer = this.$el.querySelector('.table-view')
      if (tableContainer) {
        tableContainer.style.display = 'block'
      }

      // 再次强制更新
      this.$forceUpdate()
    },

    getStockName(symbol) {
      // 从stocks数组中查找对应的股票名称
      const stock = this.stocks.find(s => s.symbol === symbol)
      return stock ? stock.name : symbol
    },

    // 格式化单元格显示
    formatCellDisplay(value, col) {
      if (value === null || value === undefined || value === '' || value === '-') {
        return '-'
      }

      // 数值类型格式化
      if (typeof value === 'number') {
        if (col.prop.includes('price') || col.prop.includes('amount')) {
          return value.toFixed(2)
        }
        if (col.prop.includes('pct') || col.prop.includes('ratio')) {
          return (value * 100).toFixed(2) + '%'
        }
        if (col.prop.includes('volume')) {
          return this.formatVolume(value)
        }
        return value.toString()
      }

      return String(value)
    },

    // 格式化成交量
    formatVolume(volume) {
      if (volume >= 100000000) {
        return (volume / 100000000).toFixed(2) + '亿'
      } else if (volume >= 10000) {
        return (volume / 10000).toFixed(2) + '万'
      }
      return volume.toString()
    },

    initCharts() {
      if (this.lineChart) {
        this.lineChart.dispose()
        this.lineChart = null
      }
      if (this.klineChart) {
        this.klineChart.dispose()
        this.klineChart = null
      }

      this.$nextTick(() => {
        if (this.$refs.lineChart) {
          this.lineChart = echarts.init(this.$refs.lineChart)
        }
        if (this.$refs.klineChart) {
          this.klineChart = echarts.init(this.$refs.klineChart)
        }

        if (this.rawRows.length > 0) {
          this.renderCharts()
        }
      })
    },

    renderCharts() {
      // 渲染折线图
      if (this.lineChart && this.$refs.lineChart) {
        const x = this.rawRows.map(r => r.date || r['日期'])
        const series = this.selectedMetricKeys
          .filter(k => !k.includes('volume') && !k.includes('amount'))
          .map(fullKey => {
            const label = this.selectedMetricColumns.find(c => c.prop === fullKey)?.label || fullKey
            return {
              type: 'line',
              name: label,
              data: this.rawRows.map(r => r[fullKey])
            }
          })

        this.lineChart.setOption({
          tooltip: { trigger: 'axis' },
          legend: { data: series.map(s => s.name) },
          xAxis: { type: 'category', data: x },
          yAxis: { type: 'value', scale: true },
          series
        })
        this.lineChart.resize()
      }
    }
  }
}
</script>

<style scoped>
.ede-right {
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

.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.toolbar .el-button {
  margin-right: 8px;
}

.toolbar .el-button:last-child {
  margin-right: 0;
}

.table-view, .chart-view, .kline-view {
  height: calc(100% - 60px);
  min-height: 300px;
  position: relative;
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 300px;
}

.empty-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
}

.column-preview {
  width: 100%;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}

.preview-header {
  background: #f5f7fa;
  padding: 12px 16px;
  font-size: 14px;
  color: #606266;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
}

.preview-header i {
  margin-right: 8px;
  color: #909399;
}

.preview-table {
  background: #fff;
}

.preview-row {
  display: flex;
  border-bottom: 1px solid #ebeef5;
}

.preview-row:last-child {
  border-bottom: none;
}

.preview-header-row {
  background: #fafafa;
  font-weight: bold;
}

.preview-cell {
  padding: 10px 12px;
  border-right: 1px solid #ebeef5;
  font-size: 12px;
  color: #606266;
  text-align: center;
  min-height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-cell:last-child {
  border-right: none;
}

.no-data-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
  color: #909399;
}

.hint-content {
  text-align: center;
}

.hint-content i {
  font-size: 32px;
  margin-bottom: 12px;
  display: block;
  color: #c0c4cc;
}

.hint-content p {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
}
</style>
