<template>
  <div class="concept-board-panel">
    <div class="panel-header">
      <i class="el-icon-s-grid"></i>
      概念板块
    </div>
    
    <!-- 搜索框 -->
    <el-input
      v-model="searchKeyword"
      placeholder="搜索概念板块"
      clearable
      size="small"
      prefix-icon="el-icon-search"
      @input="handleSearchChange"
    />
    
    <!-- 板块列表 -->
    <div class="concept-list" v-loading="loading">
      <div 
        v-if="filteredConcepts.length > 0"
        class="virtual-scroll-container"
        :style="{ height: 'calc(100% - 60px)' }"
        @scroll="handleScroll"
        ref="scrollContainer"
      >
        <div 
          class="virtual-scroll-content"
          :style="{ height: totalHeight + 'px' }"
        >
          <div 
            class="virtual-scroll-items"
            :style="{ transform: `translateY(${offsetY}px)` }"
          >
            <div 
              v-for="concept in visibleConcepts" 
              :key="concept.boardCode"
              class="concept-item"
              :class="{ 'selected': selectedConcepts.includes(concept.boardCode) }"
              @click="handleSelectConcept(concept)"
            >
              <div class="concept-info">
                <div class="concept-name">{{ concept.boardName }}</div>
                <div class="concept-stats">
                  <span class="change-pct" :class="getChangeClass(concept.changePct)">
                    {{ formatChangePct(concept.changePct) }}
                  </span>
                  <span class="stock-count">{{ getStockCount(concept) }}</span>
                </div>
              </div>
              <div class="concept-actions">
                <el-button 
                  size="mini" 
                  type="primary" 
                  @click.stop="handleBatchSelect(concept)"
                >
                  批量选择
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 无数据时显示 -->
      <div v-else class="empty-data">
        <el-empty description="暂无概念板块数据" />
      </div>
    </div>
    
    <!-- 批量选择确认对话框 -->
    <el-dialog
      title="批量选择确认"
      :visible.sync="batchSelectDialogVisible"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="batch-select-content">
        <!-- 板块信息 -->
        <div class="concept-info">
          <h4>{{ selectedConceptForBatch && selectedConceptForBatch.boardName }}</h4>
          <p>该板块共有 <strong>{{ componentStocks.length }}</strong> 只成分股</p>
        </div>
        
        <!-- 选择方式 -->
        <div class="selection-mode">
          <h5>选择方式：</h5>
          <el-radio-group v-model="selectionMode">
            <el-radio label="replace">● 替换当前选择（清空已选，使用选择个股）</el-radio>
            <el-radio label="merge">○ 智能添加（合并所有股票，自动去重）</el-radio>
          </el-radio-group>
        </div>
        
        <!-- 影响预览 -->
        <div class="impact-preview" :class="{ 'replace-mode': selectionMode === 'replace' }">
          <div class="preview-header">
            <div class="header-left">
              <div class="preview-title">影响预览：</div>
            </div>
            <div class="header-right">
              <el-tag 
                :type="selectionMode === 'replace' ? 'danger' : 'success'" 
                size="mini"
                effect="dark"
              >
                {{ selectionMode === 'replace' ? '替换模式' : '合并模式' }}
              </el-tag>
            </div>
          </div>
          <!-- 数据卡片展示 -->
          <div class="preview-cards">
            <div class="data-card current" :class="{ 'highlight': selectionMode === 'merge' }">
              <div class="card-icon">
                <i class="el-icon-check"></i>
              </div>
              <div class="card-content">
                <div class="card-title">当前已选</div>
                <div class="card-number">{{ selectedStocks.length }}</div>
                <div class="card-unit">只股票</div>
              </div>
            </div>
            
            <div class="data-card new" :class="{ 'highlight': true }">
              <div class="card-icon">
                <i class="el-icon-plus"></i>
              </div>
              <div class="card-content">
                <div class="card-title">新增板块</div>
                <div class="card-number">{{ componentStocks.length }}</div>
                <div class="card-unit">只股票</div>
              </div>
            </div>
            <div class="data-card duplicate" v-if="duplicateCount > 0">
              <div class="card-icon">
                <i class="el-icon-warning"></i>
              </div>
              <div class="card-content">
                <div class="card-title">重复股票</div>
                <div class="card-number">{{ duplicateCount }}</div>
                <div class="card-unit">将被忽略</div>
              </div>
            </div>
            <div class="data-card final">
              <div class="card-icon">
                <i class="el-icon-trophy"></i>
              </div>
              <div class="card-content">
                <div class="card-title">最终股票池</div>
                <div class="card-number">{{ finalStockCount }}</div>
                <div class="card-unit">只股票</div>
              </div>
            </div>
          </div>
          
          <!-- 变化提示 -->
          <div class="change-tip" v-if="selectionMode === 'merge' && duplicateCount > 0">
            <i class="el-icon-info"></i>
            <span>将自动去重 {{ duplicateCount }} 只重复股票</span>
          </div>
        </div>
        
        <!-- 股票筛选和预览 -->
        <div class="stock-filter-section" v-if="componentStocks.length > 0">
          <!-- 筛选控制栏 -->
          <div class="filter-controls">
            <div class="filter-header">
              <span class="filter-title">成分股筛选</span>
              <div class="filter-stats">
                <el-tag size="mini" type="info">
                  共 {{ componentStocks.length }} 只
                </el-tag>
                <el-tag 
                  size="mini" 
                  :type="filteredStocks.length > 0 ? 'success' : 'warning'"
                >
                  已筛选 {{ filteredStocks.length }} 只
                </el-tag>
              </div>
            </div>
            
            <!-- 筛选条件 -->
            <div class="filter-conditions">
              <div class="filter-row">
                <el-input
                  v-model="stockSearchKeyword"
                  placeholder="搜索股票代码/名称"
                  size="small"
                  clearable
                  prefix-icon="el-icon-search"
                  style="width: 200px; margin-right: 12px;"
                  @input="handleStockSearch"
                />
                
                <el-select
                  v-model="priceRangeFilter"
                  placeholder="价格区间"
                  size="small"
                  clearable
                  style="width: 120px; margin-right: 12px;"
                  @change="handlePriceRangeFilter"
                >
                  <el-option label="全部" value="" />
                  <el-option label="0-10元" value="0-10" />
                  <el-option label="10-50元" value="10-50" />
                  <el-option label="50-100元" value="50-100" />
                  <el-option label="100元以上" value="100+" />
                </el-select>
                
                <el-select
                  v-model="sortBy"
                  placeholder="排序方式"
                  size="small"
                  style="width: 120px;"
                  @change="handleSortChange"
                >
                  <el-option label="默认排序" value="default" />
                  <el-option label="按代码排序" value="code" />
                  <el-option label="按名称排序" value="name" />
                  <el-option label="按价格排序" value="price" />
                </el-select>
              </div>
              
              <!-- 快速筛选按钮 -->
              <div class="quick-filters">
                <el-button-group size="mini">
                  <el-button 
                    :type="quickFilter === 'all' ? 'primary' : ''"
                    @click="applyQuickFilter('all')"
                  >
                    全选
                  </el-button>
                  <el-button 
                    :type="quickFilter === 'top20' ? 'primary' : ''"
                    @click="applyQuickFilter('top20')"
                  >
                    前20只
                  </el-button>
                  <el-button 
                    :type="quickFilter === 'lowprice' ? 'primary' : ''"
                    @click="applyQuickFilter('lowprice')"
                  >
                    低价股
                  </el-button>
                  <el-button 
                    :type="quickFilter === 'clear' ? 'danger' : ''"
                    @click="applyQuickFilter('clear')"
                  >
                    清空
                  </el-button>
                </el-button-group>
              </div>
            </div>
          </div>
          
          <!-- 股票选择列表 -->
          <div class="stock-selection-list">
            <div class="selection-header">
              <div class="header-left">
                <el-checkbox 
                  v-model="selectAll"
                  :indeterminate="isIndeterminate"
                  @change="handleSelectAll"
                >
                  全选已筛选股票
                </el-checkbox>
              </div>
              <div class="header-right">
                <span class="selection-count">
                  已选择 {{ selectedStockSymbols.length }} / {{ filteredStocks.length }} 只
                </span>
              </div>
            </div>
            
            <div class="stock-list-container">
              <div class="stock-list">
                <div 
                  v-for="stock in paginatedStocks" 
                  :key="stock.symbol"
                  class="stock-selection-item"
                  :class="{ 'selected': selectedStockSymbols.includes(stock.symbol) }"
                  @click="toggleStockSelection(stock.symbol)"
                >
                  <el-checkbox 
                    :value="selectedStockSymbols.includes(stock.symbol)"
                    @change="toggleStockSelection(stock.symbol)"
                    @click.native.stop
                  />
                  <div class="stock-info">
                    <span class="stock-code">{{ stock.symbol }}</span>
                    <span class="stock-name">{{ stock.name }}</span>
                  </div>
                  <span class="stock-price">{{ stock.price }}</span>
                </div>
              </div>
              
              <!-- 分页控件 -->
              <div class="pagination-container" v-if="filteredStocks.length > pageSize">
                <el-pagination
                  :current-page="currentPage"
                  :page-size="pageSize"
                  :total="filteredStocks.length"
                  :pager-count="5"
                  layout="prev, pager, next, total"
                  small
                  @current-change="handlePageChange"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div slot="footer" class="dialog-footer">
        <el-button @click="batchSelectDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="confirmBatchSelect"
          :loading="batchSelecting"
        >
          确认选择 ({{ getFinalSelectedCount() }}只)
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { debounce } from 'lodash-es'
import { fetchConceptBoardList, fetchConceptComponentStocks } from '@/api/stock/concept_board'

export default {
  name: 'ConceptBoardPanel',
  props: {
    selectedStocks: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      // 搜索相关
      searchKeyword: '',
      actualSearchKeyword: '',
      
      // 数据相关
      concepts: [],
      loading: false,
      
      // 选择相关
      selectedConcepts: [],
      selectedConceptForBatch: null,
      componentStocks: [],
      batchSelectDialogVisible: false,
      batchSelecting: false,
      selectionMode: 'merge', // 默认选择智能添加模式
      
      // 股票筛选相关
      stockSearchKeyword: '',
      priceRangeFilter: '',
      sortBy: 'default',
      quickFilter: '',
      selectedStockSymbols: [], // 用户选择的股票代码
      currentPage: 1,
      pageSize: 20,
      
      // 虚拟滚动相关
      itemHeight: 60,
      visibleCount: 8,
      scrollTop: 0,
      startIndex: 0,
      endIndex: 8,
      
      // 缓存
      cachedFilteredConcepts: null,
      lastConceptsLength: 0
    }
  },
  computed: {
    filteredConcepts() {
      const keyword = this.actualSearchKeyword.trim().toLowerCase()
      
      if (!keyword) {
        // 缓存排序结果
        if (!this.cachedFilteredConcepts || this.concepts.length !== this.lastConceptsLength) {
          this.cachedFilteredConcepts = [...this.concepts].sort((a, b) => {
            // 按涨跌幅降序排列
            return (b.changePct || 0) - (a.changePct || 0)
          })
          this.lastConceptsLength = this.concepts.length
        }
        return this.cachedFilteredConcepts
      }
      
      // 有搜索条件时进行筛选
      return this.concepts.filter(concept => 
        concept.boardName.toLowerCase().includes(keyword)
      ).sort((a, b) => {
        return (b.changePct || 0) - (a.changePct || 0)
      })
    },
    
    totalHeight() {
      return this.filteredConcepts.length * this.itemHeight
    },
    
    offsetY() {
      return this.startIndex * this.itemHeight
    },
    
    visibleConcepts() {
      return this.filteredConcepts.slice(this.startIndex, this.endIndex)
    },
    
    // 计算重复股票数量
    duplicateCount() {
      if (!this.componentStocks.length || !this.selectedStocks.length) {
        return 0
      }
      
      const componentSymbols = new Set(this.componentStocks.map(stock => stock.symbol))
      const selectedSymbols = new Set(this.selectedStocks)
      
      let duplicates = 0
      for (const symbol of componentSymbols) {
        if (selectedSymbols.has(symbol)) {
          duplicates++
        }
      }
      
      return duplicates
    },
    
    // 计算最终股票数量
    finalStockCount() {
      if (this.selectionMode === 'replace') {
        return this.componentStocks.length
      } else {
        // 智能添加模式：当前已选 + 新增（去重后）
        const newStocks = this.componentStocks.filter(stock => 
          !this.selectedStocks.includes(stock.symbol)
        )
        return this.selectedStocks.length + newStocks.length
      }
    },
    
    // 筛选后的股票列表
    filteredStocks() {
      let stocks = [...this.componentStocks]
      
      // 搜索筛选
      if (this.stockSearchKeyword.trim()) {
        const keyword = this.stockSearchKeyword.trim().toLowerCase()
        stocks = stocks.filter(stock => 
          stock.symbol.toLowerCase().includes(keyword) || 
          stock.name.toLowerCase().includes(keyword)
        )
      }
      
      // 价格区间筛选
      if (this.priceRangeFilter) {
        stocks = stocks.filter(stock => {
          const price = parseFloat(stock.price) || 0
          switch (this.priceRangeFilter) {
            case '0-10':
              return price >= 0 && price <= 10
            case '10-50':
              return price > 10 && price <= 50
            case '50-100':
              return price > 50 && price <= 100
            case '100+':
              return price > 100
            default:
              return true
          }
        })
      }
      
      // 排序
      stocks.sort((a, b) => {
        switch (this.sortBy) {
          case 'code':
            return a.symbol.localeCompare(b.symbol)
          case 'name':
            return a.name.localeCompare(b.name)
          case 'price':
            return (parseFloat(b.price) || 0) - (parseFloat(a.price) || 0)
          default:
            return 0
        }
      })
      
      return stocks
    },
    
    // 分页后的股票列表
    paginatedStocks() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = start + this.pageSize
      return this.filteredStocks.slice(start, end)
    },
    
    // 全选状态
    selectAll() {
      return this.filteredStocks.length > 0 && 
             this.selectedStockSymbols.length === this.filteredStocks.length
    },
    
    // 半选状态
    isIndeterminate() {
      return this.selectedStockSymbols.length > 0 && 
             this.selectedStockSymbols.length < this.filteredStocks.length
    }
  },
  created() {
    // 创建防抖函数
    this.debouncedSearch = debounce((keyword) => {
      this.actualSearchKeyword = keyword
    }, 300)
    
    // 加载概念板块数据
    this.loadConceptBoards()
  },
  methods: {
    // 加载概念板块数据
    async loadConceptBoards() {
      this.loading = true
      try {
        const response = await fetchConceptBoardList()
        if (response.code === 200) {
          // 转换数据格式，使用英文字段名
          this.concepts = (response.data || []).map(item => ({
            boardCode: item['板块代码'],
            boardName: item['板块名称'],
            changePct: item['涨跌幅'],
            upCount: item['上涨家数'],
            downCount: item['下跌家数']
          }))
          this.cachedFilteredConcepts = null // 重置缓存
        } else {
          this.$message.error('获取概念板块数据失败')
        }
      } catch (error) {
        console.error('获取概念板块数据失败:', error)
        this.$message.error('获取概念板块数据失败')
      } finally {
        this.loading = false
      }
    },
    
    // 搜索处理
    handleSearchChange(keyword) {
      this.debouncedSearch(keyword)
    },
    
    // 选择概念板块
    handleSelectConcept(concept) {
      const index = this.selectedConcepts.indexOf(concept.boardCode)
      if (index > -1) {
        this.selectedConcepts.splice(index, 1)
      } else {
        this.selectedConcepts.push(concept.boardCode)
      }
    },
    
    // 批量选择处理
    async handleBatchSelect(concept) {
      this.selectedConceptForBatch = concept
      this.batchSelecting = true
      
      try {
        const response = await fetchConceptComponentStocks(concept.boardName)
        if (response.code === 200) {
          this.componentStocks = response.data || []
          // 重置筛选状态
          this.resetFilterState()
          this.batchSelectDialogVisible = true
        } else {
          this.$message.error('获取成分股数据失败')
        }
      } catch (error) {
        console.error('获取成分股数据失败:', error)
        this.$message.error('获取成分股数据失败')
      } finally {
        this.batchSelecting = false
      }
    },
    
    // 确认批量选择
    confirmBatchSelect() {
      let stockSymbols = []
      
      // 优先使用用户筛选选择的股票，如果没有选择则使用全部成分股
      const selectedStocks = this.selectedStockSymbols.length > 0 
        ? this.selectedStockSymbols 
        : this.componentStocks.map(stock => stock.symbol)
      
      if (this.selectionMode === 'replace') {
        // 替换模式：使用筛选后的股票
        stockSymbols = selectedStocks
        this.$emit('batch-select-stocks', stockSymbols, 'replace')
        this.$message.success(`已替换选择 ${stockSymbols.length} 只股票`)
      } else {
        // 智能添加模式：合并当前已选和新增股票，自动去重
        const newStocks = selectedStocks.filter(symbol => 
          !this.selectedStocks.includes(symbol)
        )
        stockSymbols = this.selectedStocks.concat(newStocks)
        this.$emit('batch-select-stocks', stockSymbols, 'merge')
        this.$message.success(`已智能添加 ${newStocks.length} 只股票，最终共 ${stockSymbols.length} 只`)
      }
      
      this.batchSelectDialogVisible = false
    },
    
    // 格式化涨跌幅
    formatChangePct(changePct) {
      if (changePct === null || changePct === undefined) return '--'
      return (changePct > 0 ? '+' : '') + changePct.toFixed(2) + '%'
    },
    
    // 获取涨跌幅样式类
    getChangeClass(changePct) {
      if (changePct > 0) return 'positive'
      if (changePct < 0) return 'negative'
      return 'neutral'
    },
    
    // 获取股票统计数量
    getStockCount(concept) {
      const upCount = concept.upCount || 0
      const downCount = concept.downCount || 0
      return `${upCount}/${upCount + downCount}`
    },
    
    // 虚拟滚动处理
    handleScroll(event) {
      const scrollTop = event.target.scrollTop
      this.scrollTop = scrollTop
      
      this.startIndex = Math.floor(scrollTop / this.itemHeight)
      this.endIndex = Math.min(
        this.startIndex + this.visibleCount + 3,
        this.filteredConcepts.length
      )
    },
    
    // 重置虚拟滚动状态
    resetVirtualScroll() {
      this.scrollTop = 0
      this.startIndex = 0
      this.endIndex = Math.min(this.visibleCount + 3, this.filteredConcepts.length)
      
      if (this.$refs.scrollContainer) {
        this.$refs.scrollContainer.scrollTop = 0
      }
    },
    
    // 股票筛选相关方法
    handleStockSearch() {
      this.currentPage = 1 // 重置到第一页
    },
    
    handlePriceRangeFilter() {
      this.currentPage = 1 // 重置到第一页
    },
    
    handleSortChange() {
      this.currentPage = 1 // 重置到第一页
    },
    
    // 快速筛选
    applyQuickFilter(filterType) {
      this.quickFilter = filterType
      this.selectedStockSymbols = [] // 清空当前选择
      
      switch (filterType) {
        case 'all':
          // 选择所有筛选后的股票
          this.selectedStockSymbols = this.filteredStocks.map(stock => stock.symbol)
          break
        case 'top20':
          // 选择前20只股票
          this.selectedStockSymbols = this.filteredStocks.slice(0, 20).map(stock => stock.symbol)
          break
        case 'lowprice':
          // 选择低价股（价格<10元）
          this.selectedStockSymbols = this.filteredStocks
            .filter(stock => parseFloat(stock.price) < 10)
            .map(stock => stock.symbol)
          break
        case 'clear':
          // 清空选择
          this.selectedStockSymbols = []
          break
      }
    },
    
    // 全选/取消全选
    handleSelectAll(checked) {
      if (checked) {
        this.selectedStockSymbols = this.filteredStocks.map(stock => stock.symbol)
      } else {
        this.selectedStockSymbols = []
      }
    },
    
    // 切换单个股票选择
    toggleStockSelection(symbol) {
      const index = this.selectedStockSymbols.indexOf(symbol)
      if (index > -1) {
        this.selectedStockSymbols.splice(index, 1)
      } else {
        this.selectedStockSymbols.push(symbol)
      }
    },
    
    // 分页处理
    handlePageChange(page) {
      this.currentPage = page
    },
    
    // 获取最终选择数量
    getFinalSelectedCount() {
      const selectedStocks = this.selectedStockSymbols.length > 0 
        ? this.selectedStockSymbols 
        : this.componentStocks.map(stock => stock.symbol)
      
      if (this.selectionMode === 'replace') {
        return selectedStocks.length
      } else {
        const newStocks = selectedStocks.filter(symbol => 
          !this.selectedStocks.includes(symbol)
        )
        return this.selectedStocks.length + newStocks.length
      }
    },
    
    // 重置筛选状态
    resetFilterState() {
      this.stockSearchKeyword = ''
      this.priceRangeFilter = ''
      this.sortBy = 'default'
      this.quickFilter = ''
      this.selectedStockSymbols = []
      this.currentPage = 1
    }
  },
  watch: {
    actualSearchKeyword() {
      this.$nextTick(() => {
        this.resetVirtualScroll()
      })
    }
  }
}
</script>

<style scoped>
.concept-board-panel {
  height: 100%;
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: none;
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

.concept-list {
  flex: 1;
  overflow: hidden;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-top: 8px;
}

.virtual-scroll-container {
  overflow-y: auto;
  border: none;
  border-radius: 0;
}

.virtual-scroll-content {
  position: relative;
}

.virtual-scroll-items {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
}

.concept-item {
  height: 60px;
  padding: 8px 12px;
  border-bottom: 1px solid #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: background-color 0.2s;
}

.concept-item:hover {
  background-color: #f5f7fa;
}

.concept-item.selected {
  background-color: #ecf5ff;
  border-color: #409eff;
}

.concept-info {
  flex: 1;
}

.concept-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.concept-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
}

.change-pct {
  font-weight: 500;
}

.change-pct.positive {
  color: #f56c6c;
}

.change-pct.negative {
  color: #67c23a;
}

.change-pct.neutral {
  color: #909399;
}

.stock-count {
  color: #909399;
}

.concept-actions {
  margin-left: 12px;
}

.empty-data {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.batch-select-content {
  max-height: 400px;
  overflow-y: auto;
}

.concept-info h4 {
  margin: 0 0 8px 0;
  color: #303133;
}

.concept-info p {
  margin: 0 0 16px 0;
  color: #606266;
}

.stock-preview {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
}

.preview-header {
  background-color: #f5f7fa;
  padding: 8px 12px;
  font-size: 12px;
  color: #909399;
  border-bottom: 1px solid #ebeef5;
}

.stock-list {
  max-height: 200px;
  overflow-y: auto;
}

.stock-preview-item {
  padding: 6px 12px;
  border-bottom: 1px solid #f5f7fa;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
}

.stock-preview-item:last-child {
  border-bottom: none;
}

.stock-code {
  color: #409eff;
  font-weight: 500;
  min-width: 60px;
}

.stock-name {
  flex: 1;
  color: #303133;
}

.stock-price {
  color: #606266;
  min-width: 50px;
  text-align: right;
}

.more-stocks {
  padding: 8px 12px;
  text-align: center;
  color: #909399;
  font-size: 12px;
  background-color: #f9f9f9;
}

/* 选择方式样式 */
.selection-mode {
  margin: 16px 0;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.selection-mode h5 {
  margin: 0 0 12px 0;
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.selection-mode .el-radio {
  display: block;
  margin: 8px 0;
  font-size: 13px;
}

.selection-mode .el-radio__label {
  color: #606266;
  font-weight: 500;
}

/* 影响预览样式 */
.impact-preview {
  margin: 16px 0;
  padding: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #fafbfc 100%);
  border-radius: 8px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.3s ease;
}

.impact-preview.replace-mode {
  background: linear-gradient(135deg, #fef0f0 0%, #fdf2f2 100%);
  border-color: #fde2e2;
}

.impact-preview .preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.impact-preview .header-left {
  display: flex;
  align-items: center;
  flex: 1;
}

.impact-preview .header-left i {
  margin-right: 8px;
  color: #409eff;
  font-size: 18px;
}

.preview-title {
  margin: 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
}

.impact-preview .header-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* 数据卡片样式 */
.preview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
  align-items: stretch;
}

.data-card {
  min-width: 120px;
  padding: 12px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.3s ease;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.02);
  text-align: center;
  height: 100%;
}

.data-card.highlight {
  border-color: #409eff;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.data-card.current {
  border-color: #67c23a;
}

.data-card.current.highlight {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-color: #409eff;
}

.data-card.new {
  border-color: #409eff;
}

.data-card.duplicate {
  border-color: #e6a23c;
  background: linear-gradient(135deg, #fdf6ec 0%, #fef7e6 100%);
}

.data-card.final {
  border-color: #f56c6c;
  background: linear-gradient(135deg, #fef0f0 0%, #fdf2f2 100%);
  box-shadow: 0 2px 8px rgba(245, 108, 108, 0.15);
}

.data-card .card-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #fff;
}

.data-card.current .card-icon {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

.data-card.new .card-icon {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}

.data-card.duplicate .card-icon {
  background: linear-gradient(135deg, #e6a23c 0%, #ebb563 100%);
}

.data-card.final .card-icon {
  background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%);
  box-shadow: 0 2px 6px rgba(245, 108, 108, 0.3);
}

.data-card .card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
}

.data-card .card-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 4px;
  text-align: center;
  white-space: nowrap;
}

.data-card .card-number {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  line-height: 1;
  text-align: center;
  min-width: 40px;
  font-variant-numeric: tabular-nums;
}

.data-card .card-unit {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
  text-align: center;
  white-space: nowrap;
}


/* 变化提示 */
.change-tip {
  margin-top: 12px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #e1f3d8 0%, #f0f9ff 100%);
  border-radius: 6px;
  border: 1px solid #b3d8ff;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #409eff;
}

.change-tip i {
  color: #67c23a;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .preview-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  
  .data-card {
    min-width: auto;
    padding: 10px;
  }
  
}

@media (max-width: 480px) {
  .impact-preview {
    padding: 12px;
    margin: 12px 0;
  }
  
  .impact-preview .preview-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .preview-cards {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  
  .data-card {
    padding: 8px;
  }
  
  .data-card .card-title {
    font-size: 13px;
  }
  
  .data-card .card-number {
    font-size: 18px;
  }
  
  .data-card .card-unit {
    font-size: 12px;
  }
  
}

/* 对话框底部样式优化 */
.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.footer-actions {
  display: flex;
  gap: 12px;
}

/* 股票筛选相关样式 */
.stock-filter-section {
  margin-top: 16px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
}

.filter-controls {
  background: #f8f9fa;
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.filter-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.filter-stats {
  display: flex;
  gap: 8px;
}

.filter-conditions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-filters {
  display: flex;
  justify-content: flex-start;
}

.stock-selection-list {
  background: #fff;
}

.selection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.selection-count {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

.stock-list-container {
  max-height: 400px;
  overflow-y: auto;
}

.stock-list {
  padding: 8px;
}

.stock-selection-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  gap: 12px;
  border: 1px solid transparent;
}

.stock-selection-item:hover {
  background-color: #f5f7fa;
  border-color: #e4e7ed;
}

.stock-selection-item.selected {
  background-color: #ecf5ff;
  border-color: #409eff;
}

.stock-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.stock-code {
  color: #409eff;
  font-weight: 500;
  font-size: 13px;
  min-width: 60px;
  flex-shrink: 0;
}

.stock-name {
  color: #303133;
  font-size: 13px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stock-price {
  color: #606266;
  font-size: 13px;
  min-width: 60px;
  text-align: right;
  font-weight: 500;
}

.pagination-container {
  padding: 12px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
  display: flex;
  justify-content: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-row .el-input,
  .filter-row .el-select {
    width: 100% !important;
    margin-right: 0 !important;
    margin-bottom: 8px;
  }
  
  .quick-filters {
    justify-content: center;
  }
  
  .selection-header {
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }
  
  .stock-selection-item {
    padding: 6px 8px;
  }
  
  .stock-info {
    gap: 8px;
  }
}
</style>