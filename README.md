# Introduction

> Based on the [okta-scim-beta](https://github.com/oktadeveloper/okta-scim-beta) project, this example shows how to use Okta's cloud-based SCIM connector to automatically provision and deprovision users managed by Okta into Mattermost.

This example code was written for Python 2.7 and wraps Mattermost REST APIs as a SCIM2.0 endpoint.




# For windows install

As part of the installation steps for Mattermost, you'll have to deploy a MySQL DB.
You may want to deploy WAMP http://www.wampserver.com/en/ so you could leverage PHPMyAdmin to sneak into your Mattermost DB easily.

To install Mattermost on Windows, see tutorial: https://docs.mattermost.com/install/prod-windows-2012.html#install-windows-server-2012

Once you have your Mattermost instance running, sign-in as an admin and create a personal access token https://docs.mattermost.com/developer/personal-access-tokens.html

Then download that git repo locally, edit the config.json file :

```js
{
  "config": {
    "mattermost": {
      "api_endpoint": "http://localhost:8065/api/v4", // localhost:8065 is where your Mattermost instance is running
      "personal_access_token": "xxxxxxxx" // the personal access token you generated as an admin
    },
    "scim_endpoint":{
      "local_token": "yyyyyyy" // the token you manually created, stored in that config.json file and on Okta side so Okta is authorized to reach your SCIM endpoint.
    }
  }
}
```
Then run your python server (see https://github.com/oktadeveloper/okta-scim-beta)

On the Okta side, connect to your oktapreview.com account, create a new app from Okta OAN, select SCIM2.0.
In the Provisioning tab > API Integration:
* base url = https://your-scim-server-url/scim/v2
* API token = your local token ("yyyyyy" above)

Note:
Your SCIM server has to be reachable over https. If your Mattermost instance + SCIM server is running on AWS, you can take advantage of AWS ELB to do a https to http routing.


Enjoy!


