// DuckLaserLaserController — pooled laser bolts: flight, shield deflection, and head hits.
//
// Owns:    a pool of LaserBolt prefab instances under this SceneObject (the authored
//          Runtime/Lasers root). Handles per-frame movement, the swept shield-disk test
//          (reflects lasers off the shield), and the swept head-sphere test.
// Expects: laserPrefab (LaserBolt.glb). DuckLaserMain calls fire() and tick().
// Must NOT: keep score or change game phase. tick() reports hits and deflections and
//          DuckLaserMain decides what they mean.

import {ShieldState} from "./DuckLaserShieldController"

interface Laser {
  obj: SceneObject
  pos: vec3
  vel: vec3
  age: number
  alive: boolean
  deflected: boolean
}

export interface LaserTickResult {
  hitHead: boolean
  deflections: number
}

@component
export class DuckLaserLaserController extends BaseScriptComponent {
  @ui.label('<span style="color: #60A5FA;">DuckLaserLaserController – pooled laser bolts</span>')
  @ui.separator

  @ui.label('<span style="color: #60A5FA;">References</span>')
  @ui.group_start("References")
  @input
  @hint("Laser bolt prefab (the 8-bit red bolt GLB). Swap it to restyle the lasers.")
  laserPrefab!: ObjectPrefab
  @ui.group_end

  @ui.separator
  @ui.label('<span style="color: #60A5FA;">Settings</span>')
  @ui.group_start("Settings")
  @input
  @hint("Maximum lasers in flight at once (pool size)")
  @widget(new SliderWidget(4, 64, 1))
  poolSize: number = 24

  @input
  @hint("Seconds before an unblocked or deflected laser despawns")
  @widget(new SliderWidget(1, 10, 0.5))
  laserLifetimeSec: number = 4

  @input
  @hint("Speed multiplier applied to a laser when your shield deflects it")
  @widget(new SliderWidget(0.5, 3, 0.1))
  deflectSpeedMultiplier: number = 1.3
  @ui.group_end

  private pool: Laser[] = []

  onAwake(): void {
    if (!this.laserPrefab) {
      print("[DuckLaserLaserController] ERROR: laserPrefab not wired")
      return
    }
    for (let i = 0; i < this.poolSize; i++) {
      const obj = this.laserPrefab.instantiate(this.getSceneObject())
      obj.name = `Laser_${i}`
      obj.enabled = false
      this.pool.push({obj, pos: vec3.zero(), vel: vec3.zero(), age: 0, alive: false, deflected: false})
    }
  }

  /** Spawn a laser at `from` flying toward `to` at `speed` cm/s. */
  fire(from: vec3, to: vec3, speed: number): boolean {
    const l = this.pool.find((p) => !p.alive)
    if (!l) return false
    const dir = to.sub(from).normalize()
    l.pos = from
    l.vel = dir.uniformScale(speed)
    l.age = 0
    l.alive = true
    l.deflected = false
    l.obj.enabled = true
    this.place(l)
    return true
  }

  clearAll(): void {
    for (const l of this.pool) {
      l.alive = false
      l.obj.enabled = false
    }
  }

  tick(dt: number, headPos: vec3, headRadiusCm: number, shield: ShieldState): LaserTickResult {
    const result: LaserTickResult = {hitHead: false, deflections: 0}
    for (const l of this.pool) {
      if (!l.alive) continue
      l.age += dt
      const prev = l.pos
      let next = prev.add(l.vel.uniformScale(dt))

      // Swept test against the shield disk (only lasers still heading for the player).
      if (!l.deflected && shield.active) {
        const d0 = prev.sub(shield.center).dot(shield.normal)
        const d1 = next.sub(shield.center).dot(shield.normal)
        if (d0 > 0 && d1 <= 0) {
          const t = d0 / (d0 - d1)
          const p = prev.add(next.sub(prev).uniformScale(t))
          if (p.distance(shield.center) <= shield.radiusCm) {
            const v = l.vel
            const reflected = v.sub(shield.normal.uniformScale(2 * v.dot(shield.normal)))
            l.vel = reflected.uniformScale(this.deflectSpeedMultiplier)
            l.deflected = true
            next = p.add(shield.normal.uniformScale(0.5))
            result.deflections++
          }
        }
      }

      // Swept test against the head sphere.
      if (!l.deflected && this.segmentPointDistance(prev, next, headPos) <= headRadiusCm) {
        result.hitHead = true
        l.alive = false
        l.obj.enabled = false
        continue
      }

      l.pos = next
      if (l.age > this.laserLifetimeSec) {
        l.alive = false
        l.obj.enabled = false
        continue
      }
      this.place(l)
    }
    return result
  }

  private place(l: Laser): void {
    const tr = l.obj.getTransform()
    tr.setWorldPosition(l.pos)
    const dir = l.vel.normalize()
    const up = Math.abs(dir.dot(vec3.up())) > 0.98 ? vec3.forward() : vec3.up()
    // The bolt is symmetric along its long (Z) axis, so either sign of look direction is fine.
    tr.setWorldRotation(quat.lookAt(dir, up))
  }

  private segmentPointDistance(a: vec3, b: vec3, p: vec3): number {
    const ab = b.sub(a)
    const len2 = ab.dot(ab)
    if (len2 < 1e-6) return p.distance(a)
    const t = Math.min(1, Math.max(0, p.sub(a).dot(ab) / len2))
    return p.distance(a.add(ab.uniformScale(t)))
  }
}
