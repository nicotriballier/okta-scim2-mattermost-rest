import re
import uuid

from flask import Flask
from flask import render_template
from flask import request
from flask import url_for
import flask

# to make call to JSON REST APIs
import json
import requests


app = Flask(__name__)
config = None
with open('config.json') as config_file:
    config_json = json.load(config_file)
    config = config_json['config']

PERSONAL_ACCESS_TOKEN = config['mattermost']['personal_access_token']
API_ENDPOINT = config['mattermost']['api_endpoint']
LOCAL_TOKEN = config['scim_endpoint']['local_token']

# Conforms the mattermost user object to a SCIM format
class MattermostUser:
    def __init__(self, resource):
        self.update(resource)

    def update(self, resource):
        # raw mattermost (output of mattermost APIs) user looks like:
        # {
        #    "id": "cwbiyd33g3dnxmjab63tisssxa",
        #    "create_at": 1509317514857,
        #    "update_at": 1509317514857,
        #    "delete_at": 0,
        #    "username": "john.smith",
        #    "auth_data": "",
        #    "auth_service": "",
        #    "email": "john.smith@oktarocks.com",
        #    "nickname": "john.smith",
        #    "first_name": "John",
        #    "last_name": "Smith",
        #    "position": "",
        #    "roles": "system_user",
        #    "locale": "en"
        # },

        setattr(self, 'userName', resource['username'])
        setattr(self, 'active', True)
        setattr(self, 'id', resource['id'])
        setattr(self, 'email', resource['email'])

        #setattr(self, 'displayName', resource['nickname'])
        setattr(self, 'familyName', resource['last_name'])
        setattr(self, 'givenName', resource['first_name'])

    def to_scim_resource(self):
        rv = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": self.id,
            "userName": self.userName,
            "name": {
                "familyName": self.familyName,
                "givenName": self.givenName
            },
            "emails": [
                {
                    "value": self.email,
                    "type": "work",
                    "primary": True
                }
            ],
            "active": self.active,
            "meta": {
                "resourceType": "User",
                "location": url_for('user_get',
                                    user_id=self.id,
                                    _external=True),
                # "created": "2010-01-23T04:56:22Z",
                # "lastModified": "2011-05-13T04:42:34Z",
            }
        }
        return rv

class ListResponse():
    def __init__(self, list, start_index=1, count=None, total_results=0):
        self.list = list
        self.start_index = start_index
        self.count = count
        self.total_results = total_results

    def to_scim_resource(self):
        rv = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": self.total_results,
            "startIndex": self.start_index,
            "Resources": []
        }
        # TODO Update ListResponse class here.
        resources = []
        for item in self.list:
            user = MattermostUser(item)
            resources.append(user.to_scim_resource())
        if self.count:
            rv['itemsPerPage'] = self.count
        rv['Resources'] = resources
        return rv

# TODO Add is_authorized function here
def is_authorized(request_headers):
    local_token = LOCAL_TOKEN
    request_token = str(request_headers.get('Authorization'))
    if local_token == request_token:
        return True
    else:
        return False

def scim_error(message, status_code=500):
    rv = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "detail": message,
        "status": str(status_code)
    }
    return flask.jsonify(rv), status_code

def render_json(obj):
    user = MattermostUser(obj)
    rv = user.to_scim_resource()
    #send_to_browser(rv)
    return flask.jsonify(rv)

@app.route('/')
def hello():
    return render_template('base.html')

@app.route("/scim/v2/Users/<user_id>", methods=['PATCH'])
def users_patch(user_id):
    # TODO Add authorization check here
    if not (is_authorized(request.headers)):
        return scim_error('Unauthorized', 401)

    patch_resource = request.get_json(force=True)
    for attribute in ['schemas', 'Operations']:
        if attribute not in patch_resource:
            message = "Payload must contain '{}' attribute.".format(attribute)
            return message, 400
    schema_patchop = 'urn:ietf:params:scim:api:messages:2.0:PatchOp'
    if schema_patchop not in patch_resource['schemas']:
        return "The 'schemas' type in this request is not supported.", 501

    deactivate = None
    reactivate = None
    for operation in patch_resource['Operations']:
        if 'op' not in operation and operation['op'] != 'replace':
            continue
        value = operation['value']
        #value looks like {"active":true/false}
        for key in value.keys():
            if key == 'active':
                val = str(value[key])
                if val == ''.join('False'):
                    deactivate = True
                else:
                    reactivate = True

    if deactivate:
        try:
            url = API_ENDPOINT + '/users/' + user_id + '/active';
            payload = {
                'active': False
            }
            headers = {
                'Authorization': 'Bearer ' + PERSONAL_ACCESS_TOKEN,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.put(url, data=json.dumps(payload), headers=headers)
        except:
            return scim_error("User not found", 404)

    if reactivate:
        try:
            url = API_ENDPOINT + '/users/' + user_id + '/active';
            payload = {
                'active': True
            }
            headers = {
                'Authorization': 'Bearer ' + PERSONAL_ACCESS_TOKEN,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.put(url, data=json.dumps(payload), headers=headers)
        except:
            return scim_error("User not found", 404)

    ## user patch has to return the user details
    return user_get(user_id)
    #user = MattermostUser(response.json())
    #rv = user.to_scim_resource()
    #resp = flask.jsonify(rv)
    #resp.headers['Location'] = url_for('user_get', user_id=user.id, _external=True)
    #return response.json(), 200
#
    #return render_json(user)

# Completed HTTP GET with filtered lookup.
@app.route("/scim/v2/Users", methods=['GET'])
def users_get():
    # TODO Add authorization check here
    if not(is_authorized(request.headers)):
        return scim_error('Unauthorized', 401)

    match = None
    search_key_name = None
    search_value = None
    count = int(request.args.get('count', 100))
    start_index = int(request.args.get('startIndex', 1))
    if start_index < 1:
        start_index = 1
    start_index -= 1
    request_filter = request.args.get('filter')

    # Handling the filter users requirement...
    # see more info at: https://github.com/oktadeveloper/okta-scim-beta#filtering-on-id-username-and-emails
    if request_filter:
        match = re.match('(\w+) eq "([^"]*)"', request_filter)
    if match:
        (search_key_name, search_value) = match.groups()

    if search_key_name == 'userName':
        url = API_ENDPOINT + '/users/usernames';
        payload = [
           search_value
        ]
        headers = {
            'Authorization': 'Bearer ' + PERSONAL_ACCESS_TOKEN,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, data=json.dumps(payload), headers=headers)
    elif search_key_name == 'id':
        url = API_ENDPOINT + '/users/ids';
        payload = [
           search_value
        ]
        headers = {
            'Authorization': 'Bearer ' + PERSONAL_ACCESS_TOKEN,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, data=json.dumps(payload), headers=headers)
    else:
        url = API_ENDPOINT + '/users';
        payload = {
        }
        headers = {
            'Authorization': 'Bearer ' + PERSONAL_ACCESS_TOKEN,
            'Accept': 'application/json'
        }
        response = requests.get(url, data=json.dumps(payload), headers=headers)

    found = response.json()
    total_results = len(found)
    rv = ListResponse(found,
                      start_index=start_index,
                      count=count,
                      total_results=total_results)
    return flask.jsonify(rv.to_scim_resource())







# TODO Add HTTP GET endpoint for single User lookup here
@app.route("/scim/v2/Users/<user_id>", methods=['GET'])
def user_get(user_id):
    # TODO Add authorization check here
    if not (is_authorized(request.headers)):
        return scim_error('Unauthorized', 401)

    try:
        url = API_ENDPOINT + '/users/' + user_id;
        payload = {
        }
        headers = {
            'Authorization': 'Bearer ' + PERSONAL_ACCESS_TOKEN,
            'Accept': 'application/json'
        }
        response = requests.get(url, data=json.dumps(payload), headers=headers)
    except:
        return scim_error("User not found", 404)

    if response.status_code == 404:
        return scim_error("User not found", 404)
    return render_json(response.json())

# TODO Add HTTP POST endpoint for Create User here
@app.route("/scim/v2/Users", methods=['POST'])
def users_post():
    # TODO Add authorization check here
    if not (is_authorized(request.headers)):
        return scim_error('Unauthorized', 401)

    user_resource = request.get_json(force=True)

    username = user_resource['userName'].split("@")[0]
    email = user_resource['emails'][0]['value']
    firstname = user_resource['name']['givenName']
    lastname = user_resource['name']['familyName']
    nickname = user_resource['displayName']
    password = str(uuid.uuid4())

    #do not generate id if the target system already does it
    #user.id = str(uuid.uuid4())

    url = API_ENDPOINT + '/users';
    payload = {
        'email': email,
        'username': username,
        'first_name': firstname,
        'last_name': lastname,
        'nickname': nickname,
        'password': password
    }
    headers = {
        'Authorization': 'Bearer ' + PERSONAL_ACCESS_TOKEN,
        'Accept': 'application/json',
        'Content-Type':'application/json'
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    user = MattermostUser(response.json())
    rv = user.to_scim_resource()
    resp = flask.jsonify(rv)
    resp.headers['Location'] = url_for('user_get', user_id=user.id, _external=True)
    return resp, 201

# TODO Add HTTP PUT endpoint for Update Attributes here
@app.route("/scim/v2/Users/<user_id>", methods=['PUT'])
def users_put(user_id):
    # PUT /users/user_id is triggered when a field is updated AND when a user is reassigned to the app
    # this code only handles the user reactivation
    # need to grant edit_other_users permission to edit existing users to overwrite all fields
    try:
        url = API_ENDPOINT + '/users/' + user_id + '/active';
        payload = {
            'active': True
        }
        headers = {
            'Authorization': 'Bearer ' + PERSONAL_ACCESS_TOKEN,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.put(url, data=json.dumps(payload), headers=headers)
    except:
        return scim_error("User not found", 404)

    ## user patch has to return the user details
    return user_get(user_id)


@app.route("/scim/v2/Groups", methods=['GET'])
def groups_get():
    # to be implemented
    rv = ListResponse([])
    return flask.jsonify(rv.to_scim_resource())

if __name__ == "__main__":
    app.run()
