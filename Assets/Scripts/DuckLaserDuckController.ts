// DuckLaserDuckController — the rubber duck turret (lives on the authored DuckRoot).
//
// Owns:    turning the duck to face the player (yaw only), the idle bob, and the
//          "alert" wobble while the player is inside the danger zone.
//          It also reports the world-space muzzle positions of its two laser eyes.
// Expects: bobRoot (authored DuckVisual child that holds the duck mesh), and
//          leftEyeMuzzle / rightEyeMuzzle (authored anchors on the eyes, under bobRoot).
// Must NOT: fire lasers or track score. DuckLaserMain decides when to fire.

@component
export class DuckLaserDuckController extends BaseScriptComponent {
  @ui.label('<span style="color: #60A5FA;">DuckLaserDuckController – turret duck facing + bob</span>')
  @ui.separator

  @ui.label('<span style="color: #60A5FA;">References</span>')
  @ui.group_start("References")
  @input
  @hint("Child SceneObject that holds the duck mesh. It bobs and wobbles. Eye anchors live under it.")
  bobRoot!: SceneObject

  @input
  @hint("Anchor on the duck's left laser eye. Lasers spawn here.")
  leftEyeMuzzle!: SceneObject

  @input
  @hint("Anchor on the duck's right laser eye. Lasers spawn here.")
  rightEyeMuzzle!: SceneObject
  @ui.group_end

  @ui.separator
  @ui.label('<span style="color: #60A5FA;">Settings</span>')
  @ui.group_start("Settings")
  @input
  @hint("How quickly the duck turns to track you (higher = snappier)")
  @widget(new SliderWidget(0.5, 20, 0.5))
  turnSpeed: number = 6

  @input
  @hint("Idle bob height in cm")
  @widget(new SliderWidget(0, 6, 0.25))
  bobHeightCm: number = 1.5

  @input
  @hint("Idle bob cycles per second")
  @widget(new SliderWidget(0.1, 3, 0.05))
  bobSpeed: number = 0.8

  @input
  @hint("Side-to-side wobble angle (degrees) while you're inside the danger zone")
  @widget(new SliderWidget(0, 25, 1))
  alertWobbleDeg: number = 8
  @ui.group_end

  private yaw = 0
  private t = 0
  private recoil = 0

  onAwake(): void {
    if (!this.bobRoot || !this.leftEyeMuzzle || !this.rightEyeMuzzle) {
      print("[DuckLaserDuckController] ERROR: bobRoot / leftEyeMuzzle / rightEyeMuzzle not wired")
    }
    // Start from the authored facing so the duck doesn't spin on the first frame.
    const f = this.getTransform().back // the mesh front is local -Z
    this.yaw = Math.atan2(f.x, -f.z)
  }

  /** Called every frame by DuckLaserMain. */
  tick(dt: number, headWorldPos: vec3, alert: boolean): void {
    this.t += dt
    const tr = this.getTransform()
    const pos = tr.getWorldPosition()
    const dir = headWorldPos.sub(pos)
    // Mesh is baked to face -Z; yaw its front toward the player (specs-runtime-patterns §10).
    const targetYaw = Math.atan2(dir.x, -dir.z)
    let delta = targetYaw - this.yaw
    while (delta > Math.PI) delta -= Math.PI * 2
    while (delta < -Math.PI) delta += Math.PI * 2
    this.yaw += delta * Math.min(1, this.turnSpeed * dt)
    tr.setWorldRotation(quat.angleAxis(this.yaw, vec3.up()))

    if (this.bobRoot) {
      const bob = Math.sin(this.t * this.bobSpeed * Math.PI * 2) * this.bobHeightCm
      this.recoil = Math.max(0, this.recoil - dt * 6)
      const wobble = alert ? Math.sin(this.t * 9) * this.alertWobbleDeg * (Math.PI / 180) : 0
      const bt = this.bobRoot.getTransform()
      bt.setLocalPosition(new vec3(0, bob, this.recoil * 2.0))
      bt.setLocalRotation(quat.angleAxis(wobble, vec3.forward()))
    }
  }

  /** World-space muzzle position for eye 0 (left) or 1 (right). */
  getMuzzleWorld(eye: number): vec3 {
    const o = eye === 0 ? this.leftEyeMuzzle : this.rightEyeMuzzle
    return o ? o.getTransform().getWorldPosition() : this.getTransform().getWorldPosition()
  }

  /** Small backward kick when the duck fires. */
  kick(): void {
    this.recoil = 1
  }
}
