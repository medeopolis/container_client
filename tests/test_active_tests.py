# Running incus (even on local socket) while connected to a network without internet is really really slow. 
# DNS lookups timing out? nothing is logged
# Running with no network connected is instant

import pytest

from unittest.mock import MagicMock

from container_client.client import Client

# Shared setup: In both cases we need a client.
client_for_socket = Client()
client_for_socket.connection_target = '/var/lib/incus/unix.socket' # -> this is default for incus

# This requires the Incus/LXD server to be listening on a network; see README for that setup.
client_for_https = Client()
client_for_https.connection_target='https://localhost:8443'
client_for_https.client_auth_certificates = ()

# "Globals" - setings all tests can/will use
test_instance_name = 'test-instance-2'
# Is this a dict because of replace?
test_volume_name = "{}-{}".format(test_instance_name, 'Testing volume made via API').lower().replace(' ', '-')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_list_of_instance(api_client):
  print('-> List current instances')
  # Will want recursion=2 for inventory gathering
  call_to_list_instances = api_client.request(api_path='instances?recursion=2')
  print(len(call_to_list_instances.json()['metadata']))
  print('-> List current instances completed\n')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_create_instance(api_client):
  print('-> Create instance')
  instance_create_data = {
    "name" : test_instance_name,
    "source" : {
        "type" : "image",
        "protocol" : "simplestreams",
        "server" : "https://images.linuxcontainers.org",
        "alias" : "ubuntu/24.04",
    },
    "start": True,
  }

  call_to_create_instances = api_client.request(request_type='POST', api_path='instances', post_json=instance_create_data)
  print('Our instance creation call has returned {}'.format(call_to_create_instances.__dict__))
  # If we need to wait for a status update, do so now.
  print(api_client.poll_api(call_to_create_instances))
  print('-> Create instance completed\n')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_gather_instance_info(api_client):
  print('-> Gather information about instance')

  print('- -> Network, IDs and image related output')
  gather_instance_devices = api_client.request(api_path='instances/{}'.format(test_instance_name))
  print(gather_instance_devices.json())

  print('-> Gather information about instance completed\n')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_create_volume(api_client):
  print('-> Create volume')
  storage_volume_data = {
    "config": {
      "size": "10GB",
    },
    "content_type": "filesystem",
    "description": "Testing volume made via API",
    "name": test_volume_name,
    # TODO find out what types can be. 'custom' works, in theory 'container' and 'virtual-machine' might also. What else?
    "type": "custom",
  }

  # NOTE: Hard coding default storage pool here
  create_new_volume = api_client.request(request_type='POST', api_path='storage-pools/default/volumes', post_json=storage_volume_data)
  print(create_new_volume)
  print(api_client.poll_api(create_new_volume))
  print('-> Create volume completed')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_add_storage(api_client):
  print('-> Attach volume to instance')

  instance_update_data = {
    "devices": {
      "newstore": {
        "path": "/srv/newstore",
        "pool": "default",
        "type": "disk",
        # Requires "relative path"; so presumably the volume name
        "source": test_volume_name,
      }
    }
  }

  change_instance_storage = api_client.request(request_type='PATCH', api_path='instances/{}'.format(test_instance_name), post_json=instance_update_data)
  print(change_instance_storage)
  print(api_client.poll_api(change_instance_storage))
  print(change_instance_storage.__dict__)
  print('-> Attach volume to instance')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_change_instance_limits(api_client):
  print('-> Change instance cpu/memory')
  instance_update_data = {
    "limits": {
      # Applies to VMs
      "cpu": "2",
      # Applies more to containers(?)
      "cpu": {
        "allowance": "100%",
      },
      # Mainly for VMs?
      "memory": "2GB",
      "type": "disk",
    }
  }

  change_instance_resource_limits = api_client.request(request_type='PATCH', api_path='instances/{}'.format(test_instance_name), post_json=instance_update_data)
  print(change_instance_resource_limits)
  print(api_client.poll_api(change_instance_resource_limits))
  print(change_instance_resource_limits.__dict__)

  print('-> Change instance cpu/memory completed\n')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_start_instance(api_client):
  print('-> Start instance')
  instance_start_data = {
    "action": "start",
  }

  start_instance = api_client.request(request_type='PUT', api_path='instances/{}/state'.format(test_instance_name), post_json=instance_start_data)

  print(start_instance)
  print(api_client.poll_api(start_instance))
  print(start_instance.__dict__)

  print('-> Start instance completed\n')

# @pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
# def test_agent_setup(api_client):
# print('-> Install agent in instance')
# print('-> Install agent in instance completed\n')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_execute_command(api_client):
  print('-> Execute command in instance')

  instance_execute_on_data = {
    # Command is a list used to build the execution commandline
    "command": [
      "touch",
      "/root/api-touch",
    ],
    "record-output": True,
  }

  call_to_execute_on_instances = api_client.request(request_type='POST', api_path='instances/{}/exec'.format(test_instance_name), post_json=instance_execute_on_data)

  print('')
  print('Our exec inside the instance call has returned {}'.format(call_to_execute_on_instances))

  # If we need to wait for a status update, do so now.
  polled_execute_on_instances = api_client.poll_api(call_to_execute_on_instances)
  print(polled_execute_on_instances.__dict__)

  print('-> Execute command in instance completed\n')

  print('-> Pull logs regarding instance')

  # do i need this for exec above?

  # Extract command output, just so i know it works.

  print('Try to pull log output')
  # Not convinced this bit is working, tbc though

  instance_stdout_full_path = polled_execute_on_instances.json()['metadata']['metadata']['output']['1']
  instance_stderr_full_path = polled_execute_on_instances.json()['metadata']['metadata']['output']['2']

  # Slice the API version off the start ; request() adds it 
  instance_stdout = instance_stdout_full_path[5:]
  instance_stderr = instance_stderr_full_path[5:]

  # Pull the logs and output (nothing for stdout, some lines for stdout)
  print('stdout')
  get_execute_on_instances_stdout = api_client.request(api_path=instance_stdout, skip_result_validation=True)
  print(get_execute_on_instances_stdout.content)
  api_client.request(request_type='DELETE', api_path=instance_stdout)

  print('stderr')
  get_execute_on_instances_stderr = api_client.request(api_path=instance_stderr, skip_result_validation=True)
  print(get_execute_on_instances_stderr.content)
  api_client.request(request_type='DELETE', api_path=instance_stderr)

  print('-> Pull logs regarding instance completed\n')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_stop_instance(api_client):
  print('-> Stop instance')
  instance_stop_data = {
    "action": "stop",
  }

  stop_instance = api_client.request(request_type='PUT', api_path='instances/{}/state'.format(test_instance_name), post_json=instance_stop_data)

  print(stop_instance)
  print(api_client.poll_api(stop_instance))
  print(stop_instance.__dict__)

  print('-> Stop instance completed\n')

@pytest.mark.parametrize("api_client", [client_for_socket, client_for_https])
def test_delete_instance(api_client):
  print('-> Delete instance')
  call_to_delete_instance = api_client.request(request_type='DELETE', api_path='instances/{}'.format(test_instance_name))
  print('-> Delete instance completed\n')


