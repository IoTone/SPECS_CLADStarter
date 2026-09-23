# Castle Clash first playable

Choose **Solo** in the opening menu for an offline match against one CPU. Choose **Multiplayer** for the SyncKit colocated flow, then each player claims Teal or Amber. The host uses Place here, Lower, Raise, and Turn to align the board with the table. Both players select Ready. Pinch the slider and move laterally; the shield follows the three-sided rail. Release to rest.

There are twelve two-hit walls per castle. Hit the exposed crown to win a round; first to two wins. Shield rebounds accelerate the ball, with a speed cap. After 75 seconds, matching wall segments fall every two seconds. Rematch rebuilds the castles and clears score. Pause/recovery preserves the interrupted rally. A lost player or missing heartbeat freezes damage; both players select Ready after recovery. Authority loss does not silently migrate gameplay.

**CPU defaults are a starting average difficulty, not a claim of human playtesting:** observations every 350 ms ±70 ms, stable aim error up to 3.4 cm per decision, 12% chance of an extra hesitation, and a 40 cm/s movement limit shared with humans. Prediction looks ahead at most 1.2 seconds. The CPU cannot repair walls, alter the ball, or teleport. Tune these on the Castle Clash component in the Inspector. Ball starts at 28 cm/s and caps at 62 cm/s.

Leave exits the current friend session and freezes the match. Play CPU starts a new local match. **Reopen the Lens to start a new friend session after leaving**; the installed SyncKit controller does not expose a full public ready-state reset. Two-device table alignment, realistic network latency, tracking interruption, and human difficulty balance still require physical-device validation.

## Implementation map

- `Scripts/CastleClashMain.ts`: lifecycle, input routing, placement, rules tuning, local presentation interpolation.
- `Scripts/CastleClashSimulation.ts`: fixed-step board-local swept collisions, walls, scoring, CPU, sudden death, pause.
- `Scripts/CastleClashSession.ts`: claimed SyncEntity authority, snapshots, authenticated intents, ownership-loss lockout.
- `Scripts/CastleClashHUDUI.ts`: passive UIKit layout, buttons and slider.
- `Scripts/CastleClashGeometry.ts` and `CastleClashPresentation.ts`: procedural modular stone castles, rails, shields, crowns, ball, trail, cosmetic rubble and impact audio.
- `Scripts/CastleClashSimulationChecks.ts`: seven deterministic development checks, including 18,000 simulation steps. Executed successfully in Lens runtime; automatic test invocation removed.
- `GeneratedSFX/CastleShield.wav`, `CastleStone.wav`, `CastleWin.wav`: generated algorithmic cues, wired into confirmed collision events. No background music.

## Asset and scene contract

All meshes use the planned code-authored MeshBuilder backend because walls are destructible, shields/projectile move, and the board geometry is parametric. No AI-generated GLB or placeholder substitution. Authored roots: Castle Clash, Castle Clash Board, Teal Castle, Amber Castle, Castle Clash Controls. Shared content is beneath ColocatedWorld / EnableOnReady. SyncKit examples are disabled; START_MENU is retained; camera uses World tracking.

The board is 42 × 62 cm including its rim, with about 8 cm towers. Teal and amber castles are at opposite ends. The local control panel sits outside the near edge and faces its seated player. Manual height and rotation controls provide table alignment without a surface-detection dependency.

Presentation is intentionally geometric for first-playable evaluation: damage shortens wall segments before removal, and team identity is shown through labeled controls and colored battlements. The design document's decorative flags, elaborate cracks, and crest art are not yet part of this first playable.
