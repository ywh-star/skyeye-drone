<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import * as THREE from 'three'

const host = ref<HTMLDivElement | null>(null)

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let frame = 0
let observer: ResizeObserver | null = null
let drone: THREE.Group | null = null
let scan: THREE.Group | null = null
let groundRing: THREE.Mesh | null = null
let curve: THREE.CatmullRomCurve3 | null = null
const rotors: THREE.Object3D[] = []
let particles: THREE.Points | null = null
let clock: THREE.Clock | null = null
let visible = true
let pointer = { x: 0, y: 0 }
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

function buildCity(target: THREE.Scene) {
  const rand = mulberry32(20261024)
  const bodyMat = new THREE.MeshStandardMaterial({
    color: 0x0a1d2c, roughness: 0.62, metalness: 0.45,
    emissive: 0x0a3d4d, emissiveIntensity: 0.16,
  })
  const count = 13 * 13
  const buildings = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), bodyMat, count)
  const beacons = new THREE.InstancedMesh(
    new THREE.SphereGeometry(0.22, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0x66f0ff }),
    60,
  )
  const dummy = new THREE.Object3D()
  let index = 0
  let beaconIndex = 0

  for (let gx = -6; gx <= 6; gx += 1) {
    for (let gz = -6; gz <= 6; gz += 1) {
      const distance = Math.hypot(gx, gz)
      const x = gx * 12 + (rand() - 0.5) * 2.2
      const z = gz * 12 + (rand() - 0.5) * 2.2
      const height = distance < 2 ? 4 + rand() * 4 : 3 + rand() * (distance > 4 ? 24 : 13)
      const width = 4.4 + rand() * 3.4
      const depth = 4.4 + rand() * 3.4
      dummy.position.set(x, height / 2, z)
      dummy.scale.set(width, height, depth)
      dummy.updateMatrix()
      buildings.setMatrixAt(index++, dummy.matrix)
      if (rand() > 0.62 && beaconIndex < 60) {
        dummy.position.set(x, height + 0.3, z)
        dummy.scale.set(1, 1, 1)
        dummy.updateMatrix()
        beacons.setMatrixAt(beaconIndex++, dummy.matrix)
      }
    }
  }
  beacons.count = beaconIndex
  const materials = bodyMat
  buildings.instanceMatrix.needsUpdate = true
  beacons.instanceMatrix.needsUpdate = true
  ;(materials as THREE.Material).needsUpdate = true
  target.add(buildings, beacons)
}

function buildTerrain(target: THREE.Scene) {
  const geometry = new THREE.PlaneGeometry(240, 240, 72, 72)
  const position = geometry.attributes.position
  for (let i = 0; i < position.count; i += 1) {
    const x = position.getX(i)
    const y = position.getY(i)
    const height = Math.sin(x * 0.055) * 1.1 + Math.cos(y * 0.048) * 1.3 + Math.sin((x + y) * 0.03) * 0.8
    position.setZ(i, height)
  }
  position.needsUpdate = true
  geometry.computeVertexNormals()
  const mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({ color: 0x061018, roughness: 0.96, metalness: 0.08 }),
  )
  mesh.rotation.x = -Math.PI / 2
  mesh.position.y = -0.4
  target.add(mesh)

  const grid = new THREE.GridHelper(240, 96, 0x1c6d80, 0x0b3242)
  const gridMat = grid.material as THREE.Material
  gridMat.transparent = true
  gridMat.opacity = 0.32
  grid.position.y = 0.02
  target.add(grid)

  const roadMat = new THREE.MeshBasicMaterial({ color: 0x123a4b, transparent: true, opacity: 0.55 })
  for (let i = -6; i <= 6; i += 1) {
    const horizontal = new THREE.Mesh(new THREE.PlaneGeometry(170, 1.1), roadMat)
    horizontal.rotation.x = -Math.PI / 2
    horizontal.position.set(0, 0.04, i * 12)
    target.add(horizontal)
    const vertical = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 170), roadMat)
    vertical.rotation.x = -Math.PI / 2
    vertical.position.set(i * 12, 0.04, 0)
    target.add(vertical)
  }
}

function buildDrone(target: THREE.Scene) {
  const group = new THREE.Group()
  const shell = new THREE.MeshStandardMaterial({ color: 0x0e2433, metalness: 0.8, roughness: 0.3 })
  const edge = new THREE.MeshStandardMaterial({ color: 0x22d3ee, emissive: 0x22d3ee, emissiveIntensity: 1.1 })

  const body = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.32, 1.5), shell)
  group.add(body)
  const core = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.34, 0.7), edge)
  core.position.y = 0.05
  group.add(core)

  for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 2.1, 6), shell)
    arm.rotation.z = Math.PI / 2
    arm.rotation.y = Math.atan2(sz, sx)
    arm.position.set(sx * 0.85, 0, sz * 0.85)
    group.add(arm)

    const rotor = new THREE.Group()
    rotor.position.set(sx * 1.75, 0.06, sz * 1.75)
    const disc = new THREE.Mesh(
      new THREE.CylinderGeometry(0.82, 0.82, 0.02, 24),
      new THREE.MeshBasicMaterial({ color: 0x9beefb, transparent: true, opacity: 0.16, depthWrite: false }),
    )
    const blade = new THREE.Mesh(
      new THREE.BoxGeometry(1.55, 0.015, 0.09),
      new THREE.MeshBasicMaterial({ color: 0xcbf7ff, transparent: true, opacity: 0.5 }),
    )
    rotor.add(disc, blade)
    group.add(rotor)
    rotors.push(rotor)

    const led = new THREE.Mesh(new THREE.SphereGeometry(0.06, 6, 6), new THREE.MeshBasicMaterial({ color: 0xff6b8a }))
    led.position.set(sx * 1.75, -0.02, sz * 1.75)
    group.add(led)
  }

  const beam = new THREE.Mesh(
    new THREE.ConeGeometry(2.6, 9, 32, 1, true),
    new THREE.MeshBasicMaterial({
      color: 0x22d3ee, transparent: true, opacity: 0.075,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false,
    }),
  )
  beam.position.y = -4.5
  const glow = new THREE.Mesh(
    new THREE.CircleGeometry(1.1, 24),
    new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false }),
  )
  glow.rotation.x = -Math.PI / 2
  glow.position.y = 0.02

  const scanGroup = new THREE.Group()
  scanGroup.add(beam)
  group.add(scanGroup)
  group.add(glow)
  ;(group as THREE.Group & { userData: { glow: THREE.Mesh } }).userData.glow = glow

  target.add(group)
  drone = group
  scan = scanGroup
}

function buildPath(target: THREE.Scene) {
  const points = [
    new THREE.Vector3(-52, 17, -38),
    new THREE.Vector3(-18, 21, -52),
    new THREE.Vector3(26, 18, -34),
    new THREE.Vector3(48, 22, 4),
    new THREE.Vector3(28, 19, 42),
    new THREE.Vector3(-16, 23, 48),
    new THREE.Vector3(-48, 18, 22),
    new THREE.Vector3(-60, 20, -12),
  ]
  curve = new THREE.CatmullRomCurve3(points, true, 'catmullrom', 0.35)
  const tube = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 260, 0.16, 5, true),
    new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.38, blending: THREE.AdditiveBlending }),
  )
  target.add(tube)

  for (const point of points) {
    const marker = new THREE.Mesh(
      new THREE.RingGeometry(0.7, 0.85, 24),
      new THREE.MeshBasicMaterial({ color: 0xa3e635, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }),
    )
    marker.position.copy(point)
    marker.lookAt(new THREE.Vector3(0, 60, 0))
    target.add(marker)
  }

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(2.4, 2.8, 64),
    new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.3, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, depthWrite: false }),
  )
  ring.rotation.x = -Math.PI / 2
  ring.position.y = 0.12
  target.add(ring)
  groundRing = ring
}

function buildParticles(target: THREE.Scene) {
  const count = 420
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count; i += 1) {
    const radius = 20 + Math.random() * 80
    const angle = Math.random() * Math.PI * 2
    positions[i * 3] = Math.cos(angle) * radius
    positions[i * 3 + 1] = 4 + Math.random() * 46
    positions[i * 3 + 2] = Math.sin(angle) * radius
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  const material = new THREE.PointsMaterial({
    color: 0x7dd3fc, size: 0.32, transparent: true, opacity: 0.5,
    blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
  })
  particles = new THREE.Points(geometry, material)
  target.add(particles)
}

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

function init() {
  if (!host.value) return
  const width = host.value.clientWidth || window.innerWidth
  const height = host.value.clientHeight || window.innerHeight

  scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x040b13, 0.0088)

  camera = new THREE.PerspectiveCamera(46, width / height, 0.1, 500)
  camera.position.set(62, 38, 66)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8))
  renderer.setSize(width, height)
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.02
  renderer.domElement.style.display = 'block'
  host.value.appendChild(renderer.domElement)

  scene.add(new THREE.HemisphereLight(0x1a6480, 0x02060b, 1.05))
  const key = new THREE.DirectionalLight(0x8df0ff, 1.5)
  key.position.set(46, 74, 28)
  scene.add(key)
  const rim = new THREE.DirectionalLight(0x7c6bff, 0.9)
  rim.position.set(-58, 24, -42)
  scene.add(rim)

  buildTerrain(scene)
  buildCity(scene)
  buildPath(scene)
  buildDrone(scene)
  buildParticles(scene)

  clock = new THREE.Clock()
  animate()

  observer = new ResizeObserver(onResize)
  observer.observe(host.value)
  window.addEventListener('pointermove', onPointer)
  document.addEventListener('visibilitychange', onVisibility)
}

function onResize() {
  if (!host.value || !renderer || !camera) return
  const width = host.value.clientWidth
  const height = host.value.clientHeight
  camera.aspect = width / Math.max(1, height)
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

function onPointer(event: PointerEvent) {
  pointer = {
    x: (event.clientX / window.innerWidth - 0.5) * 2,
    y: (event.clientY / window.innerHeight - 0.5) * 2,
  }
}

function onVisibility() {
  visible = document.visibilityState === 'visible'
}

function animate() {
  frame = requestAnimationFrame(animate)
  if (!visible || !renderer || !scene || !camera || !clock || !curve) return

  const elapsed = clock.getElapsedTime()
  const speed = reduced ? 0.25 : 1

  const t = (elapsed * 0.032 * speed) % 1
  if (drone) {
    const point = curve.getPointAt(t)
    drone.position.copy(point)
    const tangent = curve.getTangentAt(t)
    drone.rotation.y = Math.atan2(tangent.x, tangent.z)
    drone.position.y += Math.sin(elapsed * 1.6) * 0.25
    const glow = (drone.userData as { glow?: THREE.Mesh }).glow
    if (glow) {
      ;(glow.material as THREE.Material).opacity = 0.22 + Math.sin(elapsed * 3) * 0.08
    }
  }

  for (const rotor of rotors) {
    rotor.rotation.y += reduced ? 0.08 : 0.42
  }

  if (scan && drone) {
    const pulse = 0.9 + Math.sin(elapsed * 2.2) * 0.12
    scan.scale.set(pulse, 1, pulse)
  }

  if (groundRing) {
    const phase = (elapsed * 0.55) % 1
    groundRing.scale.setScalar(0.6 + phase * 2.4)
    ;(groundRing.material as THREE.Material).opacity = 0.34 * (1 - phase)
  }

  if (particles) {
    particles.rotation.y = elapsed * 0.018
    const mat = particles.material as THREE.PointsMaterial
    mat.opacity = 0.32 + Math.sin(elapsed * 0.8) * 0.12
  }

  const angle = elapsed * 0.035 * speed + pointer.x * 0.28
  const radius = 76 - pointer.y * 6
  camera.position.set(
    Math.cos(angle) * radius,
    36 + Math.sin(elapsed * 0.18) * 4 - pointer.y * 4,
    Math.sin(angle) * radius,
  )
  camera.lookAt(0, 8, 0)

  renderer.render(scene, camera)
}

function disposeScene(target: THREE.Scene) {
  target.traverse((object) => {
    const mesh = object as THREE.Mesh
    if (mesh.geometry) mesh.geometry.dispose()
    const material = mesh.material as THREE.Material | THREE.Material[] | undefined
    if (Array.isArray(material)) material.forEach((m) => m.dispose())
    else material?.dispose()
  })
}

onMounted(init)

onUnmounted(() => {
  cancelAnimationFrame(frame)
  observer?.disconnect()
  window.removeEventListener('pointermove', onPointer)
  document.removeEventListener('visibilitychange', onVisibility)
  if (scene) disposeScene(scene)
  renderer?.dispose()
  if (renderer?.domElement.parentElement) renderer.domElement.parentElement.removeChild(renderer.domElement)
  renderer = null
  scene = null
  camera = null
  drone = null
  scan = null
  groundRing = null
  particles = null
  clock = null
  rotors.length = 0
})
</script>

<template>
  <div ref="host" class="hero-scene" aria-hidden="true" />
</template>

<style scoped>
.hero-scene {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.hero-scene::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(120% 80% at 50% 100%, transparent 40%, rgba(3, 7, 12, 0.85) 100%),
    linear-gradient(90deg, rgba(3, 7, 12, 0.92) 0%, rgba(3, 7, 12, 0.35) 38%, transparent 62%);
  pointer-events: none;
}
</style>
