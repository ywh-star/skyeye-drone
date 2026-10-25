<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from '@/layouts/AppShell.vue'
import ToastHost from '@/components/ui/ToastHost.vue'

const route = useRoute()
const isApp = computed(() => route.meta.layout === 'app')
</script>

<template>
  <AppShell v-if="isApp" />
  <RouterView v-else />
  <ToastHost />
</template>
