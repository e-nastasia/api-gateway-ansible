#!/usr/bin/python

# API Gateway Ansible Modules
#
# Modules in this project allow management of the AWS API Gateway service.
#
# Authors:
#  - Brian Felton <github: bjfelton>
#
# apigw_rest_api
#    Manage creation, update, and removal of API Gateway REST APIs
#

# MIT License
#
# Copyright (c) 2016 Brian Felton, Emerson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


DOCUMENTATION='''
module: apigw_rest_api
author: Brian Felton (@bjfelton)
short_description: Add, update, or remove REST API resources
description:
  - An Ansible module to add, update, or remove REST API resources for AWS API Gateway.
version_added: "2.2"
options:
  name:
    description:
      - The name of the rest api on which to operate
    required: True
  description:
    description:
      - A description for the rest api
    required: False
  state:
    description:
      - Determine whether to assert if api should exist or not
    choices: ['present', 'absent']
    default: 'present'
    required: False
requirements:
    - python = 2.7
    - boto
    - boto3
notes:
    - This module requires that you have boto and boto3 installed and that your credentials are created or stored in a way that is compatible (see U(https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration)).
'''

EXAMPLES = '''
- name: Add rest api to Api Gateway
  hosts: localhost
  gather_facts: False
  connection: local
  tasks:
    - name: Create rest api
      apigw_rest_api:
        name: 'docs.example.io'
        description: 'stolen straight from the docs'
        state: present
      register: api

    - name: debug
      debug: var=api

- name: Rest api from Api Gateway
  hosts: localhost
  gather_facts: False
  connection: local
  tasks:
    - name: Create rest api
      apigw_rest_api:
        name: 'docs.example.io'
        state: absent
      register: api

    - name: debug
      debug: var=api
'''

RETURN = '''
### Sample create response
{
    "api": {
        "ResponseMetadata": {
            "HTTPHeaders": {
                "content-length": "79",
                "content-type": "application/json",
                "date": "Thu, 27 Oct 2016 11:55:05 GMT",
                "x-amzn-requestid": "<request id here>"
            },
            "HTTPStatusCode": 201,
            "RequestId": "<request id here>"
            "RetryAttempts": 0
        },
        "createdDate": "2016-10-27T06:55:05-05:00",
        "description": "example description",
        "id": "c8888abcde",
        "name": "example-api"
    },
    "changed": true,
    "invocation": {
        "module_args": {
            "description": "examble description",
            "name": "example-api",
            "state": "present"
        }
    }
}
'''

__version__ = '${version}'

try:
  import boto3
  import boto
  from botocore.exceptions import BotoCoreError
  HAS_BOTO3 = True
except ImportError:
  HAS_BOTO3 = False

class ApiGwRestApi:
  def __init__(self, module):
    """
    Constructor
    """
    self.module = module
    if (not HAS_BOTO3):
      self.module.fail_json(msg="boto and boto3 are required for this module")
    self.client = boto3.client('apigateway')

  @staticmethod
  def _define_module_argument_spec():
    """
    Defines the module's argument spec
    :return: Dictionary defining module arguments
    """
    return dict( name=dict(required=True),
                 description=dict(required=False),
                 state=dict(default='present', choices=['present', 'absent'])
    )

  def _retrieve_rest_api(self):
    """
    Retrieve all rest APIs in the account and match it against the provided name
    :return: Result matching the provided api name or an empty hash
    """
    response = None
    try:
      results = self.client.get_rest_apis()
      id = self.module.params.get('name')

      api = list(filter(lambda result: result['name'] == id, results['items']))

      if len(api):
        response = api[0]
    except BotoCoreError as e:
      self.module.fail_json(msg="Encountered fatal error calling boto3 get_rest_apis function: {0}".format(e))

    return response

  @staticmethod
  def _is_changed(api, params):
    """
    Determine if the discovered api differs from the user-provided params
    :param api: Result from _retrieve_rest_api()
    :param params: Module params
    :return: Boolean telling if result matches params
    """
    return api.get('name') != params.get('name') or api.get('description') != params.get('description')

  def _create_or_update_api(self, api):
    """
    When state is 'present', determine if api creation or update is appropriate
    :return: (changed, result)
              changed: Boolean showing whether a change occurred
              result: The resulting rest api object
    """
    changed = False
    if not api:
      changed, api = self._create_api()
    elif ApiGwRestApi._is_changed(api, self.module.params):
      changed, api = self._update_api(api.get('id'))

    return changed, api

  def _maybe_delete_api(self, api):
    """
    Delete's the discovered api via boto3, as appropriate
    :param api: The discovered API
    :return: (changed, result)
              changed: Boolean showing whether a change occurred
              result: Empty hash
    """
    changed = False
    if api:
      try:
        if not self.module.check_mode:
          api = self.client.delete_rest_api(restApiId=api.get('id'))
        changed = True
      except BotoCoreError as e:
        self.module.fail_json(msg="Encountered fatal error calling boto3 delete_rest_api function: {0}".format(e))

    return changed, api

  def _update_api(self, id):
    """
    Updates the API with the provided id using boto3
    :param id: Id of the discovered rest api
    :return: (changed, result)
              changed: Boolean showing whether a change occurred
              result: The resulting rest api object after the update
    """
    api = None
    description = "" if self.module.params.get('description') is None else self.module.params.get('description')
    try:
      if not self.module.check_mode:
        api = self.client.update_rest_api(restApiId=id, patchOperations=[
          {'op': 'replace', 'path': '/name', 'value': self.module.params.get('name')},
          {'op': 'replace', 'path': '/description', 'value': description},
        ])
    except BotoCoreError as e:
      self.module.fail_json(msg="Encountered fatal error calling boto3 update_rest_api function: {0}".format(e))
    return True, api

  def _create_api(self):
    """
    Creates a new api based on user input
    :return: (True, result)
              True
              result: The resulting rest api object after the create
    """
    api = None
    kwargs = dict(name=self.module.params.get('name'))
    if self.module.params.get('description'):
      kwargs['description'] = self.module.params.get('description')
    try:
      if not self.module.check_mode:
        api = self.client.create_rest_api(**kwargs)
    except BotoCoreError as e:
      self.module.fail_json(msg="Encountered fatal error calling boto3 create_rest_api function: {0}".format(e))
    return True, api

  def process_request(self):
    """
    Process the user's request -- the primary code path
    :return: Returns either fail_json or exit_json
    """
    params = self.module.params
    api = self._retrieve_rest_api()
    changed = False

    if params.get('state') == 'absent':
      changed, api = self._maybe_delete_api(api)
    else:
      changed, api = self._create_or_update_api(api)

    return self.module.exit_json(changed=changed, api=api)


def main():
    """
    Instantiates the module and calls process_request.
    :return: none
    """
    module = AnsibleModule(
        argument_spec=ApiGwRestApi._define_module_argument_spec(),
        supports_check_mode=True
    )

    rest_api = ApiGwRestApi(module)
    rest_api.process_request()

from ansible.module_utils.basic import *  # pylint: disable=W0614
if __name__ == '__main__':
    main()
