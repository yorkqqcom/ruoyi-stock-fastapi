<template>
   <div class="app-container">
      <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
         <el-form-item label="流程名称" prop="workflowName">
            <el-input
               v-model="queryParams.workflowName"
               placeholder="请输入流程名称"
               clearable
               style="width: 200px"
               @keyup.enter="handleQuery"
            />
         </el-form-item>
         <el-form-item label="状态" prop="status">
            <el-select v-model="queryParams.status" placeholder="请选择状态" clearable style="width: 200px">
               <el-option
                  v-for="dict in sys_normal_disable"
                  :key="dict.value"
                  :label="dict.label"
                  :value="dict.value"
               />
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
               v-hasPermi="['tushare:workflowConfig:add']"
            >新增</el-button>
         </el-col>
         <el-col :span="1.5">
            <el-button
               type="success"
               plain
               icon="Edit"
               :disabled="single"
               @click="handleUpdate"
               v-hasPermi="['tushare:workflowConfig:edit']"
            >修改</el-button>
         </el-col>
         <el-col :span="1.5">
            <el-button
               type="danger"
               plain
               icon="Delete"
               :disabled="multiple"
               @click="handleDelete"
               v-hasPermi="['tushare:workflowConfig:remove']"
            >删除</el-button>
         </el-col>
         <el-col :span="1.5">
            <el-button
               type="success"
               plain
               icon="EditPen"
               @click="handleVisualEdit"
               :disabled="single"
               v-hasPermi="['tushare:workflowStep:edit']"
            >可视化编辑</el-button>
         </el-col>
         <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
      </el-row>

      <el-table v-loading="loading" :data="workflowConfigList" @selection-change="handleSelectionChange">
         <el-table-column type="selection" width="55" align="center" />
         <el-table-column label="流程ID" width="100" align="center" prop="workflowId" />
         <el-table-column label="流程名称" align="center" prop="workflowName" :show-overflow-tooltip="true" />
         <el-table-column label="流程描述" align="center" prop="workflowDesc" :show-overflow-tooltip="true" />
         <el-table-column label="状态" align="center">
            <template #default="scope">
               <el-switch
                  v-model="scope.row.status"
                  active-value="0"
                  inactive-value="1"
                  @change="handleStatusChange(scope.row)"
               ></el-switch>
            </template>
         </el-table-column>
         <el-table-column label="创建时间" align="center" prop="createTime" width="180">
            <template #default="scope">
               <span>{{ parseTime(scope.row.createTime) }}</span>
            </template>
         </el-table-column>
         <el-table-column label="操作" align="center" width="250" class-name="small-padding fixed-width">
            <template #default="scope">
               <el-tooltip content="查看详情" placement="top">
                  <el-button link type="primary" icon="View" @click="handleView(scope.row)" v-hasPermi="['tushare:workflowConfig:query']"></el-button>
               </el-tooltip>
               <el-tooltip content="可视化编辑" placement="top">
                  <el-button link type="success" icon="EditPen" @click="handleVisualEdit(scope.row)" v-hasPermi="['tushare:workflowStep:edit']"></el-button>
               </el-tooltip>
               <el-tooltip content="修改" placement="top">
                  <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" v-hasPermi="['tushare:workflowConfig:edit']"></el-button>
               </el-tooltip>
               <el-tooltip content="删除" placement="top">
                  <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['tushare:workflowConfig:remove']"></el-button>
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

      <!-- 添加或修改流程配置对话框 -->
      <el-dialog :title="title" v-model="open" width="700px" append-to-body>
         <el-form ref="workflowConfigRef" :model="form" :rules="rules" label-width="120px">
            <el-row>
               <el-col :span="24">
                  <el-form-item label="流程名称" prop="workflowName">
                     <el-input v-model="form.workflowName" placeholder="请输入流程名称" />
                  </el-form-item>
               </el-col>
               <el-col :span="24">
                  <el-form-item label="流程描述" prop="workflowDesc">
                     <el-input v-model="form.workflowDesc" type="textarea" :rows="4" placeholder="请输入流程描述" />
                  </el-form-item>
               </el-col>
               <el-col :span="24" v-if="form.workflowId !== undefined">
                  <el-form-item label="状态">
                     <el-radio-group v-model="form.status">
                        <el-radio
                           v-for="dict in sys_normal_disable"
                           :key="dict.value"
                           :value="dict.value"
                        >{{ dict.label }}</el-radio>
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

      <!-- 流程详情对话框（包含步骤列表） -->
      <el-dialog title="流程详情" v-model="detailOpen" width="1000px" append-to-body>
         <el-descriptions :column="2" border v-if="workflowDetail">
            <el-descriptions-item label="流程ID">{{ workflowDetail.workflowId }}</el-descriptions-item>
            <el-descriptions-item label="流程名称">{{ workflowDetail.workflowName }}</el-descriptions-item>
            <el-descriptions-item label="流程描述" :span="2">{{ workflowDetail.workflowDesc }}</el-descriptions-item>
            <el-descriptions-item label="状态">
               <dict-tag :options="sys_normal_disable" :value="workflowDetail.status" />
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ parseTime(workflowDetail.createTime) }}</el-descriptions-item>
         </el-descriptions>
         <el-divider>流程步骤</el-divider>
         <el-table :data="workflowDetail?.steps || []" border style="margin-top: 10px">
            <el-table-column label="步骤顺序" width="100" align="center" prop="stepOrder" />
            <el-table-column label="步骤名称" align="center" prop="stepName" />
            <el-table-column label="接口配置ID" width="120" align="center" prop="configId" />
            <el-table-column label="状态" width="100" align="center">
               <template #default="scope">
                  <dict-tag :options="sys_normal_disable" :value="scope.row.status" />
               </template>
            </el-table-column>
         </el-table>
         <template #footer>
            <div class="dialog-footer">
               <el-button @click="detailOpen = false">关 闭</el-button>
            </div>
         </template>
      </el-dialog>

      <!-- 可视化流程编辑器对话框 -->
      <el-dialog
         title="可视化流程编辑器"
         v-model="editorOpen"
         width="95%"
         :close-on-click-modal="false"
         append-to-body
         class="workflow-editor-dialog"
      >
         <workflow-step-editor
            v-if="editorOpen && currentWorkflowId"
            ref="editorRef"
            :workflow-id="currentWorkflowId"
            @save="handleEditorSaved"
            @cancel="handleEditorCancel"
         />
         <template #footer>
            <div class="dialog-footer">
               <el-button type="primary" @click="handleEditorSave">保存</el-button>
               <el-button @click="handleEditorCancel">取消</el-button>
            </div>
         </template>
      </el-dialog>
   </div>
</template>

<script setup name="WorkflowConfig">
import { listWorkflowConfig, getWorkflowConfig, getWorkflowConfigBase, delWorkflowConfig, addWorkflowConfig, updateWorkflowConfig } from "@/api/tushare/workflowConfig"
import WorkflowStepEditor from '../workflowStep/WorkflowStepEditor.vue'

const { proxy } = getCurrentInstance();
const { sys_normal_disable } = proxy.useDict("sys_normal_disable");

const workflowConfigList = ref([]);
const open = ref(false);
const detailOpen = ref(false);
const editorOpen = ref(false);
const currentWorkflowId = ref(null);
const editorRef = ref(null);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);
const title = ref("");
const workflowDetail = ref(null);

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    workflowName: undefined,
    status: undefined
  },
  rules: {
    workflowName: [{ required: true, message: "流程名称不能为空", trigger: "blur" }],
  }
});

const { queryParams, form, rules } = toRefs(data);

/** 查询流程配置列表 */
function getList() {
  loading.value = true;
  listWorkflowConfig(queryParams.value).then(response => {
    workflowConfigList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
}

/** 取消按钮 */
function cancel() {
  open.value = false;
  reset();
}

/** 表单重置 */
function reset() {
  // 使用属性赋值而不是整体替换，避免丢失响应式引用
  Object.assign(form.value, {
    workflowId: undefined,
    workflowName: undefined,
    workflowDesc: undefined,
    status: "0",
    remark: undefined
  });
  proxy.resetForm("workflowConfigRef");
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
  ids.value = selection.map(item => item.workflowId);
  single.value = selection.length != 1;
  multiple.value = !selection.length;
}

// 状态修改
function handleStatusChange(row) {
  let text = row.status === "0" ? "启用" : "停用";
  proxy.$modal.confirm('确认要"' + text + '""' + row.workflowName + '"流程配置吗?').then(function () {
    const data = {
      workflowId: row.workflowId,
      status: row.status
    }
    return updateWorkflowConfig(data);
  }).then(() => {
    proxy.$modal.msgSuccess(text + "成功");
  }).catch(function () {
    row.status = row.status === "0" ? "1" : "0";
  });
}

/** 新增按钮操作 */
function handleAdd() {
  reset();
  open.value = true;
  title.value = "添加流程配置";
}

/** 修改按钮操作 */
function handleUpdate(row) {
  reset();
  const workflowId = row.workflowId || ids.value[0];
  // 使用基础信息接口，避免加载步骤列表时可能出现的后端异常
  getWorkflowConfigBase(workflowId).then(response => {
    // 接口返回的是 { code, msg, data }，这里取内层 data
    const data = response.data || response;
    // 显式拷贝字段，确保与表单模型字段一一对应并保持响应式
    form.value.workflowId = data.workflowId;
    form.value.workflowName = data.workflowName;
    form.value.workflowDesc = data.workflowDesc;
    form.value.status = data.status ?? "0";
    form.value.remark = data.remark;
    open.value = true;
    title.value = "修改流程配置";
  });
}

/** 查看详情 */
function handleView(row) {
  const workflowId = row.workflowId || ids.value[0];
  getWorkflowConfig(workflowId).then(response => {
    // 同样兼容 { code, msg, data } 或直接返回数据两种情况
    workflowDetail.value = response.data || response;
    detailOpen.value = true;
  });
}

/** 可视化编辑 */
function handleVisualEdit(row) {
  const workflowId = row.workflowId || ids.value[0];
  if (!workflowId) {
    proxy.$modal.msgWarning('请先选择流程配置');
    return;
  }
  currentWorkflowId.value = workflowId;
  editorOpen.value = true;
}

/** 编辑器保存 */
function handleEditorSave() {
  if (editorRef.value) {
    editorRef.value.handleSave();
  }
}

/** 编辑器保存成功 */
function handleEditorSaved() {
  editorOpen.value = false;
  getList();
}

/** 编辑器取消 */
function handleEditorCancel() {
  editorOpen.value = false;
}

/** 提交按钮 */
function submitForm() {
  proxy.$refs["workflowConfigRef"].validate(valid => {
    if (valid) {
      if (form.value.workflowId != undefined) {
        updateWorkflowConfig(form.value).then(response => {
          proxy.$modal.msgSuccess("修改成功");
          open.value = false;
          getList();
        });
      } else {
        addWorkflowConfig(form.value).then(response => {
          proxy.$modal.msgSuccess("新增成功");
          open.value = false;
          getList();
        });
      }
    }
  });
}

/** 删除按钮操作 */
function handleDelete(row) {
  const workflowIds = row.workflowId || ids.value;
  proxy.$modal.confirm('是否确认删除流程配置编号为"' + workflowIds + '"的数据项?').then(function () {
    return delWorkflowConfig(workflowIds);
  }).then(() => {
    getList();
    proxy.$modal.msgSuccess("删除成功");
  }).catch(() => {});
}

getList();
</script>

<style scoped lang="scss">
:deep(.workflow-editor-dialog) {
  .el-dialog {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 60px);
    max-height: 95vh;
  }
  
  .el-dialog__body {
    padding: 0;
    flex: 1;
    min-height: 0;
    height: 100%;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
}
</style>
