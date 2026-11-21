from __future__ import annotations

import pytest

from universal_dataset_builder.workers.caption_worker import select_caption_targets


def _record(filename, status, caption="", reviewed=0):
    return {
        "filename": filename,
        "status": status,
        "caption_text": caption,
        "caption_reviewed": reviewed,
    }


def test_caption_selection_only_picks_missing_captions_and_honors_limit():
    rows = [
        _record("c.png", "Pending"),
        _record("b.png", "Normalized"),
        _record("a.png", "Captioned", "Existing caption"),
        _record("d.png", "Reviewed", "Human reviewed", 1),
        _record("e.png", "Excluded"),
        _record("f.png", "Failed"),
    ]

    selected = select_caption_targets(rows, "missing", limit=1)

    assert [row["filename"] for row in selected] == ["b.png"]


def test_caption_selection_can_regenerate_unreviewed_but_not_reviewed_images():
    rows = [
        _record("a.png", "Captioned", "Old generated caption"),
        _record("b.png", "Normalized"),
        _record("c.png", "Reviewed", "Human caption", 1),
        _record("d.png", "Excluded"),
        _record("e.png", "Failed"),
    ]

    selected = select_caption_targets(rows, "unreviewed")

    assert [row["filename"] for row in selected] == ["a.png", "b.png"]


def test_caption_selection_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported caption generation mode"):
        select_caption_targets([], "everything")
