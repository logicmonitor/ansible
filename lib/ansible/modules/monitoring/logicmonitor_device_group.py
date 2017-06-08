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
module: logicmonitor_device_group
short_description: Manage LogicMonitor device groups
description:
  - LogicMonitor is a hosted, full-stack, infrastructure monitoring platform.
  - This module manages device groups within your LogicMonitor account.
version_added: '2.4'
author: [Jeff Wozniak (@woz5999)]
notes:
  - You must have an existing LogicMonitor account for this module to function.
  - The specified token Access Id and Access Key must have sufficient permission to perform the requested actions
  - This module is recommended for use from a single host using local_action or delegate_to
requirements: ['An existing LogicMonitor account', 'Linux']
options:
  state:
    description:
      - Whether to ensure that the resource is present or absent
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
  applies_to:
    description:
      - Custom applies to query for dynamic device groups
      - If set, this will create a dynamic device group
    required: false
    default: null
  description:
    description:
      - The description of the device group
    required: false
    default: ''
  disable_alerting:
    description:
      - Indicates whether alerting is disabled (true) or enabled (false) for this device group
    required: false
    default: false
    type: bool
  full_path:
    description:
      - The full path of the device group object you would like to manage
      - 'For example: /Production/Web/Databases'
      - If the parent device groups specified in the path don't exist, they will be created
    required: true
    default: null
  properties:
    description:
      - A dictionary of properties associated with this device group
    required: false
    default: {}
...
'''

EXAMPLES = '''
# creating a device group
---
- hosts: hosts
  remote_user: '{{ username }}'
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
  - name: Create device group
    logicmonitor_collector_group:
      account: '{{ account }}'
      access_id: '{{ access_id }}'
      access_key: '{{ access_key }}'
      state: present
      description: My device group created by Ansible
      disable_alerting: no
      full_path: /AnsibleDevices/WebServers
      properties:
        snmp.community: commstring
        type: webservers
    delegate_to: localhost

# removing a device group
---
- hosts: hosts
  remote_user: '{{ username }}'
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
  - name: Remove device group
    logicmonitor_collector_group:
      account: '{{ account }}'
      access_id: '{{ access_id }}'
      access_key: '{{ access_key }}'
      state: absent
      full_path: /AnsibleDevices/WebServers
    delegate_to: localhost
...
'''


import copy
import logicmonitor
from logicmonitor.rest import ApiException
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


def get_client(params, module):
    # Configure API key authorization: LMv1

    logicmonitor.configuration.host = logicmonitor.configuration.host.replace(
        'localhost',
        params['account'] + '.logicmonitor.com'
    )
    logicmonitor.configuration.api_key['id'] = params['access_id']
    logicmonitor.configuration.api_key['Authorization'] = params['access_key']

    # create an instance of the API class
    return logicmonitor.DefaultApi(logicmonitor.ApiClient())


def get_object(client, params, module):
    try:
        obj = logicmonitor.RestDeviceGroup(
            custom_properties=format_custom_properties(params['properties']),
            description=params['description'],
            disable_alerting=bool(params['disable_alerting']),
            full_path=params['full_path'].lstrip('/'),
            group_type='Normal',
        )

        if 'applies_to' in params and params['applies_to']:
            obj.applies_to = params['applies_to']
        return obj

    except Exception as e:
        err = 'Exception creating object: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)


def set_update_fields(obj_1, obj_2):
    # set immutable fields for updating object
    obj_1.id = obj_2.id
    obj_1.name = obj_2.name
    obj_1.parent_id = obj_2.parent_id
    return obj_1


def compare_obj(obj_1, obj_2):
    return compare_objects(obj_1, obj_2)


def compare_objects(group_1, group_2):
    exclude_keys = {}

    dict_1 = group_1.to_dict()
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


def find_obj(client, full_path, module):
    module.debug('finding device group ' + str(full_path))
    # trim leading / if it exists
    full_path = full_path.lstrip('/')

    device_groups = None
    try:
        device_groups = client.get_device_group_list()
    except ApiException as e:
        err = 'Exception when calling get_device_group_list: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)

    if device_groups.status != 200:
        err = (
            'Error ' + str(device_groups.status) +
            ' calling get_device_group_list: ' + str(e) + '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    # look for matching device group
    for item in device_groups.data.items:
        if item.full_path == full_path:
            return item
    return None


def add_obj(client, device_group, module):
    module.debug('adding device group ' + device_group.name)

    resp = None
    try:
        resp = client.add_device_group(device_group)
    except ApiException as e:
        err = 'Exception when calling add_device_group: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
        if resp.status == 600:
            # Status 600: The record already exists
            return device_group

        err = (
            'Status ' + str(resp.status) + ' calling add_device_group\n' +
            str(resp.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return resp.data


def create_device_group(client, device_group, module):
    module.debug('creating device group ' + str(device_group.full_path))

    # parse the device group name from its full path
    name = device_group.full_path.rsplit('/', 1)
    device_group.name = name[len(name) - 1]

    # strip the group name to get parent path
    parent_path = device_group.full_path.rsplit('/')
    parent_path = '/'.join(parent_path[0:-1])

    # determine if the parent group exists
    if parent_path == '':
        device_group.parent_id = 1
    else:
        parent_group = find_obj(client, parent_path, module)
        if parent_group is not None:
            # parent group exists
            device_group.parent_id = parent_group.id
        else:
            # parent group doesn't exist
            module.debug(
                'parent group ' + str(parent_path) + ' not found. creating.'
            )
            # create paramters for parent group
            parent_group = copy.copy(device_group)
            parent_group.full_path = parent_path

            # recursively create parent groups
            parent = create_device_group(client, parent_group, module)
            device_group.parent_id = parent.id

    return add_obj(client, device_group, module)


def delete_obj(client, device_group, module):
    module.debug('deleting device group ' + str(device_group.name))
    resp = None
    try:
        resp = client.delete_device_group_by_id(str(device_group.id))
    except ApiException as e:
        err = (
            'Exception when calling delete_device_group_by_id: ' + str(e) +
            '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
        err = (
            'Status ' + str(resp.status) +
            ' calling delete_device_group_by_id\n' +
            str(resp.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return resp


def update_obj(client, device_group, module):
    module.debug('updating device group ' + str(device_group.name))

    resp = None
    try:
        resp = client.update_device_group_by_id(
            str(device_group.id),
            device_group
        )
    except ApiException as e:
        err = (
            'Exception when calling update_device_group_by_id: ' + str(e) +
            '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
        err = (
            'Status ' + str(resp.status) +
            ' calling update_device_group_by_id\n' +
            str(resp.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return resp


def format_custom_properties(properties):
    ret = []

    for k in properties:
        ret.append({
            'name': str(k),
            'value': str(properties[k])
        })
    return ret


def ensure_present(params, module):
    client = get_client(params, module)

    obj = get_object(client, params, module)

    found_obj = find_obj(client, obj.full_path, module)
    if found_obj is None:
        if not module.check_mode:
            create_device_group(client, obj, module)
        module.exit_json(changed=True)
    if not compare_obj(obj, found_obj):
        if not module.check_mode:
            # set known fields required for updating object
            obj = set_update_fields(obj, found_obj)
            update_obj(client, obj, module)
        module.exit_json(changed=True)
    module.exit_json(changed=False)


def ensure_absent(params, module):
    client = get_client(params, module)

    obj = find_obj(client, params['full_path'], module)
    if obj is None:
        module.exit_json(changed=False)
    else:
        if not module.check_mode:
            delete_obj(client, obj, module)
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

            applies_to=dict(required=False, default=None),
            description=dict(required=False, default=''),
            disable_alerting=dict(
                required=False,
                default='false',
                type='bool',
                choices=BOOLEANS
            ),
            full_path=dict(required=True, default=None),
            properties=dict(required=False, default={}, type='dict')
        ),
        supports_check_mode=True
    )

    if HAS_LIB_JSON is not True:
        module.fail_json(msg='Unable to load JSON library')

    selector(module)


from ansible.module_utils.basic import *


if __name__ == '__main__':
    main()
