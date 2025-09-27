<template>
  <div class="app-container ede-optimized-container">
    <div class="ede-panels">
      <!-- 左侧：股票选择区 -->
      <LeftPanel
        :width="leftWidth"
        :stocks="stocks"
        :selected-stocks="selectedStocks"
        :loading="loadingStocks"
        @select-stock="handleSelectStock"
        @toggle-stock="handleToggleStock"
        @batch-select-stocks="handleBatchSelectStocks"
        @resize="handleLeftResize"
      />

      <div class="ede-resizer" @mousedown.prevent="startDrag('left')"></div>

      <!-- 中间：指标选择区 -->
      <MiddlePanel
        :width="middleWidth"
        :config-groups="configGroups"
        :selected-config-key="selectedConfigKey"
        :current-config="currentConfig"
        :config-params="configParams"
        :metric-tree="metricTree"
        :checked-metric-keys="checkedMetricKeys"
        :metric-filter="metricFilter"
        @config-change="handleConfigChange"
        @param-config="handleParamConfig"
        @metric-check="handleMetricCheck"
        @metric-filter="handleMetricFilter"
        @resize="handleMiddleResize"
      />

      <div class="ede-resizer" @mousedown.prevent="startDrag('middle')"></div>

      <!-- 右侧：数据展示区 -->
      <RightPanel
        ref="rightPanel"
        :width="rightWidth"
        :stocks="stocks"
        :selected-stocks="selectedStocks"
        :selected-metric-keys="selectedMetricKeys"
        :selected-metric-columns="selectedMetricColumns"
        :view-mode="viewMode"
        :loading-data="loadingData"
        :raw-rows="rawRows"
        :table-rows="tableRows"
        :can-extract-data="canExtractData"
        @extract-data="extractData"
        @export-table="exportTable"
        @view-mode-change="handleViewModeChange"
        @debug-toggle="handleDebugToggle"
        @resize="handleRightResize"
      />
    </div>

    <!-- 参数配置弹窗 -->
    <ParamConfigDialog
      :visible="paramConfigDialogVisible"
      :config-info="currentConfig"
      :params="currentConfigParams"
      :initial-values="configParams"
      @confirm="handleParamConfigConfirm"
      @close="handleParamConfigClose"
    />
  </div>
</template>

<script>
import { debounce } from 'lodash-es'
import { fetchStockList, fetchMetricTree, fetchDynamicDataWithFilter, fetchConfigDetail, validateParams, fetchAvailableConfigs, fetchMultiConfigData } from '@/api/stock/ede'
import enhancedConfig, { METRIC_CATEGORIES } from './enhanced-config'
import LeftPanel from './components/LeftPanel.vue'
import MiddlePanel from './components/MiddlePanel.vue'
import RightPanel from './components/RightPanel.vue'
import ParamConfigDialog from './components/ParamConfigDialog.vue'

export default {
  name: 'EDEOptimized',
  components: {
    LeftPanel,
    MiddlePanel,
    RightPanel,
    ParamConfigDialog
  },
  data() {
    return {
      // 面板宽度
      leftWidth: 280,
      middleWidth: 320,
      rightWidth: 0,
      dragging: null,
      startX: 0,
      startLeft: 0,
      startMiddle: 0,

      // 左侧
      loadingStocks: false,
      stocks: [],

      // 中间
      selectedConfigKey: '',
      configGroups: [],
      currentConfig: null,
      configParams: {},
      metricFilter: '',
      metricTree: [],
      checkedMetricKeys: [],

      // 右侧
      selectedStocks: [],
      viewMode: 'table',
      loadingData: false,
      rawRows: [],
      tableRows: [],

      // 配置缓存
      configCache: {},

      // 参数配置弹窗
      paramConfigDialogVisible: false,

      // 防抖函数
      debouncedMetricFilter: null,

      // 调试开关
      debugStockExtraction: false,

      // 股票代码和名称提取缓存
      stockExtractionCache: new Map()
    }
  },
  computed: {
    selectedMetricKeys() {
      return Array.isArray(this.checkedMetricKeys) ? this.checkedMetricKeys : []
    },
    selectedMetricColumns() {
      // 使用统一的列定义方法
      const columns = this.getUnifiedColumns()

      // 调试信息：输出列配置
      if (this.debugStockExtraction) {
        console.log('生成的列配置:', columns)
        console.log('选中的指标键:', this.selectedMetricKeys)
      }

      return columns
    },
    currentConfigParams() {
      if (!this.currentConfig || !this.currentConfig.akshare) return []
      const params = this.currentConfig.akshare.params || {}
      return Object.keys(params).map(key => ({
        key,
        ...params[key]
      }))
    },
    canExtractData() {
      return this.selectedStocks.length > 0 &&
             this.selectedMetricKeys.length > 0 &&
             (this.hasMultiConfigMetrics() || (this.selectedConfigKey && this.checkParamsValid()))
    }
  },
  created() {
    // 初始化防抖函数
    this.debouncedMetricFilter = debounce((value) => {
      this.$refs.middlePanel?.filterMetrics(value)
    }, 300)
  },
  mounted() {
    this.rightWidth = document.body.clientWidth - this.leftWidth - this.middleWidth - 16
    window.addEventListener('resize', this.onResize)
    document.addEventListener('mousemove', this.onDrag)
    document.addEventListener('mouseup', this.stopDrag)

    this.$nextTick(() => {
      this.loadConfigs()
      this.loadStocks()
    })
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.onResize)
    document.removeEventListener('mousemove', this.onDrag)
    document.removeEventListener('mouseup', this.stopDrag)
  },
  watch: {
    metricFilter(val) {
      this.debouncedMetricFilter(val)
    },
    checkedMetricKeys: {
      handler(newKeys, oldKeys) {
        // 当指标选择发生变化时，重新构建表格数据
        if (newKeys.length !== oldKeys.length ||
            JSON.stringify(newKeys) !== JSON.stringify(oldKeys)) {
          if (this.rawRows.length > 0) {
            this.$nextTick(() => {
              this.buildTableData()
            })
          }
        }
      },
      deep: true,
      immediate: false
    },
    selectedStocks: {
      handler(newStocks, oldStocks) {
        // 股票选择变化已在handleToggleStock中处理，这里不需要额外处理
      },
      deep: true
    }
  },
  methods: {
    // 配置加载相关
    async loadConfigs() {
      try {
        // 优先从后端API获取配置
        try {
          const res = await fetchMetricTree()
          if (res.data && res.data.tree) {
            this.metricTree = res.data.tree
            this.buildConfigGroups(res.data.tree)
            await this.loadConfigsFromBackend()

            if (this.metricTree.length > 0 && this.metricTree[0].children.length > 0) {
              const firstConfig = this.metricTree[0].children[0]
              this.selectedConfigKey = firstConfig.key
              await this.handleConfigChange(firstConfig.key)
            }
            return
          }
        } catch (apiError) {
          // 后端API调用失败，使用本地配置作为备用
        }

        // 备用方案：使用本地配置
        const localTree = this.buildMetricTreeFromConfig()
        this.metricTree = localTree
        this.buildConfigGroups(localTree)
        await this.preloadAllConfigs()

        if (this.metricTree.length > 0 && this.metricTree[0].children.length > 0) {
          const firstConfig = this.metricTree[0].children[0]
          this.selectedConfigKey = firstConfig.key
          await this.handleConfigChange(firstConfig.key)
        }
      } catch (error) {
        this.$message.error('加载配置失败: ' + error.message)
      }
    },

    buildMetricTreeFromConfig() {
      const treeData = []
      for (const [categoryName, categoryConfig] of Object.entries(METRIC_CATEGORIES)) {
        const categoryNode = {
          label: categoryName,
          key: `category_${categoryName}`,
          children: []
        }

        const configKeys = categoryConfig.children || []


        for (const configKey of configKeys) {
          const config = enhancedConfig[configKey]
          if (!config) {
            continue
          }

          const columns = config.ui?.columns || []
          const children = []


          for (const col of columns) {
            const excludedFields = ["date", "symbol", "name", "index"]
            if (!excludedFields.includes(col.field)) {
              children.push({
                label: col.label || col.field,
                key: `${configKey}:${col.field}`,
                configKey: configKey,
                field: col.field,
                width: col.width || 120,
                align: col.align || "left"
              })
            }
          }

          categoryNode.children.push({
            label: config.name || configKey,
            key: configKey,
            children: children,
            description: config.description || ""
          })

        }

        if (categoryNode.children.length > 0) {
          treeData.push(categoryNode)
        }
      }


      return treeData
    },

    async loadConfigsFromBackend() {
      try {
        const configsRes = await fetchAvailableConfigs()
        if (configsRes.data && configsRes.data.configs) {
          const configs = configsRes.data.configs
          for (const config of configs) {
            try {
              const detailRes = await fetchConfigDetail(config.key)
              if (detailRes.data && detailRes.data.config) {
                this.configCache[config.key] = detailRes.data.config
              }
            } catch (error) {
              // 获取配置详情失败，跳过
            }
          }
        }
      } catch (error) {
        // 从后端加载配置详情失败
      }
    },

    async preloadAllConfigs() {
      for (const [configKey, config] of Object.entries(enhancedConfig)) {
        this.configCache[configKey] = config

      }

    },

    buildConfigGroups(treeData) {
      this.configGroups = treeData.map(group => ({
        label: group.label,
        options: group.children.map(child => ({
          key: child.key,
          name: child.label,
          category: group.label,
          description: child.description
        }))
      }))
    },

    async handleConfigChange(configKey) {
      if (!configKey) return

      // 更新选中的配置键
      this.selectedConfigKey = configKey

      try {
        if (this.configCache[configKey]) {
          this.currentConfig = this.configCache[configKey]
        } else if (enhancedConfig[configKey]) {
          this.currentConfig = enhancedConfig[configKey]
          this.configCache[configKey] = enhancedConfig[configKey]
        } else {
          const res = await fetchConfigDetail(configKey)
          if (res.data && res.data.config) {
            this.currentConfig = res.data.config
            this.configCache[configKey] = res.data.config
          } else {
            this.$message.warning('配置加载失败，请检查网络连接')
            return
          }
        }

        this.initConfigParams()

        // 只有在单配置模式下才清空指标选择，多配置模式下保留已选择的指标
        if (!this.hasMultiConfigMetrics()) {
          this.checkedMetricKeys = []
          // 清空之前的数据，避免列不匹配
          this.rawRows = []
          this.tableRows = []

          // 强制更新组件，确保列结构被重置
          this.$nextTick(() => {
            this.$forceUpdate()
            // 通知右侧面板更新表格
            this.$refs.rightPanel?.forceTableRender()

          })
        } else {
          // 多配置模式下，确保所有相关配置都已加载到缓存中
          this.ensureAllConfigsLoaded()

          // 强制更新组件，确保列结构被重新计算
          this.$nextTick(() => {
            this.$forceUpdate()
            // 通知右侧面板更新表格
            this.$refs.rightPanel?.forceTableRender()

            // 如果有原始数据，重新构建表格
            if (this.rawRows.length > 0) {
              this.buildTableData()
            }
          })
        }
      } catch (error) {
        this.$message.error('加载配置详情失败: ' + error.message)
      }
    },

    initConfigParams() {
      this.configParams = {}
      this.currentConfigParams.forEach(param => {
        if (param.default !== undefined) {
          this.configParams[param.key] = param.default
        } else if (param.options && param.options.length > 0) {
          this.configParams[param.key] = param.options[0].value
        }
      })
    },

    // 确保所有相关配置都已加载到缓存中
    ensureAllConfigsLoaded() {
      if (!this.selectedMetricKeys || this.selectedMetricKeys.length === 0) {
        return
      }

      // 收集所有需要的配置键
      const configKeys = new Set()
      this.selectedMetricKeys.forEach(key => {
        const parts = key.split(':')
        if (parts.length === 2) {
          configKeys.add(parts[0])
        }
      })

      // 确保所有配置都已加载到缓存中
      configKeys.forEach(configKey => {
        if (!this.configCache[configKey] && enhancedConfig[configKey]) {
          this.configCache[configKey] = enhancedConfig[configKey]
        }
      })
    },

    // 股票相关
    async loadStocks() {
      this.loadingStocks = true
      try {
        const res = await fetchStockList()
        const rawStocks = Array.isArray(res.data) ? res.data : []

        // 前端去重处理：按股票代码去重，保留第一个出现的记录
        const uniqueStocks = []
        const seenSymbols = new Set()

        for (const stock of rawStocks) {
          if (stock.symbol && !seenSymbols.has(stock.symbol)) {
            seenSymbols.add(stock.symbol)
            uniqueStocks.push(stock)
          }
        }

        this.stocks = uniqueStocks
      } catch (e) {
        this.$message.error('加载股票列表失败')
      } finally {
        this.loadingStocks = false
      }
    },

    handleSelectStock(symbol) {
      this.handleToggleStock(symbol)
    },

    handleToggleStock(symbol) {
      const index = this.selectedStocks.indexOf(symbol)
      if (index > -1) {
        // 移除股票
        this.selectedStocks.splice(index, 1)
        // 从表格中移除对应的行
        this.removeStockRow(symbol)
      } else {
        // 添加股票
        this.selectedStocks.push(symbol)
        // 在表格中添加对应的行
        this.addStockRow(symbol)
      }

      // 确保响应式更新
      this.$forceUpdate()
    },

    // 批量选择股票
    handleBatchSelectStocks(stockSymbols) {
      // 过滤掉已经选择的股票，避免重复
      const newStocks = stockSymbols.filter(symbol => !this.selectedStocks.includes(symbol))
      
      if (newStocks.length === 0) {
        this.$message.warning('所选概念板块的股票已在当前选择中')
        return
      }
      
      // 批量添加股票
      this.selectedStocks.push(...newStocks)
      
      // 批量添加股票行到表格
      newStocks.forEach(symbol => {
        this.addStockRow(symbol)
      })
      
      // 确保响应式更新
      this.$forceUpdate()
      
      this.$message.success(`已批量选择 ${newStocks.length} 只股票`)
    },

    // 添加股票行到表格
    addStockRow(symbol) {
      // 如果表格为空或没有原始数据，则不添加
      if (!this.rawRows.length || !this.selectedMetricKeys.length) {
        return
      }

      // 检查是否已存在该股票的行
      const existingRow = this.tableRows.find(row => row.symbol === symbol)
      if (existingRow) {
        return
      }

      // 从原始数据中查找该股票的数据
      const rawRow = this.rawRows.find(row => {
        const rowSymbol = this.extractSymbol(row)
        return rowSymbol === symbol
      })

      if (!rawRow) {
        // 创建一个空行
        const emptyRow = this.createEmptyStockRow(symbol)
        this.tableRows.push(emptyRow)
      } else {
        // 从原始数据创建表格行
        const newRow = this.createStockRowFromRawData(rawRow)
        if (newRow) {
          this.tableRows.push(newRow)
        }
      }

      this.$forceUpdate()
    },

    // 从表格中移除股票行
    removeStockRow(symbol) {
      const index = this.tableRows.findIndex(row => row.symbol === symbol)
      if (index > -1) {
        this.tableRows.splice(index, 1)
      }

      this.$forceUpdate()
    },

    // 创建空股票行
    createEmptyStockRow(symbol) {
      const stock = this.stocks.find(s => s.symbol === symbol)
      const stockName = stock ? stock.name : symbol

      const emptyRow = {
        symbol: symbol,
        name: stockName
      }

      // 为每个选中的指标字段添加空值
      this.selectedMetricColumns.forEach(col => {
        emptyRow[col.prop] = '-'
      })

      return emptyRow
    },

    // 从原始数据创建股票行
    createStockRowFromRawData(rawRow) {
      const symbol = this.extractSymbol(rawRow)
      const name = this.extractName(rawRow)

      if (symbol === '-' || name === '-') {
        return null
      }

      const tableRow = {
        symbol: symbol,
        name: name
      }

      // 为每个选中的指标字段添加数据
      this.selectedMetricColumns.forEach(col => {
        const field = col.prop
        const value = this.extractFieldValue(rawRow, field, col)
        tableRow[field] = value
      })

      return tableRow
    },

    // 同步表格行与选中股票列表
    syncTableRowsWithSelectedStocks() {
      if (!this.rawRows.length || !this.selectedMetricKeys.length) {
        return
      }

      // 获取当前表格中的所有股票代码
      const currentTableStocks = this.tableRows.map(row => row.symbol)

      // 找出需要添加的股票
      const stocksToAdd = this.selectedStocks.filter(stock => !currentTableStocks.includes(stock))

      // 找出需要移除的股票
      const stocksToRemove = currentTableStocks.filter(stock => !this.selectedStocks.includes(stock))

      // 移除不需要的股票行
      stocksToRemove.forEach(symbol => {
        this.removeStockRow(symbol)
      })

      // 添加需要的股票行
      stocksToAdd.forEach(symbol => {
        this.addStockRow(symbol)
      })
    },

    // 指标相关
    handleMetricCheck(checkedKeys) {
      // 直接更新checkedMetricKeys
      this.checkedMetricKeys = checkedKeys

      // 立即清空表格数据
      this.tableRows = []


      // 确保所有相关配置都已加载到缓存中
      this.ensureAllConfigsLoaded()
      // 自动处理配置切换：如果选择了不同配置的指标，自动切换配置
      // this.autoSwitchConfigIfNeeded(checkedKeys)

    },

    handleMetricFilter(value) {
      this.metricFilter = value
    },

    // 自动处理配置切换
    autoSwitchConfigIfNeeded(checkedKeys) {
      if (!checkedKeys || checkedKeys.length === 0) {
        return
      }

      // 检查是否选择了不同配置的指标
      const configKeys = new Set()
      checkedKeys.forEach(key => {
        const parts = key.split(':')
        if (parts.length === 2) {
          configKeys.add(parts[0])
        }
      })


      // 如果只有一个配置，且与当前配置不同，自动切换
      if (configKeys.size === 1) {
        const targetConfigKey = Array.from(configKeys)[0]
        if (targetConfigKey !== this.selectedConfigKey) {
          // 显示提示信息
          const targetConfig = this.configCache[targetConfigKey] || enhancedConfig[targetConfigKey]
          if (targetConfig) {
            this.$message.info(`已自动切换到 ${targetConfig.name} 配置`)
          }

          // 自动切换配置
          this.$nextTick(() => {
            this.handleConfigChange(targetConfigKey)
          })

        }
      } else if (configKeys.size > 1) {
        // 多配置模式，不需要切换，配置加载已在handleMetricCheck中处理
        // 这里不需要重复处理，因为ensureAllConfigsLoaded()已经处理了
      }

    },

    // 数据提取 - 统一入口
    async extractData() {
      if (!this.canExtractData) {
        this.$message.warning('请完善必要参数：选择股票、指标类型和具体指标')
        return
      }

      this.loadingData = true
      try {
        // 统一的数据提取逻辑
        await this.extractUnifiedData()
      } catch (error) {
        if (error.response && error.response.data && error.response.data.data && error.response.data.data.missing_params) {
          const missingParams = error.response.data.data.missing_params
          this.$message.error(`缺少必填参数: ${missingParams.map(p => p.title).join(', ')}`)
          this.paramConfigDialogVisible = true
        } else {
          this.$message.error('提取数据失败: ' + error.message)
        }
      } finally {
        this.loadingData = false
      }
    },

    // 检查是否选择了跨配置的指标
    hasMultiConfigMetrics() {
      if (!this.selectedMetricKeys || this.selectedMetricKeys.length === 0) {
        return false
      }

      const configKeys = new Set()
      this.selectedMetricKeys.forEach(key => {
        const parts = key.split(':')
        if (parts.length === 2) {
          configKeys.add(parts[0])
        }
      })


      return configKeys.size > 1
    },

    // 统一的数据提取方法
    async extractUnifiedData() {
      // 检查是否选择了跨配置的指标
      const hasMultiConfigMetrics = this.hasMultiConfigMetrics()

      if (hasMultiConfigMetrics) {
        // 多配置数据提取
        await this.extractMultiConfigData()
      } else {
        // 单配置数据提取
        await this.extractSingleConfigData()
      }
    },

    // 统一的数据处理方法
    async processExtractedData(rawData, mode, configCount = 1) {
      // 清理缓存，确保每次提取都使用新的缓存
      this.clearStockExtractionCache()

      // 数据清理和验证
      this.rawRows = this.cleanRawData(rawData)

      // 构建表格数据
      this.buildTableData()

      // 同步表格行与选中股票列表
      this.syncTableRowsWithSelectedStocks()

      // 显示成功消息
      if (mode === '多配置') {
        this.$message.success(`成功提取 ${this.rawRows.length} 条数据（来自 ${configCount} 个配置）`)
      } else {
        this.$message.success(`成功提取 ${this.rawRows.length} 条数据`)
      }
    },

    // 单配置数据提取（原有逻辑）
    async extractSingleConfigData() {
        const params = { ...this.configParams }

        // 验证参数
        try {
          const validationRes = await validateParams(this.selectedConfigKey, params)
          if (validationRes.data && !validationRes.data.valid) {
            const missingParams = validationRes.data.missing_params || []
            this.$message.error(`缺少必填参数: ${missingParams.map(p => p.title).join(', ')}`)
            this.paramConfigDialogVisible = true
            return
          }
        } catch (validationError) {
          // 参数验证失败，继续执行
        }

        const res = await fetchDynamicDataWithFilter(this.selectedConfigKey, params, this.selectedStocks)
        if (res.data) {
          // 使用统一的数据处理方法
          await this.processExtractedData(res.data, '单配置')
        }
    },

    // 多配置数据提取
    async extractMultiConfigData() {
      // 按配置分组指标
      const configGroups = this.groupMetricsByConfig()

      // 构建配置请求
      const configRequests = []
      for (const [configKey, metrics] of Object.entries(configGroups)) {
        const config = this.configCache[configKey]
        if (!config) {
          continue
        }

        // 获取该配置的参数
        const params = this.getConfigParams(configKey)

        configRequests.push({
          key: configKey,
          params: params,
          metrics: metrics
        })
      }


      if (configRequests.length === 0) {
        this.$message.warning('没有有效的配置请求')
        return
      }

      // 调用多配置API
      const res = await fetchMultiConfigData(configRequests, this.selectedStocks)

      if (res.data && res.data.all_rows) {
        if (res.data.results) {
          res.data.results.forEach(result => {
            if (result.error) {
              // 配置出错，已记录
            }
          })
        }

        // 使用统一的数据处理方法
        await this.processExtractedData(res.data.all_rows, '多配置', res.data.config_count)
      }
    },

    // 按配置分组指标
    groupMetricsByConfig() {
      const groups = {}

      this.selectedMetricKeys.forEach(key => {
        const parts = key.split(':')
        if (parts.length === 2) {
          const [configKey, field] = parts
          if (!groups[configKey]) {
            groups[configKey] = []
          }
          groups[configKey].push(field)
        }
      })


      return groups
    },

    // 多配置数据去重，按股票代码+配置组合去重
    deduplicateMultiConfigData(data) {
      const seen = new Set()
      const deduplicated = []

      data.forEach(row => {
        const symbol = this.extractSymbol(row)
        const configKey = row._config_key || 'unknown'

        // 创建唯一键：股票代码+配置
        const uniqueKey = `${symbol}_${configKey}`

        if (!seen.has(uniqueKey)) {
          seen.add(uniqueKey)
          deduplicated.push(row)
        }
      })

      return deduplicated
    },

    // 获取指定配置的参数
    getConfigParams(configKey) {
      // 如果当前选中的配置就是目标配置，使用当前参数
      if (configKey === this.selectedConfigKey) {
        return { ...this.configParams }
      }

      // 否则使用默认参数
      const config = this.configCache[configKey]
      if (!config || !config.akshare || !config.akshare.params) {
        return {}
      }

      const params = {}
      Object.keys(config.akshare.params).forEach(key => {
        const param = config.akshare.params[key]
        if (param.default !== undefined) {
          params[key] = param.default
        } else if (param.options && param.options.length > 0) {
          // 对于日期参数，优先选择最新的日期
          if (key === 'date' && param.options.length > 1) {
            params[key] = param.options[param.options.length - 1].value
          } else {
            params[key] = param.options[0].value
          }
        }
      })

      return params
    },

    // 统一的列定义方法
    getUnifiedColumns() {
      // 检查是否为多配置模式
      const isMultiConfig = this.hasMultiConfigMetrics()


      // 如果没有选择任何指标，返回空列定义
      if (!this.selectedMetricKeys || this.selectedMetricKeys.length === 0) {
        return [
          { prop: 'symbol', label: '股票代码', width: 100 },
          { prop: 'name', label: '股票名称', width: 120 }
        ]
      }

      if (isMultiConfig) {
        // 多配置模式：使用配置分组逻辑
        return this.getMultiConfigColumns()
      } else {
        // 单配置模式：使用简化的列定义
        return this.getSingleConfigColumns()
      }
    },

    // 单配置列定义
    getSingleConfigColumns() {
      const columns = []

      // 添加基础列
      columns.push(
        { prop: 'symbol', label: '股票代码', width: 100 },
        { prop: 'name', label: '股票名称', width: 120 }
      )


      // 添加指标列
      this.selectedMetricKeys.forEach((key) => {
        const parts = key.split(':')
        if (parts.length === 2) {
          const [configKey, field] = parts


          // 优先使用当前配置，如果配置键不匹配则使用缓存中的配置
          let config = null
          if (configKey === this.selectedConfigKey && this.currentConfig) {
            config = this.currentConfig
          } else if (this.configCache[configKey]) {
            config = this.configCache[configKey]
          } else {
            // 如果缓存中也没有，尝试从enhancedConfig中获取
            config = enhancedConfig[configKey]
            if (config) {
              this.configCache[configKey] = config
            }
          }

          // 如果仍然没有找到配置，尝试从所有可用的配置中查找
          if (!config) {
            for (const [cachedKey, cachedConfig] of Object.entries(this.configCache)) {
              if (cachedKey === configKey) {
                config = cachedConfig
                break
              }
            }
          }

          if (config && config.ui && config.ui.columns) {
            const col = config.ui.columns.find(c => c.field === field)
            if (col) {
              columns.push({
                prop: `${configKey}:${field}`,
                label: col.label,
                width: col.width,
                align: col.align,
                configKey: configKey,
                originalField: field
              })

            }
          }
        }
      })


      return columns
    },

    // 多配置列定义
    getMultiConfigColumns() {
      const columns = []

      // 按配置分组处理指标
      const configGroups = this.groupMetricsByConfig()

      // 判断是否为多配置
      const isMultiConfig = Object.keys(configGroups).length > 1


      // 添加基础列
      columns.push(
        { prop: 'symbol', label: '股票代码', width: 100 },
        { prop: 'name', label: '股票名称', width: 120 }
      )

      // 多配置模式下不添加数据来源列，通过列名显示配置来源即可

      for (const [configKey, fields] of Object.entries(configGroups)) {
        const config = this.configCache[configKey]
        if (!config || !config.ui || !config.ui.columns) continue

        // 添加该配置的指标列，在列名中包含配置信息
        config.ui.columns.forEach(col => {
          // 只添加选中的字段，并且排除基础字段
          if (fields.includes(col.field) && !['symbol', 'name', 'date', 'index'].includes(col.field)) {
            // 如果是多配置，在列名中显示配置来源，并确保字段名唯一
            const label = isMultiConfig
              ? `${col.label || col.field} (${config.name || configKey})`
              : (col.label || col.field)

            // 多配置模式下，使用配置前缀确保字段名唯一
            const uniqueProp = `${configKey}:${col.field}`

            columns.push({
              prop: uniqueProp,
              label: label,
              width: col.width || 120,
              align: col.align || 'left',
              configKey: configKey,
              originalField: col.field  // 保存原始字段名用于数据提取
            })
          }
        })
      }

      return columns
    },

    // 合并多配置表格数据，按股票代码合并
    mergeMultiConfigTableData(processedRows) {
      const mergedData = {}

      // 按股票代码分组
      processedRows.forEach((row, index) => {
        const symbol = row.symbol
        const configKey = row._config_key || 'unknown'

        if (!mergedData[symbol]) {
          mergedData[symbol] = {
            symbol: row.symbol,
            name: row.name,
            _configs: new Set(), // 记录该股票来自哪些配置
            _field_sources: {} // 记录每个字段来自哪个配置
          }
        }

        // 记录配置来源
        if (row._config_key) {
          mergedData[symbol]._configs.add(row._config_key)
        }

        // 合并该配置的字段数据，避免字段覆盖
        Object.keys(row).forEach(key => {
          if (!['symbol', 'name', '_config_key', '_config_name'].includes(key)) {
            // 检查字段是否已存在
            if (mergedData[symbol][key] !== undefined) {
              // 如果字段已存在，检查是否来自不同配置
              const existingSource = mergedData[symbol]._field_sources[key]
              if (existingSource && existingSource !== configKey) {
                // 字段冲突：来自不同配置的同名字段
                // 保留带配置前缀的字段名
                const prefixedKey = `${configKey}_${key}`
                mergedData[symbol][prefixedKey] = row[key]
                mergedData[symbol]._field_sources[prefixedKey] = configKey
              } else {
                // 同一配置的字段，直接更新
                mergedData[symbol][key] = row[key]
                mergedData[symbol]._field_sources[key] = configKey
              }
            } else {
              // 新字段，直接添加
              mergedData[symbol][key] = row[key]
              mergedData[symbol]._field_sources[key] = configKey
            }
          }
        })
      })

      // 转换为数组并添加配置来源信息
      return Object.values(mergedData).map(row => {
        // 添加配置来源信息到行数据中
        row._configs = Array.from(row._configs)
        return row
      })
    },

    buildTableData() {
      // 清空之前的数据，确保重新构建
      this.tableRows = []

      if (this.debugStockExtraction) {
        console.log('=== buildTableData 开始 ===')
        console.log('原始数据行数:', this.rawRows.length)
        console.log('选中的指标键数量:', this.selectedMetricKeys.length)
      }

      if (!this.rawRows.length || !this.selectedMetricKeys.length) {
        if (this.debugStockExtraction) {
          console.log('数据不足，跳过构建表格')
        }
        return
      }

      // 获取有效的列定义（支持多配置）
      const validColumns = this.selectedMetricColumns

      if (this.debugStockExtraction) {
        console.log('有效列定义:', validColumns)
      }

      // 过滤空行和无效数据
      const validRows = this.rawRows.filter(row => {
        const hasValidData = Object.values(row).some(value =>
          value !== null && value !== undefined && value !== '' && String(value).trim() !== ''
        )
        return hasValidData
      })

      // 确保所有行都有相同的列结构
      const processedRows = validRows.map((row) => {
        const symbol = this.extractSymbol(row)
        const name = this.extractName(row)

        // 如果股票代码或名称为空，跳过这行
        if (symbol === '-' || name === '-') {
          return null
        }

        // 构建标准化的表格行
        const tableRow = {
          symbol: symbol,
          name: name
        }

        // 添加配置标识信息
        if (row._config_key) {
          tableRow._config_key = row._config_key
          tableRow._config_name = row._config_name
        }

        // 为每个选中的指标字段添加数据，确保列结构一致
        validColumns.forEach(col => {
          const field = col.prop
          // 多配置模式下，仅为与当前行配置匹配的列赋值，避免用 '-' 占位造成合并冲突
          if (this.hasMultiConfigMetrics() && col.configKey && row._config_key && col.configKey !== row._config_key) {
            return
          }
          const value = this.extractFieldValue(row, field, col)
          tableRow[field] = value
        })

        return tableRow
      }).filter(row => row !== null) // 过滤掉null值

      // 多配置模式下，需要按股票代码合并数据
      if (this.hasMultiConfigMetrics()) {
        this.tableRows = this.mergeMultiConfigTableData(processedRows)
      } else {
        this.tableRows = processedRows
      }

      if (this.debugStockExtraction) {
        console.log('=== buildTableData 完成 ===')
        console.log('处理后的行数:', processedRows.length)
        console.log('最终表格行数:', this.tableRows.length)
        if (this.tableRows.length > 0) {
          console.log('第一行表格数据:', this.tableRows[0])
        }
      }

      // 数据一致性检查
      this.validateTableConsistency()

      // 强制更新表格组件
      this.$forceUpdate()
    },

    // 验证表格数据一致性
    validateTableConsistency() {
      if (this.tableRows.length === 0) return

      const firstRowKeys = Object.keys(this.tableRows[0])
      const expectedKeys = ['symbol', 'name', ...this.selectedMetricColumns.map(col => col.prop)]

      // 检查列结构是否一致
      const hasInconsistentRows = this.tableRows.some(row => {
        const rowKeys = Object.keys(row)
        return !this.arraysEqual(firstRowKeys.sort(), rowKeys.sort())
      })

      if (hasInconsistentRows) {
        // 表格行结构不一致
      }
    },

    // 比较两个数组是否相等
    arraysEqual(a, b) {
      return a.length === b.length && a.every((val, index) => val === b[index])
    },


    // 提取股票代码
    extractSymbol(row) {
      // 生成缓存键（基于行的关键字段）
      const cacheKey = this.generateRowCacheKey(row, 'symbol')

      // 检查缓存
      if (this.stockExtractionCache.has(cacheKey)) {
        const cached = this.stockExtractionCache.get(cacheKey)
        if (this.debugStockExtraction) {
          console.log(`使用缓存的股票代码: ${cached}`)
        }
        return cached
      }

      // 调试模式：只在需要时输出调试信息
      const debugMode = this.debugStockExtraction

      if (debugMode) {
        console.log('调试股票代码提取:')
        console.log('行数据键:', Object.keys(row))
        console.log('行数据:', row)

        // 输出所有字段的值，帮助调试
        console.log('所有字段值:')
        Object.keys(row).forEach(key => {
          console.log(`${key}:`, row[key])
        })
      }

      // 尝试多种可能的股票代码字段名
      const symbolFields = [
        'symbol', '股票代码', '代码', 'stock_code', 'ts_code', 'code',
        '证券代码', '股票标识', 'ticker'
      ]

      // 首先尝试直接字段名（后端现在会保留这些字段的原始名称）
      for (const field of symbolFields) {
        if (row[field] !== undefined && row[field] !== null && row[field] !== '') {
          const value = String(row[field]).trim()
          if (debugMode) {
            console.log(`尝试字段 ${field}:`, value, '是否有效:', this.isValidStockCode(value))
          }
          if (value && this.isValidStockCode(value)) {
            if (debugMode) {
              console.log(`找到股票代码: ${value}`)
            }
            // 缓存结果
            this.stockExtractionCache.set(cacheKey, value)
            return value
          }
        }
      }

      // 多配置模式下，尝试带配置前缀的字段名
      for (const field of symbolFields) {
        // 查找所有以该字段名结尾的键
        const matchingKeys = Object.keys(row).filter(key => key.endsWith(`_${field}`))
        if (debugMode) {
          console.log(`查找前缀字段 ${field}:`, matchingKeys)
        }
        for (const key of matchingKeys) {
          if (row[key] !== undefined && row[key] !== null && row[key] !== '') {
            const value = String(row[key]).trim()
            if (debugMode) {
              console.log(`尝试前缀字段 ${key}:`, value, '是否有效:', this.isValidStockCode(value))
            }
            if (value && this.isValidStockCode(value)) {
              if (debugMode) {
                console.log(`找到股票代码: ${value}`)
              }
              // 缓存结果
              this.stockExtractionCache.set(cacheKey, value)
              return value
            }
          }
        }
      }

      if (debugMode) {
        console.log('未找到股票代码，返回默认值 -')
      }
      // 缓存默认值
      this.stockExtractionCache.set(cacheKey, '-')
      return '-'
    },

    // 验证股票代码格式
    isValidStockCode(code) {
      // 检查是否为6位数字
      if (!/^\d{6}$/.test(code)) {
        return false
      }

      // 检查股票代码是否在可用的股票列表中
      if (this.stocks && this.stocks.length > 0) {
        return this.stocks.some(stock => stock.symbol === code)
      }

      return true
    },

    // 提取股票名称
    extractName(row) {
      // 生成缓存键（基于行的关键字段）
      const cacheKey = this.generateRowCacheKey(row, 'name')

      // 检查缓存
      if (this.stockExtractionCache.has(cacheKey)) {
        const cached = this.stockExtractionCache.get(cacheKey)
        if (this.debugStockExtraction) {
          console.log(`使用缓存的股票名称: ${cached}`)
        }
        return cached
      }

      // 调试模式：只在需要时输出调试信息
      const debugMode = this.debugStockExtraction

      if (debugMode) {
        console.log('调试股票名称提取:')
        console.log('行数据键:', Object.keys(row))
        console.log('行数据:', row)
      }

      // 尝试多种可能的股票名称字段名
      const nameFields = [
        'name', '股票简称', '名称', 'stock_name', '股票名称', 'company_name',
        '证券简称', '股票全称', '公司名称'
      ]

      // 首先尝试直接字段名（后端现在会保留这些字段的原始名称）
      for (const field of nameFields) {
        if (row[field] !== undefined && row[field] !== null && row[field] !== '') {
          const value = String(row[field]).trim()
          if (debugMode) {
            console.log(`尝试字段 ${field}:`, value)
          }
          if (value) {
            if (debugMode) {
              console.log(`找到股票名称: ${value}`)
            }
            // 缓存结果
            this.stockExtractionCache.set(cacheKey, value)
            return value
          }
        }
      }

      // 多配置模式下，尝试带配置前缀的字段名
      for (const field of nameFields) {
        // 查找所有以该字段名结尾的键
        const matchingKeys = Object.keys(row).filter(key => key.endsWith(`_${field}`))
        if (debugMode) {
          console.log(`查找前缀字段 ${field}:`, matchingKeys)
        }
        for (const key of matchingKeys) {
          if (row[key] !== undefined && row[key] !== null && row[key] !== '') {
            const value = String(row[key]).trim()
            if (debugMode) {
              console.log(`尝试前缀字段 ${key}:`, value)
            }
            if (value) {
              if (debugMode) {
                console.log(`找到股票名称: ${value}`)
              }
              // 缓存结果
              this.stockExtractionCache.set(cacheKey, value)
              return value
            }
          }
        }
      }

      if (debugMode) {
        console.log('未找到股票名称，返回默认值 -')
      }
      // 缓存默认值
      this.stockExtractionCache.set(cacheKey, '-')
      return '-'
    },

    // 生成行缓存键
    generateRowCacheKey(row, type) {
      // 使用行的关键字段生成缓存键
      const keyFields = ['symbol', '股票代码', 'name', '股票简称', '序号', '_config_key']
      const keyValues = keyFields.map(field => row[field] || '').join('|')
      return `${type}_${keyValues}`
    },

    // 清理缓存
    clearStockExtractionCache() {
      this.stockExtractionCache.clear()
    },

    // 统一的字段值提取方法 - 只使用精确匹配
    extractFieldValue(row, field, col) {
      // 构建精确匹配的字段名列表
      const exactFields = this.buildExactFieldNames(field, col)

      // 调试信息：输出字段名和行数据
      const debugMode = this.debugStockExtraction
      if (debugMode) {
        console.log('调试字段值提取:')
        console.log('目标字段:', field)
        console.log('尝试的字段名列表:', exactFields)
        console.log('行数据键:', Object.keys(row))
        console.log('列配置:', col)
      }

      // 按优先级尝试精确匹配字段值
      for (const fieldName of exactFields) {
        if (row.hasOwnProperty(fieldName) && row[fieldName] !== undefined && row[fieldName] !== null && row[fieldName] !== '') {
          const value = row[fieldName]
          const formattedValue = this.formatCellValue(value, col)
          if (debugMode) {
            console.log(`找到字段 ${fieldName}:`, value, '格式化后:', formattedValue)
          }
          return formattedValue
        }
      }

      // 精确匹配失败，返回默认值
      if (debugMode) {
        console.log(`未找到字段 ${field}，返回默认值 -`)
      }
      return '-'
    },

    // 构建精确匹配的字段名列表 - 优化版本
    buildExactFieldNames(field, col) {
      // 使用Set避免重复，提高性能
      const exactFields = new Set()

      // 1. 多配置模式：使用带配置前缀的字段名（后端标准格式）
      if (this.hasMultiConfigMetrics() && col.configKey && col.originalField) {
        exactFields.add(`${col.configKey}_${col.originalField}`)
      }

      // 2. 直接字段名（英文字段名，后端已标准化）
      exactFields.add(field)

      // 3. 原始字段名（如果存在且与当前字段不同）
      if (col.originalField && col.originalField !== field) {
        exactFields.add(col.originalField)
      }

      // 4. 单配置模式下的直接字段名
      if (!this.hasMultiConfigMetrics()) {
        exactFields.add(field)
        if (col.originalField) {
          exactFields.add(col.originalField)
        }
      }

      // 转换为数组并过滤空值
      return Array.from(exactFields).filter(Boolean)
    },



    // 清理原始数据
    cleanRawData(rawData) {
      if (!Array.isArray(rawData)) {
        return []
      }

      const cleanedData = rawData.map(row => {
        const cleanedRow = {}

        // 清理所有字段，去除空格和null值
        for (const [key, value] of Object.entries(row)) {
          if (value !== null && value !== undefined) {
            // 如果是字符串，去除前后空格
            if (typeof value === 'string') {
              const trimmed = value.trim()
              cleanedRow[key] = trimmed === '' ? null : trimmed
            } else {
              cleanedRow[key] = value
            }
          } else {
            cleanedRow[key] = null
          }
        }

        return cleanedRow
      })

      // 过滤掉完全空的记录
      const filteredData = cleanedData.filter(row => {
        // 检查是否有任何非空值
        return Object.values(row).some(value =>
          value !== null && value !== undefined && value !== ''
        )
      })

      return filteredData
    },

    // 格式化单元格值
    formatCellValue(value, col) {
      if (value === null || value === undefined || value === '') {
        return '-'
      }

      // 数值类型格式化
      if (typeof value === 'number') {
        if (col.align === 'right' || col.prop.includes('price') || col.prop.includes('amount')) {
          return value.toFixed(2)
        }
        if (col.prop.includes('pct') || col.prop.includes('ratio')) {
          return (value * 100).toFixed(2) + '%'
        }
        return value.toString()
      }

      return String(value)
    },

    // 导出
    exportTable() {
      if (!this.tableRows.length) return

      const headers = ['股票代码', '股票名称', ...this.selectedMetricColumns.map(c => c.label)]
      const rows = this.tableRows.map(r => [
        r.symbol,
        r.name,
        ...this.selectedMetricColumns.map(c => r[c.prop])
      ])

      const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
      const blob = new Blob(["\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `EDE_${this.selectedConfigKey}_${new Date().toISOString().slice(0,10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    },

    // 参数配置
    handleParamConfig() {
      this.paramConfigDialogVisible = true
    },

    handleParamConfigConfirm(data) {
      this.configParams = { ...this.configParams, ...data.params }
      this.$message.success('参数配置完成')
      this.paramConfigDialogVisible = false
    },

    handleParamConfigClose() {
      this.paramConfigDialogVisible = false
    },

    checkParamsValid() {
      if (!this.currentConfig || !this.currentConfigParams) {
        return true
      }
      return this.currentConfigParams.every(param => {
        if (param.required) {
          return this.configParams[param.key] !== undefined &&
                 this.configParams[param.key] !== ''
        }
        return true
      })
    },

    // 视图模式
    handleViewModeChange(mode) {
      this.viewMode = mode
    },

    handleDebugToggle(value) {
      this.debugStockExtraction = value
      if (value) {
        this.$message.info('已开启调试模式，控制台将显示详细的股票代码提取日志')
        // 临时调试：输出当前状态
        console.log('=== 调试模式开启 ===')
        console.log('原始数据行数:', this.rawRows.length)
        console.log('表格数据行数:', this.tableRows.length)
        console.log('选中的指标键:', this.selectedMetricKeys)
        console.log('生成的列配置:', this.selectedMetricColumns)
        if (this.rawRows.length > 0) {
          console.log('第一行原始数据:', this.rawRows[0])
        }
        if (this.tableRows.length > 0) {
          console.log('第一行表格数据:', this.tableRows[0])
        }
      } else {
        this.$message.info('已关闭调试模式')
      }
    },

    // 面板调整
    handleLeftResize(width) {
      this.leftWidth = width
      this.rightWidth = document.body.clientWidth - this.leftWidth - this.middleWidth - 16
    },

    handleMiddleResize(width) {
      this.middleWidth = width
      this.rightWidth = document.body.clientWidth - this.leftWidth - this.middleWidth - 16
    },

    handleRightResize(width) {
      this.rightWidth = width
    },

    // 拖拽相关
    startDrag(which) {
      this.dragging = which
      this.startX = event.clientX
      this.startLeft = this.leftWidth
      this.startMiddle = this.middleWidth
    },

    onDrag(event) {
      if (!this.dragging) return
      const dx = event.clientX - this.startX
      if (this.dragging === 'left') {
        this.leftWidth = Math.max(200, this.startLeft + dx)
      } else if (this.dragging === 'middle') {
        this.middleWidth = Math.max(250, this.startMiddle + dx)
      }
      this.rightWidth = document.body.clientWidth - this.leftWidth - this.middleWidth - 16
    },

    stopDrag() {
      this.dragging = null
    },

    onResize() {
      this.rightWidth = document.body.clientWidth - this.leftWidth - this.middleWidth - 16
    }
  }
}
</script>

<style scoped>
.ede-optimized-container {
  padding: 10px;
  background: #f5f7fa;
}

.ede-panels {
  display: flex;
  user-select: none;
  height: calc(100vh - 120px);
}

.ede-resizer {
  width: 6px;
  cursor: col-resize;
  background: #f0f0f0;
  margin: 0 8px;
  border-radius: 3px;
}

.ede-resizer:hover {
  background: #409eff;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .ede-left { width: 240px !important; }
  .ede-middle { width: 280px !important; }
}

@media (max-width: 992px) {
  .ede-panels {
    flex-direction: column;
    height: auto;
  }

  .ede-left, .ede-middle, .ede-right {
    width: 100% !important;
    height: auto;
    margin-bottom: 16px;
  }

  .ede-resizer {
    display: none;
  }
}
</style>
