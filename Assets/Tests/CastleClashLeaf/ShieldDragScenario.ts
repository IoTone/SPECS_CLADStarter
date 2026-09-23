/**
 * Scenario 3 (regression): the player's shield responds DURING a slider drag, not only on release.
 * Drags the in-play "Shield control" UIKit Slider through SIK and samples the simulation every
 * frame while the Interactable reports an active drag (between onDragStart and onDragEnd).
 * Before the onKnobMoved fix, targets[0] only changed at release (onValueChange).
 */
import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {nextFrame, sleep} from "Leaf.lspkg/Utils/common/Utils"
import {Slider} from "SpectaclesUIKit.lspkg/Scripts/Components/Slider/Slider"
import {
  CastleClashLeafInteractor,
  ensurePractice,
  ensureSolo,
  findEnabledInteractable,
  log,
  startRally,
  waitUntil,
} from "./CastleClashLeafHelpers"

@component
export class ShieldDragScenario extends Scenario {
  async run(): Promise<void> {
    const interactor = new CastleClashLeafInteractor()
    const main = await ensureSolo(interactor)
    const s = () => main.simulation.state

    if (s().phase !== "playing" && s().phase !== "countdown") {
      await ensurePractice(interactor, main)
      await startRally(interactor, main)
    }
    await waitUntil(() => findEnabledInteractable("Shield control") !== undefined, 2000, "in-play Shield control slider")
    const interactable = findEnabledInteractable("Shield control")
    const slider = interactable.getSceneObject().getComponent(Slider.getTypeName()) as Slider
    expect(isNull(slider), "Shield control has a UIKit Slider").toBe(false)

    // Drag away from the nearer end so the value has room to change.
    const startValue = slider.currentValue
    const dir = startValue > 0.5 ? -1 : 1
    const worldRight = interactable.getSceneObject().getTransform().right
    const dragPerUpdate = worldRight.uniformScale(dir * 0.12)

    const target0 = s().targets[0]
    const shield0 = s().shields[0]
    let dragging = false
    let released = false
    let samples = 0
    let maxTargetDelta = 0
    let maxShieldDelta = 0
    let phaseBroke = false
    const offStart = interactable.onDragStart.add(() => (dragging = true))
    const offEnd = interactable.onDragEnd.add(() => {
      dragging = false
      released = true
    })
    try {
      const drag = interactor.drag(interactable, dragPerUpdate, 1200)
      while (!released) {
        await nextFrame()
        if (dragging && !released) {
          samples++
          if (s().phase === "round" || s().phase === "match") phaseBroke = true
          maxTargetDelta = Math.max(maxTargetDelta, Math.abs(s().targets[0] - target0))
          maxShieldDelta = Math.max(maxShieldDelta, Math.abs(s().shields[0] - shield0))
        }
      }
      await drag
    } finally {
      offStart()
      offEnd()
    }
    await sleep(200)
    log(`drag samples=${samples} startValue=${startValue.toFixed(3)} endValue=${slider.currentValue.toFixed(3)} target ${target0.toFixed(2)}->${s().targets[0].toFixed(2)} maxTargetDeltaDuringDrag=${maxTargetDelta.toFixed(2)} maxShieldDeltaDuringDrag=${maxShieldDelta.toFixed(2)} phaseBroke=${phaseBroke}`)

    if (phaseBroke) {
      throw new Error("A round ended during the drag (targets reset); rerun the scenario")
    }
    expect(samples, "frames observed while dragging").toBeGreaterThan(5)
    expect(Math.abs(slider.currentValue - startValue), "slider value changed after release").toBeGreaterThan(0.05)
    expect(maxTargetDelta, "shield target changed before release").toBeGreaterThan(1)
    expect(maxShieldDelta, "shield position moved before release").toBeGreaterThan(0.3)
    // After release, the sim target matches the slider (teal side: value * 54).
    expect(s().targets[0]).toBeCloseTo(slider.currentValue * 54, 1)
  }
}
