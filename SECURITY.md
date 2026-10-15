# Security Policy

## Supported Versions

| Version | Supported |
| :--- | :--- |
| 0.9.x | Yes |
| < 0.9.0 | No |

---

## Security Model & Boundary Architecture

Camera Monitor is intentionally designed as a **local administration utility** for an offline or air-gapped Windows host PC:

1. **Loopback-Only Binding**: In both development and production, the service binds exclusively to IPv4 loopback (`127.0.0.1`). Non-loopback addresses are rejected at startup with exit code 2.
2. **No Authentication Layer**: Because it is intended solely for single-operator local use on loopback, Camera Monitor does not implement user accounts, logins, or role-based access control.
3. **No External Network Exposure**:
   > [!CAUTION]
   > Camera Monitor **must not** be exposed to an external network, local area network (LAN), or the public internet via reverse proxies, port forwarding, or SSH tunnels. Exposing this application to an untrusted network allows unauthorized access to camera inventory management and ICMP probing controls.
4. **Header and Origin Hardening**:
   - The production server enforces strict `Host` header checks, rejecting any requests where the `Host` header does not match `127.0.0.1` or `localhost`.
   - Mutating HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`) require loopback `Origin` headers to protect against cross-site request forgery (CSRF) from local browsers.
   - All HTTP responses include protective headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: no-referrer`.
5. **No Camera Credentials**:
   - The application does not store, request, or handle camera passwords, API tokens, or RTSP stream credentials. It interacts with cameras strictly via ICMP echo requests (ping).

---

## Reporting a Vulnerability

If you discover a security vulnerability or security boundary bypass in Camera Monitor:

- Please use **GitHub's private vulnerability reporting** feature on this repository (located under the **Security** tab, once enabled).
- **Do not open a public issue or discussion** for undisclosed security vulnerabilities.

Include in your report:
- A description of the vulnerability and its potential impact.
- Step-by-step reproduction instructions or a minimal proof of concept.
- The operating system and version of Camera Monitor tested.

We will review reports promptly and publish fixes in a coordinated security advisory.
