// Scenario 2 — Inside the danger zone the duck fires and the survival timer increases.
// Outside the zone (when the preview head is farther than triggerDistanceCm) nothing fires and
// the timer stays put. The zone is then forced via the existing debugIgnoreProximity input
// (runtime-only, restored in finally) because the preview head cannot walk to the duck.

import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {sleep} from "Leaf.lspkg/Utils/common/Utils"
import {DefaultLeafInteractor} from "Leaf.lspkg/Interactors/interactor/DefaultLeafInteractor"
import {DuckLaserHooks, log, waitUntil} from "./DuckLaserTestHooks"
import {DuckLaserState} from "../../Scripts/DuckLaserState"

@component
export class DuckLaserDangerZoneScenario extends Scenario {
  async run(): Promise<void> {
    await sleep(500)
    const h = new DuckLaserHooks()
    const interactor = new DefaultLeafInteractor()
    const restoreZone = h.forceDangerZone(false)
    try {
      await h.startFreshRun(interactor)
      const dist = h.headDuckDistance
      log(`danger-zone: head-duck distance=${dist.toFixed(1)}cm trigger=${h.main.triggerDistanceCm}cm inZone=${h.headInZone}`)

      // A) Outside the zone: no shots, no time.
      if (!h.headInZone) {
        await sleep(1500)
        log(`danger-zone: outside zone after 1.5s survived=${h.survived.toFixed(3)} alive=${h.aliveLasers.length}`)
        expect(h.survived).toBe(0)
        expect(h.aliveLasers.length).toBe(0)
        expect(h.phase).toBe("playing")
      }

      // B) Inside the zone (forced if needed).
      h.forceDangerZone(true)
      const t0 = h.survived
      const fired = await waitUntil(() => h.aliveLasers.length > 0, 2000)
      const firstShotAt = h.survived - t0
      log(`danger-zone: first shot fired=${fired} after ${firstShotAt.toFixed(2)}s in zone (expected ~${(h.main.startFireIntervalSec * 0.6).toFixed(2)}s)`)
      expect(fired).toBe(true)
      expect(firstShotAt).toBeCloseTo(h.main.startFireIntervalSec * 0.6, 0)

      const laser = h.aliveLasers[0]
      const speed = laser.vel.length
      log(`danger-zone: first laser speed=${speed.toFixed(1)}cm/s (start=${h.main.startLaserSpeedCmPerSec})`)
      expect(speed).toBeGreaterThan(h.main.startLaserSpeedCmPerSec - 0.01)
      expect(speed).toBeLessThan(h.main.startLaserSpeedCmPerSec + 5)
      // Laser heads toward the player.
      const toHead = h.headPos.sub(laser.pos).normalize()
      expect(laser.vel.normalize().dot(toHead)).toBeGreaterThan(0.9)

      await sleep(700)
      const s1 = h.survived
      const hud1 = DuckLaserHooks.parseSeconds(h.timeText)
      log(`danger-zone: survived=${s1.toFixed(2)} hud="${h.timeText}" status="${h.statusText}" phase=${h.phase}`)
      expect(h.phase).toBe("playing")
      expect(s1).toBeGreaterThan(t0 + 1.0)
      expect(hud1).toBeGreaterThan(0.8)
      expect(h.statusText.includes("DANGER ZONE")).toBe(true)

      // Difficulty curve from the live tuning (pure state object, no scene access).
      const m = h.main
      const probe = new DuckLaserState({
        startFireIntervalSec: m.startFireIntervalSec,
        minFireIntervalSec: m.minFireIntervalSec,
        startLaserSpeedCmPerSec: m.startLaserSpeedCmPerSec,
        maxLaserSpeedCmPerSec: m.maxLaserSpeedCmPerSec,
        rampSeconds: m.rampSeconds,
      })
      probe.startRun()
      expect(probe.fireIntervalSec).toBeCloseTo(1.4, 3)
      expect(probe.laserSpeedCmPerSec).toBeCloseTo(70, 3)
      probe.addDangerTime(m.rampSeconds / 2)
      expect(probe.fireIntervalSec).toBeCloseTo((1.4 + 0.45) / 2, 3)
      expect(probe.laserSpeedCmPerSec).toBeCloseTo((70 + 150) / 2, 3)
      probe.addDangerTime(m.rampSeconds * 10)
      expect(probe.fireIntervalSec).toBeCloseTo(0.45, 3)
      expect(probe.laserSpeedCmPerSec).toBeCloseTo(150, 3)
      log("danger-zone: ramp 1.4s->0.45s and 70->150cm/s verified")
    } finally {
      restoreZone()
    }
  }
}
