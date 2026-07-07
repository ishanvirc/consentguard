# Video assets — rough cut kit

All 13 AI assets (6 clips via Kling/Cinema Studio, 7 narration segments via
seed_audio "Sterling") were generated on Higgsfield; URLs + job IDs are in
`../writeup/HIGGSFIELD_PROMPTS.md`. Media files are gitignored — only the
scripts live in the repo.

## Build the rough cut (one command)

```powershell
winget install Gyan.FFmpeg        # once, if you don't have ffmpeg; reopen terminal
cd consentguard\video_assets
.\make_rough_cut.ps1              # downloads assets + assembles rough_cut.mp4 (~3:21)
```

## What you get

`rough_cut.mp4` — the full video skeleton, narration synced in script order:

| Time | Content | Status |
|---|---|---|
| 0:00 | CLIP-1 hook (Cinema Studio) | ✅ done |
| 0:13 | CLIP-2 + CLIP-3 b-roll, then **STAT CARDS slate** | overlay graphics needed |
| 0:54 | CLIP-4 b-roll, then **B-ROLL slate** | optional footage |
| 1:19 | **ARCHITECTURE slate**, then CLIP-5 gate shot | screen-capture the diagram |
| 1:57 | **PLAYGROUND DEMO slate** | ⚠️ your screen recording — the judged part |
| 2:41 | **BUILD FOOTAGE slate** | ⚠️ pytest, Antigravity, eval, MCP, Cloud Run |
| 3:12 | CLIP-6 close + end card slate | add repo URL |

## Finishing checklist

1. Record the demo + build screen captures (PLAN.md Day 3).
2. Replace the two ⚠️ slates (any editor: Clipchamp is preinstalled on Windows 11, or DaVinci/CapCut).
3. Add text overlays where slates indicate (penalties, consent windows, verdict table callouts).
4. End card: repo URL, hold 3+ seconds.
5. Confirm ≤ 5:00, export 1080p, upload to YouTube (public), attach to the Kaggle writeup.

To re-voice: re-run generation with a different `voice_id` (see `list_voices` in the
Higgsfield connector) or record yourself — judges respond well to founder voice.
