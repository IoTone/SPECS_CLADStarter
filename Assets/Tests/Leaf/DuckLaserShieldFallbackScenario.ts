// Scenario 4a — The authored untrackedFallback shield (no hand tracked in preview) activates in
// front of the camera and deflects at least one incoming laser.
// untrackedFallback and debugIgnoreProximity are toggled at runtime only and restored in finally.

import {Scenario} from "Leaf.lspkg/Scenarios/scenario/Scenario"
import {expect} from "Leaf.lspkg/Utils/common/Expect"
import {findSceneObjectByName, sleep} from "Leaf.lspkg/Utils/common/Utils"
import {DefaultLeafInteractor} from "Leaf.lspkg/Interactors/interactor/DefaultLeafInteractor"
import {DuckLaserHooks, log} from "./DuckLaserTestHooks"
import {watchDeflections} from "./DuckLaserShieldWatch"

@component
export class DuckLaserShieldFallbackScenario extends Scenario {
  async run(): Promise<void> {
    await sleep(500)
    const h = new DuckLaserHooks()
    const interactor = new DefaultLeafInteractor()
    const restoreFallback = h.setShieldFallback(true)
    const restoreZone = h.forceDangerZone(false)
    try {
      await sleep(300)
      const s = h.shield.getShieldState()
      const head = h.headPos
      const camRot = h.main.headCamera.getTransform().getWorldRotation()
      const look = camRot.multiplyVec3(new vec3(0, 0, -1))
      const ahead = s.center.sub(head).dot(look)
      log(
        `shield-fallback: active=${s.active} visual=${findSceneObjectByName("ShieldVisual").enabled} ` +
          `center=${s.center.toString()} head=${head.toString()} aheadOfCamera=${ahead.toFixed(1)}cm radius=${s.radiusCm}`,
      )
      expect(s.active).toBe(true)
      expect(findSceneObjectByName("ShieldVisual").enabled).toBe(true)
      expect(ahead).toBeGreaterThan(30)

      // Geometric check: how far is the shield center from the duck->head line?
      const muzzle = h.main.duck.getMuzzleWorld(0).add(h.main.duck.getMuzzleWorld(1)).uniformScale(0.5)
      const dir = head.sub(muzzle).normalize()
      const rel = s.center.sub(muzzle)
      const offLine = rel.sub(dir.uniformScale(rel.dot(dir))).length
      log(`shield-fallback: shield center is ${offLine.toFixed(1)}cm off the duck->head laser line (radius ${s.radiusCm}cm, aim jitter ${h.main.aimJitterCm}cm)`)

      h.forceDangerZone(true)
      await h.startFreshRun(interactor)
      const w = await watchDeflections(h, 7000)
      log(`shield-fallback: shots=${w.shotsSeen} deflections=${w.deflections} awayFromHead=${w.awayFromHead} gameOver=${w.endedEarly} survived=${h.survived.toFixed(2)}`)
      expect(w.shotsSeen).toBeGreaterThan(0)
      expect(w.deflections).toBeGreaterThan(0)
    } finally {
      restoreZone()
      restoreFallback()
    }
  }
}
