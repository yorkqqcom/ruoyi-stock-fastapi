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
         <el-form-item label="任务类型" prop="taskType">
            <el-select
               v-model="queryParams.taskType"
               placeholder="请选择任务类型"
               clearable
               style="width: 240px"
            >
               <el-option label="单个接口" value="single" />
               <el-option label="流程配置" value="workflow" />
            </el-select>
         </el-form-item>
         <el-form-item label="执行状态" prop="status">
            <el-select
               v-model="queryParams.status"
               placeholder="请选择执行状态"
               clearable
               style="width: 240px"
            >
               <el-option
                  v-for="dict in sys_common_status"
                  :key="dict.value"
                  :label="dict.label"
                  :value="dict.value"
               />
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
               type="danger"
               plain
               icon="Delete"
               :disabled="multiple"
               @click="handleDelete"
               v-hasPermi="['tushare:downloadLog:remove']"
            >删除</el-button>
         </el-col>
         <el-col :span="1.5">
            <el-button
               type="danger"
               plain
               icon="Delete"
               @click="handleClean"
               v-hasPermi="['tushare:downloadLog:remove']"
            >清空</el-button>
         </el-col>
         <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
      </el-row>

      <el-table v-loading="loading" :data="logList" @selection-change="handleSelectionChange">
         <el-table-column type="selection" width="55" align="center" />
         <el-table-column label="日志ID" width="100" align="center" prop="logId" />
         <el-table-column label="任务类型" align="center" width="120">
            <template #default="scope">
               <el-tag :type="scope.row.taskType === 'workflow' ? 'success' : 'info'" size="small">
                  {{ scope.row.taskType === 'workflow' ? '流程配置' : '单个接口' }}
               </el-tag>
            </template>
         </el-table-column>
         <el-table-column label="任务名称" align="center" prop="taskName" :show-overflow-tooltip="true" />
         <el-table-column label="步骤名称" align="center" width="120" v-if="hasWorkflowLog">
            <template #default="scope">
               <span v-if="scope.row.stepName" style="color: #409eff;">{{ scope.row.stepName }}</span>
               <span v-else style="color: #909399;">-</span>
            </template>
         </el-table-column>
         <el-table-column label="接口名称" align="center" prop="apiName" :show-overflow-tooltip="true" />
         <el-table-column label="下载日期" align="center" prop="downloadDate" width="120" />
         <el-table-column label="记录数" align="center" prop="recordCount" width="100" />
         <el-table-column label="文件路径" align="center" prop="filePath" :show-overflow-tooltip="true" />
         <el-table-column label="执行状态" align="center" prop="status" width="100">
            <template #default="scope">
               <dict-tag :options="sys_common_status" :value="scope.row.status" />
            </template>
         </el-table-column>
         <el-table-column label="执行时长" align="center" prop="duration" width="100">
            <template #default="scope">
               <span v-if="scope.row.duration">{{ scope.row.duration }}秒</span>
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
               <el-button link type="primary" icon="View" @click="handleView(scope.row)" v-hasPermi="['tushare:downloadLog:list']">详细</el-button>
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

      <!-- 下载日志详细 -->
      <el-dialog title="下载日志详细" v-model="open" width="700px" append-to-body>
         <el-form :model="form" label-width="100px">
            <el-row>
               <el-col :span="12">
                  <el-form-item label="日志ID：">{{ form.logId }}</el-form-item>
                  <el-form-item label="任务名称：">{{ form.taskName }}</el-form-item>
                  <el-form-item label="任务类型：">
                     <el-tag :type="form.taskType === 'workflow' ? 'success' : 'info'" size="small">
                        {{ form.taskType === 'workflow' ? '流程配置' : '单个接口' }}
                     </el-tag>
                  </el-form-item>
               </el-col>
               <el-col :span="12">
                  <el-form-item label="接口名称：">{{ form.apiName }}</el-form-item>
                  <el-form-item label="步骤名称：" v-if="form.stepName">
                     <el-tag type="primary" size="small">{{ form.stepName }}</el-tag>
                  </el-form-item>
                  <el-form-item label="执行时间：">{{ parseTime(form.createTime) || '-' }}</el-form-item>
               </el-col>
               <el-col :span="12">
                  <el-form-item label="下载日期：">{{ form.downloadDate }}</el-form-item>
               </el-col>
               <el-col :span="12">
                  <el-form-item label="记录数：">{{ form.recordCount }}</el-form-item>
               </el-col>
               <el-col :span="24">
                  <el-form-item label="文件路径：">{{ form.filePath || '无' }}</el-form-item>
               </el-col>
               <el-col :span="12">
                  <el-form-item label="执行状态：">
                     <div v-if="form.status == 0">成功</div>
                     <div v-else-if="form.status == 1">失败</div>
                  </el-form-item>
               </el-col>
               <el-col :span="12">
                  <el-form-item label="执行时长：">
                     <span v-if="form.duration">{{ form.duration }}秒</span>
                     <span v-else>-</span>
                  </el-form-item>
               </el-col>
               <el-col :span="24" v-if="form.status == 1 && form.errorMessage">
                  <el-form-item label="错误信息：">
                     <el-input 
                        v-model="form.errorMessage" 
                        type="textarea" 
                        :rows="6" 
                        readonly
                        style="color: #f56c6c;"
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

<script setup name="DownloadLog">
import { listDownloadLog, delDownloadLog, cleanDownloadLog } from "@/api/tushare/downloadLog"

const { proxy } = getCurrentInstance();
const { sys_common_status } = proxy.useDict("sys_common_status");

const logList = ref([]);
const open = ref(false);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref([]);
const multiple = ref(true);
const total = ref(0);
const dateRange = ref([]);

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    taskName: undefined,
    taskType: undefined,
    status: undefined
  }
});

const hasWorkflowLog = ref(false);

const { queryParams, form } = toRefs(data);

/** 查询下载日志列表 */
function getList() {
  loading.value = true;
  listDownloadLog(proxy.addDateRange(queryParams.value, dateRange.value)).then(response => {
    logList.value = response.rows;
    total.value = response.total;
    // 检查是否有流程配置任务的日志
    hasWorkflowLog.value = response.rows.some(log => log.taskType === 'workflow');
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
  dateRange.value = [];
  proxy.resetForm("queryRef");
  handleQuery();
}

// 多选框选中数据
function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.logId);
  multiple.value = !selection.length;
}

/** 详细按钮操作 */
function handleView(row) {
  open.value = true;
  form.value = row;
}

/** 删除按钮操作 */
function handleDelete(row) {
  const logIds = row.logId || ids.value;
  proxy.$modal.confirm('是否确认删除下载日志编号为"' + logIds + '"的数据项?').then(function () {
    return delDownloadLog(logIds);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  }).catch(() => {});
}

/** 清空按钮操作 */
function handleClean() {
  proxy.$modal.confirm("是否确认清空所有下载日志数据项?").then(function () {
    return cleanDownloadLog();
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("清空成功");
  }).catch(() => {});
}

getList();
</script>
