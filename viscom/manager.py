import viscom.db as db
from viscom.model import VisComException, CaptureItem
import datetime, os
from viscom.util import SSHUtil
import shutil

def get_upload_path(app, group_name):
  return os.path.join(app.instance_path, "upload", group_name)

def sync_remote_file(app, source_path=None, group_name=None, is_remove=False):
  custom_conf = {
    "HOST": app.config["SSH_HOST"],
    "USERNAME": app.config["SSH_USERNAME"],
    "PASSWORD": app.config["SSH_PASSWORD"]
  }
  if is_remove:
    if not group_name:
      raise VisComException(400, "Missing group name to remove remote folder.")
    remote_path = os.path.join(app.config["SSH_ROOT_DIR"], group_name)
    app.logger.info("Removing target at remote path: %s", remote_path)
    SSHUtil.exec_script(app, "rm", "-rf", remote_path, conf=custom_conf)
  else:
    if not source_path:
      raise VisComException(400, "Missing source path to sync remote file")
    src_path = os.path.dirname(os.path.dirname(source_path))
    dst_path = app.config["SSH_ROOT_DIR"]
    app.logger.info("Remote copy with src path: %s, dst path: %s", src_path, dst_path)
    SSHUtil.secure_copy(app, src_path, dst_path, conf=custom_conf)

def process_uploaded_image(app, group_name, source_name, uploaded_file_list=None, is_remove=False):
  upload_path = get_upload_path(app, group_name)
  if is_remove:
    try:
      shutil.rmtree(upload_path)
    except Exception as e:
      app.logger.error("Failed to rm tree: %s", e)
    db.delete_capture_item(app, group_name)
  else:
    if not os.path.exists(upload_path):
      os.makedirs(upload_path)
    app.logger.info("Saving uploaded image to: %s", upload_path)
    filename_parts = os.path.splitext(source_name)
    update_name = source_name
    ext_name = ""
    if len(filename_parts) > 1:
      update_name = filename_parts[0]
      ext_name = filename_parts[1]
    capture_item_list = []
    for index, uploaded_file in enumerate(uploaded_file_list):
      update_source_name = "{}-{}{}".format(update_name, index + 1, ext_name)
      update_source_path = os.path.join(upload_path, update_source_name)
      uploaded_file.save(update_source_path)
      update_c = CaptureItem(group_name, update_source_name)
      update_c.f_source_path = update_source_path
      capture_item_list.append(update_c)
    return capture_item_list

def add_capture_item(app, capture_item, file_list):
  app.logger.info("Adding capture item: %s to db." % (capture_item,))
  def callback(app):
    try:
      check_capture_item(app, capture_item.group_name, capture_item.source_name)
    except VisComException as e:
      if e.status_code == 404:
        capture_item_list = process_uploaded_image(app, capture_item.group_name, capture_item.source_name, uploaded_file_list=file_list)
        print(capture_item_list)
        for c in capture_item_list:
          db.create_capture_item(app, c)
        sync_remote_file(app, source_path=capture_item_list[0].source_path)
  db.DBT.execute_in_tx(app, callback)
  
def modify_capture_item(app, capture_item, file_list):
  app.logger.info("Modifying capture item: %s to db." % (capture_item,))
  if not (hasattr(capture_item, "group_name") or hasattr(capture_item, "source_name")):
    raise VisComException(400, "Missing group_name attr in object: %s" % (capture_item))
  def callback(app):
    try:
      check_capture_item(app, capture_item.group_name, capture_item.source_name)
      capture_item_list = process_uploaded_image(app, capture_item.group_name, capture_item.source_name, uploaded_file_list=file_list)
      for c in capture_item_list:
        db.update_capture_item(app, c)
      sync_remote_file(app, source_path=capture_item_list[0].source_path)
    except VisComException as e:
      if e.status_code == 404:
        app.logger.error("Capture item: %s has not been created yet.", capture_item)
        raise VisComException(412, "Capture item: %s has not been created yet" % (capture_item,))
  db.DBT.execute_in_tx(app, callback)

def get_capture_item_list(app, group_name=None):
  r = None
  if not group_name:
    app.logger.info("Getting all capture item list.")
    r = db.get_capture_item_list()
  else:
    app.logger.info("Getting capture item list by group name: %s", group_name)
    r = db.get_capture_item_list_by_group(group_name)
  if not r:
    raise VisComException(404, "None of capture item(s) found.")
  app.logger.debug("Fetched %d item(s) from capture group." % (len(r)))
  capture_item_list = []
  for item in r:
    c = CaptureItem(item["group_name"], item["source_name"])
    c.f_source_path = item["source_path"]
    c.f_creation_time = item["creation_time"]
    c.f_update_time = item["update_time"]
    capture_item_list.append(c)
  return capture_item_list

def get_capture_item(app, group_name, source_name):
  app.logger.info("Getting capture item by group name: %s and source name: %s", group_name, source_name)
  r = db.get_capture_item(group_name, source_name)
  if not r:
    raise VisComException(404, "None of capture item by group: %s and name: %s." % (group_name, source_name))
  c = CaptureItem(r["group_name"], r["source_name"])
  c.f_source_path = r["source_path"]
  c.f_creation_time = r["creation_time"]
  c.f_update_time = r["update_time"]
  return c

def check_capture_item(app, group_name, source_name):
  filename_parts = os.path.splitext(source_name)
  if len(filename_parts) > 1:
    source_name = filename_parts[0]
  app.logger.info("Getting capture item by group name: %s and source name prefix: %s", group_name, source_name)
  r = db.checkout_capture_item(group_name, source_name)
  if not r:
    raise VisComException(404, "None of capture item by group: %s and source name: %s." % (group_name, source_name))

def remove_capture_item(app, group_name):
  app.logger.info("Removing capture item by group name %s", group_name)
  def callback(app):
    check_capture_item(app, group_name, "")
    process_uploaded_image(app, group_name, "", is_remove=True)
    sync_remote_file(app, "", group_name=group_name, is_remove=True)
  db.DBT.execute_in_tx(app, callback)