# bbsengine6/services/member.py
# MemberService - profile management, tiers, and referrals

from typing import Any, Dict, List, Optional

from bbsengine6 import database, member as member_module


class MemberService:
    """Service for member profile management, tiers, and referrals."""

    def __init__(self, args: Any):
        self.args = args

    def get_profile(self, moniker: str) -> Optional[Dict[str, Any]]:
        """Get member profile from engine.member view.
        
        Args:
            moniker: Member moniker
            
        Returns:
            Dict with member profile or None if not found
        """
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        """SELECT moniker, email, credits, tier, attrs, refcode, 
                                  parentmoniker, lastlogin, datecreated, tz, ui
                           FROM engine.member 
                           WHERE moniker = :moniker""",
                        moniker=moniker
                    )
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
                return None

    def update_profile(self, moniker: str, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Update member attributes.
        
        Args:
            moniker: Member moniker
            attrs: Dict of attributes to update (merged with existing)
            
        Returns:
            Dict with success status and message
        """
        if not member_module.verifyMemberFound(self.args, moniker):
            return {"success": False, "message": "Member not found"}

        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                member_module.setattrs(self.args, attrs, moniker=moniker, cur=cur)
                return {"success": True, "message": "Profile updated"}

    def get_tier(self, moniker: str) -> Optional[str]:
        """Get member tier from engine.member view.
        
        Args:
            moniker: Member moniker
            
        Returns:
            Tier string or None if not set
        """
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        "SELECT tier FROM engine.member WHERE moniker = :moniker",
                        moniker=moniker
                    )
                )
                row = cur.fetchone()
                return row["tier"] if row else None

    def set_tier(self, moniker: str, tier: str) -> bool:
        """Set member tier in attrs.
        
        Args:
            moniker: Member moniker
            tier: Tier string to set
            
        Returns:
            True if successful, False otherwise
        """
        if not member_module.verifyMemberFound(self.args, moniker):
            return False

        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                member_module.setattrs(
                    self.args, {"tier": tier}, moniker=moniker, cur=cur
                )
                return True

    def get_referral_code(self, moniker: str) -> Optional[str]:
        """Get member's referral code.
        
        Args:
            moniker: Member moniker
            
        Returns:
            Referral code or None if not set
        """
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        "SELECT refcode FROM engine.__member WHERE moniker = :moniker",
                        moniker=moniker
                    )
                )
                row = cur.fetchone()
                return row["refcode"] if row else None

    def get_referrals(self, moniker: str) -> List[Dict[str, Any]]:
        """Get list of members referred by this member.
        
        Uses parentmoniker to find members who were referred by this member.
        
        Args:
            moniker: Member moniker (the referrer)
            
        Returns:
            List of dicts with referred member info
        """
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        """SELECT moniker, email, tier, datecreated as referral_date
                           FROM engine.member 
                           WHERE parentmoniker = :moniker
                           ORDER BY datecreated DESC""",
                        moniker=moniker
                    )
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]

    def use_referral_code(self, moniker: str, code: str) -> Dict[str, Any]:
        """Record referral code usage.
        
        Validates the code and records usage in map_refcode_use.
        Also updates the member's parentmoniker.
        
        Args:
            moniker: Member using the code (the referred)
            code: Referral code being used
            
        Returns:
            Dict with success status and message
        """
        with database.connect(self.args) as conn:
            with database.cursor(conn) as cur:
                cur.execute(
                    database.query(
                        "SELECT code, createdbymoniker FROM engine.__refcode WHERE code = :code",
                        code=code
                    )
                )
                row = cur.fetchone()
                if not row:
                    return {"success": False, "message": "Invalid referral code"}

                referrer = row["createdbymoniker"]
                if not referrer:
                    return {"success": False, "message": "Referral code has no owner"}

                if referrer == moniker:
                    return {"success": False, "message": "Cannot use your own referral code"}

                cur.execute(
                    database.query(
                        "SELECT 1 FROM engine.map_refcode_use WHERE code = :code AND usedbymoniker = :moniker",
                        code=code, moniker=moniker
                    )
                )
                if cur.fetchone():
                    return {"success": False, "message": "Referral code already used"}

                cur.execute(
                    database.query(
                        "INSERT INTO engine.map_refcode_use (code, usedbymoniker, dateused) VALUES (:code, :moniker, NOW())",
                        code=code, moniker=moniker
                    )
                )

                cur.execute(
                    database.query(
                        "UPDATE engine.__member SET parentmoniker = :referrer WHERE moniker = :moniker",
                        referrer=referrer, moniker=moniker
                    )
                )

                return {"success": True, "message": f"Referral recorded", "referrer": referrer}
