from flask import Blueprint, current_app, jsonify, request, abort, send_from_directory, send_file, Response, render_template
import viscom.manager as m
from viscom.model import VisComException, CaptureItem, Encoder, VideoCamera
import json, os
import traceback

import requests

hnd = Blueprint("hnd", __name__, url_prefix="/api")

@hnd.route("/captures", methods=["GET", "POST", "PUT", "DELETE"])
def process_capture():
  if request.method == "GET":
    try:
      group_name = request.args.get("group_name", None)
      if not group_name:
        capture_item_list = m.get_capture_item_list(current_app)
        return jsonify(Encoder.to_json(capture_item_list))
      source_name = request.args.get("source_name", None)
      if not source_name:
        capture_item_list_by_group = m.get_capture_item_list(current_app, group_name)
        return jsonify(Encoder.to_json(capture_item_list_by_group))
      capture_item = m.get_capture_item(current_app, group_name, source_name)
      return send_from_directory(m.get_upload_path(current_app, group_name), capture_item.source_name)
    except VisComException as e:
      msg = "Failed to get capture item(s) with error: %s" % (e,)
      current_app.logger.error(msg)
      return abort(e.status_code, msg)
  elif request.method in ["POST", "PUT"]:
    group_name = request.form["group_name"]
    if not group_name:
      return abort(400, "Group name is required.")
    source_name = request.form["source_name"]
    if not source_name:
      return abort(400, "Source name is required.")
    if "capture_images" not in request.files:
      return abort(400, "Upload captured_images form field is required.")
    try:
      file_list = request.files.getlist("capture_images")
      c = CaptureItem(group_name, source_name)
      action = ""
      if request.method == "POST":
        m.add_capture_item(current_app, c, file_list)
        action = "added"
      elif request.method == "PUT":
        m.modify_capture_item(current_app, c, file_list)
        action = "modified"
      return jsonify(message="Successfully %s capture item." % (action,))
    except VisComException as e:
      traceback.print_exc()
      msg = "Failed to process uploading captured image with error: %s" % (e,)
      current_app.logger.error(msg)
      return abort(e.status_code, msg)
  elif request.method == "DELETE":
    group_name = request.args.get("group_name", None)
    if not group_name:
      return abort(400, "Group name is required.")
    try:
      m.remove_capture_item(current_app, group_name)
      return jsonify(message="Successfully removed capture item for group name: %s" % (group_name,))
    except VisComException as e:
      msg = "Failed to remove capture item: %s" % (e.message)
      current_app.logger.error(msg)
      return abort(e.status_code, msg)

def gen(camera):
  while True:
    frame = camera.get_frame()
    yield(b'--frame\r\n'
      b'Content-Type: image/jpeg\r\n\r\n'+frame+b'\r\n\n')

@hnd.route("/showtime")
def showtime():
  return render_template('showtime.html')

@hnd.route("/video", methods=["GET"])
def video():
  return Response(gen(VideoCamera()), mimetype='multipart/x-mixed-replace; boundary=frame')

@hnd.route("/detect", methods=["GET"])
def face_detect():
  c = VideoCamera()
  with open("c.jpg", "wb") as f:
    f.write(c.get_frame())
    send_file(f, mimetype="Content-Type: image/jpge", as_attachment=True, attachment_filename="c.jpg")
  if m.face_detect(current_app, "c.jpg"):
    return jsonify(message="Face detected.")
  return abort(404, "No face detected.")