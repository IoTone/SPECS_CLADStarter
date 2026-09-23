// Scenario 1 — Pressing the play button starts a run: phase -> "playing" and the HUD reflects it.

import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {sleep} from "Leaf.lspkg/Utils/common/Utils"
import {DefaultLeafInteractor} from "Leaf.lspkg/Interactors/interactor/DefaultLeafInteractor"
import {DuckLaserHooks, log} from "./DuckLaserTestHooks"

@component
export class DuckLaserStartRunScenario extends Scenario {
  async run(): Promise<void> {
    await sleep(1000)
    const h = new DuckLaserHooks()
    const interactor = new DefaultLeafInteractor()

    const phaseBefore = h.phase
    const labelBefore = h.buttonLabel
    log(`start-run: before phase=${phaseBefore} button="${labelBefore}" time="${h.timeText}"`)
    // Button label must match the phase it is shown in.
    const expectedLabel: Record<string, string> = {idle: "Start", playing: "Restart", over: "Play Again"}
    expect(labelBefore).toBe(expectedLabel[phaseBefore])

    await h.pressPlay(interactor)

    log(`start-run: after phase=${h.phase} button="${h.buttonLabel}" time="${h.timeText}" status="${h.statusText}" survived=${h.survived.toFixed(3)}`)
    expect(h.phase).toBe("playing")
    expect(h.buttonLabel).toBe("Restart")
    expect(h.survived).toBeLessThan(0.5)
    expect(DuckLaserHooks.parseSeconds(h.timeText)).toBeLessThan(0.5)
    // Status either prompts to enter the zone, or (head already in zone) shows the danger message.
    const st = h.statusText
    expect(st.includes("danger zone") || st.includes("DANGER ZONE")).toBe(true)
    // startRun clears the laser pool.
    expect(h.aliveLasers.length).toBe(0)
  }
}
