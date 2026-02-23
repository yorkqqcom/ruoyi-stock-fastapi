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
          <el-tooltip content="编辑" placement="top" v-if="scope.row.status === '0' || scope.row.status === '3'">
            <el-button
              link
              type="primary"
              icon="Edit"
              @click="handleEdit(scope.row)"
              v-hasPermi="['backtest:task:create']"
            />
          </el-tooltip>
          <el-tooltip
            :content="getExecuteTooltip(scope.row)"
            placement="top"
            v-if="scope.row.status === '0' || scope.row.status === '3'"
          >
            <span>
              <el-button
                link
                type="warning"
                icon="VideoPlay"
                :disabled="isTaskWithoutModel(scope.row)"
                @click="handleExecute(scope.row)"
                v-hasPermi="['backtest:task:create']"
              />
            </span>
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
          <el-tooltip content="删除" placement="top">
            <el-button
              link
              type="danger"
              icon="Delete"
              @click="handleDelete(scope.row)"
              v-hasPermi="['backtest:task:remove']"
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

    <!-- 添加/编辑回测任务对话框 -->
    <el-dialog :title="title" v-model="open" width="980px" append-to-body class="backtest-dialog">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" class="backtest-form">
        <!-- 基础信息 -->
        <div class="form-section">
          <div class="form-section-title">基础信息</div>
          <el-row :gutter="20">
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="任务名称" prop="taskName">
                <el-input v-model="form.taskName" placeholder="请输入任务名称" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="信号来源" prop="signalSourceType">
                <el-select v-model="form.signalSourceType" placeholder="请选择信号来源" @change="onSignalSourceChange" style="width: 100%">
                  <el-option label="预测表（离线）" value="predict_table" />
                  <el-option label="在线模型" value="online_model" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="选择模型" prop="resultId" v-if="form.signalSourceType">
            <el-select v-model="form.resultId" placeholder="请选择训练结果" filterable style="width: 100%">
              <el-option
                v-for="item in modelResultList"
                :key="item.id"
                :label="`${item.taskName} (v${item.version}) | Acc ${item.accuracy ? (item.accuracy * 100).toFixed(1) : 'N/A'}%`"
                :value="item.id"
              />
            </el-select>
            <div class="form-hint">仅展示训练成功的模型结果</div>
          </el-form-item>
          <el-form-item label="标的列表" prop="symbolList">
            <el-input
              v-model="form.symbolList"
              type="textarea"
              :rows="2"
              placeholder="留空表示全部可用个股；如需限制范围，请输入股票代码（逗号分隔），例如：000001.SZ,000002.SZ"
            />
            <div class="form-hint">
              <template v-if="form.signalSourceType === 'online_model'">
                在线模式下留空表示使用当日 K 线中的全部标的；仅同时具备 K 线与因子数据的标的会产生信号。
              </template>
              <template v-else>
                若不填写，则自动根据模型在所选日期范围内可用的数据回测全部相关个股。
              </template>
            </div>
          </el-form-item>
        </div>

        <!-- 回测区间与资金 -->
        <div class="form-section">
          <div class="form-section-title">回测区间与资金</div>
          <el-row :gutter="20">
            <el-col :xs="24" :sm="12" :md="12">
              <el-form-item label="开始日期" prop="startDate">
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
            <el-col :xs="24" :sm="12" :md="12">
              <el-form-item label="结束日期" prop="endDate">
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
          </el-row>
          <el-row :gutter="20">
            <el-col :xs="24" :sm="24" :md="8">
              <el-form-item label="初始资金" prop="initialCash">
                <el-input-number v-model="form.initialCash" :min="1000" :step="10000" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="24" :md="8">
              <el-form-item label="最大仓位" prop="maxPosition">
                <el-input-number v-model="form.maxPosition" :min="0" :max="1" :step="0.1" style="width: 100%" />
                <div class="form-hint">0~1，1表示满仓</div>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="24" :md="8">
              <el-form-item label="手续费率" prop="commissionRate">
                <el-input-number v-model="form.commissionRate" :min="0" :max="0.01" :step="0.0001" style="width: 100%" />
                <div class="form-hint">默认0.0003（万三）</div>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 信号与阈值 -->
        <div class="form-section">
          <div class="form-section-title">信号与阈值</div>
          <el-row :gutter="20">
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="买入阈值" prop="signalBuyThreshold">
                <el-input-number v-model="form.signalBuyThreshold" :min="0" :max="1" :step="0.1" style="width: 100%" />
                <div class="form-hint">predict_prob需大于此值才买入</div>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="卖出阈值" prop="signalSellThreshold">
                <el-input-number v-model="form.signalSellThreshold" :min="0" :max="1" :step="0.1" style="width: 100%" />
                <div class="form-hint">predict_prob需小于此值才卖出</div>
              </el-form-item>
            </el-col>
          </el-row>
        </div>
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
import { listBacktestTask, createBacktestTask, updateBacktestTask, executeBacktestTask, getBacktestTaskDetail, deleteBacktestTask } from '@/api/backtest/index'
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
const formRef = ref(null)

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
    resultId: [
      {
        validator: (rule, value, callback) => {
          const t = data.form.signalSourceType
          if (t === 'predict_table' || t === 'online_model') {
            if (value === undefined || value === null || value === '') {
              callback(new Error('请选择模型（离线/在线模式必选）'))
            } else {
              callback()
            }
          } else {
            callback()
          }
        },
        trigger: 'change'
      }
    ],
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

/** 是否未配置模型（不可执行），与后端执行前校验规则一致 */
function isTaskWithoutModel(row) {
  if (!row) return true
  const st = row.signalSourceType
  const hasResultId = row.resultId != null && row.resultId !== '' && Number(row.resultId) > 0
  const hasPredictTaskId = row.predictTaskId != null && row.predictTaskId !== '' && Number(row.predictTaskId) > 0
  const hasModelSceneBindingId = row.modelSceneBindingId != null && row.modelSceneBindingId !== '' && Number(row.modelSceneBindingId) > 0
  if (st === 'predict_table') return !hasResultId && !hasPredictTaskId
  if (st === 'online_model') return !hasResultId && !hasModelSceneBindingId
  return false
}

/** 执行按钮的提示文案：与后端错误消息保持一致，并给出修复建议 */
function getExecuteTooltip(row) {
  if (!row) return ''
  if (isTaskWithoutModel(row)) {
    if (row.signalSourceType === 'online_model') {
      return '该任务未配置模型或场景绑定，无法执行。请删除后重新创建并选择模型。'
    }
    // 默认视为离线预测表模式
    return '该任务未配置模型或预测任务，无法执行。请删除后重新创建并选择模型。'
  }
  return row.status === '3' ? '重新执行' : '执行'
}

/** 执行/重新执行 */
function handleExecute(row) {
  if (isTaskWithoutModel(row)) return
  proxy.$modal.confirm(
    row.status === '3' ? '是否重新执行该回测任务？' : '是否立即执行该回测任务？'
  ).then(() => {
    return executeBacktestTask(row.id)
  }).then((response) => {
    proxy.$modal.msgSuccess(response.msg || '已触发执行')
    getList()
  }).catch(() => {})
}

/** 编辑按钮操作 */
function handleEdit(row) {
  reset()
  loadModelResultList()
  getBacktestTaskDetail(row.id).then((response) => {
    const d = response.data || response
    const detailResultId = d.resultId
    const normalizedResultId = detailResultId !== undefined && detailResultId !== null && detailResultId !== '' ? Number(detailResultId) : undefined
    const normalizedPredictTaskId = d.predictTaskId !== undefined && d.predictTaskId !== null && d.predictTaskId !== '' ? Number(d.predictTaskId) : undefined
    const normalizedModelSceneBindingId = d.modelSceneBindingId !== undefined && d.modelSceneBindingId !== null && d.modelSceneBindingId !== '' ? Number(d.modelSceneBindingId) : undefined
    form.value = {
      id: d.id,
      taskName: d.taskName ?? '',
      signalSourceType: d.signalSourceType ?? 'predict_table',
      resultId: normalizedResultId,
      predictTaskId: normalizedPredictTaskId,
      modelSceneBindingId: normalizedModelSceneBindingId,
      symbolList: d.symbolList ?? '',
      startDate: d.startDate ?? '',
      endDate: d.endDate ?? '',
      initialCash: d.initialCash ?? 1000000,
      maxPosition: d.maxPosition ?? 1.0,
      commissionRate: d.commissionRate ?? 0.0003,
      slippageBp: d.slippageBp ?? 0,
      signalBuyThreshold: d.signalBuyThreshold ?? 0.6,
      signalSellThreshold: d.signalSellThreshold ?? 0.4,
      positionMode: d.positionMode ?? 'equal_weight'
    }
    title.value = '编辑回测任务'
    open.value = true
  }).catch(() => {})
}

/** 查看详情 */
function handleView(row) {
  router.push(`/backtest/task/detail/${row.id}`)
}

/** 查看结果 */
function handleViewResult(row) {
  router.push(`/backtest/result/detail/${row.id}`)
}

/** 删除 */
function handleDelete(row) {
  if (row.status === '1') {
    proxy.$modal.msgWarning('任务正在执行中，请等待执行完成后再删除')
    return
  }
  proxy.$modal.confirm('是否确认删除该回测任务？删除后将同时删除其关联的交易明细、净值与结果数据。').then(() => {
    return deleteBacktestTask(row.id)
  }).then((response) => {
    proxy.$modal.msgSuccess(response.msg || '删除成功')
    getList()
  }).catch(() => {})
}

/** 信号来源变化时重新校验「选择模型」 */
function onSignalSourceChange() {
  formRef.value?.validateField('resultId', () => {})
}

/** 将表单中的 ID 转为数字或 null，与后端 VO 类型一致 */
function toOptionalId(v) {
  if (v === undefined || v === null || v === '') return null
  const n = Number(v)
  return Number.isNaN(n) ? null : n
}

/** 提交按钮 */
function submitForm() {
  formRef.value?.validate((valid) => {
    if (valid) {
      // 调试：打印当前表单值，关注 resultId / predictTaskId / modelSceneBindingId
      // 注意：仅用于排查问题，确认无误后可删除
      // eslint-disable-next-line no-console
      console.log('[BacktestTask] submitForm 原始 form:', JSON.parse(JSON.stringify(form.value || {})))
      const payload = {
        taskName: form.value.taskName ?? '',
        signalSourceType: form.value.signalSourceType ?? 'predict_table',
        resultId: toOptionalId(form.value.resultId),
        predictTaskId: toOptionalId(form.value.predictTaskId),
        modelSceneBindingId: toOptionalId(form.value.modelSceneBindingId),
        symbolList: form.value.symbolList ?? '',
        startDate: form.value.startDate ?? '',
        endDate: form.value.endDate ?? '',
        initialCash: form.value.initialCash,
        maxPosition: form.value.maxPosition,
        commissionRate: form.value.commissionRate,
        slippageBp: form.value.slippageBp,
        signalBuyThreshold: form.value.signalBuyThreshold,
        signalSellThreshold: form.value.signalSellThreshold,
        positionMode: form.value.positionMode
      }
      // 将值为 null 或 undefined 的可选字段从 payload 中剔除，避免在控制台看到多余的 null，
      // 同时保持与后端「可选字段缺省」的语义一致
      Object.keys(payload).forEach((key) => {
        if (payload[key] === null || payload[key] === undefined) {
          delete payload[key]
        }
      })
      // 调试：打印最终请求 payload，确认三个 ID 字段在前端是否为 null/数字
      // eslint-disable-next-line no-console
      console.log('[BacktestTask] submitForm 组装 payload:', payload)
      if (form.value.id) {
        // eslint-disable-next-line no-console
        console.log('[BacktestTask] 调用 updateBacktestTask，taskId=', form.value.id)
        updateBacktestTask(form.value.id, payload).then((response) => {
          // eslint-disable-next-line no-console
          console.log('[BacktestTask] updateBacktestTask 响应:', response)
          proxy.$modal.msgSuccess(response.msg || '任务已更新')
          open.value = false
          getList()
        })
      } else {
        // eslint-disable-next-line no-console
        console.log('[BacktestTask] 调用 createBacktestTask，payload=', payload)
        createBacktestTask(payload).then((response) => {
          // eslint-disable-next-line no-console
          console.log('[BacktestTask] createBacktestTask 响应:', response)
          proxy.$modal.msgSuccess(response.msg || '回测任务已创建，请点击任务运行按钮执行')
          open.value = false
          getList()
        })
      }
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
    id: undefined,
    taskName: undefined,
    signalSourceType: 'predict_table',
    resultId: undefined,
    predictTaskId: undefined,
    modelSceneBindingId: undefined,
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
  formRef.value?.resetFields()
}

getList()
</script>

<style scoped lang="scss">
.form-section {
  margin-bottom: 18px;
  padding: 16px 20px 12px;
  border-radius: 8px;
  background-color: #fff;
  border: 1px solid var(--el-border-color-lighter);
  &:last-of-type {
    margin-bottom: 0;
  }
}
.form-section-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.form-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
.backtest-form {
  max-height: 70vh;
  overflow-y: auto;
}
.backtest-dialog {
  :deep(.el-dialog__body) {
    padding: 16px 24px 12px;
    background-color: #f5f7fa;
  }
}
</style>
