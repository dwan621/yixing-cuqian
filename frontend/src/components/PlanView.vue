<template>
  <el-card header="生成结果">
    <div v-html="rendered" class="markdown-body"></div>
    <ExportButton style="margin-top:16px" />
    <el-button style="margin-top:16px;margin-left:12px" @click="plan.reset()">返回重新生成</el-button>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import { usePlanStore } from '@/stores/plan'
import ExportButton from './ExportButton.vue'

const plan = usePlanStore()
const rendered = computed(() => marked(plan.result?.markdown ?? ''))
</script>

<style>
.markdown-body h1 { font-size:1.8em; border-bottom:2px solid #409EFF; padding-bottom:8px; }
.markdown-body h2 { font-size:1.4em; margin-top:24px; }
.markdown-body h3 { font-size:1.1em; margin-top:16px; }
.markdown-body pre { background:#f5f7fa; padding:12px; border-radius:4px; overflow-x:auto; }
.markdown-body table { border-collapse:collapse; width:100%; }
.markdown-body th, .markdown-body td { border:1px solid #dcdfe6; padding:8px; text-align:left; }
</style>
