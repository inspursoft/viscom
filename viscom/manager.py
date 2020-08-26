import viscom.db as db
from viscom.model import VisComException, CaptureItem
import datetime, os
import shutil, cv2, dlib

def get_upload_path(app, group_name):
  return os.path.join(app.instance_path, "upload", group_name)

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
      update_source_name = "{}{}".format(index + 1, ext_name)
      update_source_path = os.path.join(upload_path, update_source_name)
      uploaded_file.save(update_source_path)
      image_gray(app, update_source_path)
      update_c = CaptureItem(group_name, update_source_name)
      update_c.f_source_path = update_source_path
      capture_item_list.append(update_c)
    # check_list_path = os.path.join(app.instance_path, "upload", "check.list")
    # with open(check_list_path, "w") as f:
    #   f.write('\n'.join([c.source_name for c in capture_item_list]))
    #   uploaded_file.save(check_list_path)
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
  db.DBT.execute_in_tx(app, callback)

def face_detect(app, image):
  detector = dlib.get_frontal_face_detector()
  captured = cv2.imread(image)
  img_gray = cv2.cvtColor(captured, cv2.COLOR_BGR2GRAY)
  is_detected = False
  if detector(img_gray, 1):
    is_detected = True
  cv2.destroyAllWindows()
  return is_detected

def image_gray(app, file_path):
  detector = dlib.get_frontal_face_detector()
  detector = dlib.get_frontal_face_detector()
  image = cv2.imread(file_path)
  img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
  #使用探测器识别图像中的人脸，形成一个人脸列表
  face_dets = detector(img_gray, 1)
  if face_dets and len(face_dets) > 0:
    app.logger.debug("Found and process one person face...")
    det = face_dets[0]
    # 提取人脸区域
    face_top = det.top() if det.top() > 0 else 0
    face_bottom = det.bottom() if det.bottom() > 0 else 0
    face_left = det.left() if det.left() > 0 else 0
    face_right = det.right() if det.right() > 0 else 0
    face_img = img_gray[face_top:face_bottom, face_left:face_right]  
    cv2.imwrite(file_path, face_img)
  else:
    app.logger.debug("No found for person face...")
    os.remove(file_path)
  cv2.destroyAllWindows()
