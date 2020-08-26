from flask import Flask, current_app
import os
import viscom.db as db

def create_app():
  app = Flask(__name__, instance_relative_config=True)
  app.config.from_mapping(DATABASE="viscom.db")
  init_app(app)

  from viscom.handler import hnd
  app.register_blueprint(hnd)
  return app

def init_app(app):
  app.cli.add_command(db.init_db)