#!/usr/bin/env python3
from collections import OrderedDict
from ipaddress import ip_network
from math import log
import os
import subprocess
import yaml
import jinja2
from hashlib import sha256

base_vid = 200

working_dir = os.path.realpath(__file__)
git_rev = subprocess.check_output('git describe --long --all HEAD'.split(' ')).decode('utf-8')

header = 'Generated using https://git.darmstadt.ccc.de/ffda/multidomain-pillar-generator @ {}'.format(git_rev)


# begin config

# setup
gateways = 8

domain_names = [
    # dom0
    {'ffda_default': "Default"},
    # dom1
    {'ffda_da_110': 'Darmstadt: Stadtzentrum',
     'ffda_da_120': 'Darmstadt: Mollerstadt',
     'ffda_da_130': 'Darmstadt: Hochschulviertel',
     'ffda_da_210': 'Darmstadt: Johannesviertel',
     'ffda_da_220_230': 'Darmstadt: Martinsviertel',
     'ffda_da_270': 'Darmstadt: Bürgerparkviertel',
     'ffda_da_310': 'Darmstadt: Am Oberfeld',
     'ffda_da_320': 'Darmstadt: Mathildenhöhe'},
    # dom2
    {'ffda_da_240': 'Darmstadt: Waldkolonie',
     'ffda_da_250': 'Darmstadt: Mornewegviertel',
     'ffda_da_260': 'Darmstadt: Pallaswiesenviertel',
     'ffda_da_530': 'Darmstadt: Verlegerviertel',
     'ffda_da_540': 'Darmstadt: Am Kavalleriesand'},
    # dom3
    {'ffda_da_140': 'Darmstadt: Kapellplatzviertel',
     'ffda_da_150': 'Darmstadt: St. Ludwig mit Eichbergviertel',
     'ffda_da_330': 'Darmstadt: Woogsviertel',
     'ffda_da_340': 'Darmstadt: An den Lichtwiesen',
     'ffda_da_410': 'Darmstadt: Paulusviertel',
     'ffda_da_420': 'Darmstadt: Alt-Bessungen'},
    # dom4
    {'ffda_da_430': 'Darmstadt: An der Ludwigshöhe',
     'ffda_da_440': 'Darmstadt: Lincoln-Siedlung',
     'ffda_da_510': 'Darmstadt: Am Südbahnhof',
     'ffda_da_520': 'Darmstadt: Heimstättensiedlung'},
    # dom5
    {'ffda_da_610_620_630': 'Darmstadt: Arheilgen',
     'ffda_da_910_920': 'Darmstadt: Kranichstein',
     'ffda_da_810_820': 'Darmstadt: Wixhausen',
     'ffda_64390': 'Erzhausen'},
    # dom6
    {'ffda_64521': 'Groß-Gerau',
     'ffda_64546': 'Mörfelden-Walldorf',
     'ffda_64572': 'Büttelborn',
     'ffda_64569': 'Nauheim'},
    # dom7
    {'ffda_64579': 'Gernsheim',
     'ffda_64560': 'Riedstadt',
     'ffda_64589': 'Stockstadt am Rhein',
     'ffda_64584': 'Biebesheim am Rhein'},
    # dom8
    {'ffda_64832': 'Babenhausen (Hessen)'},
    # dom9
    {'ffda_64347': 'Griesheim',
     'ffda_64331': 'Weiterstadt'},
    # dom10
    {'ffda_64807': 'Dieburg',
     'ffda_64409': 'Messel',
     'ffda_64839': 'Münster (Hessen)',
     'ffda_64859': 'Eppertshausen'},
    # dom11
    {'ffda_64846': 'Groß-Zimmern',
     'ffda_64380': 'Roßdorf (bei Darmstadt)',
     'ffda_64354': 'Reinheim',
     'ffda_64401': 'Groß-Bieberau'},
    # dom12
    {'ffda_64853': 'Otzberg',
     'ffda_64823': 'Groß-Umstadt',
     'ffda_64850': 'Schaafheim'},
    # dom13
    {'ffda_64297': 'Darmstadt-Eberstadt',
     'ffda_64342': 'Seeheim-Jugenheim',
     'ffda_64665': 'Alsbach-Hähnlein',
     'ffda_64319': 'Pfungstadt',
     'ffda_64404': 'Bickenbach',
     'ffda_64673': 'Zwingenberg'},
    # dom14
    {'ffda_64372': 'Ober-Ramstadt',
     'ffda_64397': 'Modautal',
     'ffda_64367': 'Mühltal',
     'ffda_64405': 'Fischbachtal'},
    # dom15
    {'ffda_63303': 'Dreieich',
     'ffda_63225': 'Langen',
     'ffda_63329': 'Egelsbach'},
    # dom16
    {'ffda_63128': 'Dietzenbach',
     'ffda_63110': 'Rodgau',
     'ffda_63322': 'Rödermark',
     'ffda_63500': 'Seligenstadt',
     'ffda_63533': 'Mainhausen'},
    # dom17
    {'ffda_64732': 'Bad König',
     'ffda_64747': 'Breuberg',
     'ffda_64711': 'Erbach',
     'ffda_64720': 'Michelstadt',
     'ffda_64395': 'Brensbach',
     'ffda_64753': 'Brombachtal',
     'ffda_64407': 'Fränkisch-Crumbach',
     'ffda_64739': 'Höchst im Odenwald',
     'ffda_64750': 'Lützelbach',
     'ffda_64756': 'Mossautal',
     'ffda_64385': 'Reichelsheim (Odenwald)'},
]

# vpn
fastd_port_range = range(10000, 10500)
fastd_peers_groups = ['nodes']

# layer 2
mtu = 1312

# layer 3
prefix4_rfc1918 = '10.84.0.0/15'
prefix4_defaultlen = 20

prefix6_glob = '2001:67c:2ed8:1000::/56'
prefix6_ula = 'fd01:67c:2ed8:1000::/56'

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
	extra_prefixes6 = { '{{ prefix6_global }}' },

	next_node = {
		name = { 'nextnode.ffda.io', 'nextnode' },
		ip4 = '{{ nextnode4 }}',
		ip6 = '{{ nextnode6 }}',
		mac = '{{ nextnode_mac }}',
	},

	wifi24 = {
		ap = {
			ssid = "darmstadt.freifunk.net",
		},
		mesh = {
			id = 'ffda-mesh-dom{{ domain_id }}',
		},
	},
	wifi5 = {
		ap = {
			ssid = "darmstadt.freifunk.net",
		},
		mesh = {
			id = 'ffda-mesh-dom{{ domain_id }}',
		},
	},

	mesh_vpn = {
		fastd = {
			groups = {
				backbone = {
					peers = {
						gw01 = {
							key = 'e04a2e54f873876ea2fc50973f85743daee7878c1872f905c94b12371fea3b9d',
							remotes = {
								'"gw01.darmstadt.freifunk.net" port {{ fastd_port }}',
								'[2001:67c:2ed8::40:1] port {{ fastd_port }}',
								'82.195.73.40 port {{ fastd_port }}',
							},
						},
						gw02 = {
							key = 'def654cd1a37ac86dd38f2a60e6cf40bdc23a4ac8232d4be4903c4078c18518e',
							remotes = {
								'"gw02.darmstadt.freifunk.net" port {{ fastd_port }}',
								'[2001:67c:2ed8::41:1] port {{ fastd_port }}',
								'82.195.73.41 port {{ fastd_port }}',
							},
						},
						gw03 = {
							key = 'f96ca591b5df2a1c2e9f238ae131a374053e32ce492afa4c9a6765ac53b49cc4',
							remotes = {
								'"gw03.darmstadt.freifunk.net" port {{ fastd_port }}',
								'[2001:67c:2ed8::42:1] port {{ fastd_port }}',
								'82.195.73.42 port {{ fastd_port }}',
							},
						},
						gw04 = {
							key = 'cd89e3420d1e4b57ca5a75b6aa3afcde846c8bbf87286bb6405ad75e3d3bfe3e',
							remotes = {
								'"gw04.darmstadt.freifunk.net" port {{ fastd_port }}',
							},
						},
						gw05 = {
							key = 'b39fc4fecabc6d418baf05fb3f4b08c3a2f79eba5ccd94027a93726a037f99bb',
							remotes = {
								'"gw05.darmstadt.freifunk.net" port {{ fastd_port }}',
								'[2001:67c:2ed8::44:1] port {{ fastd_port }}',
								'82.195.73.44 port {{ fastd_port }}',
							},
						},
						gw06 = {
							key = '975c523c6bda7b20234dd3ca260ed3bf7dbcbb0510159062a27e9081822a4973',
							remotes = {
								'"gw06.darmstadt.freifunk.net" port {{ fastd_port }}',
								'[2001:67c:2ed8::45:1] port {{ fastd_port }}',
								'82.195.73.45 port {{ fastd_port }}',
							},
						},
						gw07 = {
							key = '7f7cc68bb1b75e30ad7472159bd2b3b481378c27ea0687679d85d8a28aedf0c7',
							remotes = {
								'"gw07.darmstadt.freifunk.net" port {{ fastd_port }}',
								'[2001:67c:2ed8::46:1] port {{ fastd_port }}',
								'82.195.73.46 port {{ fastd_port }}',
							},
						},
						gw08 = {
							key = '818a2192858dc8e71f1bbfaa9da1fb394cb9077dfad9e3cfa79280ad248cb0d5',
							remotes = {
								'"gw08.darmstadt.freifunk.net" port {{ fastd_port }}',
								'[2001:67c:2ed8::47:1] port {{ fastd_port }}',
								'82.195.73.47 port {{ fastd_port }}',
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
    os.makedirs('pillar/domains')
except FileExistsError:
    pass

try:
    os.makedirs('gluon/domains')
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

ip4_prefixes = ip4_pool.subnets(new_prefix=prefix4_defaultlen)
ip6_prefixes_glob = ip6_pool_glob.subnets(new_prefix=64)
ip6_prefixes_ula = ip6_pool_ula.subnets(new_prefix=64)

gnt_network_cmds = []
gnt_instance_cmds = []

domains = {}
for _id, names in enumerate(domain_names):
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
            domain_seed=sha256(bytes('ffda-dom{}'.format(_id), 'utf-8')).hexdigest(),
            prefix4=str(prefix4_rfc1918),
            prefix6_ula=str(_ip6_ula_prefix),
            prefix6_global=str(_ip6_global_prefix),
            nextnode4=str(nextnode4),
            nextnode6=str(nextnode6),
            nextnode_mac="da:ff:{:02d}:00:ff:ff".format(_id),
            fastd_port=fastd_port_range[_id * 10]
        )
        gluon_site_handle.write(
            domain_template.render(**context)
        )

    with open('pillar/domains/dom{}.sls'.format(_id), 'w') as handle:
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
                            'network': str(_ip6_global_prefix.network_address)
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
                        'domain': 'ffda.io',
                        'search': [
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
        gnt_instance_cmds.append("gnt-instance modify --net add:network=dom{},mac=da:ff:{:02d}:00:{:02d}:05 gw{:02d}\n".format(_id, _id, i+1, i+1))

        with open('pillar/host/gw{:02d}/domains/dom{}.sls'.format(i+1, _id), 'w') as handle:
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
                                 'last': str(pool[-3 if i == (gateways - 1) else -1])},
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


# ganeti networking commands
with open('ganeti-commands.txt', 'w') as fh:
    for line in gnt_network_cmds:
        fh.write(line)
    for line in gnt_instance_cmds:
        fh.write(line)

# domain include file
with open('pillar/domains/init.sls', 'w') as handle:
    handle.write(yaml.dump({
        '__generator': header,
        'include': [
            'domains.dom{}'.format(domain_id)
            for domain_id, _ in enumerate(domain_names)
        ]
    }, default_flow_style=False))

# per host domain include file
for i in range(gateways):
    with open('pillar/host/gw{:02d}/domains/init.sls'.format(i+1), 'w') as handle:
        handle.write(yaml.dump({
            '__generator': header,
            'include': [
                'host.gw{:02d}.domains.dom{}'.format(i+1, domain_id)
                for domain_id, _ in enumerate(domain_names)
            ]
        }, default_flow_style=False))

# netbox vlan csv
with open("netbox_vlans.csv", "w") as fh:
    fh.write("# NetBox VLAN Import\n")
    fh.write("site,group_name,vid,name,tenant,status,role\n")

    for _id, names in enumerate(domain_names):
        vid = base_vid + _id
        fh.write("S2|02 C303,mesh-batadv,{},dom{},NOC,Active,Mesh (batman-adv)\n".format(vid, _id))
