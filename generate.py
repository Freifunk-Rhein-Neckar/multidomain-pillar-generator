#!/usr/bin/env python3
from collections import OrderedDict
from ipaddress import ip_network
from math import log
import os
import subprocess
import yaml
import jinja2
from hashlib import sha256

base_vid = 4011

working_dir = os.path.realpath(__file__)
git_rev = subprocess.check_output('git describe --long --all HEAD'.split(' ')).decode('utf-8')

header = 'Generated using https://git.darmstadt.ccc.de/ffda/multidomain-pillar-generator @ {}'.format(git_rev)


# begin config

# setup
gateways = 8
base_gateway = 2

base_domain_id = 1
domain_names = [
    # dom1 - Weinheim
    {'ffrn_69469': "Weinheim"},
    # dom2 - Bergstraße
    {'ffrn_64625': 'Bensheim',
     'ffrn_64646': 'Heppenheim'},
]

# vpn
fastd_port_range = range(10000, 10500)
fastd_peers_groups = ['nodes']

# layer 2
mtu = 1312
nextnode_mac = 'fe:ca:ff:ee:ff:42'

# layer 3
prefix4_rfc1918 = '10.94.0.0/15'
prefix4_defaultlen = 20

prefix6_glob = '2a01:4f8:171:fc00::/58'
prefix6_ula = 'fdc3:67ce:cc7e:9040::/58'

batadv = {
    'hop_penalty': 60,
    'features': {
        'dat': True,
        'mm': True,
    },
    'gw_mode': {
        'enabled': False,
        'uplink': "200mbit",
        'downlink': "200mbit"
    }
}

batadv_gw = {
    'gw_mode': {
        'enabled': True
    }
}

# end config

# begin domain template

domain_template = jinja2.Template("""{
	domain_names = {
		dom{{ domain_id }} = 'Domain {{ domain_id }}',
		{%- for domain_code, domain_name in domain_names.items() %}
		{{ domain_code }} = '{{ domain_name }}'{% if not loop.last %},{% endif %}
		{%- endfor %}
	},
	domain_seed = '{{ domain_seed }}',
	hide_domain = { 'dom{{ domain_id }}' },
	prefix4 = '{{ prefix4 }}',
	prefix6 = '{{ prefix6_ula }}',
	-- extra_prefixes6 = { '{{ prefix6_global }}' },
	next_node = {
		name = { 'nextnode.ffrn.de', 'nextnode' },
		ip4 = '{{ nextnode4 }}',
		ip6 = '{{ nextnode6 }}',
	},
	wifi24 = {
		ap = {
			ssid = "freifunk-rhein-neckar.de",
			owe_ssid = "owe.freifunk-rhein-neckar.de",
			owe_transition_mode = false,
		},
		mesh = {
			id = 'ffrn-mesh-dom{{ domain_id }}',
		},
	},
	wifi5 = {
		ap = {
			ssid = "freifunk-rhein-neckar.de",
			owe_ssid = "freifunk-rhein-neckar.de",
			owe_transition_mode = false,
		},
		mesh = {
			id = 'ffrn-mesh-dom{{ domain_id }}',
		},
	},
	mesh_vpn = {
		fastd = {
			groups = {
				backbone = {
					peers = {
						gw02 = {
							key = '0fdf2eb0707a1fefbc3f73359601db1f6f549cee1f5d9c454ccf0590c956771b',
							remotes = {
								'"gw02.ffrn.de" port {{ fastd_port }}',
							},
						},
						gw03 = {
							key = '5c22137952681ca821d6f9dc711ca1cb94c6ff2b0e46a2aa6c9e90f338fa5593',
							remotes = {
								'"gw03.ffrn.de" port {{ fastd_port }}',
							},
						},
						gw04 = {
							key = '8be4613b63b063fdd6606e02279cac497bf286dd4d31ea0bf886b49ee539802e',
							remotes = {
								'"gw04.ffrn.de" port {{ fastd_port }}',
							},
						},
						gw05 = {
							key = '313f8733fdb3de152c6dfe520a3c70d6cf37a94c7727a7530e6a491ac3920a59',
							remotes = {
								'"gw05.ffrn.de" port {{ fastd_port }}',
							},
						},
						gw06 = {
							key = '2f4770397d2cf1533dcd0ab817d73bad933760c1367d5c85d1367bfbdefc78fd',
							remotes = {
								'"gw06.ffrn.de" port {{ fastd_port }}',
							},
						},
						gw07 = {
							key = '98da8744f0c3597c808b522714a5f34693a2f878338e4b3ec3d1d731e94c6bcc',
							remotes = {
								'"gw07.ffrn.de" port {{ fastd_port }}',
							},
						},
						gw08 = {
							key = '81813900a53dc6483114e804de8b463799da4cda52393eb454a8d15cdacbf289',
							remotes = {
								'"gw08.ffrn.de" port {{ fastd_port }}',
							},
						},
						gw09 = {
							key = '743e20f293de1a00a82b34d64e62363b3c4069ae20051f9847c70c8d2d885207',
							remotes = {
								'"gw09.ffrn.de" port {{ fastd_port }}',
							},
						},
					},
				},
			},
		},
	},
}
""")


# end domain template

try:
    os.makedirs('pillar/groups/domains')
except FileExistsError:
    pass

try:
    os.makedirs('gluon/domains')
except FileExistsError:
    pass

for i in range(gateways):
    i += base_gateway
    try:
        os.makedirs('pillar/host/gw{:02d}/domains'.format(i))
    except FileExistsError:
        pass


ip4_pool = ip_network(prefix4_rfc1918)
ip6_pool_glob = ip_network(prefix6_glob)
ip6_pool_ula = ip_network(prefix6_ula)

ip4_prefixes = ip4_pool.subnets(new_prefix=prefix4_defaultlen)
ip6_prefixes_glob = ip6_pool_glob.subnets(new_prefix=64)
ip6_prefixes_ula = ip6_pool_ula.subnets(new_prefix=64)

gnt_network_cmds = []
gnt_instance_cmds = []

domains = {}
for _id, names in enumerate(domain_names):
    _id += base_domain_id
    _ip6_global_prefix = ip6_prefixes_glob.__next__()
    _ip6_ula_prefix = ip6_prefixes_ula.__next__()
    prefix4_rfc1918 = ip4_prefixes.__next__()

    dhcp_pools = prefix4_rfc1918.subnets(
        new_prefix=prefix4_defaultlen + int(log(gateways, 2)))

    nextnode4 = prefix4_rfc1918[-2]
    nextnode6 = _ip6_ula_prefix[2**16+1]

    vlan_id = base_vid + _id

    gnt_network_cmds.append('gnt-network add --network={network} --mac-prefix=DA:FF:{id:02} dom{id}\n'.format(network=prefix4_rfc1918, id=_id))
    gnt_network_cmds.append('gnt-network connect --nic-parameters=mode=bridged,link=br-vlan{vid} dom{id}\n\n'.format(vid=vlan_id, id=_id))

    with open("gluon/domains/dom{}.conf".format(_id), 'w') as gluon_site_handle:
        context = dict(
            domain_names={
                domain_code.replace('-', '_'): domain_name
                for domain_code, domain_name
                in names.items()
            },
            domain_id=_id,
            domain_seed=sha256(bytes('ffrn-dom{}'.format(_id), 'utf-8')).hexdigest(),
            prefix4=str(prefix4_rfc1918),
            prefix6_ula=str(_ip6_ula_prefix),
            prefix6_global=str(_ip6_global_prefix),
            nextnode4=str(nextnode4),
            nextnode6=str(nextnode6),
            fastd_port=fastd_port_range[_id * 10]
        )
        gluon_site_handle.write(
            domain_template.render(**context)
        )

    with open('pillar/groups/domains/dom{}.sls'.format(_id), 'w') as handle:
        handle.write(yaml.dump({
            '__generator': header,
            'domains': {
                'dom{}'.format(_id): {
                    'domain_id': _id,
                    'domain_names': names,
                    'vlan': vlan_id,
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
                            'network': str(_ip6_ula_prefix.network_address)
                        },
                    },
                    'netrange4': {
                        # the first /29 in each /23 is rsvd for the gateway address and static addressing
                        'static': [str(list(prefix4_rfc1918.subnets(new_prefix=29))[i]) for i in range (0, 512, 64)],
                        'total': str(prefix4_rfc1918)
                    },
                    'dns': {
                        'nameservers4': [
                            str(nextnode4),
                        ],
                        'nameservers6': [
                            str(nextnode6),
                        ],
                        'domain': 'ffrn.de',
                        'search': [
                            'ffrn.de',
                            'freifunk-rhein-neckar.de'
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
        i += base_gateway

        gnt_instance_cmds.append("gnt-instance modify --net add:network=dom{},mac=da:ff:{:02d}:00:{:02d}:05 gw{:02d}\n".format(_id, _id, i, i))

        with open('pillar/host/gw{:02d}/domains/dom{}.sls'.format(i, _id), 'w') as handle:
            handle.write(yaml.dump({
               '__generator': header,
               'domains': {
                    'dom{}'.format(_id): {
                        'ip4': {
                            str(prefix4_rfc1918): {
                                'address': str(pool[1]),
                            },
                        },
                        'dhcp4': {
                            'pools': [
                                {'cidr': str(pool),
                                 # leave the first /29 in the /23 free for gateway and static allocations
                                 'first': str(pool[8]),
                                 # the last pool has to make place for nextnode (254) and broadcast (255) address which are rsvd
                                 'last': str(pool[-3 if i-1 == (gateways - 1) else -1])},
                            ],
                        },
                        'ip6': {
                            str(_ip6_global_prefix): {
                                'address': str(_ip6_global_prefix[i]),
                            },
                            str(_ip6_ula_prefix): {
                                'address': str(_ip6_ula_prefix[i]),
                            },
                        },
                        'batman-adv': batadv_gw
                    }
                }
            }, default_flow_style=False))


# # ganeti networking commands
# with open('ganeti-commands.txt', 'w') as fh:
#     for line in gnt_network_cmds:
#         fh.write(line)
#     for line in gnt_instance_cmds:
#         fh.write(line)

# domain include file
with open('pillar/groups/domains/init.sls', 'w') as handle:
    handle.write(yaml.dump({
        '__generator': header,
        'include': [
            'groups.domains.dom{}'.format(domain_id+base_domain_id)
            for domain_id, _ in enumerate(domain_names)
        ]
    }, default_flow_style=False))

# per host domain include file
for i in range(gateways):
    i += base_gateway
    with open('pillar/host/gw{:02d}/domains/init.sls'.format(i), 'w') as handle:
        handle.write(yaml.dump({
            '__generator': header,
            'include': [
                'host.gw{:02d}.domains.dom{}'.format(i, domain_id+base_domain_id)
                for domain_id, _ in enumerate(domain_names)
            ]
        }, default_flow_style=False))

# # netbox vlan csv
# with open("netbox_vlans.csv", "w") as fh:
#     fh.write("# NetBox VLAN Import\n")
#     fh.write("site,group_name,vid,name,tenant,status,role\n")

#     for _id, names in enumerate(domain_names):
#         vid = base_vid + _id
#         fh.write("S2|02 C303,mesh-batadv,{},dom{},NOC,Active,Mesh (batman-adv)\n".format(vid, _id))
