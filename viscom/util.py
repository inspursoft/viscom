from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import os

class SSHUtil:
  @classmethod
  def _get_ssh_client(cls, custom_conf=None):
    cls.client = SSHClient()
    cls.client.set_missing_host_key_policy(AutoAddPolicy())
    if custom_conf:
      hostname=custom_conf["HOST"]
      username=custom_conf["USERNAME"]
      password=custom_conf["PASSWORD"]
    cls.client.connect(hostname=hostname, username=username, password=password)
      
  @classmethod
  def exec_script(cls, app, command, *args, conf=None):
    try:
      cls._get_ssh_client(custom_conf=conf)
      exec_command = '{} {}'.format(command, ' '.join(args))
      app.logger.debug(exec_command)
      _, stdout, _ = cls.client.exec_command(exec_command)
      return stdout.read().decode("utf-8")
    except Exception as e:
      app.logger.error("Failed to execute script: %s with error: %s", "{} {}".format(filepath, *args), e)
    finally:
      if cls.client:
        cls.client.close()
 
  @classmethod
  def secure_copyfile(cls, app, src, dest, conf=None):
    try:
      cls._get_ssh_client(custom_conf=conf)
      with SCPClient(cls.client.get_transport()) as scp:
        scp.put(src, remote_path=dest)
    except Exception as e:
      app.logger.error("Failed to execute secure copyfile with error: %s", e)

  @classmethod
  def secure_copy(cls, app, src, dest, conf=None):
    try:
      cls._get_ssh_client(custom_conf=conf)
      with SCPClient(cls.client.get_transport()) as scp:
        for root, dirs, files in os.walk(src, topdown=True):
          for dir in dirs:
            scp.put(os.path.join(root, dir), remote_path=dest, recursive=True)
            for file in files:
              scp.put(os.path.join(root, file), remote_path=dest)
    except Exception as e:
      app.logger.error("Failed to execute secure copy with error: %s", e)