import viscom.db as db
from viscom.model import VisComException, CaptureItem
import datetime, os

def get_upload_path(app, group_name):
  return os.path.join(app.instance_path, "upload", group_name)

def process_uploaded_image(app, capture_item, uploaded_file=None, is_remove=False):
  upload_path = get_upload_path(app, capture_item.group_name)
  if is_remove:
    os.remove(capture_item.source_path)
    db.delete_capture_item(app, capture_item)
    try:  
      os.removedirs(upload_path)
    except OSError as e:
      app.logger.error("Failed to remove capture item source with error: %s" % (e,))
  else:
    if not os.path.exists(upload_path):
      os.makedirs(upload_path)
    app.logger.info("Saving uploaded image to: %s", upload_path)
    capture_item.f_source_path = os.path.join(upload_path, capture_item.source_name)
    uploaded_file.save(capture_item.f_source_path)

def add_capture_item(app, capture_item, file):
  app.logger.info("Adding capture item: %s to db." % (capture_item,))
  def callback(app):   
    try:
      get_capture_item(app, capture_item.group_name, capture_item.source_name)
    except VisComException as e:
      if e.status_code == 404:
        process_uploaded_image(app, capture_item, uploaded_file=file)
        db.create_capture_item(app, capture_item)
  db.DBT.execute_in_tx(app, callback)

def modify_capture_item(app, capture_item, file):
  app.logger.info("Modifying capture item: %s to db." % (capture_item,))
  if not (hasattr(capture_item, "group_name") or hasattr(capture_item, "source_name")):
    raise VisComException(400, "Missing group_name attr in object: %s" % (capture_item))
  def callback(app):
    try:
      get_capture_item(app, capture_item.group_name, capture_item.source_name)
      process_uploaded_image(app, capture_item, uploaded_file=file)
      db.update_capture_item(app, capture_item)
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

def remove_capture_item(app, group_name, source_name):
  app.logger.info("Removing capture item by group name %s and source name: %s", group_name, source_name)
  def callback(app):
    capture_item = get_capture_item(app, group_name, source_name)
    process_uploaded_image(app, capture_item, is_remove=True)
  db.DBT.execute_in_tx(app, callback)