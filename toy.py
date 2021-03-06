'''
GitHub OAuth Handlers for Tornado (using coroutines)
'''

import json
import os

import tornado

import tornado.options
from tornado.log import app_log
from tornado.web import RequestHandler
from tornado.auth import OAuth2Mixin
from tornado import gen, web

from tornado.httputil import url_concat
from tornado.httpclient import HTTPRequest, AsyncHTTPClient

class RootHandler(RequestHandler):
    @web.authenticated
    def get(self):
        self.write("Welcome")

class GitHubMixin(OAuth2Mixin):
    _OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"

class GitHubLoginHandler(RequestHandler, GitHubMixin):
    @gen.coroutine
    def get(self):
        yield self.authorize_redirect(
            redirect_uri='http://127.0.0.1:8777/oauth',
            client_id=self.settings['github_client_id'],
            scope=[], # 
            response_type='code')

class GitHubOAuthHandler(RequestHandler):
    @gen.coroutine
    def get(self):
        
        # TODO: Check if state argument needs to be checked
                
        if self.get_argument("code", False):
            
            code = self.get_argument("code")
            #self.write("<pre>OAuth Code: {}</pre>".format(code))
            
            # TODO: Configure the curl_httpclient for tornado
            http_client = AsyncHTTPClient()
            
            # Exchange the OAuth code for a GitHub Access Token
            #
            # See: https://developer.github.com/v3/oauth/
            
            # GitHub specifies a POST request yet requires URL parameters
            params = dict(
                    client_id=self.settings['github_client_id'],
                    client_secret=self.settings['github_client_secret'],
                    code=code
            )
            
            url = url_concat("https://github.com/login/oauth/access_token",
                             params)
            
            req = HTTPRequest(url,
                              method="POST",
                              headers={"Accept": "application/json"},
                              body='' # Body is required for a POST...
                              )
            
            resp = yield http_client.fetch(req)
            resp_json = json.loads(resp.body)
            
            access_token = resp_json['access_token']
            #self.write("<pre>Access Token: {}</pre>".format(access_token))
            # The cookie and the access_token should be paired in the database
            
            
            # Determine who the logged in user is
            headers={"Accept": "application/json",
                     "User-Agent": "JupyterHub",
                     "Authorization": "token {}".format(access_token)
            }
            req = HTTPRequest("https://api.github.com/user",
                              method="GET",
                              headers=headers
                              )
            resp = yield http_client.fetch(req)
            resp_json = json.loads(resp.body)
            
            user = resp_json["login"]
            self.write("<pre>Welcome, {}</pre>".format(user))
            
            # Redirection should happen after this.
            # If the user reloads this page with an old code, we currently error
            
        else:
            # TODO: Raise a 4xx of some kind
            pass

def main():
    tornado.options.parse_command_line()
    handlers = [
        (r"/", RootHandler),
        (r"/login", GitHubLoginHandler),
        (r"/oauth", GitHubOAuthHandler)
    ]

    settings = dict(
        cookie_secret="supersecret",
        login_url="/login",
        xsrf_cookies=True,
        github_client_id=os.environ["GITHUB_CLIENT_ID"],
        github_client_secret=os.environ["GITHUB_CLIENT_SECRET"],
        github_scope="",
        debug=True,
        autoescape=None
    )
    
    port = 8777
    
    app_log.info("Listening on {}".format(port))

    application = tornado.web.Application(handlers, **settings)
    application.listen(port)
    tornado.ioloop.IOLoop().instance().start()

if __name__ == "__main__":
    main()