/**
 * EDE模块状态管理
 * 使用Vuex进行状态管理，优化组件间数据共享
 */

import { fetchStockList, fetchMetricTree, fetchDynamicDataWithFilter, fetchConfigDetail, validateParams, fetchAvailableConfigs } from '@/api/stock/ede'
import enhancedConfig, { METRIC_CATEGORIES } from '../enhanced-config'

const state = {
  // 面板状态
  leftWidth: 280,
  middleWidth: 320,
  rightWidth: 0,

  // 股票相关
  stocks: [],
  selectedStocks: [],
  loadingStocks: false,
  stockFilter: '',

  // 配置相关
  configGroups: [],
  selectedConfigKey: '',
  currentConfig: null,
  configParams: {},
  configCache: {},

  // 指标相关
  metricTree: [],
  checkedMetricKeys: [],
  metricFilter: '',

  // 数据相关
  viewMode: 'table',
  loadingData: false,
  rawRows: [],
  tableRows: [],

  // UI状态
  paramConfigDialogVisible: false
}

const mutations = {
  // 面板调整
  SET_LEFT_WIDTH(state, width) {
    state.leftWidth = width
  },

  SET_MIDDLE_WIDTH(state, width) {
    state.middleWidth = width
  },

  SET_RIGHT_WIDTH(state, width) {
    state.rightWidth = width
  },

  // 股票相关
  SET_STOCKS(state, stocks) {
    state.stocks = stocks
  },

  SET_SELECTED_STOCKS(state, stocks) {
    state.selectedStocks = stocks
  },

  ADD_SELECTED_STOCK(state, symbol) {
    if (!state.selectedStocks.includes(symbol)) {
      state.selectedStocks.push(symbol)
    }
  },

  REMOVE_SELECTED_STOCK(state, symbol) {
    const index = state.selectedStocks.indexOf(symbol)
    if (index > -1) {
      state.selectedStocks.splice(index, 1)
    }
  },

  SET_LOADING_STOCKS(state, loading) {
    state.loadingStocks = loading
  },

  SET_STOCK_FILTER(state, filter) {
    state.stockFilter = filter
  },

  // 配置相关
  SET_CONFIG_GROUPS(state, groups) {
    state.configGroups = groups
  },

  SET_SELECTED_CONFIG_KEY(state, key) {
    state.selectedConfigKey = key
  },

  SET_CURRENT_CONFIG(state, config) {
    state.currentConfig = config
  },

  SET_CONFIG_PARAMS(state, params) {
    state.configParams = params
  },

  UPDATE_CONFIG_PARAM(state, { key, value }) {
    state.configParams[key] = value
  },

  SET_CONFIG_CACHE(state, { key, config }) {
    state.configCache[key] = config
  },

  // 指标相关
  SET_METRIC_TREE(state, tree) {
    state.metricTree = tree
  },

  SET_CHECKED_METRIC_KEYS(state, keys) {
    state.checkedMetricKeys = keys
  },

  SET_METRIC_FILTER(state, filter) {
    state.metricFilter = filter
  },

  // 数据相关
  SET_VIEW_MODE(state, mode) {
    state.viewMode = mode
  },

  SET_LOADING_DATA(state, loading) {
    state.loadingData = loading
  },

  SET_RAW_ROWS(state, rows) {
    state.rawRows = rows
  },

  SET_TABLE_ROWS(state, rows) {
    state.tableRows = rows
  },

  // UI状态
  SET_PARAM_CONFIG_DIALOG_VISIBLE(state, visible) {
    state.paramConfigDialogVisible = visible
  }
}

const getters = {
  // 计算属性
  filteredStocks: (state) => {
    const q = state.stockFilter.trim().toLowerCase()
    let filtered = state.stocks

    if (q) {
      filtered = state.stocks.filter(s =>
        s.symbol.toLowerCase().includes(q) ||
        (s.name && s.name.toLowerCase().includes(q))
      )
    }

    // 按股票代码排序
    return filtered.sort((a, b) => {
      const aNum = parseInt(a.symbol.replace(/\D/g, '')) || 0
      const bNum = parseInt(b.symbol.replace(/\D/g, '')) || 0
      return aNum - bNum
    })
  },

  selectedMetricKeys: (state) => {
    return Array.isArray(state.checkedMetricKeys) ? state.checkedMetricKeys : []
  },

  selectedMetricColumns: (state) => {
    const columns = []
    state.selectedMetricKeys.forEach((key) => {
      const parts = key.split(':')
      if (parts.length === 2) {
        const [configKey, field] = parts
        const config = state.configCache[configKey]
        if (config && config.ui && config.ui.columns) {
          const col = config.ui.columns.find(c => c.field === field)
          if (col) {
            columns.push({
              prop: field,
              label: col.label,
              width: col.width,
              align: col.align
            })
          }
        }
      }
    })
    return columns
  },

  currentConfigParams: (state) => {
    if (!state.currentConfig || !state.currentConfig.akshare) return []
    const params = state.currentConfig.akshare.params || {}
    return Object.keys(params).map(key => ({
      key,
      ...params[key]
    }))
  },

  canExtractData: (state, getters) => {
    return state.selectedStocks.length > 0 &&
           state.selectedConfigKey &&
           state.selectedMetricKeys.length > 0 &&
           getters.checkParamsValid
  },

  checkParamsValid: (state, getters) => {
    if (!state.currentConfig || !getters.currentConfigParams) {
      return true
    }
    return getters.currentConfigParams.every(param => {
      if (param.required) {
        return state.configParams[param.key] !== undefined &&
               state.configParams[param.key] !== ''
      }
      return true
    })
  }
}

const actions = {
  // 初始化
  async initEDE({ dispatch }) {
    await Promise.all([
      dispatch('loadStocks'),
      dispatch('loadConfigs')
    ])
  },

  // 股票相关
  async loadStocks({ commit, state }) {
    commit('SET_LOADING_STOCKS', true)
    try {
      const res = await fetchStockList()
      const stocks = Array.isArray(res.data) ? res.data : []
      commit('SET_STOCKS', stocks)
    } catch (e) {
      console.error('加载股票列表失败:', e)
    } finally {
      commit('SET_LOADING_STOCKS', false)
    }
  },

  toggleStock({ commit, state }, symbol) {
    if (state.selectedStocks.includes(symbol)) {
      commit('REMOVE_SELECTED_STOCK', symbol)
    } else {
      commit('ADD_SELECTED_STOCK', symbol)
    }
  },

  // 配置相关
  async loadConfigs({ commit, dispatch }) {
    try {
      // 优先从后端API获取配置
      try {
        const res = await fetchMetricTree()
        if (res.data && res.data.tree) {
          commit('SET_METRIC_TREE', res.data.tree)
          dispatch('buildConfigGroups', res.data.tree)
          await dispatch('loadConfigsFromBackend')

          if (res.data.tree.length > 0 && res.data.tree[0].children.length > 0) {
            const firstConfig = res.data.tree[0].children[0]
            commit('SET_SELECTED_CONFIG_KEY', firstConfig.key)
            await dispatch('handleConfigChange', firstConfig.key)
          }
          return
        }
      } catch (apiError) {
        console.warn('后端API调用失败，使用本地配置作为备用:', apiError)
      }

      // 备用方案：使用本地配置
      const localTree = dispatch('buildMetricTreeFromConfig')
      commit('SET_METRIC_TREE', localTree)
      dispatch('buildConfigGroups', localTree)
      await dispatch('preloadAllConfigs')

      if (localTree.length > 0 && localTree[0].children.length > 0) {
        const firstConfig = localTree[0].children[0]
        commit('SET_SELECTED_CONFIG_KEY', firstConfig.key)
        await dispatch('handleConfigChange', firstConfig.key)
      }
    } catch (error) {
      console.error('加载配置失败:', error)
    }
  },

  buildMetricTreeFromConfig({ commit }) {
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
        if (!config) continue

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

  async loadConfigsFromBackend({ commit }) {
    try {
      const configsRes = await fetchAvailableConfigs()
      if (configsRes.data && configsRes.data.configs) {
        const configs = configsRes.data.configs
        for (const config of configs) {
          try {
            const detailRes = await fetchConfigDetail(config.key)
            if (detailRes.data && detailRes.data.config) {
              commit('SET_CONFIG_CACHE', { key: config.key, config: detailRes.data.config })
            }
          } catch (error) {
            console.warn(`获取配置详情失败: ${config.key}`, error)
          }
        }
      }
    } catch (error) {
      console.error('从后端加载配置详情失败:', error)
    }
  },

  async preloadAllConfigs({ commit }) {
    for (const [configKey, config] of Object.entries(enhancedConfig)) {
      commit('SET_CONFIG_CACHE', { key: configKey, config: config })
    }
  },

  buildConfigGroups({ commit }, treeData) {
    const groups = treeData.map(group => ({
      label: group.label,
      options: group.children.map(child => ({
        key: child.key,
        name: child.label,
        category: group.label,
        description: child.description
      }))
    }))
    commit('SET_CONFIG_GROUPS', groups)
  },

  async handleConfigChange({ commit, state }, configKey) {
    if (!configKey) return

    try {
      let config = null
      if (state.configCache[configKey]) {
        config = state.configCache[configKey]
      } else if (enhancedConfig[configKey]) {
        config = enhancedConfig[configKey]
        commit('SET_CONFIG_CACHE', { key: configKey, config: config })
      } else {
        const res = await fetchConfigDetail(configKey)
        if (res.data && res.data.config) {
          config = res.data.config
          commit('SET_CONFIG_CACHE', { key: configKey, config: config })
        }
      }

      if (config) {
        commit('SET_CURRENT_CONFIG', config)
        dispatch('initConfigParams')
        commit('SET_CHECKED_METRIC_KEYS', [])
      }
    } catch (error) {
      console.error('加载配置详情失败:', error)
    }
  },

  initConfigParams({ commit, getters }) {
    const params = {}
    getters.currentConfigParams.forEach(param => {
      if (param.default !== undefined) {
        params[param.key] = param.default
      } else if (param.options && param.options.length > 0) {
        params[param.key] = param.options[0].value
      }
    })
    commit('SET_CONFIG_PARAMS', params)
  },

  // 数据提取
  async extractData({ commit, state, getters }) {
    if (!getters.canExtractData) {
      return { success: false, message: '请完善必要参数：选择股票、指标类型和具体指标' }
    }

    commit('SET_LOADING_DATA', true)
    try {
      const params = { ...state.configParams }

      // 验证参数
      try {
        const validationRes = await validateParams(state.selectedConfigKey, params)
        if (validationRes.data && !validationRes.data.valid) {
          const missingParams = validationRes.data.missing_params || []
          return {
            success: false,
            message: `缺少必填参数: ${missingParams.map(p => p.title).join(', ')}`,
            needParamConfig: true
          }
        }
      } catch (validationError) {
        console.warn('参数验证失败，继续执行:', validationError)
      }

      const res = await fetchDynamicDataWithFilter(state.selectedConfigKey, params, state.selectedStocks)
      if (res.data) {
        commit('SET_RAW_ROWS', res.data)
        dispatch('buildTableData')
        return { success: true, message: `成功提取 ${res.data.length} 条数据` }
      }
    } catch (error) {
      if (error.response && error.response.data && error.response.data.data && error.response.data.data.missing_params) {
        const missingParams = error.response.data.data.missing_params
        return {
          success: false,
          message: `缺少必填参数: ${missingParams.map(p => p.title).join(', ')}`,
          needParamConfig: true
        }
      } else {
        return { success: false, message: '提取数据失败: ' + error.message }
      }
    } finally {
      commit('SET_LOADING_DATA', false)
    }
  },

  buildTableData({ commit, state }) {
    const columns = ['symbol', 'name']
    const metricFields = state.selectedMetricKeys.map(key => key)

    const tableRows = state.rawRows.map(row => {
      const tableRow = {
        symbol: row.symbol || row['股票代码'] || '-',
        name: row.name || row['股票简称'] || '-'
      }

      metricFields.forEach(fullKey => {
        const value = row[fullKey]
        tableRow[fullKey] = (value !== undefined && value !== null && value !== '') ? value : '-'
      })

      return tableRow
    })

    commit('SET_TABLE_ROWS', tableRows)
  }
}

export default {
  namespaced: true,
  state,
  mutations,
  getters,
  actions
}
