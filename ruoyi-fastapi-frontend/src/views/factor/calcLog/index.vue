<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch" label-width="68px">
      <el-form-item label="任务名称" prop="taskName">
        <el-input
          v-model="queryParams.taskName"
          placeholder="请输入任务名称"
          clearable
          style="width: 240px"
          @keyup.enter="handleQuery"
        />
      </el-form-item>
      <el-form-item label="执行状态" prop="status">
        <el-select
          v-model="queryParams.status"
          placeholder="请选择执行状态"
          clearable
          style="width: 240px"
        >
          <el-option label="成功" value="0" />
          <el-option label="失败" value="1" />
        </el-select>
      </el-form-item>
      <el-form-item label="执行时间" style="width: 308px">
        <el-date-picker
          v-model="dateRange"
          value-format="YYYY-MM-DD"
          type="daterange"
          range-separator="-"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
        ></el-date-picker>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button 
          type="warning" 
          plain 
          icon="Close"
          @click="handleClose"
        >关闭</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="logList">
      <el-table-column label="日志ID" width="80" align="center" prop="id" />
      <el-table-column label="任务ID" width="80" align="center" prop="taskId" />
      <el-table-column label="任务名称" align="center" prop="taskName" :show-overflow-tooltip="true" />
      <el-table-column label="因子代码" align="center" prop="factorCodes" :show-overflow-tooltip="true" />
      <el-table-column label="标的范围" align="center" prop="symbolUniverse" :show-overflow-tooltip="true" />
      <el-table-column label="日期范围" align="center" :show-overflow-tooltip="true">
        <template #default="scope">
          <span v-if="scope.row.startDate && scope.row.endDate">
            {{ scope.row.startDate }} ~ {{ scope.row.endDate }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="执行状态" align="center" prop="status" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.status === '0' ? 'success' : 'danger'">
            {{ scope.row.status === '0' ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="记录数" align="center" prop="recordCount" width="100" />
      <el-table-column label="执行时长" align="center" prop="duration" width="120">
        <template #default="scope">
          <span v-if="scope.row.duration !== null && scope.row.duration !== undefined">
            {{ scope.row.duration }}秒
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="执行时间" align="center" prop="createTime" width="180">
        <template #default="scope">
          <span>{{ parseTime(scope.row.createTime) || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="center" width="100" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-button link type="primary" icon="View" @click="handleView(scope.row)">详细</el-button>
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

    <!-- 日志详细 -->
    <el-dialog title="因子计算日志详细" v-model="open" width="700px" append-to-body>
      <el-form :model="form" label-width="120px">
        <el-row>
          <el-col :span="12">
            <el-form-item label="日志ID：">{{ form.id }}</el-form-item>
            <el-form-item label="任务ID：">{{ form.taskId }}</el-form-item>
            <el-form-item label="任务名称：">{{ form.taskName }}</el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="执行状态：">
              <el-tag :type="form.status === '0' ? 'success' : 'danger'">
                {{ form.status === '0' ? '成功' : '失败' }}
              </el-tag>
            </el-form-item>
            <el-form-item label="记录数：">{{ form.recordCount || 0 }}</el-form-item>
            <el-form-item label="执行时长：">
              <span v-if="form.duration !== null && form.duration !== undefined">
                {{ form.duration }}秒
              </span>
              <span v-else>-</span>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="因子代码：">{{ form.factorCodes || '-' }}</el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="标的范围：">{{ form.symbolUniverse || '-' }}</el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="开始日期：">{{ form.startDate || '-' }}</el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期：">{{ form.endDate || '-' }}</el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="执行时间：">{{ parseTime(form.createTime) || '-' }}</el-form-item>
          </el-col>
          <el-col :span="24" v-if="form.status === '1' && form.errorMessage">
            <el-form-item label="错误信息：">
              <el-input
                type="textarea"
                :rows="5"
                v-model="form.errorMessage"
                readonly
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="open = false">关 闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="FactorCalcLog">
import { listFactorCalcLog } from "@/api/factor/calcLog";

const { proxy } = getCurrentInstance();

const logList = ref([]);
const open = ref(false);
const loading = ref(true);
const showSearch = ref(true);
const total = ref(0);
const dateRange = ref([]);
const route = useRoute();

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    taskId: undefined,
    taskName: undefined,
    status: undefined
  }
});

const { queryParams, form } = toRefs(data);

/** 查询因子计算日志列表 */
function getList() {
  loading.value = true;
  listFactorCalcLog(proxy.addDateRange(queryParams.value, dateRange.value)).then(response => {
    logList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
}

// 返回按钮
function handleClose() {
  const obj = { path: "/factor/task" };
  proxy.$tab.closeOpenPage(obj);
}

/** 搜索按钮操作 */
function handleQuery() {
  queryParams.value.pageNum = 1;
  getList();
}

/** 重置按钮操作 */
function resetQuery() {
  dateRange.value = [];
  proxy.resetForm("queryRef");
  handleQuery();
}

/** 详细按钮操作 */
function handleView(row) {
  open.value = true;
  form.value = row;
}

(() => {
  const taskId = route.params && route.params.taskId;
  if (taskId !== undefined && taskId != 0) {
    queryParams.value.taskId = parseInt(taskId);
  }
  getList();
})();
</script>
