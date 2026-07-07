# ConsentGuard — rough-cut assembler (Windows PowerShell)
# Downloads the 13 Higgsfield assets (6 clips + 7 VO segments) and assembles
# rough_cut.mp4: AI clips + narration in script order, with labeled slates
# where YOUR screen recordings (demo, build, deploy) get dropped in.
#
# Usage:  cd consentguard\video_assets ; .\make_rough_cut.ps1
# Needs ffmpeg:  winget install Gyan.FFmpeg   (then reopen the terminal)
#
# Pipeline was validated end-to-end (normalize -> freeze -> slates -> per-segment
# VO mux -> concat) before this script was written.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "ffmpeg not found. Install with:  winget install Gyan.FFmpeg  then reopen this terminal." -ForegroundColor Red
    exit 1
}

# ---------- 1. Download assets (skipped if already present) ----------
# V2 "THE GATEKEEPER" assets — Cinema Studio 3.0 clips + Sienna VO (2026-07-02)
$base = "https://d8j0ntlcm91z4.cloudfront.net/user_3Fxsfj103hJh3EWWIe3FAXmh1k9"
$assets = @{
    "clip1.mp4" = "$base/hf_20260702_225247_c6279207-0448-4cd6-9de0-06dffd9f068b.mp4"  # B1 gauntlet slam (hook)
    "clip2.mp4" = "$base/hf_20260702_225251_aca576a0-0582-4a00-8a4a-63153d54a3f0.mp4"  # B2 drone foundry
    "clip3.mp4" = "$base/hf_20260702_225255_0ee9af7b-338d-47ab-9509-d4d4054340e9.mp4"  # B3 consent decay
    "clip4.mp4" = "$base/hf_20260702_225259_1c0779e6-b118-4448-80ad-021a005d15b2.mp4"  # B4 adjudication in palm
    "clip5.mp4" = "$base/hf_20260702_225943_92c12b5b-37c0-49bd-b93b-4c0d574f1217.mp4"  # B5 key-turn (money shot)
    "clip6.mp4" = "$base/hf_20260702_225307_9bd9d735-8c07-48ea-a100-bab11b737563.mp4"  # B6 dawn resolution
    "vo1.wav"   = "$base/hf_20260702_225320_7cdd2d3b-6881-4cd6-a612-adc69b5b18b1.wav"  # Sienna 14.1s
    "vo2.wav"   = "$base/hf_20260702_225323_3fb6d4d7-4b4b-492c-988d-2003d92101d6.wav"  # 29.4s
    "vo3.wav"   = "$base/hf_20260702_225326_fe79effd-04bb-4dd5-8366-8e442c65a97c.wav"  # 27.5s
    "vo4.wav"   = "$base/hf_20260702_225328_effe23cc-a876-4d8c-b29d-b4890586d3ff.wav"  # 33.2s
    "vo5.wav"   = "$base/hf_20260702_225332_f46699aa-fc1d-491f-b0c6-c65636ea43f8.wav"  # 45.5s
    "vo6.wav"   = "$base/hf_20260702_225335_976f06e1-990e-48b1-9977-ce10bb981b55.wav"  # 38.0s
    "vo7.wav"   = "$base/hf_20260702_225338_5597fd2e-1813-4186-82f3-c7b9f4d41b3c.wav"  # 9.4s
    "vo8.wav"   = "$base/hf_20260706_213947_6172ec6f-1b37-4ff9-bf54-31fa3f691884.wav"  # DX bridge 16.7s
}
foreach ($name in $assets.Keys) {
    if (-not (Test-Path $name)) {
        Write-Host "downloading $name"
        Invoke-WebRequest -Uri $assets[$name] -OutFile $name
    }
}

$font = 'C\\:/Windows/Fonts/arialbd.ttf'   # escaped for ffmpeg filter syntax
New-Item -ItemType Directory -Force -Path work | Out-Null

# ---------- helpers ----------
function Normalize($in, $out) {
    # unify: 1920x1080, 30fps, yuv420p, video-only
    & ffmpeg -v error -y -i $in -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p" -an -c:v libx264 -preset veryfast -crf 19 $out
}
function FreezeTail($in, $out, $sec) {
    # extend by cloning the last frame (holds the final image under remaining VO)
    & ffmpeg -v error -y -i $in -vf "tpad=stop_mode=clone:stop_duration=$sec" -an -c:v libx264 -preset veryfast -crf 19 $out
}
function Slate($out, $sec, $title, $sub) {
    # navy slate, two centered text lines; replace these sections with real footage
    $vf = "drawtext=fontfile=$font`:text='$title'`:fontcolor=0xf5f2ea`:fontsize=72`:x=(w-text_w)/2`:y=(h-text_h)/2-70," +
          "drawtext=fontfile=$font`:text='$sub'`:fontcolor=0x8fa3bf`:fontsize=34`:x=(w-text_w)/2`:y=(h-text_h)/2+50,format=yuv420p"
    & ffmpeg -v error -y -f lavfi -i "color=c=0x0d1b2e:s=1920x1080:d=${sec}:r=30" -vf $vf -an -c:v libx264 -preset veryfast -crf 19 $out
}
function Segment($n, $pieces, $vo) {
    # concat video pieces, then mux VO (padded; -shortest ends at video length)
    $list = "work/s$n.txt"
    ($pieces | ForEach-Object { "file '$(Split-Path $_ -Leaf)'" }) | Set-Content -Encoding ascii $list
    & ffmpeg -v error -y -f concat -safe 0 -i $list -c copy "work/seg${n}_v.mp4"
    & ffmpeg -v error -y -i "work/seg${n}_v.mp4" -i $vo -filter_complex "[1:a]aresample=48000,apad[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -shortest "work/seg$n.mp4"
}

# ---------- 2. Normalize clips ----------
Write-Host "normalizing clips..."
1..6 | ForEach-Object { Normalize "clip$_.mp4" "work/n$_.mp4" }

# ---------- 3. Build pieces (durations driven by VO lengths) ----------
Write-Host "building slates and extensions..."
# v3 TECHNICAL UX/DX CUT — slates are the screen-recording placeholders (the
# judged content); animation clips are brief accents only (B3/B4 unused spares).
Slate "work/sl1.mp4" 6.6  "COLD OPEN" "playground run screen recording — verdict table streams in"
Slate "work/sl2.mp4" 23.9 "PROBLEM" "send-tool code + stat overlays — 10M CASL · 53K CAN-SPAM · 1.5K TCPA"
Slate "work/sl3.mp4" 28.0 "WHY AGENTS" "seed json c_004 history + template_b missing unsubscribe"
Slate "work/sl4.mp4" 25.7 "ARCHITECTURE" "mermaid diagram + gate.py invariant lines — B5 lands on the invariant"
Slate "work/sl5.mp4" 46.0 "UX DEMO" "full playground run · c_004 overturn · audit log tail"
Slate "work/sl6.mp4" 17.2 "DX BRIDGE" "pytest 9-9 green + skills rule-pack swap"
Slate "work/sl7.mp4" 38.5 "DX DEEP CUTS" "Antigravity · agents-cli eval · MCP in Gemini CLI · Cloud Run"
Slate "work/sl8.mp4" 3.9  "CONSENTGUARD" "agents advise. code decides. — add repo URL end card"

# ---------- 4. Segments (v3 script order S1..S7; 8 audio segments) ----------
Write-Host "assembling segments..."
Segment 1 @("work/sl1.mp4","work/n1.mp4")                "vo1.wav"   # cold open + B1 accent
Segment 2 @("work/sl2.mp4","work/n2.mp4")                "vo2.wav"   # problem + foundry accent
Segment 3 @("work/sl3.mp4")                              "vo3.wav"   # why agents (screen only)
Segment 4 @("work/sl4.mp4","work/n5.mp4")                "vo4.wav"   # architecture + key-turn
Segment 5 @("work/sl5.mp4")                              "vo5.wav"   # UX demo
Segment 6 @("work/sl6.mp4")                              "vo8.wav"   # DX bridge
Segment 7 @("work/sl7.mp4")                              "vo6.wav"   # DX deep cuts
Segment 8 @("work/n6.mp4","work/sl8.mp4")                "vo7.wav"   # close: dawn + end card

# ---------- 5. Final concat ----------
(1..8 | ForEach-Object { "file 'seg$_.mp4'" }) | Set-Content -Encoding ascii work/final.txt
& ffmpeg -v error -y -f concat -safe 0 -i work/final.txt -c copy rough_cut.mp4

$d = & ffprobe -v error -show_entries format=duration -of csv=p=0 rough_cut.mp4
Write-Host ("DONE: rough_cut.mp4  ({0:n1}s ~ {1}m{2:d2}s)" -f [double]$d, [math]::Floor($d/60), [int]($d%60)) -ForegroundColor Green
Write-Host "Next: replace the slate sections with your screen recordings, add text overlays, export <= 5:00."
