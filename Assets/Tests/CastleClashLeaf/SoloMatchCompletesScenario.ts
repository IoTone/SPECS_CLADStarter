/**
 * Scenario 2: a Solo first-to-N match completes.
 * Approach: the match is started through the real HUD (Play CPU / Ready), then the live
 * simulation is fast-forwarded with its own step() at 120 Hz (CPU on, human idle), up to
 * `maxSimSeconds` of simulated play. No state is injected; sudden death guarantees progress.
 */
import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {ScenarioConfig} from "Leaf.lspkg/Scenarios/scenario/ScenarioConfig"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {nextFrame} from "Leaf.lspkg/Utils/common/Utils"
import {
  CastleClashLeafInteractor,
  ensurePractice,
  ensureSolo,
  fastForward,
  hudScore,
  hudStatus,
  log,
  startRally,
} from "./CastleClashLeafHelpers"

@component
export class SoloMatchCompletesScenario extends Scenario {
  async run(config?: ScenarioConfig): Promise<void> {
    const maxSimSeconds = config?.getNumber("maxSimSeconds") ?? 1800
    const interactor = new CastleClashLeafInteractor()
    const main = await ensureSolo(interactor)
    const sim = main.simulation
    await ensurePractice(interactor, main)
    await startRally(interactor, main)

    const wins = sim.rules.wins
    const phasesSeen = new Set<string>()
    let rounds = 0
    let lastPhase = sim.state.phase
    const simulated = await fastForward(
      main,
      (st) => st.phase === "match",
      maxSimSeconds,
      (st) => {
        phasesSeen.add(st.phase)
        if (st.phase === "round" && lastPhase !== "round") rounds++
        lastPhase = st.phase
      },
    )
    await nextFrame()
    await nextFrame()
    const s = sim.state
    log(`match finished after ${simulated.toFixed(1)}s simulated; scores=${s.scores} winner=${s.winner} rounds=${rounds} phases=${Array.from(phasesSeen)}`)

    expect(s.phase).toBe("match")
    expect(s.winner === 0 || s.winner === 1, `winner ${s.winner}`).toBe(true)
    expect(s.scores[s.winner]).toBe(wins)
    expect(s.scores[1 - s.winner], "loser below win threshold").toBeLessThan(wins)
    // First-to-two requires at least one intermediate round break (round -> countdown -> serve).
    if (wins > 1) expect(rounds, "intermediate round breaks").toBeGreaterThan(0)
    expect(hudStatus(main).includes("wins the match"), `status: ${hudStatus(main)}`).toBe(true)
    expect(hudScore(main).includes(`${s.scores[0]}  —  ${s.scores[1]}`), `score: ${hudScore(main)}`).toBe(true)

    // Match is terminal: time passing must not change the result.
    const before = s.scores.slice()
    for (let i = 0; i < 600; i++) sim.step(1 / 120, true)
    expect(sim.state.phase).toBe("match")
    expect(sim.state.scores[0]).toBe(before[0])
    expect(sim.state.scores[1]).toBe(before[1])
  }
}
