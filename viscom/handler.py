from flask import Blueprint, current_app, jsonify, request, abort, send_from_directory
import viscom.manager as m
from viscom.model import VisComException, CaptureItem, Encoder
import json, os
import traceback

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
    if "capture_image" not in request.files:
      return abort(400, "Upload captured image is required.")
    try:
      file = request.files["capture_image"]
      c = CaptureItem(group_name, source_name)
      action = ""
      if request.method == "POST":
        m.add_capture_item(current_app, c, file)
        action = "added"
      elif request.method == "PUT":
        m.modify_capture_item(current_app, c, file)
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
    source_name = request.args.get("source_name", None)
    if not source_name:
      return abort(400, "Source name is required.")
    try:
      m.remove_capture_item(current_app, group_name, source_name)
      return jsonify(message="Successfully removed capture item for group name: %s and source name: %s" %
        (group_name, source_name))
    except VisComException as e:
      msg = "Failed to remove capture item: %s" % (e.message)
      current_app.logger.error(msg)
      return abort(e.status_code, msg)