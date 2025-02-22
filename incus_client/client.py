"""
# For client:
# - handle auth (looks harder than i expected; might just offer a stub + examples)
# - error/status codes (done)
# - polling (stub in place)
# - proxy through everything else unfiltered.
# - option to choose incus or lxd as api target? currently the same.
"""

# https://stackoverflow.com/q/26964595 this question mentions https://github.com/msabramo/requests-unixsocket and the semi hostile fork
# https://gitlab.com/thelabnyc/requests-unixsocket2 as ways to provide access via the requests UX. Both have maintenance questions.
import requests_unixsocket

# For non socket communication
import requests

# Used to encode socket path
from urllib.parse import quote_plus

# Error handling; flows in via requests_unixsocket
import urllib3.exceptions
import requests.exceptions


class Client():
  """Container for API communication.

  """

  # Values taken from API documentation
  HTTP_SUCCESSFUL_SYNCHRONOUS_CODES = [ 200 ]
  HTTP_SUCCESSFUL_BACKGROUND_CODES = [ 202 ]
  HTTP_ERROR_CODES = [ 400, 401, 403, 404, 409, 412, 500 ]
  # Key = hard coded API identifier, Value = friendly text for humans
  API_STATUS_CODES = {
    100 : 'Operation created',
    101 : 'Started',
    102 : 'Stopped',
    103 : 'Running',
    104 : 'Canceling',
    105 : 'Pending',
    106 : 'Starting',
    107 : 'Stopping',
    108 : 'Aborting',
    109 : 'Freezing',
    110 : 'Frozen',
    111 : 'Thawed',
    112 : 'Error',
    113 : 'Ready',
    200 : 'Success',
    400 : 'Failure',
    401 : 'Canceled',
  }

  # requests session.
  session = None

  # Where is the server? can be overriden. UNIX socket or https URIs are supported
  connection_target = '/var/lib/incus/unix.socket'


  def authenticate(self):
    """Authentication entrypoint

    Only required for https targets
    """
    pass

  def poll_api(self, returned_data=None):
    """Manage polling for status updates on long running requests

    returned_data (default none) is what our api returned.

    Default implementation waits until an operation finishes or times out, rather than actually polling.
    """

    if returned_data == None:
      print('Data is "None"; perhaps this was called without a parameter')
      return False

    if returned_data == False:
      print('Data is "False"; perhaps this was called on the output of a failed function?')
      return False

    if returned_data.status_code not in self.HTTP_SUCCESSFUL_BACKGROUND_CODES:
      print('Data has a status code of {}, this function is not necesary'.format(returned_data.status_code))
      return returned_data

    # ok, thats the known error cases out of the way...

    try:
      # read out json content from response
      json_content = returned_data.json()
    except requests.exceptions.JSONDecodeError as rejde:
      print('Response did not contain valid json. Error was {}'.format(rejde))
      return False

    # So thats the basic validation done.
    # now we check for the operation ID
    operation_id = json_content['metadata']['id']

    print('Waiting for request to complete')

    # with operation ID in hand - we hope - we can start polling.
    # I don't know how this works... will it just sit and wait? Will I need to update some timeout?
    op_status = self.request(api_path='operations/{}/wait'.format(operation_id))
    print('Polling result: {}'.format(op_status))

    print('Status is {}. Continuing to validating current data'.format(op_status.status_code))
    # Once we're no longer polling, validity check the result.
    # Check return codes are in order
    if self.validate(op_status) is True:
      return op_status
    else:
      print('Poll validate failed on {}'.format(op_status.__dict__))
      return None


  def request(self, api_version='1.0', api_path='', auto_poll=True,
                *args, **kwargs):
    """Make request to API

    Send query to LXD or Incus API endpoint.
    api_path (default unset) should be the HTTPS URI of your remote server or path to local socket.
    auto_poll (default true) specifies if this call should wait until async operations complete
    """

    # Pull connection target from object
    connection_target = self.connection_target

    # TODO: import `re` and match on > 1st char?
    if connection_target.startswith('/'):
      self.session = requests_unixsocket.Session()

      # Use unix socket ; this is the default behaviour
      try:
        request_result = self.session.get('http+unix://{0}/{1}/{2}'.format(quote_plus(connection_target), api_version, api_path))
      except ( urllib3.exceptions.ProtocolError, requests.exceptions.ConnectionError) as uepe:
        print('Unable to connect to socket at {}, error {}'.format(connection_target, uepe))

    # Otherwise use a remote https target if connection target is so configured
    # TODO: use self.authenticate() to handle auth when i get to testing a remote service
    elif connection_target.startswith('https://'):
      self.session = requests.Session()
      try:
        request_result = self.session.get('{0}/{1}/{2}'.format(connection_target, api_version, api_path))
      except (urllib3.exceptions.ProtocolError, requests.exceptions.ConnectionError) as uepe:
        print('Unable to connect to remote server at {}, error {}'.format(connection_target, uepe))

    # Lastly just produce an error
    else:
      print('Unknown connection target: {}'.format(connection_target))
      request_result = None

    # Print out request result 
    # print(request_result.__dict__)

    # Once we're no longer polling, validity check the result.
    # Check return codes are in order
    if self.validate(request_result) is True:
      return request_result
    else:
      print('Validate failed on {}'.format(request_result.__dict__))
      return None


  def validate(self, returned_data=None):
    """Validate/verify response from API

    Uses data hard coded in to the class such as HTTP_ERROR_CODES and API_STATUS_CODES to provide a convenient way to check if a call was successful
    or not.
    """

    if returned_data == None:
      return False

    if returned_data.ok is not True:
      print('Request returned an HTTP error status: {}'.format(returned_data.status_code))
      return False

    try:
      # read out json content from response
      json_content = returned_data.json()
    except requests.exceptions.JSONDecodeError as rejde:
      print('response did not contain valid json. Error was {}'.format(rejde))
      return False

    print(json_content)

    if json_content['status_code'] < 400:
      # Assume we're OK
      return True

