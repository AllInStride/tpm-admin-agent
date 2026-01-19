"""Tests for Block Kit formatter."""

from src.prep.formatter import format_prep_blocks, format_prep_text


class TestFormatPrepBlocks:
    """Tests for format_prep_blocks function."""

    def test_creates_header_block(self):
        """format_prep_blocks creates header with meeting title."""
        blocks = format_prep_blocks(
            meeting_title="Weekly Sync",
            attendees=[],
            open_items=[],
            talking_points=[],
        )

        header = blocks[0]
        assert header["type"] == "header"
        assert header["text"]["type"] == "plain_text"
        assert header["text"]["text"] == "Meeting Prep: Weekly Sync"

    def test_includes_attendees_section(self):
        """format_prep_blocks includes attendees with roles."""
        blocks = format_prep_blocks(
            meeting_title="Team Sync",
            attendees=[
                {"name": "Alice", "role": "Host"},
                {"name": "Bob", "role": "Reviewer"},
            ],
            open_items=[],
            talking_points=[],
        )

        attendee_block = blocks[1]
        assert attendee_block["type"] == "section"
        assert "Alice (Host)" in attendee_block["text"]["text"]
        assert "Bob (Reviewer)" in attendee_block["text"]["text"]

    def test_attendees_without_role(self):
        """format_prep_blocks handles attendees without role."""
        blocks = format_prep_blocks(
            meeting_title="Team Sync",
            attendees=[
                {"name": "Alice"},
                {"name": "Bob", "role": "PM"},
            ],
            open_items=[],
            talking_points=[],
        )

        attendee_block = blocks[1]
        # Alice without role, Bob with role
        assert "Alice, Bob (PM)" in attendee_block["text"]["text"]

    def test_includes_dividers(self):
        """format_prep_blocks includes dividers between sections."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[{"name": "Alice"}],
            open_items=[],
            talking_points=["Point 1"],
        )

        dividers = [b for b in blocks if b["type"] == "divider"]
        assert len(dividers) >= 2

    def test_overdue_items_section(self):
        """format_prep_blocks creates overdue items section with warning."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[
                {
                    "description": "Finish report",
                    "owner": "Alice",
                    "due_date": "2026-01-15",
                    "is_overdue": True,
                    "is_new": False,
                },
            ],
            talking_points=[],
        )

        # Find overdue section
        overdue_section = None
        for block in blocks:
            if block["type"] == "section":
                text = block["text"]["text"]
                if "Overdue Items" in text:
                    overdue_section = block
                    break

        assert overdue_section is not None
        assert ":warning:" in overdue_section["text"]["text"]
        assert "Finish report" in overdue_section["text"]["text"]
        assert "Alice" in overdue_section["text"]["text"]
        assert "2026-01-15" in overdue_section["text"]["text"]

    def test_open_items_section(self):
        """format_prep_blocks creates open items section."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[
                {
                    "description": "Review design",
                    "owner": "Bob",
                    "due_date": "2026-02-01",
                    "is_overdue": False,
                    "is_new": False,
                },
            ],
            talking_points=[],
        )

        # Find open items section
        items_section = None
        for block in blocks:
            if block["type"] == "section":
                text = block["text"]["text"]
                if "Open Items:" in text:
                    items_section = block
                    break

        assert items_section is not None
        assert "Review design" in items_section["text"]["text"]
        assert "Bob" in items_section["text"]["text"]

    def test_new_items_marked(self):
        """format_prep_blocks marks new items with *NEW* prefix."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[
                {
                    "description": "New task",
                    "owner": "Charlie",
                    "due_date": "2026-02-15",
                    "is_overdue": False,
                    "is_new": True,
                },
            ],
            talking_points=[],
        )

        # Find open items section
        items_section = None
        for block in blocks:
            if block["type"] == "section":
                text = block["text"]["text"]
                if "Open Items:" in text:
                    items_section = block
                    break

        assert items_section is not None
        assert "*NEW*" in items_section["text"]["text"]

    def test_description_truncation(self):
        """format_prep_blocks truncates long descriptions at 50 chars."""
        long_description = "A" * 100
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[
                {
                    "description": long_description,
                    "owner": "Dave",
                    "due_date": None,
                    "is_overdue": False,
                    "is_new": False,
                },
            ],
            talking_points=[],
        )

        # Find the items section
        items_section = None
        for block in blocks:
            if block["type"] == "section":
                text = block["text"]["text"]
                if "Open Items:" in text:
                    items_section = block
                    break

        assert items_section is not None
        # Check truncation with ellipsis
        assert "A" * 50 + "..." in items_section["text"]["text"]
        assert "A" * 51 not in items_section["text"]["text"]

    def test_talking_points_section(self):
        """format_prep_blocks includes talking points as bullets."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[],
            talking_points=["Point one", "Point two", "Point three"],
        )

        # Find talking points section
        tp_section = None
        for block in blocks:
            if block["type"] == "section":
                text = block["text"]["text"]
                if "Suggested Talking Points:" in text:
                    tp_section = block
                    break

        assert tp_section is not None
        assert "- Point one" in tp_section["text"]["text"]
        assert "- Point two" in tp_section["text"]["text"]
        assert "- Point three" in tp_section["text"]["text"]

    def test_max_three_talking_points(self):
        """format_prep_blocks limits talking points to 3."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[],
            talking_points=["One", "Two", "Three", "Four", "Five"],
        )

        # Find talking points section
        tp_section = None
        for block in blocks:
            if block["type"] == "section":
                text = block["text"]["text"]
                if "Suggested Talking Points:" in text:
                    tp_section = block
                    break

        assert tp_section is not None
        assert "- One" in tp_section["text"]["text"]
        assert "- Two" in tp_section["text"]["text"]
        assert "- Three" in tp_section["text"]["text"]
        assert "- Four" not in tp_section["text"]["text"]
        assert "- Five" not in tp_section["text"]["text"]

    def test_links_section_with_both_urls(self):
        """format_prep_blocks includes links when URLs provided."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[],
            talking_points=[],
            recent_meeting_url="https://example.com/notes",
            full_prep_url="https://example.com/prep",
        )

        # Find context block with links
        links_section = None
        for block in blocks:
            if block["type"] == "context":
                links_section = block
                break

        assert links_section is not None
        elements = links_section["elements"]
        assert len(elements) == 1
        link_text = elements[0]["text"]
        assert "<https://example.com/notes|Recent Meeting Notes>" in link_text
        assert "<https://example.com/prep|View Full Prep>" in link_text

    def test_links_section_with_only_recent(self):
        """format_prep_blocks handles only recent meeting URL."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[],
            talking_points=[],
            recent_meeting_url="https://example.com/notes",
        )

        links_section = None
        for block in blocks:
            if block["type"] == "context":
                links_section = block
                break

        assert links_section is not None
        link_text = links_section["elements"][0]["text"]
        assert "Recent Meeting Notes" in link_text
        assert "Full Prep" not in link_text

    def test_no_links_section_when_no_urls(self):
        """format_prep_blocks omits links section when no URLs."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[],
            talking_points=[],
        )

        # Should have no context block
        context_blocks = [b for b in blocks if b["type"] == "context"]
        assert len(context_blocks) == 0

    def test_handles_empty_attendees(self):
        """format_prep_blocks handles empty attendees list."""
        blocks = format_prep_blocks(
            meeting_title="Solo Meeting",
            attendees=[],
            open_items=[],
            talking_points=["Check in"],
        )

        # Should not have attendees section (no section with "Attendees:")
        attendee_sections = [
            b
            for b in blocks
            if b["type"] == "section" and "Attendees:" in b["text"]["text"]
        ]
        assert len(attendee_sections) == 0

    def test_handles_missing_owner(self):
        """format_prep_blocks uses TBD for missing owner."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[
                {
                    "description": "Unassigned task",
                    "owner": None,
                    "due_date": "2026-02-01",
                    "is_overdue": False,
                    "is_new": False,
                },
            ],
            talking_points=[],
        )

        # Find items section
        items_section = None
        for block in blocks:
            if block["type"] == "section":
                text = block["text"]["text"]
                if "Open Items:" in text:
                    items_section = block
                    break

        assert items_section is not None
        assert "| TBD |" in items_section["text"]["text"]

    def test_handles_missing_due_date(self):
        """format_prep_blocks uses 'No date' for missing due date."""
        blocks = format_prep_blocks(
            meeting_title="Test",
            attendees=[],
            open_items=[
                {
                    "description": "Task without date",
                    "owner": "Eve",
                    "due_date": None,
                    "is_overdue": False,
                    "is_new": False,
                },
            ],
            talking_points=[],
        )

        items_section = None
        for block in blocks:
            if block["type"] == "section":
                text = block["text"]["text"]
                if "Open Items:" in text:
                    items_section = block
                    break

        assert items_section is not None
        assert "No date" in items_section["text"]["text"]


class TestFormatPrepText:
    """Tests for format_prep_text function."""

    def test_includes_meeting_title(self):
        """format_prep_text includes meeting title."""
        text = format_prep_text(
            meeting_title="Weekly Review",
            open_items=[],
            talking_points=[],
        )

        assert "Meeting Prep: Weekly Review" in text

    def test_shows_item_counts(self):
        """format_prep_text shows open item counts."""
        text = format_prep_text(
            meeting_title="Test",
            open_items=[
                {"description": "Item 1", "is_overdue": False},
                {"description": "Item 2", "is_overdue": False},
                {"description": "Item 3", "is_overdue": True},
            ],
            talking_points=[],
        )

        assert "3 open items, 1 overdue" in text

    def test_no_overdue_text(self):
        """format_prep_text omits overdue count when none overdue."""
        text = format_prep_text(
            meeting_title="Test",
            open_items=[
                {"description": "Item 1", "is_overdue": False},
                {"description": "Item 2", "is_overdue": False},
            ],
            talking_points=[],
        )

        assert "2 open items" in text
        assert "overdue" not in text

    def test_no_items_text(self):
        """format_prep_text handles no open items."""
        text = format_prep_text(
            meeting_title="Test",
            open_items=[],
            talking_points=[],
        )

        assert "No open items" in text

    def test_includes_top_talking_point(self):
        """format_prep_text includes first talking point."""
        text = format_prep_text(
            meeting_title="Test",
            open_items=[],
            talking_points=["Review Q4 goals", "Budget update"],
        )

        assert "Top talking point: Review Q4 goals" in text
        assert "Budget update" not in text

    def test_no_talking_points(self):
        """format_prep_text handles no talking points."""
        text = format_prep_text(
            meeting_title="Test",
            open_items=[],
            talking_points=[],
        )

        assert "Top talking point" not in text
