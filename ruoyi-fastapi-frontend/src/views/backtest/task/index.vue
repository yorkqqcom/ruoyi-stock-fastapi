<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
      <el-form-item label="任务名称" prop="taskName">
        <el-input
          v-model="queryParams.taskName"
          placeholder="请输入任务名称"
          clearable
          style="width: 200px"
          @keyup.enter="handleQuery"
        />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="queryParams.status" placeholder="请选择状态" clearable style="width: 200px">
          <el-option label="待执行" value="0" />
          <el-option label="执行中" value="1" />
          <el-option label="成功" value="2" />
          <el-option label="失败" value="3" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button
          type="primary"
          plain
          icon="Plus"
          @click="handleAdd"
          v-hasPermi="['backtest:task:create']"
        >新增回测任务</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="taskList">
      <el-table-column label="任务ID" width="80" align="center" prop="id" />
      <el-table-column label="任务名称" align="center" prop="taskName" :show-overflow-tooltip="true" />
      <el-table-column label="回测区间" align="center" :show-overflow-tooltip="true">
        <template #default="scope">
          <span v-if="scope.row.startDate && scope.row.endDate">
            {{ scope.row.startDate }} ~ {{ scope.row.endDate }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="状态" align="center" width="100">
        <template #default="scope">
          <el-tag v-if="scope.row.status === '0'" type="info">待执行</el-tag>
          <el-tag v-else-if="scope.row.status === '1'" type="warning">执行中</el-tag>
          <el-tag v-else-if="scope.row.status === '2'" type="success">成功</el-tag>
          <el-tag v-else-if="scope.row.status === '3'" type="danger">失败</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" align="center" width="100">
        <template #default="scope">
          <el-progress :percentage="scope.row.progress || 0" :status="scope.row.status === '3' ? 'exception' : undefined" />
        </template>
      </el-table-column>
      <el-table-column label="关键指标" align="center" width="300" v-if="taskList.some(item => item.result)">
        <template #default="scope">
          <div v-if="scope.row.result">
            <span>总收益: {{ (scope.row.result.totalReturn * 100).toFixed(2) }}%</span><br>
            <span>年化: {{ (scope.row.result.annualReturn * 100).toFixed(2) }}%</span>
            <span style="margin-left: 10px;">回撤: {{ (scope.row.result.maxDrawdown * 100).toFixed(2) }}%</span><br>
            <span>夏普: {{ scope.row.result.sharpeRatio?.toFixed(2) || '-' }}</span>
            <span style="margin-left: 10px;">交易: {{ scope.row.result.tradeCount || 0 }}次</span>
          </div>
          <span v-else style="color: #909399;">暂无结果</span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" align="center" prop="createTime" width="180">
        <template #default="scope">
          <span v-if="scope.row.createTime">{{ parseTime(scope.row.createTime) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="center" width="200" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-tooltip content="查看详情" placement="top">
            <el-button
              link
              type="primary"
              icon="View"
              @click="handleView(scope.row)"
              v-hasPermi="['backtest:task:query']"
            />
          </el-tooltip>
          <el-tooltip content="查看结果" placement="top" v-if="scope.row.status === '2'">
            <el-button
              link
              type="success"
              icon="DataAnalysis"
              @click="handleViewResult(scope.row)"
              v-hasPermi="['backtest:result:query']"
            />
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>

    <pagination
      v-show="total > 0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="getList"
    />

    <!-- 添加回测任务对话框 -->
    <el-dialog :title="title" v-model="open" width="900px" append-to-body>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="任务名称" prop="taskName">
          <el-input v-model="form.taskName" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="信号来源" prop="signalSourceType">
          <el-select v-model="form.signalSourceType" placeholder="请选择信号来源" @change="onSignalSourceChange">
            <el-option label="预测表（离线）" value="predict_table" />
            <el-option label="在线模型" value="online_model" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择模型" prop="resultId" v-if="form.signalSourceType">
          <el-select v-model="form.resultId" placeholder="请选择训练结果" filterable style="width: 100%">
            <el-option
              v-for="item in modelResultList"
              :key="item.id"
              :label="`${item.taskName} (v${item.version}) | Acc ${item.accuracy ? (item.accuracy * 100).toFixed(1) : 'N/A'}%`"
              :value="item.id"
            />
          </el-select>
          <span style="margin-left: 10px; color: #909399;">仅展示训练成功的模型结果</span>
        </el-form-item>
        <el-form-item label="标的列表" prop="symbolList">
          <el-input
            v-model="form.symbolList"
            type="textarea"
            :rows="3"
            placeholder="留空表示全部可用个股；如需限制范围，请输入股票代码（逗号分隔），例如：000001.SZ,000002.SZ"
          />
          <span style="margin-top: 4px; display: block; color: #909399; font-size: 12px;">
            若不填写，则自动根据模型在所选日期范围内可用的数据回测全部相关个股。
          </span>
        </el-form-item>
        <el-form-item label="回测区间" prop="startDate">
          <el-col :span="11">
            <el-form-item prop="startDate">
              <el-date-picker
                v-model="form.startDate"
                type="date"
                placeholder="开始日期"
                format="YYYYMMDD"
                value-format="YYYYMMDD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="2" class="text-center">
            <span class="text-gray-500">-</span>
          </el-col>
          <el-col :span="11">
            <el-form-item prop="endDate">
              <el-date-picker
                v-model="form.endDate"
                type="date"
                placeholder="结束日期"
                format="YYYYMMDD"
                value-format="YYYYMMDD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-form-item>
        <el-form-item label="初始资金" prop="initialCash">
          <el-input-number v-model="form.initialCash" :min="1000" :step="10000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最大仓位" prop="maxPosition">
          <el-input-number v-model="form.maxPosition" :min="0" :max="1" :step="0.1" style="width: 100%" />
          <span style="margin-left: 10px; color: #909399;">0~1，1表示满仓</span>
        </el-form-item>
        <el-form-item label="手续费率" prop="commissionRate">
          <el-input-number v-model="form.commissionRate" :min="0" :max="0.01" :step="0.0001" style="width: 100%" />
          <span style="margin-left: 10px; color: #909399;">默认0.0003（万三）</span>
        </el-form-item>
        <el-form-item label="买入阈值" prop="signalBuyThreshold">
          <el-input-number v-model="form.signalBuyThreshold" :min="0" :max="1" :step="0.1" style="width: 100%" />
          <span style="margin-left: 10px; color: #909399;">predict_prob需大于此值才买入</span>
        </el-form-item>
        <el-form-item label="卖出阈值" prop="signalSellThreshold">
          <el-input-number v-model="form.signalSellThreshold" :min="0" :max="1" :step="0.1" style="width: 100%" />
          <span style="margin-left: 10px; color: #909399;">predict_prob需小于此值才卖出</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="BacktestTask">
import { listBacktestTask, createBacktestTask, getBacktestTaskDetail } from '@/api/backtest/index'
import { listModelTrainResult } from '@/api/factor/model'
import { getCurrentInstance } from 'vue'
import { useRouter } from 'vue-router'

const { proxy } = getCurrentInstance()
const router = useRouter()

const taskList = ref([])
const open = ref(false)
const loading = ref(true)
const showSearch = ref(true)
const total = ref(0)
const title = ref('')
const modelResultList = ref([])

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    taskName: undefined,
    status: undefined
  },
  rules: {
    taskName: [{ required: true, message: '任务名称不能为空', trigger: 'blur' }],
    resultId: [{ required: true, message: '请选择模型', trigger: 'change' }],
    // symbolList 可为空，留空表示“全部可用个股”
    startDate: [{ required: true, message: '开始日期不能为空', trigger: 'change' }],
    endDate: [{ required: true, message: '结束日期不能为空', trigger: 'change' }],
    signalSourceType: [{ required: true, message: '信号来源不能为空', trigger: 'change' }]
  }
})

const { queryParams, form, rules } = toRefs(data)

/** 查询回测任务列表 */
function getList() {
  loading.value = true
  listBacktestTask(queryParams.value).then((response) => {
    taskList.value = response.rows || []
    total.value = response.total || 0
    loading.value = false
  }).catch(() => {
    loading.value = false
  })
}

/** 搜索按钮操作 */
function handleQuery() {
  queryParams.value.pageNum = 1
  getList()
}

/** 重置按钮操作 */
function resetQuery() {
  proxy.resetForm('queryRef')
  handleQuery()
}

/** 新增按钮操作 */
function handleAdd() {
  reset()
  loadModelResultList()
  open.value = true
  title.value = '新增回测任务'
}

/** 加载模型训练结果列表（仅成功的最新结果） */
function loadModelResultList() {
  listModelTrainResult({
    pageNum: 1,
    pageSize: 50,
    status: '0'
  }).then((response) => {
    modelResultList.value = response.rows || []
  }).catch(() => {
    modelResultList.value = []
  })
}

/** 查看详情 */
function handleView(row) {
  router.push(`/backtest/task/detail/${row.id}`)
}

/** 查看结果 */
function handleViewResult(row) {
  router.push(`/backtest/result/detail/${row.id}`)
}

/** 信号来源变化 */
function onSignalSourceChange() {
  // 可以在这里添加逻辑
}

/** 提交按钮 */
function submitForm() {
  proxy.$refs['formRef'].validate((valid) => {
    if (valid) {
      createBacktestTask(form.value).then((response) => {
        proxy.$modal.msgSuccess('回测任务已创建并启动')
        open.value = false
        getList()
      })
    }
  })
}

/** 取消按钮 */
function cancel() {
  open.value = false
  reset()
}

/** 表单重置 */
function reset() {
  form.value = {
    taskName: undefined,
    signalSourceType: 'predict_table',
    resultId: undefined,
    symbolList: undefined,
    startDate: undefined,
    endDate: undefined,
    initialCash: 1000000,
    maxPosition: 1.0,
    commissionRate: 0.0003,
    slippageBp: 0,
    signalBuyThreshold: 0.6,
    signalSellThreshold: 0.4,
    positionMode: 'equal_weight'
  }
  proxy.resetForm('formRef')
}

getList()
</script>
