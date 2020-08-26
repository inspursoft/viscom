import sqlite3
from flask import g, current_app
import datetime

import click
from flask.cli import with_appcontext

def get_db():
  if "db" not in g:
    g.db = sqlite3.connect(
      current_app.config["DATABASE"], 
      detect_types=sqlite3.PARSE_DECLTYPES)
    g.db.row_factory = sqlite3.Row
  return g.db

@click.command("init-db")
@with_appcontext
def init_db():
  db = get_db()
  with current_app.open_resource("schema.sql") as f:
    db.executescript(f.read().decode("utf8"))

def create_capture_item(app, capture_item):
  current_time = datetime.datetime.now()
  tx_exec(app, '''
    insert into capture_item (group_name, source_name, source_path, creation_time, update_time) values (?, ?, ?, ?, ?)
  ''', (capture_item.group_name, capture_item.source_name, capture_item.f_source_path, current_time, current_time))

def update_capture_item(app, capture_item):
  current_time = datetime.datetime.now()
  tx_exec(app, '''
    update capture_item set source_name = ?, source_path = ?, update_time = ? where group_name = ?
  ''', (capture_item.source_name, capture_item.f_source_path, current_time, capture_item.group_name))

def delete_capture_group(app, roup_name):
  tx_exec(app, '''
    delete from capture_item where group_name = ?
  ''', (group_name,))

def delete_capture_item(app, group_name):
  tx_exec(app, '''
    delete from capture_item where group_name = ?
  ''', (group_name,))

def get_capture_item_list():
    return get_db().execute('''
      select group_name, min(source_name) source_name, min(source_path) source_path, 
          min(creation_time) creation_time, min(update_time) update_time
        from capture_item group by group_name''').fetchall()

def get_capture_item_list_by_group(group_name):
    return get_db().execute('''
      select group_name, source_name, source_path, creation_time, update_time 
        from capture_item where group_name = ? 
    ''', (group_name,)).fetchall()

def checkout_capture_item(group_name, source_name):
  return get_db().execute('''
      select group_name, source_name, source_path, creation_time, update_time
        from capture_item where group_name = ? and source_name like ?
    ''', (group_name, "{}%".format(source_name,))).fetchall()

def get_capture_item(group_name, source_name):
  return get_db().execute('''
      select group_name, source_name, source_path, creation_time, update_time 
        from capture_item where group_name = ? and source_name = ?
    ''', (group_name, source_name)).fetchone()

def tx_exec(app, sql, *params):
  conn = get_db()
  if "CONN" in app.config:
    conn = app.config["CONN"]
    app.logger.debug("Execute SQL in transaction...")
    conn.execute(sql, *params)
    return
  try:
    conn.execute(sql, *params)
    conn.commit()
  except sqlite3.Error as e:
    conn.rollback()
    app.logger.error("Failed to execute tx sql then rollback: %s", e)
  
class DBT:
  conn = None
  @classmethod
  def __get_conn(cls, app):
    cls.conn = get_db()
    app.config["CONN"] = cls.conn

  @classmethod  
  def __commit(cls):
    cls.conn.commit()

  @classmethod
  def __rollback(cls):
    cls.conn.rollback()

  @classmethod
  def __reset(cls, app):
    cls.conn = None
    app.config["CONN"] = None

  @classmethod
  def execute_in_tx(cls, app, callback):
    try:
      cls.__get_conn(app)
      callback(app)
      cls.__commit()
    except sqlite3.Error as e:
      app.logger.error("Failed to execute SQL in transaction: %s, will rollback.", e)
      cls.__rollback()
    finally:
      cls.__reset(app)
  