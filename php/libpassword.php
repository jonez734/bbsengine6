<?php

/**
 * libpassword.php
 *
 * PHP-side password hashing helpers. Mirrors the role of
 * bbsengine6.util.encryptpassword on the Python side: single source
 * of truth for new password hashes, no PostgreSQL crypt()/gen_salt()
 * round-trip, prefix and cost in lock-step with PG's gen_salt('bf')
 * default so cross-platform verification still works.
 *
 * Hash format produced by hash_password():
 *   "$2y$06$<22-char salt><31-char digest>"  (length 60)
 *
 * Verification is local via PHP password_verify() — no PostgreSQL
 * round-trip. The chk_member_password_bcrypt CHECK constraint
 * (^\$2[abxy]\$, length 60) accepts this hash, and the cost factor
 * matches:
 *   - bbsengine6.util._BCRYPT_ROUNDS = 6 (Python passlib)
 *   - PG gen_salt('bf') default = 6
 *
 * Note: PG crypt(plaintext, stored) only recognises the $2a$ prefix
 * (gen_salt('bf') output). PHP password_hash() emits $2y$ and Python
 * passlib emits $2b$, so the historical "crypt() backstop" path is
 * broken for both local writers by design. Since verification happens
 * locally on each platform, the cross-platform drift is harmless; the
 * integration test (test_php_password_round_trip.php) pins the
 * behaviour so any regression that reintroduces PG crypt() as a
 * fallback catches the mismatch immediately.
 *
 * @since 20260823
 */

namespace bbsengine6\password
{

if (!defined("BBSENGINE_BCRYPT_COST")) {
    define("BBSENGINE_BCRYPT_COST", 6);
}

const BCRYPT_PREFIX_REGEX = '#^\$2[abxy]\$#';
const BCRYPT_HASH_LENGTH  = 60;
const LEGACY_MD5_PREFIX_REGEX = '#^\$1\$#';

function hash_password(string $plaintext): string
{
    if ($plaintext === "") {
        throw new \InvalidArgumentException("Plaintext must be non-empty");
    }
    $hash = \password_hash(
        $plaintext,
        \PASSWORD_BCRYPT,
        ["cost" => BBSENGINE_BCRYPT_COST]
    );
    if ($hash === false || strlen($hash) !== BCRYPT_HASH_LENGTH) {
        throw new \RuntimeException("password_hash() returned malformed value");
    }
    return $hash;
}

function verify_password(string $plaintext, string $stored): bool
{
    if ($plaintext === "" || $stored === "") {
        return false;
    }
    try {
        return \password_verify($plaintext, $stored);
    } catch (\Throwable $e) {
        \bbsengine6\util\logentry(
            "libpassword.verify_password.100: " . $e->getMessage()
        );
        return false;
    }
}

function is_healthy_hash(?string $stored): bool
{
    if ($stored === null || $stored === "") {
        return false;
    }
    if (strlen($stored) !== BCRYPT_HASH_LENGTH) {
        return false;
    }
    return (bool) preg_match(BCRYPT_PREFIX_REGEX, $stored);
}

function needs_rehash(?string $stored): bool
{
    return !is_healthy_hash($stored);
}

function classify_hash(?string $stored): string
{
    if ($stored === null) return "null";
    if ($stored === "")   return "empty";
    if (preg_match(BCRYPT_PREFIX_REGEX, $stored) === 1) return "bcrypt";
    if (preg_match(LEGACY_MD5_PREFIX_REGEX, $stored) === 1) return "md5crypt";
    return "other";
}

} /* namespace bbsengine6\password */
?>
