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
      <el-form-item label="频率" prop="freq">
        <el-select v-model="queryParams.freq" placeholder="请选择频率" clearable style="width: 200px">
          <el-option label="日频(D)" value="D" />
          <el-option label="周频(W)" value="W" />
          <el-option label="月频(M)" value="M" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="queryParams.status" placeholder="请选择状态" clearable style="width: 200px">
          <el-option label="正常" value="0" />
          <el-option label="暂停" value="1" />
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
          v-hasPermi="['factor:task:add']"
        >新增</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="success"
          plain
          icon="Edit"
          :disabled="single"
          @click="handleUpdate"
          v-hasPermi="['factor:task:edit']"
        >修改</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button
          type="danger"
          plain
          icon="Delete"
          :disabled="multiple"
          @click="handleDelete"
          v-hasPermi="['factor:task:remove']"
        >删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="taskList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="任务ID" width="80" align="center" prop="id" />
      <el-table-column label="任务名称" align="center" prop="taskName" :show-overflow-tooltip="true" />
      <el-table-column label="频率" align="center" prop="freq" width="80" />
      <el-table-column label="运行模式" align="center" prop="runMode" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.runMode === 'full' ? 'warning' : 'info'">
            {{ scope.row.runMode === 'full' ? '全量' : '增量' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="因子代码列表" align="center" prop="factorCodes" :show-overflow-tooltip="true" />
      <el-table-column label="标的范围" align="center" prop="symbolUniverse" :show-overflow-tooltip="true" />
      <el-table-column label="日期范围" align="center" :show-overflow-tooltip="true">
        <template #default="scope">
          <span v-if="scope.row.startDate && scope.row.endDate">
            {{ scope.row.startDate }} ~ {{ scope.row.endDate }}
          </span>
          <span v-else-if="scope.row.startDate">
            {{ scope.row.startDate }} ~ (自动)
          </span>
          <span v-else-if="scope.row.endDate">
            (自动) ~ {{ scope.row.endDate }}
          </span>
          <span v-else style="color: #909399;">按任务逻辑自动计算</span>
        </template>
      </el-table-column>
      <el-table-column label="cron表达式" align="center" prop="cronExpression" :show-overflow-tooltip="true" />
      <el-table-column label="运行统计" align="center" width="160">
        <template #default="scope">
          <span>运行: {{ scope.row.runCount || 0 }}</span>
          <span style="margin-left: 8px; color: #67c23a;">成: {{ scope.row.successCount || 0 }}</span>
          <span style="margin-left: 8px; color: #f56c6c;">败: {{ scope.row.failCount || 0 }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" align="center" width="100">
        <template #default="scope">
          <el-switch
            v-model="scope.row.status"
            active-value="0"
            inactive-value="1"
            @change="handleStatusChange(scope.row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="最后运行" align="center" prop="lastRunTime" width="180">
        <template #default="scope">
          <span v-if="scope.row.lastRunTime">{{ parseTime(scope.row.lastRunTime) }}</span>
          <span v-else style="color: #909399;">未运行</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="center" width="320" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-tooltip content="执行" placement="top">
            <el-button
              link
              type="success"
              icon="VideoPlay"
              @click="handleExecute(scope.row)"
              v-hasPermi="['factor:task:execute']"
            />
          </el-tooltip>
          <el-tooltip content="查看日志" placement="top">
            <el-button
              link
              type="info"
              icon="Document"
              @click="handleViewLog(scope.row)"
              v-hasPermi="['factor:calcLog:list']"
            />
          </el-tooltip>
          <el-tooltip content="修改" placement="top">
            <el-button
              link
              type="primary"
              icon="Edit"
              @click="handleUpdate(scope.row)"
              v-hasPermi="['factor:task:edit']"
            />
          </el-tooltip>
          <el-tooltip content="删除" placement="top">
            <el-button
              link
              type="primary"
              icon="Delete"
              @click="handleDelete(scope.row)"
              v-hasPermi="['factor:task:remove']"
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

    <!-- 添加或修改因子任务对话框 -->
    <el-dialog :title="title" v-model="open" width="900px" append-to-body>
      <el-form ref="taskRef" :model="form" :rules="rules" label-width="120px">
        <el-row>
          <el-col :span="24">
            <el-form-item label="任务名称" prop="taskName">
              <el-input v-model="form.taskName" placeholder="请输入任务名称" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="因子代码列表" prop="factorCodes">
              <el-input
                v-model="form.factorCodes"
                type="textarea"
                :rows="2"
                placeholder="逗号分隔，例如：MA_5,MA_20,MOM_20"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="标的范围(JSON)" prop="symbolUniverse">
              <el-input
                v-model="form.symbolUniverse"
                type="textarea"
                :rows="3"
                placeholder='如：{"type":"all"} 或 {"type":"index","code":"000300.SH"}'
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="频率" prop="freq">
              <el-select v-model="form.freq" placeholder="请选择频率" style="width: 100%">
                <el-option label="日频(D)" value="D" />
                <el-option label="周频(W)" value="W" />
                <el-option label="月频(M)" value="M" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="运行模式" prop="runMode">
              <el-radio-group v-model="form.runMode">
                <el-radio value="increment">增量</el-radio>
                <el-radio value="full">全量</el-radio>
              </el-radio-group>
              <div style="margin-top: 4px; font-size: 12px; color: #909399;">
                <span v-if="form.runMode === 'increment'">
                  增量模式：每次运行只计算自上次运行以来的新数据，适合每日定时任务
                </span>
                <span v-else>
                  全量模式：每次运行都使用完整的日期范围进行计算
                </span>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="开始日期" prop="startDate">
              <el-date-picker
                v-model="form.startDate"
                type="date"
                placeholder="选择开始日期（可选）"
                value-format="YYYYMMDD"
                style="width: 100%"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期" prop="endDate">
              <el-date-picker
                v-model="form.endDate"
                type="date"
                placeholder="选择结束日期（可选）"
                value-format="YYYYMMDD"
                style="width: 100%"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item>
              <div style="font-size: 12px; color: #909399;">
                <div v-if="form.runMode === 'increment'">
                  <div><strong>增量模式下的日期范围逻辑：</strong></div>
                  <div style="margin-top: 4px;">
                    • 如果设置了日期范围：作为最大计算范围，实际计算从上次运行时间的下一个交易日开始，到最新交易日结束（不超过设置的范围）
                  </div>
                  <div style="margin-top: 4px;">
                    • 如果开始日期为空：首次运行使用最早交易日，后续运行从上次运行时间的下一个交易日开始
                  </div>
                  <div style="margin-top: 4px;">
                    • 如果结束日期为空：使用最新交易日作为结束日期
                  </div>
                  <div style="margin-top: 4px;">
                    • 如果两个日期都为空：首次运行从最早交易日到最新交易日，后续运行从上次运行时间的下一个交易日到最新交易日
                  </div>
                </div>
                <div v-else>
                  <div><strong>全量模式下的日期范围逻辑：</strong></div>
                  <div style="margin-top: 4px;">
                    • 如果设置了日期范围：使用此日期范围进行计算
                  </div>
                  <div style="margin-top: 4px;">
                    • 如果开始日期为空：使用最早交易日
                  </div>
                  <div style="margin-top: 4px;">
                    • 如果结束日期为空：使用最新交易日
                  </div>
                  <div style="margin-top: 4px;">
                    • 如果两个日期都为空：从最早交易日到最新交易日
                  </div>
                </div>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="cron表达式" prop="cronExpression">
              <el-input v-model="form.cronExpression" placeholder="如：0 0 2 * * ? 每天凌晨2点" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="任务参数(JSON)" prop="params">
              <el-input
                v-model="form.params"
                type="textarea"
                :rows="3"
                placeholder='如：{"recalcFailedOnly": true}'
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="状态" prop="status">
              <el-radio-group v-model="form.status">
                <el-radio value="0">正常</el-radio>
                <el-radio value="1">暂停</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注" prop="remark">
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
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

<script setup name="FactorTask">
import { listFactorTask, addFactorTask, updateFactorTask, delFactorTask, changeFactorTaskStatus, executeFactorTask } from "@/api/factor/task"

const { proxy } = getCurrentInstance();

const taskList = ref([]);
const open = ref(false);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);
const title = ref("");

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    taskName: undefined,
    freq: undefined,
    status: undefined
  },
  rules: {
    taskName: [{ required: true, message: "任务名称不能为空", trigger: "blur" }],
    factorCodes: [{ required: true, message: "因子代码列表不能为空", trigger: "blur" }]
  }
});

const { queryParams, form, rules } = toRefs(data);

/** 查询因子任务列表 */
function getList() {
  loading.value = true;
  listFactorTask(queryParams.value).then(response => {
    taskList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
}

/** 搜索按钮操作 */
function handleQuery() {
  queryParams.value.pageNum = 1;
  getList();
}

/** 重置按钮操作 */
function resetQuery() {
  proxy.resetForm("queryRef");
  handleQuery();
}

// 多选框选中数据
function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.id);
  single.value = selection.length !== 1;
  multiple.value = !selection.length;
}

/** 新增按钮操作 */
function handleAdd() {
  resetForm();
  title.value = "新增因子任务";
  open.value = true;
}

/** 修改按钮操作 */
function handleUpdate(row) {
  resetForm();
  form.value = { ...row };
  // 日期字段直接使用，不需要转换
  title.value = "编辑因子任务";
  open.value = true;
}

/** 删除按钮操作 */
function handleDelete(row) {
  const taskIds = row.id || ids.value.join(",");
  proxy.$modal.confirm('是否确认删除因子任务编号为"' + taskIds + '"的数据项？').then(function () {
    return delFactorTask(taskIds);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  }).catch(() => {});
}

/** 状态开关切换 */
function handleStatusChange(row) {
  const text = row.status === '0' ? "启用" : "暂停";
  proxy.$modal.confirm('确认要"' + text + '"因子任务 "' + row.taskName + '" 吗？').then(function () {
    return changeFactorTaskStatus(row.id, row.status);
  }).then(() => {
    proxy.$modal.msgSuccess(text + "成功");
    getList();
  }).catch(() => {
    // 还原
    row.status = row.status === '0' ? '1' : '0';
  });
}

/** 执行按钮 */
function handleExecute(row) {
  proxy.$modal.confirm('确认要立即执行因子任务 "' + row.taskName + '" 吗？').then(function () {
    return executeFactorTask(row.id);
  }).then(() => {
    proxy.$modal.msgSuccess("任务已提交执行");
  }).catch(() => {});
}

/** 查看日志按钮 */
function handleViewLog(row) {
  const path = `/factor/calcLog/index/${row.id}`;
  proxy.$tab.openPage(path, () => {
    proxy.$router.push(path);
  });
}

/** 提交按钮 */
function submitForm() {
  proxy.$refs["taskRef"].validate(valid => {
    if (!valid) {
      return;
    }
    // 日期字段已经是独立的，直接使用，空值转换为 undefined
    if (!form.value.startDate || form.value.startDate === '') {
      form.value.startDate = undefined;
    }
    if (!form.value.endDate || form.value.endDate === '') {
      form.value.endDate = undefined;
    }
    if (form.value.id) {
      updateFactorTask(form.value).then(() => {
        proxy.$modal.msgSuccess("修改成功");
        open.value = false;
        getList();
      });
    } else {
      addFactorTask(form.value).then(() => {
        proxy.$modal.msgSuccess("新增成功");
        open.value = false;
        getList();
      });
    }
  });
}

/** 取消按钮 */
function cancel() {
  open.value = false;
}

/** 表单重置 */
function resetForm() {
  form.value = {
    id: undefined,
    taskName: undefined,
    factorCodes: undefined,
    symbolUniverse: undefined,
    freq: 'D',
    startDate: undefined,
    endDate: undefined,
    cronExpression: undefined,
    runMode: 'increment',
    params: undefined,
    status: '0',
    remark: undefined
  };
  proxy.resetForm("taskRef");
}

onMounted(() => {
  getList();
});
</script>

