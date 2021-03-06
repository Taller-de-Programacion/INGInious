# -*- coding: utf-8 -*-
#
# This file is part of INGInious. See the LICENSE and the COPYRIGHTS files for
# more information about the licensing of this file.

""" Github auth plugin """

import json
import os
import re

import web
from requests_oauthlib import OAuth2Session

from inginious.frontend.user_manager import AuthMethod

authorization_base_url = 'https://github.com/login/oauth/authorize'
token_url = 'https://github.com/login/oauth/access_token'
scope = ["user:email"]

class GithubAuthMethod(AuthMethod):
    """
    Github auth method
    """
    def get_auth_link(self, auth_storage, share=False):
        github = OAuth2Session(self._client_id, scope=scope,  redirect_uri=web.ctx.home + self._callback_page)
        authorization_url, state = github.authorization_url(authorization_base_url)
        auth_storage["oauth_state"] = state
        return authorization_url

    def callback(self, auth_storage):
        github = OAuth2Session(self._client_id, state=auth_storage["oauth_state"],  redirect_uri=web.ctx.home + self._callback_page)
        try:
            github.fetch_token(token_url, client_secret=self._client_secret,
                               authorization_response=web.ctx.home + web.ctx.fullpath)
            r = github.get('https://api.github.com/user')
            profile = json.loads(r.content.decode('utf-8'))
            r = github.get('https://api.github.com/user/emails')
            profile["email"] = json.loads(r.content.decode('utf-8'))[0]["email"]
            realname = profile["name"] if profile.get("name", None) else profile["login"]
            self._create_user_if_doesnt_exist(profile, realname)
            return str(profile["id"]), realname, profile["email"], {}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None

    def _create_user_if_doesnt_exist(self, profile, realname):
        login = profile['login']
        email = profile['email']
        if re.match(r"^[-_|~0-9A-Z]{4,}$", login, re.IGNORECASE) is None:
            raise Exception("Invalid username")

        if self.database.users.find_one({"username": login}):
            return

        self.user_manager.disconnect_user()
        self.user_manager.connect_user(
                login,
                realname,
                email,
                'en'
                )

    def share(self, auth_storage, course, task, submission, language):
        return False

    def allow_share(self):
        return False

    def __init__(self, id, name, client_id, client_secret):
        self._name = name
        self._id = id
        self._client_id = client_id
        self._client_secret = client_secret
        self._callback_page = '/auth/callback/' + self._id

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def get_imlink(self):
        return '<i class="fa fa-github" style="font-size:50px; color:#24292e;"></i>'


def init(plugin_manager, course_factory, client, conf):

    if conf.get("debug", False):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    client_id = conf.get("client_id", "")
    client_secret = conf.get("client_secret", "")

    auth_meth = GithubAuthMethod(
                conf.get("id"),
                conf.get('name', 'Github'),
                client_id,
                client_secret
                )
    auth_meth.database = plugin_manager.get_database()
    auth_meth.user_manager = plugin_manager.get_user_manager()
    plugin_manager.register_auth_method(auth_meth)
