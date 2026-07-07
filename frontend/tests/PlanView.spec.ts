import { describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PlanView from '@/components/PlanView.vue'
import { usePlanStore } from '@/stores/plan'

describe('PlanView', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('renders markdown from store result', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = usePlanStore()
    store.result = { session_id: 's1', markdown: '# 售前方案\n\n测试', functions: [], mock_data: {}, architecture: '', demo_script: {} }
    store.phase = 'done'
    const wrapper = mount(PlanView, { global: { plugins: [pinia] } })
    await nextTick()
    expect(wrapper.html()).toContain('售前方案')
  })
})
