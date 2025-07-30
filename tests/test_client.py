
import pytest

from unittest.mock import MagicMock

from container_client.client import Client

# Just import
def test_class_smoketest():
  api_client = Client()
  assert api_client is not None

### Authentication related tests

def test_class_fn_authenticate_no_params():
  api_client = Client()
  api_client_auth = api_client.authenticate()
  assert api_client_auth is None

def test_class_fn_authenticate_none_cert_yes_verification():
  api_client = Client()
  api_client.session = MagicMock()
  api_client_auth = api_client.authenticate(client_auth_certificates=None, server_verification=True)
  assert api_client_auth is None

def test_class_fn_authenticate_yes_cert_none_verification():
  api_client = Client()
  api_client.session.verify = MagicMock(return_value=True)
  api_client_auth = api_client.authenticate(client_auth_certificates='/path/to/cert', server_verification=None)
  assert api_client.server_verification == None
  assert api_client.session.cert == '/path/to/cert'
  assert api_client.session.verify.called == True
  assert api_client.session.verify == False

def test_class_fn_authenticate_yes_cert_false_verification():
  api_client = Client()
  api_client.session = MagicMock()
  api_client_auth = api_client.authenticate(client_auth_certificates='certificate-file.pem', server_verification=False)
  assert api_client.server_verification == None
  assert api_client.session.cert == 'certificate-file.pem'
  assert api_client.session.verify == False

def test_class_fn_authenticate_yes_cert_missing_verification():
  api_client = Client()
  api_client.session = MagicMock()
  api_client_auth = api_client.authenticate(client_auth_certificates='testing.cert')
  assert api_client.server_verification == None
  assert api_client.session.cert == 'testing.cert'
  assert api_client.session.verify == False

# NOTE: This proves our data validation isn't good enough as we shouldn't allow session.cert to be a bool
def test_class_fn_authenticate_yes_cert_yes_verification():
  api_client = Client()
  api_client.session = MagicMock()
  api_client_auth = api_client.authenticate(client_auth_certificates=True, server_verification=True)
  assert api_client.session.cert == True
  assert api_client.session.verify == True


### Set of tests for the 'short circuits' in Client.poll_api

# What happens if we have no returned data?
def test_class_fn_poll_no_returned_data():
  api_client = Client()
  api_client_poll = api_client.poll_api()
  assert api_client_poll is False

def test_class_fn_poll_None_data():
  returned_data = None
  api_client = Client()
  api_client_poll = api_client.poll_api(returned_data=returned_data)
  assert api_client_poll is False

def test_class_fn_poll_False_data():
  returned_data = False
  api_client = Client()
  api_client_poll = api_client.poll_api(returned_data=returned_data)
  assert api_client_poll is False

# If status code is 202; the supplied returned_data is given back by poll_api without any further checking
def test_class_fn_poll_code_202():
  returned_data = MagicMock()
  returned_data.status_code.return_value = 202
  api_client = Client()
  api_client_poll = api_client.poll_api(returned_data=returned_data)
  assert api_client_poll is returned_data


### Other tests for Client.poll_api after the short circuits

def test_class_fn_poll_json_function_with_metadata_id_successful_validation():
  returned_data = MagicMock()
  returned_data.json = MagicMock(return_value={ 'metadata': { 'id': 123 }} )
  returned_data.status_code = 200
  api_client = Client()
  api_client.request = MagicMock()
  api_client.validate = MagicMock(return_value=True)
  api_client_poll = api_client.poll_api(returned_data=returned_data)
  # What is it? 
  # assert api_client_poll is ...

def test_class_fn_poll_json_direct_with_metadata_id_successful_validation():
  returned_data = {'status_code': 200 , 'metadata': { 'id': 123 }}
  api_client = Client()
  api_client.request = MagicMock()
  api_client.validate = MagicMock(return_value=True)
  api_client_poll = api_client.poll_api(returned_data=returned_data)
  # What is it? 
  # assert api_client_poll is ...

# # FIXME: for some reason this status code is not being handled correctly by returned_data['status_code']
# def test_class_fn_poll_json_function_without_metadata_id():
#   returned_data = MagicMock()
#   returned_data.json = MagicMock(return_value='bad')
#   returned_data.status_code.return_value = 200
#   api_client = Client()
#   api_client.request = MagicMock()
#   api_client.validate = MagicMock(return_value=True)
#   api_client_poll = api_client.poll_api(returned_data=returned_data)
#   assert api_client_poll is False

# # FIXME: for some reason this status code is not being handled correctly by returned_data['status_code']
# def test_class_fn_poll_json_direct_without_metadata_id():
#   # TODO: try this as string, as empty dict, other options?
#   returned_data = { 'metadata': '' , 'status_code': 200 }
#   api_client = Client()
#   api_client.request = MagicMock()
#   api_client.validate = MagicMock(return_value=True)
#   api_client_poll = api_client.poll_api(returned_data=returned_data)
#   assert api_client_poll is False

# # FIXME: for some reason this status code is not being handled correctly by returned_data['status_code']
# def test_class_fn_poll_json_function_with_metadata_id_failed_validation():
#   returned_data = MagicMock()
#   returned_data.json = MagicMock(return_value={ 'metadata': { 'id': 123 }} )
#   returned_data.status_code = 200
#   api_client = Client()
#   api_client.request = MagicMock()
#   api_client.validate = MagicMock(return_value=False)
#   api_client_poll = api_client.poll_api(returned_data=returned_data)
#   assert api_client_poll is None

# TODO: test poll_api handles invalid status codes? is that its problem?


### Tests for Client.request

# Request to API using filesystem path
def test_class_fn_request_filesystem():
  api_client = Client()
  api_client.connection_target = '/path/to/place'
  api_client.session = MagicMock()
  api_client_request = api_client.request()
  assert api_client_request is None

# test case where socket path is valid, and api returns successfully
# test case where socket path is valid, but api returns error/s


# Request to API using remote web server
# Need to write the code this will check
def test_class_fn_request_https():
  api_client = Client()
  api_client.connection_target = 'https://api.example.org'
  api_client.session = MagicMock()
  api_client_request = api_client.request()
  assert api_client_request is None

# test case where web api connection is valid, and api returns successfully
# test case where api connection is valid, but api returns error/s

# We look for "starts with '/'" and "starts with https://" to decide which client to use
# This test ensures when its a different case we handle it
def test_class_fn_invalid_request_type():
  api_client = Client()
  api_client.connection_target = 'abc@123'
  api_client_request = api_client.request()
  assert api_client_request is None

#  post_json is None and request_type in ['PUT', 'PATCH', 'POST'] -> will error; tbd
# post_json is set and request_type in ['PUT', 'PATCH', 'POST'] -> should pass

# Test request has completed successfully and we want to skip validation -> ret requests.response
# Test request has completed successfully and we want validation and it succeeds -> ret requests.response
# Test request has completed successfully and we want validation and it fails -> ret noen

### Testing Client.validate function (usually called by other methods)

# when we aren't given anything to validate
def test_class_fn_validate_no_returned_data():
  api_client = Client()
  api_client_validate_nrd = api_client.validate()
  assert api_client_validate_nrd is False

# when our returned requests.Response is not ok/good
def test_class_fn_validate():
  api_client = Client()
  returned_data = MagicMock()
  returned_data.ok = False
  api_client_validate = api_client.validate()
  assert api_client_validate is False

# when our returned requests.Response is OK but the json() method payload is invalid
def test_class_fn_validate():
  api_client = Client()
  returned_data = MagicMock()
  returned_data.ok = True
  returned_data.json = MagicMock(return_value='bad')
  api_client_validate = api_client.validate()
  assert api_client_validate is False

# when our returned requests.Response is OK and the json() method payload is valid and a good return code
def test_class_fn_validate():
  api_client = Client()
  returned_data = MagicMock()
  returned_data.ok = True
  returned_data.json = MagicMock(return_value={ 'status_code': 200 })
  api_client_validate = api_client.validate()
  assert api_client_validate is False

# when our returned requests.Response is OK and the json() method payload is valid but a bad return code
def test_class_fn_validate():
  api_client = Client()
  returned_data = MagicMock()
  returned_data.ok = True
  returned_data.json = MagicMock(return_value={ 'status_code': 499 })
  api_client_validate = api_client.validate()
  assert api_client_validate is False

