# Fullbody Game Cutout Rework Guide

Last updated: 2026-05-30

This document is the shared standard for rebuilding the 200 new general fullbody assets as game-ready cutouts. Future agents should read this before generating, editing, reviewing, or wiring any new fullbody images.

## Current Baseline

- Reference review page: `new_generals_halfbody_recovered_200_v6_progress.html`
- Roster source: `assets/generals/roster_200.js`
- Current fullbody reference set:
  - `assets/generals/new_characters/front_gaze_200_v10_scale_audit/{id}_front_gaze_v1.png`
  - Count: 200 images
  - Size: 1024 x 1536
- Current halfbody reference set:
  - `assets/generals/new_characters/upper_body_200_redraw_v6_above_navel/{id}_halfbody_redraw_v6.png`
  - Count: 200 images

The current fullbody images are reference images, not final game assets. They include fire, sparks, glowing dust, floor light, and background atmosphere that make them unsuitable for direct in-game compositing.

## Goal

Recreate all 200 generals as clean fullbody game cutouts.

The work is not "remove the flames from the old image." The correct direction is "redraw the same character as a clean fullbody game asset." Preserve the character identity, silhouette, costume language, palette, and readable pose from the reference, but rebuild the image without background effects.

## Proposed Output

- New output folder:
  - `assets/generals/new_characters/fullbody_game_cutout_v1/`
- Final filename pattern:
  - `{id}_fullbody_game_cutout_v1.png`
- Optional chroma-key source folder:
  - `assets/generals/new_characters/fullbody_game_cutout_v1_chromakey/`
- Optional review page:
  - `new_generals_fullbody_game_cutout_v1_review.html`

Do not overwrite the current `front_gaze_200_v10_scale_audit` images. They remain the identity reference set.

## Asset Spec

- Canvas: 1024 x 1536.
- Final format: PNG with alpha transparency.
- Subject: one fullbody general, head to feet visible.
- Framing: centered, full body contained inside canvas, generous edge padding.
- Bottom alignment: feet near the lower safe area, but not cropped.
- Pose: front-facing or slight three-quarter front, suitable for strategy/RPG character UI.
- Style: match the existing stylized game-general look exactly: adult compact heroic proportions, mature expressive face, broad sturdy torso, short weighty stance, chunky hands and boots, rounded armor masses, polished painted/3D hybrid finish, strong costume detail, clean readable silhouette. Do not drift into realistic fantasy illustration, and do not turn the character into a baby/child/chibi mascot.
- Proportions: keep the current adult compact heroic proportions. Head and face should match the reference scale, body should stay broad and weighty, legs should not become long, hands and boots should remain chunky. Avoid both extremes: realistic tall-body proportions and babyish oversized-head proportions.
- Lighting: character-only studio lighting. No environmental glow or floor bounce that implies a background.

## Style Fidelity Rules

The reference fullbody image is the style target, not just an identity target.

The new cutout must preserve:

- adult compact game character body ratio
- mature head and face scale matching the reference
- short, thick legs and large boots
- rounded hands with simplified expressive fingers
- broad chunky armor plates rather than thin realistic armor
- slightly toy-like 3D/painterly finish
- same level of facial stylization as the reference
- original pose attitude and silhouette weight

Reject the image if it becomes:

- tall realistic fantasy concept art
- narrow-waisted realistic armor illustration
- overly sharp or grim western fantasy rendering
- too anatomically realistic
- too detailed in a way that loses the original game roster style
- a different body scale from the reference character set
- babyish, cute, toddler-like, or mascot-like proportions
- face too young for the character's age and role

## Framing Correction Rules

Some current fullbody references have weapons, sleeves, capes, tassels, or robe hems running past the usable card area. For game cutouts, the final asset must look complete when composited.

When a prop or costume part would be clipped:

- Prefer fitting the entire item inside the canvas with extra padding.
- Slightly reduce the weapon length, sleeve spread, cape width, or gesture reach if needed.
- If reducing size would damage the character identity, redraw the full item end-to-end inside the frame.
- Never leave a weapon tip, sleeve edge, tassel, cape corner, hand, boot, or robe hem visibly cut off.
- Do not crop the subject to preserve the old reference framing. The clean game asset takes priority.

## Weapon Handling Rules

Weapons must be complete and held in a physically readable combat grip. Do not solve framing by flipping a weapon into an unnatural grip.

For weapon-bearing generals:

- Preserve the reference's weapon type and intended pose.
- Hands must grip the handle/hilt/shaft naturally, not the blade or an impossible reversed handle.
- Sword, saber, spear, bow, and polearm orientation must look usable in battle.
- A blade may be shortened or angled inward for framing, but it must not look upside down, backwards, or reversed.
- For sabers and swords, the hilt should read clearly at the hand and the blade should project from the hilt in a natural direction.
- Reject the image if a weapon is complete but the grip direction looks implausible.

## Palette Direction

Avoid making half the roster read as the same dull dark-gold outfit. Gold trim is allowed, but it should not become the dominant identity color for every character.

For each character:

- Preserve the reference faction/role color language where it is clear.
- Use richer secondary colors to separate characters at game size: deep red, imperial purple, jade green, indigo, steel blue, white cloth, black lacquer, warm leather, silver, bronze, or faction-specific accents.
- Keep gold as trim, ornament, or rank detail unless the character identity specifically requires heavy gold.
- Increase cloth/armor color contrast enough that silhouettes and faction families remain readable in a roster grid.
- Avoid a muddy "black plus dull gold everywhere" result unless the reference strongly demands it.

## Strictly Forbidden

Do not include:

- fire
- sparks
- embers
- glowing dust
- smoke
- magical aura
- rim-light halo
- background texture
- battlefield background
- floor plane
- floor glow
- cast shadow
- contact shadow
- vignette
- decorative particles
- text
- watermark

If any of these appear, the asset should be marked for regeneration rather than patched unless the issue is extremely minor and fully outside the character silhouette.

## Identity Preservation

For each character, preserve:

- face shape and expression attitude
- age impression
- hairstyle, beard, eyebrows, and headwear
- armor/robe category
- main colors and accent metals
- signature props already visible in the reference
- broad pose language and silhouette

Allowed changes:

- clean up noisy background-contaminated edges
- slightly simplify tiny costume detail if it improves small-size readability
- adjust arms, sleeves, hem, or weapon angle to fit cleanly inside the cutout
- improve feet visibility and bottom framing

Not allowed:

- changing gender, age band, faction color language, or role type
- adding new weapons or props that were not implied by the reference
- making the character look like a different named general
- converting the style to photoreal, flat anime, comic line art, or western fantasy

## Generation Workflow

1. Before generating each character, read this guide and `FULLBODY_GAME_CUTOUT_REWORK_LOG.md`.
2. For re-audit or repair work, prefer a local mask from the original fullbody reference first. Do not regenerate/redraw a character merely to make it cleaner or prettier; use generation/redraw only when the original source has an actual clipped weapon, hand, cape edge, robe hem, or other silhouette part that cannot be accepted as-is.
3. Start with a small sample batch. Do not begin with all 200.
4. Recommended first sample IDs:
   - `kan_ze` - civil official with tall hat and paper prop
   - `zhang_fei` - bold heavy warrior
   - `zhuge_liang` - iconic strategist
   - `huang_zhong` - older martial figure
   - `xiahou_ba` - armor/detail balance check
5. Generate each as a clean fullbody asset on a flat chroma-key background first.
6. Remove chroma key locally into transparent PNG.
7. Validate the transparent result.
8. Build a review HTML comparing:
   - original fullbody reference
   - new transparent cutout on dark background
   - new transparent cutout on light background
   - new transparent cutout on a representative game UI background
9. Only after the sample passes, continue to the remaining roster.

## Chroma-Key Standard

Use a flat solid background only for extraction.

Default key color:

- `#00ff00`

Prompt requirements:

- background must be one uniform color
- no shadows, gradients, texture, reflections, or floor plane
- no cast shadow or contact shadow
- subject must not use the key color
- subject edges should be crisp and fully separated from the background

After generation, remove the key with the imagegen helper:

```bash
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
  --input <source> \
  --out <final.png> \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 220 \
  --despill
```

If a visible green fringe remains, retry once with:

```bash
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
  --input <source> \
  --out <final.png> \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 220 \
  --despill \
  --edge-contract 1
```

## Prompt Template

Use this as the base prompt for each character. Fill in character-specific notes after inspecting the reference image.

```text
Use case: stylized-concept
Asset type: game-ready fullbody character cutout for a strategy/RPG roster
Primary request: Recreate the referenced Three Kingdoms general as a clean fullbody game asset.
Reference role: preserve the character identity, face, costume type, color palette, pose attitude, and major props from the reference image.
Canvas: 1024x1536 vertical.
Composition: full body visible from head to feet, centered, feet fully visible, generous padding, no cropping.
Framing correction: if weapons, sleeves, cape corners, tassels, robe hems, hands, or boots would cross the canvas edge, resize or redraw them so the entire item remains visible inside the frame.
Weapon handling: keep every weapon in a natural combat grip. Do not flip, reverse, or invert weapons just to fit the frame; hands must grip the handle/hilt/shaft correctly and the blade must project naturally from the hilt.
Style: polished stylized game art, painted/3D hybrid, strong readable silhouette, detailed armor and cloth, expressive face, consistent with the existing general portrait set.
Style fidelity: match the provided reference image's adult compact game-general proportions exactly: mature adult face, broad sturdy torso, short weighty stance, chunky hands and boots, rounded armor masses, expressive simplified face. Do not make the character tall, realistic, narrow, western fantasy, babyish, cute, or childlike.
Palette: preserve the reference colors but avoid muddy repeated dark-gold dominance; use distinct cloth and armor color accents where appropriate.
Background: perfectly flat solid #00ff00 chroma-key background only.
Lighting: character-only studio lighting, no environmental glow.
Avoid: fire, sparks, embers, particles, smoke, aura, rim-light halo, background texture, floor plane, floor glow, cast shadow, contact shadow, vignette, text, watermark.
Output requirement: the character must be cleanly separable from the background as a transparent PNG cutout.
```

## Review Criteria

An asset passes only if all are true:

- The character is immediately recognizable against the original reference.
- The full body is present and not cropped.
- The silhouette works on both dark and light backgrounds.
- There are no flames, sparks, particles, smoke, aura, or background remnants.
- Transparent corners are actually transparent.
- Edges have no obvious green fringe.
- Feet, sleeves, weapons, and robe edges do not disappear after extraction.
- The image looks usable in a game UI without further manual cleanup.

## Progress Tracking

When production starts, track per-character status in a generated review page or a small manifest. Suggested statuses:

- `sample`
- `pass`
- `regen_needed`
- `edge_cleanup_needed`
- `identity_mismatch`
- `missing`

Keep the original reference path and final cutout path visible in review pages so another agent can audit the work quickly.
