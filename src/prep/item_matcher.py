"""Item matcher for meeting prep.

Matches open items by attendee emails and project association,
with prioritization for meeting prep summaries.
"""

from datetime import datetime

from src.db.turso import TursoClient
from src.prep.schemas import TalkingPoint
from src.search.open_items import CLOSED_STATUSES

# Type priority order per CONTEXT.md: action > risk > issue > decision
TYPE_ORDER = {"action": 0, "risk": 1, "issue": 2, "decision": 3}


class ItemMatcher:
    """Matches and retrieves open items for meeting prep.

    Queries raid_items_projection for open items matching both
    attendee emails AND project association per CONTEXT.md.
    """

    def __init__(self, db_client: TursoClient):
        """Initialize with database client.

        Args:
            db_client: TursoClient instance for database operations
        """
        self._db = db_client
        # Build closed statuses SQL for IN clause
        self._closed_statuses_sql = ", ".join(f"'{s}'" for s in CLOSED_STATUSES)

    async def get_items_for_prep(
        self,
        attendee_emails: list[str],
        project_id: str,
        lookback_days: int = 90,
    ) -> list[dict]:
        """Get open items matching attendees AND project.

        Per CONTEXT.md: match by BOTH attendee overlap AND project association.
        Items are returned where:
        1. owner email is in attendee_emails list, OR
        2. meeting_id is from a meeting where any attendee_emails were present

        Args:
            attendee_emails: Meeting attendee emails
            project_id: Project ID for scoping (reserved for future use)
            lookback_days: How far back to look (default 90 days)

        Returns:
            List of matching items with id, meeting_id, item_type, description,
            owner, due_date, status, confidence, created_at, is_overdue
        """
        if not attendee_emails:
            return []

        # Build email placeholders for SQL
        email_placeholders = ",".join(["?"] * len(attendee_emails))

        # Query for open items matching attendee criteria
        # Note: project_id filtering would be added when project associations exist
        query = f"""
            SELECT id, meeting_id, item_type, description, owner,
                   due_date, status, confidence, created_at
            FROM raid_items_projection
            WHERE status NOT IN ({self._closed_statuses_sql})
              AND created_at >= date('now', '-{lookback_days} days')
              AND (
                  owner IN ({email_placeholders})
                  OR meeting_id IN (
                      SELECT DISTINCT meeting_id FROM raid_items_projection
                      WHERE owner IN ({email_placeholders})
                  )
              )
            ORDER BY created_at DESC
        """

        # Params: attendee_emails used twice in query
        params = list(attendee_emails) + list(attendee_emails)

        result = await self._db.execute(query, params)

        today = datetime.now().strftime("%Y-%m-%d")
        items = []
        for row in result.rows:
            due_date = row[5]
            is_overdue = bool(due_date and due_date < today)

            items.append(
                {
                    "id": row[0],
                    "meeting_id": row[1],
                    "item_type": row[2],
                    "description": row[3],
                    "owner": row[4],
                    "due_date": due_date,
                    "status": row[6],
                    "confidence": row[7],
                    "created_at": row[8],
                    "is_overdue": is_overdue,
                }
            )

        return items


def prioritize_items(
    items: list[dict],
    max_items: int = 10,
    last_meeting_date: datetime | None = None,
) -> list[dict]:
    """Prioritize items for meeting prep summary.

    Sort order per CONTEXT.md:
    1. Overdue items first (is_overdue = True)
    2. Then by type order: action=0, risk=1, issue=2, decision=3
    3. Then by due_date ascending (nulls last)

    Also marks items as is_new if created after last_meeting_date.

    Args:
        items: List of item dicts with is_overdue, item_type, due_date
        max_items: Maximum items to return (default 10)
        last_meeting_date: When last meeting occurred (for is_new marking)

    Returns:
        Prioritized list truncated to max_items
    """
    if not items:
        return []

    def priority_key(item: dict) -> tuple:
        """Sort key: (not overdue, type_order, due_date)."""
        is_overdue = item.get("is_overdue", False)
        item_type = item.get("item_type", "decision")
        type_order = TYPE_ORDER.get(item_type, 4)
        due_date = item.get("due_date") or "9999-99-99"  # Nulls last
        return (not is_overdue, type_order, due_date)

    sorted_items = sorted(items, key=priority_key)

    # Mark is_new for items created after last meeting
    if last_meeting_date:
        last_date_str = last_meeting_date.strftime("%Y-%m-%dT%H:%M:%S")
        for item in sorted_items:
            created_at = item.get("created_at", "")
            item["is_new"] = bool(created_at and created_at > last_date_str)
    else:
        for item in sorted_items:
            item["is_new"] = False

    return sorted_items[:max_items]


def generate_talking_points(
    items: list[dict],
    max_points: int = 3,
) -> list[TalkingPoint]:
    """Generate suggested talking points from items.

    Heuristic approach per RESEARCH.md:
    - If overdue items exist: "Review N overdue items"
    - If high-severity risks exist: "Discuss risk: description"
    - If new items since last meeting: "N new items since last meeting"
    - Generic fallback: "Status update on open action items"

    Args:
        items: List of item dicts
        max_points: Maximum points to return (default 3)

    Returns:
        List of TalkingPoint models (2-3 items)
    """
    points: list[TalkingPoint] = []

    if not items:
        points.append(
            TalkingPoint(
                text="No open items to discuss",
                category="general",
            )
        )
        return points[:max_points]

    # Check for overdue items
    overdue_items = [i for i in items if i.get("is_overdue")]
    if overdue_items:
        count = len(overdue_items)
        plural = "s" if count > 1 else ""
        points.append(
            TalkingPoint(
                text=f"Review {count} overdue item{plural}",
                category="overdue",
            )
        )

    # Check for high-severity risks
    risks = [i for i in items if i.get("item_type") == "risk"]
    if risks:
        # Get the first risk description, truncated
        risk_desc = risks[0].get("description", "")[:50]
        if len(risks[0].get("description", "")) > 50:
            risk_desc += "..."
        points.append(
            TalkingPoint(
                text=f"Discuss risk: {risk_desc}",
                category="risk",
            )
        )

    # Check for new items
    new_items = [i for i in items if i.get("is_new")]
    if new_items:
        count = len(new_items)
        plural = "s" if count > 1 else ""
        points.append(
            TalkingPoint(
                text=f"{count} new item{plural} since last meeting",
                category="new_item",
            )
        )

    # Generic fallback if no specific points yet
    if not points:
        action_count = len([i for i in items if i.get("item_type") == "action"])
        if action_count > 0:
            plural = "s" if action_count > 1 else ""
            points.append(
                TalkingPoint(
                    text=f"Status update on {action_count} open action item{plural}",
                    category="general",
                )
            )
        else:
            points.append(
                TalkingPoint(
                    text="Review open items status",
                    category="general",
                )
            )

    return points[:max_points]
