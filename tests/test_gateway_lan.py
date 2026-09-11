"""desk.gateway.lan：从 ifconfig 输出挑局域网地址，排除隧道/CGNAT（J8/J19）。"""
from desk.gateway.lan import lan_candidates, pick_lan_host

SAMPLE = """lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
\tinet 127.0.0.1 netmask 0xff000000
utun8: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1350
\tinet 100.64.100.6 --> 100.64.100.5 netmask 0xffffffff
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet 192.168.31.68 netmask 0xffffff00 broadcast 192.168.31.255
bridge100: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet 10.37.129.2 netmask 0xffffff00 broadcast 10.37.129.255
"""


def test_tunnel_and_loopback_are_never_offered():
    assert "100.64.100.6" not in lan_candidates(SAMPLE)
    assert "127.0.0.1" not in lan_candidates(SAMPLE)


def test_real_lan_interface_wins():
    assert pick_lan_host(SAMPLE) == "192.168.31.68"


def test_candidates_keep_every_usable_address_in_preference_order():
    assert lan_candidates(SAMPLE) == ["192.168.31.68", "10.37.129.2"]


def test_no_usable_interface_returns_none():
    assert pick_lan_host("lo0:\n\tinet 127.0.0.1 netmask 0xff000000\n") is None
