<template>
  <div class="chat-container">
    <!-- 新增控制栏 -->
    <div class="control-bar">
      <el-switch
        v-model="showThinking"
        active-text="显示思考过程"
        inactive-text="隐藏思考过程"
      />
    </div>
    <!-- 消息展示区域 -->
    <div class="message-list" ref="messageContainer">
      <!-- 消息项循环 -->
      <div v-for="(msg, index) in messages" :key="index">
        <!-- 用户消息 -->
        <div v-if="msg.isUser" class="user-message">
          <div class="message-bubble">{{ msg.text }}</div>
        </div>

        <!-- AI消息 -->
        <div v-else class="ai-message">
          <!-- 思考过程区块 -->
          <div v-if="showThinking && msg.think" class="think-section">
            <div class="think-label">思考过程</div>
            <pre class="think-content">{{ msg.think }}</pre>
          </div>

          <!-- 正式回答区块 -->
          <div class="answer-bubble">
            <div v-html="renderMarkdown(msg.text)"></div>
            <div class="meta-info">
              <span>原始时间戳: {{ msg.meta.timestamp }}</span>
              <span>状态码: {{ msg.meta.mcp_status }}</span>
              <span>数据时间: {{ formatDate(msg.meta.timestamp) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <el-input v-model="inputMessage" @keyup.enter.native="sendMessage"/>
      <el-button @click="sendMessage" :loading="loading">发送</el-button>
    </div>
  </div>
</template>

<script>
import { postChat } from '@/api/ai/chat'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

// 初始化Markdown解析器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
})
export default {
  data() {
    return {
      messages: [],
      inputMessage: '',
      loading: false,
      showThinking: false // 新增显示控制状态
    }
  },
  methods: {
    // 新增Markdown渲染方法
    renderMarkdown(content) {
      if (!content && content !== 0) return '' // 处理null/undefined
      const unsafeHtml = md.render(content.toString())
      return DOMPurify.sanitize(unsafeHtml)
    },
    formatDate(timestamp) {
      try {
        if (timestamp === undefined || timestamp === null) return 'N/A'

        // 统一转换为数值类型
        let ts = Number(timestamp)
        if (isNaN(ts)) return 'N/A'

        // 自动识别秒级时间戳（10位）
        if (ts.toString().length === 10) ts *= 1000

        const date = new Date(ts)
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        })
      } catch (e) {
        return 'N/A'
      }
    },
    parseResponse(response) {
      // 强化安全过滤
      const cleanHtml = DOMPurify.sanitize(response.response, {
        ALLOWED_TAGS: ['think'], // 仅允许think标签
        ALLOWED_ATTR: [] // 禁止所有属性
      })

      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = cleanHtml

      // 提取思考内容
      const thinkEl = tempDiv.querySelector('think')
      const thinkContent = thinkEl?.textContent.trim() || ''

      // 移除think标签保留其他内容
      const processedText = tempDiv.innerHTML.replace(/<think>.*<\/think>/gis, '')

      return {
        think: thinkContent,
        text: processedText,
        meta: {
          mcp_status: response.mcp_status || 200, // 默认状态码
          timestamp: response.timestamp || Date.now() // 默认当前时间
        }
      }
    },
    async sendMessage() {
      if (!this.inputMessage.trim()) return

      const userMsg = { text: this.inputMessage, isUser: true }
      this.messages.push(userMsg)
      const botMsg = {
        think: '',
        text: '思考中...',
        meta: {},
        isUser: false
      }
      this.messages.push(botMsg)

      this.loading = true
      try {
        const { data } = await postChat({ query: this.inputMessage })
        const parsed = this.parseResponse(data)

        this.$set(this.messages, this.messages.length - 1, {
          isUser: false,
          text: parsed.text,
          think: parsed.think,
          meta: parsed.meta
        })
      } catch (error) {
        this.$set(this.messages, this.messages.length - 1, {
          isUser: false,
          text: `错误：${error.message}`,
          meta: { // 保持meta结构
            mcp_status: 500,
            timestamp: Date.now()
          }
        })
      } finally {
        this.inputMessage = ''
        this.loading = false
        this.$nextTick(() => {
          this.$refs.messageContainer.scrollTop =
            this.$refs.messageContainer.scrollHeight
        })
      }
    }
  }
}
</script>

<style scoped>
.chat-container {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  height: 80vh; /* 改为视窗百分比 */
  min-height: 400px; /* 设置最小高度 */
  max-height: 1000px; /* 设置最大高度 */
  display: flex;
  flex-direction: column;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  height: calc(100% - 72px); /* 72px为输入区域高度 */
}

.message-item {
  margin: 10px 0;
  display: flex;
}

.user-message {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 4px;
  background: #f0f2f5;
}

.user-message .message-bubble {
  background: #409EFF;
  color: white;
}

.input-area {
  border-top: 1px solid #ebeef5;
  padding: 20px;
  display: flex;
  gap: 10px;
}

.input-box {
  flex: 1;
}

/* 新增思考过程样式 */
.ai-message {
  width: 100%;
  max-width: 80%;
}

.think-section {
  background: #f8f9fa;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 8px;
  border-left: 3px solid #e9ecef;
}

.think-label {
  font-size: 0.9em;
  color: #6c757d;
  margin-bottom: 6px;
  font-weight: 500;
}

.think-content {
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 0.85em;
  color: #495057;
  margin: 0;
  line-height: 1.4;
}

/* 调整回答气泡 */
.answer-bubble {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

/* 元信息样式 */
.meta-info {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #dee2e6;
  font-size: 0.8em;
  color: #868e96;
  display: flex;
  gap: 15px;
}

/* 保持原有用户消息样式 */
.user-message .message-bubble {
  background: #409EFF;
  color: white;
}
/* 新增加载样式 */
.loading-placeholder {
  color: #666;
  padding: 12px;
  font-style: italic;
}
.el-icon-loading {
  margin-right: 5px;
  animation: rotating 2s linear infinite;
}
@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.control-bar {
  padding: 12px 20px;
  border-bottom: 1px solid #ebeef5;
  background: #f8f9fa;
  display: flex;
  align-items: center;
  height: 56px;
}

.el-switch {
  margin-left: auto;
}
.think-section {
  transition: all 0.3s ease;
  max-height: 500px;
  overflow: hidden;
}

.think-section-leave-to {
  max-height: 0;
  opacity: 0;
  margin-bottom: 0;
  padding: 0;
}
</style>

