// LeafIndex — registers the Laser Duck LEAF scenarios (test-only; lives on the "LeafIndex" SceneObject).

import {scenariosIndex} from "Leaf.lspkg/Scenarios/decorator/ScenarioIndexDecorator"
import {ScenarioMetadata} from "Leaf.lspkg/Scenarios/scenario/ScenarioMetadata"
import {DuckLaserStartRunScenario} from "./DuckLaserStartRunScenario"
import {DuckLaserDangerZoneScenario} from "./DuckLaserDangerZoneScenario"
import {DuckLaserHeadHitScenario} from "./DuckLaserHeadHitScenario"
import {DuckLaserShieldFallbackScenario} from "./DuckLaserShieldFallbackScenario"
import {DuckLaserShieldInPathScenario} from "./DuckLaserShieldInPathScenario"
import {DuckLaserRestartScenario} from "./DuckLaserRestartScenario"
import {DuckLaserPlayButtonIKScenario} from "./DuckLaserPlayButtonIKScenario"

@component
export class LeafIndex extends BaseScriptComponent {
  @scenariosIndex
  static scenariosIndex: ScenarioMetadata[] = [
    {id: "duck-1-start-run", typename: DuckLaserStartRunScenario.getTypeName()},
    {id: "duck-2-danger-zone", typename: DuckLaserDangerZoneScenario.getTypeName()},
    {id: "duck-3-head-hit", typename: DuckLaserHeadHitScenario.getTypeName()},
    {id: "duck-4a-shield-fallback", typename: DuckLaserShieldFallbackScenario.getTypeName()},
    {id: "duck-4b-shield-in-path", typename: DuckLaserShieldInPathScenario.getTypeName()},
    {id: "duck-5-restart", typename: DuckLaserRestartScenario.getTypeName()},
    {id: "duck-6-ik-play-button", typename: DuckLaserPlayButtonIKScenario.getTypeName()},
  ]
}
