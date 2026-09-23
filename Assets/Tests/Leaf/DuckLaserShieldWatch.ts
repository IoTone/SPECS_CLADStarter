// Shared helper for the shield scenarios: counts deflection events on the live laser pool.

import {sleep} from "Leaf.lspkg/Utils/common/Utils"
import {DuckLaserHooks} from "./DuckLaserTestHooks"

export interface DeflectionWatch {
  deflections: number
  shotsSeen: number
  awayFromHead: number // deflected lasers observed moving away from the head
  endedEarly: boolean
}

/** Watch the pool for `durationMs`, counting not-deflected -> deflected transitions per slot. */
export async function watchDeflections(h: DuckLaserHooks, durationMs: number, stopOnGameOver = true): Promise<DeflectionWatch> {
  const pool = h.laserPool
  const prevDeflected = pool.map((l) => l.alive && l.deflected)
  const prevAlive = pool.map((l) => l.alive)
  const res: DeflectionWatch = {deflections: 0, shotsSeen: 0, awayFromHead: 0, endedEarly: false}
  let elapsed = 0
  while (elapsed < durationMs) {
    await sleep(20)
    elapsed += 20
    const head = h.headPos
    for (let i = 0; i < pool.length; i++) {
      const l = pool[i]
      if (l.alive && !prevAlive[i]) res.shotsSeen++
      const d = l.alive && l.deflected
      if (d && !prevDeflected[i]) {
        res.deflections++
        if (l.vel.dot(head.sub(l.pos)) < 0) res.awayFromHead++
      }
      prevDeflected[i] = d
      prevAlive[i] = l.alive
    }
    if (stopOnGameOver && h.phase === "over") {
      res.endedEarly = true
      break
    }
  }
  return res
}
