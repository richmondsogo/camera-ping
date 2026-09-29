import ipaddress

from app.dev_fixtures import RESERVED_TEST_IPS

TEST_NET_1 = ipaddress.ip_network("192.0.2.0/24")


def test_reserved_test_ips_are_in_rfc5737_range() -> None:
    assert len(RESERVED_TEST_IPS) == 3
    for ip_str in RESERVED_TEST_IPS:
        ip = ipaddress.ip_address(ip_str)
        assert ip in TEST_NET_1, (
            f"{ip_str} is not within RFC 5737 TEST-NET-1 (192.0.2.0/24)"
        )
