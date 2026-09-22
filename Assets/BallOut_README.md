# BALL OUT

Empty the colorful pool as quickly as possible. The timer begins with your first interaction; clear every ball over the outer rim to finish.

- Push and scoop with either open hand. Palm and fingertip colliders physically displace the balls.
- Pinch near a ball to pick it up. Move your hand over the rim, then release to throw. The ball stays in the physics simulation while held.
- Select RESTART on the scoreboard to refill the pool and reset the timer.
- Tracking loss releases a held ball and disables that hand's collision proxies.

## Editing

Move `Pool • move to place` in the scene to position the play area. `BALL OUT • Scoreboard` is independently positioned. The default interior is 90 × 70 cm, 18 cm deep, with 48 balls of 5 cm radius. The pool sits 55 cm below the initial eye height and 100 cm forward.

`BallPitMain` exposes ball count, radius, mass, dimensions, gravity, maximum speed, audio volumes and collider debugging. `PlasticContact` controls bounce/friction. Geometry is generated in centimeters using MeshBuilder; spheres share one mesh and six glossy materials. The physics world runs at 120 Hz.

`BallPitHands.ts` handles tracked direct pinch and physical hands. Direct near-hand pickup is the tested interaction; indirect ball targeting is not required. The UIKit HUD remains compatible with standard SIK targeting.

Audio assets were synthesized locally with the ls-clad audio toolkit. `BuildTools/generate_audio.cjs` retains the reproducible generation recipe (requires the installed toolkit at the path in that file).
