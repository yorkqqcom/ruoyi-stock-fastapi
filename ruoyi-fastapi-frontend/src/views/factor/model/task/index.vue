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
          <el-option label="待训练" value="0" />
          <el-option label="训练中" value="1" />
          <el-option label="训练完成" value="2" />
          <el-option label="训练失败" value="3" />
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
          v-hasPermi="['factor:model:train']"
        >新增训练任务</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="danger"
          plain
          icon="Delete"
          :disabled="multiple"
          @click="handleDelete"
          v-hasPermi="['factor:model:task:remove']"
        >删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="taskList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="任务ID" width="80" align="center" prop="id" />
      <el-table-column label="任务名称" align="center" prop="taskName" :show-overflow-tooltip="true" />
      <el-table-column label="因子代码" align="center" prop="factorCodes" :show-overflow-tooltip="true" />
      <el-table-column label="日期范围" align="center" :show-overflow-tooltip="true">
        <template #default="scope">
          <span v-if="scope.row.startDate && scope.row.endDate">
            {{ scope.row.startDate }} ~ {{ scope.row.endDate }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="状态" align="center" width="100">
        <template #default="scope">
          <el-tag v-if="scope.row.status === '0'" type="info">待训练</el-tag>
          <el-tag v-else-if="scope.row.status === '1'" type="warning">训练中</el-tag>
          <el-tag v-else-if="scope.row.status === '2'" type="success">训练完成</el-tag>
          <el-tag v-else-if="scope.row.status === '3'" type="danger">训练失败</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="运行统计" align="center" width="160">
        <template #default="scope">
          <span>运行: {{ scope.row.runCount || 0 }}</span>
          <span style="margin-left: 8px; color: #67c23a;">成: {{ scope.row.successCount || 0 }}</span>
          <span style="margin-left: 8px; color: #f56c6c;">败: {{ scope.row.failCount || 0 }}</span>
        </template>
      </el-table-column>
      <el-table-column label="最后运行" align="center" prop="lastRunTime" width="180">
        <template #default="scope">
          <span v-if="scope.row.lastRunTime">{{ parseTime(scope.row.lastRunTime) }}</span>
          <span v-else style="color: #909399;">未运行</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="center" width="300" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-tooltip content="编辑" placement="top" v-if="scope.row.status !== '1'">
            <el-button
              link
              type="primary"
              icon="Edit"
              @click="handleUpdate(scope.row)"
              v-hasPermi="['factor:model:task:edit']"
            />
          </el-tooltip>
          <el-tooltip content="执行训练" placement="top" v-if="scope.row.status === '0' || scope.row.status === '3'">
            <el-button
              link
              type="success"
              icon="VideoPlay"
              @click="handleExecute(scope.row)"
              v-hasPermi="['factor:model:task:execute']"
            />
          </el-tooltip>
          <el-tooltip content="删除" placement="top">
            <el-button
              link
              type="danger"
              icon="Delete"
              @click="handleDelete(scope.row)"
              v-hasPermi="['factor:model:task:remove']"
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

    <!-- 添加或修改训练任务对话框 -->
    <el-dialog :title="title" v-model="open" width="900px" append-to-body>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="任务名称" prop="taskName">
          <el-input v-model="form.taskName" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="因子配置文件" prop="factorConfigPath">
          <el-select
            v-model="form.factorConfigPath"
            placeholder="请选择因子配置文件"
            clearable
            filterable
            style="width: 100%"
            @change="onFactorConfigChange"
          >
            <el-option
              v-for="item in factorConfigList"
              :key="item.path"
              :label="item.name + ' (' + item.factorCount + ' 个因子)'"
              :value="item.path"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="因子代码列表" prop="factorCodes">
          <el-input
            v-model="form.factorCodes"
            type="textarea"
            :rows="3"
            readonly
            placeholder="选择因子配置文件后自动带出，或编辑任务时显示已保存的因子列表"
          />
        </el-form-item>
        <el-form-item label="标的范围(JSON)" prop="symbolUniverse">
          <el-input
            v-model="form.symbolUniverse"
            type="textarea"
            :rows="3"
            placeholder='如：["000001.SZ","000002.SZ"] 或留空表示全部'
          />
        </el-form-item>
        <el-row>
          <el-col :span="12">
            <el-form-item label="开始日期" prop="startDate">
              <el-date-picker
                v-model="form.startDate"
                type="date"
                placeholder="选择开始日期"
                value-format="YYYYMMDD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期" prop="endDate">
              <el-date-picker
                v-model="form.endDate"
                type="date"
                placeholder="选择结束日期"
                value-format="YYYYMMDD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="模型参数(JSON)" prop="modelParams">
          <el-input
            v-model="form.modelParams"
            type="textarea"
            :rows="4"
            placeholder='如：{"n_estimators": 100, "max_depth": 10, "min_samples_split": 2}'
          />
        </el-form-item>
        <el-form-item label="训练集比例" prop="trainTestSplit">
          <el-input-number v-model="form.trainTestSplit" :min="0.5" :max="0.95" :step="0.05" :precision="2" />
          <span style="margin-left: 10px; color: #909399;">默认0.8（80%训练，20%测试）</span>
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

<script setup name="ModelTrainTask">
import { listModelTrainTask, getModelTrainTask, trainModel, editModelTrainTask, delModelTrainTask, executeModelTrainTask } from '@/api/factor/model'
import { listFactorConfig, getFactorConfigContent } from '@/api/factor/config'

const { proxy } = getCurrentInstance()

const taskList = ref([])
const open = ref(false)
const loading = ref(true)
const showSearch = ref(true)
const ids = ref([])
const single = ref(true)
const multiple = ref(true)
const total = ref(0)
const title = ref('')
const factorConfigList = ref([])

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
    factorCodes: [{ required: true, message: '因子代码列表不能为空', trigger: 'blur' }],
    startDate: [{ required: true, message: '开始日期不能为空', trigger: 'change' }],
    endDate: [{ required: true, message: '结束日期不能为空', trigger: 'change' }]
  }
})

const { queryParams, form, rules } = toRefs(data)

/** 查询模型训练任务列表 */
function getList() {
  loading.value = true
  listModelTrainTask(queryParams.value).then((response) => {
    taskList.value = response.rows
    total.value = response.total
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
/** 多选框选中数据 */
function handleSelectionChange(selection) {
  ids.value = selection.map((item) => item.id)
  single.value = selection.length !== 1
  multiple.value = !selection.length
}
/** 新增按钮操作 */
function handleAdd() {
  reset()
  loadFactorConfigList()
  open.value = true
  title.value = '新增模型训练任务'
}

/** 加载因子配置文件列表 */
function loadFactorConfigList() {
  listFactorConfig().then((response) => {
    factorConfigList.value = response.data || []
  }).catch(() => {})
}

/** 选择因子配置文件后拉取内容并填入 factorCodes */
function onFactorConfigChange(path) {
  if (!path) {
    form.value.factorCodes = undefined
    return
  }
  getFactorConfigContent(path).then((response) => {
    form.value.factorCodes = response.data?.factorCodes || ''
  }).catch(() => {
    proxy.$modal.msgError('获取配置内容失败')
    form.value.factorCodes = undefined
  })
}

/** 修改按钮操作 */
function handleUpdate(row) {
  reset()
  loadFactorConfigList()
  const taskId = row.id || ids.value
  getModelTrainTask(taskId).then((response) => {
    form.value = response.data
    open.value = true
    title.value = '修改模型训练任务'
  })
}
/** 提交按钮 */
function submitForm() {
  proxy.$refs['formRef'].validate((valid) => {
    if (valid) {
      if (form.value.id !== undefined) {
        // 编辑模式
        editModelTrainTask(form.value).then((response) => {
          proxy.$modal.msgSuccess('编辑成功')
          open.value = false
          getList()
        })
      } else {
        // 新增模式
        trainModel(form.value).then((response) => {
          proxy.$modal.msgSuccess('训练任务已创建并启动')
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
    factorConfigPath: undefined,
    factorCodes: undefined,
    symbolUniverse: undefined,
    startDate: undefined,
    endDate: undefined,
    modelParams: '{"n_estimators": 100, "max_depth": 10, "min_samples_split": 2}',
    trainTestSplit: 0.8
  }
  proxy.resetForm('formRef')
}
/** 执行训练任务 */
function handleExecute(row) {
  proxy.$modal
    .confirm('是否确认执行模型训练任务"' + row.taskName + '"？')
    .then(function () {
      return executeModelTrainTask(row.id)
    })
    .then(() => {
      proxy.$modal.msgSuccess('训练任务已提交后台执行')
      getList()
    })
    .catch(() => {})
}

/** 删除按钮操作 */
function handleDelete(row) {
  const taskIds = row.id || ids.value
  proxy.$modal
    .confirm('是否确认删除模型训练任务编号为"' + taskIds + '"的数据项？')
    .then(function () {
      return delModelTrainTask(taskIds)
    })
    .then(() => {
      getList()
      proxy.$modal.msgSuccess('删除成功')
    })
    .catch(() => {})
}

getList()
</script>
