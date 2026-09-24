# Security and PII

The generator creates clearly fake PII using reserved values (`example.test`, `192.0.2.0/24`, synthetic names and 555 phones). It exists only to demonstrate safe handling.

Before warehouse load, email is trimmed/case-folded and phone is canonicalized. Identifiers use HMAC-SHA256 with `PII_HMAC_SECRET`; plain unsalted SHA256 and base64 are not protection. If reversible storage is required, the complete PII object is encrypted with Fernet authenticated encryption using `PII_ENCRYPTION_KEY`. Without that key the raw values are dropped, which is the preferred analytical behavior.

Quarantine payloads redact `name`, `email`, `phone`, and `ip_address`. Core and marts expose anonymous/user business IDs only. Automated tests inspect mart schemas for forbidden columns and verify encryption/tamper handling.

`security/roles.sql` defines least-privilege roles: ETL writes all pipeline layers; analysts read core/marts but not raw; BI reads marts only; admin manages all schemas. Login creation and passwords are deliberately out-of-band. `.env` is ignored; `.env.example` contains placeholders only.

Trade-off: HMAC remains linkable within the environment and secret rotation changes identifiers, so a production migration needs key versioning and controlled re-keying. Fernet centralizes encryption but key custody, KMS integration, audit logs, and deletion workflows are outside this synthetic project.
