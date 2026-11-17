# Interface acceptance walk

Copy this sheet into the task's external work/report directory and extend it.
Use an isolated fictional family. Record engine commit/version, family root,
local URL, browser, viewport widths, date, reviewer and evidence paths. Start
the actual reader/desk, verify HTTP and render both tree and a chapter. Stop
owned servers at the end. This is a browser walk, not an automatic UI test.
Screenshots support the observations; they do not replace executing actions.

Execute each row at 1440 and 390 CSS pixels. Put actual observations (and any
failure or unavailable surface) in the final column. Preserve failed rows when
adding a corrected follow-up. Add task-specific actions below these base rows.

| Width | Action | Expected | Observed / evidence |
|---|---|---|---|
| each | Open tree, person, families, stories, investigation, questions, kinship; include map/photos if present | Same lower navigation, private notice, version and remark entry; no overlaps; all links reachable | |
| each | Tree → Investigation → Tree; then browser back/forward | Navigation stays in the same place; current link follows the screen | |
| each | Open a full person card, click “Write to us” once | One common remark sheet opens immediately; page and card scroll do not change | |
| each | Hover remark entry, then move away | No sheet opens or stays behind | |
| each | Open empty remark, click outside | Sheet closes | |
| each | Open empty remark, press Escape | Sheet closes | |
| each | Open empty remark, click entry again | Sheet closes | |
| each | Type text, click outside, reopen; repeat with Escape and entry | Sheet collapses; unsent indicator appears; exact text and context survive | |
| each | With draft collapsed, navigate to investigation, reopen; reload and reopen | Draft and original attachment survive navigation/reload | |
| each | Click “Name”, question's “Know something?”, and any event correction once | Same sheet opens once, with the right person/question/event | |
| each | Read investigation's work volume | Open, dropped, confirmed awaiting tree and included-in-tree counts sit with work volume; no isolated top counter | |
| each | Open a chapter; locate and click exit | Rendered chapter has an always-visible exit; exit returns to stories | |
| each | Inspect tree nodes and uncertain link; select long-name and placeholder nodes | No kinship or weight label on nodes; uncertain link is dotted; whole name/owner placeholder visible | |
| each | Navigate every narrow-screen link; scroll page and card | Footer stays fixed; links and content remain usable without overlap | |

Record defects with the action and its consequence. Acceptance covers only
executed rows. Do not attest independent reading of family facts during an
interface walk. If tool access fails, record the exact limitation and leave
the affected rows explicitly unaccepted.
