/**
 * Scenario 1: Solo / Play CPU starts without a multiplayer session.
 * Start menu -> Solo -> Play CPU -> Ready -> countdown -> playing; ball moves;
 * CPU shield moves and never exceeds the shared shield speed cap.
 */
import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {findSceneObjectByName, nextFrame} from "Leaf.lspkg/Utils/common/Utils"
import {SessionController} from "SpectaclesSyncKit.lspkg/Core/SessionController"
import {
  CastleClashLeafInteractor,
  ensurePractice,
  ensureSolo,
  hudStatus,
  isMultiplayer,
  log,
  waitUntil,
} from "./CastleClashLeafHelpers"

@component
export class SoloCpuStartScenario extends Scenario {
  async run(): Promise<void> {
    const interactor = new CastleClashLeafInteractor()
    const main = await ensureSolo(interactor)
    const sim = main.simulation
    const s = () => sim.state

    expect(isMultiplayer(main), "Solo game must not be in multiplayer mode").toBe(false)
    expect(SessionController.getInstance().getIsReady(), "Solo must not start a SyncKit session").toBe(false)

    await ensurePractice(interactor, main)
    // Play CPU from practice starts a new local match.
    await interactor.tapButton("Play CPU")
    expect(s().phase).toBe("practice")
    expect(hudStatus(main).includes("practice"), `status: ${hudStatus(main)}`).toBe(true)

    await interactor.tapButton("Ready")
    await waitUntil(() => s().phase === "countdown", 1500, "countdown after Ready")
    await nextFrame()
    expect(hudStatus(main).includes("Get ready"), `status: ${hudStatus(main)}`).toBe(true)
    await waitUntil(() => s().phase === "playing", (sim.rules.countdown + 2) * 1000, "playing after countdown")

    // Compact in-play controls replace the setup panel.
    await nextFrame()
    expect(findSceneObjectByName("Play controls").enabled, "compact play controls visible").toBe(true)
    expect(findSceneObjectByName("Setup controls").enabled, "setup panel hidden").toBe(false)

    const cap = sim.rules.shieldSpeed
    const x0 = s().x
    const z0 = s().z
    const cpu0 = s().shields[1]
    let maxBallTravel = 0
    let cpuTravel = 0
    let worstRate = 0
    let prev = {phase: s().phase, elapsed: s().elapsed, cpu: s().shields[1]}
    const endAt = getTime() + 4
    while (getTime() < endAt) {
      await nextFrame()
      const cur = {phase: s().phase, elapsed: s().elapsed, cpu: s().shields[1]}
      maxBallTravel = Math.max(maxBallTravel, Math.hypot(s().x - x0, s().z - z0))
      if (prev.phase === "playing" && cur.phase === "playing" && cur.elapsed > prev.elapsed) {
        const dt = cur.elapsed - prev.elapsed
        const d = Math.abs(cur.cpu - prev.cpu)
        cpuTravel += d
        worstRate = Math.max(worstRate, d / dt)
        expect(d <= cap * dt + 1e-4, `CPU shield moved ${d.toFixed(3)} in ${dt.toFixed(4)}s (cap ${cap}/s)`).toBe(true)
      }
      prev = cur
    }
    log(`ball travel=${maxBallTravel.toFixed(2)}cm cpuTravel=${cpuTravel.toFixed(2)} worstRate=${worstRate.toFixed(2)}/s cap=${cap} cpu0=${cpu0.toFixed(2)}`)
    expect(maxBallTravel, "ball should move during play").toBeGreaterThan(5)
    expect(cpuTravel, "CPU shield should move in 4s of play").toBeGreaterThan(0.5)
  }
}
