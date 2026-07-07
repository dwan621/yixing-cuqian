<template>
  <el-container class="app-container">
    <el-header style="text-align:center;font-size:24px;font-weight:bold;padding:20px 0">
      以型促签 · 售前快速原型生成器
    </el-header>
    <el-main>
      <RequirementForm v-if="plan.phase === 'form'" />
      <ProgressPanel v-else-if="plan.phase === 'generating'" />
      <PlanView v-else-if="plan.phase === 'done'" />
      <el-result v-else-if="plan.phase === 'error'" status="error" :title="plan.error ?? '未知错误'" sub-title="请返回重新提交">
        <template #extra><el-button type="primary" @click="plan.reset()">返回</el-button></template>
      </el-result>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { usePlanStore } from '@/stores/plan'
import RequirementForm from '@/components/RequirementForm.vue'
import ProgressPanel from '@/components/ProgressPanel.vue'
import PlanView from '@/components/PlanView.vue'
const plan = usePlanStore()
</script>

<style>
.app-container { max-width: 960px; margin: 0 auto; }
</style>
