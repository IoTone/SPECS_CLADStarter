/**
 * Shared helpers for the Castle Clash LEAF scenarios.
 *
 * Game access strategy (no game-script edits needed):
 *  - CastleClashMain is found on the "Castle Clash" SceneObject.
 *  - `main.simulation` (public) exposes the live Snapshot (`state`) and the rules.
 *  - `main.hud` (public @input) exposes the HUD component.
 *  - A few private fields (multiplayer, session, localSide, pendingStatus) are read
 *    through `any` for assertions only; they are never written.
 *
 * UI is driven through real SIK interactables (UIKit Buttons/Sliders) with
 * DefaultLeafInteractor, so HUD wiring is exercised end-to-end.
 */
import {DefaultLeafInteractor} from "Leaf.lspkg/Interactors/interactor/DefaultLeafInteractor"
import {findInteractablesByName} from "Leaf.lspkg/Interactors/InteractableUtils"
import {findSceneObjectByName, nextFrame, sleep} from "Leaf.lspkg/Utils/common/Utils"
import {Interactable} from "SpectaclesInteractionKit.lspkg/Components/Interaction/Interactable/Interactable"
import {CastleClashMain} from "../../Scripts/CastleClashMain"
import {Snapshot} from "../../Scripts/CastleClashSimulation"

export const SIM_DT = 1 / 120

export function log(msg: string): void {
  print("[CastleClashLeaf] " + msg)
}

export function getMain(): CastleClashMain | undefined {
  const so = findSceneObjectByName("Castle Clash")
  if (!so) return undefined
  const main = so.getComponent(CastleClashMain.getTypeName()) as CastleClashMain
  return isNull(main) ? undefined : main
}

/** Returns the main component once its OnStart has created the simulation. */
export function requireStartedMain(): CastleClashMain {
  const main = getMain()
  if (!main || !main.simulation) {
    throw new Error("Castle Clash has not started (EnableOnReady not enabled yet?)")
  }
  return main
}

export function state(): Snapshot {
  return requireStartedMain().simulation.state
}

export function isMultiplayer(main: CastleClashMain): boolean {
  return (main as any).multiplayer === true
}

export function hudStatus(main: CastleClashMain): string {
  return String((main.hud as any).pendingStatus ?? "")
}

export function hudScore(main: CastleClashMain): string {
  return String((main.hud as any).pendingScore ?? "")
}

export async function waitUntil(
  cond: () => boolean,
  timeoutMs: number,
  label: string,
): Promise<void> {
  const deadline = getTime() * 1000 + timeoutMs
  while (!cond()) {
    if (getTime() * 1000 > deadline) {
      throw new Error(`Timed out after ${timeoutMs}ms waiting for: ${label}`)
    }
    await nextFrame()
  }
}

export function findEnabledInteractable(name: string): Interactable | undefined {
  return findInteractablesByName(name, undefined, true)[0]
}

export class CastleClashLeafInteractor extends DefaultLeafInteractor {
  constructor() {
    super("CastleClashLeafInteractor")
  }

  /** Taps an enabled UIKit button (a SIK Interactable) by its SceneObject name. */
  async tapButton(name: string, timeoutMs = 3000): Promise<void> {
    let button: Interactable | undefined
    await waitUntil(
      () => (button = findEnabledInteractable(name)) !== undefined,
      timeoutMs,
      `enabled button "${name}"`,
    )
    await this.trigger(button)
    await sleep(150)
  }
}

/**
 * Brings the Lens into the offline Solo/CPU game:
 *  - If the SyncKit start menu is showing, presses "SoloButton".
 *  - If the game had started in Multiplayer, presses "Play CPU" (offline switch).
 * Leaves the simulation in whatever phase it was in otherwise.
 */
export async function ensureSolo(interactor: CastleClashLeafInteractor): Promise<CastleClashMain> {
  // The start menu appears shortly after Lens start; wait for either the menu or a started game.
  await waitUntil(
    () => findEnabledInteractable("SoloButton") !== undefined || !!getMain()?.simulation,
    8000,
    "start menu SoloButton or a started Castle Clash game",
  )
  if (findEnabledInteractable("SoloButton")) {
    log("Start menu visible, pressing Solo")
    await interactor.tapButton("SoloButton")
  }
  await waitUntil(() => !!getMain()?.simulation, 5000, "CastleClashMain OnStart (simulation created)")
  const main = requireStartedMain()
  if (isMultiplayer(main)) {
    log("Game is in Multiplayer mode, pressing Play CPU to switch offline")
    await ensurePractice(interactor, main)
    await interactor.tapButton("Play CPU")
    await waitUntil(() => !isMultiplayer(main), 2000, "offline mode after Play CPU")
  }
  return main
}

/**
 * Fast-forwards the real simulation (with CPU enabled, human side idle) in large chunks per
 * frame until `done()` returns true. This is time acceleration only: the same step() the Lens
 * runs at 120 Hz; no state is injected.
 */
export async function fastForward(
  main: CastleClashMain,
  done: (s: Snapshot) => boolean,
  maxSimSeconds: number,
  onStep?: (s: Snapshot) => void,
): Promise<number> {
  const sim = main.simulation
  const stepsPerFrame = 600 // 5 simulated seconds per rendered frame
  let simulated = 0
  while (!done(sim.state)) {
    if (simulated >= maxSimSeconds) {
      throw new Error(
        `Condition not reached after ${maxSimSeconds}s of simulated play (phase=${sim.state.phase}, scores=${sim.state.scores})`,
      )
    }
    for (let i = 0; i < stepsPerFrame && !done(sim.state); i++) {
      sim.step(SIM_DT, true)
      simulated += SIM_DT
      if (onStep) onStep(sim.state)
    }
    await nextFrame()
  }
  return simulated
}

/**
 * Gets the offline game back to 'practice' from any phase, using only player-reachable actions
 * plus time acceleration (a paused/in-progress game has no reset button, so it is played out).
 */
export async function ensurePractice(
  interactor: CastleClashLeafInteractor,
  main: CastleClashMain,
): Promise<void> {
  const s = () => main.simulation.state
  if (s().phase === "practice") return
  if (s().phase === "paused") {
    main.simulation.ready() // same call the Ready button makes offline
  }
  if (s().phase !== "match") {
    await fastForward(main, (st) => st.phase === "match", 1800)
  }
  await interactor.tapButton("Play CPU")
  await waitUntil(() => s().phase === "practice", 2000, "practice after Play CPU")
}

/** From practice, presses Ready and waits for the serve. */
export async function startRally(
  interactor: CastleClashLeafInteractor,
  main: CastleClashMain,
): Promise<void> {
  const s = () => main.simulation.state
  await interactor.tapButton("Ready")
  await waitUntil(() => s().phase === "countdown" || s().phase === "playing", 2000, "countdown after Ready")
  await waitUntil(
    () => s().phase === "playing",
    (main.simulation.rules.countdown + 2) * 1000,
    "playing after countdown",
  )
}
