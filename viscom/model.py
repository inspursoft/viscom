import json, cv2, time

class VisComException(Exception):
  def __init__(self, status_code=500, message=""):
    self.status_code = status_code
    self.message = message

class CaptureItem(json.JSONEncoder):
  def __init__(self, group_name, source_name):
    self.group_name = group_name
    self.source_name = source_name
    
  @property
  def f_source_path(self):
    return self.source_path

  @f_source_path.setter
  def f_source_path(self, p):
    self.source_path = p

  @property
  def f_creation_time(self):
    return self.creation_time

  @f_creation_time.setter
  def f_creation_time(self, c):
    self.creation_time = c.strftime("%Y-%m-%d %H:%I:%S")

  @property
  def f_update_time(self):
    return self.update_time

  @f_update_time.setter
  def f_update_time(self, u):
    self.update_time = u.strftime("%Y-%m-%d %H:%I:%S")

  def __str__(self):
    return "group_name: %s, source_name: %s" % (
      self.group_name, self.source_name)

  def default(self, o):
    if isinstance(o, list):
      return o.__dict__
    return json.JSONEncoder.default(self, o)
  
class Encoder:
  @staticmethod
  def to_json(obj):
    return json.loads(json.dumps(obj, default=lambda o: o.__dict__))

class VideoCamera:
  
  video = None

  @classmethod
  def __get_video(cls):
    if not cls.video:
      c = cv2.VideoCapture(0)
      if not c.isOpened():
        c = cv2.VideoCapture(1)
      cls.video = c

  @classmethod
  def get_frame(cls):
    cls.__get_video()
    success, image = cls.video.read()
    if success:
      _, jpeg = cv2.imencode('.jpg', image)
      return jpeg.tobytes()
    raise VisComException(500, "Failed to read video from camera.")

  @classmethod
  def get_stream(cls):
    cls.__get_video()
    success, image = cls.video.read()
    if success:
      return image
    raise VisComException(500, "Failed to get stream from camera.")
