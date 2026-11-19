# BP_Trap_Trampoline - build guide

**Status (19 Nov 2026)** — Design and editor build guide for Unreal Engine 4.27.2. The art is present in `feature/Wing` at `5b29147`. This guide records the current build settings. Verify the cases in §7 in PIE before submitting.

The trampoline is a player-only, reusable bounce pad. Use a child of `BP_TrapBase` so it follows the trap asset structure. Build and test it on a flat floor.

## 1. Behaviour

1. At rest, show the idle spring.
2. When the player's capsule enters `BounceBox` while walking on the ground or descending onto the spring, launch the player upward and restart the jump flipbook.
3. Preserve the player's horizontal velocity. Set the vertical launch velocity so an ordinary fall and a faster descent produce the same initial bounce speed.
4. When the jump flipbook finishes, return to idle. The player can bounce again on the next descent, even if the previous animation is still playing.
5. Rising through the sensor, bullets, and enemies leave the pad idle.

The pad is safe to touch. The level floor provides solid collision underneath it. For this build, place the pad on level ground and keep its actor rotation at zero.

## 2. Art

| Purpose | Asset |
|---|---|
| Idle source sprite | `SPR_Trampoline_Idle` |
| Idle flipbook | `FLB_Trampoline_Idle`, create from the idle sprite |
| Bounce flipbook | `FLB_Trampoline_Jump`, already imported |

In the Content Browser, right-click `SPR_Trampoline_Idle` and choose **Create Flipbook**. Save the result as `Content/DontTrustTheLevels/Traps/Animations/FLB_Trampoline_Idle`. Use one keyframe. The sprite asset can stay in its current folder.

[Paper2DArt.md](Paper2DArt.md) documents the trap import convention of top-left pivots and `0.16` pixels per Unreal unit. Verify both flipbooks in the editor. Align the spring base with the floor and preview the first bounce frame against the idle frame. Use the child Blueprint's visual transform to position the spring.

## 3. Components

Create `Content/DontTrustTheLevels/Traps/Blueprints/BP_Trap_Trampoline` by right-clicking `BP_TrapBase` and choosing **Create Child Blueprint Class**. Set the following in the child Blueprint.

| Component | Settings |
|---|---|
| `TrapRoot` | Inherited. Keep its relative transform at the default. |
| `Sprite` | Inherited Paper Flipbook component. Source Flipbook = `FLB_Trampoline_Idle`. Collision Presets = `NoCollision`. Disable Generate Overlap Events, Auto Play, and Looping where shown. |
| `Trigger` | Inherited lethal box. Set Collision Presets = `NoCollision` and disable Generate Overlap Events in the child defaults before placing the actor. |
| `BounceBox` | New Box Collision under `TrapRoot`. Set Collision Enabled = `Query Only`, Object Type = `WorldDynamic`, Pawn = `Overlap`, other channels = `Ignore`, Generate Overlap Events = on. |

Size `BounceBox` to the landing face of the art. Use a Z half extent of `12 uu` as a starting value. Put the bottom of the box at the top surface of the spring, so its center Z is the surface Z plus the box half height. Center X on the pad and size X to the usable top of the spring. Start with Y half extent `50 uu` and verify that it covers the player's depth lane. Select the box in the Blueprint Viewport to verify it. Keep the scale at 1 during the first test.

## 4. Variables

| Name | Type | Initial value | Instance Editable |
|---|---|---:|---|
| `BounceSpeed` | Float | `1600.0` | Yes |
| `LandingTolerance` | Float | `6.0` | No |

`BounceSpeed` sets the launch speed in uu/s. The class default is `1600.0`. A placed actor can override it in Details.

## 5. Event Graph

### 5.1 BounceBox overlap

Select `BounceBox` in Components, then click **+** next to **On Component Begin Overlap** in Details. Add the first two checks in sequence. Connect each Boolean result to its own **Branch**. Continue from `True` and leave `False` empty.

| Check | Connections |
|---|---|
| The overlapping actor is the player | `Equal (Object)` takes `Other Actor` and `Get Player Character (0)`. |
| The overlap is from the main player capsule | From `Get Player Character.Return Value` drag out `Get Capsule Component`. Compare it with the event's `Other Comp` using `Equal (Object)`. |

From the capsule check's `True`, add a **Branch** for ground movement. Drag from `Get Player Character.Return Value` to get **Character Movement**. From that component, call **Is Moving on Ground** and connect its Boolean result to the Branch.

- `True` goes straight to **Launch Character**. This lets a player walking into the sensor from the side bounce.
- `False` goes to the descending check. From the player character, get **Get Velocity**, split `Return Value`, and connect `Return Value Z < -1.0` to a **Branch**. Continue from `True` to the feet-height check. Leave `False` empty.

For the feet-height check:

1. From the player capsule, get `Get World Location` and `Get Scaled Capsule Half Height`. Split the location vector. Subtract the half height from location Z to get the player's feet Z.
2. Drag `BounceBox` into the graph twice as needed for `Get World Location` and `Get Scaled Box Extent`. Split both vectors. Subtract scaled extent Z from the box location Z to get the spring surface Z.
3. Subtract `LandingTolerance` from the spring surface Z. Connect `Feet Z >= Spring Surface Z - LandingTolerance` to a **Branch**. Its `True` goes to the same **Launch Character** as the ground-movement branch. Leave `False` empty.

### 5.2 Launch and play the bounce animation

1. Add **Launch Character**. Set `Target` to the blue `Get Player Character.Return Value`.
2. Right-click `Launch Velocity` and choose **Split Struct Pin**. Set X and Y to `0`, connect `Get Bounce Speed` to Z, leave **XYOverride** unchecked, and tick **ZOverride**.
3. Drag in the inherited `Sprite` and call **Set Flipbook** with `FLB_Trampoline_Jump`, then **Set Looping** with **New Looping** unchecked, then **Play From Start**. Connect each node with a white execution wire.

The main capsule check excludes overlaps from additional player components. Leaving the sensor and falling back in gives a new bounce without a timer or a gameplay cooldown.

### 5.3 Restore idle

Select the inherited `Sprite` and add **On Finished Playing** from its Events in Details. On that event, use **Set Flipbook** with `FLB_Trampoline_Idle`, then **Stop** on the same Sprite. The non-looping jump flipbook fires this event after the last frame. The next bounce uses **Play From Start** again.

## 6. Placement and source control

1. Place one pad on a solid, level floor in a personal test map. Keep the actor upright, put the spring at floor height, and check that the player has space overhead.
2. Start at `BounceSpeed = 1600.0`. In the level editor, select the placed pad and check its Details for a per-instance override before judging the bounce height.
3. Both new `.uasset` files are LFS-managed and lockable. After the new assets exist locally, use the following commands from the repository folder if editor checkout did not already acquire the locks. Run `git lfs locks` to check ownership. The Markdown guide uses ordinary Git.

```cmd
git lfs lock "Content/DontTrustTheLevels/Traps/Blueprints/BP_Trap_Trampoline.uasset"
git lfs lock "Content/DontTrustTheLevels/Traps/Animations/FLB_Trampoline_Idle.uasset"
```

Build in the child Blueprint and use a personal test map. The common player-only rule is documented in [TrapTriggers.md](TrapTriggers.md).

## 7. PIE checklist

| Test | Expected |
|---|---|
| Drop straight onto the pad | The player launches upward once and the jump animation plays. |
| Fall onto it while moving sideways | The current horizontal motion carries through the bounce. |
| Walk into the side on level ground | The player bounces when their capsule enters the sensor. |
| Jump up through the sensor | The pad stays idle during ascent. |
| Land on it on the way down after jumping up through it | The pad bounces once after the capsule has cleared the sensor and returned. |
| Fall back onto the same pad | It bounces again. The animation restarts and later returns to idle. |
| Fire a bullet through it and move an enemy past it | Neither triggers the pad. |
| Stand beside the pad and repeat after a level restart | The pad starts idle and the player survives contact with it. |
| Set a different `BounceSpeed` on another instance | Only that instance's launch speed changes. |

## 8. Troubleshooting

| Symptom | First check |
|---|---|
| The pad kills the player | Inspect the child defaults for inherited `Trigger`. Check `NoCollision` and Generate Overlap Events. |
| There is no bounce on a vertical drop | Check capsule overlap, sensor placement, the descending branch, and feet height. |
| Walking into the side does not bounce | Verify that the capsule enters `BounceBox` while grounded and `Is Moving on Ground.True` reaches `Launch Character`. |
| The bounce is too low | Check for a placed-actor speed override, confirm `ZOverride` is enabled, and test with clear space overhead. |
| The spring snaps position when switching flipbooks | Compare the idle and jump frame pivots and visible baselines in the sprite editors. |
| The spring stays in the jump pose | Ensure the jump flipbook has looping disabled and `On Finished Playing` is bound to the inherited `Sprite`. |
