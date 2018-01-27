#!/usr/bin/env python3
import os
import yaml
from ipaddress import ip_network
from math import log

# begin config

# setup
gateways = 8
domain_names = {
    'default': 'Default',
    'da-nord': 'Darmstadt Nord',
    'da-sued': 'Darmstadt Süd',
    'ah-kra-wix': 'Arheilgen, Kranichstein & Wixhauesn',
    'weiterstadt': 'Weiterstadt',
    'gg-nord': 'Groß-Gerau Nord',
    'gg-sued': 'Groß-Gerau Süd',
    'babenhausen': 'Babenhausen',
    'muehltal': 'Mühltal',
    'odenwald': 'Odenwald',
    'da-di-nord': 'Darmstadt-Dieburg Nord',
    'da-di-ost': 'Darmstadt-Dieburg Ost',
    'da-di-sued': 'Darmstadt-Dieburg Süd',
    'offenbach-sued': 'Offenbach Süd',
    'bergstrasse-nord': 'Bergstraße Nord',
    'bergstrasse-sued': 'Bergstraße Süd'
}

sorted_domain_names = sorted(domain_names.keys())

# vpn
fastd_port_range = range(10000, 10500)
fastd_peers_groups = ['nodes']

# layer 2
mtu = 1312

# layer 3
prefix4_rfc1918 = '10.104.0.0/16'
prefix6_glob = '2001:67c:2ed8:1000::/56'
prefix6_ula = 'fd01:67c:2ed8:1000::/56'
prefixlen = 20

batadv = {
    'hop_penalty': 60,
    'features': {
        'dat': True,
        'mm': True,
    },
    'gw_mode': {
        'enabled': False,
        'uplink': "100mbit",
        'downlink': "100mbit"
    }
}

batadv_gw = {
    'gw_mode': {
        'enabled': True
    }
}

# end config

try:
    os.makedirs('pillar/domains')
except FileExistsError:
    pass

for i in range(gateways):
    try:
        os.makedirs('pillar/host/gw{:02d}/domains'.format(i+1))
    except FileExistsError:
        pass


ip4_pool = ip_network(prefix4_rfc1918)
ip6_pool_glob = ip_network(prefix6_glob)
ip6_pool_ula = ip_network(prefix6_ula)

ip4_prefixes = ip4_pool.subnets(new_prefix=prefixlen)
ip6_prefixes_glob = ip6_pool_glob.subnets(new_prefix=64)
ip6_prefixes_ula = ip6_pool_ula.subnets(new_prefix=64)

domains = {}

for _id, domain in enumerate(sorted_domain_names):
    _ip6_global_prefix = ip6_prefixes_glob.__next__()
    _ip6_ula_prefix = ip6_prefixes_ula.__next__()
    prefix4_rfc1918 = ip4_prefixes.__next__()

    dhcp_pools = prefix4_rfc1918.subnets(
        new_prefix=prefixlen + int(log(gateways, 2)))

    nextnode4 = prefix4_rfc1918[-2]
    nextnode6 = _ip6_ula_prefix[2**16+1]

    with open('pillar/domains/{}_{}.sls'.format(_id, domain), 'w') as handle:
        handle.write(yaml.dump({
            'domains': {
                domain: {
                    'domain_id': _id,
                    'domain_name': domain,
                    'domain_pretty': domain_names[domain],
                    'mtu': mtu,
                    'ip4': {
                        str(prefix4_rfc1918): {
                            'prefix': str(prefix4_rfc1918),
                            'prefixlen': int(prefix4_rfc1918.prefixlen),
                            'network': str(prefix4_rfc1918.network_address),
                            'netmask': str(prefix4_rfc1918.netmask)
                        },
                    },
                    'ip6': {
                        str(_ip6_global_prefix): {
                            'prefix': str(_ip6_global_prefix),
                            'prefixlen': int(_ip6_global_prefix.prefixlen),
                            'network': str(_ip6_global_prefix.network_address)
                        },
                        str(_ip6_ula_prefix): {
                            'prefix': str(_ip6_ula_prefix),
                            'prefixlen': int(_ip6_ula_prefix.prefixlen),
                            'network': str(_ip6_global_prefix.network_address)
                        },
                    },
                    'dns': {
                        'nameservers4': [
                            str(nextnode4),
                            '10.223.254.55',
                            '10.223.254.56'
                        ],
                        'nameservers6': [
                            str(nextnode6),
                            'fd01:67c:2ed8:a::55:1',
                            'fd01:67c:2ed8:a::56:1'
                        ],
                        'domain': 'ffda.io',
                        'search': [
                            '{}.ffda.io'.format(domain),
                            'ffda.io',
                            'darmstadt.freifunk.net'
                        ]
                    },
                    'fastd': {
                        'instances': [
                            {
                                'mtu': mtu,
                                'port': fastd_port_range[_id * 10]
                            }
                        ],
                        'peer_groups': fastd_peers_groups
                    },
                    'batman-adv': batadv
                }
            }
        }, default_flow_style=False))

    for i, pool in enumerate(dhcp_pools):
        with open('pillar/host/gw{:02d}/domains/{}_{}.sls'.format(i+1, _id, domain), 'w') as handle:
            handle.write(yaml.dump({
                'domains': {
                    domain: {
                        'ip4': {
                            str(prefix4_rfc1918): {
                                'address': str(pool[1]),
                            },
                        },
                        'dhcp4': {
                            'pools': [
                                {'cidr': str(pool),
                                 'first': str(pool[2]),
                                 # last pool has to make place for nextnode
                                 # and broadcast address and 12 few free ips
                                 # per pool (possibly statics)
                                 'last': str(pool[-13-3 if i == (gateways - 1) else -13-1])},
                            ],
                        },
                        'ip6': {
                            str(_ip6_global_prefix): {
                                'address': str(_ip6_global_prefix[i + 1]),
                            },
                            str(_ip6_ula_prefix): {
                                'address': str(_ip6_ula_prefix[i + 1]),
                            },
                        },
                        'batman-adv': batadv_gw
                    }
                }
            }, default_flow_style=False))


# domain include file
with open('pillar/domains/init.sls', 'w') as handle:
    handle.write(yaml.dump({
        'include': [
            'domains.{}_{}'.format(domain_id, domain_name)
            for domain_id, domain_name in enumerate(sorted_domain_names)
        ]
    }, default_flow_style=False))

# per host domain include file
for i in range(gateways):
    with open('pillar/host/gw{:02d}/domains/init.sls'.format(i+1), 'w') as handle:
        handle.write(yaml.dump({
            'include': [
                'host.gw{:02d}.domains.{}_{}'.format(i+1, domain_id, domain_name)
                for domain_id, domain_name in enumerate(sorted_domain_names)
            ]
        }, default_flow_style=False))

# netbox vlan csv
base_vid = 200

print("# NetBox VLAN Import")
print("site,group_name,vid,name,tenant,status,role,description")
for domain_id, domain_name in enumerate(sorted(domain_names.keys())):
    print("S2|02 C303,mesh-batadv,{},{},NOC,Active,Mesh (batman-adv),\"{}\"".format(
        base_vid + domain_id, domain_name, domain_names[domain_name]))
