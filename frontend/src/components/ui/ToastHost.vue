<script setup lang="ts">
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
</script>

<template>
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div" class="toast-host">
      <button
        v-for="toast in ui.toasts"
        :key="toast.id"
        class="toast"
        :class="toast.type"
        @click="ui.dismiss(toast.id)"
      >
        <span class="toast-icon">
          {{ toast.type === 'success' ? '✓' : toast.type === 'error' ? '!' : 'i' }}
        </span>
        <span class="toast-text">{{ toast.message }}</span>
      </button>
    </TransitionGroup>
  </Teleport>
</template>

<style scoped>
.toast-host {
  position: fixed;
  top: 22px;
  right: 24px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 220px;
  max-width: 360px;
  padding: 11px 14px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(10, 22, 36, 0.94);
  backdrop-filter: blur(16px);
  color: var(--text);
  font-size: 13px;
  text-align: left;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4);
  cursor: pointer;
}

.toast-icon {
  width: 22px;
  height: 22px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.toast.success .toast-icon { background: rgba(163, 230, 53, 0.15); color: var(--lime); border: 1px solid rgba(163, 230, 53, 0.3); }
.toast.error .toast-icon { background: rgba(251, 113, 133, 0.15); color: var(--danger); border: 1px solid rgba(251, 113, 133, 0.3); }
.toast.info .toast-icon { background: rgba(34, 211, 238, 0.12); color: var(--cyan); border: 1px solid rgba(34, 211, 238, 0.3); }
.toast.info { border-color: rgba(34, 211, 238, 0.35); }
.toast.error { border-color: rgba(251, 113, 133, 0.35); }

.toast-text { line-height: 1.45; }

.toast-enter-active, .toast-leave-active { transition: all 0.32s cubic-bezier(0.22, 1, 0.36, 1); }
.toast-enter-from { opacity: 0; transform: translateX(24px) scale(0.96); }
.toast-leave-to { opacity: 0; transform: translateX(24px) scale(0.96); }
</style>
