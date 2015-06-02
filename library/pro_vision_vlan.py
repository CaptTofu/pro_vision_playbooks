#!/usr/bin/python
#coding: utf-8 -*-

# (c) 2015, Patrick Galbraith <patg@patg.net>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: pro_vision_vlan
version_added: 0.1
author: Patrick Galbraith
short_description: Basic management of Pro Vision-based HP Switches
requirements: [ pro_vision_ansible (http://code.patg.net/pro_vision.tar.gz)]
description:
    - Create, modify, and delete VLANs on Pro Vision-based Switches
options:
    state:
        required: false
        choices: [ present, absent ]
        default: present
        description:
            - State of VLAN
    save:
        required: false
        default: false
        choices: [ false, true ]
        description:
            - if true, ensures startup config is the same as running config (persists reboot)
    startup_cfg:
        required: false
        default: startup.cfg
        description:
            - The name of the save startup config file when save or reboot
    host:
        required: true
        default: empty
        description:
            - host/ip of switch
    username:
        required: true
        default: empty
        description:
            - username to connect to switch as
    password:
        required: true
        default: empty
        description:
            - password to connect switch with
    timeout:
        required: false
        default: 30
        description:
            - How long to wait for switch to respond
    name:
        required: true
        default: Must be set to valid name
        description:
            - Canonical name of VLAN
    id:
        required: true
        default: Must be a valid numeric ID
        description:
            - ID of VLAN
    tagged:
        required: false
        default: None
        description:
            - List of tagged ports e.g. 1-5,6,7,10
    untagged:
        required: false
        default: None
        description:
            - List of untagged ports e.g. 1-5,6,7,10
'''

EXAMPLES = '''

# file: switch_vlan.yml
- hosts: localhost
  tasks:
  - name: set switch in developer mode
    local_action:
      module: pro_vision_vlan
      developer-mode: true
      host: 192.168.1.100
      username: operator
      password: ckrit
      state: present
      save: true
      name: VLAN 11
      id: 11
      ipv4:
        - 192.168.3.1/255.255.255.0
        - 192.168.4.1/255.255.255.0
      tagged: 1-10
      untagged: 11,13,14-17

OR

- hosts: localhost
  tasks:
  - name: create VLAN 11
    pro_vision_vlan: host=192.168.1.100 username=operator password=ckrit state=present vlan_name="VLAN 11" vlan_id=11 pv4=192.168.3.1/255.255.255.0,192.168.4.1/255.255.255.0 tagged=1-10 untagged=11,13,14-17

'''

from pro_vision_ansible import ProVision
from ansible.module_utils.basic import *

import pprint
pp = pprint.PrettyPrinter(indent=4)

l = open('/tmp/pro_vision_vlan.log', 'wb')

class ProVisionVlan(ProVision):
    def dispatch(self):
        l.write("dispatch()\n")
        l.flush()
        facts = self.handle_vlan()
        return facts

    def handle_vlan(self):
        l.write("handle_vlan()\n")
        l.flush()
        facts = self.get_facts()
        l.write("%s\n" % pp.pformat(facts))
        l.flush()
        state = self.module.params.get('state')
        l.write("state: %s\n" % state)
        l.flush()
        vlan = {'vlan_id': self.module.params.get('vlan_id'),
                'vlan_name': self.module.params.get('vlan_name'),
                'ipv4': self.module.params.get('ipv4'),
                'tagged': self.module.params.get('tagged'),
                'untagged': self.module.params.get('untagged'),
                'state': self.module.params.get('state') }

        if vlan['tagged'] is not None:
            vlan['tagged'] = self._cleanup_port_listing(vlan['tagged'])
        if vlan['untagged'] is not None:
            vlan['untagged'] = self._cleanup_port_listing(vlan['untagged'])

        l.write("vlan: %s\n" % pp.pformat(vlan))
        l.flush()

        if vlan['state'] == 'absent':
            l.write("call delete_vlan()\n")
            facts = self.delete_vlan(facts, vlan['vlan_id'])
        else:
            l.write("call save_vlan()\n")
            facts = self.save_vlan(facts, vlan)

        # After adding or deleting vlan, save
        if self.module.params.get('save') is True:
            self.save()
        return facts

    def vlan_changed(self, facts, vlan):
        l.write("vlan_changed()\n")
        vlan_id = str(vlan['vlan_id'])
        if vlan_id not in facts['running']['vlans']:
            return False
        existing_vlan = facts['running']['vlans'][vlan_id]
        l.write("existing_vlan %s\n" % pp.pformat(existing_vlan))
        l.flush()
        for key in ('vlan_name', 'tagged', 'untagged'):
            l.write("checking key %s\n" % key)
            l.flush()
            if key in vlan and key in existing_vlan:
               if vlan[key] != existing_vlan[key]:
                   l.write("key: %s %s != %s\n" % (key, vlan[key], existing_vlan[key]))
                   l.flush()
                   return True
            else:
                l.write("key: %s not in vlan or existing_vlan\n")
                l.flush()
                return True
            l.write("done checking key %s\n" % key)
            l.flush()

        # if the list of IPs changed...
        if len(vlan['ipv4']) != len(existing_vlan['ipv4']):
            l.write("ipv4 %s != %s\n", (vlan['ipv4'], existing_vlan['ipv4']))
            l.flush()
            return True
        if len(vlan['ipv4']):
            for ip in vlan['ipv4']:
                if ip not in existing_vlan['ipv4']:
                    l.write("ipv4 %s in vlan but not in existing_vlan\n", ip)
                    l.flush()
                    return True
        if len(existing_vlan['ipv4']):
            for ip in existing_vlan['ipv4']:
                if ip not in vlan['ipv4']:
                    l.write("ipv4 %s in existing_vlan but not in vlan\n", ip)
                    l.flush()
                    return True

        return False


    def save_vlan(self, facts, vlan):
        # if something has changed, best to delete then recreate
        if self.vlan_changed(facts, vlan):
            facts = self.delete_vlan(facts, vlan['vlan_id'])
        self.set_changed(False)

        # TODO: add error handling here
        vlan_id = str(vlan['vlan_id'])

        if vlan_id in facts['running']['vlans']:
            self.set_changed(False)
            self.append_message("VLAN %s already exists\n" % vlan_id)
            return facts

        # enter global config
        self._enter_config_level()

        self.sw.exec_command("vlan %s\n" % vlan_id,
                           "ERROR: unable to enter VLAN ID")
        # if user doesn't assign, name assigned by switch 000${vlan_id}
        if vlan['vlan_name'] != None and len(vlan['vlan_name']):
            self.sw.exec_command("name %s\n" % vlan['vlan_name'],
                               "ERROR: unable to enter VLAN name %s" %
                               vlan['vlan_name'])

        # set IP if specified
        if len(vlan['ipv4']):
            for ip in vlan['ipv4']:
                l.write("ip address %s\n" % ip)
                l.flush()
                self.sw.exec_command("ip address %s\n" % ip,
                                   "ERROR: unable to set address %s for vlan %s" %
                                   (ip, vlan_id))

        # set tagged if specified
        for key in ('tagged', 'untagged'):
            if vlan[key] != None and len(vlan[key]):
                l.write("checking key %s\n" % key)
                l.flush()
                self.sw.exec_command("%s %s\n" % (key, vlan[key]),
                                   "ERROR: unable to set %s ports for vlan %s" %
                                   (key, vlan['ipv4']))

        # leave interface view
        self.exit()

        # refresh facts to confirm if the new vlan shows up
        facts = self.get_facts()
        if vlan_id in facts['running']['vlans']:
            self.set_changed(True)
            self.append_message("VLAN ID %s created\n" % vlan_id)
        else:
            self.append_message("Unable to create VLAN ID %s\n" % vlan_id)

        return facts

    def delete_vlan(self, facts, vlan_id):
        self.set_changed(False)
        l.write("delete_vlan() vlan_id %d\n" % vlan_id)
        l.flush()
        if type(vlan_id) is not int:
            self.set_failed(True)
            self.set_message("ERROR: 'id' provided is not numeric.")

        if self.get_failed():
            self.module.exit_json(failed=self.get_failed(),
                                  changed=self.get_changed(),
                                  msg=self.get_message())

        # force to string
        vlan_id = str(vlan_id)

        if vlan_id not in facts['running']['vlans']:
            self.set_changed(False)
            self.append_message("VLAN %s doesn't exist\n" % vlan_id)
            return facts

        self._enter_config_level()
        self.sw.exec_command("no vlan %s\n" % vlan_id,
                           "Unable to delete vlan %s" % vlan_id)

        # refresh facts
        facts = self.get_facts()

        if vlan_id not in facts['running']['vlans']:
            self.set_changed(True)
            self.append_message("VLAN ID %s deleted\n" % vlan_id)
        else:
            self.append_message("Unable to delete VLAN ID %s\n" % vlan_id)

        self.exit()

        return facts


def main():
    facts = {}
    module = AnsibleModule(
        argument_spec=dict(
            developer_mode=dict(type='bool'),
            state=dict(required=False, default='present',
                       choices=['present', 'reboot', 'absent']),
            save=dict(required=False, type='bool', default=False),
            username=dict(required=True),
            password=dict(required=False),
            host=dict(required=True),
            vlan_id=dict(required=True, type='int'),
            vlan_name=dict(required=False),
            ipv4=dict(required=False, type='list', default=[]),
            tagged=dict(required=False),
            untagged=dict(required=False),
            gather_facts=dict(required=False, type='bool', default='True'),
            timeout=dict(require=False, default=30, type='int'),
            port=dict(required=False, default=22, type='int'),
            private_key_file=dict(required=False)
        ),
        supports_check_mode=True,
    )

    failed = False

    if module.params.get('private_key_file') is None \
       and module.params.get('password') is None:
        err_msg = "No password or private_key_file provided. " +\
                  "Either one must be supplied!"
        module.exit_json(failed=True,
                         changed=False,
                         msg=err_msg,
                         ansible_facts={})
    switch = ProVisionVlan(module,
                           host=module.params.get('host'),
                           username=module.params.get('username'),
                           password=module.params.get('password'),
                           timeout=module.params.get('timeout'),
                           port=module.params.get('port'),
                           private_key_file=
                           module.params.get('private_key_file'))

    try:
        l.write("module instantiated\n")
        l.flush()
        facts = switch.dispatch()
        if not module.params.get('gather_facts'):
            facts = {}

        module.exit_json(failed=failed,
                         changed=switch.get_changed(),
                         msg=switch.get_message(),
                         ansible_facts=facts)
    except Exception, e:
        msg = switch.get_message() + " %s %s" % (e.__class__, e)
        switch.fail(msg)

# entry point
main()
