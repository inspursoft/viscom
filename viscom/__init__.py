from flask import Flask, current_app
import os
import viscom.db as db

def create_app():
  app = Flask(__name__, instance_relative_config=True)
  app.logger.debug("App instance path is: %s" % app.instance_path)
  app.config.from_mapping(DATABASE=os.path.join(app.instance_path, "viscom.db"))
  app.config.from_json(os.path.join(app.instance_path, "config.json"))
  try:
    os.makedirs(app.instance_path)
  except OSError:
    pass
  
  init_app(app)

  from viscom.handler import hnd
  app.register_blueprint(hnd)
  return app

def init_app(app):
  app.cli.add_command(db.init_db)