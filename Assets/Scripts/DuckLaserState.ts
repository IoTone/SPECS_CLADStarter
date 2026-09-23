// DuckLaserState — pure game state for Laser Duck (no scene access).
//
// Owns:    run phase, survival time (counted only while inside the danger zone), best time,
//          and the difficulty curve (fire interval + laser speed ramp with survival time).
// Expects: a DuckLaserTuning object with values from DuckLaserMain's @inputs.
// Must NOT: touch SceneObjects, audio, or UI. DuckLaserMain reads this and pushes updates to the view.

export type DuckLaserPhase = "idle" | "playing" | "over"

export interface DuckLaserTuning {
  startFireIntervalSec: number
  minFireIntervalSec: number
  startLaserSpeedCmPerSec: number
  maxLaserSpeedCmPerSec: number
  rampSeconds: number
}

const BEST_KEY = "DuckLaser_BestSeconds"

export class DuckLaserState {
  phase: DuckLaserPhase = "idle"
  survivedSeconds = 0
  bestSeconds = 0
  fireCooldown = 0
  nextEye = 0

  constructor(private tuning: DuckLaserTuning) {
    this.bestSeconds = DuckLaserState.loadBest()
  }

  startRun(): void {
    this.phase = "playing"
    this.survivedSeconds = 0
    this.fireCooldown = this.tuning.startFireIntervalSec * 0.6
    this.nextEye = 0
  }

  /** Advance survival time (call only while the player is inside the danger zone). */
  addDangerTime(dt: number): void {
    if (this.phase !== "playing") return
    this.survivedSeconds += dt
  }

  /** Ends the run. Returns true when a new best time was set. */
  endRun(): boolean {
    this.phase = "over"
    if (this.survivedSeconds > this.bestSeconds) {
      this.bestSeconds = this.survivedSeconds
      DuckLaserState.saveBest(this.bestSeconds)
      return true
    }
    return false
  }

  /** 0..1 difficulty progress based on survival time. */
  get ramp(): number {
    const r = this.tuning.rampSeconds > 0 ? this.survivedSeconds / this.tuning.rampSeconds : 1
    return Math.min(1, Math.max(0, r))
  }

  get fireIntervalSec(): number {
    const t = this.tuning
    return t.startFireIntervalSec + (t.minFireIntervalSec - t.startFireIntervalSec) * this.ramp
  }

  get laserSpeedCmPerSec(): number {
    const t = this.tuning
    return t.startLaserSpeedCmPerSec + (t.maxLaserSpeedCmPerSec - t.startLaserSpeedCmPerSec) * this.ramp
  }

  private static loadBest(): number {
    try {
      const store = global.persistentStorageSystem.store
      return store.has(BEST_KEY) ? store.getFloat(BEST_KEY) : 0
    } catch (e) {
      return 0
    }
  }

  private static saveBest(v: number): void {
    try {
      global.persistentStorageSystem.store.putFloat(BEST_KEY, v)
    } catch (e) {
      // Persistent storage unavailable in some preview contexts. The best time stays in memory.
    }
  }
}
