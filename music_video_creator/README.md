# Music Video Creator

A desktop app (Tkinter) that combines images and an audio file into a music video — with AI-powered lyric transcription to set image switch points by clicking words.

## Requirements

- Python 3.9+
- pip
- **ffmpeg** must be installed on your system (required by MoviePy and Whisper)
  - macOS: `brew install ffmpeg`
  - Windows: download from https://ffmpeg.org/download.html and add to PATH
  - Linux: `sudo apt install ffmpeg`

## Setup

```bash
cd music_video_creator
pip install -r requirements.txt
```

> **Note:** The first run of "Transcribe Lyrics" downloads the Whisper `base` model (~140 MB). This only happens once.

## Run

```bash
python main.py
```

## How to use

### Basic workflow
1. Click **Browse…** to pick your audio file (MP3, WAV, AAC, OGG, FLAC)
2. Go to the **Images & Timing** tab → click **+ Add Image** to add images in order
3. Set "Switch after" values manually, or use the Lyrics feature below
4. Click **▶ Generate Video** → choose where to save the `.mp4`

### Using Lyrics to set switch points
1. Load your audio file
2. Click **🎤 Transcribe Lyrics** — Whisper AI will transcribe the audio with word-level timestamps
3. The **Lyrics** tab opens showing every word as clickable text
4. Click a word at the moment you want to switch to the next image
   - Selected words highlight in orange
   - You need exactly **(number of images − 1)** switch points
   - A counter at the top guides you
5. Switch times are automatically applied to your image list
6. Click **▶ Generate Video** when ready

## Build progress

| Step | Status | What it adds |
|------|--------|-------------|
| Step 1 | ✅ Done | Basic UI — audio picker, image list, timing controls |
| Step 2 | ✅ Done | Real video generation with MoviePy |
| Step 3 | ✅ Done | AI lyric transcription + click-to-set switch points |
| Step 4 | 🔜 Next | In-app video preview / playback |
