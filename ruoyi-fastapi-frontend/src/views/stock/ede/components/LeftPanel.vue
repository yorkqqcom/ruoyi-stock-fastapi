<template>
  <div class="ede-left" :style="{ width: width + 'px' }">
    <!-- 上部：现有待选股票列表 -->
    <div class="stock-section">
      <div class="panel-header">
        <i class="el-icon-s-grid"></i>
        待选股票
      </div>
      
      <el-input
        v-model="stockFilter"
        placeholder="按代码/名称筛选"
        clearable
        size="small"
        prefix-icon="el-icon-search"
        @input="handleFilterChange"
      />
      
      <div class="stock-list" v-loading="loading">
      <!-- 使用虚拟滚动优化长列表 -->
      <div 
        v-if="filteredStocks.length > 0"
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
              v-for="item in visibleStocks" 
              :key="item.symbol"
              class="stock-item"
              :class="{ 'selected': selectedStocks.includes(item.symbol) }"
              @click="handleSelectSymbol(item.symbol)"
            >
              <el-checkbox
                :value="selectedStocks.includes(item.symbol)"
                @click.stop="handleToggleStock(item.symbol)"
              />
              <span class="code">{{ item.symbol }}</span>
              <span class="name">{{ item.name }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 无数据时显示 -->
      <div v-else class="empty-data">
        <el-empty description="暂无股票数据" />
      </div>
    </div>
    </div>
    
    <!-- 分隔线 -->
    <div class="section-divider"></div>
    
    <!-- 下部：概念板块列表 -->
    <div class="concept-section">
      <ConceptBoardPanel
        :selected-stocks="selectedStocks"
        @batch-select-stocks="handleBatchSelectStocks"
      />
    </div>
  </div>
</template>

<script>
import { debounce } from 'lodash-es'
import ConceptBoardPanel from './ConceptBoardPanel.vue'

export default {
  name: 'LeftPanel',
  components: {
    ConceptBoardPanel
  },
  props: {
    width: {
      type: Number,
      default: 280
    },
    stocks: {
      type: Array,
      default: () => []
    },
    selectedStocks: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      stockFilter: '',
      actualStockFilter: '', // 实际用于筛选的值
      
      // 虚拟滚动相关
      itemHeight: 40, // 每个股票项的高度
      visibleCount: 20, // 可见区域显示的项目数量
      scrollTop: 0,
      startIndex: 0,
      endIndex: 20,
      
      // 缓存排序结果
      cachedSortedStocks: null,
      lastStocksLength: 0
    }
  },
  computed: {
    // 优化后的筛选逻辑，使用缓存和防抖
    filteredStocks() {
      const q = this.actualStockFilter.trim().toLowerCase()
      
      if (!q) {
        // 缓存排序结果，避免每次重新排序
        if (!this.cachedSortedStocks || this.stocks.length !== this.lastStocksLength) {
          this.cachedSortedStocks = [...this.stocks].sort((a, b) => {
            const aNum = parseInt(a.symbol.replace(/\D/g, '')) || 0
            const bNum = parseInt(b.symbol.replace(/\D/g, '')) || 0
            return aNum - bNum
          })
          this.lastStocksLength = this.stocks.length
        }
        return this.cachedSortedStocks
      }
      
      // 有筛选条件时进行筛选
      return this.stocks.filter(s => 
        s.symbol.toLowerCase().includes(q) || 
        (s.name && s.name.toLowerCase().includes(q))
      ).sort((a, b) => {
        const aNum = parseInt(a.symbol.replace(/\D/g, '')) || 0
        const bNum = parseInt(b.symbol.replace(/\D/g, '')) || 0
        return aNum - bNum
      })
    },
    
    // 虚拟滚动计算
    totalHeight() {
      return this.filteredStocks.length * this.itemHeight
    },
    
    offsetY() {
      return this.startIndex * this.itemHeight
    },
    
    visibleStocks() {
      return this.filteredStocks.slice(this.startIndex, this.endIndex)
    }
  },
  created() {
    // 创建防抖函数
    this.debouncedFilter = debounce((value) => {
      this.actualStockFilter = value
    }, 300)
  },
  methods: {
    handleFilterChange(value) {
      this.debouncedFilter(value)
    },
    
    handleSelectSymbol(symbol) {
      this.$emit('select-stock', symbol)
    },
    
    handleToggleStock(symbol) {
      this.$emit('toggle-stock', symbol)
    },
    
    // 处理批量选择股票
    handleBatchSelectStocks(stockSymbols, mode = 'merge') {
      this.$emit('batch-select-stocks', stockSymbols, mode)
    },
    
    // 虚拟滚动处理
    handleScroll(event) {
      const scrollTop = event.target.scrollTop
      this.scrollTop = scrollTop
      
      // 计算可见区域的项目索引
      this.startIndex = Math.floor(scrollTop / this.itemHeight)
      this.endIndex = Math.min(
        this.startIndex + this.visibleCount + 5, // 多渲染5个项目作为缓冲
        this.filteredStocks.length
      )
    },
    
    // 重置虚拟滚动状态
    resetVirtualScroll() {
      this.scrollTop = 0
      this.startIndex = 0
      this.endIndex = Math.min(this.visibleCount + 5, this.filteredStocks.length)
      
      if (this.$refs.scrollContainer) {
        this.$refs.scrollContainer.scrollTop = 0
      }
    }
  },
  watch: {
    // 当筛选条件变化时重置滚动位置
    actualStockFilter() {
      this.$nextTick(() => {
        this.resetVirtualScroll()
      })
    },
    
    // 当股票数据变化时重置缓存
    stocks: {
      handler() {
        this.cachedSortedStocks = null
        this.lastStocksLength = 0
      },
      deep: true
    }
  }
}
</script>

<style scoped>
.ede-left {
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

.stock-section {
  flex: 6;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}

.section-divider {
  height: 1px;
  background-color: #ebeef5;
  margin: 16px 0;
}

.concept-section {
  flex: 4;
  min-height: 200px;
  display: flex;
  flex-direction: column;
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

.stock-list {
  flex: 1;
  overflow: hidden;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
}

.virtual-scroll-container {
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  height: 100%;
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

.stock-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px dotted #f0f0f0;
  transition: all 0.3s;
  height: 40px;
  box-sizing: border-box;
}

.stock-item:hover {
  background: #f9f9f9;
}

.stock-item.selected {
  background: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.stock-item .code {
  color: #606266;
  margin-left: 8px;
  font-weight: 500;
  flex-shrink: 0;
}

.stock-item .name {
  color: #909399;
  margin-left: auto;
  font-size: 12px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100px;
}

.empty-data {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
}

/* 滚动条样式优化 */
.virtual-scroll-container::-webkit-scrollbar {
  width: 6px;
}

.virtual-scroll-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.virtual-scroll-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.virtual-scroll-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
