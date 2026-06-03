# Cao Cao War Face Icon v6 Notes

Date: 2026-05-30

Master tracking file:

`WAR_FACE_ICONS_V6_HALFBODY_STYLE.md`

Management gallery:

`war_face_icons_v6_halfbody_style_gallery.html`

Production note:

- The production direction was changed to transparent PNG after the early background experiments.
- Use the transparent master file for actual game/UI work:
  `assets/generals/face_icons/war_v6_halfbody_style_transparent/cao_cao_war_face_icon_v6_cute50.png`
- The older `assets/generals/face_icons/war_v6_halfbody_style/` files are background experiments and should not be treated as final game assets.

## Goal

Create a battle-mode representative face icon for Cao Cao.

User intent:

- Use the current `new_generals_halfbody_recovered_200_v6_progress.html` board as the style reference.
- Make a face-only icon, not full body or half body.
- The icon is for war mode.
- Resolution does not need to be high.
- Expression should be different from the calm base portrait: angry, grim, solemn, battle-ready.

Reference board:

`http://127.0.0.1:5174/new_generals_halfbody_recovered_200_v6_progress.html?fresh=20260530-dong-zhuo-v2`

## Reference Assets

Main Cao Cao references inspected before generation:

- `assets/generals/new_characters/fullbody_game_cutout_v1/cao_cao_fullbody_game_cutout_v3.png`
- `assets/generals/new_characters/upper_body_200_redraw_v6_above_navel/cao_cao_halfbody_redraw_v6.png`

Important Cao Cao identity traits:

- Black swept-back hair with sharp volume.
- Thick angular black eyebrows.
- Narrow stern brown eyes.
- Short mustache and pointed black beard.
- Gold-and-purple crown with central purple gem.
- Black-and-gold armor with purple accents.
- Stylized 3D game render, not flat anime.

## Output

Generated final icon:

`assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_grim.png`

Working source copy:

`assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_grim_source.png`

Cute +10% variant:

`assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_cute10.png`

Cute +10% source copy:

`assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_cute10_source.png`

Cute +30% variant, requested after the cute +10% version:

`assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_cute30.png`

Cute +30% source copy:

`assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_cute30_source.png`

Cute +50% variant, requested after the cute +30% version:

`assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_cute50.png`

Cute +50% source copy:

`assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_cute50_source.png`

The final icon was downscaled to 256x256 using:

```bash
sips -z 256 256 \
  assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_grim_source.png \
  --out assets/generals/face_icons/war_v6_halfbody_style/cao_cao_war_face_icon_v6_grim.png
```

Original built-in imagegen output path:

`/Users/leesp/.codex/generated_images/019e7950-f35f-7502-a9b8-484c6f0ea8fb/ig_0dd28a0de50dfa94016a1af7908ff88191ac3596d17cbc4573.png`

Cute +10% built-in imagegen output path:

`/Users/leesp/.codex/generated_images/019e7950-f35f-7502-a9b8-484c6f0ea8fb/ig_0dd28a0de50dfa94016a1af94c0f0881919b9dd550a4f4c246.png`

Cute +30% selected built-in imagegen output path:

`/Users/leesp/.codex/generated_images/019e7950-f35f-7502-a9b8-484c6f0ea8fb/ig_0dd28a0de50dfa94016a1afbe367b88191998b0c6bafe420d3.png`

Cute +50% selected built-in imagegen output path:

`/Users/leesp/.codex/generated_images/019e7950-f35f-7502-a9b8-484c6f0ea8fb/ig_0dd28a0de50dfa94016a1afd7f9cb48191ba7cc0aefe7641bf.png`

## Prompt Used

```text
Use case: stylized-concept
Asset type: small square battle-mode representative face icon for a Three Kingdoms mobile/strategy game
Primary request: Generate one face-only icon of Cao Cao based on the visible reference images in this conversation. Keep the same stylized 3D game portrait art direction, identity, costume language, and color palette.
Subject: Cao Cao as a commanding warlord. Face only, front-facing or very slight three-quarter angle. Black swept-back hair with sharp volume, thick angular black eyebrows, intense narrow brown eyes, short mustache and pointed black beard, gold-and-purple crown with a central purple gem. Hint of black-and-gold armor collar and purple trim at the bottom edge only.
Expression: angry, grim, battle-resolved expression; lowered brows, focused eyes, compressed mouth or restrained snarl. It should read as wartime command, not goofy rage.
Composition: square icon composition, tight crop. The face fills most of the frame, usable even at 128x128. Include crown top if possible, but prioritize the eyes, eyebrows, nose, mustache, and beard. No hands, no full body, no weapon, no large shoulder armor.
Style: polished stylized 3D render matching the reference images, toy-like but serious, sharp gold highlights, dark smoky warm background, high contrast, clean silhouette, readable at small size.
Avoid: text, watermark, UI frame, extra characters, realistic human photo style, anime flat cel shading, open screaming mouth, exaggerated cartoon comedy, different helmet design, different facial hair.
```

## Background Experiment Notes

Historical only. These notes describe the early background-bearing experiments. They are kept for comparison, but production should use the transparent PNG listed above and in `WAR_FACE_ICONS_V6_HALFBODY_STYLE.md`.

The generated icon reads more like a war-mode grim commander than the older `war_v1` Cao Cao, which had a more ambitious smile.

Strengths:

- Face-only crop works well at 256px and should still read at 128px.
- Cao Cao identity is clear through crown, hair, eyebrows, mustache, and beard.
- Expression is stern and battle-ready without becoming comical.
- Style is closer to the current v6 halfbody/fullbody set than the older anime-style icons.

Potential issues in the old background experiments:

- Background is dark smoky, not transparent.
- A small amount of armor collar remains at the bottom, but no hands, weapons, or body pose are present.
- If the final UI needs transparent face cutouts, generate on chroma key or remove the dark background in a separate pass.

Cute +10% variant notes:

- Intended to keep the war-mode seriousness while making Cao Cao slightly more approachable.
- Changes are subtle: slightly clearer eyes, softer cheeks, and less brutal facial tension.
- Use `cao_cao_war_face_icon_v6_cute10.png` if the original grim version feels too stern in the UI.

Cute +30% variant notes:

- Requested as "20% more cute" after the cute +10% version.
- Face shape is rounder, eyes are slightly larger/brighter, and the mouth reads more like a stern pout.
- Still keeps Cao Cao's crown, eyebrows, mustache, beard, black/gold/purple palette, and war-mode authority.
- Use `cao_cao_war_face_icon_v6_cute30.png` if the UI needs a friendlier, more collectible-feeling icon.

Cute +50% variant notes:

- Requested as another "20% more cute" after the cute +30% version.
- Eyes are larger and rounder, the face feels more compact, and the stern mouth reads closer to a cute determined pout.
- This is currently the friendliest variant while still preserving Cao Cao's crown, beard, heavy eyebrows, and war-mode authority.
- Use `cao_cao_war_face_icon_v6_cute50.png` if the UI should lean more collectible and approachable than stern.

## Suggested Next-Agent Workflow

For expanding this to more generals:

1. Use each general's current v6 halfbody as the identity/style reference.
2. Generate square face-only icons with expression variants suitable for war mode.
3. Keep naming consistent:

```text
assets/generals/face_icons/war_v6_halfbody_style/{id}_war_face_icon_v6_cute50.png
```

4. Keep source copies only if useful for later resizing:

```text
assets/generals/face_icons/war_v6_halfbody_style/{id}_war_face_icon_v6_cute50_source.png
```

5. Do not overwrite older folders unless explicitly requested:

- `assets/generals/face_icons/war_v1`
- `assets/generals/face_icons/war_v2_anime`
- `assets/generals/face_icons/war_v3_portrait`

6. If creating a review page, make a new gallery instead of modifying the older comparison pages. Suggested filename:

```text
war_face_icons_v6_halfbody_style_gallery.html
```

7. For the gallery source list, use `assets/generals/roster_200.js`.

## Batch Prompt Template

```text
Use case: stylized-concept
Asset type: small square battle-mode representative face icon for a Three Kingdoms mobile/strategy game
Primary request: Generate one face-only icon of {Korean name} / {id}, based on the current v6 halfbody/fullbody reference style. Preserve the character identity, costume language, faction colors, hair, facial hair, crown/helmet, and recognizable silhouette from the reference.
Expression: grim battle-ready expression, angry or solemn but not comedic. Lowered brows, focused eyes, compressed mouth or restrained snarl.
Composition: square icon, tight face crop, readable at 128x128. Prioritize eyes, eyebrows, nose, mouth, facial hair, and key headgear. No hands, no full body, no weapon, no large shoulder armor.
Style: polished stylized 3D game render matching the current v6 general portraits, high contrast, clean silhouette, dark warm battle background.
Avoid: text, watermark, UI frame, extra characters, photoreal human style, flat anime cel shading, open screaming mouth, changed identity.
```
