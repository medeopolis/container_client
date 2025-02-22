
import pytest

from incus_client.client import Client

class ReturnedDataStub:
  status_code = 999
  def json():
    # TODO: add a test for when this isn't present
    # E     TypeError: 'NoneType' object is not subscriptable
    return {
      'metadata': { 'id': 'uuid-string-here' }
      }

# Just import
def test_class_smoketest():
  api_client = Client()
  assert api_client is not None

# authenticate test, its just a pass atm
def test_class_fn_authenticate():
  api_client = Client()
  api_client_auth = api_client.authenticate()
  assert api_client_auth is None

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

# What happens if we don't have a polling return code?
def test_class_fn_poll_not_202():
  returned_data = ReturnedDataStub
  returned_data.status_code = 400
  api_client = Client()
  api_client_poll = api_client.poll_api(returned_data=returned_data)
  assert api_client_poll is returned_data

# What happens if we have a polling return code?
# broken
# >     print('Status is {}. Continuing to validating current data'.format(op_status.status_code))
# E     AttributeError: 'NoneType' object has no attribute 'status_code'
def test_class_fn_poll_code_202_valid_json():
  returned_data = ReturnedDataStub
  returned_data.status_code = 202
  api_client = Client()
  api_client_poll = api_client.poll_api(returned_data=returned_data)
  assert api_client_poll is None

# TODO: test_class_fn_poll_code_202_not_valid_json
# TODO: valid json, no metadata id; should match KeyError

# request filesystem path
# need to mock requests for this one to succeed
def test_class_fn_request_filesystem():
  api_client = Client()
  api_client.connection_target = '/path/to/place'
  # E     UnboundLocalError: cannot access local variable 'request_result' where it is not associated with a value
  api_client_request = api_client.request()
  assert api_client_request is None

# request remote web server path
# Need to write the code this will check
# then need to mock requests for this one to succeed
def test_class_fn_request_https():
  api_client = Client()
  api_client.connection_target = 'https://example.org'
  api_client_request = api_client.request()
  assert api_client_request is None

def test_class_fn_invalid_request_type():
  api_client = Client()
  api_client.connection_target = 'abc@123'
  api_client_request = api_client.request()
  assert api_client_request is None

# request remote web server path
def test_class_fn_validate_no_returned_data():
  api_client = Client()
  api_client_validate_nrd = api_client.validate()
  assert api_client_validate_nrd is False

# request remote web server path
def test_class_fn_validate():
  api_client = Client()
  returned_data = ReturnedDataStub
  returned_data.ok = True
  # E     UnboundLocalError: cannot access local variable 'request_result' where it is not associated with a value
  api_client_validate = api_client.validate()
  assert api_client_validate is False

