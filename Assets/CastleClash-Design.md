# Castle Clash

## Pitch

A tabletop SPECS castle defense game played solo against one CPU opponent or face-to-face against another player through SyncKit. Each side guards a miniature fortress with a movable magical shield, redirecting a ricocheting fireball toward its opponent. Walls chip away until a shot can reach the exposed crown. Matches take approximately three minutes.

Inspired by the defensive paddle play of Atari Warlords, with original castle designs, audio, and branding.

## The view across the table

A roughly 60 × 40 cm enchanted tournament board rests on the actual table. Players sit at opposing short ends. Each castle occupies its player's end, facing the other castle across an open courtyard. A luminous U-shaped shield rail wraps around the courtyard-facing three sides of each fortress. Solid arena side rails keep shots in play; the protected rear edge prevents attacks from bypassing the defense entirely.

The visual style is a handcrafted miniature: chunky pale stone, copper trim, tiny fluttering banners, and an ember-lit ball. One kingdom uses teal and a diamond crest; the other uses amber and a sun crest. Crests and silhouettes distinguish sides without relying solely on color. Castles stand about 8 cm tall; effects remain low enough to preserve the view of the opponent.

Top view, approximate arrangement:

```text
                   PLAYER B
          ┌────────────────────────┐
          │       Crown B          │
          │    ▪ ▪ ▪ ▪ ▪ ▪ ▪       │  destructible walls
          │   ╭─────▰──────╮       │  shield on U-shaped rail
          │                        │
          │          ● ↘           │  fireball
          │                        │
          │   ╰──▰─────────╯       │  shield on U-shaped rail
          │    ▪ ▪ ▪ ▪ ▪ ▪ ▪       │
          │       Crown A          │
          └────────────────────────┘
                   PLAYER A
```

## Core rules

- Each castle starts with 12 destructible wall segments arranged across its front and two flanks, with a crown behind them. Each segment survives two hits and clearly changes from intact to cracked to broken.
- One fireball launches from midfield after a three-second countdown. It travels horizontally at a fixed height, visibly above the tabletop, and reflects from shields, intact walls, and arena rails.
- Players move a single shield along their own U-shaped rail. The shield's contact position steers the rebound: center hits return predictably; edge hits create sharper angles. Clamp angles to avoid near-horizontal rallies and corner traps.
- A wall hit removes one hit point and rebounds the ball. Destroyed segments leave permanent openings. An exposed crown takes one hit to end the round.
- Consecutive shield returns gradually increase ball speed, with a firm cap. A wall hit lowers speed slightly so the next exchange remains recoverable.
- First to two round wins takes the match. Rebuild both castles between rounds. After 75 seconds, announce sudden death and progressively remove corresponding wall segments on both castles until a crown is vulnerable. Keep a single ball in the first version.

## Hand interaction

Each player has a small glowing control handle beside their near board edge. Pinch the handle and move laterally to slide the shield along its entire rail. Map a comfortable, approximately 20 cm hand movement to the full rail; crossing center moves through the front span, and the outer portions wrap onto the flanks. The handle makes this mapping visible during a short practice serve.

The shield remains at its last position when the player releases, allowing rest without holding a sustained pinch. Re-grabbing uses a relative movement offset so the shield does not jump. A faint tether connects the hand and handle while held. Do not require reaching across the battlefield or blocking the opponent's view.

For the first playable, support only movement and rebound steering. A later optional catch-and-release mechanic can give each player one timed fireball catch per round, added only if rallies already feel fair and readable.

## Play modes

Both modes are required for the first playable and use the same arena, collision simulation, shield limits, damage, scoring, and win conditions.

- **Play CPU:** One human versus one CPU-controlled castle. Start locally without joining a multiplayer session or waiting for a second device. Place the board, claim the near castle, practice the controls, and select Ready; the CPU takes the opposite castle automatically. Tracking loss pauses the local match.
- **Play a Friend:** Two human players seated across the table, using SyncKit for colocated alignment and synchronized gameplay. Follow the shared-table flow below.

The CPU predicts where the incoming ball will reach its defense rail, accounting for arena rebounds, then moves its shield toward that point. Give it a reaction delay, bounded aiming error, and the same movement-speed limit as human shields. It must move continuously rather than teleport, and cannot alter the ball or repair walls. Start with one balanced difficulty; expose reaction delay and aiming error as tuning parameters. Run CPU decisions only on the local simulation authority and route them through the same shield-input interface used by human players.

Choose the mode before starting a match. Rematch retains the current mode; returning to the menu permits changing it. A disconnected human opponent does not silently become a CPU.

## Shared-table flow (Play a Friend)

1. One player hosts and the other joins the same colocated session.
2. The host positions a translucent board on the table, rotates it so the castles face the seated players, and confirms placement. Offer manual placement adjustment if surface placement is unreliable.
3. Both players verify a shared alignment marker at the board center. Each selects the castle nearest their seat; a castle can have only one owner.
4. A local practice prompt teaches pinch, slide, and release. Both players select Ready.
5. Start the countdown, play the round, show the winning crest over the arena, and rebuild for the next round. At match end, offer Rematch and Leave.

If tracking or connectivity is lost, freeze the shared match and show a short recovery message. Resume with a countdown after both players are ready. Never let an invisible or untracked ball damage a castle.

## Feedback and atmosphere

- The ball has a bright solid core, short trail, and tabletop shadow. Its contact point remains legible even during impacts.
- Shield impacts flash briefly and produce a directional metallic chime. Rising rally speed raises the chime pitch modestly.
- Wall damage produces a stone crack, visible fractures, and a short burst of cosmetic rubble that disappears. Rubble never affects ball motion or clutters the board.
- Crown destruction triggers a small upward burst of sparks and a collapsing banner, keeping the opponent's face visible.
- Show round score as two crest sockets on each player's board edge. Place Ready, recovery prompts, and Rematch near the player's castle. Keep the central play area free of menus.
- Avoid continuous music in the first version so conversation and impact cues remain clear.

## Proposed implementation

This is an implementation design, not a claim that the project currently contains these systems. Verify package and API support when building.

- Use a single board-local coordinate system with a local table anchor for Play CPU and a shared colocated anchor for Play a Friend. Transform each player's interaction into that system before applying movement.
- Use Spectacles Interaction Kit for handle interaction and Spectacles Sync Kit for the shared session and replicated match state, subject to installed-version verification.
- In Play CPU, the local device owns ball simulation, CPU input, wall damage, scoring, and state transitions without a SyncKit session dependency. In Play a Friend, give one peer authority over the same simulation. Clients transmit shield input; only the authority commits collisions and outcomes.
- Use a fixed-step 2D collision simulation in the board's horizontal plane, rendered with 3D assets. Sweep ball motion against collision shapes to prevent fast shots passing through thin walls. Resolve corners deterministically and handle remaining motion after a collision.
- Move the local shield immediately for responsive control; constrain motion to a plausible maximum speed and reconcile to authoritative input. Interpolate remote shields and ball snapshots. Cosmetic hit effects follow confirmed collision events and carry event IDs to avoid duplicate playback.
- Replicate ball position and velocity, shield positions, wall health, crown state, round score, match phase, and a simulation timestamp. Validate authority behavior under realistic connection latency before choosing snapshot frequency or adding prediction.
- Separate BoardPlacement, MatchSession, MatchSimulation, ShieldInput, CpuController, CastlePresentation, and MatchHUD responsibilities. ShieldInput accepts local human, remote human, or CPU commands through a common interface. Keep simulation independent of session transport and cosmetic animation outside gameplay authority.
- Pause on authority loss for the initial prototype; do not silently restart a divergent simulation. Host migration is outside the first playable scope.

## First playable scope and verification

Build in stages: one readable local arena and fireball; shield movement and destructible walls; a complete solo match against one CPU; then two-device placement and SyncKit multiplayer using the same simulation. Both modes belong in the first playable. Use simple original geometric assets until interaction and alignment are proven.

Acceptance checks:

- Play CPU starts and completes a first-to-two match on one device without creating or joining a multiplayer session.
- The CPU obeys shield movement limits, reacts with a visible delay, and can lose; it never teleports or changes castle health outside normal gameplay rules.
- Both modes use identical collision, damage, sudden-death, and victory rules. Rematch resets all round state, including CPU decision state in solo play.
- Two seated players see the same board center, wall openings, ball impacts, scores, and round result.
- A player can defend all three castle faces without reaching across the table or holding a pinch continuously.
- The ball cannot tunnel through intact walls, enter the protected rear of a castle, or remain trapped indefinitely in a corner.
- Destroyed walls leave real gameplay openings; rubble remains cosmetic.
- Crown hits, sudden death, round resets, and first-to-two victory happen exactly once on both devices.
- Releasing and re-grabbing the handle does not cause shield jumps.
- Tracking loss or a disconnected peer pauses damage and allows an understandable recovery path.
- The scene stays readable from both seated viewpoints, including fast rallies and damage effects.

Defer additional CPU difficulty levels, four-player play, power-ups, free-flight ball physics, castle customization, persistent progression, and catch-and-release until both core modes are enjoyable.

## Tuning defaults

Starting values for the first playable. They set a balanced baseline and have not yet been validated through human playtesting. All are exposed as Inspector parameters on the Castle Clash component.

| Parameter | Default | Notes |
|---|---|---|
| Ball launch speed | 28 cm/s | Rises with consecutive shield returns |
| Ball speed cap | 62 cm/s | Firm ceiling; wall hits lower speed slightly |
| Shield speed limit | 40 cm/s | Shared by human and CPU shields |
| Shield width | 7 cm | Center-versus-edge steering zones scale with width |
| Countdown | 3 s | Used for serves and recovery resumes |
| Sudden death | 75 s | One matching wall pair falls every 2 s, starting at the center |
| Rounds to win | 2 | First to two |
| CPU reaction interval | 350 ms ± 70 ms | Periodic observation, not per-frame tracking |
| CPU aim error | up to 3.4 cm | Stable within each decision |
| CPU hesitation chance | 12% | Adds one decision interval |
| CPU prediction horizon | 1.2 s | Includes arena rebounds |

## Open questions

- Do the default ball speed and CPU tuning parameters feel fair to first-time players, and should a second CPU difficulty be the first deferred feature?
- Is snapshot interpolation sufficient under realistic network latency, or does the remote shield/ball presentation need client-side prediction?
- Does the manual height/rotation placement align reliably on two devices, or should surface detection be added?
- Does the slider panel feel as direct as the designed in-world handle? Replace it only if on-device testing shows the panel is limiting.
- When should the placeholder art advance to crests, cracks, and banners — before or after the multiplayer latency pass?

Resolve these through two-device physical testing before expanding scope.

## Addendum: As built (first playable)

This section records what the current first playable implements. Where it differs from the design above, the build is the current reference; the design remains the target for later polish. Implementation notes and the file map are in `CastleClash-Build.md`.

**Modes and menu.** The opening menu offers **Solo**, which starts an offline match against the CPU with no SyncKit session, and **Multiplayer**, which enters the SyncKit colocated flow. In Multiplayer each player claims Teal or Amber, and a castle can have only one owner. The control panel's **Play CPU** button starts a fresh local match at any time. **Leave** exits the friend session and freezes the match. The Lens must be reopened to start a new friend session, because the installed SyncKit controller does not expose a public ready-state reset.

**Board and placement.** The board measures 42 × 62 cm including the rim, with towers about 8 cm tall. Teal and Amber castles sit at opposite ends. The host aligns the shared board with **Place here**, **Lower**, **Raise**, and **Turn**. There is no surface-detection dependency. Only the host can move the shared board. Shared content lives under ColocatedWorld / EnableOnReady, and the camera uses World tracking.

**Controls.** Each player controls their shield with a UIKit slider on a control panel just outside their near board edge, facing their seat. This replaces the designed in-world glowing handle and tether. The slider's full travel maps to the three-sided rail: front span in the middle, flanks at the ends. The shield follows the knob continuously **while it is being dragged**, not only on release, and stays where it was left when the pinch ends. Shield motion is capped at the shared 40 cm/s limit. In Multiplayer, the local shield is shown immediately, and shield input is sent to the authority at up to about 20 updates per second, with the final position always delivered. A compact panel with score, status, the slider, and Pause is shown during play.

**Rules.** Rules are implemented as designed:
- 12 two-hit walls per castle.
- Exposed crowns.
- First to two round wins.
- Shield-rebound speed-up with a cap.
- Sudden death after 75 s, removing matching wall pairs every 2 s from the center outward.
- Castles rebuild between rounds.

Rematch rebuilds both castles and clears the score. Pause and recovery keep the interrupted rally and resume after a countdown.

**CPU.** The CPU observes the ball periodically instead of every frame, with bounded aim error, occasional hesitation, and a 1.2 s prediction horizon that includes rebounds. It uses the same speed limit and input path as human shields. All values are Inspector-tunable (see Tuning defaults).

**Simulation and networking.** A fixed-step, board-local 2D simulation uses swept collisions. In Solo, the local device is the authority. In Multiplayer, the SyncEntity owner is the authority: clients send authenticated intents, and the authority replicates snapshots. The remote ball is interpolated. Impact effects and audio follow confirmed collision events. A lost player or missing heartbeat freezes damage until both players select Ready. Authority loss does not migrate gameplay.

**Presentation and audio.** All geometry is procedural (MeshBuilder), with no AI-generated or imported models. Walls shorten as they take damage and are then removed. Teams are identified by color and labelled controls. Rubble is cosmetic. Three generated cues (shield, stone, win) play on confirmed events, and there is no background music. The crests, crack detailing, banners, crown sparks, and crest score sockets from the design are not yet built.

**Verification.** Seven deterministic simulation checks, including an 18,000-step run, pass in the Lens runtime (`Scripts/CastleClashSimulationChecks.ts`). Five LEAF playability scenarios (`Tests/CastleClashLeaf/`) pass in Preview: Solo start without a session, a complete first-to-two CPU match, shield movement during an active slider drag, Rematch/Play CPU reset, and single-device Multiplayer entry and seat claiming. Still to validate on physical devices: two-device table alignment, behavior under real network latency, tracking interruption, and difficulty balance with human players.

