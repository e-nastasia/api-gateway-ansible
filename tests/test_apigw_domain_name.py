#!/usr/bin/python
# TODO: License goes here

import library.apigw_domain_name as apigw_domain_name
from library.apigw_domain_name import ApiGwDomainName
import mock
from mock import patch
from mock import create_autospec
from mock import ANY
import unittest
import boto
from botocore.exceptions import BotoCoreError, ClientError

class TestApiGwDomainName(unittest.TestCase):

  def setUp(self):
    self.module = mock.MagicMock()
    self.module.check_mode = False
    self.module.exit_json = mock.MagicMock()
    self.module.fail_json = mock.MagicMock()
    self.domain_name  = ApiGwDomainName(self.module)
    self.domain_name.client = mock.MagicMock()
    self.domain_name.module.params = {
      'name': 'testify',
      'cert_name': 'cert-name',
      'cert_body': 'cert-body',
      'cert_private_key': 'cert-private-key',
      'cert_chain': 'cert-chain',
      'state': 'present',
    }
    reload(apigw_domain_name)

  def test_boto_module_not_found(self):
    # Setup Mock Import Function
    import __builtin__ as builtins
    real_import = builtins.__import__

    def mock_import(name, *args):
      if name == 'boto': raise ImportError
      return real_import(name, *args)

    with mock.patch('__builtin__.__import__', side_effect=mock_import):
      reload(apigw_domain_name)
      ApiGwDomainName(self.module)

    self.module.fail_json.assert_called_with(msg='boto and boto3 are required for this module')

  def test_boto3_module_not_found(self):
    # Setup Mock Import Function
    import __builtin__ as builtins
    real_import = builtins.__import__

    def mock_import(name, *args):
      if name == 'boto3': raise ImportError
      return real_import(name, *args)

    with mock.patch('__builtin__.__import__', side_effect=mock_import):
      reload(apigw_domain_name)
      ApiGwDomainName(self.module)

    self.module.fail_json.assert_called_with(msg='boto and boto3 are required for this module')

  @patch.object(apigw_domain_name, 'boto3')
  def test_boto3_client_properly_instantiated(self, mock_boto):
    ApiGwDomainName(self.module)
    mock_boto.client.assert_called_once_with('apigateway')

  def test_process_request_calls_get_domain_name_and_stores_result_when_invoked(self):
    self.domain_name.client.get_domain_name = mock.MagicMock(return_value='found it!')

    self.domain_name.process_request()

    self.assertEqual('found it!', self.domain_name.me)
    self.domain_name.client.get_domain_name.assert_called_once_with(domainName='testify')

  def test_process_request_stores_None_result_when_not_found_in_get_domain_name_result(self):
    self.domain_name.client.get_domain_name = mock.MagicMock(side_effect=ClientError({'Error': {'Code': 'x NotFoundException x'}}, 'xxx'))

    self.domain_name.process_request()

    self.assertEqual(None, self.domain_name.me)
    self.domain_name.client.get_domain_name.assert_called_once_with(domainName='testify')

  def test_process_request_calls_fail_json_when_get_domain_name_raises_exception(self):
    self.domain_name.client.get_domain_name = mock.MagicMock(side_effect=BotoCoreError())

    self.domain_name.process_request()

    self.domain_name.client.get_domain_name.assert_called_once_with(domainName='testify')
    self.domain_name.module.fail_json.assert_called_once_with(
      msg='Error when getting domain_name from boto3: An unspecified error occurred'
    )

  def test_define_argument_spec(self):
    result = ApiGwDomainName._define_module_argument_spec()
    self.assertIsInstance(result, dict)
    self.assertEqual(result, dict(
                     name=dict(required=True, aliases=['domain_name']),
                     cert_name=dict(required=False),
                     cert_body=dict(required=False),
                     cert_private_key=dict(required=False),
                     cert_chain=dict(required=False),
                     state=dict(default='present', choices=['present', 'absent']),
    ))

  @patch.object(apigw_domain_name, 'AnsibleModule')
  @patch.object(apigw_domain_name, 'ApiGwDomainName')
  def test_main(self, mock_ApiGwDomainName, mock_AnsibleModule):
    mock_ApiGwDomainName_instance      = mock.MagicMock()
    mock_AnsibleModule_instance     = mock.MagicMock()
    mock_ApiGwDomainName.return_value  = mock_ApiGwDomainName_instance
    mock_AnsibleModule.return_value = mock_AnsibleModule_instance

    apigw_domain_name.main()

    mock_ApiGwDomainName.assert_called_once_with(mock_AnsibleModule_instance)
    assert mock_ApiGwDomainName_instance.process_request.call_count == 1


if __name__ == '__main__':
    unittest.main()

