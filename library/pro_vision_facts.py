#!/usr/bin/python
#coding: utf-8 -*-

# (c) 2014, Patrick Galbraith <patg@patg.net>
#
# This file is part of Ansible
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

# Note: this code is currently under development and is full of debug code that
# writes to a text file in /tmp.
# This debug will be removed soon
#

DOCUMENTATION = '''
---
module: pro_vision_facts
version_added: 0.1
author: Patrick Galbraith
short_description: Basic management of Pro Vision-based HP Switches
requirements: [ pro_vision_ansible (http://code.patg.net/pro_vision_ansible.tar.gz)]
description:
    - Basic management of Pro Vision-based Switches
options:
    developer-mode:
        required: false
        default: true
        choices: [ true, false ]
        description:
            - Whether to set the switch into developer mode.
    state:
        required: false
        default: present
        choices: [ 'present', 'reboot' ]
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
'''

EXAMPLES = '''

# file: switch.yml
- hosts: localhost
  tasks:
  - name: get facts for the switch
    local_action:
      module: pro_vision_facts
      developer-mode: true
      host: 192.168.1.100
      username: admin
      password: ckrit

# OR

# file: switch.yml
- hosts: localhost
  tasks:
  - name: gather facts from switch
    pro_vision: host=192.168.1.100 username=admin password=ckrit

'''

# http://code.patg.net/pro_vision.tar.gz
from pro_vision_ansible import ProVision
from ansible.module_utils.basic import *

l = open('/tmp/provision.log', 'wb')

class ProVisionFacts(ProVision):
    def dispatch(self):
        l.write("dispatch()\n")
        l.flush()
        facts = self.get_facts()
        state = self.module.params.get('state')
        if state == 'reboot':
            self.reboot()
        return facts


def main():
    facts = {}
    module = AnsibleModule(
        argument_spec=dict(
            developer_mode=dict(type='bool'),
            state=dict(required=False, default='present',
                       choices=['present', 'reboot']),
            save=dict(required=False, type='bool', default=False),
            username=dict(required=True),
            password=dict(required=False),
            host=dict(required=True),
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
    l.write("ProVisionFacts\n")
    l.flush()
    switch = ProVisionFacts(module,
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
