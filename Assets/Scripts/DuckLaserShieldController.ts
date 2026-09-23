// DuckLaserShieldController — keeps the green-and-yellow "O" shield on the player's dominant hand.
//
// Owns:    the shield's pose. It sits at the palm center, pushed a little away from the head,
//          with its face turned away from the player so it blocks lasers coming at the head.
//          It exposes that pose (center, normal, radius, active) for laser collision.
// Expects: headCamera (the Camera Object) and shieldVisual (the authored child holding the O-shield mesh).
// Must NOT: move lasers or change score. DuckLaserLaserController reads getShieldState().

import {HandInputData} from "SpectaclesInteractionKit.lspkg/Providers/HandInputData/HandInputData"

export interface ShieldState {
  active: boolean
  center: vec3
  normal: vec3 // unit vector pointing away from the player (toward incoming lasers)
  radiusCm: number
}

@component
export class DuckLaserShieldController extends BaseScriptComponent {
  @ui.label('<span style="color: #60A5FA;">DuckLaserShieldController – hand-held deflector shield</span>')
  @ui.separator

  @ui.label('<span style="color: #60A5FA;">References</span>')
  @ui.group_start("References")
  @input
  @hint("The world camera (the player's head). The shield faces away from it.")
  headCamera!: SceneObject

  @input
  @hint("Child SceneObject holding the shield mesh. It is hidden while no hand is tracked.")
  shieldVisual!: SceneObject
  @ui.group_end

  @ui.separator
  @ui.label('<span style="color: #60A5FA;">Settings</span>')
  @ui.group_start("Settings")
  @input
  @hint("Deflection radius in cm around the shield center. The mesh is about 22 x 26 cm.")
  @widget(new SliderWidget(5, 30, 0.5))
  shieldRadiusCm: number = 13

  @input
  @hint("How far (cm) in front of the palm, away from your head, the shield floats")
  @widget(new SliderWidget(0, 20, 0.5))
  palmOffsetCm: number = 5

  @input
  @hint("Pose smoothing (0 = raw hand data, 0.9 = very smooth but laggy)")
  @widget(new SliderWidget(0, 0.9, 0.05))
  smoothing: number = 0.35

  @input
  @hint("When no hand is tracked (e.g. Lens Studio preview), hold the shield at a fixed spot in front of the camera instead of hiding it")
  untrackedFallback: boolean = false
  @ui.group_end

  private state: ShieldState = {active: false, center: vec3.zero(), normal: new vec3(0, 0, -1), radiusCm: 13}
  private hands = HandInputData.getInstance()
  private hasPose = false

  onAwake(): void {
    if (!this.headCamera || !this.shieldVisual) {
      print("[DuckLaserShieldController] ERROR: headCamera / shieldVisual not wired")
      return
    }
    this.createEvent("UpdateEvent").bind(() => this.onUpdate())
  }

  getShieldState(): ShieldState {
    this.state.radiusCm = this.shieldRadiusCm
    return this.state
  }

  private onUpdate(): void {
    const head = this.headCamera.getTransform()
    const headPos = head.getWorldPosition()
    let target: vec3 | null = null

    const hand = this.hands.getDominantHand()
    if (hand && hand.isTracked()) {
      const palm = hand.getPalmCenter()
      if (palm) target = palm
    }
    if (!target && this.untrackedFallback) {
      // Lower-right of view, 40 cm ahead: lets you exercise deflection in the editor preview.
      target = headPos.add(head.back.uniformScale(40)).add(head.right.uniformScale(10)).add(head.down.uniformScale(10))
    }

    if (!target) {
      this.state.active = false
      this.hasPose = false
      this.shieldVisual.enabled = false
      return
    }

    let n = target.sub(headPos)
    if (n.length < 1e-3) n = head.back
    n = n.normalize()
    const desired = target.add(n.uniformScale(this.palmOffsetCm))

    const tr = this.getTransform()
    const k = this.hasPose ? 1 - this.smoothing : 1
    const center = this.hasPose ? vec3.lerp(tr.getWorldPosition(), desired, k) : desired
    tr.setWorldPosition(center)
    // quat.lookAt aligns +Z with n; the voxel shield has an "O" on both faces.
    tr.setWorldRotation(quat.lookAt(n, vec3.up()))

    this.shieldVisual.enabled = true
    this.hasPose = true
    this.state.active = true
    this.state.center = center
    this.state.normal = n
  }
}
