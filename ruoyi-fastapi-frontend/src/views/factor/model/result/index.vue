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
          <el-option label="成功" value="0" />
          <el-option label="失败" value="1" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="resultList">
      <el-table-column label="结果ID" width="80" align="center" prop="id" />
      <el-table-column label="版本" width="80" align="center" prop="version" />
      <el-table-column label="任务名称" align="center" prop="taskName" :show-overflow-tooltip="true" />
      <el-table-column label="准确率" align="center" width="100">
        <template #default="scope">
          <span v-if="scope.row.accuracy">{{ (scope.row.accuracy * 100).toFixed(2) }}%</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="精确率" align="center" width="100">
        <template #default="scope">
          <span v-if="scope.row.precisionScore">{{ (scope.row.precisionScore * 100).toFixed(2) }}%</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="召回率" align="center" width="100">
        <template #default="scope">
          <span v-if="scope.row.recallScore">{{ (scope.row.recallScore * 100).toFixed(2) }}%</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="F1分数" align="center" width="100">
        <template #default="scope">
          <span v-if="scope.row.f1Score">{{ (scope.row.f1Score * 100).toFixed(2) }}%</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="训练样本数" align="center" width="120" prop="trainSamples" />
      <el-table-column label="测试样本数" align="center" width="120" prop="testSamples" />
      <el-table-column label="训练时长" align="center" width="120">
        <template #default="scope">
          <span v-if="scope.row.trainDuration">{{ scope.row.trainDuration }}秒</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" align="center" width="100">
        <template #default="scope">
          <el-tag v-if="scope.row.status === '0'" type="success">成功</el-tag>
          <el-tag v-else-if="scope.row.status === '1'" type="danger">失败</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" align="center" prop="createTime" width="180">
        <template #default="scope">
          <span v-if="scope.row.createTime">{{ parseTime(scope.row.createTime) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="center" width="200" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-button
            link
            type="primary"
            icon="View"
            @click="handleViewDetail(scope.row)"
            v-hasPermi="['factor:model:result:detail']"
          >查看详情</el-button>
          <el-button
            link
            type="success"
            icon="Position"
            @click="openSceneBindDialog(scope.row)"
            v-hasPermi="['factor:model:scene:bind']"
          >场景绑定</el-button>
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

    <!-- 详情对话框 -->
    <el-dialog title="训练结果详情" v-model="detailOpen" width="800px" append-to-body>
      <el-descriptions :column="2" border v-if="detailData">
        <el-descriptions-item label="任务名称">{{ detailData.taskName }}</el-descriptions-item>
        <el-descriptions-item label="版本号">
          {{ detailData.version ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="准确率">
          {{ detailData.accuracy ? (detailData.accuracy * 100).toFixed(2) + '%' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="精确率">
          {{ detailData.precisionScore ? (detailData.precisionScore * 100).toFixed(2) + '%' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="召回率">
          {{ detailData.recallScore ? (detailData.recallScore * 100).toFixed(2) + '%' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="F1分数">
          {{ detailData.f1Score ? (detailData.f1Score * 100).toFixed(2) + '%' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="训练样本数">{{ detailData.trainSamples }}</el-descriptions-item>
        <el-descriptions-item label="测试样本数">{{ detailData.testSamples }}</el-descriptions-item>
        <el-descriptions-item label="训练时长">{{ detailData.trainDuration }}秒</el-descriptions-item>
        <el-descriptions-item label="模型文件路径" :span="2">
          {{ detailData.modelFilePath }}
        </el-descriptions-item>
        <el-descriptions-item label="混淆矩阵" :span="2" v-if="detailData.confusionMatrix">
          <pre>{{ JSON.parse(detailData.confusionMatrix) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="特征重要性" :span="2" v-if="detailData.featureImportance">
          <pre>{{ JSON.stringify(JSON.parse(detailData.featureImportance), null, 2) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 场景绑定对话框 -->
    <el-dialog title="绑定场景到模型版本" v-model="sceneDialogOpen" width="480px" append-to-body>
      <el-form :model="sceneForm" label-width="90px">
        <el-form-item label="任务名称">
          <span>{{ sceneForm.taskName }}</span>
        </el-form-item>
        <el-form-item label="结果ID">
          <span>{{ sceneForm.resultId }}</span>
        </el-form-item>
        <el-form-item label="版本号">
          <span>{{ sceneForm.version }}</span>
        </el-form-item>
        <el-form-item label="场景编码">
          <el-select v-model="sceneForm.sceneCode" placeholder="请选择场景" style="width: 240px">
            <el-option label="默认场景（default）" value="default" />
            <el-option label="实盘场景（live）" value="live" />
            <el-option label="回测场景（backtest）" value="backtest" />
            <el-option label="模拟盘（paper）" value="paper" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="sceneDialogOpen = false">取 消</el-button>
          <el-button type="primary" @click="submitSceneBind">确 定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="ModelTrainResult">
import { listModelTrainResult, getModelTrainResult, bindModelScene } from '@/api/factor/model'

const { proxy } = getCurrentInstance()

const resultList = ref([])
const loading = ref(true)
const showSearch = ref(true)
const total = ref(0)
const detailOpen = ref(false)
const detailData = ref(null)

const sceneDialogOpen = ref(false)
const sceneForm = reactive({
  taskId: undefined,
  taskName: '',
  resultId: undefined,
  version: undefined,
  sceneCode: 'default'
})

const data = reactive({
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    taskName: undefined,
    status: undefined
  }
})

const { queryParams } = toRefs(data)

/** 查询模型训练结果列表 */
function getList() {
  loading.value = true
  listModelTrainResult(queryParams.value).then((response) => {
    resultList.value = response.rows
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
/** 查看详情 */
function handleViewDetail(row) {
  getModelTrainResult(row.id).then((response) => {
    detailData.value = response.data
    detailOpen.value = true
  })
}

/** 打开场景绑定对话框 */
function openSceneBindDialog(row) {
  sceneForm.taskId = row.taskId
  sceneForm.taskName = row.taskName
  sceneForm.resultId = row.id
  sceneForm.version = row.version ?? 1
  sceneForm.sceneCode = 'default'
  sceneDialogOpen.value = true
}

/** 提交场景绑定 */
function submitSceneBind() {
  if (!sceneForm.taskId || !sceneForm.resultId || !sceneForm.sceneCode) {
    proxy.$modal.msgWarning('任务ID、结果ID和场景编码不能为空')
    return
  }
  bindModelScene({
    taskId: sceneForm.taskId,
    sceneCode: sceneForm.sceneCode,
    resultId: sceneForm.resultId
  }).then((res) => {
    proxy.$modal.msgSuccess(res.msg || '场景绑定成功')
    sceneDialogOpen.value = false
  })
}

getList()
</script>
