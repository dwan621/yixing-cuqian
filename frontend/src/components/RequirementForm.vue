<template>
  <el-card header="客户需求输入">
    <el-form :model="form" :rules="rules" ref="formRef" label-width="130px" @submit.prevent="handleSubmit">
      <el-form-item label="客户行业" prop="industry">
        <el-input v-model="form.industry" placeholder="如：制造业、金融、零售" />
      </el-form-item>
      <el-form-item label="关注场景" prop="scenario">
        <el-input v-model="form.scenario" placeholder="如：供应链管理、风控" />
      </el-form-item>
      <el-form-item label="客户规模" prop="scale">
        <el-input v-model="form.scale" placeholder="如：500 人以上" />
      </el-form-item>
      <el-form-item label="演示时长（分钟）" prop="demo_minutes">
        <el-input-number v-model="form.demo_minutes" :min="1" :max="120" />
      </el-form-item>
      <el-form-item label="客户背景">
        <el-input v-model="form.background" type="textarea" :rows="3" placeholder="（选填）客户痛点、竞品情况等" />
      </el-form-item>
      <el-form-item label="演示模板">
        <el-select v-model="form.template" placeholder="（选填）选择预设模板" clearable>
          <el-option label="供应链演示模板" value="供应链演示模板" />
          <el-option label="风控演示模板" value="风控演示模板" />
          <el-option label="数据分析演示模板" value="数据分析演示模板" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit">生成方案</el-button>
        <el-button @click="formRef?.resetFields()">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { usePlanStore } from '@/stores/plan'

const plan = usePlanStore()
const formRef = ref<FormInstance>()
const form = reactive({ industry: '', scenario: '', scale: '', demo_minutes: 15, background: '', template: '' })

const rules: FormRules = {
  industry: [{ required: true, message: '请输入客户行业', trigger: 'blur' }],
  scenario: [{ required: true, message: '请输入关注场景', trigger: 'blur' }],
  scale: [{ required: true, message: '请输入客户规模', trigger: 'blur' }],
  demo_minutes: [{ required: true, message: '请选择演示时长', trigger: 'change' }],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  plan.submit({
    industry: form.industry, scenario: form.scenario, scale: form.scale,
    demo_minutes: form.demo_minutes,
    background: form.background || undefined, template: form.template || undefined,
  })
}
</script>
