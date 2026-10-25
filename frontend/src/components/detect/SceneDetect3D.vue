<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { DetectionItem } from '@/types'

const props = withDefaults(defineProps<{
  imageUrl: string
  detections: DetectionItem[]
  imageW?: number
  imageH?: number
}>(), { imageW: 1600, imageH: 900 })

const host = ref<HTMLDivElement | null>(null)
const autoRotate = ref(true)
const ready = ref(false)

const PLANE_W = 26

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let observer: ResizeObserver | null = null
let frame = 0
let plane: THREE.Mesh | null = null
let boxes: THREE.Group | null = null
let texture: THREE.Texture | null = null

function planeHeight() {
  return PLANE_W * (props.imageH / Math.max(1, props.imageW))
}

function init() {
  if (!host.value) return
  const width = host.value.clientWidth
  const height = host.value.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x040a11)

  camera = new THREE.PerspectiveCamera(44, width / Math.max(1, height), 0.1, 200)
  camera.position.set(0, 13, 19)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8))
  renderer.setSize(width, height)
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.1
  host.value.appendChild(renderer.domElement)

  scene.add(new THREE.HemisphereLight(0x4fc3e8, 0x050a12, 1.5))
  const key = new THREE.DirectionalLight(0xa8f4ff, 1.2)
  key.position.set(10, 20, 8)
  scene.add(key)
  const rim = new THREE.DirectionalLight(0x9f7bff, 0.7)
  rim.position.set(-14, 8, -12)
  scene.add(rim)

  const grid = new THREE.GridHelper(40, 40, 0x1b6070, 0x0b2f3d)
  grid.position.y = -0.05
  scene.add(grid)

  const pad = new THREE.Mesh(
    new THREE.PlaneGeometry(PLANE_W + 1.4, planeHeight() + 1.4),
    new THREE.MeshBasicMaterial({ color: 0x07131d }),
  )
  pad.rotation.x = -Math.PI / 2
  pad.position.y = -0.02
  scene.add(pad)

  plane = new THREE.Mesh(
    new THREE.PlaneGeometry(PLANE_W, planeHeight()),
    new THREE.MeshBasicMaterial({ color: 0x0a1a26 }),
  )
  plane.rotation.x = -Math.PI / 2
  scene.add(plane)
  loadTexture()

  boxes = new THREE.Group()
  scene.add(boxes)
  rebuild()

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minDistance = 8
  controls.maxDistance = 52
  controls.maxPolarAngle = Math.PI / 2.06
  controls.target.set(0, 1.4, 0)
  controls.autoRotate = autoRotate.value
  controls.autoRotateSpeed = 0.5

  observer = new ResizeObserver(resize)
  observer.observe(host.value)
  clock = new THREE.Clock()
  animate()
  ready.value = true
}

let clock: THREE.Clock | null = null

function loadTexture() {
  if (!plane) return
  texture?.dispose()
  const loader = new THREE.TextureLoader()
  loader.load(props.imageUrl, (tex) => {
    tex.colorSpace = THREE.SRGBColorSpace
    texture = tex
    const material = plane?.material as THREE.MeshBasicMaterial
    if (material) {
      material.map = tex
      material.color.set(0xffffff)
      material.needsUpdate = true
    }
  })
}

function disposeGroup(group: THREE.Group) {
  group.traverse((object) => {
    const mesh = object as THREE.Mesh
    mesh.geometry?.dispose()
    const material = mesh.material as THREE.Material | THREE.Material[] | undefined
    if (Array.isArray(material)) material.forEach((m) => m.dispose())
    else material?.dispose()
    const sprite = object as THREE.Sprite
    if (sprite.isSprite) {
      const map = (sprite.material as THREE.SpriteMaterial).map
      map?.dispose()
      ;(sprite.material as THREE.SpriteMaterial).dispose()
    }
  })
  group.clear()
}

function spriteLabel(text: string, color: string) {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 64
  const ctx = canvas.getContext('2d')
  if (ctx) {
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.roundRect(2, 12, 252, 40, 8)
    ctx.fill()
    ctx.fillStyle = '#06121a'
    ctx.font = 'bold 24px "Microsoft YaHei", sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(text, 128, 33)
  }
  const map = new THREE.CanvasTexture(canvas)
  map.colorSpace = THREE.SRGBColorSpace
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false }))
  sprite.scale.set(3.1, 0.78, 1)
  return sprite
}

function rebuild() {
  if (!boxes) return
  disposeGroup(boxes)
  const height = planeHeight()
  const list = props.detections.slice(0, 40)

  list.forEach((det) => {
    const w = Math.max(0.18, det.w * PLANE_W)
    const d = Math.max(0.18, det.h * height)
    const h = 0.5 + det.conf * 2.6
    const color = new THREE.Color(det.color)

    const box = new THREE.Mesh(
      new THREE.BoxGeometry(w, h, d),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.16, depthWrite: false }),
    )
    box.position.set((det.x + det.w / 2 - 0.5) * PLANE_W, h / 2 + 0.04, (det.y + det.h / 2 - 0.5) * height)
    boxes?.add(box)

    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(w, h, d)),
      new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.9 }),
    )
    edges.position.copy(box.position)
    boxes?.add(edges)

    if (det.conf > 0.3) {
      const label = spriteLabel(`${det.label_cn} ${(det.conf * 100).toFixed(0)}%`, det.color)
      label.position.set(box.position.x, box.position.y + h / 2 + 0.55, box.position.z)
      boxes?.add(label)
    }
  })
}

function resize() {
  if (!host.value || !renderer || !camera) return
  const width = host.value.clientWidth
  const height = host.value.clientHeight
  camera.aspect = width / Math.max(1, height)
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

function animate() {
  frame = requestAnimationFrame(animate)
  if (!renderer || !scene || !camera || !clock) return
  controls?.update()
  const elapsed = clock.getElapsedTime()
  boxes?.children.forEach((child) => {
    if ((child as THREE.Sprite).isSprite) {
      child.position.y += Math.sin(elapsed * 2 + child.id) * 0.0018
    }
  })
  renderer.render(scene, camera)
}

watch(() => props.detections, rebuild, { deep: false })
watch(() => props.imageUrl, loadTexture)

onMounted(init)

onUnmounted(() => {
  cancelAnimationFrame(frame)
  observer?.disconnect()
  controls?.dispose()
  if (boxes) disposeGroup(boxes)
  if (scene) {
    scene.traverse((object) => {
      const mesh = object as THREE.Mesh
      mesh.geometry?.dispose()
      const material = mesh.material as THREE.Material | undefined
      material?.dispose()
    })
  }
  texture?.dispose()
  renderer?.dispose()
  if (renderer?.domElement.parentElement) renderer.domElement.parentElement.removeChild(renderer.domElement)
  renderer = null
  scene = null
  camera = null
  controls = null
  plane = null
  boxes = null
  clock = null
})
</script>

<template>
  <div class="scene-host" ref="host">
    <div v-if="!ready" class="scene-loading"><span class="spinner" /> 初始化 3D 场景…</div>
    <div class="scene-hud">
      <span class="chip cyan">3D 立体框</span>
      <span class="chip">{{ detections.length }} / 40 框</span>
      <button class="btn btn-sm" type="button" @click="autoRotate = !autoRotate; controls && (controls.autoRotate = autoRotate)">
        {{ autoRotate ? '停止环绕' : '自动环绕' }}
      </button>
    </div>
    <div class="scene-tip">拖拽旋转 · 滚轮缩放 · 框体高度映射置信度</div>
  </div>
</template>

<style scoped>
.scene-host { position: relative; width: 100%; height: 100%; min-height: 360px; border-radius: 14px; overflow: hidden; background: #040a11; border: 1px solid var(--line); }
.scene-loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 12px; color: var(--muted); }
.scene-hud { position: absolute; left: 10px; top: 10px; display: flex; gap: 6px; align-items: center; }
.scene-tip { position: absolute; right: 12px; bottom: 10px; font-size: 10px; color: var(--muted); background: rgba(4, 10, 17, 0.72); padding: 3px 8px; border-radius: 5px; border: 1px solid var(--line); }
</style>
