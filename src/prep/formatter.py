"""Block Kit formatter for Slack meeting prep messages.

Creates scannable Slack Block Kit messages for meeting prep summaries
per CONTEXT.md formatting requirements.
"""


def format_prep_blocks(
    meeting_title: str,
    attendees: list[dict],  # {name, role}
    open_items: list[dict],  # PrepItem-like dicts
    talking_points: list[str],
    recent_meeting_url: str | None = None,
    full_prep_url: str | None = None,
) -> list[dict]:
    """Format prep summary as Slack Block Kit blocks.

    Per CONTEXT.md:
    - Scannable (fits one screen)
    - Header block with meeting title
    - Attendees with roles
    - Overdue items with warning emoji
    - Open items compact format
    - NEW items marked with *NEW* prefix
    - Talking points (2-3 max)
    - Links to recent meeting notes and full prep

    Args:
        meeting_title: Title of the meeting
        attendees: List of dicts with 'name' and optional 'role'
        open_items: Prep item dicts with description, owner, due_date, etc.
        talking_points: List of talking point strings (max 3)
        recent_meeting_url: URL to most recent meeting notes
        full_prep_url: URL to full prep document

    Returns:
        List of Slack Block Kit block dicts
    """
    blocks: list[dict] = []

    # Header
    blocks.append(
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Meeting Prep: {meeting_title}"},
        }
    )

    # Attendees section
    if attendees:
        attendee_text = ", ".join(
            f"{a.get('name', 'Unknown')} ({a.get('role')})"
            if a.get("role")
            else a.get("name", "Unknown")
            for a in attendees
        )
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Attendees:* {attendee_text}"},
            }
        )

    blocks.append({"type": "divider"})

    # Separate overdue and non-overdue items
    overdue_items = [i for i in open_items if i.get("is_overdue")]
    other_items = [i for i in open_items if not i.get("is_overdue")]

    # Overdue items section
    if overdue_items:
        overdue_lines = []
        for item in overdue_items:
            desc = item.get("description", "")[:50]
            if len(item.get("description", "")) > 50:
                desc += "..."
            owner = item.get("owner") or "TBD"
            due = item.get("due_date") or "No date"
            overdue_lines.append(f":warning: {desc} | {owner} | {due}")

        overdue_text = "\n".join(overdue_lines)
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Overdue Items:*\n{overdue_text}",
                },
            }
        )

    # Open items section (non-overdue)
    if other_items:
        item_lines = []
        for item in other_items:
            prefix = "*NEW* " if item.get("is_new") else ""
            desc = item.get("description", "")[:50]
            if len(item.get("description", "")) > 50:
                desc += "..."
            owner = item.get("owner") or "TBD"
            due = item.get("due_date") or "No date"
            item_lines.append(f"{prefix}{desc} | {owner} | {due}")

        items_text = "\n".join(item_lines)
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Open Items:*\n{items_text}"},
            }
        )

    blocks.append({"type": "divider"})

    # Talking points (max 3)
    if talking_points:
        tp_text = "\n".join(f"- {tp}" for tp in talking_points[:3])
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Suggested Talking Points:*\n{tp_text}",
                },
            }
        )

    # Links section
    links = []
    if recent_meeting_url:
        links.append(f"<{recent_meeting_url}|Recent Meeting Notes>")
    if full_prep_url:
        links.append(f"<{full_prep_url}|View Full Prep>")

    if links:
        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": " | ".join(links)}],
            }
        )

    return blocks


def format_prep_text(
    meeting_title: str,
    open_items: list[dict],
    talking_points: list[str],
) -> str:
    """Format prep summary as plain text fallback.

    Concise text for Slack notification previews:
    "Meeting Prep: {title}\n{N} open items, {M} overdue\nTop talking point: {point}"

    Args:
        meeting_title: Title of the meeting
        open_items: List of prep item dicts
        talking_points: List of talking point strings

    Returns:
        Plain text summary
    """
    total = len(open_items)
    overdue = len([i for i in open_items if i.get("is_overdue")])

    lines = [f"Meeting Prep: {meeting_title}"]

    if total > 0:
        if overdue > 0:
            lines.append(f"{total} open items, {overdue} overdue")
        else:
            lines.append(f"{total} open items")
    else:
        lines.append("No open items")

    if talking_points:
        lines.append(f"Top talking point: {talking_points[0]}")

    return "\n".join(lines)
