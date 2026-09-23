import {scenariosIndex} from "Leaf.lspkg/Scenarios/decorator/ScenarioIndexDecorator"
import {ScenarioMetadata} from "Leaf.lspkg/Scenarios/scenario/ScenarioMetadata"
import {MultiplayerEntryScenario} from "./MultiplayerEntryScenario"
import {RematchResetScenario} from "./RematchResetScenario"
import {ShieldDragScenario} from "./ShieldDragScenario"
import {SoloCpuStartScenario} from "./SoloCpuStartScenario"
import {SoloMatchCompletesScenario} from "./SoloMatchCompletesScenario"

@component
export class LeafIndex extends BaseScriptComponent {
  @scenariosIndex
  static scenariosIndex: ScenarioMetadata[] = [
    {id: "castle-solo-cpu-start", typename: SoloCpuStartScenario.getTypeName()},
    {
      id: "castle-solo-match-completes",
      typename: SoloMatchCompletesScenario.getTypeName(),
      parameters: {maxSimSeconds: "1800"},
    },
    {id: "castle-shield-drag", typename: ShieldDragScenario.getTypeName()},
    {id: "castle-rematch-reset", typename: RematchResetScenario.getTypeName()},
    {
      id: "castle-multiplayer-entry",
      typename: MultiplayerEntryScenario.getTypeName(),
      parameters: {waitSecs: "20", requireReady: "false"},
    },
  ]
}
