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
import ssl

import logging

logger = logging.getLogger(__name__)


class Client():
  """Container for API communication.

  """

  # Values taken from API documentation
  HTTP_SUCCESSFUL_SYNCHRONOUS_CODES = [ 200 ]
  # Trying this with 100 added; its not in the API spec.
  HTTP_SUCCESSFUL_BACKGROUND_CODES = [ 100, 202 ]
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
  client_auth_certificates = None
  server_verification = None

  # Where is the server? can be overriden. UNIX socket or https URIs are supported
  connection_target = '/var/lib/incus/unix.socket'

  logger.info('Client')

  def authenticate(self, client_auth_certificates=None, server_verification=False):
    """Authentication entrypoint

    Only required for https targets

    client_auth_certificates - Path to a certificate or tuple of certificates
    server_verification (default False) when a path to a server certificate is provided, turns on verification
    """

    logger.info('Starting authentication process')

    if self.client_auth_certificates == None:
      logger.warning('self.client_auth_certificates == None')
      if client_auth_certificates == None:
        logger.warning('A certificate in PEM format or a tuple of (crt,key) files must be provided')
        return None
      else:
        logger.warning('Setting self.client_auth_certificates to {}'.format(client_auth_certificates))
        self.client_auth_certificates = client_auth_certificates
    else:
      logger.warning('self.client_auth_certificates already set to {}'.format(self.client_auth_certificates))

    # Now self.client_auth_certificates is set, use that
    self.session.cert = self.client_auth_certificates

    if self.server_verification == None:
      logger.warning('self.server_verification == None')
      if server_verification in [ None, False ]:
        logger.warning('HTTPs server verification is turned off')
        self.session.verify = False
      else:
        logger.warning('HTTPS verification turned on using {}'.format(server_verification))
        self.server_verification = server_verification
    else:
      logger.warning('self.server_verification already set to {}'.format(self.server_verification))

    # Using self.server_verification, enable verification - if its requested.
    self.session.verify = self.server_verification


  def poll_api(self, returned_data=None):
    """Manage polling for status updates on long running requests

    Currently blocks and waits rather than polling.

    returned_data (default None) is a requests.Response object with what our api returned.

    Default implementation waits until an operation finishes or times out, rather than actually polling.
    """

    if returned_data == None:
      logging.info('Data is "None"; perhaps this was called without a parameter')
      return False

    if returned_data == False:
      logging.info('Data is "False"; perhaps this was called on the output of a failed function?')
      return False

    if returned_data.status_code not in self.HTTP_SUCCESSFUL_BACKGROUND_CODES:
      logging.info('Data has a status code of {}, polling is not necesary'.format(returned_data.status_code))
      return returned_data

    # ok, thats the known error cases out of the way...

    # This duplicats validate() but I'd have to change it to return json_content instead of bool in order to re use it here.
    try:
      # read out json content from response
      json_content = returned_data.json()
    except requests.exceptions.JSONDecodeError as rejde:
      logging.warning('Response did not contain valid json. Error was {}'.format(rejde))
      return False

    # So thats the basic validation done.
    # now we check for the operation ID
    # TODO: try/catch this
    operation_id = json_content['metadata']['id']

    logging.info('Waiting for request to complete')

    # with operation ID in hand - we hope - we can start polling.
    # I don't know how this works... will it just sit and wait? Will I need to update some timeout?
    op_status = self.request(api_path='operations/{}/wait'.format(operation_id))
    # logging.warning('Polling result: {}'.format(op_status.__dict__))
    logging.warning('Polling result: {}'.format(op_status))

    logging.info('Status is {}. Continuing to validate current data'.format(op_status.status_code))
    # Once we're no longer polling, validity check the result.
    # Check return codes are in order
    if self.validate(op_status) is True:
      return op_status
    else:
      logging.warning('Poll validate failed on {}'.format(op_status.__dict__))
      return None


  def request(self, api_version='1.0', request_type='GET', api_path='', post_json=None,
               skip_result_validation=False, client_auth_certificates=None, server_verification=False,
               *args, **kwargs):
    """Make request to API

    Send query to LXD or Incus API endpoint.
    api_version (default 1.0) allows choosing a version for the API
    request_type (default 'GET') allows choosing how the request is made
    api_path (default unset) should be the HTTPS URI of your remote server or path to local socket.
    post_json (default None) a python dictionary which will be passed to requests's json parameter.
    skip_result_validation (default False) prevents json returned from the API being checked
    client_auth_certificates (default None) is a path to a pem or a tuple of client cert, client key.
    server_verification (default False) when a path to a server certificate is provided, turns on verification

    Returns ``requests.Response`` (provided by Python ``requests`` or ``requests_unixsocket``) or ``None`` on error.
    """

    # Pull connection target from object
    connection_target = self.connection_target
    logging.warning('Connection target is {}'.format(connection_target))

    if post_json is None and request_type in ['PUT', 'PATCH', 'POST']:
      logging.info('This request type ({}) requires post_json be provided'.format(request_type))

    # import `re` and match on > 1st char?
    if connection_target.startswith('/'):
      # Use unix socket ; this is the default behaviour
      self.session = requests_unixsocket.Session()

      try:
        request_result = self.session.request(request_type,
                                'http+unix://{0}/{1}/{2}'.format(quote_plus(connection_target), api_version, api_path), json=post_json)
      except ( urllib3.exceptions.ProtocolError, requests.exceptions.ConnectionError) as uepe:
        logging.warning('Unable to connect to socket at {}, error {}'.format(connection_target, uepe))
        # Raise error to caller?
        return None

    # Otherwise use a remote https target if connection target is so configured
    elif connection_target.startswith('https://'):
      self.session = requests.Session()

      logging.info('Calling to authenticate')
      self.authenticate(client_auth_certificates, server_verification)

      # TODO: catch exceptions when port is wrong/absent
      try:
        request_result = self.session.request(request_type,
                                '{0}/{1}/{2}'.format(connection_target, api_version, api_path), json=post_json)
      # except (urllib3.exceptions.ProtocolError, requests.exceptions.ConnectionError) as uepe:
      except urllib3.exceptions.ProtocolError as uepe:
        logging.error('Unable to connect to remote server at {}, error {}'.format(connection_target, uepe))
        # Raise error to caller?
        return None
      except (ssl.SSLCertVerificationError, urllib3.exceptions.SSLError, requests.exceptions.SSLError) as sscve:
        logging.error('Unable to verify certificate provided by {}, error {}'.format(connection_target, sscve))
        # Raise error to caller?
        return None
      except urllib3.exceptions.MaxRetryError as uemre:
        logging.error('Unable to establish stable connection with {}, error {}'.format(connection_target, sscve))
        # Raise error to caller?
        return None
      except requests.exceptions.ConnectionError as rece:
        logging.error('Unable to connect to host {}, error {}'.format(connection_target, rece))
        # Raise error to caller?
        return None
      except urllib3.exceptions.NameResolutionError as uenre:
        logging.error('Unable to resolve host {}, error {}'.format(connection_target, uenre))
        # Raise error to caller?
        return None

    # Lastly just produce an error
    else:
      logging.warning('Unknown connection target: {}'.format(connection_target))
      return None

    # Print out request result 
    # logging.debug('Request result headers: {}'.format(request_result.headers))
    # logging.debug('Request result full: {}'.format(request_result.__dict__))

    # We don't always want validation, it may not be appropriate (eg pulling logs seems to cause this)
    if skip_result_validation is True:
      logging.info('Skipping validation and returning')
      return request_result

    # Check return codes are in order
    if self.validate(request_result) is True:
      return request_result
    else:
      logging.warning('Request validate failed on {}'.format(request_result.__dict__))
      # Raise error instead of return none?
      return None


  def validate(self, returned_data=None):
    """Validate/verify response from API

    Uses data hard coded in to the class such as HTTP_ERROR_CODES and API_STATUS_CODES to provide a convenient way to check if a call was successful
    or not.
    """

    if returned_data == None:
      return False

    if returned_data.ok is not True:
      logging.info('Request returned an HTTP error status: {}'.format(returned_data.status_code))
      return False

    try:
      # read out json content from response
      json_content = returned_data.json()
    except requests.exceptions.JSONDecodeError as rejde:
      logging.warning('Response did not contain valid json. Error was {}'.format(rejde))
      return False

    # logging.debug('Validated json content: {}'.format(json_content))

    # When an instance or volume already exists there is error_code 409 and status_code 0. That may or may not actually be OK depending on what was planned...
    # but I think its OK for my purposes.
    if returned_data.status_code not in self.HTTP_ERROR_CODES:
      # Assume we're OK
      return True

