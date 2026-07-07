import { defineStore } from 'pinia'
import { ref } from 'vue'
import { submitRequirement, streamProgress, fetchResult, exportUrl, type AgentEvent, type PlanResult, type RequirementInput } from '@/api'

export const usePlanStore = defineStore('plan', () => {
  const phase = ref<'form' | 'generating' | 'done' | 'error'>('form')
  const sessionId = ref('')
  const events = ref<AgentEvent[]>([])
  const result = ref<PlanResult | null>(null)
  const error = ref<string | null>(null)
  let cancel: (() => void) | null = null

  async function submit(req: RequirementInput) {
    phase.value = 'generating'; events.value = []; result.value = null; error.value = null
    try {
      sessionId.value = await submitRequirement(req)
      cancel = streamProgress(
        sessionId.value,
        (ev) => { events.value = [...events.value, ev] },
        async () => {
          const last = events.value[events.value.length - 1]
          if (last?.status === 'failed' || last?.error) {
            phase.value = 'error'; error.value = last?.error || 'Pipeline failed'; return
          }
          result.value = await fetchResult(sessionId.value)
          phase.value = 'done'
        },
      )
    } catch (e: any) { phase.value = 'error'; error.value = e.message }
  }

  function reset() { cancel?.(); phase.value = 'form'; events.value = []; result.value = null; error.value = null }
  function exportLink() { return sessionId.value ? exportUrl(sessionId.value) : '' }
  return { phase, sessionId, events, result, error, submit, reset, exportLink }
})
