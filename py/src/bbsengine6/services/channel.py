# bbsengine6/services/channel.py
# ChannelService - channel configuration and access control.
#
# Phase: Channel Access Control
#
# Channels are named pub/sub topics backed by an in-memory subscription
# state (bbsengine6.net.ChannelState) and a persistent configuration row
# in engine.__channel. The persistent row holds the announce_only flag and
# the list of explicit announcer monikers.
#
# Anyone may subscribe and read from a channel. The announce_only flag
# restricts publishing to:
#   - the configured list of announcers
#   - sysops (always allowed by default)

from typing import Any, Dict, List, Optional

from bbsengine6 import database, member as member_module


class ChannelService:
    """Service for channel configuration and publish-permission checks."""

    def __init__(self, args: Any):
        self.args = args

    def create_channel(
        self,
        name: str,
        createdby: str,
        description: Optional[str] = None,
        announce_only: bool = False,
        announcers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new channel.

        Args:
            name: Unique channel name (used as the pub/sub topic).
            createdby: Moniker of the creating member.
            description: Optional human description.
            announce_only: If True, only announcers (and sysops) may publish.
            announcers: Optional list of initial announcer monikers.

        Returns:
            Dict with success status and the new channel record.
        """
        if not name:
            return {"success": False, "message": "Channel name required"}

        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        "SELECT id FROM $engine.__channel WHERE name = :name",
                        name=name,
                    )
                )
                if cur.fetchone():
                    return {"success": False, "message": "Channel already exists"}

                cur.execute(
                    database.query(
                        """INSERT INTO $engine.__channel
                               (name, description, announce_only, createdby)
                           VALUES (:name, :description, :announce_only, :createdby)
                           RETURNING id, name, description, announce_only,
                                     createdby, datecreated""",
                        name=name,
                        description=description,
                        announce_only=announce_only,
                        createdby=createdby,
                    )
                )
                row = cur.fetchone()
                if not row:
                    return {"success": False, "message": "Failed to create channel"}
                channel_id = row["id"]

                if announce_only and announcers:
                    for moniker in announcers:
                        cur.execute(
                            database.query(
                                """INSERT INTO $engine.__channel_announcer
                                       (channel_id, moniker, addedby)
                                   VALUES (:channel_id, :moniker, :addedby)
                                   ON CONFLICT DO NOTHING""",
                                channel_id=channel_id,
                                moniker=moniker,
                                addedby=createdby,
                            )
                        )

                return {
                    "success": True,
                    "channel": {
                        "id": channel_id,
                        "name": row["name"],
                        "description": row["description"],
                        "announce_only": row["announce_only"],
                        "createdby": row["createdby"],
                        "datecreated": row["datecreated"],
                    },
                }

    def get_channel(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a channel by name from the engine.channel view.

        Returns:
            Dict with channel fields (including the announcers list) or None.
        """
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        """SELECT id, name, description, announce_only,
                                  createdby, datecreated, datemodified, announcers
                           FROM $engine.channel
                           WHERE name = :name""",
                        name=name,
                    )
                )
                row = cur.fetchone()
                if not row:
                    return None
                return dict(row)

    def list_channels(self) -> List[Dict[str, Any]]:
        """List all configured channels."""
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        """SELECT id, name, description, announce_only,
                                  createdby, datecreated, datemodified, announcers
                           FROM $engine.channel
                           ORDER BY name"""
                    )
                )
                return [dict(row) for row in cur.fetchall()]

    def set_announce_only(
        self, name: str, announce_only: bool, by_moniker: str
    ) -> Dict[str, Any]:
        """Toggle the announce_only flag on a channel.

        Args:
            name: Channel name.
            announce_only: New value for the flag.
            by_moniker: Moniker performing the change (for auditing).

        Returns:
            Dict with success status.
        """
        if not member_module.verifyMemberFound(
            self.args, by_moniker, column="moniker"
        ):
            return {"success": False, "message": "Member not found"}

        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        """UPDATE $engine.__channel
                           SET announce_only = :announce_only,
                               datemodified = NOW()
                           WHERE name = :name""",
                        announce_only=announce_only,
                        name=name,
                    )
                )
                if cur.rowcount == 0:
                    return {"success": False, "message": "Channel not found"}
                return {"success": True, "message": "Updated"}

    def add_announcer(
        self, channel_name: str, moniker: str, addedby: str
    ) -> Dict[str, Any]:
        """Add a moniker to a channel's announcer list.

        Returns:
            Dict with success status.
        """
        if not member_module.verifyMemberFound(
            self.args, moniker, column="moniker"
        ):
            return {"success": False, "message": "Member not found"}
        if not member_module.verifyMemberFound(
            self.args, addedby, column="moniker"
        ):
            return {"success": False, "message": "Adding member not found"}

        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        "SELECT id FROM $engine.__channel WHERE name = :name",
                        name=channel_name,
                    )
                )
                row = cur.fetchone()
                if not row:
                    return {"success": False, "message": "Channel not found"}
                channel_id = row["id"]

                cur.execute(
                    database.query(
                        """INSERT INTO $engine.__channel_announcer
                               (channel_id, moniker, addedby)
                           VALUES (:channel_id, :moniker, :addedby)
                           ON CONFLICT DO NOTHING""",
                        channel_id=channel_id,
                        moniker=moniker,
                        addedby=addedby,
                    )
                )
                return {"success": True, "message": "Announcer added"}

    def remove_announcer(
        self, channel_name: str, moniker: str
    ) -> Dict[str, Any]:
        """Remove a moniker from a channel's announcer list.

        Returns:
            Dict with success status.
        """
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        """DELETE FROM $engine.__channel_announcer
                           WHERE moniker = :moniker
                             AND channel_id = (
                                 SELECT id FROM $engine.__channel
                                 WHERE name = :name
                             )""",
                        moniker=moniker,
                        name=channel_name,
                    )
                )
                if cur.rowcount == 0:
                    return {"success": False, "message": "Announcer not found"}
                return {"success": True, "message": "Announcer removed"}

    def can_publish(
        self, channel_name: str, moniker: str, is_sysop: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Check whether a moniker may publish to a channel.

        Non-announce-only channels allow any authenticated member to publish.

        Announce-only channels allow publishing if the moniker is:
          - a sysop (always), or
          - listed in the channel's announcers.

        Args:
            channel_name: Channel name.
            moniker: Member attempting to publish.
            is_sysop: Optional cached sysop flag. If None, looks it up.

        Returns:
            Dict with ``allowed`` (bool) and ``reason`` (str).
        """
        if is_sysop is None:
            is_sysop = member_module.issysop(self.args, moniker=moniker) is True

        channel = self.get_channel(channel_name)
        if not channel:
            return {"allowed": False, "reason": "Channel not found"}

        if not channel["announce_only"]:
            return {"allowed": True, "reason": "Channel is open"}

        if is_sysop:
            return {"allowed": True, "reason": "Sysop"}

        announcers = channel.get("announcers") or []
        if moniker in announcers:
            return {"allowed": True, "reason": "Announcer"}

        return {
            "allowed": False,
            "reason": "Channel is announce-only; sender is not an announcer",
        }
