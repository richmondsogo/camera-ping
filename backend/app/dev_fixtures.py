"""Development and test fixtures for Camera Monitor.

These IP addresses are reserved by RFC 5737 (TEST-NET-1) for documentation
and testing. They are non-production documentation-range addresses and will never
conflict with real camera network addresses. No ping code is implemented yet.
"""

RESERVED_TEST_IPS: list[str] = [
    "192.0.2.10",
    "192.0.2.11",
    "192.0.2.12",
]
