import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import RequirementForm from '@/components/RequirementForm.vue'

describe('RequirementForm', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('renders all required fields', () => {
    const wrapper = mount(RequirementForm, { global: { plugins: [ElementPlus] } })
    expect(wrapper.find('input[placeholder*="制造业"]').exists()).toBe(true)
    expect(wrapper.find('input[placeholder*="供应链"]').exists()).toBe(true)
    expect(wrapper.findAll('button').some(b => b.text().includes('生成方案'))).toBe(true)
  })
})
