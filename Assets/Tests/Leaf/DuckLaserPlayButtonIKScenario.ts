// Scenario 6 — IK reachability: a Bitmoji IK avatar presses the HUD play button the way a real
// user would. The HUD sits ~160 cm away, so this is expected to route far-field (ray) rather
// than a direct poke; the LEAF diagnostic report records the routing decision.

import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {sleep} from "Leaf.lspkg/Utils/common/Utils"
import {findInteractableByName} from "Leaf.lspkg/Interactors/InteractableUtils"
import {createIKInteractor} from "Leaf.lspkg/Interactors/interactor/ik/visualizer/BitmojiAvatar"
import {DuckLaserHooks, log} from "./DuckLaserTestHooks"

@component
export class DuckLaserPlayButtonIKScenario extends Scenario {
  private readonly ik = createIKInteractor()

  async run(): Promise<void> {
    await sleep(1000)
    const h = new DuckLaserHooks()
    const restoreZone = h.forceDangerZone(false)
    try {
      const button = findInteractableByName("PlayButton", undefined, true)
      expect(button !== undefined).toBe(true)
      const dist = button.getTransform().getWorldPosition().distance(h.headPos)
      log(`ik-play: PlayButton is ${dist.toFixed(1)}cm from the head; phase before=${h.phase}`)

      await this.ik.trigger(button)
      await sleep(300)
      log(`ik-play: after IK trigger phase=${h.phase} button="${h.buttonLabel}" survived=${h.survived.toFixed(2)}`)
      expect(h.phase).toBe("playing")
      expect(h.buttonLabel).toBe("Restart")
      expect(h.survived).toBeLessThan(0.5)
    } finally {
      restoreZone()
    }
  }
}
