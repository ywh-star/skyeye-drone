<script setup lang="ts">
import { onUnmounted, watch } from 'vue'

const props = withDefaults(defineProps<{
  open: boolean
  title?: string
  width?: string
}>(), { title: '', width: '560px' })

const emit = defineEmits<{ (e: 'close'): void }>()

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

watch(() => props.open, (open) => {
  document.documentElement.style.overflow = open ? 'hidden' : ''
  if (open) window.addEventListener('keydown', onKey)
  else window.removeEventListener('keydown', onKey)
})

onUnmounted(() => {
  document.documentElement.style.overflow = ''
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="modal-mask" @click.self="emit('close')">
        <div class="modal" :style="{ maxWidth: width }" role="dialog" aria-modal="true">
          <header class="modal-head">
            <h3 class="modal-title">{{ title }}</h3>
            <button class="btn btn-icon btn-sm" type="button" aria-label="关闭" @click="emit('close')">✕</button>
          </header>
          <div class="modal-body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="modal-foot">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(2, 7, 12, 0.7);
  backdrop-filter: blur(6px);
}
.modal {
  width: 100%;
  border-radius: 18px;
  border: 1px solid rgba(34, 211, 238, 0.25);
  background: linear-gradient(180deg, #0b1a2a, #071220);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.6), 0 0 40px rgba(34, 211, 238, 0.08);
  max-height: 86vh;
  display: flex;
  flex-direction: column;
}
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; border-bottom: 1px solid var(--line); }
.modal-title { font-size: 15px; font-weight: 600; }
.modal-body { padding: 18px; overflow-y: auto; }
.modal-foot { padding: 12px 18px; border-top: 1px solid var(--line); display: flex; justify-content: flex-end; gap: 10px; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.24s ease; }
.modal-enter-active .modal, .modal-leave-active .modal { transition: transform 0.26s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.24s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal, .modal-leave-to .modal { opacity: 0; transform: translateY(16px) scale(0.97); }
</style>
