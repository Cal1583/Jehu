# Verse Wallpaper

A Windows desktop app that renders a daily Bible reading wallpaper with an “open book” layout: analytics treemap on the left page, Scripture on the right page.

## Setup

1. Install Python 3.11+.
2. Install dependencies:

```bash
pip install PySide6 Pillow
```

Optional (for improved fonts/treemap rendering):

```bash
pip install squarify
```

> The app ships with a built-in treemap fallback if `squarify` is not installed.

## Run the GUI

```bash
python main.py
```

## Run daily mode (for Task Scheduler)

```bash
python main.py --daily
```

## Windows Task Scheduler

Create a task that runs daily at **12:00 AM** with the action:

```
python C:\path\to\VerseWallpaper\main.py --daily
```

Ensure the task is set to “Run whether user is logged on or not” so the wallpaper updates at midnight.
