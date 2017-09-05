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
    description: the id of the SDT
    returned: success
    type: str
    sample: H_1
comment:
    description: the comment associated with the SDT
    returned: success
    type: str
    sample: This is in SDT for scheduled maintenance
start_date_time:
    description: the epoch time, in milliseconds,that the SDT will start
    returned: success
    type: int
    sample: 1497904296000
end_date_time:
    description: the epoch time, in milliseconds, that the SDT will end
    returned: success
    type: int
    sample: 1497907894000
...
'''


DOCUMENTATION = '''
---
module: logicmonitor_collector_sdt
short_description: Manage LogicMonitor Collector Scheduled Downtime
description:
  - LogicMonitor is a hosted, full-stack, infrastructure monitoring platform.
  - This module manages scheduled downtime within your LogicMonitor account.
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
  device_id:
    description:
      - The id of the collector that the SDT will be applied to
    required: true
    default: null
  duration:
    description:
      - The duration of the SDT in minutes
    required: false
    default: 15
  start_time:
    description:
      - The UTC time when the SDT will start
      - yyyy-mm-dd HH:MM +
    required: false
    default: now
...
'''

EXAMPLES = '''
# scheduling immediate downtime for a collector
---
- hosts: all
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
    - logicmonitor_collector_sdt:
      account: '{{ account }}'
      access_id: '{{ access_id }}'
      access_key: '{{ access_key }}'
      state: present
      collector_id: 6
      start_time: 2017-07-18 13:45
      duration: 60

# removing scheduled downtime from a collector
---
- hosts: all
  vars:
    account: myaccount
    access_id: access_id
    access_key: access_key
  tasks:
    - logicmonitor_collector_sdt:
      account: '{{ account }}'
      access_id: '{{ access_id }}'
      access_key: '{{ access_key }}'
      state: absent
      collector_id: 6
      start_time: 2017-07-18 13:45
      duration: 60
'''


ONE_TIME_SDT = 1
DAILY_SDT = 4
WEEKLY_SDT = 2
MONTHLY_SDT = 3

THIS_SDT = 'CollectorSDT'

from ansible.module_utils.basic import AnsibleModule
import datetime
import time
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
    lm_sdk.user_agent = lm_sdk.user_agent + '; Ansible'

    # create an instance of the API class
    return lm_sdk.DefaultApi(lm_sdk.ApiClient())


def get_obj(client, params, module):
    kwargs = {
        'collector_id': params['collector_id'],
        'comment': params['comment'],
        'end_date_time': params['end_date_time'],
        'sdt_type': params['sdt_type'],
        'start_date_time': params['start_time'],
        'type': 'CollectorSDT'
    }
    try:
        obj = lm_sdk.CollectorSDT(**kwargs)
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
        # skip SDT types outside the scope of this module
        if item.type != THIS_SDT:
            continue

        match = False
        if 'collector_id' in params and params['collector_id']:
            if int(item.collector_id) == int(params['collector_id']):
                match = True

        if (
            match and
            int(item.start_date_time) == int(params['start_time']) and
            int(item.end_date_time) == int(params['end_date_time'])
        ):
            return item

    return None


def add_obj(client, sdt, module):
    module.debug('adding sdt')

    resp = None
    try:
        resp = client.add_sdt(sdt)
    except ApiException as e:
        err = 'Exception when calling add_sdt: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)

    if resp.status != 200:
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
        resp = client.delete_sdt_by_id(str(sdt.id))
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
    return resp.data


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
    return resp.data


def succeed(changed, obj, module):
    return module.exit_json(
        changed=changed,
        success=True,
        id=str(obj.id),
        comment=obj.comment,
        start_date_time=obj.end_date_time,
        end_date_time=obj.end_date_time
    )


def ensure_present(client, params, module):
    obj = get_obj(client, params, module)

    found_obj = find_obj(client, params, module)
    if found_obj is None:
        if not module.check_mode:
            obj = add_obj(client, obj, module)
        succeed(True, obj, module)
    # there not currently a case where an SDT is able to be updated
    # leave this here for potential future use
    # if not compare_obj(obj, found_obj):
    #     if not module.check_mode:
    #         # set known fields required for updating object
    #         obj = set_update_fields(obj, found_obj)
    #         update_obj(client, obj, module)
    #     succeed(True, obj, module)
    succeed(False, obj, module)


def ensure_absent(client, params, module):
    obj = find_obj(client, params, module)
    if obj is None:
        obj = get_obj(client, params, module)
        succeed(False, obj, module)
    else:
        if not module.check_mode:
            delete_obj(client, obj, module)
        succeed(True, obj, module)


def convert_datetime_to_epoch(date, module):
    try:
        return int(
            (date - datetime.datetime(1970, 1, 1)).total_seconds() * 1000
        )
    except Exception as e:
        err = 'Error converting date to epoch: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)


def parse_time(time, module):
    # parse start time format in local time
    try:
        return datetime.datetime.strptime(time, '%Y-%m-%d %H:%M')
    except Exception as e:
        err = 'Error parsing time: ' + str(e) + '\n'
        module.fail_json(msg=err, changed=False, failed=True)


def parse_sdt_type(module):
    # repeating SDT currently not supported. default to one-time
    return ONE_TIME_SDT
    # sdt_type = module.params['sdt_type']
    # # convert sdt type to int
    # if sdt_type == 'one-time':
    #     return ONE_TIME_SDT
    # elif sdt_type == 'daily':
    #     return DAILY_SDT
    # elif sdt_type == 'weekly':
    #     return WEEKLY_SDT
    # elif sdt_type == 'monthly':
    #     return MONTHLY_SDT
    # else:
    #     err = 'Unknown SDT type: ' + str(module.params['sdt_type'])
    #     module.fail_json(msg=err, changed=False, failed=True)


def parse_one_time_sdt(module):
    # default to start time of now
    if not module.params['start_time']:
        # since we're doing this calculation, generate epoch and don't convert
        module.params['start_time'] = int(time.time()) * 1000
    else:
        # parse start_time string to datetime
        module.params['start_time'] = parse_time(
            module.params['start_time'],
            module
        )
        # convert start_time to epoch
        module.params['start_time'] = (
            convert_datetime_to_epoch(module.params['start_time'], module)
        )

    # calculate end time from duration for one-time sdt
    if module.params['sdt_type'] == ONE_TIME_SDT:
        module.params['end_date_time'] = calculate_end_time(
            module.params['start_time'],
            module.params['duration'],
            module
        )
    return module.params


def selector(module):
    '''Figure out which object and which actions
    to take given the right parameters'''

    client = get_client(module.params, module)

    # translate sdt type string to int
    module.params['sdt_type'] = parse_sdt_type(module)

    # parse date arguments
    if module.params['sdt_type'] == ONE_TIME_SDT:
        module.params = parse_one_time_sdt(module)

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
            comment=dict(required=False, default=''),
            collector_id=dict(required=True, default=None),
            duration=dict(required=False, default=15),
            start_time=dict(required=False, default=None)
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
