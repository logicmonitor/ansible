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
module: logicmonitor
short_description: Manage your LogicMonitor account through Ansible Playbooks
description:
  - LogicMonitor is a hosted, full-stack, infrastructure monitoring platform.
  - This module manages collectors within your LogicMonitor account.
version_added: '2.2'
author: [Jeff Wozniak (@woz5999)]
notes:
  - You must have an existing LogicMonitor account for this module to function.
requirements: ['An existing LogicMonitor account', 'Linux']
options:
  state:
    description:
    required: true
    default: null
    choices: ['present', 'absent']
  company:
    description:
      - The LogicMonitor account company name. If you would log in to your account at 'superheroes.logicmonitor.com' you would use 'superheroes.'
    required: true
    default: null
  access_id:
    description:
      - Your API Token Access ID
    required: true
    default: null
  access_key:
    description:
        - Your API Token Access Key
    required: true
    default: null
  description:
    description:
      - The long text description of the collector in your LogicMonitor account.
    required: false
    default: ''
...
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
        params['company'] + '.logicmonitor.com'
    )
    logicmonitor.configuration.api_key['id'] = params['access_id']
    logicmonitor.configuration.api_key['Authorization'] = params['access_key']

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

    if 'backup_collector_id' in params:
        obj.backup_agent_id = params['backup_collector_id']
    if 'description' in params:
        obj.description = params['description']
    else:
        obj.description = socket.getfqdn()
    if 'id' in params:
        obj.id = params['id']
    if 'resend_interval' in params:
        obj.resend_ival = params['resend_interval']
    if 'suppress_alert_clear' in params:
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
    if 'id' in params and 'present' != params['state']:
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
    if 'description' not in params:
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

    if 'description' in params:
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
            if 'id' in params:
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
    STATE = [
        'absent,'
        'present'
    ]

    module = AnsibleModule(
        argument_spec=dict(
            state=dict(required=True, default=None, choices=STATE),
            company=dict(required=True, default=None),
            access_id=dict(required=True, default=None),
            access_key=dict(required=True, default=None, no_log=True),

            backup_collector_id=dict(required=False, default=None, type='int'),
            collector_size=dict(
                required='small',
                default=None,
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
            hostname=dict(equired=False, default=None),
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
from ansible.module_utils.urls import *
from ansible.module_utils.urls import open_url


if __name__ == '__main__':
    main()
