// DuckLaserTestHooks — TEST-ONLY helpers for the Laser Duck LEAF scenarios.
//
// Scope:   read-only access to live game components plus a few runtime-only toggles of
//          existing @input flags (debugIgnoreProximity, untrackedFallback). Every toggle is
//          returned as a restore callback so scenarios put the original value back in `finally`.
// Must NOT: be imported by production scripts, or change any authored scene / script value.

import {findSceneObjectByName, sleep} from "Leaf.lspkg/Utils/common/Utils"
import {findInteractableByName} from "Leaf.lspkg/Interactors/InteractableUtils"
import {DefaultLeafInteractor} from "Leaf.lspkg/Interactors/interactor/DefaultLeafInteractor"
import {DuckLaserMain} from "../../Scripts/DuckLaserMain"
import {DuckLaserHudUI} from "../../Scripts/DuckLaserHudUI"
import {DuckLaserShieldController, ShieldState} from "../../Scripts/DuckLaserShieldController"
import {DuckLaserLaserController} from "../../Scripts/DuckLaserLaserController"
import {DuckLaserState} from "../../Scripts/DuckLaserState"

export const BEST_KEY = "DuckLaser_BestSeconds"

export interface LaserSnapshot {
  alive: boolean
  deflected: boolean
  pos: vec3
  vel: vec3
  age: number
}

export class DuckLaserHooks {
  readonly main: DuckLaserMain
  readonly hud: DuckLaserHudUI
  readonly shield: DuckLaserShieldController
  readonly lasers: DuckLaserLaserController

  constructor() {
    this.main = findSceneObjectByName("DuckLaserGame").getComponent(DuckLaserMain.getTypeName()) as DuckLaserMain
    this.hud = findSceneObjectByName("DuckLaserHUD").getComponent(DuckLaserHudUI.getTypeName()) as DuckLaserHudUI
    this.shield = findSceneObjectByName("ShieldRoot").getComponent(
      DuckLaserShieldController.getTypeName(),
    ) as DuckLaserShieldController
    this.lasers = findSceneObjectByName("Lasers").getComponent(
      DuckLaserLaserController.getTypeName(),
    ) as DuckLaserLaserController
    if (!this.main || !this.hud || !this.shield || !this.lasers) {
      throw new Error("DuckLaser components not found (DuckLaserGame / DuckLaserHUD / ShieldRoot / Lasers)")
    }
  }

  // ── Game state (private fields read via `any`; read-only) ─────────────
  get state(): DuckLaserState {
    const s = (this.main as any).state as DuckLaserState
    if (!s) throw new Error("DuckLaserMain.state is not initialised (onAwake bailed?)")
    return s
  }

  get phase(): string {
    return this.state.phase
  }

  get survived(): number {
    return this.state.survivedSeconds
  }

  get best(): number {
    return this.state.bestSeconds
  }

  // ── HUD ────────────────────────────────────────────────────────────
  get timeText(): string {
    return ((this.hud as any).timeText as Text).text
  }

  get bestText(): string {
    return ((this.hud as any).bestText as Text).text
  }

  get statusText(): string {
    return ((this.hud as any).statusText as Text).text
  }

  get buttonLabel(): string {
    return (this.hud as any).playContent.text as string
  }

  static parseSeconds(text: string): number {
    return parseFloat(text.replace(/[^0-9.]/g, ""))
  }

  static fmt(seconds: number): string {
    return `${Math.max(0, seconds).toFixed(1)}s`
  }

  // ── Lasers ─────────────────────────────────────────────────────────
  get laserPool(): LaserSnapshot[] {
    return (this.lasers as any).pool as LaserSnapshot[]
  }

  get aliveLasers(): LaserSnapshot[] {
    return this.laserPool.filter((l) => l.alive)
  }

  // ── Geometry ───────────────────────────────────────────────────────
  get headPos(): vec3 {
    return this.main.headCamera.getTransform().getWorldPosition()
  }

  get duckPos(): vec3 {
    return this.main.duck.getTransform().getWorldPosition()
  }

  get headDuckDistance(): number {
    return this.headPos.distance(this.duckPos)
  }

  get headInZone(): boolean {
    return this.headDuckDistance < this.main.triggerDistanceCm
  }

  // ── Runtime-only toggles (each returns a restore callback) ──────────
  forceDangerZone(on: boolean): () => void {
    const prev = this.main.debugIgnoreProximity
    this.main.debugIgnoreProximity = on
    return () => {
      this.main.debugIgnoreProximity = prev
    }
  }

  setShieldFallback(on: boolean): () => void {
    const prev = this.shield.untrackedFallback
    this.shield.untrackedFallback = on
    return () => {
      this.shield.untrackedFallback = prev
    }
  }

  /** Instance-level override of getShieldState (no prototype / source change). */
  overrideShieldState(provider: () => ShieldState): () => void {
    const inst = this.shield as any
    const hadOwn = Object.prototype.hasOwnProperty.call(inst, "getShieldState")
    const prevOwn = inst.getShieldState
    inst.getShieldState = provider
    return () => {
      if (hadOwn) inst.getShieldState = prevOwn
      else delete inst.getShieldState
    }
  }

  // ── Interaction ────────────────────────────────────────────────────
  async pressPlay(interactor: DefaultLeafInteractor): Promise<void> {
    const button = findInteractableByName("PlayButton", undefined, true)
    if (!button) throw new Error('Interactable "PlayButton" not found or disabled')
    await interactor.trigger(button)
    await sleep(100)
  }

  /** Ensure a fresh run is playing (presses the button once from any phase). */
  async startFreshRun(interactor: DefaultLeafInteractor): Promise<void> {
    await this.pressPlay(interactor)
    if (this.phase !== "playing") throw new Error(`Expected phase "playing" after pressing play, got "${this.phase}"`)
  }
}

/** Poll `pred` every `pollMs` until it is true or `timeoutMs` elapses. Returns the final value. */
export async function waitUntil(pred: () => boolean, timeoutMs: number, pollMs: number = 30): Promise<boolean> {
  let elapsed = 0
  while (elapsed < timeoutMs) {
    if (pred()) return true
    await sleep(pollMs)
    elapsed += pollMs
  }
  return pred()
}

export function readPersistedBest(): number | null {
  try {
    const store = global.persistentStorageSystem.store
    return store.has(BEST_KEY) ? store.getFloat(BEST_KEY) : null
  } catch (e) {
    return null
  }
}

export function log(msg: string): void {
  print(`[DuckLaserLeaf] ${msg}`)
}
