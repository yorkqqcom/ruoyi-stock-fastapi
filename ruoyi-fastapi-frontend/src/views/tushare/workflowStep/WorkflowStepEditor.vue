<template>
  <div class="workflow-editor-container">
    <!-- 左侧工具栏 -->
    <div class="editor-toolbar">
      <div class="toolbar-header">
        <h3>节点类型</h3>
      </div>
      <el-scrollbar class="toolbar-scrollbar">
        <div class="node-types">
          <div 
            class="node-type-item start-node" 
            draggable="true"
            @dragstart="handleDragStart($event, 'start')"
          >
            <div class="node-icon start-icon"></div>
            <div class="node-label">开始节点</div>
          </div>
          <div 
            class="node-type-item task-node" 
            draggable="true"
            @dragstart="handleDragStart($event, 'task')"
          >
            <div class="node-icon task-icon"></div>
            <div class="node-label">任务节点</div>
          </div>
          <div 
            class="node-type-item end-node" 
            draggable="true"
            @dragstart="handleDragStart($event, 'end')"
          >
            <div class="node-icon end-icon"></div>
            <div class="node-label">结束节点</div>
          </div>
        </div>
      </el-scrollbar>
    </div>

    <!-- 中间画布区 -->
    <div class="editor-canvas">
      <div class="canvas-toolbar">
        <el-button-group>
          <el-button size="small" icon="ZoomIn" @click="zoomIn">放大</el-button>
          <el-button size="small" icon="ZoomOut" @click="zoomOut">缩小</el-button>
          <el-button size="small" icon="FullScreen" @click="fitView">适应</el-button>
          <el-button size="small" icon="RefreshLeft" @click="undo" :disabled="!canUndo">撤销</el-button>
          <el-button size="small" icon="RefreshRight" @click="redo" :disabled="!canRedo">重做</el-button>
          <el-button size="small" icon="Delete" @click="deleteSelected">删除</el-button>
        </el-button-group>
      </div>
      <VueFlow
        ref="vueFlowRef"
        v-model="elements"
        :nodes="nodes"
        :edges="edges"
        :node-types="nodeTypes"
        :default-edge-options="{ type: 'smoothstep' }"
        :fit-view-on-init="false"
        :min-zoom="0.2"
        :max-zoom="2"
        class="vue-flow-container"
        @nodes-change="onNodesChange"
        @edges-change="onEdgesChange"
        @node-click="onNodeClick"
        @edge-click="onEdgeClick"
        @pane-click="onPaneClick"
        @connect="onConnect"
        @node-drag="onNodeDrag"
        @node-drag-stop="onNodeDragStop"
        @drop="onDrop"
        @dragover="onDragOver"
      >
        <Background pattern-color="#e5e7eb" :gap="20" />
        <MiniMap />
        <Controls />
      </VueFlow>
    </div>

    <!-- 右侧属性面板 -->
    <div class="editor-properties">
      <div class="properties-header">
        <h3>属性配置</h3>
      </div>
      <el-scrollbar class="properties-scrollbar">
        <PropertyPanel
          v-if="selectedElement"
          :element="selectedElement"
          :element-type="selectedElementType"
          :api-configs="apiConfigs"
          @update="handlePropertyUpdate"
        />
        <div v-else class="empty-properties">
          <el-empty description="请选择节点或连接线进行配置" />
        </div>
      </el-scrollbar>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick, onUnmounted } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
// @vue-flow/background 不需要单独的样式导入（该包不提供样式文件）
import '@vue-flow/minimap/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import { getWorkflowConfig } from '@/api/tushare/workflowConfig'
import { batchSaveWorkflowStep } from '@/api/tushare/workflowStep'
import { listApiConfig } from '@/api/tushare/apiConfig'
import StartNode from './components/StartNode.vue'
import EndNode from './components/EndNode.vue'
import TaskNode from './components/TaskNode.vue'
import PropertyPanel from './components/PropertyPanel.vue'

const props = defineProps({
  workflowId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['save', 'cancel'])

const { proxy } = getCurrentInstance()

// Vue Flow 配置
const nodeTypes = {
  start: StartNode,
  end: EndNode,
  task: TaskNode
}

// 数据状态
const nodes = ref([])
const edges = ref([])
const apiConfigs = ref([])
const selectedElement = ref(null)
const selectedElementType = ref(null) // 'node' | 'edge' | null
const vueFlowRef = ref(null)

// 撤销/重做
const history = ref([])
const historyIndex = ref(-1)
const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value < history.value.length - 1)

// 拖拽状态
const draggedNodeType = ref(null)

// 计算属性：elements for VueFlow
const elements = computed({
  get: () => [...nodes.value, ...edges.value],
  set: (val) => {
    nodes.value = val.filter(item => item.type !== 'edge' && !item.source)
    edges.value = val.filter(item => item.type === 'edge' || item.source)
  }
})

// 初始化
onMounted(async () => {
  await loadApiConfigs()
  await loadWorkflowData()
  saveHistory()
})

// 加载API配置列表
async function loadApiConfigs() {
  try {
    const response = await listApiConfig({ pageNum: 1, pageSize: 1000 })
    apiConfigs.value = response.rows || []
  } catch (error) {
    proxy.$modal.msgError('加载API配置失败')
  }
}

// 加载流程数据
async function loadWorkflowData() {
  try {
    const response = await getWorkflowConfig(props.workflowId)
    const workflow = response.data
    const steps = workflow.steps || []
    
    if (steps.length === 0) {
      return
    }

    // 如果有layout_data，使用它
    const firstStep = steps[0]
    if (firstStep.layoutData) {
      const layout = typeof firstStep.layoutData === 'string' 
        ? JSON.parse(firstStep.layoutData) 
        : firstStep.layoutData
      
      if (layout.nodes && layout.edges) {
        // 创建步骤ID到步骤数据的映射，用于补充缺失的字段
        const stepMap = new Map()
        steps.forEach(step => {
          stepMap.set(step.stepId, step)
        })
        
        nodes.value = layout.nodes.map(node => {
          // 从数据库步骤数据中获取完整信息（用于补充layout中可能缺失的字段）
          const stepData = stepMap.get(node.data?.stepId)
          
          return {
            ...node,
            data: {
              ...node.data,
              stepId: node.data?.stepId,
              stepName: node.data?.stepName || stepData?.stepName || '',
              configId: node.data?.configId || stepData?.configId || null,
              stepParams: node.data?.stepParams !== undefined ? node.data.stepParams : (stepData?.stepParams || null),
              conditionExpr: node.data?.conditionExpr !== undefined ? node.data.conditionExpr : (stepData?.conditionExpr || null),
              dataTableName: node.data?.dataTableName || stepData?.dataTableName || '',
              loopMode: node.data?.loopMode !== undefined ? node.data.loopMode : (stepData?.loopMode || '0'),
              updateMode: node.data?.updateMode !== undefined ? node.data.updateMode : (stepData?.updateMode || '0'),
              uniqueKeyFields: node.data?.uniqueKeyFields !== undefined ? node.data.uniqueKeyFields : (stepData?.uniqueKeyFields || null),
              apiConfigs: apiConfigs.value
            }
          }
        })
        edges.value = layout.edges.map(e => ({
          ...e,
          sourceHandle: e.sourceHandle || null,
          targetHandle: e.targetHandle || null,
          type: e.type || 'smoothstep'
        }))
        return
      }
    }

    // 否则，从步骤数据构建节点和边
    const nodeMap = new Map()
    const edgeList = []

    steps.forEach((step, index) => {
      const nodeId = `step_${step.stepId}`
      const nodeType = step.nodeType || (index === 0 ? 'start' : index === steps.length - 1 ? 'end' : 'task')
      
      const node = {
        id: nodeId,
        type: nodeType,
        position: {
          x: step.positionX || (index * 200 + 100),
          y: step.positionY || 100
        },
        data: {
          stepId: step.stepId,
          stepName: step.stepName,
          configId: step.configId,
          stepParams: step.stepParams,
          conditionExpr: step.conditionExpr,
          dataTableName: step.dataTableName || '',
          loopMode: step.loopMode || '0',
          updateMode: step.updateMode || '0',
          uniqueKeyFields: step.uniqueKeyFields || null,
          apiConfigs: apiConfigs.value
        }
      }
      
      nodeMap.set(nodeId, node)

      // 构建连接关系
      if (step.sourceStepIds) {
        const sourceIds = typeof step.sourceStepIds === 'string' 
          ? JSON.parse(step.sourceStepIds) 
          : step.sourceStepIds
        
        if (Array.isArray(sourceIds)) {
          sourceIds.forEach(sourceId => {
            const sourceNodeId = `step_${sourceId}`
            if (nodeMap.has(sourceNodeId)) {
              edgeList.push({
                id: `edge_${sourceId}_${step.stepId}`,
                source: sourceNodeId,
                target: nodeId,
                sourceHandle: null,  // 从数据库加载时没有连接点信息，使用默认
                targetHandle: null,
                label: step.conditionExpr || '',
                type: 'smoothstep'
              })
            }
          })
        }
      }
    })

    nodes.value = Array.from(nodeMap.values())
    edges.value = edgeList

    // 如果没有连接关系，按step_order顺序连接
    if (edges.value.length === 0 && nodes.value.length > 1) {
      const sortedNodes = [...nodes.value].sort((a, b) => {
        const stepA = steps.find(s => s.stepId === a.data.stepId)
        const stepB = steps.find(s => s.stepId === b.data.stepId)
        return (stepA?.stepOrder || 0) - (stepB?.stepOrder || 0)
      })

      for (let i = 0; i < sortedNodes.length - 1; i++) {
        edges.value.push({
          id: `edge_${sortedNodes[i].id}_${sortedNodes[i + 1].id}`,
          source: sortedNodes[i].id,
          target: sortedNodes[i + 1].id,
          sourceHandle: null,  // 自动连接时使用默认连接点
          targetHandle: null,
          type: 'smoothstep'
        })
      }
    }
  } catch (error) {
    proxy.$modal.msgError('加载流程数据失败')
  }
}

// 拖拽开始
function handleDragStart(event, nodeType) {
  draggedNodeType.value = nodeType
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('application/vueflow', nodeType)
}

// 拖拽放置
function onDrop(event) {
  event.preventDefault()
  
  const type = event.dataTransfer.getData('application/vueflow')
  if (!type) return

  // 计算相对于画布的坐标
  const canvasElement = event.currentTarget
  const rect = canvasElement.getBoundingClientRect()
  const position = {
    x: event.clientX - rect.left - 100, // 减去节点宽度的一半
    y: event.clientY - rect.top - 50    // 减去节点高度的一半
  }

  addNode(type, position)
  draggedNodeType.value = null
}

// 拖拽悬停
function onDragOver(event) {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

// 添加节点
function addNode(type, position) {
  const nodeId = `node_${Date.now()}`
      const nodeData = {
        stepId: null,
        stepName: type === 'start' ? '开始' : type === 'end' ? '结束' : '任务节点',
        configId: null,
        stepParams: null,
        conditionExpr: null,
        dataTableName: '',
        loopMode: '0',
        updateMode: '0',
        uniqueKeyFields: null,
        apiConfigs: apiConfigs.value
      }

  const newNode = {
    id: nodeId,
    type: type,
    position: position,
    data: nodeData
  }

  nodes.value.push(newNode)
  saveHistory()
}

// 节点变化
function onNodesChange(changes) {
  changes.forEach(change => {
    if (change.type === 'position' && change.dragging === false) {
      saveHistory()
    }
  })
}

// 边变化
function onEdgesChange(changes) {
  // 边变化时保存历史
  if (changes.some(c => c.type === 'remove' || c.type === 'add')) {
    saveHistory()
  }
}

// 节点点击
function onNodeClick(event) {
  selectedElement.value = event.node
  selectedElementType.value = 'node'
}

// 边点击
function onEdgeClick(event) {
  selectedElement.value = event.edge
  selectedElementType.value = 'edge'
}

// 画布点击
function onPaneClick(event) {
  if (event.target === event.currentTarget) {
    selectedElement.value = null
    selectedElementType.value = null
  }
}

// 连接
function onConnect(connection) {
  const newEdge = {
    id: `edge_${connection.source}_${connection.target}`,
    source: connection.source,
    target: connection.target,
    sourceHandle: connection.sourceHandle || null,  // 保存源连接点
    targetHandle: connection.targetHandle || null,  // 保存目标连接点
    type: 'smoothstep',
    label: ''
  }
  edges.value.push(newEdge)
  saveHistory()
}

// 节点拖拽
function onNodeDrag(event) {
  // 拖拽中不保存历史，只在停止时保存
}

// 节点拖拽停止
function onNodeDragStop(event) {
  saveHistory()
}

// 属性更新
function handlePropertyUpdate(updates) {
  if (selectedElementType.value === 'node') {
    const node = selectedElement.value
    if (node) {
      Object.assign(node.data, updates)
    }
  } else if (selectedElementType.value === 'edge') {
    const edge = selectedElement.value
    if (edge) {
      if (updates.label !== undefined) {
        edge.label = updates.label
      }
    }
  }
  saveHistory()
}

// 缩放功能
function zoomIn() {
  if (vueFlowRef.value) {
    const instance = vueFlowRef.value
    if (instance.zoomIn) {
      instance.zoomIn()
    } else if (instance.getViewport) {
      const viewport = instance.getViewport()
      instance.setViewport({ ...viewport, zoom: Math.min(viewport.zoom + 0.1, 2) })
    }
  }
}

function zoomOut() {
  if (vueFlowRef.value) {
    const instance = vueFlowRef.value
    if (instance.zoomOut) {
      instance.zoomOut()
    } else if (instance.getViewport) {
      const viewport = instance.getViewport()
      instance.setViewport({ ...viewport, zoom: Math.max(viewport.zoom - 0.1, 0.2) })
    }
  }
}

function fitView() {
  if (vueFlowRef.value && nodes.value.length > 0) {
    const instance = vueFlowRef.value
    if (instance.fitView) {
      instance.fitView()
    } else if (instance.getViewport) {
      // 计算所有节点的边界
      const minX = Math.min(...nodes.value.map(n => n.position.x))
      const minY = Math.min(...nodes.value.map(n => n.position.y))
      const maxX = Math.max(...nodes.value.map(n => n.position.x + 200))
      const maxY = Math.max(...nodes.value.map(n => n.position.y + 100))
      
      const width = maxX - minX
      const height = maxY - minY
      const container = document.querySelector('.vue-flow-container')
      if (container) {
        const containerWidth = container.clientWidth
        const containerHeight = container.clientHeight
        const zoom = Math.min(containerWidth / width, containerHeight / height, 1) * 0.9
        
        instance.setViewport({
          x: (containerWidth - width * zoom) / 2 - minX * zoom,
          y: (containerHeight - height * zoom) / 2 - minY * zoom,
          zoom
        })
      }
    }
  }
}

// 撤销/重做
function saveHistory() {
  const snapshot = {
    nodes: JSON.parse(JSON.stringify(nodes.value)),
    edges: JSON.parse(JSON.stringify(edges.value))
  }
  
  // 移除当前位置之后的历史
  history.value = history.value.slice(0, historyIndex.value + 1)
  history.value.push(snapshot)
  historyIndex.value = history.value.length - 1
  
  // 限制历史记录数量
  if (history.value.length > 50) {
    history.value.shift()
    historyIndex.value--
  }
}

function undo() {
  if (canUndo.value) {
    historyIndex.value--
    const snapshot = history.value[historyIndex.value]
    nodes.value = JSON.parse(JSON.stringify(snapshot.nodes))
    edges.value = JSON.parse(JSON.stringify(snapshot.edges))
  }
}

function redo() {
  if (canRedo.value) {
    historyIndex.value++
    const snapshot = history.value[historyIndex.value]
    nodes.value = JSON.parse(JSON.stringify(snapshot.nodes))
    edges.value = JSON.parse(JSON.stringify(snapshot.edges))
  }
}

// 删除选中元素
function deleteSelected() {
  if (selectedElementType.value === 'node') {
    const nodeId = selectedElement.value.id
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
    selectedElement.value = null
    selectedElementType.value = null
  } else if (selectedElementType.value === 'edge') {
    const edgeId = selectedElement.value.id
    edges.value = edges.value.filter(e => e.id !== edgeId)
    selectedElement.value = null
    selectedElementType.value = null
  }
  saveHistory()
}

// 保存
async function handleSave() {
  try {
    if (nodes.value.length === 0) {
      proxy.$modal.msgWarning('请至少添加一个节点')
      return
    }

    // 使用拓扑排序计算step_order
    const sortedNodes = topologicalSort(nodes.value, edges.value)
    
    const createList = []
    const updateList = []
    
    // 构建步骤数据
    sortedNodes.forEach((node, index) => {
      // 计算连接关系
      const sourceIds = edges.value
        .filter(e => e.target === node.id)
        .map(e => {
          const sourceNode = nodes.value.find(n => n.id === e.source)
          return sourceNode?.data?.stepId
        })
        .filter(id => id !== undefined && id !== null)

      const targetIds = edges.value
        .filter(e => e.source === node.id)
        .map(e => {
          const targetNode = nodes.value.find(n => n.id === e.target)
          return targetNode?.data?.stepId
        })
        .filter(id => id !== undefined && id !== null)

      // 对于任务节点，configId 是必填的
      if (node.type === 'task' && !node.data.configId) {
        proxy.$modal.msgWarning(`节点"${node.data.stepName || `步骤${index + 1}`}"需要配置接口`)
        throw new Error(`节点"${node.data.stepName || `步骤${index + 1}`}"需要配置接口`)
      }

      const stepData = {
        workflowId: props.workflowId,
        stepOrder: index + 1,
        stepName: node.data.stepName || `步骤${index + 1}`,
        // 开始和结束节点可以没有 configId，任务节点必须有
        configId: node.type === 'task' ? (node.data.configId || 0) : (node.data.configId || 0),
        stepParams: node.data.stepParams || null,
        conditionExpr: node.data.conditionExpr || null,
        dataTableName: node.data.dataTableName || null,
        loopMode: node.data.loopMode || '0',
        updateMode: node.data.updateMode || '0',
        uniqueKeyFields: node.data.uniqueKeyFields || null,
        positionX: Math.round(node.position.x),
        positionY: Math.round(node.position.y),
        nodeType: node.type || 'task',
        sourceStepIds: sourceIds.length > 0 ? JSON.stringify(sourceIds) : null,
        targetStepIds: targetIds.length > 0 ? JSON.stringify(targetIds) : null
      }

      // 保存布局数据（只在第一个节点保存完整布局）
      if (index === 0) {
        const layoutObj = {
          nodes: nodes.value.map(n => ({
            id: n.id,
            type: n.type,
            position: n.position,
            data: {
              stepId: n.data.stepId,
              stepName: n.data.stepName,
              configId: n.data.configId,
              stepParams: n.data.stepParams || null,
              conditionExpr: n.data.conditionExpr || null,
              dataTableName: n.data.dataTableName || '',
              loopMode: n.data.loopMode || '0',
              updateMode: n.data.updateMode || '0',
              uniqueKeyFields: n.data.uniqueKeyFields || null
            }
          })),
          edges: edges.value.map(e => ({
            id: e.id,
            source: e.source,
            target: e.target,
            sourceHandle: e.sourceHandle || null,
            targetHandle: e.targetHandle || null,
            label: e.label || ''
          }))
        }
        // layoutData 应该直接是对象，不是 JSON 字符串（后端期望 dict | list | None）
        stepData.layoutData = layoutObj
      }

      if (node.data.stepId) {
        stepData.stepId = node.data.stepId
        updateList.push(stepData)
      } else {
        createList.push(stepData)
      }
    })

    // 找出需要删除的步骤（数据库中存在但画布中不存在的）
    const existingStepIds = new Set(
      nodes.value
        .map(n => n.data.stepId)
        .filter(id => id !== undefined && id !== null)
    )

    // 获取当前流程的所有步骤
    const currentWorkflow = await getWorkflowConfig(props.workflowId)
    const allSteps = currentWorkflow.data.steps || []
    const deleteIds = allSteps
      .filter(step => step.stepId && !existingStepIds.has(step.stepId))
      .map(step => step.stepId)
      .filter(id => id !== undefined && id !== null)

    // 调用批量保存API
    await batchSaveWorkflowStep({
      create: createList.length > 0 ? createList : [],
      update: updateList.length > 0 ? updateList : [],
      delete: deleteIds.length > 0 ? deleteIds : []
    })

    proxy.$modal.msgSuccess('保存成功')
    emit('save')
  } catch (error) {
    console.error('保存失败:', error)
    proxy.$modal.msgError('保存失败：' + (error.message || '未知错误'))
  }
}

// 拓扑排序计算执行顺序
function topologicalSort(nodes, edges) {
  if (nodes.length === 0) {
    return []
  }
  
  // 如果没有边，直接返回节点顺序
  if (edges.length === 0) {
    return [...nodes]
  }
  
  // 构建邻接表和入度
  const inDegree = new Map()
  const adjList = new Map()
  
  nodes.forEach(node => {
    inDegree.set(node.id, 0)
    adjList.set(node.id, [])
  })
  
  edges.forEach(edge => {
    const target = edge.target
    const source = edge.source
    // 确保 source 和 target 都在节点列表中
    if (inDegree.has(source) && inDegree.has(target)) {
      inDegree.set(target, (inDegree.get(target) || 0) + 1)
      const sourceList = adjList.get(source)
      if (sourceList) {
        sourceList.push(target)
      }
    }
  })
  
  // 找到所有入度为0的节点（开始节点）
  const queue = []
  nodes.forEach(node => {
    if (inDegree.get(node.id) === 0) {
      queue.push(node)
    }
  })
  
  // 如果没有入度为0的节点，说明有环，返回原始顺序
  if (queue.length === 0) {
    return [...nodes]
  }
  
  const result = []
  while (queue.length > 0) {
    const node = queue.shift()
    result.push(node)
    
    // 更新相邻节点的入度
    const nodeAdjList = adjList.get(node.id)
    if (nodeAdjList) {
      nodeAdjList.forEach(targetId => {
        if (inDegree.has(targetId)) {
          const newInDegree = inDegree.get(targetId) - 1
          inDegree.set(targetId, newInDegree)
          if (newInDegree === 0) {
            const targetNode = nodes.find(n => n.id === targetId)
            if (targetNode) {
              queue.push(targetNode)
            }
          }
        }
      })
    }
  }
  
  // 如果还有节点未处理，说明有环，返回原始顺序
  if (result.length !== nodes.length) {
    return [...nodes]
  }
  
  return result
}

// 暴露保存方法给父组件
defineExpose({
  handleSave
})

// 键盘快捷键
let keydownHandler = null

// 检查焦点是否在可编辑元素中
function isEditableElement(target) {
  if (!target) return false
  
  // 检查是否是输入框、文本域等可编辑元素
  const tagName = target.tagName?.toLowerCase()
  const isInput = tagName === 'input' || tagName === 'textarea'
  const isContentEditable = target.contentEditable === 'true'
  const isEditable = target.isContentEditable
  
  // 检查是否在 Element Plus 的输入组件中
  const isInElInput = target.closest('.el-input__inner') || 
                      target.closest('.el-textarea__inner') ||
                      target.closest('.el-select__input') ||
                      target.closest('.el-input-number')
  
  return isInput || isContentEditable || isEditable || isInElInput
}

onMounted(() => {
  keydownHandler = (event) => {
    // 如果焦点在可编辑元素中，不处理快捷键（除了撤销/重做）
    const isEditing = isEditableElement(event.target)
    
    if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !event.shiftKey) {
      // 撤销操作：如果不在可编辑元素中，或者可编辑元素支持撤销，则处理
      if (!isEditing) {
        event.preventDefault()
        undo()
      }
    } else if ((event.ctrlKey || event.metaKey) && (event.key === 'y' || (event.key === 'z' && event.shiftKey))) {
      // 重做操作：如果不在可编辑元素中，则处理
      if (!isEditing) {
        event.preventDefault()
        redo()
      }
    } else if ((event.key === 'Delete' || event.key === 'Backspace') && !isEditing) {
      // 删除操作：只有在不在可编辑元素中时才触发删除节点
      if (selectedElement.value) {
        event.preventDefault()
        deleteSelected()
      }
    }
  }

  window.addEventListener('keydown', keydownHandler)
})

onUnmounted(() => {
  if (keydownHandler) {
    window.removeEventListener('keydown', keydownHandler)
  }
})
</script>

<style scoped lang="scss">
.workflow-editor-container {
  display: flex;
  height: 100%;
  width: 100%;
  background: #f5f5f5;
}

.editor-toolbar {
  width: 200px;
  background: white;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;

  .toolbar-header {
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;

    h3 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
    }
  }

  .toolbar-scrollbar {
    flex: 1;
  }

  .node-types {
    padding: 16px;

    .node-type-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
      margin-bottom: 12px;
      border: 2px dashed #d1d5db;
      border-radius: 8px;
      cursor: move;
      transition: all 0.2s;

      &:hover {
        border-color: #3b82f6;
        background: #eff6ff;
      }

      .node-icon {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        margin-bottom: 8px;

        &.start-icon {
          background: #10b981;
        }

        &.task-icon {
          width: 80px;
          height: 48px;
          border-radius: 8px;
          background: #3b82f6;
        }

        &.end-icon {
          background: #ef4444;
        }
      }

      .node-label {
        font-size: 12px;
        color: #6b7280;
      }
    }
  }
}

.editor-canvas {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;

  .canvas-toolbar {
    padding: 8px 16px;
    background: white;
    border-bottom: 1px solid #e5e7eb;
    z-index: 10;
  }

  .vue-flow-container {
    flex: 1;
    background: #fafafa;
  }
}

.editor-properties {
  width: 300px;
  background: white;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;

  .properties-header {
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;

    h3 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
    }
  }

  .properties-scrollbar {
    flex: 1;
  }

  .empty-properties {
    padding: 40px 20px;
  }
}
</style>
