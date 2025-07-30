
``container_client`` is a minimal API wrapper for `LXD`_ and `Incus`_.

.. _`LXD`: https://documentation.ubuntu.com/lxd/en/latest/
.. _`Incus`: https://linuxcontainers.org/incus/

A minimal amount of error checking and data validation are performed but most is left to the caller. All API calls should work, but only a handful
have been tested.

Where possible, `PyLXD`_ is probably a better choice for most casual uses.

.. _`PyLXD`: https://pylxd.readthedocs.io/


Functionality
=============

Connects to local (socket) and remote (HTTPs) LXD and Incus servers.

Key functions to interact with the API are ``request`` (send request) and ``poll_api`` to wait for an async task to complete its background processing.
``authentication`` function can be used to change the python ``requests.Session()`` object and ``validate`` can be changed if the existing
request/json verification doesn't suit.


Installing
==========

This is not currently distributed through pypi or similar channels. Please install it with `pip install` directly from the source repository.


Usage
=====

Authentication examples
-----------------------

To give access to the local socket add the executing user to a suitable group (``lxd`` or ``incus-admin`` are the most likely).

This example uses Shared certificates (the code assumes them), steps are from `this Incus guide`_ ; but they should work for LXD too.

.. _`this Incus guide`: https://linuxcontainers.org/incus/docs/main/howto/server_expose/

Make an Incus *server* listen on a host, in this case the server is localhost

::

  :~/source/lxd_incus_api_client$ nc -vz4 localhost 8443
  nc: connect to localhost (127.0.0.1) port 8443 (tcp) failed: Connection refused
  :~/source/lxd_incus_api_client$ incus config set core.https_address 127.0.0.1
  :~/source/lxd_incus_api_client$ nc -vz4 localhost 8443
  Connection to localhost (127.0.0.1) 8443 port [tcp/*] succeeded!

On the *server* create a trust cert for the client to use during key generation

::

  :~/source/lxd_incus_api_client$ incus config trust add laptop-localhost-client
  Client laptop-localhost-client certificate add token:
  eyJjbGllbnRfbmFtZSI6ImxhcHRvcC...DowMDowMFoifQ==

Generate a key on the **client**, providing the trust token.

::

  :~/source/lxd_incus_api_client$ incus remote add localhost 127.0.0.1 --auth-type tls
  Generating a client certificate. This may take a minute...
  Certificate fingerprint: b46951079ff5eb...69e78c85e7b807e5072
  ok (y/n/[fingerprint])? y
  Trust token for localhost: eyJjbGllbnRfbm...VQwMDowMDowMFoifQ==
  Client certificate now trusted by server: localhost

The server and client are now ready to communicate.


API examples
------------

Connecting
^^^^^^^^^^

Import the client and connect to Incus via local socket. Override ``api_client.connection_target`` to set a different socket (eg for LXD) or specify a
remote host

::

  from container_client.client import Client

  api_client = Client()
  # set api_client.connection_target here to override default

  calling_endpoint = 'instances'

  # Get basic list of instances using API 1.0
  call_to_list_instances = api_client.request(api_path=calling_endpoint)
  print('Call to instances completed\n')


Connecting to a remote host involves a couple of extra steps before API calls can succeed (see 'Authentication' further up for instructions). This
example shows connecting to localhost (using its IP to avoid certificate validation problems) using certificates created using the commandline.

::

  from container_client.client import Client

  api_client = Client()
  api_client.connection_target='https://127.0.0.1:8443'

  calling_endpoint = 'instances'

  # Get basic list of instances using API 1.0
  # Uses certificates set up by ``incus`` or ``lxc`` commands to authenticate the connection
  call_to_list_instances = api_client.request(api_path=calling_endpoint,
          client_auth_certificates=('/user/.config/incus/client.crt', '/user/.config/incus/client.key'),
          server_verification = '/user/.config/incus/servercerts/localhost.crt', )
  print('Call to instances completed\n')

Note that if testing using hostname ``localhost`` despite having the correct certificates you'll still have a validation error - the certificate
generated for localhost only covers its IPs not hostname.

::

  Unable to verify certificate provided by https://localhost:8443, error HTTPSConnectionPool(host='localhost', port=8443): Max retries exceeded with url: /1.0/instances?recursion=2 (Caused by SSLError(SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is not valid for 'localhost'. (_ssl.c:992)")))

This LXD example has no certificate verification because the servers certificate only covers localhost IPs not its public network IP.

::

  api_client = Client()
  api_client.connection_target='https://192.168.0.123:8443/'

  calling_endpoint = 'instances'
  call_to_list_instances = api_client.request(api_path=calling_endpoint,
          client_auth_certificates=('/user/.config/lxc/client.crt', '/user/.config/lxc/client.key'),)



Actions
^^^^^^^

Create an instance on the remote server using the ``api_client`` from the first section.

In this example the initial request (involving a POST and json data) is an ``async`` task and its status is captured in ``call_to_create_instances``.
``poll_api`` is used to wait for instance creation to complete before printing the output.

::

  instance_create_data = {
    "name" : "test-instance-3",
    "source" : {
        "type" : "image",
        "protocol" : "simplestreams",
        "server" : "https://images.linuxcontainers.org",
        "alias" : "ubuntu/22.04",
    }
  }

  call_to_create_instances = api_client.request(request_type='POST', api_path=calling_endpoint, post_json=instance_create_data)
  print('Our instance creation call has returned {}'.format(call_to_create_instances))
  print(api_client.poll_api(call_to_create_instances))

Executing commands is another async task which comes in two parts: executing the task and querying for output. Querying for output is what sets the
two approaches appart. The first (as done below) sets ``"record-output": True``, the logs are then stored by LXD and we have to query for them as a
second stage. Alternatively ``record-output`` can be ommitted and ``"wait-for-websocket": True`` set instead. In that instance the caller is
responsible for handling the websockets created by LXD by overriding ``poll_api`` or adding an additional function.

First we set up the path and data required for the execute command.

::

  instance_to_execute_against = 'test-instance-3'
  instance_execute_endpoint = 'instances/{}/exec'.format(instance_to_execute_against)
  instance_execute_on_data = {
    # Command is a list used to build the execution commandline
    "command": [
      "touch",
      "/tmp/api-touch"
    ],
    "record-output": True,
  }
  
  call_to_execute_on_instances = api_client.request(request_type='POST', api_path=instance_execute_endpoint, post_json=instance_execute_on_data)
  polled_execute_on_instances = api_client.poll_api(call_to_execute_on_instances)
  
Then we gather the log output , print them out, and delete the LXD stored copy.

::

  print('Try to pull log output')
  # Is there a better way to access these paths? Not that I can see.
  instance_stdout_full_path = polled_execute_on_instances.json()['metadata']['metadata']['output']['1']
  instance_stderr_full_path = polled_execute_on_instances.json()['metadata']['metadata']['output']['2']
  
  # Slice the API version off the start ; request() adds it so we work around that choice here
  instance_stdout = instance_stdout_full_path[5:]
  instance_stderr = instance_stderr_full_path[5:]
  
  # Pull the logs and output what w have (nothing for stdout, some lines for stdout)
  print('stdout')
  get_execute_on_instances_stdout = api_client.request(api_path=instance_stdout, skip_validation=True)
  print(get_execute_on_instances_stdout.content)
  api_client.request(request_type='DELETE', api_path=instance_stdout)
  
  print('stderr')
  get_execute_on_instances_stderr = api_client.request(api_path=instance_stderr, skip_validation=True)
  print(get_execute_on_instances_stderr.content)
  api_client.request(request_type='DELETE', api_path=instance_stderr)


On error, ``None`` is returned along with an error message.

::

  Unable to verify certificate provided by https://localhost:8443, error HTTPSConnectionPool(host='localhost', port=8443): Max retries exceeded with url: /1.0/instances?recursion=2 (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:992)')))

  Unable to connect to host https://farhost:8443, error HTTPSConnectionPool(host='farhost', port=8443): Max retries exceeded with url: /1.0/instances?recursion=2 (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x7f724b16e610>: Failed to resolve 'farhost' ([Errno -2] Name or service not known)"))


Running tests
^^^^^^^^^^^^^

Some basic ``pytest`` based tests are included. In order to use them:
- Configure incus to listen on localhost and set up certificates (see ``Authentication examples``)
- Optionally, create a new Python virtual environment to test in, eg
::

  virtualenv ~/.venvs/incusapi/

- Install packages from ``requirements-test.txt``
::

  pip install -r requirements-test.txt

- Run tests
::

  pytest --cov

