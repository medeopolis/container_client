
``container_client`` is a minimal API wrapper for `LXD`_ and `Incus`_.

.. _`LXD`: https://documentation.ubuntu.com/lxd/en/latest/
.. _`Incus`: https://linuxcontainers.org/incus/

A minimal amount of error checking and data validation are performed but most is left to the caller.

Where possible, `PyLXD`_ is probably a better choice for most casual uses.

.. _`PyLXD`: https://pylxd.readthedocs.io/


Functionality
=============

Connectivity:
- Connecting to local socket: yes
- Connecting to remote host: no (not yet implemented)

Key functions to interact with the API are ``request`` (send request) and ``poll_api`` to wait for an async task to complete its background processing.
Functions ``authentication`` and ``validate`` are available if those behaviours need to be customised.


Usage
=====

API examples
------------

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


Create an instance using the ``api_client`` from the first example.

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
responsible for handling the websockets created by LXD.

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
  
  # If we need to wait for a status update, do so now.
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





Authentication examples
-----------------------

To give access to the local socket add the executing user to a suitable group (``lxd`` or ``incus-admin`` are the most likely).

Remote access is still TODO.
- if needed Document how to trigger certificate generate for API to use.
- if needed Document making certificate trusted https://linuxcontainers.org/incus/docs/main/authentication/#authentication-add-certs



