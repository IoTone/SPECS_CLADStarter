// DuckLaserMain — orchestrates Laser Duck. Laser-eyed rubber duck vs. your hand-held "O" shield.
//
// Owns:    the per-frame game loop. It measures your head's distance to the duck, fires lasers
//          from alternating eyes while you're in the danger zone, reads laser results
//          (deflect / hit), and pushes time, best and status into the HUD.
// Expects: typed refs to the HUD, duck, shield, laser and audio components plus the head camera,
//          all wired by the bootstrap. Gameplay tuning lives in the Settings group.
// Must NOT: build UI or text (that's DuckLaserHudUI) or own the laser/shield math
//          (the controllers do). Domain state lives in DuckLaserState.

import {DuckLaserHudUI} from "./DuckLaserHudUI"
import {DuckLaserDuckController} from "./DuckLaserDuckController"
import {DuckLaserShieldController} from "./DuckLaserShieldController"
import {DuckLaserLaserController} from "./DuckLaserLaserController"
import {DuckLaserAudioController} from "./DuckLaserAudioController"
import {DuckLaserState} from "./DuckLaserState"

@component
export class DuckLaserMain extends BaseScriptComponent {
  @ui.label('<span style="color: #60A5FA;">DuckLaserMain – survive the laser duck</span>')
  @ui.separator

  @ui.label('<span style="color: #60A5FA;">References</span>')
  @ui.group_start("References")
  @input
  @hint("HUD panel (time, best, status, play button)")
  hud!: DuckLaserHudUI

  @input
  @hint("Duck turret controller on DuckRoot")
  duck!: DuckLaserDuckController

  @input
  @hint("Hand-held shield controller on ShieldRoot")
  shield!: DuckLaserShieldController

  @input
  @hint("Laser pool controller on the Lasers runtime root")
  lasers!: DuckLaserLaserController

  @input
  @hint("Audio controller (music + SFX)")
  audio!: DuckLaserAudioController

  @input
  @hint("World camera (the player's head). Lasers aim here.")
  headCamera!: SceneObject
  @ui.group_end

  @ui.separator
  @ui.label('<span style="color: #60A5FA;">Gameplay</span>')
  @ui.group_start("Gameplay")
  @input
  @hint("The duck fires when your head is closer than this (cm). The survival timer only runs inside this zone.")
  @widget(new SliderWidget(40, 300, 5))
  triggerDistanceCm: number = 120

  @input
  @hint("Radius (cm) around your head that counts as a hit")
  @widget(new SliderWidget(4, 30, 0.5))
  headHitRadiusCm: number = 12

  @input
  @hint("Seconds between shots at the start of a run")
  @widget(new SliderWidget(0.2, 4, 0.05))
  startFireIntervalSec: number = 1.4

  @input
  @hint("Fastest firing interval (seconds), reached after the ramp time")
  @widget(new SliderWidget(0.1, 2, 0.05))
  minFireIntervalSec: number = 0.45

  @input
  @hint("Laser speed (cm/s) at the start of a run")
  @widget(new SliderWidget(20, 300, 5))
  startLaserSpeedCmPerSec: number = 70

  @input
  @hint("Top laser speed (cm/s), reached after the ramp time")
  @widget(new SliderWidget(20, 400, 5))
  maxLaserSpeedCmPerSec: number = 150

  @input
  @hint("Seconds of survival until the duck reaches max fire rate and laser speed")
  @widget(new SliderWidget(5, 180, 5))
  rampSeconds: number = 45

  @input
  @hint("Random aim offset (cm) around your head, so the shots aren't perfectly predictable")
  @widget(new SliderWidget(0, 20, 0.5))
  aimJitterCm: number = 5
  @ui.group_end

  @ui.separator
  @ui.label('<span style="color: #60A5FA;">Debug</span>')
  @ui.group_start("Debug")
  @input
  @hint("Treat the player as always inside the danger zone (handy in the Lens Studio preview, where you can't walk)")
  debugIgnoreProximity: boolean = false
  @ui.group_end

  private state!: DuckLaserState
  private wasInZone = false
  private hudTimer = 0

  onAwake(): void {
    if (!this.hud || !this.duck || !this.shield || !this.lasers || !this.audio || !this.headCamera) {
      print("[DuckLaserMain] ERROR: a required @input is not wired (hud/duck/shield/lasers/audio/headCamera). Check Phase B wiring.")
      return
    }
    this.state = new DuckLaserState({
      startFireIntervalSec: this.startFireIntervalSec,
      minFireIntervalSec: this.minFireIntervalSec,
      startLaserSpeedCmPerSec: this.startLaserSpeedCmPerSec,
      maxLaserSpeedCmPerSec: this.maxLaserSpeedCmPerSec,
      rampSeconds: this.rampSeconds,
    })

    this.createEvent("OnStartEvent").bind(() => {
      this.hud.onPlayPressed.add(() => this.startRun())
      this.hud.showIdle()
      this.hud.setTime(0)
      this.hud.setBest(this.state.bestSeconds)
    })
    this.createEvent("UpdateEvent").bind(() => this.onUpdate())
  }

  private startRun(): void {
    this.lasers.clearAll()
    this.state.startRun()
    this.wasInZone = false
    this.hud.showPlaying()
    this.hud.setTime(0)
    this.hud.setStatus("Step inside the danger zone to score!")
    this.audio.playSqueak()
    print("[DuckLaserMain] Run started")
  }

  private onUpdate(): void {
    if (!this.state) return
    const dt = getDeltaTime()
    const headPos = this.headCamera.getTransform().getWorldPosition()
    const duckPos = this.duck.getTransform().getWorldPosition()
    const inZone = this.debugIgnoreProximity || headPos.distance(duckPos) < this.triggerDistanceCm
    const playing = this.state.phase === "playing"

    this.duck.tick(dt, headPos, playing && inZone)
    if (!playing) {
      // Let stray lasers finish flying after game over. They can't end another run.
      this.lasers.tick(dt, headPos, 0, this.shield.getShieldState())
      return
    }

    // Zone enter / exit feedback
    if (inZone !== this.wasInZone) {
      this.wasInZone = inZone
      if (inZone) {
        this.audio.playSqueak()
        this.hud.setStatus("DANGER ZONE! Block the lasers with your shield!", true)
      } else {
        this.hud.setStatus("Step inside the danger zone to score!")
      }
    }

    if (inZone) {
      this.state.addDangerTime(dt)
      this.state.fireCooldown -= dt
      if (this.state.fireCooldown <= 0) {
        this.fireLaser(headPos)
        this.state.fireCooldown = this.state.fireIntervalSec
      }
    }

    const res = this.lasers.tick(dt, headPos, this.headHitRadiusCm, this.shield.getShieldState())
    if (res.deflections > 0) this.audio.playDeflect()
    if (res.hitHead) {
      this.gameOver()
      return
    }

    this.hudTimer -= dt
    if (this.hudTimer <= 0) {
      this.hudTimer = 0.1
      this.hud.setTime(this.state.survivedSeconds)
    }
  }

  private fireLaser(headPos: vec3): void {
    const eye = this.state.nextEye
    this.state.nextEye = 1 - eye
    const from = this.duck.getMuzzleWorld(eye)
    const j = this.aimJitterCm
    const target = headPos.add(new vec3((Math.random() * 2 - 1) * j, (Math.random() * 2 - 1) * j, (Math.random() * 2 - 1) * j))
    if (this.lasers.fire(from, target, this.state.laserSpeedCmPerSec)) {
      this.duck.kick()
      this.audio.playLaser()
    }
  }

  private gameOver(): void {
    const newBest = this.state.endRun()
    this.audio.playHit()
    this.hud.showGameOver(this.state.survivedSeconds, this.state.bestSeconds)
    print(`[DuckLaserMain] Shot down after ${this.state.survivedSeconds.toFixed(1)}s${newBest ? " (new best)" : ""}`)
  }
}
