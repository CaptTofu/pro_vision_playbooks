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
requirements: [ paramiko pro_vision (http://code.patg.net/pro_vision.tar.gz)]
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
            - if true, all changes will be written. Upon reboot, save
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
    tagged_port_type:
        required: false
        choices: [ trunk, hybrid]
        default: trunk
        description:
            - Type that all tagged ports will be given
    untagged_port_type:
        required: false
        choices: [ access, hybrid]
        default: access
        description:
            - Type that all untagged port will be given
    tagged_ports:
        required: false
        default: None
        description:
            - List of tagged ports
    untagged_ports:
        required: false
        default: None
        description:
            - List of untagged ports
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
      name: VLAN 11
      id: 11
      interface_type: access
      tagged: false
      interfaces:
      - 1-25 

OR

- hosts: localhost
  tasks:
  - name: create VLAN 11
    pro_vision_vlan: host=192.168.1.100 username=operator password=ckrit state=present vlan_name="VLAN 11" vlan_id=11 untagged_port_type: access untagged_interfaces=1-25

'''

EXAMPLES = '''

# file: switch.yml
- hosts: localhost
  tasks:
  - name: get facts for the switch
    local_action:
      module: pro_vision_vlan
      developer-mode: true
      host: 192.168.1.100
      username: operator 
      password: ckrit

# OR

# file: switch.yml
- hosts: localhost
  tasks:
  - name: gather facts from switch
    pro_vision_vlan: host=192.168.1.100 username=operator password=ckrit

'''

# http://code.patg.net/pro_vision.tar.gz
from pro_vision import ProVision 
from ansible.module_utils.basic import *
import pprint 
pp = pprint.PrettyPrinter(indent=4)

l = open('/tmp/provision.log', 'wb')

class ProVisionVlan(ProVision):
    def dispatch(self):
        facts = self._handle_vlan()
        return facts

    def _handle_vlan(self):
        l.write("dispatch()\n")
        l.flush()
        facts = self.get_facts()
        l.write("%s\n" % pp.pformat(facts))
        state = self.module.params.get('state')
        vlan = {'vlan_id': self.module.params.get('vlan_id'),
                'vlan_name': self.module.params.get('vlan_name'),
                'tagged_port_type': self.module.params.get('tagged_port_type'),
                'untagged_port_type':
                self.module.params.get('untagged_port_type'),
                'tagged_ports': self.module.params.get('tagged_ports'),
                'untagged_ports': self.module.params.get('untagged_ports'),
                'state': self.module.params.get('state'),
                'interfaces': self.module.params.get('interfaces')}
        if vlan['state'] == 'absent':
            facts = self._delete_vlan(facts, vlan['vlan_id'])
        else:
            facts = self._save_vlan(facts, vlan)
        # After adding or deleting vlan, save
        if self.module.params.get('save') is True:
            self.save()
        return facts

    def _vlan_changed(self, facts, vlan):
        vlan_id = str(vlan['vlan_id'])
        if vlan_id not in facts['running']['vlans']:
            return False
        existing_vlan = facts['running']['vlans'][vlan_id]
        if vlan['vlan_name'] != existing_vlan['vlan_name']:
            return True

    def _save_vlan(self, facts, vlan):
        # if something has changed, best to delete then recreate
        if self._vlan_changed(facts, vlan):
            facts = self._delete_vlan(facts, vlan['vlan_id'])
        self.set_changed(False)

        # TODO: add error handling here
        vlan_id = str(vlan['vlan_id'])

        if vlan_id in facts['running']['vlans']:
            self.set_changed(False)
            self.append_message("VLAN %s already exists\n" % vlan_id)
            return facts

        # enter global config
        self._enter_config_level()

        self._exec_command("vlan %s\n" % vlan_id,
                           "ERROR: unable to enter VLAN ID")
        # if user doesn't assign, name assigned by switch 000${vlan_id}
        if length(vlan['vlan_name']):
            self._exec_command("name %s\n" % vlan['vlan_name'],
                               "ERROR: unable to enter VLAN name %s" % vlan['vlan_name'])

        # set IP if specified
        if length(vlan['ipv4']): 
            self._exec_command("ip address %s\n" % vlan['ipv4'], 
                               "ERROR: unable to set address for vlan %s" % vlan['ipv4'])

        # leave interface view
        self._exit()

        # refresh facts to confirm if the new vlan shows up
        facts = self.get_facts()
        if vlan_id in facts['running']['vlans']:
            self.set_changed(True)
            self.append_message("VLAN ID %s created\n" % vlan_id)
        else:
            self.append_message("Unable to create VLAN ID %s\n" % vlan_id)

        return facts

    def _delete_vlan(self, facts, vlan_id):
        self.set_changed(False)
        l.write("_delete_vlan() vlan_id %d\n" % vlan_id)
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
        self._exec_command("no vlan %s\n" % vlan_id,
                           "Unable to delete vlan %s" % vlan_id)

        # refresh facts
        facts = self.get_facts()

        if vlan_id not in facts['running']['vlans']:
            self.set_changed(True)
            self.append_message("VLAN ID %s deleted\n" % vlan_id)
        else:
            self.append_message("Unable to delete VLAN ID %s\n" % vlan_id)

        self._exit()

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
            gather_facts=dict(required=False, type='bool', default='True'),
            timeout=dict(default=30, type='int'),
            port=dict(default=22, type='int'),
            private_key_file=dict(required=False)
        ),
        supports_check_mode=True,
    )
    l.write("module started\n")
    l.flush()

    failed = False

    if module.params.get('private_key_file') is None \
       and module.params.get('password') is None:
        err_msg = "No password or private_key_file provided. " +\
                  "Either one must be supplied!"
        module.exit_json(failed=True,
                         changed=False,
                         msg=err_msg,
                         ansible_facts={})
    l.write("ProVision_Facts\n")
    l.flush()
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
