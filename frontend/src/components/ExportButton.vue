<template>
  <el-button type="primary" :icon="Download" @click="doExport">导出 Markdown</el-button>
</template>

<script setup lang="ts">
import { Download } from '@element-plus/icons-vue'
import { usePlanStore } from '@/stores/plan'
const plan = usePlanStore()
function doExport() { const url = plan.exportLink(); if (url) window.open(url, '_blank') }
</script>
