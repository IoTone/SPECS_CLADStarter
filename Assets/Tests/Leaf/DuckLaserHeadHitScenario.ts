// Scenario 3 — An unblocked laser reaching the head ends the run: phase "over", timer frozen,
// button "Play Again", best time updated (and persisted when beaten).

import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {sleep} from "Leaf.lspkg/Utils/common/Utils"
import {DefaultLeafInteractor} from "Leaf.lspkg/Interactors/interactor/DefaultLeafInteractor"
import {DuckLaserHooks, log, readPersistedBest, waitUntil} from "./DuckLaserTestHooks"

@component
export class DuckLaserHeadHitScenario extends Scenario {
  async run(): Promise<void> {
    await sleep(500)
    const h = new DuckLaserHooks()
    const interactor = new DefaultLeafInteractor()
    const restoreFallback = h.setShieldFallback(false)
    const restoreZone = h.forceDangerZone(true)
    try {
      await h.startFreshRun(interactor)
      const bestBefore = h.best
      await sleep(100)
      log(`head-hit: bestBefore=${bestBefore.toFixed(2)} shieldActive=${h.shield.getShieldState().active}`)
      expect(h.shield.getShieldState().active).toBe(false)

      const ended = await waitUntil(() => h.phase === "over", 8000)
      const final = h.survived
      log(`head-hit: ended=${ended} survived=${final.toFixed(2)} hud="${h.timeText}" best="${h.bestText}" button="${h.buttonLabel}" status="${h.statusText}"`)
      expect(ended).toBe(true)
      expect(final).toBeGreaterThan(0.5)

      // Timer stops (danger zone still forced on).
      await sleep(1000)
      log(`head-hit: 1s later survived=${h.survived.toFixed(2)} hud="${h.timeText}" phase=${h.phase}`)
      expect(h.phase).toBe("over")
      expect(h.survived).toBe(final)
      expect(h.timeText).toBe(`Time ${DuckLaserHooks.fmt(final)}`)

      expect(h.buttonLabel).toBe("Play Again")
      expect(h.statusText.includes("SHOT DOWN")).toBe(true)

      // Best = max(previous best, this run); HUD shows it.
      const expectedBest = Math.max(bestBefore, final)
      expect(h.best).toBeCloseTo(expectedBest, 4)
      expect(h.bestText).toBe(`Best ${DuckLaserHooks.fmt(expectedBest)}`)
      const persisted = readPersistedBest()
      log(`head-hit: best=${h.best.toFixed(3)} persisted=${persisted === null ? "n/a" : persisted.toFixed(3)} newBest=${final > bestBefore}`)
      if (final > bestBefore) {
        expect(persisted !== null).toBe(true)
        expect(persisted as number).toBeCloseTo(final, 2)
      }
    } finally {
      restoreZone()
      restoreFallback()
    }
  }
}
