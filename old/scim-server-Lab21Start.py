# lab21start.py


#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright  2016, Okta, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import re
import uuid

from flask import Flask
from flask import render_template
from flask import request
from flask import url_for
from flask_socketio import SocketIO
from flask_socketio import emit
from flask_sqlalchemy import SQLAlchemy
import flask

app = Flask(__name__)
database_url = os.getenv('DATABASE_URL', 'sqlite:///test-users.db')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
db = SQLAlchemy(app)
socketio = SocketIO(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True)
    active = db.Column(db.Boolean, default=False)
    userName = db.Column(db.String(250),
                         unique=True,
                         nullable=False,
                         index=True)
    familyName = db.Column(db.String(250))
    givenName = db.Column(db.String(250))

    def __init__(self, resource):
        self.update(resource)

    def update(self, resource):
        for attribute in ['userName', 'active']:
            if attribute in resource:
                setattr(self, attribute, resource[attribute])
        for attribute in ['givenName', 'familyName']:
            if attribute in resource['name']:
                setattr(self, attribute, resource['name'][attribute])

    def to_scim_resource(self):
        rv= {
            "schemas":["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": self.id,
            "userName": self.userName,
            "name": {
                "familyName": self.familyName,
                "givenName": self.givenName
            },
            "active": self.active,
            "meta": {
                "resourceType": "User",
                "location": url_for( 'user_get',
                                    user_id=self.id,
                                    _external=True)
            }
        }
        return rv

class ListResponse():
    def __init__( self, list, start_index=1, count=None, total_results=0):
        self.list = list
        self.start_index = start_index
        self.count = count
        self.total_results = total_results

    def to_scim_resource(self):
        rv = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": self.total_results,
            "startIndex": self.start_index,
            "Ressources": []
        }
        rv['itemsPerPage'] = 0
        return rv

# TODO Add Users HTTP Endpoint here
@app.route("/scim/v2/Users", methods=['GET'])
def users_get():
    rv = ListResponse([])
    return flask.jsonify(rv.to_scim_resource())

# TODO Add Groups HTTP Endpoint here
@app.route("/scim/v2/Groups", methods=['GET'])
def groups_get():
    rv = ListResponse([])
    return flask.jsonify(rv.to_scim_resource())

# TODO Add Users HTTP endpoint here

def scim_error(message, status_code=500):
    rv = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "detail": message,
        "status": str(status_code)
    }
    return flask.jsonify(rv), status_code

def send_to_browser(obj):
    socketio.emit('user',
                  {'data': obj},
                  broadcast=True,
                  namespace='/test')

def render_json(obj):
    rv = obj.to_scim_resource()
    send_to_browser(rv)
    return flask.jsonify(rv)


@socketio.on('connect', namespace='/test')
def test_connect():
    for user in User.query.filter_by(active=True).all():
        emit('user', {'data': user.to_scim_resource()})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')


@app.route('/')
def hello():
    return render_template('base.html')

if __name__ == "__main__":
    try:
        User.query.one()
    except:
        db.create_all()
    app.debug = True
    #socketio.run(app)
