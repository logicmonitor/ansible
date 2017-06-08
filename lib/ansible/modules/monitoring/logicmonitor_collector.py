#!/usr/bin/python

'''LogicMonitor Ansible module for managing device groups
   Copyright (C) 2015  LogicMonitor

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software Foundation,
   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA'''


ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

RETURN = '''
---
success:
    description: flag indicating that execution was successful
    returned: success
    type: boolean
    sample: True
...
'''


DOCUMENTATION = '''
---
module: logicmonitor_collector
short_description: Manage LogicMonitor collectors
description:
  - LogicMonitor is a hosted, full-stack, infrastructure monitoring platform.
  - This module manages collectors within your LogicMonitor account.
version_added: '2.4'
author: [Jeff Wozniak (@woz5999)]
notes:
  - You must have an existing LogicMonitor account for this module to function.
  - The specified token Access Id and Access Key must have sufficient permission to perform the requested actions
requirements: ['An existing LogicMonitor account', 'Linux']
options:
  state:
    description:
      - Whether to ensure that the resource is present or absent
      - When 'absent', 'id' or 'description' must be specified
    required: true
    default: null
    choices: ['present', 'absent']
  account:
    description:
      - LogicMonitor account name
    required: true
    default: null
  access_id:
    description:
      - LogicMonitor API Token Access ID
    required: true
    default: null
  access_key:
    description:
      - LogicMonitor API Token Access Key
    required: true
    default: null
  backup_collector_id:
    description:
      - The Id of the failover Collector configured for this Collector
    required: false
    default: null
    type: int
  collector_group:
    description:
      - The Id of the group the Collector is in
    required: false
    default: /
  collector_size:
    description:
      - The size of the Collector to install
      - small requires 2GB memory)
      - medium requires 4GB memory)
      - large requires 8GB memory)
    required: false
    default: small
    choices: ['nano', 'small', 'medium', 'large']
  description:
    description:
       - The Collector's description
    required: false
    default: null
  enable_fail_back:
    description:
      - Whether or not automatic failback is enabled for the Collector
    required: false
    default: False
    type: bool
  escalating_chain_id:
    description:
      - The Id of the escalation chain associated with this Collector
    required: false
    default: 1
    type: int
  id:
    description:
      - The Id of an existing Collector provision
      - The specified Collector Id must already exist in order to use this option
    required: false
    default: null
    type: int
   resend_interval:
    description:
      - The interval, in minutes, after which alert notifications for the Collector will be resent
    required: false
    default: 15
    type: int
   suppress_alert_clear:
    description:
      - Whether alert clear notifications are suppressed for the Collector
    required: false
    default: False
    type: bool
   us_ea:
    description:
      - If true, the latest EA Collector version will be used
    required: false
    default: False
    type: bool
...
'''

EXAMPLES = '''
# creating a collector
---
- hosts: hosts
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
  - name: Create and install collector
    logicmonitor_collector:
      account: '{{ account }}'
      access_id: '{{ access_id }}'
      access_key: '{{ access_key }}'
      state: present
      backup_collector_id: 15
      collector_group: AnsibleCollectors
      collector_size: large
      description: My collector created by Ansible
      enable_fail_back: yes
      escalation_chain_id: 1
      resend_interval: 60
      suppress_alert_clear: no
      use_ea: yes

# installing and/or updating an existing collector
---
- hosts: hosts
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
  - name: Create and install collector
    logicmonitor_collector:
      account: '{{ account }}'
      access_id: '{{ access_id }}'
      access_key: '{{ access_key }}'
      state: present
      id: 16
      backup_collector_id: 15
      collector_group: AnsibleCollectors
      collector_size: large
      description: My collector created by Ansible
      enable_fail_back: yes
      escalation_chain_id: 1
      resend_interval: 60
      suppress_alert_clear: no
      use_ea: yes

# removing a collector by id
---
- hosts: hosts
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
  - name: Create and install collector
    logicmonitor_collector:
      account: '{{ account }}'
      access_id: '{{ access_id }}'
      access_key: '{{ access_key }}'
      state: absent
      id: 15

# removing a collector by description
---
- hosts: hosts
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
  - name: Create and install collector
    logicmonitor_collector:
      account: '{{ account }}'
      access_id: '{{ access_id }}'
      access_key: '{{ access_key }}'
      state: absent
      description: My collector created by Ansible
'''

import logicmonitor
from logicmonitor.rest import ApiException
import os
import socket
import sys
import types

HAS_LIB_JSON = True
try:
    import json
    # Detect the python-json library which is incompatible
    # Look for simplejson if that's the case
    try:
        if (
            not isinstance(json.loads, types.FunctionType) or
            not isinstance(json.dumps, types.FunctionType)
        ):
            raise ImportError
    except AttributeError:
        raise ImportError
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print(
            '\n{"msg": "Error: ansible requires the stdlib json or ' +
            'simplejson module, neither was found!", "failed": true}'
        )
        HAS_LIB_JSON = False
    except SyntaxError:
        print(
            '\n{"msg": "SyntaxError: probably due to installed simplejson ' +
            'being for a different python version", "failed": true}'
        )
        HAS_LIB_JSON = False


AGENT_DIRECTORY = 'agent'
DEFAULT_OS = 'Linux'
INSTALL_PATH = '/usr/local/logicmonitor/'
UNINSTALL_PATH = INSTALL_PATH + AGENT_DIRECTORY + '/bin/uninstall.pl'


def get_client(params, module):
    # Configure API key authorization: LMv1

    logicmonitor.configuration.host = logicmonitor.configuration.host.replace(
        'localhost',
        params['account'] + '.logicmonitor.com'
    )
    logicmonitor.configuration.api_key['id'] = params['access_id']
    logicmonitor.configuration.api_key['Authorization'] = params['access_key']
    logicmonitor.configuration.temp_folder_path = INSTALL_PATH

    # create an instance of the API class
    return logicmonitor.DefaultApi(logicmonitor.ApiClient())


def get_obj(client, params, module):
    obj = None
    try:
        obj = logicmonitor.RestCollector(
            enable_fail_back=params['enable_fail_back'],
            escalating_chain_id=params['escalation_chain_id']
        )
    except Exception as e:
        err = 'Exception creating object: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)

    collector_group = find_collector_group(
        client,
        params['collector_group'],
        module
    )
    if collector_group is not None:
        obj.collector_group_id = collector_group.id
    else:
        err = (
            'Collecor group ' + params['collector_group'] +
            ' does not exist.'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    if 'backup_collector_id' in params and params['backup_collector_id']:
        obj.backup_agent_id = params['backup_collector_id']
    if 'description' in params and params['description']:
        obj.description = params['description']
    else:
        obj.description = socket.getfqdn()
    if 'id' in params and params['id']:
        obj.id = params['id']
    if 'resend_interval' in params and params['resend_interval']:
        obj.resend_ival = params['resend_interval']
    if 'suppress_alert_clear' in params and params['suppress_alert_clear']:
        obj.suppress_alert_clear = params['suppress_alert_clear']

    return obj


def set_update_fields(obj_1, obj_2):
    # set immutable fields for updating object
    obj_1.id = obj_2.id
    return obj_1


def destructive_updates(collector, params):
    # any diff between the params listed will require a collector reinstall
    if (
        'collector_size' in params and
        collector.collector_size != params['collector_size']
    ):
        return False
    if (
        'use_ea' in params and
        collector.use_ea != params['use_ea']
    ):
        return False
    if (
        'collector_version' in params and
        collector.collector_version != params['collector_version']
    ):
        return False

    return True


def compare_obj(obj_1, obj_2):
    return compare_objects(obj_1, obj_2)


def compare_objects(group_1, group_2):
    exclude_keys = {}

    dict_1 = {}
    dict_2 = {}
    # determine if the compare objects are dicts or classes
    if isinstance(group_1, dict):
        dict_1 = group_1
    else:
        dict_1 = group_1.to_dict()

    if isinstance(group_2, dict):
        dict_2 = group_2
    else:
        dict_2 = group_2.to_dict()

    for k in dict_1:
        if k in exclude_keys:
            continue
        if dict_1[k] is not None and k in dict_2 and dict_2[k] is not None:
            if str(dict_1[k]) != str(dict_2[k]):
                return False
    for k in dict_2:
        if k in exclude_keys:
            continue
        if dict_2[k] is not None and k in dict_1 and dict_1[k] is not None:
            if str(dict_1[k]) != str(dict_2[k]):
                return False
    return True


def find_collector_group(client, collector_group_name, module):
    module.debug('finding collector group ' + str(collector_group_name))

    # if the root group is set, no need to search
    if collector_group_name == '/':
        return 1

    # trim leading / if it exists
    collector_group_name = collector_group_name.lstrip('/')

    collector_groups = None
    try:
        collector_groups = client.get_collector_group_list()
    except ApiException as e:
        err = (
            'Exception when calling get_collector_group_list: ' + str(e) + '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    if collector_groups.status != 200:
        err = (
            'Error ' + str(collector_groups.status) +
            ' calling get_collector_group_list: ' + str(e) + '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    # look for matching collector group
    for item in collector_groups.data.items:
        if item.name == collector_group_name:
            return item
    return None


def find_obj(client, params, module):
    if 'id' in params and params['id'] and 'present' != params['state']:
        return find_collector_by_id(client, params['id'], module)
    else:
        return find_collector(client, params, module)


def find_collector_by_id(client, id, module):
    module.debug('finding collector ' + str(id))

    collector = None
    try:
        collector = client.get_collector_by_id(str(id))
    except ApiException as e:
        err = 'Exception when calling get_collector_by_id: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)

    if collector.status != 200:
        if collector.status == 1069:
            # Status 1069: No such agent
            return None

        err = (
            'Status ' + str(collector.status) +
            ' calling find_collector_by_id\n' + str(collector.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return collector.data


def find_collector(client, params, module):
    if 'description' not in params or not params['description']:
        return None

    module.debug('finding collector ' + str(params['description']))

    collectors = None
    try:
        collectors = client.get_collector_list()
    except ApiException as e:
        err = 'Exception when calling get_collector_list: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)

    if collectors.status != 200:
        err = (
            'Error ' + str(collectors.status) +
            ' calling get_device_list: ' + str(e) + '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    if 'description' in params and params['description']:
        for item in collectors.data.items:
            if item.description == params['description']:
                return item
    return None


def collector_installed():
    return os.path.exists(INSTALL_PATH + AGENT_DIRECTORY)


def install_collector(client, collector, params, module):
    fail = False
    installer = download_installer(client, collector, params, module)

    module.debug('installing ' + str(installer))
    result, out, err = module.run_command(str(installer) + ' -y')
    if result < 0 or err != '':
        fail = True

    # be nice and clean up
    remove_installer(client, installer, module)

    if fail:
        module.fail_json(msg=err, changed=True, failed=True)


def uninstall_collector(client, module):
    module.debug('uninstalling collector ' + str(UNINSTALL_PATH))
    result, out, err = module.run_command(UNINSTALL_PATH)
    if result < 0 or err != '':
        module.fail_json(msg=err, changed=True, failed=True)


def download_installer(client, collector, params, module):
    module.debug('downloading collector ' + str(collector.id))

    os_and_arch = None
    if sys.maxsize > 2**32:
        os_and_arch = DEFAULT_OS + '64'
    else:
        os_and_arch = DEFAULT_OS + '32'

    resp = None
    try:
        resp = client.install_collector(
            str(collector.id),
            os_and_arch,
            collector_size=params['collector_size'],
            use_ea=bool(params['use_ea'])
        )
    except ApiException as e:
        err = 'Exception when calling install_collector: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=True, failed=True)

    try:
        f = open(resp, "w")
        f.write(resp)
        f.close()
    except Exception as e:
        f.close()
        err = (
            'Error downloading collector\n' + str(e)
        )
        module.fail_json(msg=err, changed=True, failed=True)
    return resp


def remove_installer(client, path, module):
    module.debug('Removing installer ' + path)
    module.run_command('rm -f ' + path)


def add_obj(client, collector, module):
    module.debug('adding collector')

    resp = None
    try:
        resp = client.add_collector(collector)
    except ApiException as e:
        err = 'Exception when calling add_collector: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
        if resp.status == 600:
            # Status 600: The record already exists
            return collector

        err = (
            'Status ' + str(resp.status) + ' calling add_collector\n' +
            str(resp.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return resp.data


def delete_obj(client, collector, module):
    module.debug('deleting collector group ' + str(collector.id))
    resp = None
    try:
        resp = client.delete_collector_by_id(str(collector.id))
    except ApiException as e:
        err = (
            'Exception when calling delete_collector_by_id: ' + str(e) +
            '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
        err = (
            'Status ' + str(resp.status) +
            ' calling delete_collector_by_id\n' +
            str(resp.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return resp


def update_obj(client, collector, module):
    module.debug('updating collector ' + str(collector.id))

    resp = None
    try:
        resp = client.update_collector_by_id(str(collector.id), collector)
    except ApiException as e:
        err = (
            'Exception when calling update_collector_by_id: ' + str(e) +
            '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
        err = (
            'Status ' + str(resp.status) +
            ' calling update_collector_by_id\n' +
            str(resp.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return resp


def ensure_present(params, module):
    changed = False
    client = get_client(params, module)

    obj = get_obj(client, params, module)

    found_obj = find_obj(client, params, module)
    if found_obj is None:
        if not module.check_mode:
            if 'id' in params and params['id']:
                err = (
                    'The specified collector does not exist and collectors ' +
                    'cannot be created with a specific id.'
                )
                module.fail_json(msg=err, changed=False, failed=True)

            resp = add_obj(client, obj, module)
            # grab the id from the created object
            obj.id = resp.id
        changed = True
    elif not compare_obj(obj, found_obj):
        if not module.check_mode:
            # set known fields required for updating object
            obj = set_update_fields(obj, found_obj)
            update_obj(client, obj, module)

            # determine if any of the updated values require a reinstall
            if collector_installed() and destructive_updates():
                uninstall_collector(client, obj, module)
        changed = True
    else:
        # make sure to give the object an id if it's found
        obj.id = found_obj.id

    if not collector_installed():
        if not module.check_mode:
            install_collector(client, obj, params, module)
        changed = True

    module.exit_json(changed=changed)


def ensure_absent(params, module):
    client = get_client(params, module)

    obj = find_obj(client, params, module)
    if obj is None:
        if not module.check_mode and collector_installed():
            uninstall_collector(client, obj, module)
        module.exit_json(changed=False)
    else:
        if not module.check_mode:
            delete_obj(client, obj, module)
            if collector_installed():
                uninstall_collector(client, obj, module)
        module.exit_json(changed=True)


def selector(module):
    '''Figure out which object and which actions
    to take given the right parameters'''

    changed = False
    if module.params['state'].lower() == 'present':
        changed = ensure_present(module.params, module)
    elif module.params['state'].lower() == 'absent':
        changed = ensure_absent(module.params, module)
    else:
        errmsg = ('Error: Unexpected state \'' + module.params['state'] +
                  '\' was specified.')
        module.fail_json(msg=errmsg)

    module.exit_json(changed=changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(required=True, default=None, choices=[
                'absent',
                'present'
            ]),
            account=dict(required=True, default=None),
            access_id=dict(required=True, default=None),
            access_key=dict(required=True, default=None, no_log=True),

            backup_collector_id=dict(required=False, default=None, type='int'),
            collector_size=dict(
                required=False,
                default='small',
                choices=['nano', 'small', 'medium', 'large']
            ),
            collector_group=dict(required=False, default='/'),
            description=dict(required=False, default=None),
            enable_fail_back=dict(
                required=False,
                default=False,
                type='bool',
                choices=BOOLEANS
            ),
            escalation_chain_id=dict(required=False, default=1, type='int'),
            id=dict(required=False, default=None, type='int'),
            resend_interval=dict(required=False, default=15, type='int'),
            suppress_alert_clear=dict(
                required=False,
                default=False,
                type='bool',
                choices=BOOLEANS
            ),
            use_ea=dict(
                required=False,
                default=False,
                type='bool',
                choices=BOOLEANS
            ),
        ),
        supports_check_mode=True
    )

    if HAS_LIB_JSON is not True:
        module.fail_json(msg='Unable to load JSON library')

    selector(module)


from ansible.module_utils.basic import *


if __name__ == '__main__':
    main()
