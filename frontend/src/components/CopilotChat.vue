<script setup lang="ts">
import { ref, computed, nextTick } from "vue";

type MessageRole = "user" | "assistant" | "system";

interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  agent?: string;
  confidence?: number;
  context?: Record<string, unknown>;
}

interface CopilotContext {
  selectedNodes?: string[];
  currentView?: string;
  objectTypes?: string[];
  recentEvents?: string[];
  tick?: number;
}

interface ProposalSuggestion {
  proposal_id: string;
  title: string;
  description: string;
  code_preview?: string;
  impact_analysis?: string[];
  requires_approval: boolean;
}

const props = defineProps<{
  context: CopilotContext;
  busy?: boolean;
}>();

const emit = defineEmits<{
  (event: "send-message", payload: { intent: string; prompt: string; context: CopilotContext }): void;
  (event: "apply-proposal", proposalId: string): void;
  (event: "refine-proposal", proposalId: string, feedback: string): void;
  (event: "reject-proposal", proposalId: string): void;
}>();

const userInput = ref<string>("");
const messages = ref<ChatMessage[]>([
  {
    id: "welcome",
    role: "assistant",
    content: "你好！我是 Genesis Copilot。我可以帮助你创建本体结构、编写逻辑规则、生成实体数据或分析仿真结果。请告诉我你想做什么？",
    timestamp: new Date().toISOString(),
    agent: "Supervisor",
  },
]);
const currentSuggestion = ref<ProposalSuggestion | null>(null);
const chatContainer = ref<HTMLDivElement | null>(null);
const isTyping = ref<boolean>(false);

const hasMessages = computed(() => messages.value.length > 1);
const canSend = computed(() => userInput.value.trim().length > 0 && !props.busy && !isTyping.value);

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
};

const scrollToBottom = async () => {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  }
};

const sendMessage = () => {
  const content = userInput.value.trim();
  if (!content || !canSend.value) return;

  // Add user message
  const userMessage: ChatMessage = {
    id: `user-${Date.now()}`,
    role: "user",
    content,
    timestamp: new Date().toISOString(),
  };
  messages.value.push(userMessage);
  
  // Clear input
  userInput.value = "";
  
  scrollToBottom();

  // Emit to parent for API call
  emit("send-message", {
    intent: classifyIntent(content),
    prompt: content,
    context: props.context,
  });
};

const classifyIntent = (content: string): string => {
  const lowered = content.toLowerCase();
  if (lowered.includes("创建") || lowered.includes("添加") || lowered.includes("生成") || lowered.includes("ontology") || lowered.includes("schema")) {
    return "ontology";
  }
  if (lowered.includes("规则") || lowered.includes("逻辑") || lowered.includes("动作") || lowered.includes("action") || lowered.includes("rule")) {
    return "logic";
  }
  if (lowered.includes("批量") || lowered.includes("填充") || lowered.includes("生成") || lowered.includes("populate") || lowered.includes("seed")) {
    return "workflow";
  }
  if (lowered.includes("分析") || lowered.includes("查询") || lowered.includes("统计") || lowered.includes("analytics") || lowered.includes("query")) {
    return "data";
  }
  return "general";
};

const addAssistantMessage = (response: {
  agent: string;
  confidence: number;
  plan: string[];
  guardrail: { allowed: boolean; reasons: string[] };
  proposal?: ProposalSuggestion;
}) => {
  isTyping.value = true;
  
  setTimeout(() => {
    const message: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: generateResponseText(response),
      timestamp: new Date().toISOString(),
      agent: response.agent,
      confidence: response.confidence,
      context: { plan: response.plan },
    };
    messages.value.push(message);
    
    if (response.proposal) {
      currentSuggestion.value = response.proposal;
    }
    
    isTyping.value = false;
    scrollToBottom();
  }, 800);
};

const generateResponseText = (response: { agent: string; plan: string[]; guardrail: { allowed: boolean; reasons: string[] } }): string => {
  if (!response.guardrail.allowed) {
    return `请求被安全护栏阻止。原因：${response.guardrail.reasons.join("，")}`;
  }
  
  let text = `我已分析你的请求，将由 **${response.agent}** 代理处理。\n\n执行计划：`;
  response.plan.forEach((step, index) => {
    text += `\n${index + 1}. ${step}`;
  });
  
  return text;
};

const applyProposal = () => {
  if (currentSuggestion.value) {
    emit("apply-proposal", currentSuggestion.value.proposal_id);
    currentSuggestion.value = null;
  }
};

const refineProposal = () => {
  if (currentSuggestion.value) {
    const feedback = prompt("请输入改进建议：");
    if (feedback) {
      emit("refine-proposal", currentSuggestion.value.proposal_id, feedback);
    }
  }
};

const rejectProposal = () => {
  if (currentSuggestion.value) {
    emit("reject-proposal", currentSuggestion.value.proposal_id);
    currentSuggestion.value = null;
  }
};

const clearChat = () => {
  messages.value = [
    {
      id: "welcome",
      role: "assistant",
      content: "你好！我是 Genesis Copilot。我可以帮助你创建本体结构、编写逻辑规则、生成实体数据或分析仿真结果。请告诉我你想做什么？",
      timestamp: new Date().toISOString(),
      agent: "Supervisor",
    },
  ];
  currentSuggestion.value = null;
};

const quickPrompts = [
  "创建一个无人机单位类型",
  "添加巡逻动作规则",
  "生成50个测试实体",
  "分析当前仿真性能",
];

const useQuickPrompt = (prompt: string) => {
  userInput.value = prompt;
};

defineExpose({
  addAssistantMessage,
  scrollToBottom,
});
</script>

<template>
  <section class="copilot-chat-panel">
    <header class="chat-header">
      <h3>Copilot AI 助手</h3>
      <div class="header-actions">
        <span v-if="context.selectedNodes?.length" class="context-badge">
          已选 {{ context.selectedNodes.length }} 个节点
        </span>
        <span v-if="context.currentView" class="context-badge">
          {{ context.currentView }}
        </span>
        <button type="button" class="clear-btn" @click="clearChat" :disabled="!hasMessages">
          清空对话
        </button>
      </div>
    </header>

    <div ref="chatContainer" class="chat-messages">
      <div
        v-for="message in messages"
        :key="message.id"
        class="message"
        :class="`role-${message.role}`"
      >
        <div class="message-header">
          <strong v-if="message.role === 'user'">你</strong>
          <strong v-else-if="message.agent">{{ message.agent }}</strong>
          <strong v-else>Copilot</strong>
          <span class="timestamp">{{ formatTime(message.timestamp) }}</span>
          <span v-if="message.confidence" class="confidence-badge">
            置信度: {{ (message.confidence * 100).toFixed(0) }}%
          </span>
        </div>
        <div class="message-content">
          <pre v-if="message.context?.plan">{{ message.content }}</pre>
          <template v-else>{{ message.content }}</template>
        </div>
      </div>

      <div v-if="isTyping" class="message role-assistant typing">
        <div class="message-content">
          <span class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </span>
        </div>
      </div>
    </div>

    <div v-if="currentSuggestion" class="proposal-suggestion">
      <h4>变更建议: {{ currentSuggestion.title }}</h4>
      <p class="description">{{ currentSuggestion.description }}</p>
      <div v-if="currentSuggestion.code_preview" class="code-preview">
        <pre>{{ currentSuggestion.code_preview }}</pre>
      </div>
      <ul v-if="currentSuggestion.impact_analysis" class="impact-list">
        <li v-for="impact in currentSuggestion.impact_analysis" :key="impact">
          {{ impact }}
        </li>
      </ul>
      <div class="proposal-actions">
        <button type="button" class="apply-btn" @click="applyProposal">
          应用变更
        </button>
        <button type="button" class="refine-btn" @click="refineProposal">
          细化调整
        </button>
        <button type="button" class="reject-btn" @click="rejectProposal">
          拒绝
        </button>
      </div>
      <p v-if="currentSuggestion.requires_approval" class="approval-notice">
        此变更需要管理员审批
      </p>
    </div>

    <div class="quick-prompts">
      <button
        v-for="prompt in quickPrompts"
        :key="prompt"
        type="button"
        class="quick-prompt-btn"
        @click="useQuickPrompt(prompt)"
      >
        {{ prompt }}
      </button>
    </div>

    <div class="chat-input-area">
      <textarea
        v-model="userInput"
        placeholder="输入你的需求，例如：创建一个坦克单位，带有攻击动作..."
        rows="3"
        @keydown.enter.prevent="sendMessage"
      />
      <button
        type="button"
        class="send-btn"
        :disabled="!canSend"
        @click="sendMessage"
      >
        发送
      </button>
    </div>
  </section>
</template>

<style scoped>
.copilot-chat-panel {
  display: grid;
  grid-template-rows: auto 1fr auto auto auto;
  gap: 12px;
  height: 100%;
  max-height: 600px;
  border: 1px solid #cde0e8;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(120deg, #0d6c8d, #2a8e72);
  color: #fff;
}

.chat-header h3 {
  margin: 0;
  font-size: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.context-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 999px;
}

.clear-btn {
  border: 1px solid rgba(255, 255, 255, 0.5);
  background: transparent;
  color: #fff;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.clear-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-messages {
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f8fbfd;
}

.message {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}

.role-user {
  align-self: flex-end;
  background: #0d6c8d;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.role-user .message-header {
  color: rgba(255, 255, 255, 0.8);
}

.role-assistant {
  align-self: flex-start;
  background: #fff;
  border: 1px solid #d2e4ec;
  border-bottom-left-radius: 4px;
}

.role-assistant .message-header {
  color: #0d6c8d;
}

.timestamp {
  font-size: 11px;
  color: #7fa6bf;
}

.confidence-badge {
  font-size: 10px;
  padding: 2px 6px;
  background: #e9f4fa;
  color: #0d6c8d;
  border-radius: 999px;
}

.message-content pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 13px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #7fa6bf;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.proposal-suggestion {
  margin: 0 16px;
  padding: 12px;
  background: #fff9e6;
  border: 1px solid #f0d78c;
  border-radius: 10px;
}

.proposal-suggestion h4 {
  margin: 0 0 8px;
  color: #744210;
  font-size: 14px;
}

.description {
  margin: 0 0 12px;
  color: #975a16;
  font-size: 13px;
}

.code-preview {
  background: #1f2937;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 12px;
  overflow-x: auto;
}

.code-preview pre {
  margin: 0;
  color: #e5e7eb;
  font-size: 12px;
  font-family: 'Monaco', 'Consolas', monospace;
}

.impact-list {
  margin: 0 0 12px;
  padding-left: 18px;
  font-size: 12px;
  color: #744210;
}

.impact-list li {
  margin-bottom: 4px;
}

.proposal-actions {
  display: flex;
  gap: 8px;
}

.apply-btn {
  background: #2a8e72;
  color: #fff;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.refine-btn {
  background: #f4fafc;
  color: #15425a;
  border: 1px solid #7fa6bf;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.reject-btn {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.approval-notice {
  margin: 8px 0 0;
  font-size: 11px;
  color: #975a16;
  font-style: italic;
}

.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 16px;
}

.quick-prompt-btn {
  border: 1px solid #d2e4ec;
  background: #f8fbfd;
  color: #365364;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 11px;
  white-space: nowrap;
}

.quick-prompt-btn:hover {
  background: #e9f4fa;
  border-color: #0d6c8d;
}

.chat-input-area {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #d2e4ec;
}

.chat-input-area textarea {
  border: 1px solid #c5d9e4;
  border-radius: 8px;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 14px;
  resize: none;
  outline: none;
}

.chat-input-area textarea:focus {
  border-color: #0d6c8d;
}

.send-btn {
  background: linear-gradient(120deg, #0d6c8d, #2a8e72);
  color: #fff;
  border: none;
  padding: 8px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  align-self: stretch;
}

.send-btn:disabled {
  background: #c5d9e4;
  cursor: not-allowed;
}
</style>
