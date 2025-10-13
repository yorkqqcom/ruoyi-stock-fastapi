<template>
  <div class="app-container" @keydown.enter="handleEnterKey">
    <!-- 查询条件 -->
    <el-form :inline="true">
      <el-form-item label="股票代码" prop="symbol">
        <el-autocomplete
          v-model="queryForm.symbol"
          :fetch-suggestions="fetchSuggestions"
          placeholder="输入股票代码或名称"
          class="light-input"
          style="width: 150px"
          @select="handleSelectSymbol"
          value-key="symbol"
          :trigger-on-focus="false"
          @input="handleSymbolInput"
        >
          <template slot-scope="{ item }">
            <div class="symbol-item">
              <span class="symbol-code">{{ item.symbol }}</span>
              <span class="symbol-name">{{ item.name }}</span>
            </div>
          </template>
        </el-autocomplete>
      </el-form-item>

      <el-form-item label="复权类型">
        <el-select
          v-model="queryForm.adjustType"
          class="light-select"
          style="width: 150px;"
          @change="saveSettings"
        >
          <el-option label="前复权" value="qfq"/>
          <el-option label="后复权" value="hfq"/>
          <el-option label="不复权" value="normal"/>
        </el-select>
      </el-form-item>

      <el-form-item label="日期范围">
        <el-date-picker
          v-model="queryForm.dateRange"
          style="width: 280px;"
          type="daterange"
          class="light-date-picker"
          value-format="yyyy-MM-dd"
          range-separator="至"
        />
      </el-form-item>

      <el-button
        type="primary"
        @click="loadData"
        :loading="loading"
        icon="el-icon-search"
        style="background: #409EFF;"
      >
        查询
      </el-button>

      <el-button
        type="success"
        @click="showTrainDialog"
        :loading="trainLoading"
        icon="el-icon-video-play"
        style="margin-left: 15px;"
        :disabled="!hasKlineData"
      >
        训练模型
      </el-button>

      <el-button
        type="warning"
        @click="handlePredict"
        :loading="predictLoading"
        icon="el-icon-data-line"
        style="margin-left: 15px;"
        :disabled="!modelTrained"
      >
        预测未来走势
      </el-button>

      <el-button
        type="info"
        @click="showFeatureDialog"
        icon="el-icon-setting"
        style="margin-left: 15px;"
      >
        训练因子配置
        <el-badge
          v-if="selectedFeatures.length > 0"
          :value="selectedFeatures.length"
          class="feature-badge"
        />
      </el-button>
    </el-form>

    <!-- 状态提示 -->
    <el-alert
      v-if="loading"
      title="数据加载中..."
      type="info"
      :closable="false"
      show-icon
      class="status-alert"
    />

    <el-alert
      v-if="modelTrained"
      type="success"
      :closable="false"
      show-icon
      class="status-alert"
    >
      <template slot="title">
        <span>模型已训练完成，可以进行预测</span>
        <el-tag size="mini" type="success" style="margin-left: 10px;">
          R² = {{ trainResult.r2_score ? trainResult.r2_score.toFixed(4) : 'N/A' }}
        </el-tag>
        <el-tag size="mini" type="info" style="margin-left: 5px;">
          回顾天数 = {{ trainResult.best_lookback }}
        </el-tag>
      </template>
    </el-alert>

    <!-- K线图表 -->
    <div ref="chart" class="chart-container"></div>

    <!-- 训练结果展示 -->
    <el-card class="result-card" v-if="trainResult && trainResult.metrics">
      <div slot="header" class="clearfix">
        <span>模型训练结果</span>
        <el-tag size="small" type="success" style="margin-left: 10px;">
          最佳回顾窗口: {{ trainResult.best_lookback }}天
        </el-tag>
      </div>

      <!-- 模型评估指标 -->
      <el-descriptions title="模型评估指标" :column="5" border>
        <el-descriptions-item label="R² Score">
          <span :style="getR2Style(trainResult.r2_score)">
            {{ trainResult.r2_score ? trainResult.r2_score.toFixed(4) : 'N/A' }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="RMSE">
          {{ trainResult.metrics.rmse ? trainResult.metrics.rmse.toFixed(2) : 'N/A' }}
        </el-descriptions-item>
        <el-descriptions-item label="MAE">
          {{ trainResult.metrics.mae ? trainResult.metrics.mae.toFixed(2) : 'N/A' }}
        </el-descriptions-item>
        <el-descriptions-item label="MAPE">
          {{ trainResult.metrics.mape ? trainResult.metrics.mape.toFixed(2) + '%' : 'N/A' }}
        </el-descriptions-item>
        <el-descriptions-item label="方向准确率">
          <el-tag :type="getDirectionAccuracyType(trainResult.metrics.direction_accuracy)" size="medium">
            {{ trainResult.metrics.direction_accuracy ? trainResult.metrics.direction_accuracy.toFixed(2) + '%' : 'N/A' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- v7新增：综合评分和过拟合检查 -->
      <el-descriptions
        v-if="trainResult.metrics.composite_score"
        title="v7增强指标"
        :column="2"
        border
        style="margin-top: 15px;"
      >
        <el-descriptions-item label="综合评分">
          <span :style="getR2Style(trainResult.metrics.composite_score)">
            {{ trainResult.metrics.composite_score.toFixed(4) }}
          </span>
          <el-tooltip content="综合评分 = 0.4 * R² + 0.4 * (方向准确率/100) - 0.2 * 过拟合惩罚" placement="top">
            <i class="el-icon-question" style="margin-left: 5px; color: #909399; cursor: help;"></i>
          </el-tooltip>
        </el-descriptions-item>
        <el-descriptions-item label="过拟合检查">
          <el-tag :type="getOverfitType(trainResult.metrics.overfit_penalty)" size="medium">
            {{ trainResult.metrics.overfit_penalty ? trainResult.metrics.overfit_penalty.toFixed(4) : '0' }}
            {{ getOverfitText(trainResult.metrics.overfit_penalty) }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 训练配置 -->
      <el-descriptions title="训练配置" :column="4" border style="margin-top: 20px;">
        <el-descriptions-item label="训练轮次">
          {{ trainConfig.epochs }}
        </el-descriptions-item>
        <el-descriptions-item label="批次大小">
          {{ trainConfig.batch_size }}
        </el-descriptions-item>
        <el-descriptions-item label="学习率">
          {{ trainConfig.learning_rate }}
        </el-descriptions-item>
        <el-descriptions-item label="特征数量">
          {{ selectedFeatures.length || '全部' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 预测结果展示 -->
    <el-card class="result-card" v-if="predictionResult && predictionResult.predictions">
      <div slot="header" class="clearfix">
        <span>未来 {{ predictionResult.predictions.length }} 天价格预测</span>
        <el-tag
          size="small"
          :type="predictionResult.trend === 'up' ? 'success' : 'danger'"
          style="margin-left: 10px;"
        >
          {{ predictionResult.trend === 'up' ? '看涨' : '看跌' }}
        </el-tag>
        <el-tag size="small" type="info" style="margin-left: 10px;">
          {{ queryForm.adjustType === 'qfq' ? '前复权' : queryForm.adjustType === 'hfq' ? '后复权' : '不复权' }}
        </el-tag>
        <el-button-group style="float: right;">
          <el-button
            size="small"
            :type="predictionViewMode === 'chart' ? 'primary' : ''"
            icon="el-icon-data-line"
            @click="predictionViewMode = 'chart'"
          >
            图表视图
          </el-button>
          <el-button
            size="small"
            :type="predictionViewMode === 'table' ? 'primary' : ''"
            icon="el-icon-tickets"
            @click="predictionViewMode = 'table'"
          >
            表格视图
          </el-button>
        </el-button-group>
      </div>

      <!-- 图表视图提示 -->
      <el-alert
        v-if="predictionViewMode === 'chart'"
        type="success"
        :closable="false"
        style="margin-bottom: 15px;"
      >
        <template slot="title">
          <i class="el-icon-info"></i>
          <span style="margin-left: 8px;">
            预测结果已在上方K线图中展示。历史K线为实心，预测K线为虚线半透明显示（橙色区域）。
            <strong>开盘价和收盘价均为LSTM模型预测值</strong>，最高最低价为估算值，橙色虚线为预测收盘价走势线。
          </span>
        </template>
      </el-alert>

      <el-table
        v-if="predictionViewMode === 'table'"
        :data="predictionResult.predictions"
        border
        style="width: 100%"
      >
        <el-table-column prop="date" label="预测日期" width="120">
          <template slot-scope="scope">
            {{ formatDate(scope.row.date) }}
          </template>
        </el-table-column>
        <el-table-column prop="predicted_open" label="预测开盘价" width="120">
          <template slot-scope="scope">
            <el-tag type="warning" size="mini">LSTM</el-tag>
            {{ (scope.row.predicted_open || scope.row.predicted_price).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="predicted_price" label="预测收盘价" width="120">
          <template slot-scope="scope">
            <el-tag type="success" size="mini">LSTM</el-tag>
            {{ scope.row.predicted_price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="daily_change" label="日涨跌" width="100">
          <template slot-scope="scope">
            <span :style="getChangeStyle(scope.row.daily_change)">
              {{ scope.row.daily_change > 0 ? '+' : '' }}{{ scope.row.daily_change.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="daily_change_pct" label="日涨跌幅" width="100">
          <template slot-scope="scope">
            <span :style="getChangeStyle(scope.row.daily_change_pct)">
              {{ scope.row.daily_change_pct > 0 ? '+' : '' }}{{ scope.row.daily_change_pct.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="total_change" label="距今涨跌" width="100">
          <template slot-scope="scope">
            <span :style="getChangeStyle(scope.row.total_change)">
              {{ scope.row.total_change > 0 ? '+' : '' }}{{ scope.row.total_change.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="total_change_pct" label="距今涨跌幅" width="100">
          <template slot-scope="scope">
            <span :style="getChangeStyle(scope.row.total_change_pct)">
              {{ scope.row.total_change_pct > 0 ? '+' : '' }}{{ scope.row.total_change_pct.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template slot-scope="scope">
            <el-progress
              :percentage="scope.row.confidence * 100"
              :color="getConfidenceColor(scope.row.confidence)"
            ></el-progress>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 训练参数配置对话框 -->
    <el-dialog
      title="LSTM模型训练配置"
      :visible.sync="trainDialogVisible"
      width="60%"
      @close="handleTrainDialogClose"
    >
      <el-form :model="trainConfig" label-width="140px">
        <el-form-item label="回顾窗口选项">
          <el-checkbox-group v-model="trainConfig.lookback_options">
            <el-checkbox :label="10">10天</el-checkbox>
            <el-checkbox :label="30">30天</el-checkbox>
            <el-checkbox :label="45">45天</el-checkbox>
            <el-checkbox :label="60">60天</el-checkbox>
            <el-checkbox :label="90">90天</el-checkbox>
          </el-checkbox-group>
          <div class="form-tip">
            <el-tag size="mini" type="warning">v7推荐</el-tag>
            系统将自动测试选中的窗口大小并选择最佳配置（v7聚焦中期窗口：30/45/60天）
          </div>
        </el-form-item>

        <el-form-item label="训练轮次">
          <el-input-number
            v-model="trainConfig.epochs"
            :min="50"
            :max="500"
            :step="10"
          ></el-input-number>
          <span class="form-tip">建议 100-300</span>
        </el-form-item>

        <el-form-item label="批次大小">
          <el-input-number
            v-model="trainConfig.batch_size"
            :min="8"
            :max="128"
            :step="8"
          ></el-input-number>
          <span class="form-tip">建议 16-32</span>
        </el-form-item>

        <el-form-item label="学习率">
          <el-input-number
            v-model="trainConfig.learning_rate"
            :min="0.0001"
            :max="0.01"
            :step="0.0001"
            :precision="4"
          ></el-input-number>
          <span class="form-tip">建议 0.001</span>
        </el-form-item>

        <el-form-item label="测试集比例">
          <el-slider
            v-model="trainConfig.test_size"
            :min="0.05"
            :max="0.3"
            :step="0.05"
            :format-tooltip="val => (val * 100).toFixed(0) + '%'"
          ></el-slider>
        </el-form-item>

        <el-form-item label="验证集比例">
          <el-slider
            v-model="trainConfig.validation_split"
            :min="0.1"
            :max="0.3"
            :step="0.05"
            :format-tooltip="val => (val * 100).toFixed(0) + '%'"
          ></el-slider>
        </el-form-item>

        <el-form-item label="使用样本权重">
          <el-switch v-model="trainConfig.use_sample_weights"></el-switch>
          <span class="form-tip">近期数据权重更大</span>
        </el-form-item>

        <el-form-item label="样本权重衰减率" v-if="trainConfig.use_sample_weights">
          <el-input-number
            v-model="trainConfig.sample_weight_decay"
            :min="0.990"
            :max="0.999"
            :step="0.001"
            :precision="3"
          ></el-input-number>
          <span class="form-tip">建议 0.995-0.999</span>
        </el-form-item>

        <el-form-item label="预测未来天数">
          <el-input-number
            v-model="trainConfig.future_steps"
            :min="5"
            :max="60"
            :step="5"
          ></el-input-number>
          <span class="form-tip">预测时间越远准确度越低</span>
        </el-form-item>

        <el-divider content-position="left">
          <span style="color: #E6A23C; font-weight: bold;">v7 高级参数</span>
        </el-divider>

        <el-form-item label="L2正则化系数">
          <el-input-number
            v-model="trainConfig.l2_reg"
            :min="0"
            :max="0.01"
            :step="0.0001"
            :precision="4"
          ></el-input-number>
          <span class="form-tip">防止过拟合，建议 0.001</span>
        </el-form-item>

        <el-form-item label="Dropout率">
          <el-slider
            v-model="trainConfig.dropout_rate"
            :min="0.2"
            :max="0.6"
            :step="0.05"
            :format-tooltip="val => (val * 100).toFixed(0) + '%'"
          ></el-slider>
          <span class="form-tip">v7默认: 40%（原30%）</span>
        </el-form-item>

        <el-form-item label="使用方向感知损失">
          <el-switch v-model="trainConfig.use_directional_loss"></el-switch>
          <span class="form-tip">学习价格变化趋势</span>
        </el-form-item>

        <el-form-item label="方向损失权重" v-if="trainConfig.use_directional_loss">
          <el-slider
            v-model="trainConfig.direction_alpha"
            :min="0.1"
            :max="0.9"
            :step="0.1"
            :format-tooltip="val => (val * 100).toFixed(0) + '%'"
          ></el-slider>
          <span class="form-tip">方向损失的权重，建议 50%</span>
        </el-form-item>
      </el-form>

      <span slot="footer" class="dialog-footer">
        <el-button @click="trainDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleTrain" :loading="trainLoading">
          开始训练（v7增强版）
        </el-button>
      </span>
    </el-dialog>

    <!-- 特征选择对话框 -->
    <el-dialog
      title="训练因子选择"
      :visible.sync="featureDialogVisible"
      width="75%"
      @close="handleFeatureDialogClose"
      class="feature-selection-dialog"
    >
      <div class="feature-dialog-header">
        <el-alert
          type="success"
          :closable="false"
          style="margin-bottom: 20px;"
          v-if="hasFeatureConfig"
        >
          <template slot="title">
            <i class="el-icon-circle-check"></i>
            <span style="margin-left: 8px;">
              当前配置已保存，训练时将使用此因子配置
            </span>
          </template>
        </el-alert>

        <el-alert
          type="info"
          :closable="false"
          style="margin-bottom: 20px;"
        >
          <template slot="title">
            <i class="el-icon-info"></i>
            <span style="margin-left: 8px;">
              <strong>推荐因子</strong>包含价格、成交量、技术指标等核心数据，<strong style="color: #E6A23C;">建议保留</strong>
            </span>
          </template>
        </el-alert>

        <div class="selection-summary">
          <span class="summary-label">当前选择：</span>
          <el-tag type="success" size="medium">{{ selectedFeatures.length }} 个因子</el-tag>
          <el-button
            type="text"
            size="small"
            @click="selectAllFeatures"
            style="margin-left: 10px;"
          >
            全选
          </el-button>
          <el-button
            type="text"
            size="small"
            @click="clearAllFeatures"
          >
            清空
          </el-button>
          <el-button
            type="text"
            size="small"
            @click="resetToDefault"
            v-if="hasFeatureConfig"
          >
            恢复默认
          </el-button>
        </div>
      </div>

      <div v-loading="featuresLoading" class="feature-content">
        <el-collapse v-model="activeCategories">
          <el-collapse-item
            v-for="(features, category) in availableFeatures"
            :key="category"
            :name="category"
          >
            <template slot="title">
              <div class="category-header">
                <i class="el-icon-folder-opened"></i>
                <span class="category-title">{{ category }}</span>
                <el-tag size="mini" type="info" style="margin-left: 10px;">
                  {{ features.length }} 个因子
                </el-tag>
                <el-tag
                  size="mini"
                  type="success"
                  style="margin-left: 5px;"
                  v-if="getSelectedCountInCategory(features) > 0"
                >
                  已选 {{ getSelectedCountInCategory(features) }} 个
                </el-tag>
              </div>
            </template>

            <div class="feature-list">
              <div
                v-for="feature in features"
                :key="feature.key"
                class="feature-item"
                :class="{
                  'feature-selected': isFeatureSelected(feature.key),
                  'feature-recommended': feature.recommended
                }"
              >
                <el-checkbox
                  :value="isFeatureSelected(feature.key)"
                  @change="toggleFeature(feature.key)"
                  class="feature-checkbox"
                >
                  <span class="feature-name">
                    {{ feature.name }}
                    <el-tag v-if="feature.recommended" type="warning" size="mini" style="margin-left: 8px;">推荐</el-tag>
                  </span>
                </el-checkbox>

                <el-tooltip
                  :content="feature.description"
                  placement="top"
                  effect="light"
                  popper-class="feature-tooltip"
                >
                  <i class="el-icon-question feature-help-icon"></i>
                </el-tooltip>

                <div class="feature-description">
                  {{ feature.description }}
                </div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <span slot="footer" class="dialog-footer">
        <el-button @click="featureDialogVisible = false" size="medium">取消</el-button>
        <el-button type="primary" @click="applyFeatureSelection" size="medium">
          确定选择（{{ selectedFeatures.length }}）
        </el-button>
      </span>
    </el-dialog>

  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getKline, getstocklist } from '@/api/stock/kline'
import { getLstmFeatures, trainLstmModel, predictFuture, getModelInfo } from '@/api/stock/lstm'

function calculateMA(data, window) {
  return data.map((d, index) => {
    if (index < window - 1) return null
    const sum = data
      .slice(index - window + 1, index + 1)
      .reduce((a, b) => a + b.close, 0)
    return Number((sum / window).toFixed(2))
  })
}

export default {
  data() {
    const end = new Date()
    const start = new Date()
    start.setFullYear(start.getFullYear() - 3) // 1年数据

    const formatDate = (date) => {
      return date.toISOString().split('T')[0]
    }

    const defaultDateRange = [
      formatDate(start),
      formatDate(end)
    ]

    return {
      mockSymbols: [],
      loading: false,
      trainLoading: false,
      predictLoading: false,
      queryForm: {
        symbol: '600519',
        adjustType: 'normal',
        dateRange: defaultDateRange
      },
      chartInstance: null,
      rawData: [],
      lastSymbol: '',
      resizeTimer: null,
      updateTimer: null,

      // 训练配置（v7优化参数）
      trainConfig: {
        lookback_options: [30, 45, 60],  // v7: 聚焦中期窗口
        epochs: 150,  // v7: 减少轮次（从200降至150）
        batch_size: 32,  // v7: 增加批次大小（从16增至32）
        learning_rate: 0.0005,  // v7: 降低学习率（从0.001降至0.0005）
        test_size: 0.15,  // v7: 更严格的测试（从0.1增至0.15）
        validation_split: 0.2,
        use_sample_weights: true,
        sample_weight_decay: 0.997,  // v7: 更平衡（从0.9985改为0.997）
        future_steps: 20,
        // v7新增参数
        l2_reg: 0.001,  // L2正则化系数
        dropout_rate: 0.4,  // Dropout率
        use_directional_loss: true,  // 是否使用方向感知损失
        direction_alpha: 0.5  // 方向损失权重
      },

      // 训练结果
      trainResult: null,
      modelTrained: false,

      // 预测结果
      predictionResult: null,
      predictionViewMode: 'chart', // 预测结果展示模式：chart=图表, table=表格

      // 特征选择
      featureDialogVisible: false,
      featuresLoading: false,
      availableFeatures: {},
      selectedFeatures: [],
      activeCategories: [],

      // 训练对话框
      trainDialogVisible: false
    }
  },

  computed: {
    hasKlineData() {
      return this.rawData.length > 0
    },
    hasFeatureConfig() {
      return this.selectedFeatures.length > 0
    }
  },

  created() {
    this.loadStockList()
    this.loadFeatureConfig()
  },

  mounted() {
    this.initChart()
    this.loadData()
    window.addEventListener('resize', this.handleResize)
  },

  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize)

    // 清理所有计时器
    if (this.resizeTimer) {
      clearTimeout(this.resizeTimer)
    }
    if (this.updateTimer) {
      clearTimeout(this.updateTimer)
    }

    // 销毁图表实例
    if (this.chartInstance && !this.chartInstance.isDisposed()) {
      this.chartInstance.dispose()
    }
  },

  methods: {
    async loadStockList() {
      try {
        const response = await getstocklist()
        this.mockSymbols = response.data || []
      } catch (error) {
        console.error('股票列表加载失败:', error)
        this.$message.error('股票列表加载失败')
      }
    },

    handleSelectSymbol(item) {
      this.queryForm.symbol = item.symbol
      this.loadData()
    },

    async fetchSuggestions(queryString, cb) {
      try {
        const source = Array.isArray(this.mockSymbols) ? this.mockSymbols : []
        const results = source.filter(item => {
          if (!item || typeof item !== 'object') return false
          const symbol = String(item.symbol || '')
          const name = String(item.name || '')
          return symbol.includes(queryString) || name.includes(queryString)
        }).map(item => ({
          ...item,
          value: String(item.symbol || '')
        }))
        cb(results)
      } catch (error) {
        console.error('股票列表过滤出错:', error)
        cb([])
      }
    },

    handleSymbolInput(val) {
      if (val.length > 6) {
        this.queryForm.symbol = val.slice(0, 6)
        return
      }

      clearTimeout(this.debounceTimer)
      if (/^\d{6}$/.test(val)) {
        this.debounceTimer = setTimeout(() => {
          this.loadData()
        }, 800)
      }
    },

    saveSettings() {
      localStorage.setItem('lstmQuerySettings', JSON.stringify({
        symbol: this.queryForm.symbol,
        adjustType: this.queryForm.adjustType,
        dateRange: this.queryForm.dateRange
      }))
    },

    async loadData() {
      if (!this.validateSymbol()) return

      this.loading = true
      try {
        const { data } = await getKline(this.queryForm)
        if (data.length === 0) {
          this.$message.warning('未找到相关股票数据')
          return
        }

        this.rawData = data.sort((a, b) => new Date(a.date) - new Date(b.date))
        this.lastSymbol = this.queryForm.symbol
        this.saveSettings()
        this.updateChart()

        // 重置模型状态
        this.modelTrained = false
        this.trainResult = null
        this.predictionResult = null
      } catch (error) {
        this.handleError(error, '数据加载')
      } finally {
        this.loading = false
      }
    },

    validateSymbol() {
      if (!/^\d{6}$/.test(this.queryForm.symbol)) {
        this.$message.warning('请输入6位数字股票代码')
        return false
      }
      return true
    },

    handleError(error, action = '') {
      const defaultMsg = `${action}失败，请检查网络或输入`
      const message = error.response?.data?.message || error.message || defaultMsg
      this.$message.error(message)
    },

    handleEnterKey(event) {
      const activeElement = document.activeElement
      if (activeElement?.classList?.contains('el-autocomplete__input')) return

      if (this.queryForm.symbol && !this.loading) {
        this.loadData()
      }
    },

    handleResize() {
      if (this.resizeTimer) {
        clearTimeout(this.resizeTimer)
      }
      this.resizeTimer = setTimeout(() => {
        if (this.chartInstance && !this.chartInstance.isDisposed()) {
          try {
            this.chartInstance.resize()
          } catch (e) {
            console.warn('Chart resize error:', e)
          }
        }
      }, 100)
    },

    initChart() {
      try {
        // 如果已存在实例，先销毁
        if (this.chartInstance && !this.chartInstance.isDisposed()) {
          this.chartInstance.dispose()
        }

        this.chartInstance = echarts.init(this.$refs.chart)

        const option = {
          backgroundColor: '#fff',
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            confine: true  // 限制在图表区域内
          },
          legend: {
            data: ['K线', '成交量', 'MA5', 'MA10', 'MA20']
          },
          grid: [
            { left: '10%', right: '8%', height: '60%', top: '10%' },
            { left: '10%', right: '8%', top: '72%', height: '15%' }
          ],
          xAxis: [
            { type: 'category', boundaryGap: false, data: [] },
            { type: 'category', gridIndex: 1, data: [] }
          ],
          yAxis: [
            { scale: true },
            { scale: true, gridIndex: 1 }
          ],
          dataZoom: [
            { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
            { type: 'slider', xAxisIndex: [0, 1], bottom: 20, start: 0, end: 100 }
          ],
          series: [
            {
              name: 'K线',
              type: 'candlestick',
              itemStyle: {
                color: '#ef5350',
                color0: '#26a69a',
                borderColor: '#ef5350',
                borderColor0: '#26a69a'
              },
              data: []
            },
            {
              name: '成交量',
              type: 'bar',
              xAxisIndex: 1,
              yAxisIndex: 1,
              data: []
            },
            {
              name: 'MA5',
              type: 'line',
              smooth: true,
              showSymbol: false,
              lineStyle: { color: '#ff9800' },
              data: []
            },
            {
              name: 'MA10',
              type: 'line',
              smooth: true,
              showSymbol: false,
              lineStyle: { color: '#2196f3' },
              data: []
            },
            {
              name: 'MA20',
              type: 'line',
              smooth: true,
              showSymbol: false,
              lineStyle: { color: '#9c27b0' },
              data: []
            }
          ]
        }

        this.chartInstance.setOption(option)
      } catch (e) {
        console.error('Chart initialization error:', e)
        this.$message.error('图表初始化失败')
      }
    },

    updateChart() {
      if (!this.chartInstance || this.chartInstance.isDisposed() || this.rawData.length === 0) return

      // 清除之前的更新计时器
      if (this.updateTimer) {
        clearTimeout(this.updateTimer)
      }

      // 延迟执行，避免在渲染过程中重复调用
      this.updateTimer = setTimeout(() => {
        try {
          const candleData = this.rawData.map(d => [d.open, d.close, d.low, d.high])
          const volumeData = this.rawData.map(d => d.volume)
          const ma5Data = calculateMA(this.rawData, 5)
          const ma10Data = calculateMA(this.rawData, 10)
          const ma20Data = calculateMA(this.rawData, 20)
          const dates = this.rawData.map(d => d.date)

          const option = {
            xAxis: [{ data: dates }, { data: dates }],
            series: [
              { data: candleData },
              { data: volumeData },
              { data: ma5Data },
              { data: ma10Data },
              { data: ma20Data }
            ]
          }

          this.chartInstance.setOption(option)

          // 如果有预测结果，延迟更新预测展示
          if (this.predictionResult && this.predictionResult.predictions) {
            this.$nextTick(() => {
              this.updateChartWithPredictions()
            })
          }
        } catch (e) {
          console.warn('Chart update error:', e)
        }
      }, 50)
    },

    updateChartWithPredictions() {
      if (!this.chartInstance || this.chartInstance.isDisposed() || !this.predictionResult || !this.predictionResult.predictions) return

      try {
        // 合并历史日期和预测日期
        const historicalDates = this.rawData.map(d => d.date)
        const predictionDates = this.predictionResult.predictions.map(p => p.date)
        const allDates = [...historicalDates, ...predictionDates]

        // 历史K线数据
        const historicalCandles = this.rawData.map(d => [d.open, d.close, d.low, d.high])

         // 预测数据转换为K线格式（使用LSTM预测的开盘价和收盘价）
         const predictionCandles = this.predictionResult.predictions.map((p) => {
           // v7: LSTM模型同时预测开盘价和收盘价
           const open = p.predicted_open || p.predicted_price  // 兼容旧版本
           const close = p.predicted_close || p.predicted_price
           const high = p.predicted_high || Math.max(open, close) * 1.01
           const low = p.predicted_low || Math.min(open, close) * 0.99

           return [open, close, low, high]
         })

        // 合并所有K线数据（历史 + 预测）
        const allCandleData = [...historicalCandles, ...predictionCandles]

        // 创建预测收盘价线（连接历史最后一个点）
        const predictionCloseLine = new Array(historicalDates.length - 1).fill(null)
        predictionCloseLine.push(this.rawData[this.rawData.length - 1].close) // 连接点
        predictionCloseLine.push(...this.predictionResult.predictions.map(p => p.predicted_price))

        // 成交量数据（预测部分用历史平均值填充，设置为半透明）
        const avgVolume = this.rawData.slice(-20).reduce((sum, d) => sum + d.volume, 0) / 20
        const volumeData = this.rawData.map(d => d.volume)
        const predictionVolume = new Array(predictionDates.length).fill(avgVolume * 0.7)
        const allVolumes = [...volumeData, ...predictionVolume]

        // 获取复权类型说明
        const adjustTypeMap = {
          'qfq': '前复权',
          'hfq': '后复权',
          'normal': '不复权'
        }
        const adjustTypeText = adjustTypeMap[this.queryForm.adjustType] || this.queryForm.adjustType

        // 更新图表配置
        const option = {
          title: {
            text: `${this.queryForm.symbol} 历史行情与未来预测（${adjustTypeText}）`,
            subtext: `预测周期: ${predictionDates.length}天 | 趋势: ${this.predictionResult.trend === 'up' ? '看涨↑' : '看跌↓'} | 当前价格: ${this.predictionResult.current_price.toFixed(2)}元`,
            left: 'center',
            textStyle: {
              fontSize: 16,
              fontWeight: 'bold'
            },
            subtextStyle: {
              color: this.predictionResult.trend === 'up' ? '#67C23A' : '#F56C6C',
              fontSize: 14
            }
          },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          backgroundColor: 'rgba(255,255,255,0.95)',
          borderWidth: 1,
          borderColor: '#ccc',
          textStyle: { color: '#333' },
          formatter: (params) => {
            try {
              if (!params || !params[0]) return ''

              const dataIndex = params[0].dataIndex
              if (dataIndex < 0 || dataIndex >= allDates.length) return ''

              const date = allDates[dataIndex]
              const isHistorical = dataIndex < historicalDates.length

              if (isHistorical) {
                // 历史数据tooltip
                if (dataIndex >= this.rawData.length) return ''
                const data = this.rawData[dataIndex]
                if (!data) return ''

                return `
                  <div style="padding: 8px;">
                    <div style="font-weight: bold; margin-bottom: 8px; color: #409EFF;">
                      ${date} (历史数据)
                    </div>
                    开盘: ${data.open.toFixed(2)}<br/>
                    收盘: ${data.close.toFixed(2)}<br/>
                    最高: ${data.high.toFixed(2)}<br/>
                    最低: ${data.low.toFixed(2)}<br/>
                    成交量: ${data.volume.toLocaleString()}<br/>
                  </div>
                `
              } else {
                // 预测数据tooltip
                const predIndex = dataIndex - historicalDates.length
                if (predIndex < 0 || predIndex >= this.predictionResult.predictions.length) return ''

                const prediction = this.predictionResult.predictions[predIndex]
                const candleData = allCandleData[dataIndex]
                if (!prediction || !candleData) return ''

                return `
                  <div style="padding: 8px;">
                    <div style="font-weight: bold; margin-bottom: 8px; color: #E6A23C;">
                      ${date} (LSTM预测)
                    </div>
                    开盘(预测): <strong>${candleData[0].toFixed(2)}</strong><br/>
                    收盘(预测): <strong>${prediction.predicted_price.toFixed(2)}</strong><br/>
                    最高(估算): ${candleData[3].toFixed(2)}<br/>
                    最低(估算): ${candleData[2].toFixed(2)}<br/>
                    日涨跌幅: <span style="color: ${prediction.daily_change_pct > 0 ? '#67C23A' : '#F56C6C'}">
                      ${prediction.daily_change_pct > 0 ? '+' : ''}${prediction.daily_change_pct.toFixed(2)}%
                    </span><br/>
                    距今涨跌幅: <span style="color: ${prediction.total_change_pct > 0 ? '#67C23A' : '#F56C6C'}">
                      ${prediction.total_change_pct > 0 ? '+' : ''}${prediction.total_change_pct.toFixed(2)}%
                    </span><br/>
                    置信度: ${(prediction.confidence * 100).toFixed(1)}%<br/>
                  </div>
                `
              }
            } catch (e) {
              console.warn('Tooltip formatter error:', e)
              return ''
            }
          }
        },
        legend: {
          data: ['K线', '预测价格', '成交量', 'MA5', 'MA10', 'MA20'],
          top: 40
        },
        grid: [
          { left: '10%', right: '8%', height: '55%', top: '15%' },
          { left: '10%', right: '8%', top: '72%', height: '15%' }
        ],
        xAxis: [
          {
            data: allDates,
            axisLabel: {
              formatter: (value) => {
                // 标记预测区域
                if (predictionDates.includes(value)) {
                  return '{prediction|' + value.split('-').slice(1).join('-') + '}'
                }
                return value.split(' ')[0]
              },
              rich: {
                prediction: {
                  color: '#E6A23C',
                  fontWeight: 'bold'
                }
              }
            }
          },
          {
            data: allDates,
            gridIndex: 1,
            axisLabel: { show: false }
          }
        ],
        yAxis: [
          { scale: true },
          { scale: true, gridIndex: 1 }
        ],
        dataZoom: [
          { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
          { type: 'slider', xAxisIndex: [0, 1], bottom: 20, start: 0, end: 100 }
        ],
        series: [
          {
            name: 'K线',
            type: 'candlestick',
            data: allCandleData,
            itemStyle: {
              color: (params) => {
                const index = params.dataIndex
                // 预测数据使用半透明颜色
                if (index >= historicalDates.length) {
                  return 'rgba(239, 83, 80, 0.4)'
                }
                return '#ef5350'
              },
              color0: (params) => {
                const index = params.dataIndex
                if (index >= historicalDates.length) {
                  return 'rgba(38, 166, 154, 0.4)'
                }
                return '#26a69a'
              },
              borderColor: (params) => {
                const index = params.dataIndex
                if (index >= historicalDates.length) {
                  return 'rgba(239, 83, 80, 0.6)'
                }
                return '#ef5350'
              },
              borderColor0: (params) => {
                const index = params.dataIndex
                if (index >= historicalDates.length) {
                  return 'rgba(38, 166, 154, 0.6)'
                }
                return '#26a69a'
              },
              borderType: (params) => {
                const index = params.dataIndex
                // 预测数据使用虚线
                return index >= historicalDates.length ? 'dashed' : 'solid'
              }
            },
            markArea: {
              silent: true,
              itemStyle: {
                color: 'rgba(255, 173, 177, 0.1)'
              },
              data: [[
                {
                  xAxis: historicalDates[historicalDates.length - 1]
                },
                {
                  xAxis: predictionDates[predictionDates.length - 1]
                }
              ]],
              label: {
                show: true,
                position: 'insideTop',
                formatter: '预测区域',
                color: '#E6A23C',
                fontSize: 12
              }
            }
          },
          {
            name: '预测价格',
            type: 'line',
            data: predictionCloseLine,
            smooth: true,
            showSymbol: true,
            symbolSize: 6,
            lineStyle: {
              color: '#E6A23C',
              width: 3,
              type: 'dashed'
            },
            itemStyle: {
              color: '#E6A23C',
              borderColor: '#fff',
              borderWidth: 2
            },
            markPoint: {
              data: [
                {
                  name: '预测起点',
                  coord: [historicalDates.length - 1, this.rawData[this.rawData.length - 1].close],
                  symbol: 'pin',
                  symbolSize: 50,
                  itemStyle: { color: '#409EFF' },
                  label: {
                    formatter: '预测起点\n{c}',
                    fontSize: 12
                  }
                }
              ]
            }
          },
          {
            name: '成交量',
            type: 'bar',
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: allVolumes,
            itemStyle: {
              color: (params) => {
                const index = params.dataIndex
                // 历史成交量
                if (index < historicalDates.length) {
                  const data = this.rawData[index]
                  return data.close > data.open ? '#26a69a' : '#ef5350'
                }
                // 预测成交量（半透明灰色）
                return 'rgba(150, 150, 150, 0.3)'
              }
            }
          },
          {
            name: 'MA5',
            type: 'line',
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2, color: '#ff9800' },
            data: calculateMA(this.rawData, 5).concat(new Array(predictionDates.length).fill(null))
          },
          {
            name: 'MA10',
            type: 'line',
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2, color: '#2196f3' },
            data: calculateMA(this.rawData, 10).concat(new Array(predictionDates.length).fill(null))
          },
          {
            name: 'MA20',
            type: 'line',
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2, color: '#9c27b0' },
            data: calculateMA(this.rawData, 20).concat(new Array(predictionDates.length).fill(null))
          }
        ]
        }

        // 使用完全替换模式更新图表
        this.chartInstance.setOption(option, {
          notMerge: true,   // 完全替换，避免数据合并冲突
          lazyUpdate: false // 立即更新
        })
      } catch (e) {
        console.error('Update chart with predictions error:', e)
      }
    },

    // 训练相关方法
    showTrainDialog() {
      this.trainDialogVisible = true
    },

    handleTrainDialogClose() {
      this.trainDialogVisible = false
    },

    async handleTrain() {
      if (!this.hasKlineData) {
        this.$message.warning('请先加载股票数据')
        return
      }

      if (this.trainConfig.lookback_options.length === 0) {
        this.$message.warning('请至少选择一个回顾窗口选项')
        return
      }

      this.trainLoading = true
      this.trainDialogVisible = false

      try {
        const params = {
          symbol: this.lastSymbol,
          start_date: this.queryForm.dateRange[0],
          end_date: this.queryForm.dateRange[1],
          adjust_type: this.queryForm.adjustType, // 传递复权类型
          lookback_options: this.trainConfig.lookback_options,
          epochs: this.trainConfig.epochs,
          batch_size: this.trainConfig.batch_size,
          learning_rate: this.trainConfig.learning_rate,
          test_size: this.trainConfig.test_size,
          validation_split: this.trainConfig.validation_split,
          use_sample_weights: this.trainConfig.use_sample_weights,
          sample_weight_decay: this.trainConfig.sample_weight_decay,
          selected_features: this.selectedFeatures.length > 0 ? this.selectedFeatures : null,
          // v7新增参数
          l2_reg: this.trainConfig.l2_reg,
          dropout_rate: this.trainConfig.dropout_rate,
          use_directional_loss: this.trainConfig.use_directional_loss,
          direction_alpha: this.trainConfig.direction_alpha
        }

        const response = await trainLstmModel(params)

        if (response.code === 200 && response.data.success) {
          this.trainResult = response.data
          this.modelTrained = true
          this.$message.success('模型训练完成！')
        }
      } catch (error) {
        this.$message.error('模型训练失败: ' + (error.response?.data?.message || error.message))
      } finally {
        this.trainLoading = false
      }
    },

    async handlePredict() {
      if (!this.modelTrained) {
        this.$message.warning('请先训练模型')
        return
      }

      this.predictLoading = true

      try {
        const params = {
          symbol: this.lastSymbol,
          future_steps: this.trainConfig.future_steps
        }

        const response = await predictFuture(params)

        if (response.code === 200 && response.data.success) {
          this.predictionResult = response.data
          this.$message.success('预测完成！')

          // 延迟更新图表展示预测结果，避免渲染冲突
          this.$nextTick(() => {
            setTimeout(() => {
              this.updateChartWithPredictions()
            }, 100)
          })
        }
      } catch (error) {
        this.$message.error('预测失败: ' + (error.response?.data?.message || error.message))
      } finally {
        this.predictLoading = false
      }
    },

    // 特征选择相关方法
    async showFeatureDialog() {
      this.featureDialogVisible = true
      this.featuresLoading = true
      try {
        const response = await getLstmFeatures()
        if (response.data) {
          this.availableFeatures = response.data
          const categories = Object.keys(this.availableFeatures)
          if (categories.length > 0) {
            this.activeCategories = [categories[0]]
          }
          if (this.selectedFeatures.length === 0) {
            this.selectRecommendedFeatures()
          }
        }
      } catch (error) {
        this.$message.error('获取特征列表失败: ' + (error.response?.data?.message || error.message))
      } finally {
        this.featuresLoading = false
      }
    },

    selectAllFeatures() {
      const allFeatures = []
      Object.values(this.availableFeatures).forEach(features => {
        features.forEach(feature => {
          allFeatures.push(feature.key)
        })
      })
      this.selectedFeatures = allFeatures
    },

    selectRecommendedFeatures() {
      const recommendedFeatures = []
      Object.values(this.availableFeatures).forEach(features => {
        features.forEach(feature => {
          if (feature.recommended) {
            recommendedFeatures.push(feature.key)
          }
        })
      })
      this.selectedFeatures = recommendedFeatures
    },

    clearAllFeatures() {
      this.selectedFeatures = []
    },

    resetToDefault() {
      this.selectRecommendedFeatures()
      this.$message.success('已恢复推荐配置')
    },

    toggleFeature(featureKey) {
      const index = this.selectedFeatures.indexOf(featureKey)
      if (index > -1) {
        this.selectedFeatures.splice(index, 1)
      } else {
        this.selectedFeatures.push(featureKey)
      }
    },

    isFeatureSelected(featureKey) {
      return this.selectedFeatures.includes(featureKey)
    },

    getSelectedCountInCategory(features) {
      return features.filter(f => this.selectedFeatures.includes(f.key)).length
    },

    applyFeatureSelection() {
      if (this.selectedFeatures.length === 0) {
        this.$message.error('请至少选择1个训练因子')
        return
      }

      this.saveFeatureConfig()
      this.featureDialogVisible = false
      this.$message.success(`已保存因子配置！将使用 ${this.selectedFeatures.length} 个训练因子`)
    },

    handleFeatureDialogClose() {
      this.featureDialogVisible = false
    },

    loadFeatureConfig() {
      try {
        const savedConfig = localStorage.getItem('lstmFeatureConfig')
        if (savedConfig) {
          const config = JSON.parse(savedConfig)
          this.selectedFeatures = config.features || []
        }
      } catch (error) {
        console.error('加载因子配置失败:', error)
      }
    },

    saveFeatureConfig() {
      try {
        const config = {
          features: this.selectedFeatures,
          timestamp: Date.now()
        }
        localStorage.setItem('lstmFeatureConfig', JSON.stringify(config))
      } catch (error) {
        console.error('保存因子配置失败:', error)
      }
    },

    // 样式辅助方法
    getR2Style(r2) {
      if (typeof r2 !== 'number') return {}
      if (r2 >= 0.8) return { color: '#67C23A', fontWeight: 'bold' }
      if (r2 >= 0.5) return { color: '#E6A23C', fontWeight: 'bold' }
      return { color: '#F56C6C', fontWeight: 'bold' }
    },

    getChangeStyle(value) {
      if (value > 0) return { color: '#67C23A', fontWeight: 'bold' }
      if (value < 0) return { color: '#F56C6C', fontWeight: 'bold' }
      return {}
    },

    getConfidenceColor(confidence) {
      if (confidence >= 0.8) return '#67C23A'
      if (confidence >= 0.6) return '#E6A23C'
      return '#F56C6C'
    },

    // v7新增：方向准确率样式
    getDirectionAccuracyType(accuracy) {
      if (typeof accuracy !== 'number') return 'info'
      if (accuracy >= 60) return 'success'
      if (accuracy >= 50) return 'warning'
      return 'danger'
    },

    // v7新增：过拟合检查样式
    getOverfitType(penalty) {
      if (typeof penalty !== 'number') return 'success'
      if (penalty < 0.05) return 'success'
      if (penalty < 0.15) return 'warning'
      return 'danger'
    },

    getOverfitText(penalty) {
      if (typeof penalty !== 'number') return ''
      if (penalty < 0.05) return '✓ 正常'
      if (penalty < 0.15) return '⚠ 轻微'
      return '✗ 严重'
    },

    formatDate(dateStr) {
      return dateStr.split('T')[0]
    }
  }
}
</script>

<style scoped>
/* 复用 detail.vue 的样式，这里只列出主要样式 */
.app-container {
  background-color: #fff;
  padding: 20px;
  min-height: 100vh;
}

.chart-container {
  height: 700px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-top: 20px;
}

.status-alert {
  margin: 10px 0;
  padding: 8px 16px;
}

.result-card {
  margin-top: 20px;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.symbol-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
}

.symbol-code {
  color: #409EFF;
  font-weight: 600;
  margin-right: 15px;
}

.symbol-name {
  color: #606266;
}

/* 特征选择对话框样式 - 复用 detail.vue 的样式 */
.feature-selection-dialog ::v-deep .el-dialog__header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.feature-selection-dialog ::v-deep .el-dialog__title {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}

.feature-dialog-header {
  margin-bottom: 20px;
}

.selection-summary {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 6px;
}

.feature-content {
  max-height: 500px;
  overflow-y: auto;
}

.category-header {
  display: flex;
  align-items: center;
  width: 100%;
}

.category-title {
  flex: 1;
  margin-left: 8px;
}

.feature-list {
  padding: 12px 0;
}

.feature-item {
  padding: 12px 16px;
  margin-bottom: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  transition: all 0.3s;
  cursor: pointer;
  position: relative;
}

.feature-item:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.feature-item.feature-selected {
  border-color: #409EFF;
  background: #ecf5ff;
}

.feature-item.feature-recommended {
  border-color: #E6A23C;
  background: #fdf6ec;
}

.feature-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.feature-description {
  margin-top: 8px;
  padding-left: 24px;
  font-size: 13px;
  color: #606266;
}

.feature-help-icon {
  position: absolute;
  top: 14px;
  right: 16px;
  color: #909399;
  cursor: help;
}
</style>

