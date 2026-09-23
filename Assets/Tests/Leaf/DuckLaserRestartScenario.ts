// Scenario 5 — Restart resets the timer to 0: both mid-run ("Restart") and after game over
// ("Play Again"). The in-flight lasers are cleared as well.

import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {sleep} from "Leaf.lspkg/Utils/common/Utils"
import {DefaultLeafInteractor} from "Leaf.lspkg/Interactors/interactor/DefaultLeafInteractor"
import {DuckLaserHooks, log, waitUntil} from "./DuckLaserTestHooks"

@component
export class DuckLaserRestartScenario extends Scenario {
  async run(): Promise<void> {
    await sleep(500)
    const h = new DuckLaserHooks()
    const interactor = new DefaultLeafInteractor()
    const restoreFallback = h.setShieldFallback(false)
    const restoreZone = h.forceDangerZone(false)
    try {
      // A) Mid-run restart.
      await h.startFreshRun(interactor)
      h.forceDangerZone(true)
      const accrued = await waitUntil(() => h.survived >= 1.0 && h.aliveLasers.length > 0, 3000)
      h.forceDangerZone(false) // freeze the clock so the post-restart value is deterministic
      log(`restart: mid-run before survived=${h.survived.toFixed(2)} hud="${h.timeText}" button="${h.buttonLabel}" alive=${h.aliveLasers.length} phase=${h.phase}`)
      expect(accrued).toBe(true)
      expect(h.phase).toBe("playing")
      expect(h.buttonLabel).toBe("Restart")

      await h.pressPlay(interactor)
      log(`restart: mid-run after survived=${h.survived.toFixed(2)} hud="${h.timeText}" alive=${h.aliveLasers.length} phase=${h.phase}`)
      expect(h.phase).toBe("playing")
      expect(h.survived).toBe(0)
      expect(h.timeText).toBe("Time 0.0s")
      expect(h.aliveLasers.length).toBe(0)

      // B) Play Again after being shot down.
      h.forceDangerZone(true)
      const over = await waitUntil(() => h.phase === "over", 8000)
      h.forceDangerZone(false)
      log(`restart: over=${over} survived=${h.survived.toFixed(2)} button="${h.buttonLabel}"`)
      expect(over).toBe(true)
      expect(h.buttonLabel).toBe("Play Again")
      expect(h.survived).toBeGreaterThan(0)

      await h.pressPlay(interactor)
      log(`restart: play-again after survived=${h.survived.toFixed(2)} hud="${h.timeText}" button="${h.buttonLabel}" phase=${h.phase}`)
      expect(h.phase).toBe("playing")
      expect(h.survived).toBe(0)
      expect(h.timeText).toBe("Time 0.0s")
      expect(h.buttonLabel).toBe("Restart")
      expect(h.aliveLasers.length).toBe(0)
    } finally {
      restoreZone()
      restoreFallback()
    }
  }
}
