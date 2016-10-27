#!/usr/bin/env python3
# encoding: utf-8
import hashlib
import logging
import config
from confluence import Confluence
from prettytable import from_html
from bs4 import BeautifulSoup
import IPy
from subprocess import Popen, PIPE

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')
logger = logging.getLogger()

import json


PERSISTENT_HASH_FILE = '/opt/confluence-dns/update.hash'

class DNSUpdaterNG(object):
    def __init__(self, base_url, username, password, page_id, verify_ssl=True):
        self.page_id = page_id
        self.c = Confluence(base_url, username, password, verify_ssl=verify_ssl)

    def update(self):
        page = self.c.get_page(self.page_id)
        if not page:
            raise Exception("Failed to fetch confluence page")
        data = BeautifulSoup(page, "lxml")
        stored_hash = None
        page_hash = hashlib.sha512(page.encode('ascii', errors='ignore')).hexdigest()
        try:
            hf = open(PERSISTENT_HASH_FILE)
            stored_hash = hf.read()
            hf.close()
        except:
            pass
        if stored_hash == page_hash:
            logger.info('equality via hash, no-op')
            return
        else:
            hf = open(PERSISTENT_HASH_FILE, 'w')
            hf.write(page_hash)
            hf.close()
        logger.info('updating DNS')
        addrtables = self._locate_addrtables(data)
        addrtable_data = []
        for addrtable in addrtables:
            for addrtable_info in self._parse_addrtable(addrtable):
                addrtable_data.append(addrtable_info)
        zone_updates = self._build_batch_update(addrtable_data)
        self._update_all_zones(zone_updates)
        logger.info('all done')

    def _update_all_zones(self, zone_updates):
        commands = []
        for zonename in zone_updates.keys():
            commands.append('server 127.1')
            commands.append('zone %s' % (zonename))
            updates = zone_updates[zonename]
            for update in updates:
                commands.append('update delete %s' % (update[0]))
                commands.append('update add %s' % (update[1]))
            commands.append('send')
            cmd_out = '\n'.join(commands).encode('ascii', errors='ignore')
            logger.debug(cmd_out.decode("ascii"))
            p = Popen(['nsupdate'], stdout=PIPE, stdin=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate(input=cmd_out)[0:2]
            ser = stderr.decode('ascii', errors='ignore')
            if ser.strip() != '':
                logger.error("%s: %s" % (zonename, ser.strip()))
            commands = []

    def _build_batch_update(self, addrtable_data):
        zone_updates = {}
        for item in addrtable_data:
            zi = item['_zoneinfo']
            if zi['dns_zone'] != '-' and zi['dns_zone'] not in zone_updates:
                zone_updates[zi['dns_zone']] = []
            if zi['dns_reverse4'] != '-' and zi['dns_reverse4'] not in zone_updates:
                zone_updates[zi['dns_reverse4']] = []
            if zi['dns_reverse6'] != '-' and zi['dns_reverse6'] not in zone_updates:
                zone_updates[zi['dns_reverse6']] = []
            if item['Name'] == '':
                continue
            if item['A'] != '':
                if zi['dns_zone'] != '-':
                    zone_updates[zi['dns_zone']].append([
                        "%s.%s. A" % (item['Name'], zi['dns_suffix']),
                        "%s.%s. 60 A %s" % (item['Name'], zi['dns_suffix'], item['A'])
                    ])
                if zi['dns_reverse4'] != '-':
                    this_reverse = IPy.IP(item['A']).reverseNames()[0]
                    if this_reverse.endswith(zi['dns_reverse4']):
                        zone_updates[zi['dns_reverse4']].append([
                            "%s PTR" % (IPy.IP(item['A']).reverseNames()[0]),
                            "%s 60 PTR %s.%s." % (IPy.IP(item['A']).reverseNames()[0], item['Name'], zi['dns_suffix'])
                        ])
                    else:
                        logger.error("IP address %s don't match reverse %s" % (item['A'], zi['dns_reverse4']))
            if item['AAAA'] != '':
                ipv6 = item['AAAA']
                if '/' in ipv6:
                    ipv6, crap = ipv6.split('/',1)
                if zi['dns_zone'] != '-':
                    zone_updates[zi['dns_zone']].append([
                        "%s.%s. AAAA" % (item['Name'], zi['dns_suffix']),
                        "%s.%s. 60 AAAA %s" % (item['Name'], zi['dns_suffix'], ipv6)
                    ])
                if zi['dns_reverse6'] != '-':
                    this_reverse = IPy.IP(ipv6).reverseNames()[0]
                    if this_reverse.endswith(zi['dns_reverse6']):
                        zone_updates[zi['dns_reverse6']].append([
                            "%s PTR" % (IPy.IP(ipv6).reverseNames()[0]),
                            "%s 60 PTR %s.%s." % (IPy.IP(ipv6).reverseNames()[0], item['Name'], zi['dns_suffix'])
                        ])
                    else:
                        logger.error("IPv6 address %s don't match reverse %s" % (ipv6, zi['dns_reverse6']))
            for cname in item['CNAME']:
                zone_updates[zi['dns_zone']].append([
                    "%s 60 CNAME" % (cname),
                    "%s 60 CNAME %s.%s." % (cname, item['Name'], zi['dns_suffix'])
                ])
            for srv in item['SRV']:
                srv_components = srv.split(':')
                if len(srv_components) != 2:
                    continue
                srv_desc, srv_port = srv_components
                zone_updates[zi['dns_zone']].append([
                    "%s.%s SRV 0 0 %s %s.%s." % (srv_desc, zi['dns_zone'], srv_port, item['Name'], zi['dns_suffix']),
                    "%s.%s 60 SRV 0 0 %s %s.%s." % (srv_desc, zi['dns_zone'], srv_port, item['Name'], zi['dns_suffix'])
                ])
        for zone, data in zone_updates.items():
            for item in data:
                logger.debug("%s" % (item,))
        return zone_updates

    def _parse_addrtable(self, addrtable):
        ret = []
        dns_suffix = None
        dns_zone = None
        dns_reverse4 = None
        dns_reverse6 = None
        keys = []
        for row in addrtable.find_all('tr'):
            rowcells = []
            if row.find('th'):
                for cell in row.find_all('th'):
                    keys.append(cell.getText())
                continue
            for cell in row.find_all('td'):
                plaintext = cell.getText()
                if plaintext.startswith('$'):
                    argv = plaintext.strip('$').split(' ', 1)
                    dnsgen_command = argv[0]
                    if dnsgen_command == 'DNSGEN-ADDRTABLE':
                        pass
                    elif dnsgen_command == 'DNSGEN-SUBZONE' and len(argv) > 1:
                        args = argv[1].split(' ')
                        if len(args) != 4:
                            break
                        dns_suffix, dns_zone, dns_reverse4, dns_reverse6 = args
                    break
                else:
                    rowcells.append(plaintext.replace('\xa0', ' ').strip())
            if len(rowcells) == 0:
                continue
            rowdata = dict(zip(keys, rowcells))
            if rowdata['CNAME'] == '':
                 rowdata['CNAME'] = []
            else:
                 rowdata['CNAME'] = rowdata['CNAME'].split()
            if rowdata['SRV'] == '':
                 rowdata['SRV'] = []
            else:
                 rowdata['SRV'] = rowdata['SRV'].split(' ')
            rowdata['_zoneinfo'] = {
                'dns_zone': dns_zone,
                'dns_suffix': dns_suffix,
                'dns_reverse4': dns_reverse4,
                'dns_reverse6': dns_reverse6
            }
            ret.append(rowdata)
        return ret

    def _locate_addrtables(self, bs_data):
        ret = []
        tbls = bs_data.find_all('table')
        for tbl in tbls:
            try:
                first_td = tbl.find('td')
                if first_td is not None:
                    hint = first_td.next_element.getText()
                    if hint == '$DNSGEN-ADDRTABLE':
                        ret.append(tbl)
                        return ret
            except:
                pass

if __name__ == '__main__':
    d = DNSUpdaterNG(config.base_url, config.username, config.password, config.page_id, config.verify_ssl)
    d.update()

