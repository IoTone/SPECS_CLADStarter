/**
 * Scenario 4: after a finished match, Play CPU and Rematch both clear scores and rebuild walls
 * (24 walls at 2 hp). Matches are completed by fast-forwarding the real simulation.
 */
import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {nextFrame} from "Leaf.lspkg/Utils/common/Utils"
import {CastleClashMain} from "../../Scripts/CastleClashMain"
import {
  CastleClashLeafInteractor,
  ensurePractice,
  ensureSolo,
  fastForward,
  log,
  startRally,
  waitUntil,
} from "./CastleClashLeafHelpers"

function expectFreshBoard(main: CastleClashMain, label: string): void {
  const s = main.simulation.state
  expect(s.scores[0], `${label}: teal score`).toBe(0)
  expect(s.scores[1], `${label}: amber score`).toBe(0)
  expect(s.walls.length, `${label}: wall count`).toBe(24)
  expect(s.walls.every((hp) => hp === 2), `${label}: walls ${s.walls.join(",")}`).toBe(true)
  expect(s.winner, `${label}: winner cleared`).toBe(-1)
}

async function playToMatch(interactor: CastleClashLeafInteractor, main: CastleClashMain): Promise<void> {
  if (main.simulation.state.phase === "match") return
  if (main.simulation.state.phase === "practice") await startRally(interactor, main)
  await fastForward(main, (st) => st.phase === "match", 1800)
  await nextFrame()
  const damaged = main.simulation.state.walls.filter((hp) => hp < 2).length
  log(`match reached: scores=${main.simulation.state.scores} damagedWalls=${damaged}`)
  expect(Math.max(...main.simulation.state.scores)).toBe(main.simulation.rules.wins)
  expect(damaged, "a completed match leaves damaged walls (sudden death or hits)").toBeGreaterThan(0)
}

@component
export class RematchResetScenario extends Scenario {
  async run(): Promise<void> {
    const interactor = new CastleClashLeafInteractor()
    const main = await ensureSolo(interactor)
    const phase = () => main.simulation.state.phase

    // Path A: Play CPU after a finished match.
    if (phase() !== "match") {
      await ensurePractice(interactor, main)
      await playToMatch(interactor, main)
    }
    await interactor.tapButton("Play CPU")
    await waitUntil(() => phase() === "practice", 2000, "practice after Play CPU")
    expectFreshBoard(main, "Play CPU")

    // Path B: Rematch after a finished match (resets and starts the countdown).
    await playToMatch(interactor, main)
    await interactor.tapButton("Rematch")
    await waitUntil(() => phase() === "countdown", 2000, "countdown after Rematch")
    expectFreshBoard(main, "Rematch")
    await waitUntil(() => phase() === "playing", (main.simulation.rules.countdown + 2) * 1000, "playing after Rematch")
    expect(main.simulation.state.walls.every((hp) => hp === 2), "walls intact at rematch serve").toBe(true)
  }
}
