# Security Deep-Dive — OWASP Top 10 Focused Review

When `--security` is active, review the code against ALL 10 OWASP categories below in addition to the standard checklist. This is a thorough security audit, not a surface scan.

## OWASP Top 10 (2021) Checklist

### A01: Broken Access Control
- Missing authorization checks on endpoints/functions
- Insecure direct object references (IDOR) — can user A access user B's data by changing an ID?
- Missing function-level access control (admin endpoints accessible to regular users)
- CORS misconfiguration allowing unintended origins
- Path traversal vulnerabilities (e.g., `../../etc/passwd` in file paths)
- Missing `rel="noopener"` on external links (minor but flag it)

### A02: Cryptographic Failures
- Sensitive data transmitted without encryption (HTTP instead of HTTPS)
- Weak hashing algorithms (MD5, SHA1 for passwords)
- Hardcoded secrets, API keys, passwords, or tokens in source code
- Missing encryption at rest for sensitive data
- Weak random number generation (Math.random() for security purposes)
- Expired or self-signed certificates in config

### A03: Injection
- **SQL injection** — string concatenation in queries instead of parameterized queries
- **XSS** — unescaped user input rendered in HTML/templates
- **Command injection** — user input passed to shell commands (`exec`, `system`, `child_process`)
- **LDAP injection** — user input in LDAP queries
- **Template injection** — user input in server-side template rendering
- **Header injection** — user input in HTTP headers (CRLF injection)
- Check all user input paths from entry point to where they're consumed

### A04: Insecure Design
- Missing rate limiting on authentication or sensitive endpoints
- Missing account lockout after failed login attempts
- Business logic flaws (e.g., negative quantities in cart, skipping payment steps)
- Missing CAPTCHA or bot protection on public forms
- Insufficient anti-automation on sensitive operations

### A05: Security Misconfiguration
- Debug mode enabled in production config
- Default credentials or example secrets in config files
- Overly permissive CORS, CSP, or security headers
- Stack traces or verbose errors exposed to users
- Unnecessary features/ports/services enabled
- Missing security headers (X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security)

### A06: Vulnerable and Outdated Components
- Known vulnerable dependency versions (check against major CVE databases)
- Unmaintained dependencies (no updates in >2 years)
- Dependencies with known security advisories
- Using `*` or overly broad version ranges in dependency files

### A07: Identification and Authentication Failures
- Weak password policies (no minimum length, no complexity)
- Missing multi-factor authentication for sensitive operations
- Session tokens in URLs
- Sessions not invalidated on logout
- Missing session timeout
- Credential stuffing vulnerabilities (no rate limiting on login)

### A08: Software and Data Integrity Failures
- Missing integrity checks on downloaded resources (no SRI hashes)
- Insecure deserialization (deserializing untrusted data)
- Missing signature verification on updates or plugins
- CI/CD pipeline vulnerabilities (unprotected build scripts)

### A09: Security Logging and Monitoring Failures
- Missing logging for authentication events (login, logout, failed attempts)
- Missing logging for authorization failures
- Sensitive data in logs (passwords, tokens, PII)
- No alerting mechanism for suspicious activity
- Log injection vulnerabilities

### A10: Server-Side Request Forgery (SSRF)
- User-supplied URLs fetched by the server without validation
- Missing URL allowlists/blocklists for server-side requests
- Internal network access possible through URL parameters
- DNS rebinding vulnerabilities

---

## How to Review

1. **Trace all user input paths** — from HTTP request/form/API to where the data is used
2. **Check every boundary** — authentication, authorization, validation at each layer
3. **Look for trust assumptions** — where does the code assume input is safe?
4. **Check secrets management** — grep for hardcoded keys, tokens, passwords
5. **Review dependency security** — check for known vulnerabilities

## Severity Mapping

| OWASP Category | Default Severity |
|----------------|-----------------|
| A01-A03 (Access, Crypto, Injection) | **Critical** |
| A04-A05 (Design, Misconfig) | **Important** |
| A06-A07 (Components, Auth) | **Important** (Critical if actively exploitable) |
| A08-A10 (Integrity, Logging, SSRF) | **Important** |

Override default severity based on actual exploitability and blast radius in context.
