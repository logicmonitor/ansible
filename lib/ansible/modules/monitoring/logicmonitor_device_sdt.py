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
module: logicmonitor_device_sdt
short_description: Manage LogicMonitor Scheduled Downtime
description:
  - LogicMonitor is a hosted, full-stack, infrastructure monitoring platform.
  - This module manages scheduled downtime within your LogicMonitor account.
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
  comment:
    description:
      - The comment associated with the SDT
    required: false
    default: ''
  device_display_name:
    description:
      - The name of the device that this SDT will be associated with
      - device_id or device_display_name must be specified
    required: false
    default: null
  device_id:
    description:
      - The id of the device that the SDT will be associated with
      - device_id or device_display_name must be specified
    required: false
    default: null
  duration:
    description:
      - The duration of the SDT in minutes
    required: false
    default: 15
  start_time:
    description:
      - The time the SDT will start
      - yyyy-mm-dd HH:MM
    required: false
    default: now
...
'''

EXAMPLES = '''
# TODO
'''


import datetime
import logicmonitor
from logicmonitor.rest import ApiException
import time
import types
import re


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


def get_obj(client, params, module):
    try:
        obj = logicmonitor.RestSDTBase(
            comment=params['comment'],
            end_date_time=params['end_date_time'],
            sdt_type=params['sdt_type'],
            start_date_time=params['start_time_epoch'],
            type='DeviceSDT'
        )

        if 'device_id' in params and params['device_id']:
            obj.device_id = params['device_id']
        if 'device_display_name' in params and params['device_display_name']:
            obj.device_display_name = params['device_display_name']

        return obj
    except Exception as e:
        err = 'Exception creating object: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)


def validate_epoch(epoch):
    try:
        datetime.datetime.fromtimestamp(int(epoch) / 1000)
        return True
    except Exception:
        return False


def calculate_end_time(start_epoch, duration, module):
    try:
        return int(start_epoch) + (int(duration) * 60 * 1000)
    except Exception as e:
        err = 'Exception calculating SDT end time: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)


def set_update_fields(obj_1, obj_2):
    # set immutable fields for updating object
    obj_1.id = obj_2.id
    obj_1.name = obj_2.name
    return obj_1


def compare_obj(obj_1, obj_2):
    return compare_objects(obj_1, obj_2)


def compare_objects(group_1, group_2):
    exclude_keys = {
        'custom_properties': 'custom_properties'
    }

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


def upper_repl(match):
    return match.group(1).upper()


def fix_polymorphic_object(src):
    # hacky shit to deal with polymorphic resource
    obj = {}
    for attr, value in src.__dict__.iteritems():
        if attr == 'swagger_types' or attr == 'attribute_map':
            continue
        if getattr(src, attr):
            # add the attr to obj and strip leading _
            k = re.sub('^_', '', attr)
            k = re.sub('_(\w)', upper_repl, k)
            obj[k] = getattr(src, attr)
    return obj


def fix_pagination_object(item, module):
    item = item.replace('u\'', '\'')
    item = item.replace('\'', '"')
    item = item.replace('True', 'true')
    item = item.replace('False', 'false')
    try:
        return json.loads(item)
    except Exception as e:
        err = 'Exception unmarshaling SDT list result: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)
    return item


def find_obj(client, params, module):
    sdts = None
    try:
        sdts = client.get_sdt_list(size=-1)
    except ApiException as e:
        err = 'Exception when calling get_sdt_list: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)

    if sdts.status != 200:
        err = (
            'Error ' + str(sdts.status) +
            ' calling get_sdt_list: ' + str(e) + '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    for item in sdts.data.items:
        # normalize the result into something actually useful
        item = fix_pagination_object(item, module)

        match = False
        # display id is globally unique, so prefer that match
        if 'device_id' in params and params['device_id']:
            if int(item['deviceId']) == int(params['device_id']):
                match = True

        if 'device_display_name' in params and params['device_display_name']:
            if item['deviceDisplayName'] == params['device_display_name']:
                match = True
        if (
            match and
            int(item['startDateTime']) == int(params['start_time_epoch']) and
            int(item['endDateTime']) == int(params['end_date_time'])
        ):
            return item

    return None


def add_obj(client, sdt, module):
    module.debug('adding sdt')

    resp = None
    try:
        # hacky garbage. can remove this when objects are handled better
        sdt = fix_polymorphic_object(sdt)
        resp = client.add_sdt(sdt)
    except ApiException as e:
        err = 'Exception when calling add_sdt: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
        if resp.status == 600:
            # TODO CHECK THIS RETURN CODE
            # Status 600: The record already exists
            return sdt

        err = (
            'Status ' + str(resp.status) + ' calling add_sdt\n' +
            str(resp.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return resp.data


def delete_obj(client, sdt, module):
    module.debug('deleting sdt')
    resp = None
    try:
        # hacky garbage. should be sdt.id assuming sdt was an object
        resp = client.delete_sdt_by_id(str(sdt['id']))
    except ApiException as e:
        err = (
            'Exception when calling delete_sdt: ' + str(e) +
            '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
        err = (
            'Status ' + str(resp.status) +
            ' calling delete_sdt\n' +
            str(resp.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return resp


def update_obj(client, sdt, module):
    module.debug('updating sdt')

    resp = None
    try:
        resp = client.update_sdt_by_id(str(sdt.id))
    except ApiException as e:
        err = (
            'Exception when calling update_device: ' + str(e) +
            '\n'
        )
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
        err = (
            'Status ' + str(resp.status) +
            ' calling update_device\n' +
            str(resp.errmsg)
        )
        module.fail_json(msg=err, changed=False, failed=True)
    return resp


def ensure_present(params, module):
    client = get_client(params, module)

    obj = get_obj(client, params, module)

    found_obj = find_obj(client, params, module)
    if found_obj is None:
        if not module.check_mode:
            add_obj(client, obj, module)
        module.exit_json(changed=True)
    # there not currently a case where an SDT is able to be updated
    # leave this here for potential future use
    # if not compare_obj(obj, found_obj):
    #     if not module.check_mode:
    #         # set known fields required for updating object
    #         obj = set_update_fields(obj, found_obj)
    #         update_obj(client, obj, module)
    #     module.exit_json(changed=True)
    module.exit_json(changed=False)


def ensure_absent(params, module):
    client = get_client(params, module)

    obj = find_obj(client, params, module)
    if obj is None:
        module.exit_json(changed=False)
    else:
        if not module.check_mode:
            delete_obj(client, obj, module)
        module.exit_json(changed=True)


def parse_sdt_type(sdt_type):
    # convert sdt type to int
    if sdt_type == 'one-time':
        return 1
    elif sdt_type == 'daily':
        return 4
    elif sdt_type == 'weekly':
        return 2
    elif sdt_type == 'monthly':
        return 3
    else:
        return -1


def parse_arguments(module):
    # validate device id and display name inputs. specify one and only one
    if (
        (
            not module.params['device_id'] and
            not module.params['device_display_name']
        ) or
        (
            module.params['device_id'] and
            module.params['device_display_name']
        )
    ):
        err = "You must specify either 'device_id' or 'device_display_name'"
        module.fail_json(msg=err, changed=False, failed=True)

    # translate sdt type string to int
    sdt_type_int = parse_sdt_type(module.params['sdt_type'])
    if sdt_type_int >= 1:
        module.params['sdt_type'] = sdt_type_int
    else:
        err = 'Unknown SDT type: ' + str(module.params['sdt_type'])
        module.fail_json(msg=err, changed=False, failed=True)

    # default to start time of now
    if not module.params['start_time_epoch']:
        module.params['start_time_epoch'] = int(time.time()) * 1000

    if not validate_epoch(module.params['start_time_epoch']):
        err = 'Invalid epoch ' + str(module.params['start_time_epoch'])
        module.fail_json(msg=err, changed=False, failed=True)

    # calculate end time from duration
    module.params['end_date_time'] = calculate_end_time(
        module.params['start_time_epoch'],
        module.params['duration'],
        module
    )
    return module.params


def selector(module):
    '''Figure out which object and which actions
    to take given the right parameters'''

    module.params = parse_arguments(module)

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
            comment=dict(required=False, default=''),
            device_display_name=dict(required=False, default=None),
            device_id=dict(required=False, default=None),
            duration=dict(required=False, default=15),
            sdt_type=dict(required=False, default='one-time', choices=[
                'one-time',
                'daily',
                'weekly',
                'monthly'
            ]),
            start_time_epoch=dict(required=False, default=None)
        ),
        supports_check_mode=True
    )

    if HAS_LIB_JSON is not True:
        module.fail_json(msg='Unable to load JSON library')

    selector(module)


from ansible.module_utils.basic import *


if __name__ == '__main__':
    main()
