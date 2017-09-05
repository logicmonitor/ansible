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
    sample: true
id:
    description: the id of the collector
    returned: success
    type: str
    sample: 6
description:
    description: the description of the collector
    returned: success
    type: str
    sample: This is an important collector
backup_agent_id:
    description: the id of the failover Collector configured for this collector
    returned: success
    type: int
    sample: 5
enable_fail_back:
    description: whether or not automatic failback is enabled for the collector
    returned: success
    type: boolean
    sample: true
resend_interval:
    description: the interval, in minutes, after which alert notifications for the collector will be resent
    returned: success
    type: int
    sample: 15
suppress_alert_clear:
    description: whether alert clear notifications are suppressed for the collector
    returned: success
    type: boolean
    sample: false
escalation_chain_id:
    description: the id of the escalation chain associated with this collector
    returned: success
    type: int
    sample: 1
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
requirements:
  - An existing LogicMonitor account
  - Linux
  - logicmonitor_sdk >= 1.0.0
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
  collector_group:
    description:
      - The Id of the group the Collector is in
    required: false
    default: /
  collector_size:
    description:
      - The size of the Collector to install
      - nano requires < 2GB memory
      - small requires 2GB memory
      - medium requires 4GB memory
      - large requires 8GB memory
    required: false
    default: small
    choices: ['nano', 'small', 'medium', 'large']
  collector_version:
    description:
      - The version of the collector to install
      - https://www.logicmonitor.com/support/settings/collectors/collector-versions/
    required: false
    default: null
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
  id:
    description:
      - The Id of an existing Collector provision
      - The specified Collector Id must already exist in order to use this option
    required: false
    default: null
  resend_interval:
    description:
      - The interval, in minutes, after which alert notifications for the Collector will be resent
    required: false
    default: 15
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
- hosts: all
  become: yes
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
    - logicmonitor_collector:
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
    - service:
        name: logicmonitor-agent
        state: started

# installing and/or updating an existing collector
---
- hosts: all
  become: yes
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
    - logicmonitor_collector:
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
    - service:
        name: logicmonitor-agent
        state: started

# removing a collector by id
---
- hosts: all
  become: yes
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
    - logicmonitor_collector:
        account: '{{ account }}'
        access_id: '{{ access_id }}'
        access_key: '{{ access_key }}'
        state: absent
        id: 15

# removing a collector by description
---
- hosts: all
  become: yes
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
    - logicmonitor_collector:
        account: '{{ account }}'
        access_id: '{{ access_id }}'
        access_key: '{{ access_key }}'
        state: absent
        description: My collector created by Ansible
'''

DEFAULT_OS = 'Linux'

AGENT_DIRECTORY = 'agent/'
BIN_PATH = 'bin/'
CONF_PATH = 'conf/'
INSTALL_PATH = '/usr/local/logicmonitor/'
TEMP_PATH = '/tmp/'

AGENT_BINARY = INSTALL_PATH + AGENT_DIRECTORY + BIN_PATH + 'logicmonitor-agent'
UNINSTALL_BINARY = INSTALL_PATH + AGENT_DIRECTORY + '/bin/uninstall.pl'

AGENT_CONF = INSTALL_PATH + AGENT_DIRECTORY + CONF_PATH + 'agent.conf'
WRAPPER_CONF = INSTALL_PATH + AGENT_DIRECTORY + CONF_PATH + 'wrapper.conf'

AUTOWORKERS_CONFIG = 'autoprops.workers'
WRAPPER_HEAP_CONFIG = 'wrapper.java.maxmemory'

NANO_HEAP = '1024'
SMALL_HEAP = '1024'
MEDIUM_HEAP = '2048'
LARGE_HEAP = '4096'

NANO_SIZE = 'nano'
SMALL_SIZE = 'small'
MEDIUM_SIZE = 'medium'
LARGE_SIZE = 'large'

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.basic import BOOLEANS
import os
import shutil
import socket
import sys
import types

try:
    import logicmonitor_sdk as lm_sdk
    from logicmonitor_sdk.rest import ApiException
    HAS_LM = True
except ImportError:
    HAS_LM = False

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
    lm_sdk.configuration.host = lm_sdk.configuration.host.replace(
        'localhost',
        params['account'] + '.logicmonitor.com'
    )
    lm_sdk.configuration.api_key['id'] = params['access_id']
    lm_sdk.configuration.api_key['Authorization'] = params['access_key']
    lm_sdk.configuration.temp_folder_path = TEMP_PATH
    lm_sdk.user_agent = lm_sdk.user_agent + '; Ansible'

    # create an instance of the API class
    return lm_sdk.DefaultApi(lm_sdk.ApiClient())


def get_obj(client, params, module):
    obj = None
    kwargs = {
        'enable_fail_back': params['enable_fail_back'],
        'escalating_chain_id': params['escalation_chain_id'],
        'need_auto_create_collector_device': False
    }

    if 'backup_collector_id' in params and params['backup_collector_id']:
        kwargs['backup_agent_id'] = params['backup_collector_id']
    if 'description' in params and params['description']:
        kwargs['description'] = params['description']
    else:
        kwargs['description'] = socket.getfqdn()
    if 'id' in params and params['id']:
        kwargs['id'] = params['id']
    if 'resend_interval' in params and params['resend_interval']:
        kwargs['resend_ival'] = params['resend_interval']
    if 'suppress_alert_clear' in params and params['suppress_alert_clear']:
        kwargs['suppress_alert_clear'] = params['suppress_alert_clear']
    collector_group = find_collector_group_id(
        client,
        params['collector_group'],
        module
    )
    if collector_group is not None:
        kwargs['collector_group_id'] = collector_group
    else:
        err = (
            'Collecor group ' + params['collector_group'] +
            ' does not exist.'
        )
        module.fail_json(msg=err, changed=False, failed=True)
    try:
        obj = lm_sdk.RestCollector(**kwargs)
        return obj
    except Exception as e:
        err = 'Exception creating object: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)


def set_update_fields(obj_1, obj_2):
    # set immutable fields for updating object
    obj_1.id = obj_2.id
    return obj_1


def compare_installed_collector_size(size):
    # TODO remove when api returns this info in collector resource
    # determine collector size the hard way until the API returns this info
    heap = get_config_value(WRAPPER_CONF, WRAPPER_HEAP_CONFIG)
    if (
        (heap == NANO_HEAP or heap == SMALL_HEAP) and
        (size == NANO_SIZE or size == SMALL_SIZE)
    ):
        # currently, small and nano collectors have the same config
        return True
    if heap == MEDIUM_HEAP and size == MEDIUM_SIZE:
        return True
    if heap == LARGE_HEAP and size == LARGE_SIZE:
        return True
    return False


def get_config_value(file_name, config_name):
    value = None
    try:
        with open(file_name, 'r') as f:
            for line in f:
                if line.startswith(config_name):
                    value = line.split('=', 1)[-1].strip()
                    break
    except:
        return value
    return value


def destructive_updates(collector, params):
    # TODO update when api returns this info in collector resource
    # any diff between the params listed will require a collector reinstall
    # this param will be added to the collector resource in the future.
    # placeholder logic until then
    # if (
    #     'collector_size' in params and
    #     collector.collector_size != params['collector_size']
    # ):
    #     return True
    if 'collector_size' in params and params['collector_size']:
        # in the meantime, determine size based on the wrapper config
        if not compare_installed_collector_size(params['collector_size']):
            return True
    # this param will be added to the collector resource in the future.
    # placeholder logic until then
    # if (
    #     'use_ea' in params and
    #     collector.use_ea != params['use_ea']
    # ):
    #     return True
    if (
        'collector_version' in params and params['collector_version'] and
        collector.build != params['collector_version']
    ):
        return True
    return False


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


def find_collector_group_id(client, collector_group_name, module):
    module.debug('finding collector group ' + str(collector_group_name))

    # if the root group is set, no need to search
    if collector_group_name == '/':
        return 1

    # trim leading / if it exists
    collector_group_name = collector_group_name.lstrip('/')

    collector_groups = None
    try:
        collector_groups = client.get_collector_group_list(size=-1)
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
            return item.id
    return None


def find_obj(client, params, module):
    if 'id' in params and params['id']:
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
        collectors = client.get_collector_list(size=-1)
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
    return os.path.exists(AGENT_BINARY)


def install_collector(client, collector, params, module):
    fail = False
    installer = download_installer(client, collector, params, module)

    # ensure installer is executable
    module.set_mode_if_different(str(installer), 0755, True)

    module.debug('installing ' + str(installer))
    result, out, err = module.run_command(
        str(installer) + ' -y',
        use_unsafe_shell=True
    )

    if result != 0 or err != '':
        if err == '':
            err = out
        fail = True

    # be nice and clean up
    remove_path(installer, module)

    if fail:
        remove_path(INSTALL_PATH + AGENT_DIRECTORY, module)
        module.fail_json(msg=err, changed=True, failed=True)


def uninstall_collector(client, module):
    module.debug('uninstalling collector ' + str(UNINSTALL_BINARY))

    # ensure uninstaller is executable
    module.set_mode_if_different(str(UNINSTALL_BINARY), 0755, True)

    result, out, err = module.run_command(UNINSTALL_BINARY)
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
    kwargs = {
        'collector_size': params['collector_size']
        # TODO: Restore when API returns this in the collector resource
        # , 'use_ea': bool(params['use_ea'])
    }
    if 'collector_version' in params and params['collector_version']:
        kwargs['collector_version'] = params['collector_version']
    try:
        resp = client.install_collector(
            str(collector.id),
            os_and_arch,
            **kwargs
        )
    except ApiException as e:
        err = 'Exception when calling install_collector: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=True, failed=True)

    return resp


def remove_path(path, module):
    module.debug('Removing ' + path)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except:
            module.debug('Error deleting ' + path)
    if os.path.isdir(path):
        try:
            shutil.rmtree(path)
        except:
            module.debug('Error deleting ' + path)


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
    module.debug('deleting collector ' + str(collector.id))
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
    return resp.data


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
    return resp.data


def succeed(changed, obj, module):
    return module.exit_json(
        changed=changed,
        success=True,
        id=str(obj.id),
        description=obj.description,
        backup_agent_id=obj.backup_agent_id,
        enable_fail_back=obj.enable_fail_back,
        resend_interval=obj.resend_ival,
        suppress_alert_clear=obj.suppress_alert_clear,
        escalation_chain_id=obj.escalating_chain_id
    )


def ensure_present(client, params, module):
    changed = False

    obj = get_obj(client, params, module)

    found_obj = find_obj(client, params, module)
    if found_obj is None:
        if 'id' in params and params['id']:
            err = (
                'The specified collector does not exist and collectors ' +
                'cannot be created with a specific id.'
            )
            module.fail_json(msg=err, changed=False, failed=True)
        if not module.check_mode:
            obj = add_obj(client, obj, module)
        changed = True
    elif not compare_obj(obj, found_obj):
        if not module.check_mode:
            # set known fields required for updating object
            obj = set_update_fields(obj, found_obj)
            obj = update_obj(client, obj, module)
        changed = True
    else:
        # make sure to give the object an id if it's found
        obj.id = found_obj.id

    # determine if any values have changed that require a re-install
    if collector_installed() and destructive_updates(obj, params):
        if not module.check_mode:
            uninstall_collector(client, module)
        changed = True

    if not collector_installed():
        if not module.check_mode:
            install_collector(client, obj, params, module)
        changed = True

    succeed(changed, obj, module)


def ensure_absent(client, params, module):
    obj = find_obj(client, params, module)
    if obj is None:
        if not module.check_mode and collector_installed():
            obj = get_obj(client, params, module)
            uninstall_collector(client, module)
        succeed(False, obj, module)
    else:
        if not module.check_mode:
            delete_obj(client, obj, module)
            if collector_installed():
                uninstall_collector(client, module)
        succeed(True, obj, module)


def selector(module):
    '''Figure out which object and which actions
    to take given the right parameters'''

    client = get_client(module.params, module)

    if module.params['collector_version']:
        module.params['collector_version'] = (
            module.params['collector_version'].replace('.', '')
        )

    if module.params['state'].lower() == 'present':
        ensure_present(client, module.params, module)
    elif module.params['state'].lower() == 'absent':
        ensure_absent(client, module.params, module)
    else:
        errmsg = ('Error: Unexpected state \'' + module.params['state'] +
                  '\' was specified.')
        module.fail_json(msg=errmsg)


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
                default=SMALL_SIZE,
                choices=[NANO_SIZE, SMALL_SIZE, MEDIUM_SIZE, LARGE_SIZE]
            ),
            collector_group=dict(required=False, default='/'),
            collector_version=dict(required=False, default=None, type='int'),
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

    if not HAS_LIB_JSON:
        module.fail_json(msg='Unable to load JSON library')
    if not HAS_LM:
        module.fail_json(msg='logicmonitor_sdk required for this module')

    selector(module)


if __name__ == '__main__':
    main()
