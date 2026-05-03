# Music Video Creator

A simple desktop app (Tkinter) that combines images and an audio file into a music video.

## Requirements

- Python 3.9+
- pip

## Setup

```bash
cd music_video_creator
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## How to use

1. Click **Browse…** to pick your MP3 (or WAV/AAC/OGG/FLAC) audio file
2. Click **+ Add Image** to add one or more images — you can select multiple at once
3. Set how many seconds each image should be shown using the duration spinner next to it
4. Click **▶ Generate Video** — a Save dialog will ask where to save the `.mp4`
5. Wait for the progress bar to finish — your video will be saved at the chosen location

## Build progress

| Step | Status | What it adds |
|------|--------|-------------|
| Step 1 | ✅ Done | Basic UI — audio picker, image list, timing controls |
| Step 2 | ✅ Done | Real video generation with MoviePy, progress bar, Save As dialog |
| Step 3 | 🔜 Next | Preview / playback inside the app |
| Step 4 | 🔜 Planned | Export options (resolution, fps) |
