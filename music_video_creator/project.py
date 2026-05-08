import json
import os
from pathlib import Path

VPROJ_VERSION = "1.0"
VPROJ_EXTENSION = ".vproj"


def _resolve_tree_save(node: dict, project_dir: Path) -> dict:
    if not node:
        return node
    return {
        "type":     node.get("type"),
        "name":     node.get("name"),
        "path":     _to_stored_path(node["path"], project_dir) if node.get("path") else None,
        "duration": node.get("duration"),
        "children": [_resolve_tree_save(c, project_dir) for c in node.get("children", [])],
    }


def _resolve_tree_load(node: dict, project_dir: Path) -> dict:
    if not node:
        return node
    return {
        "type":     node.get("type"),
        "name":     node.get("name"),
        "path":     _to_absolute_path(node["path"], project_dir) if node.get("path") else None,
        "duration": node.get("duration"),
        "children": [_resolve_tree_load(c, project_dir) for c in node.get("children", [])],
    }


def _to_stored_path(asset_path: str, project_dir: Path) -> str:
    """Relative if the asset lives inside the project folder, otherwise absolute."""
    try:
        return str(Path(asset_path).relative_to(project_dir))
    except ValueError:
        return str(Path(asset_path))


def _to_absolute_path(stored_path: str, project_dir: Path) -> str:
    """Resolve a stored path (relative or absolute) to an absolute filesystem path."""
    p = Path(stored_path)
    return str(p if p.is_absolute() else project_dir / p)


def new_project(filepath: str) -> None:
    """
    Create the .vproj file plus the standard folder structure:
      out/  — rendered video outputs
      gen/  — generated assets (transcripts, etc.)
    """
    project_dir = Path(filepath).parent
    (project_dir / "out").mkdir(parents=True, exist_ok=True)
    (project_dir / "gen").mkdir(parents=True, exist_ok=True)

    project_name = Path(filepath).stem
    data = {
        "version":      VPROJ_VERSION,
        "audio_path":   None,
        "project_tree": {"type": "video", "name": project_name, "path": None, "children": []},
        "images":       [],
        "transcript":   None,
        "switch_points": [],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_project(state, filepath: str) -> None:
    project_dir = Path(filepath).parent

    # Persist transcript to gen/transcript.json; keep .vproj compact
    transcript_ref = None
    if state.transcription_words:
        gen_dir = project_dir / "gen"
        gen_dir.mkdir(exist_ok=True)
        transcript_file = gen_dir / "transcript.json"
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(state.transcription_words, f, indent=2)
        transcript_ref = "gen/transcript.json"

    project_tree = _resolve_tree_save(state.project_tree, project_dir)

    images = [
        {
            "path": _to_stored_path(e["path"], project_dir),
            "load_time": e["load_var"].get(),
        }
        for e in state.image_entries
    ]

    data = {
        "version":      VPROJ_VERSION,
        "audio_path":   _to_stored_path(state.audio_path, project_dir) if state.audio_path else None,
        "project_tree": project_tree,
        "images":       images,
        "transcript":   transcript_ref,
        "switch_points": state.switch_points,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_project(filepath: str) -> dict:
    project_dir = Path(filepath).parent

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Resolve audio path to absolute
    if data.get("audio_path"):
        data["audio_path"] = _to_absolute_path(data["audio_path"], project_dir)

    # Resolve project tree paths to absolute
    if data.get("project_tree"):
        data["project_tree"] = _resolve_tree_load(data["project_tree"], project_dir)

    # Resolve image paths to absolute
    data["images"] = [
        {
            "path": _to_absolute_path(img["path"], project_dir),
            "load_time": img.get("load_time", 0.0),
        }
        for img in data.get("images", [])
    ]

    # Load transcript from gen/ if the reference exists
    transcript_ref = data.get("transcript")
    if transcript_ref:
        transcript_file = _to_absolute_path(transcript_ref, project_dir)
        if os.path.exists(transcript_file):
            with open(transcript_file, "r", encoding="utf-8") as f:
                data["transcription_words"] = json.load(f)
        else:
            data["transcription_words"] = []
    else:
        data["transcription_words"] = []

    return data
