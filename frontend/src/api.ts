export interface RequirementInput {
  industry: string; scenario: string; scale: string
  demo_minutes: number; background?: string; template?: string
}

export interface AgentEvent {
  agent: string; status: 'running' | 'done' | 'failed'
  elapsed_ms?: number; error?: string
}

export interface PlanResult {
  session_id: string; markdown: string
  functions: Record<string, any>[]
  mock_data: Record<string, any>
  architecture: string; demo_script: Record<string, any>
}

export async function submitRequirement(req: RequirementInput): Promise<string> {
  const r = await fetch('/api/generate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req),
  })
  if (!r.ok) throw new Error(await r.text())
  return (await r.json()).session_id
}

export function streamProgress(
  sessionId: string,
  onEvent: (ev: AgentEvent) => void,
  onDone: () => void
): () => void {
  const evt = new EventSource(`/api/progress/${sessionId}`)
  evt.onmessage = (msg) => {
    const data = JSON.parse(msg.data)
    if (data.agent === 'pipeline' && data.status === 'done') { evt.close(); onDone(); return }
    if (data.error) { evt.close(); onEvent({ agent: 'pipeline', status: 'failed', error: data.error }); onDone(); return }
    onEvent(data as AgentEvent)
  }
  evt.onerror = () => { evt.close(); onDone() }
  return () => evt.close()
}

export async function fetchResult(sid: string): Promise<PlanResult> {
  const r = await fetch(`/api/result/${sid}`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export function exportUrl(sid: string): string { return `/api/export/${sid}?format=md` }
