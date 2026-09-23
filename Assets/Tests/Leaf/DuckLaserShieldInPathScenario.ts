// Scenario 4b — A shield placed squarely in the laser path reflects every laser, the run survives,
// and the timer keeps running. The shield pose is supplied through an instance-level override of
// DuckLaserShieldController.getShieldState (runtime-only, removed in finally) because no hand is
// tracked in the preview.

import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {sleep} from "Leaf.lspkg/Utils/common/Utils"
import {DefaultLeafInteractor} from "Leaf.lspkg/Interactors/interactor/DefaultLeafInteractor"
import {DuckLaserHooks, log} from "./DuckLaserTestHooks"
import {watchDeflections} from "./DuckLaserShieldWatch"
import {ShieldState} from "../../Scripts/DuckLaserShieldController"

@component
export class DuckLaserShieldInPathScenario extends Scenario {
  async run(): Promise<void> {
    await sleep(500)
    const h = new DuckLaserHooks()
    const interactor = new DefaultLeafInteractor()
    const radius = h.shield.shieldRadiusCm
    const provider = (): ShieldState => {
      const head = h.headPos
      const muzzle = h.main.duck.getMuzzleWorld(0).add(h.main.duck.getMuzzleWorld(1)).uniformScale(0.5)
      const n = muzzle.sub(head).normalize() // away from the player, toward incoming lasers
      return {active: true, center: head.add(n.uniformScale(40)), normal: n, radiusCm: radius}
    }
    const restoreShield = h.overrideShieldState(provider)
    const restoreZone = h.forceDangerZone(true)
    try {
      await h.startFreshRun(interactor)
      const w = await watchDeflections(h, 6000)
      log(`shield-in-path: shots=${w.shotsSeen} deflections=${w.deflections} awayFromHead=${w.awayFromHead} gameOver=${w.endedEarly} survived=${h.survived.toFixed(2)} hud="${h.timeText}"`)
      expect(w.endedEarly).toBe(false)
      expect(h.phase).toBe("playing")
      expect(w.shotsSeen).toBeGreaterThan(1)
      expect(w.deflections).toBeGreaterThan(1)
      expect(w.awayFromHead).toBe(w.deflections)
      expect(h.survived).toBeGreaterThan(5)
      expect(DuckLaserHooks.parseSeconds(h.timeText)).toBeGreaterThan(4.5)
    } finally {
      restoreZone()
      restoreShield()
      // Leave the run idle-safe: nothing else will fire with the zone restored.
      await sleep(100)
    }
  }
}
