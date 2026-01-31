<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
      <el-form-item label="股票代码" prop="symbol">
        <el-input
          v-model="queryParams.symbol"
          placeholder="如：000001.SZ"
          clearable
          style="width: 200px"
          @keyup.enter="handleQuery"
        />
      </el-form-item>
      <el-form-item label="因子代码" prop="factorCodes">
        <el-input
          v-model="queryParams.factorCodes"
          placeholder="逗号分隔，如：MA_5,MA_20"
          clearable
          style="width: 260px"
          @keyup.enter="handleQuery"
        />
      </el-form-item>
      <el-form-item label="交易日期" style="width: 320px">
        <el-date-picker
          v-model="dateRange"
          value-format="YYYYMMDD"
          type="daterange"
          range-separator="-"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
        />
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
          icon="Download"
          :disabled="!tableData.length"
          @click="handleExport"
          v-hasPermi="['factor:value:list']"
        >导出</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="tableData">
      <el-table-column label="交易日期" align="center" prop="tradeDate" width="120" />
      <el-table-column label="股票代码" align="center" prop="symbol" width="140" />
      <el-table-column label="因子代码" align="center" prop="factorCode" width="140" />
      <el-table-column label="因子值" align="center" prop="factorValue" />
      <el-table-column label="任务ID" align="center" prop="taskId" width="100" />
      <el-table-column label="计算时间" align="center" prop="calcDate" width="180">
        <template #default="scope">
          <span>{{ parseTime(scope.row.calcDate) }}</span>
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
  </div>
</template>

<script setup name="FactorValue">
import { pageFactorValue } from "@/api/factor/value"

const { proxy } = getCurrentInstance();

const tableData = ref([]);
const loading = ref(true);
const showSearch = ref(true);
const total = ref(0);
const dateRange = ref([]);

const data = reactive({
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    symbol: undefined,
    factorCodes: undefined,
    startDate: undefined,
    endDate: undefined
  }
});

const { queryParams } = toRefs(data);

/** 查询因子结果列表 */
function getList() {
  loading.value = true;
  const params = { ...queryParams.value };
  if (dateRange.value && dateRange.value.length === 2) {
    params.startDate = dateRange.value[0];
    params.endDate = dateRange.value[1];
  } else {
    params.startDate = undefined;
    params.endDate = undefined;
  }
  pageFactorValue(params).then(response => {
    tableData.value = response.rows;
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
  dateRange.value = [];
  proxy.resetForm("queryRef");
  handleQuery();
}

/** 导出按钮操作（简单导出为 CSV 字符串，通过浏览器下载） */
function handleExport() {
  if (!tableData.value.length) {
    proxy.$modal.msgWarning("暂无数据可导出");
    return;
  }
  const header = ["tradeDate", "symbol", "factorCode", "factorValue", "taskId", "calcDate"];
  const rows = tableData.value.map(row => header.map(h => row[h] ?? ""));
  const csvContent = [header.join(","), ...rows.map(r => r.join(","))].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "factor_value.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

onMounted(() => {
  getList();
});
</script>

