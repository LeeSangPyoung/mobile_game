# War Face Icons v6 QA Rework

Date: 2026-06-03

## Goal

Re-audit all 200 war face icons against the Huang Gai-style from-scratch `cute50` face icon target.

The accepted target means:

- Must be a newly drawn/generated `cute50` face icon, not a crop fallback.
- Face-only square icon, matching `huang_gai` as the practical correct example.
- Compact cute50 battle commander face.
- Face and facial hair read first at 128x128.
- Headgear/hair silhouette preserved, but not allowed to dominate the face.
- Strict face icon means head, face, hair, facial hair, headgear, and visible neck only.
- No chest, no shoulders, no armor/collar area, no body/torso hint.
- No hands, weapons, shoulder armor, body-heavy crop, or background.
- Final assets stay transparent PNG at 256x256.
- Any `crop` label or deterministic recrop is an invalid placeholder until redrawn from scratch.

## Huang Gai Redraw Audit Override

User correction on 2026-06-03: Huang Gai is the correct target. Previous crop-based QA was too permissive.

Current gallery status after applying this stricter rule:

- Accepted `cute50` from-scratch/generated icons: 20.
- Redraw-required placeholders: 180.
- All remaining `crop` entries in `war_face_icons_v6_halfbody_style_gallery.html` were downgraded to `redraw 필요` and no longer count as complete.
- Built-in image generation must be attempted one icon at a time only.
- Do not mark an icon complete unless it is a newly drawn strict face-and-neck icon with transparent final PNG.
- The user clarified on 2026-06-04 that war-mode icons should be recognizable from the face and neck area alone. Include neck, but chest, shoulder, collar, and armor mass are not acceptable.
- Additional from-scratch Guan Yu redraw attempts after this audit initially failed: one chocolate-cake recipe image and one water-cycle diagram were returned. These were not saved or accepted.
- Guan Yu was later accepted after a one-at-a-time retry with Huang Gai and Guan Yu references visible, then magenta-key background removal to alpha.
- Guo Jia was later accepted after a one-at-a-time retry with Huang Gai and Guo Jia references visible, then magenta-key background removal to alpha.
- Xiahou Dun was later accepted after a one-at-a-time face-and-neck redraw with Huang Gai and Xiahou Dun references visible, corrected to include neck but exclude shoulders/chest/armor, then magenta-key background removal to alpha.

## Current Full-Audit Sheets

Generated on 2026-06-03:

```text
tmp/war_face_icon_qa_sheets/war_face_icon_qa_sheet_01.png
tmp/war_face_icon_qa_sheets/war_face_icon_qa_sheet_02.png
tmp/war_face_icon_qa_sheets/war_face_icon_qa_sheet_03.png
tmp/war_face_icon_qa_sheets/war_face_icon_qa_sheet_04.png
tmp/war_face_icon_qa_sheets/war_face_icon_qa_sheet_05.png
tmp/war_face_icon_qa_sheets/war_face_icon_qa_sheet_06.png
tmp/war_face_icon_qa_sheets/war_face_icon_qa_sheet_07.png
tmp/war_face_icon_qa_sheets/war_face_icon_qa_sheet_08.png
```

Regenerated after the first QA reworks on 2026-06-03 with visible `No. ID / Korean name` labels.
All 200 current final icons were also checked for existence, 256x256 dimensions, and alpha channel.

## Backup

Before this rework pass, the completed 200-icon folder was copied to:

```text
assets/generals/face_icons/war_v6_halfbody_style_transparent_backup_20260603/
```

## Initial Visual Audit Notes

The largest mismatch is not alpha/dimension quality; it is set consistency.

- Early generated icons such as `cao_cao`, `cao_xing`, `dian_wei`, `dong_zhuo`, and `gan_ning` define the desired face-first cute50 look.
- Several early fallback icons are visibly more like cropped portraits than face icons.
- Previous notes that treated later crop fallback icons as acceptable are obsolete after the Huang Gai correction.
- Rework must now start with the first `redraw 필요` entry in roster order and produce a newly drawn/generated face-only icon, one request at a time.

## Rework Queue

The queue tables below preserve the earlier crop-tightening pass. A `done` status here only means the old crop/recrop QA action was performed; it does not mean the icon is accepted under the current Huang Gai redraw rule.

High-priority candidates from the first full pass:

| Priority | ID | Name | Issue | Status |
| --- | --- | --- | --- | --- |
| 1 | `guan_yu` | 관우 | Regenerated from scratch against the Huang Gai target; no hands, weapon, or background. | accepted |
| 2 | `guo_jia` | 곽가 | Regenerated from scratch against the Huang Gai target; no hands, fan, weapon, or background. | accepted |
| 3 | `wen_chou` | 문추 | Body/shoulder-heavy crop; face reads smaller than baseline. | done |
| 4 | `xiahou_dun` | 하후돈 | Regenerated from scratch under strict face-only rule; no chest, shoulders, armor, hands, weapon, or background. | accepted |
| 5 | `xu_chu` | 허저 | Body-heavy crop; face can be more compact and icon-like. | reviewed-pass |
| 6 | `xu_huang` | 서황 | Face is small/low in frame; armor dominates. | done |
| 7 | `zhou_yu` | 주유 | Elegant portrait balance; face can be larger for war icon readability. | done |
| 8 | `zhuge_liang` | 제갈량 | Tall crown/robe balance is more portrait than compact icon. | done |
| 9 | `zhang_he` | 장합 | Face acceptable but could be tighter and more baseline-like. | done |
| 10 | `chen_dao` | 진도 | Face sits low/cropped awkwardly in the cell; needs review. | done |

Continue adding/revising queue entries as each contact sheet is rechecked.

## Second-Pass Visual Queue

Candidates from the regenerated 200-icon sheets. Work through these one at a time, comparing against `cao_cao` / `cao_xing`.

| Priority | ID | Name | Issue | Status |
| --- | --- | --- | --- | --- |
| 11 | `zhang_liao` | 장료 | Face reads small; tall topknot/ribbon and armor dominate. | done |
| 12 | `zhao_yun` | 조운 | Face reads small; white plume and shoulder armor dominate. | done |
| 13 | `yu_jin` | 우금 | Face/eyes are strong but body and dragon shoulder remain heavy. | done |
| 14 | `li_dian` | 이전 | Open-mouth face is good, but armor fills too much of the square. | done |
| 15 | `cao_ren` | 조인 | Helmet/armor silhouette is heavy; face can be brought forward. | done |
| 16 | `cao_pi` | 조비 | Elegant portrait balance; face can be larger and less body-heavy. | done |
| 17 | `cao_zhi` | 조식 | Face is calm and small compared with baseline. | done |
| 18 | `zhong_yao` | 종요 | Elder face is low/small; robe and crown dominate. | done |
| 19 | `guo_huai` | 곽회 | Helmet/shoulder mass competes with face. | done |
| 20 | `zhang_yun` | 장윤 | Weapon/hand/armor compete with face; needs no-hand face crop. | done |
| 21 | `xu_sheng` | 서성 | Face small under armor/collar mass. | done |
| 22 | `ding_feng` | 정봉 | Headband/armor heavy; face can be larger. | done |
| 23 | `ling_tong` | 능통 | Youthful face small; red ribbons and armor dominate. | done |
| 24 | `huang_quan` | 황권 | Hand-at-chin violates no-hands rule; needs face-only crop. | done |
| 25 | `meng_da` | 맹달 | Face sits small under crown/armor; needs tighter read. | done |
| 26 | `zhang_song` | 장송 | Face is too low/small in the crop. | done |
| 27 | `huo_jun` | 곽준 | Body-heavy crop; face can be larger. | done |
| 28 | `hou_xuan` | 후선 | Face reads very small in a rugged body-heavy crop. | done |
| 29 | `hu_che_er` | 호거아 | Body/weapon mass dominates the icon. | done |
| 30 | `zhang_jiao` | 장각 | Hair/crown/body mass dominate; face can be tighter. | done |

## Third-Pass Visual Queue

Candidates from the latest regenerated sheets after priorities 1-30 were reworked. Continue one at a time.

| Priority | ID | Name | Issue | Status |
| --- | --- | --- | --- | --- |
| 31 | `xu_huang` | 서황 | Latest sheet shows the icon reads too small/empty after prior trim; needs larger face-first recrop. | done |
| 32 | `yan_liang` | 안량 | Red plume and armor dominate; face can be larger. | done |
| 33 | `yuan_shao` | 원소 | Crown/shoulder mass makes the face read smaller than baseline. | done |
| 34 | `yue_jin` | 악진 | Open-mouth face is good, but helmet/armor fill too much of the square. | done |
| 35 | `cao_zhang` | 조창 | Hair/armor and yellow beard mass dominate; face can be tighter. | done |
| 36 | `cao_rui` | 조예 | Tall crown and robe/armor dominate; face is low/small. | done |
| 37 | `cao_shuang` | 조상 | Fur/shoulder armor competes strongly with face. | done |
| 38 | `cao_zhen` | 조진 | Large beard/armor crop remains body-heavy. | done |
| 39 | `xiahou_yuan` | 하후연 | Blue scarf/shoulder armor dominate; face can be larger. | done |
| 40 | `cheng_yu` | 정욱 | Tall official crown and robe make the face read small. | done |

## Fourth-Pass Visual Queue

Candidates from the same full-sheet audit pass after priorities 31-40. Continue one at a time and keep transparent face-first assets only.

| Priority | ID | Name | Issue | Status |
| --- | --- | --- | --- | --- |
| 41 | `man_chong` | 만총 | Face is readable, but robe/shoulder mass makes the icon feel body-heavy. | done |
| 42 | `deng_ai` | 등애 | Scarf/fur/armor mass competes with the face at small size. | done |
| 43 | `zhong_hui` | 종회 | Armor and shoulder silhouette fill too much of the square. | done |
| 44 | `wang_ping` | 왕평 | Shoulder armor and lower body hints dominate the face-first read. | done |
| 45 | `wen_pin` | 문빙 | Tall body/crown/armor composition makes the face read smaller than baseline. | done |
| 46 | `zang_ba` | 장패 | Teeth and face read well, but shoulder/body crop is still too broad. | done |
| 47 | `li_tong` | 이통 | Helmet and shoulder armor dominate; face can be tighter. | done |
| 48 | `han_hao` | 한호 | Body-heavy crop; face needs stronger priority. | done |
| 49 | `lu_qian` | 여건 | Face sits small under hair/armor mass. | done |
| 50 | `mao_jie` | 모개 | Tall portrait/body crop; face should be enlarged. | done |

## Per-Icon Rework Log

| No. | ID | Name | Action | Result |
| --- | --- | --- | --- | --- |
| 006 | `guan_yu` | 관우 | Replaced previous portrait-like crop with `tmp/war_face_icons_v6_qa_rework/guan_yu_qa_crop_360_y405_x330.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Better face-first read: eyes, brows, cap, and beard dominate; right shoulder armor is reduced to a secondary hint. Alpha 256x256 validated. |
| 007 | `guo_jia` | 곽가 | Replaced previous full-crown crop with `tmp/war_face_icons_v6_qa_rework/guo_jia_qa_crop_360_y300_x360.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face reads larger and faster; crown is intentionally partial but blue jewel/crown identity remains. Alpha 256x256 validated. |
| 020 | `wen_chou` | 문추 | Replaced previous shoulder-heavy crop with `tmp/war_face_icons_v6_qa_rework/wen_chou_qa_crop_340_y295_x330.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Shouting face now fills the icon more strongly; red armor remains only as a supporting edge. Alpha 256x256 validated. |
| 021 | `xiahou_dun` | 하후돈 | Replaced previous weapon/shoulder-heavy crop with `tmp/war_face_icons_v6_qa_rework/xiahou_dun_qa_crop_330_y300_x325.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Eyepatch and stern face now read first; blade and armor are still present but less dominant. Alpha 256x256 validated. |
| 022 | `xu_chu` | 허저 | Tested tighter candidates `xu_chu_qa_crop_370_y280_x370.png` and `xu_chu_qa_crop_330_y315_x390.png`. | Kept existing final because candidate crops damage the topknot/round-face silhouette and do not improve set consistency enough. |
| 023 | `xu_huang` | 서황 | Replaced previous armor-heavy crop with `tmp/war_face_icons_v6_qa_rework/xu_huang_qa_facecut_340_y260_x350.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, brows, beard, and blue crown jewel read faster; lower and side armor were alpha-trimmed so only a compact armor hint remains. Alpha 256x256 validated. |
| 029 | `zhou_yu` | 주유 | Replaced previous portrait-balanced crop with `tmp/war_face_icons_v6_qa_rework/zhou_yu_qa_facecut_340_y240_x375.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face is larger and faster to read while red plume, gold crown, and youthful strategist expression remain; lower/right armor was alpha-trimmed to reduce visual competition. Alpha 256x256 validated. |
| 030 | `zhuge_liang` | 제갈량 | Replaced previous tall portrait crop with `tmp/war_face_icons_v6_qa_rework/zhuge_liang_qa_fantrim_380_y200_x410.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, brows, beard, and green crown jewel read larger; fan/body presence is reduced while the tall strategist crown remains recognizable. Alpha 256x256 validated. |
| 031 | `zhang_he` | 장합 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/zhang_he_qa_busttrim_from_current_226_y6_x10.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face is larger without losing the blue forehead jewel, high topknot, and ribbon; lower armor is slightly reduced compared with the old icon. Alpha 256x256 validated. |
| 121 | `chen_dao` | 진도 | Replaced previous off-center crop with `tmp/war_face_icons_v6_qa_rework/chen_dao_qa_busttrim_360_y210_x380.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face is centered and much larger; dark crown, green jewel, green ribbon, stern brows, and green scarf remain while armor is kept secondary. Alpha 256x256 validated. |
| 027 | `zhang_liao` | 장료 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/zhang_liao_qa_busttrim_from_current_228_y6_x8.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, brows, moustache, and beard read larger while the black topknot, blue ribbon, headband jewel, and blue armor hint remain. Alpha 256x256 validated. |
| 028 | `zhao_yun` | 조운 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/zhao_yun_qa_busttrim_from_current_218_y2_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Clean youthful face and blue forehead jewel read larger while the white plume, black topknot, and silver-blue armor hint remain. Alpha 256x256 validated. |
| 032 | `yu_jin` | 우금 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/yu_jin_qa_from_current_218_y2_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, stern brows, moustache, beard, and blue crown jewel read larger while black-blue-gold armor remains as a smaller hint. Alpha 256x256 validated. |
| 034 | `li_dian` | 이전 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/li_dian_qa_from_current_218_y2_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, stern brows, moustache, pointed beard, and large blue forehead jewel read larger while the armor is reduced to a side hint. Alpha 256x256 validated. |
| 035 | `cao_ren` | 조인 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/cao_ren_qa_from_current_218_y2_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Helmeted face, heavy brows, full beard, blue plume, and central blue jewel read larger while shield/armor mass is reduced. Alpha 256x256 validated. |
| 037 | `cao_pi` | 조비 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/cao_pi_qa_from_current_218_y2_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Cold youthful face, thick brows, tall crown, and blue jewel read larger while noble robe/armor becomes a supporting hint. Alpha 256x256 validated. |
| 038 | `cao_zhi` | 조식 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/cao_zhi_qa_from_current_218_y2_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Blue-eyed youthful face, softer noble expression, tall crown, and blue jewel read larger while the fan/robe remain as edge hints. Alpha 256x256 validated. |
| 052 | `zhong_yao` | 종요 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/zhong_yao_qa_from_current_218_y2_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Elder face, heavy gray brows, long silver moustache/beard, and blue crown jewel read larger while robe/armor becomes secondary. Alpha 256x256 validated. |
| 055 | `guo_huai` | 곽회 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/guo_huai_qa_from_current_218_y2_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Helmeted face, stacked blue jewels, stern brows, moustache, beard, and blue scarf read larger while shoulder armor is reduced. Alpha 256x256 validated. |
| 067 | `zhang_yun` | 장윤 | Replaced previous hand/weapon crop with `tmp/war_face_icons_v6_qa_rework/zhang_yun_qa_from_current_220_y0_x36.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Weapon and hand are removed from the frame; face, teeth, beard, topknot, and blue headband now read first. Alpha 256x256 validated. |
| 068 | `xu_sheng` | 서성 | Replaced previous icon with a tighter recrop from the existing transparent generated icon: `tmp/war_face_icons_v6_qa_rework/xu_sheng_qa_from_current_218_y10_x12.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Stern youthful face, teal-red crown, green jewel, and red ribbon read larger while teal-gold armor/shield remain as hints. Alpha 256x256 validated. |
| 069 | `ding_feng` | 정봉 | Replaced previous spear-edge crop with `tmp/war_face_icons_v6_qa_rework/ding_feng_qa_from_current_218_y2_x30.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Spear edge is removed; face, beard, high ponytail, blue jeweled headband, and scarf now read first. Alpha 256x256 validated. |
| 074 | `ling_tong` | 능통 | Replaced previous ribbon/armor-heavy crop with `tmp/war_face_icons_v6_qa_rework/ling_tong_qa_from_current_208_y14_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Youthful grin, thick brows, red headband, ponytail, and battle expression read larger while armor/ribbons are reduced to secondary edge hints. Alpha 256x256 validated. |
| 120 | `huang_quan` | 황권 | Replaced previous hand-at-chin crop with `tmp/war_face_icons_v6_qa_rework/huang_quan_qa_from_current_208_y4_x24.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Hand is removed from the icon frame; crown, worried brows, side-looking eyes, moustache, and beard now read first, with only minimal armor/hair edge hints. Alpha 256x256 validated. |
| 123 | `meng_da` | 맹달 | Replaced previous crown/armor-heavy crop with `tmp/war_face_icons_v6_qa_rework/meng_da_qa_from_current_212_y4_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, confident eyes, brows, moustache, and beard read larger; horned crown and green ribbon remain, with shoulder armor reduced to edge hints. Alpha 256x256 validated. |
| 124 | `zhang_song` | 장송 | Replaced previous low/small face crop with `tmp/war_face_icons_v6_qa_rework/zhang_song_qa_from_current_200_y28_x24.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, sly eyes, brows, moustache, and pointed beard read larger; tall crown identity remains while robe/armor is mostly cropped away. Alpha 256x256 validated. |
| 126 | `huo_jun` | 곽준 | Replaced previous body/shoulder-heavy crop with `tmp/war_face_icons_v6_qa_rework/huo_jun_qa_from_current_204_y12_x18.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Stern eyes, brows, headband jewel, topknot, moustache, and beard read larger; right shoulder armor is reduced to a secondary edge hint. Alpha 256x256 validated. |
| 162 | `hou_xuan` | 후선 | Replaced previous body-heavy crop with the left-centered face recrop `tmp/war_face_icons_v6_qa_rework/hou_xuan_qa_leftface_184_y20_x4.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Worried eyes, sweat, clenched teeth, headband jewel, and topknot read larger; right shoulder armor/fur are pushed to secondary edge hints. Alpha 256x256 validated. |
| 175 | `hu_che_er` | 호거아 | Replaced previous body/weapon-heavy crop with the alpha-masked face-only recrop `tmp/war_face_icons_v6_qa_rework/hu_che_er_qa_faceonly_rightbase_c.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, thick brows, eyes, nose, moustache, and beard dominate; most club/shoulder mass is removed or pushed outside the visible alpha silhouette. Alpha 256x256 validated. |
| 191 | `zhang_jiao` | 장각 | Replaced previous hair/crown/body-heavy crop with `tmp/war_face_icons_v6_qa_rework/zhang_jiao_qa_from_current_196_y26_x20.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Shouting face, fierce eyes, open mouth, yellow headband, cap, and black beard read larger while robe/armor mass is reduced. Alpha 256x256 validated. |
| 023 | `xu_huang` | 서황 | Revisited prior QA result and replaced it with `tmp/war_face_icons_v6_qa_rework/xu_huang_qa_revisit_from_current_196_y12_x26.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, brows, moustache, and beard now read larger in the sheet; partial blue crown jewel remains while armor stays secondary. Alpha 256x256 validated. |
| 024 | `yan_liang` | 안량 | Replaced previous plume/armor-heavy crop with `tmp/war_face_icons_v6_qa_rework/yan_liang_qa_from_current_206_y6_x26.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Stern face, heavy brows, full beard, blue jewel, and red plume identity read larger while red-gold armor becomes a side hint. Alpha 256x256 validated. |
| 025 | `yuan_shao` | 원소 | Replaced previous crown/shoulder-heavy crop with `tmp/war_face_icons_v6_qa_rework/yuan_shao_qa_facefirst_180_y44_x58.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, brows, eyes, moustache, and beard read first; tall crown is intentionally partial and shoulder armor is reduced to an edge hint. Alpha 256x256 validated. |
| 033 | `yue_jin` | 악진 | Replaced previous helmet/armor-heavy crop with `tmp/war_face_icons_v6_qa_rework/yue_jin_qa_from_current_226_y0_x14.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Open shouting mouth and fierce eyes are preserved while shoulder/armor mass is slightly reduced. Alpha 256x256 validated. |
| 039 | `cao_zhang` | 조창 | Replaced previous hair/armor-heavy crop with `tmp/war_face_icons_v6_qa_rework/cao_zhang_qa_from_current_196_y16_x24.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Blond shouting face, brows, mouth, moustache, and beard read larger while right armor is reduced to an edge hint. Alpha 256x256 validated. |
| 041 | `cao_rui` | 조예 | Replaced previous tall crown/robe-heavy crop with `tmp/war_face_icons_v6_qa_rework/cao_rui_qa_from_current_206_y24_x26.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, brows, moustache, and long beard read larger; imperial crown is intentionally partial and robe/shoulder armor is reduced. Alpha 256x256 validated. |
| 042 | `cao_shuang` | 조상 | Replaced previous fur/shoulder-heavy crop with left-centered recrop `tmp/war_face_icons_v6_qa_rework/cao_shuang_qa_leftface_196_y12_x0.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Grinning face, brows, moustache, and beard read larger while fur collar and right shoulder armor are reduced to edge hints. Alpha 256x256 validated. |
| 043 | `cao_zhen` | 조진 | Replaced previous beard/armor-heavy crop with `tmp/war_face_icons_v6_qa_rework/cao_zhen_qa_from_current_196_y16_x24.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Stern face, heavy brows, white side hair, moustache, and long beard read larger while armor becomes secondary. Alpha 256x256 validated. |
| 045 | `xiahou_yuan` | 하후연 | Replaced previous scarf/quiver/shoulder-heavy crop with left-centered recrop `tmp/war_face_icons_v6_qa_rework/xiahou_yuan_qa_leftface_206_y6_x0.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Arrow quiver is removed; eyepatch, stern eye, brows, beard, headband jewel, and blue scarf now read first. Alpha 256x256 validated. |
| 047 | `cheng_yu` | 정욱 | Replaced previous tall-crown/robe-heavy crop with `tmp/war_face_icons_v6_qa_rework/cheng_yu_qa_from_current_196_y32_x32.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Elder strategist face, white brows, intense eyes, moustache, and long beard read larger; tall blue-gold crown remains as a partial identity cue while robe/shoulder mass is reduced. Alpha 256x256 validated. |
| 051 | `man_chong` | 만총 | Replaced previous robe/shoulder-heavy crop with `tmp/war_face_icons_v6_qa_rework/man_chong_qa_from_current_194_y18_x24.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Face, thick brows, black moustache, and full beard now read larger; blue jewel crown and dragon shoulder armor remain as compact identity hints. Alpha 256x256 validated. |
| 053 | `deng_ai` | 등애 | Replaced previous scarf/fur/armor-heavy crop with `tmp/war_face_icons_v6_qa_rework/deng_ai_qa_from_current_194_y18_x42.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Stern eyes, brows, moustache, beard, blue jeweled headband, and blue scarf read larger; fur collar and armor are reduced to side/bottom hints. Alpha 256x256 validated. |
| 054 | `zhong_hui` | 종회 | Replaced previous armor/dragon-shoulder-heavy crop with alpha-trimmed face crop `tmp/war_face_icons_v6_qa_rework/zhong_hui_qa_facefirst_186_y20_x0_righttrim.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Youthful grin, sharp eyes, heavy brows, and black hair now dominate; right dragon shoulder armor is trimmed to a secondary edge hint. Alpha 256x256 validated. |
| 056 | `wang_ping` | 왕평 | Replaced previous shoulder-heavy crop with `tmp/war_face_icons_v6_qa_rework/wang_ping_qa_from_current_194_y18_x0.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Resolute face, thick brows, moustache, full beard, green crown, and teal jewel read larger while green-gold shoulder armor becomes a compact edge hint. Alpha 256x256 validated. |
| 057 | `wen_pin` | 문빙 | Replaced previous heavy-armor crop with `tmp/war_face_icons_v6_qa_rework/wen_pin_qa_from_current_186_y10_x34.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Grim face, thick brows, headband jewel, moustache, and full beard read larger; topknot and heavy shoulder armor remain as small identity hints. Alpha 256x256 validated. |
| 058 | `zang_ba` | 장패 | Replaced previous broad shoulder/body crop with `tmp/war_face_icons_v6_qa_rework/zang_ba_qa_from_current_186_y28_x16.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Toothy grin, fierce eyes, green headband, scar marks, moustache, and beard dominate; scarf and spiked armor are reduced to edge hints. Alpha 256x256 validated. |
| 059 | `li_tong` | 이통 | Replaced previous helmet/shoulder-heavy crop with `tmp/war_face_icons_v6_qa_rework/li_tong_qa_from_current_186_y28_x16.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Stern youthful face, eyes, brows, short goatee, blue jeweled helmet, and plume read larger; shoulder armor is reduced to edge hints. Alpha 256x256 validated. |
| 060 | `han_hao` | 한호 | Replaced previous body-heavy crop with `tmp/war_face_icons_v6_qa_rework/han_hao_qa_from_current_194_y20_x24.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Stern face, thick brows, moustache, full beard, black topknot, and blue jewel crown hint read larger; heavy armor is reduced to lower/side hints. Alpha 256x256 validated. |
| 061 | `lu_qian` | 여건 | Replaced previous hair/armor-heavy crop with `tmp/war_face_icons_v6_qa_rework/lu_qian_qa_from_current_186_y28_x16.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Firm face, heavy brows, moustache, full beard, blue jewel crown, plume hint, and blue scarf read larger; armor is reduced to side hints. Alpha 256x256 validated. |
| 062 | `mao_jie` | 모개 | Replaced previous tall robe/scroll-edge crop with `tmp/war_face_icons_v6_qa_rework/mao_jie_qa_from_current_202_y6_x46.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Stern civil-officer face, thick brows, moustache, pointed beard, tall black-gold crown, and blue jewel read larger; left scroll/hand edge is removed and robe mass is reduced. Alpha 256x256 validated. |
| 006 | `guan_yu` | 관우 | Revisited after the user identified `huang_gai` as the correct target; replaced the prior still-shoulder-heavy crop with `tmp/war_face_icons_v6_qa_rework/guan_yu_huang_gai_baseline_180_y34_x10_righttrim.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Now treated as a Huang Gai-style face-only icon: green cap, red jewel, stern eyes, brows, and long beard dominate; shoulder armor is reduced to tiny edge hints. Alpha 256x256 validated. |
| 007 | `guo_jia` | 곽가 | Revisited after the user identified `huang_gai` as the correct target; replaced the prior bust-like crop with `tmp/war_face_icons_v6_qa_rework/guo_jia_huanggai_faceonly_final.png`; overwrote final/source in `war_v6_halfbody_style_transparent`. | Fullbody source was recropped to preserve the tall blue crown while making the face read first; robe/shoulder mass is trimmed to small edge hints. Alpha 256x256 validated. |
| 006 | `guan_yu` | 관우 | User correction: crop-based rework is rejected. Built-in image generation was retried one at a time for a from-scratch Guan Yu redraw, but returned unrelated cell/infographic images three times; later attempts returned a chocolate-cake recipe and a water-cycle diagram. No bad generation was saved. | Must be regenerated from scratch in the Huang Gai target style before it can be counted complete. Current visible asset is an invalid placeholder only. |
| 007 | `guo_jia` | 곽가 | User correction: crop-based rework is rejected. No crop fallback should be accepted as final for this slot. | Must be regenerated from scratch in the Huang Gai target style before it can be counted complete. Current visible asset is an invalid placeholder only. |
| 006 | `guan_yu` | 관우 | Accepted new one-at-a-time generation from `tmp/war_face_icons_v6_chromakey/guan_yu_war_face_icon_v6_cute50_chromakey.png`; magenta key removed to `assets/generals/face_icons/war_v6_halfbody_style_transparent/guan_yu_war_face_icon_v6_cute50_source.png`; final resized to `assets/generals/face_icons/war_v6_halfbody_style_transparent/guan_yu_war_face_icon_v6_cute50.png`. | Newly drawn Huang Gai-style face-only icon. Green cap, red jewel, thick brows, stern eyes, moustache, and long beard dominate. No hands, weapon, body, or background. Alpha 256x256 validated. |
| 007 | `guo_jia` | 곽가 | Accepted new one-at-a-time generation from `tmp/war_face_icons_v6_chromakey/guo_jia_war_face_icon_v6_cute50_chromakey.png`; magenta key removed to `assets/generals/face_icons/war_v6_halfbody_style_transparent/guo_jia_war_face_icon_v6_cute50_source.png`; final resized to `assets/generals/face_icons/war_v6_halfbody_style_transparent/guo_jia_war_face_icon_v6_cute50.png`. | Newly drawn Huang Gai-style face-only icon. Tall navy crown, blue jewel, hair, brows, clever eyes, slight smile, and goatee dominate. No hands, fan, weapon, body, or background. Alpha 256x256 validated. |
| 021 | `xiahou_dun` | 하후돈 | Accepted latest one-at-a-time generation from `tmp/war_face_icons_v6_chromakey/xiahou_dun_war_face_icon_v6_cute50_chromakey.png`; magenta key removed to `assets/generals/face_icons/war_v6_halfbody_style_transparent/xiahou_dun_war_face_icon_v6_cute50_source.png`; final resized to `assets/generals/face_icons/war_v6_halfbody_style_transparent/xiahou_dun_war_face_icon_v6_cute50.png`. | Newly drawn face-and-neck combat-expression icon. Gold eyepatch, one visible eye, heavy brows, clenched teeth, moustache, full beard, wild hair, blue-gold hair ornament, and visible neck dominate. No chest, shoulders, armor, collar, hands, weapon, body, or background. Alpha 256x256 validated. |
