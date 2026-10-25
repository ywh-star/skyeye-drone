<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

const searched = ref('')

function jump() {
  const value = searched.value.trim()
  if (value) window.location.href = value
}
</script>

<template>
  <div class="not-found">
    <div class="radar" aria-hidden="true">
      <span class="ring r1" />
      <span class="ring r2" />
      <span class="ring r3" />
      <span class="sweep" />
      <span class="blip" />
    </div>

    <div class="nf-content">
      <span class="chip pink">SIGNAL LOST</span>
      <h1 class="mono">404</h1>
      <h2>航迹信号丢失</h2>
      <p>当前坐标没有对应的作战页面，可能链接已被移动或任务尚未部署。</p>

      <div class="nf-actions">
        <RouterLink to="/console" class="btn btn-primary">返回任务控制台</RouterLink>
        <RouterLink to="/" class="btn">回到接入页</RouterLink>
      </div>

      <div class="nf-search">
        <input v-model="searched" class="input" placeholder="输入要跳转的路径，例如 /detect" @keydown.enter="jump" />
        <button class="btn btn-sm" @click="jump">跳转</button>
      </div>

      <div class="nf-links">
        <RouterLink to="/detect">检测工作台</RouterLink>
        <RouterLink to="/replay">三维航迹回放</RouterLink>
        <RouterLink to="/dataset">VisDrone 数据集</RouterLink>
        <RouterLink to="/training">模型训练中心</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  position: relative; z-index: 1;
  min-height: 100vh; display: grid; place-items: center;
  padding: 32px 20px; overflow: hidden;
}
.radar {
  position: absolute; left: 50%; top: 50%;
  width: 560px; height: 560px; transform: translate(-50%, -50%);
  border-radius: 50%; pointer-events: none;
  opacity: 0.7;
}
.ring {
  position: absolute; inset: 0; border-radius: 50%;
  border: 1px solid rgba(34, 211, 238, 0.14);
}
.ring.r2 { inset: 15%; }
.ring.r3 { inset: 32%; }
.sweep {
  position: absolute; inset: 0; border-radius: 50%;
  background: conic-gradient(from 0deg, rgba(34, 211, 238, 0.22), transparent 24%, transparent);
  animation: spin 5s linear infinite;
}
.blip {
  position: absolute; left: 63%; top: 37%;
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--pink);
  box-shadow: 0 0 14px var(--pink);
  animation: breathe 1.8s ease-in-out infinite;
}
.nf-content {
  position: relative; z-index: 2;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  text-align: center; max-width: 520px;
  padding: 34px 32px; border-radius: 22px;
  border: 1px solid rgba(34, 211, 238, 0.2);
  background: rgba(7, 17, 29, 0.82);
  backdrop-filter: blur(18px);
  box-shadow: var(--shadow);
}
.nf-content h1 { font-size: 76px; line-height: 1; color: var(--cyan); letter-spacing: 0.08em; text-shadow: 0 0 32px rgba(34, 211, 238, 0.45); }
.nf-content h2 { font-size: 19px; font-weight: 550; letter-spacing: 0.02em; }
.nf-content p { font-size: 12px; color: var(--muted); line-height: 1.7; }
.nf-actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; margin-top: 6px; }
.nf-search { display: flex; gap: 8px; width: 100%; margin-top: 4px; }
.nf-links { display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; margin-top: 8px; font-size: 11px; color: var(--muted); }
.nf-links a:hover { color: var(--cyan); }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes breathe { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.35; transform: scale(0.7); } }
</style>
