<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { ReplayMarker } from '@/types'

const props = withDefaults(defineProps<{
  markers: ReplayMarker[]
  playing?: boolean
  speed?: number
  cameraMode?: 'free' | 'follow' | 'top'
  progress?: number
}>(), { playing: false, speed: 1, cameraMode: 'free', progress: 0 })

const emit = defineEmits<{
  (e: 'update:progress', value: number): void
  (e: 'telemetry', value: { altitude: number; speed: number; heading: number; progress: number }): void
}>()

const host = ref<HTMLDivElement | null>(null)
const ready = ref(false)

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let observer: ResizeObserver | null = null
let frame = 0
let clock: THREE.Clock | null = null
let drone: THREE.Group | null = null
let curve: THREE.CatmullRomCurve3 | null = null
let markerGroup: THREE.Group | null = null
let rotors: THREE.Object3D[] = []
let scanRing: THREE.Mesh | null = null
let localProgress = props.progress
let lastEmit = 0
let lastTelemetry = 0
const dragging = ref(false)

const WAYPOINTS = [
  [-46, 22, -34], [-8, 26, -46], [30, 20, -32], [48, 24, 6],
  [26, 18, 38], [-14, 24, 44], [-44, 19, 20], [-56, 23, -8],
] as const

function mulberry32(seed: number) {
  let value = seed
  return () => {
    value |= 0
    value = (value + 0x6d2b79f5) | 0
    let t = Math.imul(value ^ (value >>> 15), 1 | value)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function terrainHeight(x: number, z: number) {
  return Math.sin(x * 0.06) * 1.1 + Math.cos(z * 0.05) * 1.3 + Math.sin((x + z) * 0.035) * 0.7
}

function buildTerrain(target: THREE.Scene) {
  const geometry = new THREE.PlaneGeometry(150, 150, 80, 80)
  const position = geometry.attributes.position
  for (let i = 0; i < position.count; i += 1) {
    position.setZ(i, terrainHeight(position.getX(i), position.getY(i)))
  }
  position.needsUpdate = true
  geometry.computeVertexNormals()
  const mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({ color: 0x071620, roughness: 0.92, metalness: 0.14 }),
  )
  mesh.rotation.x = -Math.PI / 2
  target.add(mesh)

  const grid = new THREE.GridHelper(150, 60, 0x1d6b7e, 0x0c3542)
  const material = grid.material as THREE.Material
  material.transparent = true
  material.opacity = 0.26
  grid.position.y = 0.06
  target.add(grid)

  const rand = mulberry32(7)
  const blockMat = new THREE.MeshStandardMaterial({
    color: 0x0b2230, roughness: 0.55, metalness: 0.5, emissive: 0x0a2f3c, emissiveIntensity: 0.18,
  })
  for (let i = 0; i < 60; i += 1) {
    const angle = rand() * Math.PI * 2
    const radius = 18 + rand() * 46
    const x = Math.cos(angle) * radius
    const z = Math.sin(angle) * radius
    const height = 2 + rand() * 9
    const block = new THREE.Mesh(new THREE.BoxGeometry(2 + rand() * 3, height, 2 + rand() * 3), blockMat)
    block.position.set(x, height / 2 + terrainHeight(x, z) * 0.2, z)
    block.rotation.y = rand() * Math.PI
    target.add(block)
  }
}

function buildRoute(target: THREE.Scene) {
  curve = new THREE.CatmullRomCurve3(
    WAYPOINTS.map(([x, y, z]) => new THREE.Vector3(x, y, z)),
    true,
    'catmullrom',
    0.3,
  )
  const tube = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 280, 0.14, 5, true),
    new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.42, blending: THREE.AdditiveBlending }),
  )
  target.add(tube)

  WAYPOINTS.forEach(([x, y, z]) => {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.7, 0.95, 28),
      new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.55, side: THREE.DoubleSide, blending: THREE.AdditiveBlending }),
    )
    ring.position.set(x, y, z)
    ring.lookAt(new THREE.Vector3(0, 80, 0))
    target.add(ring)
  })
}

function buildDrone(target: THREE.Scene) {
  const group = new THREE.Group()
  const shell = new THREE.MeshStandardMaterial({ color: 0x123041, metalness: 0.85, roughness: 0.28 })
  const neon = new THREE.MeshStandardMaterial({ color: 0x22d3ee, emissive: 0x22d3ee, emissiveIntensity: 1.2 })
  group.add(new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.3, 1.4), shell))
  const core = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.32, 0.6), neon)
  core.position.y = 0.04
  group.add(core)

  for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 2, 6), shell)
    arm.rotation.z = Math.PI / 2
    arm.rotation.y = Math.atan2(sz, sx)
    arm.position.set(sx * 0.8, 0, sz * 0.8)
    group.add(arm)
    const rotor = new THREE.Group()
    rotor.position.set(sx * 1.65, 0.06, sz * 1.65)
    rotor.add(new THREE.Mesh(
      new THREE.CylinderGeometry(0.8, 0.8, 0.02, 20),
      new THREE.MeshBasicMaterial({ color: 0x9beefb, transparent: true, opacity: 0.14, depthWrite: false }),
    ))
    group.add(rotor)
    rotors.push(rotor)
  }

  const beam = new THREE.Mesh(
    new THREE.ConeGeometry(2.4, 8.5, 28, 1, true),
    new THREE.MeshBasicMaterial({
      color: 0x22d3ee, transparent: true, opacity: 0.06, side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }),
  )
  beam.position.y = -4.2
  group.add(beam)

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(2.2, 2.5, 56),
    new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.28, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }),
  )
  ring.rotation.x = -Math.PI / 2
  ring.position.y = 0.1
  group.add(ring)
  scanRing = ring

  target.add(group)
  drone = group
}

function labelSprite(label: string, count: number, color: string) {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 96
  const ctx = canvas.getContext('2d')
  if (ctx) {
    ctx.fillStyle = 'rgba(5,13,21,0.92)'
    ctx.beginPath()
    ctx.roundRect(4, 6, 248, 84, 12)
    ctx.fill()
    ctx.strokeStyle = color
    ctx.lineWidth = 3
    ctx.stroke()
    ctx.fillStyle = color
    ctx.font = 'bold 26px "Microsoft YaHei", sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(label, 128, 40)
    ctx.fillStyle = '#e8f3ff'
    ctx.font = 'bold 30px Consolas, monospace'
    ctx.fillText(String(count), 128, 74)
  }
  const map = new THREE.CanvasTexture(canvas)
  map.colorSpace = THREE.SRGBColorSpace
  return new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false }))
}

function buildMarkers() {
  if (!markerGroup) return
  markerGroup.traverse((object) => {
    const mesh = object as THREE.Mesh
    mesh.geometry?.dispose()
    const material = mesh.material as THREE.Material | undefined
    material?.dispose()
    const sprite = object as THREE.Sprite
    if (sprite.isSprite) {
      const map = (sprite.material as THREE.SpriteMaterial).map
      map?.dispose()
      ;(sprite.material as THREE.SpriteMaterial).dispose()
    }
  })
  markerGroup.clear()

  props.markers.forEach((marker, index) => {
    const color = new THREE.Color(marker.color)
    const height = 3.4 + marker.count * 0.18
    const beam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.14, 0.14, height, 6),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.65 }),
    )
    const ground = terrainHeight(marker.x, marker.z) * 0.2
    beam.position.set(marker.x, height / 2 + ground, marker.z)
    markerGroup?.add(beam)

    const ring = new THREE.Mesh(
      new THREE.RingGeometry(1.1, 1.35, 32),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.5, side: THREE.DoubleSide, blending: THREE.AdditiveBlending }),
    )
    ring.rotation.x = -Math.PI / 2
    ring.position.set(marker.x, ground + 0.12, marker.z)
    markerGroup?.add(ring)

    const halo = new THREE.Mesh(
      new THREE.SphereGeometry(0.35, 12, 12),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.8 }),
    )
    halo.position.set(marker.x, height + ground + 0.4, marker.z)
    markerGroup?.add(halo)

    const label = labelSprite(marker.label, marker.count, marker.color)
    label.scale.set(3.6, 1.35, 1)
    label.position.set(marker.x, height + ground + 1.5, marker.z)
    markerGroup?.add(label)

    ring.userData.phase = index * 0.7
  })
}

function init() {
  if (!host.value) return
  const width = host.value.clientWidth
  const height = host.value.clientHeight

  scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x040a12, 0.008)
  scene.background = new THREE.Color(0x040a12)

  camera = new THREE.PerspectiveCamera(48, width / Math.max(1, height), 0.1, 400)
  camera.position.set(58, 44, 62)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8))
  renderer.setSize(width, height)
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.08
  host.value.appendChild(renderer.domElement)

  scene.add(new THREE.HemisphereLight(0x1d6684, 0x03070d, 1.2))
  const key = new THREE.DirectionalLight(0x9ef4ff, 1.4)
  key.position.set(40, 70, 30)
  scene.add(key)
  const rim = new THREE.DirectionalLight(0x7f74ff, 0.85)
  rim.position.set(-50, 30, -40)
  scene.add(rim)

  buildTerrain(scene)
  buildRoute(scene)
  buildDrone(scene)

  markerGroup = new THREE.Group()
  scene.add(markerGroup)
  buildMarkers()

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minDistance = 10
  controls.maxDistance = 130
  controls.maxPolarAngle = Math.PI / 2.15
  controls.target.set(0, 6, 0)
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.35

  observer = new ResizeObserver(resize)
  observer.observe(host.value)
  clock = new THREE.Clock()
  ready.value = true
  animate()
}

function resize() {
  if (!host.value || !renderer || !camera) return
  const width = host.value.clientWidth
  const height = host.value.clientHeight
  camera.aspect = width / Math.max(1, height)
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

function setCameraMode() {
  if (!controls) return
  const mode = props.cameraMode
  controls.autoRotate = mode === 'free'
  controls.enabled = mode === 'free'
}

watch(() => props.cameraMode, () => {
  setCameraMode()
  if (!camera) return
  if (props.cameraMode === 'top') {
    camera.position.set(0, 86, 8)
    camera.lookAt(0, 0, 0)
  }
  if (props.cameraMode === 'free') {
    camera.position.set(58, 44, 62)
    controls?.target.set(0, 6, 0)
  }
})

watch(() => props.progress, (value) => {
  if (Math.abs(value - localProgress) > 0.02) localProgress = value
})

watch(() => props.markers, buildMarkers, { deep: true })

function animate() {
  frame = requestAnimationFrame(animate)
  if (!renderer || !scene || !camera || !clock || !curve || !drone) return

  const delta = Math.min(clock.getDelta(), 0.06)
  const elapsed = clock.elapsedTime

  if (props.playing && !dragging.value) {
    localProgress = (localProgress + delta * 0.035 * props.speed) % 1
    const now = performance.now()
    if (now - lastEmit > 90) {
      emit('update:progress', localProgress)
      lastEmit = now
    }
  }

  const point = curve.getPointAt(localProgress)
  const tangent = curve.getTangentAt(localProgress)
  drone.position.copy(point)
  drone.position.y += Math.sin(elapsed * 1.7) * 0.22
  drone.rotation.y = Math.atan2(tangent.x, tangent.z)
  drone.rotation.z = Math.sin(elapsed * 0.9) * 0.04

  for (const rotor of rotors) rotor.rotation.y += delta * 22

  if (scanRing) {
    const phase = (elapsed * 0.6) % 1
    scanRing.scale.setScalar(0.8 + phase * 2.1)
    ;(scanRing.material as THREE.Material).opacity = 0.3 * (1 - phase)
  }

  if (markerGroup) {
    markerGroup.children.forEach((child) => {
      const ring = child as THREE.Mesh
      const phase = ring.userData.phase
      if (typeof phase === 'number' && ring.geometry.type === 'RingGeometry') {
        const pulse = 0.9 + Math.sin(elapsed * 2 + phase) * 0.18
        ring.scale.setScalar(pulse)
      }
    })
  }

  controls?.update()

  if (props.cameraMode === 'follow') {
    const desired = point.clone().addScaledVector(tangent, -8).add(new THREE.Vector3(0, 4.5, 0))
    camera.position.lerp(desired, 0.045)
    const look = point.clone().addScaledVector(tangent, 6)
    camera.lookAt(look)
    controls?.target.copy(point)
  } else if (props.cameraMode === 'top') {
    camera.position.lerp(new THREE.Vector3(0, 86, 8), 0.05)
    camera.lookAt(0, 0, 0)
  }

  const now = performance.now()
  if (now - lastTelemetry > 160) {
    lastTelemetry = now
    emit('telemetry', {
      altitude: Math.round(point.y * 8),
      speed: Number((6 + props.speed * 3.5 + Math.sin(elapsed) * 0.6).toFixed(1)),
      heading: Math.round(((Math.atan2(tangent.x, tangent.z) * 180) / Math.PI + 360) % 360),
      progress: Math.round(localProgress * 100),
    })
  }

  renderer.render(scene, camera)
}

onMounted(init)

onUnmounted(() => {
  cancelAnimationFrame(frame)
  observer?.disconnect()
  controls?.dispose()
  if (markerGroup) {
    markerGroup.traverse((object) => {
      const mesh = object as THREE.Mesh
      mesh.geometry?.dispose()
      const material = mesh.material as THREE.Material | undefined
      material?.dispose()
    })
  }
  scene?.traverse((object) => {
    const mesh = object as THREE.Mesh
    mesh.geometry?.dispose()
    const material = mesh.material as THREE.Material | undefined
    material?.dispose()
  })
  renderer?.dispose()
  if (renderer?.domElement.parentElement) renderer.domElement.parentElement.removeChild(renderer.domElement)
  renderer = null
  scene = null
  camera = null
  controls = null
  drone = null
  markerGroup = null
  scanRing = null
  curve = null
  clock = null
  rotors.length = 0
})

defineExpose({ setProgress: (value: number) => { localProgress = value } })
</script>

<template>
  <div class="replay-host" ref="host" @pointerdown="dragging = true" @pointerup="dragging = false">
    <div v-if="!ready" class="loading"><span class="spinner" /> 正在构建三维航迹…</div>
    <div class="hud-tip">左键旋转 · 右键平移 · 滚轮缩放</div>
  </div>
</template>

<style scoped>
.replay-host { position: relative; width: 100%; height: 100%; min-height: 480px; overflow: hidden; background: #040a12; }
.loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; gap: 10px; color: var(--muted); font-size: 12px; }
.hud-tip { position: absolute; right: 12px; bottom: 10px; font-size: 10px; color: var(--muted); background: rgba(4, 10, 17, 0.7); border: 1px solid var(--line); border-radius: 5px; padding: 3px 8px; }
</style>
