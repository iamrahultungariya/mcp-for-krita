# Design Specification: 10-Second Anime Running Animation & Krita Multi-Plane Parallax

**Document ID**: `SPEC-RUN-2026-11-19`  
**Status**: DRAFT (Pending User Approval)  
**Date**: 2026-11-19  
**Canvas Target**: `C:\Users\Rahul\Downloads\running.kra` (Live Krita `doc_4`, $3840 \times 2160$, 4K UHD)  
**Output Target**: 10-Second Master Video (`output/anime_running_10s.mp4`, 24 FPS, 240 Frames)

---

## 1. Intent & Purpose
Produce a high-energy, 10-second anime running animation video featuring the established **Anime Creator** character from the studio cel library, reimagined in athletic running attire on a bright sunny morning stadium track. The animation combines an authentic 12-frame studio hand-drawn run cycle with multi-plane parallax background motion, dynamic physical sweat simulation, flying hair physics, and camera impact bob.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Character Continuity & Redesign**: Preserve the facial structure, eye style, and brunette hair tone of `anime_creator` while outfitting her in an athletic tank top, running shorts, sweatband, and sports running shoes.
- **Krita Canvas Integration**: Populate the active 4K document `running.kra` (`doc_4`) with structured multi-plane layers:
  - `BG_Sky_Sun`
  - `BG_Stadium_Bleachers`
  - `Track_Ground_Lanes`
  - `Char_Run_Cycle`
  - `FX_Sweat_Emitters`
  - `FX_Speedlines`
- **Fluid Athletic Motion**: Deliver an 8–12 frame looping run-cycle animated on 2s (12 drawings/sec in a 24 fps timeline) with authentic squash-and-stretch, contact, recoil, passing, and airborne phases.
- **Secondary Physical FX**:
  - Parabolic flying sweat droplets breaking off from forehead and neck with air resistance.
  - Bouncing ponytail/hair tufts with momentum delay.
  - Subtle camera bounce synchronized with foot-strikes.
- **Final Master Video**: Render a 10.0-second ($240\text{ frames}$ at $24\text{ fps}$) high-definition MP4 video (`output/anime_running_10s.mp4`).

### Non-Goals
- Modifying or overwriting the original character sheet document `anime_creator_canvas`.
- Complex multi-character racing or crowd cheering animations.
- Audio foley or voice track mixing (animation/video delivery focus).

### Anti-Goals
- **Robotic Puppet Cutout**: Stiff, linear limb rotation without organic squash, stretch, and perspective foreshortening.
- **Zero Krita Persistence**: Generating a standalone video without writing the editable layers back into the user's open `running.kra` canvas.
- **Static Background**: A character running in place without believable multi-depth parallax conveyor movement.

---

## 3. Technical Constraints
- **Duration**: Exactly $10.0\text{ seconds}$ ($240\text{ frames}$).
- **Frame Rate**: $24\text{ fps}$ broadcast standard.
- **Canvas Resolution**: $3840 \times 2160$ (4K UHD) in Krita; video deliverable formatted to $1920 \times 1080$ Full HD (or native 4K) for optimal playback performance.
- **Krita IPC Protocol**: Loopback authenticated TCP port `18812` communicating with active document `doc_4`.

---

## 4. Evaluated Approaches

| Approach | Description | Pros | Cons / Verdict |
| :--- | :--- | :--- | :--- |
| **Approach 1: Hybrid Studio Run-Cycle + Parallax Engine** *(Chosen)* | 12-frame animated character run cycle composited over continuous multi-plane parallax background with particle sweat simulation. | True anime aesthetic, fluid stride physics, both Krita `.kra` layers and MP4 video delivered. | **Selected by User**. Optimal balance of studio quality and editable structure. |
| **Approach 2: Pure Transform Cutout Puppet Rigging** | Rotating parented limb layers in Krita using keyframe transforms. | Low initial drawing count. | Rejected: Stride perspective and cloth folding look stiff and robotic. |
| **Approach 3: Standalone Synthetic Video Generation** | Direct neural/algorithmic video generation bypassing Krita canvas. | Quick video output. | Rejected: Violates requirement to work in user's live open `running.kra` file. |

---

## 5. Architectural & Visual Breakdown

### 5.1 Environment Multi-Plane Parallax (Stadium Track)
The background moves from right to left to create forward running momentum:
- **Plane 1 (Far Sky & Morning Sun)**: Very slow drift ($0.2\text{ px/frame}$) with warm lens flare and subtle cloud shift.
- **Plane 2 (Mid-ground Bleachers & Field Turf)**: Mid-speed parallax ($4.0\text{ px/frame}$) featuring stadium arches, green infield turf, and goalposts.
- **Plane 3 (Foreground Running Track)**: Fast textured red polyurethane running track with white lane markings ($18.0\text{ px/frame}$).

### 5.2 Character Stride Mechanics (12-Frame Run Cycle)
Each complete 2-step cycle spans $12\text{ frames}$ ($0.5\text{ seconds}$), meaning the character completes 20 full cycles in 10 seconds:
1. **Frame 1 (Right Foot Contact)**: Right heel plants, body begins downward compression.
2. **Frame 2 (Recoil / Deep Squash)**: Knee flexes, lowest center of gravity, hair compresses down.
3. **Frame 3 (Right Leg Push / High Passing)**: Left leg swings forward, torso drives upward.
4. **Frame 4 (Airborne Peak / Stretch 1)**: Both feet off ground, maximum vertical lift, hair floats up, sweat flies.
5. **Frame 5-6 (Descending Stride 1)**: Preparing left heel strike.
6. **Frame 7-12 (Left Foot Sequence)**: Mirrored stride dynamics for left foot cycle.

### 5.3 Secondary FX & Camera Dynamics
- **Sweat Particles**: Active particle system emitting 3–6 droplets per stride from forehead and neck, following velocity vectors $\vec{v} = (-v_x + \text{jitter}, v_y + g \cdot t)$ with alpha dissipation.
- **Camera Impact Bob**: Subtle $2\text{ px}$ vertical camera dip on every contact frame (frames 1 and 7) for palpable athletic impact.
- **Speed Lines**: Radial and horizontal motion streaks on outer screen margins reinforcing speed.

---

## 6. Implementation Deliverables
1. **Krita Canvas Setup**: Structured layer hierarchy injected into `doc_4` (`running.kra`) via Krita MCP IPC.
2. **Composite Frame Engine**: Rendering pipeline iterating through 240 frames with parallax, stride cycling, and particle dynamics.
3. **Master Video Export**: `output/anime_running_10s.mp4` encoded via H.264 / AAC at 24 fps.
4. **Validation**: Frame inspection, duration certification (exact $10.0\text{s}$), and Krita document sync verification.
