/**
 * Scenario 5: Multiplayer entry (single-preview coverage only).
 *
 * REQUIRES a freshly reset preview with the SyncKit start menu showing (run it first, or after a
 * preview refresh). It verifies:
 *  - structure: "Castle Clash" (with its HUD) lives under ColocatedWorld / EnableOnReady and the
 *    game has not started before a mode is chosen;
 *  - pressing "MultiplayerButton" hides the start menu and enters the SyncKit session flow
 *    without a connection-failure / no-internet error during `waitSecs`;
 *  - if the session becomes ready in preview: EnableOnReady turns on, CastleClashMain starts in
 *    multiplayer mode, its SyncEntity becomes ready, and the host can claim the Teal seat.
 *
 * NEEDS TWO DEVICES (not covered here): the second player claiming Amber, both-Ready start,
 * authoritative snapshot replication to the peer, peer shield intents, heartbeat-loss pause,
 * owner-loss lockout, colocated board alignment and real network latency.
 */
import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {ScenarioConfig} from "Leaf.lspkg/Scenarios/scenario/ScenarioConfig"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {findSceneObjectByName, sleep} from "Leaf.lspkg/Utils/common/Utils"
import {SessionController} from "SpectaclesSyncKit.lspkg/Core/SessionController"
import {
  CastleClashLeafInteractor,
  findEnabledInteractable,
  getMain,
  hudStatus,
  isMultiplayer,
  log,
  waitUntil,
} from "./CastleClashLeafHelpers"

@component
export class MultiplayerEntryScenario extends Scenario {
  async run(config?: ScenarioConfig): Promise<void> {
    const waitSecs = config?.getNumber("waitSecs") ?? 20
    const requireReady = config?.get("requireReady") === "true"
    const interactor = new CastleClashLeafInteractor()

    // --- Structure: shared content under ColocatedWorld / EnableOnReady.
    const castle = findSceneObjectByName("Castle Clash")
    expect(castle !== undefined, "Castle Clash scene object exists").toBe(true)
    const enableOnReady = castle.getParent()
    expect(enableOnReady?.name).toBe("EnableOnReady")
    const colocated = enableOnReady.getParent()
    expect(colocated !== null && colocated.name.startsWith("ColocatedWorld"), `grandparent ${colocated?.name}`).toBe(true)
    const hudObject = findSceneObjectByName("Castle Clash Controls", castle)
    expect(hudObject !== undefined, "HUD lives under Castle Clash").toBe(true)
    expect(findSceneObjectByName("Castle Clash Board", castle) !== undefined, "board lives under Castle Clash").toBe(true)

    // --- Must start from the start menu.
    await waitUntil(() => findEnabledInteractable("MultiplayerButton") !== undefined || !!getMain()?.simulation, 8000, "start menu")
    if (!findEnabledInteractable("MultiplayerButton")) {
      throw new Error("Start menu is not showing (a mode was already chosen). Refresh the preview and run this scenario first.")
    }
    expect(enableOnReady.enabled, "EnableOnReady disabled before a mode is chosen").toBe(false)
    expect(!!getMain()?.simulation, "game not started before a mode is chosen").toBe(false)

    const sc = SessionController.getInstance()
    const failures: string[] = []
    sc.onConnectionFailed.add((code: string, description: string) => failures.push(`${code}: ${description}`))

    log(`internet available=${global.deviceInfoSystem.isInternetAvailable()}`)
    await interactor.tapButton("MultiplayerButton")
    await waitUntil(() => findEnabledInteractable("MultiplayerButton") === undefined, 2000, "start menu hidden after Multiplayer")
    await sleep(300)
    const noInternet = findSceneObjectByName("NoInternetError")
    expect(noInternet?.enabled === true, "no-internet error shown").toBe(false)

    // --- Wait for the SyncKit session.
    const deadline = getTime() + waitSecs
    while (!sc.getIsReady() && failures.length === 0 && getTime() < deadline) {
      await sleep(250)
    }
    log(`after ${waitSecs}s max: ready=${sc.getIsReady()} state=${String(sc.getState())} failures=${JSON.stringify(failures)} users=${sc.getIsReady() ? sc.getUsers().length : 0}`)
    expect(failures.length, `connection failures: ${failures.join(" | ")}`).toBe(0)

    if (!sc.getIsReady()) {
      if (requireReady) throw new Error(`SyncKit session not ready after ${waitSecs}s`)
      log("SyncKit session did not become ready in this preview; session flow entered without errors (requires a logged-in Lens Studio / device for the rest).")
      return
    }

    // --- Session ready: the shared game starts in multiplayer mode.
    await waitUntil(() => enableOnReady.enabled && !!getMain()?.simulation, 3000, "EnableOnReady + CastleClashMain started")
    const main = getMain()
    expect(isMultiplayer(main), "CastleClashMain in multiplayer mode").toBe(true)
    const session = (main as any).session
    await waitUntil(() => session && session.ready === true, 10000, "Castle Clash SyncEntity ready")
    log(`session ready: owner=${session.isOwner()} localId=${session.localId} status="${hudStatus(main)}"`)
    expect(session.isOwner(), "single preview is the store owner / host").toBe(true)
    await waitUntil(() => hudStatus(main).includes("Choose the castle"), 3000, "seat prompt")

    // Host claims Teal through the HUD (intent echoes locally to the authority).
    await interactor.tapButton("Teal")
    await waitUntil(() => (main as any).localSide === 0, 3000, "local seat = teal")
    expect(hudStatus(main).includes("practice"), `status after seat: ${hudStatus(main)}`).toBe(true)

    // Ready alone must NOT start: both seats are required (second device needed).
    await interactor.tapButton("Ready")
    await sleep(800)
    expect(main.simulation.state.phase, "one player cannot start a friend match").toBe("practice")
    log("Multiplayer single-preview checks passed. Second-player flow requires two devices.")
  }
}
