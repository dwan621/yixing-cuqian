<template>
  <el-card header="正在生成方案…">
    <el-steps :active="activeStep" finish-status="success" direction="vertical">
      <el-step v-for="agent in orderedAgents" :key="agent"
        :title="agentLabel(agent)"
        :status="stepStatus(agent)"
        :description="stepDescription(agent)" />
    </el-steps>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { usePlanStore } from '@/stores/plan'

const plan = usePlanStore()
const orderedAgents = ['parse', 'design', 'content', 'data', 'architecture', 'integrate']
const labels: Record<string, string> = {
  parse: '需求解析', design: '方案设计', content: '内容生成',
  data: '数据模拟', architecture: '架构描述', integrate: '结果整合',
}
function agentLabel(n: string) { return labels[n] ?? n }

const activeStep = computed(() => plan.events.filter(e => e.status === 'done').length)

function stepStatus(name: string): 'wait' | 'process' | 'finish' | 'error' {
  const ev = plan.events.find(e => e.agent === name)
  if (!ev) return 'wait'
  if (ev.status === 'done') return 'finish'
  if (ev.status === 'failed') return 'error'
  return 'process'
}

function stepDescription(name: string): string {
  const ev = plan.events.find(e => e.agent === name)
  if (!ev) return ''
  if (ev.status === 'done') return `${ev.elapsed_ms}ms`
  if (ev.status === 'failed') return ev.error ?? '失败'
  return '执行中…'
}
</script>
