#!/usr/bin/env python
# coding: utf-8
from __future__ import print_function, unicode_literals
import os
import sys
import base64
import gzip
import tempfile
import logging
import six
from six import string_types
if six.PY2:
    import urllib2
    import StringIO
    import BaseHTTPServer
    import SocketServer
    import httplib
    import urllib
    import urlparse
    import Cookie
    import rpcrequest
    import rpcresponse
    import rpcerror
    import rpclib
    import rpcjson
    import tools
else:

    import urllib.request, urllib.error, urllib.parse
    import io
    import http.server
    import socketserver
    import http.client
    import urllib.request, urllib.parse, urllib.error
    import urllib.parse
    import http.cookies
    from . import rpcrequest
    from . import rpcresponse
    from . import rpcerror
    from . import rpclib
    from . import rpcjson
    from . import tools
    BaseHTTPServer = http.server
    SocketServer = socketserver
    urllib2 = urllib.request
    unicode = str
    StringIO = io
    Cookey = http.cookies
    urlparse = urllib.parse



# Workaround for Google App Engine
if "APPENGINE_RUNTIME" in os.environ:
    TmpFile = StringIO.StringIO
    google_app_engine = True
else:
    TmpFile = tempfile.SpooledTemporaryFile
    google_app_engine = False


MAX_SIZE_IN_MEMORY = 1024 * 1024 * 10  # 10 MiB
CHUNK_SIZE = 1024 * 1024  # 1 MiB


def http_request(
    url,
    json_string,
    username = None,
    password = None,
    timeout = None,
    additional_headers = None,
    content_type = None,
    cookies = None,
    gzipped = None,
    ssl_context = None,
    debug = None
):
    """
    Fetch data from webserver (POST request)

    :param json_string: JSON-String

    :param username: If *username* is given, BASE authentication will be used.

    :param timeout: Specifies a timeout in seconds for blocking operations
        like the connection attempt (if not specified, the global default
        timeout setting will be used).
        See: https://github.com/gerold-penz/python-jsonrpc/pull/6

    :param additional_headers: Dictionary with additional headers
        See: https://github.com/gerold-penz/python-jsonrpc/issues/5

    :param content_type: Possibility to change the content-type header.

    :param cookies: Possibility to add simple cookie-items as key-value pairs.
        The key and the value of each cookie-item must be a bytestring.
        Unicode is not allowed here.

    :param gzipped: If `True`, the JSON-String will be gzip-compressed.

    :param ssl_context: Specifies custom TLS/SSL settings for connection.
        Python > 2.7.9
        See: https://docs.python.org/2/library/ssl.html#client-side-operation

    :param debug: If `True` --> *logging.debug*
    """

    # Debug
    if debug:
        logging.debug("Client-->Server: {json_string}".format(json_string=repr(json_string)))

    # Create request and add data
    request = urllib2.Request(url)


    if gzipped:
        # Compress content (SpooledTemporaryFile to reduce memory usage)
        spooled_file = tools.SpooledFile()
        tools.gzip_str_to_file(json_string, spooled_file)
        del json_string
        request.add_header("Content-Encoding", "gzip")
        request.add_header("Accept-Encoding", "gzip")
        spooled_file.seek(0)
        if six.PY2:
            request.add_data(spooled_file)
        else:
            request.data = spooled_file
    else:
        if six.PY2:
            request.add_data(json_string)
        else:
            request.data = json_string

    # Content Type
    request.add_header("Content-Type", content_type or "application/json")

    # Authorization
    if username:
        base64string = base64.b64encode("%s:%s" % (username, password)).strip()
        request.add_unredirected_header("Authorization", "Basic %s" % base64string)

    # Cookies
    if cookies:
        cookie = Cookie.SimpleCookie(cookies)
        request.add_header("Cookie", cookie.output(header = "", sep = ";"))

    # Additional headers (overrides other headers)
    if additional_headers:
        for key, val in six.iteritems(additional_headers):
            request.add_header(key, val)

    # Send request to server
    http_error_exception = urllib2.HTTPError if six.PY2 else urllib.error.HTTPError
    try:
        if ssl_context:
            try:
                response = urllib2.urlopen(
                    request, timeout=timeout, context=ssl_context
                )
            except TypeError as err:
                if "context" in unicode(err):
                    raise NotImplementedError("SSL-Context needs Python >= 2.7.9")
                else:
                    raise
        else:
            response = urllib2.urlopen(request, timeout=timeout)

    except http_error_exception as err:
        if debug:
            retval = err.read()
            logging.debug("Client<--Server: {retval}".format(retval=repr(retval)))
        raise

    # Analyze response and return result
    try:
        if "gzip" in response.headers.get("Content-Encoding", ""):
            response_file = tools.SpooledFile(source_file = response)
            if debug:
                retval = tools.gunzip_file(response_file)
                logging.debug("Client<--Server: {retval}".format(retval = repr(retval)))
                return retval
            return tools.gunzip_file(response_file)
        else:
            if debug:
                retval = response.read()
                logging.debug("Client<--Server: {retval}".format(retval=repr(retval)))
                return retval
            return response.read()
    finally:
        response.close()


class HttpClient(object):


    class _Method(object):

        def __init__(self, http_client_instance, method):
            self.http_client_instance = http_client_instance
            self.method = method

        def __call__(self, *args, **kwargs):
            return self.http_client_instance.call(self.method, *args, **kwargs)


    def __init__(
        self,
        url,
        username = None,
        password = None,
        timeout = None,
        additional_headers = None,
        content_type = None,
        cookies = None,
        gzipped = None,
        ssl_context = None,
        debug = None
    ):
        """
        :param: URL to the JSON-RPC handler on the HTTP-Server.
            Example: ``"https://example.com/jsonrpc"``

        :param username: If *username* is given, BASE authentication will be used.

        :param password: Password for BASE authentication.

        :param timeout: Specifies a timeout in seconds for blocking operations
            like the connection attempt (if not specified, the global default
            timeout setting will be used).

        :param additional_headers: Dictionary with additional headers
            See: https://github.com/gerold-penz/python-jsonrpc/issues/5

        :param content_type: Possibility to change the content-type header.

        :param cookies: Possibility to add simple cookie-items as key-value pairs.
            The key and the value of each cookie-item must be a bytestring.
            Unicode is not allowed here.

        :param gzipped: If `True`, the JSON-String will gzip-compressed.

        :param ssl_context:  Specifies custom TLS/SSL settings for connection.
            Python >= 2.7.9
            See: https://docs.python.org/2/library/ssl.html#client-side-operation

        :param debug: If `True` --> *logging.debug*
        """

        self.url = url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.additional_headers = additional_headers
        self.content_type = content_type
        self.cookies = cookies
        self.gzipped = gzipped
        self.ssl_context = ssl_context
        self.debug = debug


    def call(self, method, *args, **kwargs):
        """
        Creates the JSON-RPC request string, calls the HTTP server, converts
        JSON-RPC response string to python and returns the result.

        :param method: Name of the method which will be called on the HTTP server.
            Or a list with RPC-Request-Dictionaries. Syntax::

                "<MethodName>" or [<JsonRpcRequestDict>, ...]

            RPC-Request-Dictionaries will be made with the function
            *rpcrequest.create_request_dict()*.
        """

        # Create JSON-RPC-request
        if isinstance(method, string_types):
            request_json = rpcrequest.create_request_json(method, *args, **kwargs)
        else:
            assert not args and not kwargs
            request_json = rpcjson.dumps(method)

        # Call the HTTP-JSON-RPC server
        response_json = http_request(
            url = self.url,
            json_string = request_json,
            username = self.username,
            password = self.password,
            timeout = self.timeout,
            additional_headers = self.additional_headers,
            content_type = self.content_type,
            cookies = self.cookies,
            gzipped = self.gzipped,
            ssl_context = self.ssl_context,
            debug = self.debug
        )
        if not response_json:
            return

        # Convert JSON-RPC-response to python-object
        response = rpcresponse.parse_response_json(response_json)
        if isinstance(response, rpcresponse.Response):
            if response.error:
                # Raise error
                if response.error.code in rpcerror.jsonrpcerrors:
                    raise rpcerror.jsonrpcerrors[response.error.code](
                        message = response.error.message,
                        data = response.error.data
                    )
                else:
                    raise rpcerror.JsonRpcError(
                        message = response.error.message,
                        data = response.error.data,
                        code = response.error.code
                    )
            else:
                # Return result
                return response.result
        elif isinstance(response, list):
            # Bei Listen wird keine Fehlerauswerung gemacht
            return response


    def notify(self, method, *args, **kwargs):
        """
        Sends a notification or multiple notifications to the server.

        A notification is a special request which does not have a response.
        """

        methods = []

        # Create JSON-RPC-request (without ID)
        if isinstance(method, string_types):
            request_dict = rpcrequest.create_request_dict(method, *args, **kwargs)
            del request_dict["id"]
            methods.append(request_dict)
        else:
            assert not args and not kwargs
            for request_dict in method:
                for delkey in ["id", "ID", "Id"]:
                    if delkey in request_dict:
                        del request_dict[delkey]
                methods.append(request_dict)

        # Redirect to call-method
        self.call(methods)

        # Fertig
        return

    # for compatibility with jsonrpclib
    _notify = notify


    def __call__(self, method, *args, **kwargs):
        """
        Redirects the direct call to *self.call*
        """

        return self.call(method, *args, **kwargs)


    def __getattr__(self, method):
        """
        Allows the usage of attributes as *method* names.
        """

        return self._Method(http_client_instance = self, method = method)

class ThreadingHttpServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
        """
        Threading HTTP Server
        """
        pass


class HttpRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler, rpclib.JsonRpc):
        """
        HttpRequestHandler for JSON-RPC-Requests

        Info: http://www.simple-is-better.org/json-rpc/transport_http.html
        """

        protocol_version = "HTTP/1.1"
        content_type = "application/json"

        def set_content_type(self, content_type):
            """
            Set content-type to *content_type*
            """

            self.send_header("Content-Type", content_type)

        def set_content_type_json(self):
            """
            Set content-type to "application/json"
            """

            self.set_content_type("application/json")

        def set_no_cache(self):
            """
            Disable caching
            """

            self.send_header("Cache-Control", "no-cache")
            self.send_header("Pragma", "no-cache")

        def set_content_length(self, length):
            """
            Set content-length-header
            """

            self.send_header("Content-Length", str(length))

        def set_content_encoding(self, content_encoding):
            """
            Set content-encoding to *content_encoding*
            """

            self.send_header("Content-Encoding", content_encoding)

        def do_GET(self):
            """
            Handles HTTP-GET-Request
            """

            # Parse URL query
            path, query_str = urllib.splitquery(self.path) if six.PY2 else urlparse.splitquery(self.path)
            if not query_str:
                # Bad Request
                return self.send_error(httplib.BAD_REQUEST)

            # Parse querystring
            query = urlparse.parse_qs(query_str)

            # jsonrpc
            jsonrpc = query.get("jsonrpc")
            if jsonrpc:
                jsonrpc = jsonrpc[0]

            # id
            id = query.get("id")
            if id:
                id = id[0]

            # method
            method = query.get("method")
            if method:
                method = method[0]
            else:
                # Bad Request
                return self.send_error(httplib.BAD_REQUEST)

            # params
            args = []
            kwargs = {}
            params = query.get("params")
            if params:
                params = rpcjson.loads(params[0])
                if isinstance(params, list):
                    args = params
                    kwargs = {}
                elif isinstance(params, dict):
                    args = []
                    kwargs = params

            # Create JSON request string
            request_dict = rpcrequest.create_request_dict(method, *args, **kwargs)
            request_dict["jsonrpc"] = jsonrpc
            request_dict["id"] = id
            request_json = rpcjson.dumps(request_dict)

            # Call
            response_json = self.call(request_json) or ""

            # Return result
            self.send_response(code=httplib.OK)
            self.set_content_type(self.content_type)
            self.set_no_cache()
            self.set_content_length(len(response_json))
            self.end_headers()
            self.wfile.write(response_json)

        def do_POST(self):
            """
            Handles HTTP-POST-Request
            """

            # Read, analyze and parse request
            content_length = int(self.headers.get("Content-Length", 0))
            content_encoding = self.headers.get("Content-Encoding", "")
            accept_encoding = self.headers.get("Accept-Encoding", "")

            if "gzip" in content_encoding and not google_app_engine:
                # Decompress
                with tools.SpooledFile() as gzipped_file:
                    # ToDo: read chunks
                    # if content_length <= CHUNK_SIZE:
                    #     gzipped_file.write(self.rfile.read(content_length))
                    # else:
                    #     chunks_quantity = content_length % CHUNK_SIZE
                    # ...
                    gzipped_file.write(self.rfile.read(content_length))
                    gzipped_file.seek(0)
                    with gzip.GzipFile(
                            filename="", mode="rb", fileobj=gzipped_file
                    ) as gz:
                        request_json = gz.read()
            else:
                request_json = self.rfile.read(content_length)

            # Call
            response_json = self.call(request_json) or ""

            # Return result
            self.send_response(code=httplib.OK)
            self.set_content_type(self.content_type)
            self.set_no_cache()

            if "gzip" in accept_encoding:
                # Gzipped
                content = tools.SpooledFile()
                with gzip.GzipFile(filename="", mode="wb", fileobj=content) as gz:
                    gz.write(response_json)
                content.seek(0)

                # Send compressed
                self.set_content_encoding("gzip")
                self.set_content_length(len(content))
                self.end_headers()
                self.wfile.write(content.read())
            else:
                # Send uncompressed
                self.set_content_length(len(response_json))
                self.end_headers()
                self.wfile.write(response_json)

            return




def handle_cgi_request(methods = None):
    """
    Gets the JSON-RPC request from CGI environment and returns the
    result to STDOUT
    """

    import cgi
    import cgitb
    cgitb.enable()

    # get response-body
    request_json = sys.stdin.read()
    if request_json:
        # POST
        request_json = urlparse.unquote(request_json)
    else:
        # GET
        args = []
        kwargs = {}
        fields = cgi.FieldStorage()
        jsonrpc = fields.getfirst("jsonrpc")
        id = fields.getfirst("id")
        method = fields.getfirst("method")
        params = fields.getfirst("params")
        if params:
            params = rpcjson.loads(params)
            if isinstance(params, list):
                args = params
                kwargs = {}
            elif isinstance(params, dict):
                args = []
                kwargs = params

        # Create JSON request string
        request_dict = rpcrequest.create_request_dict(method, *args, **kwargs)
        request_dict["jsonrpc"] = jsonrpc
        request_dict["id"] = id
        request_json = rpcjson.dumps(request_dict)

    # Call
    response_json = rpclib.JsonRpc(methods = methods).call(request_json)

    # Return headers

    print("Content-Type: application/json")
    print("Cache-Control: no-cache")
    print("Pragma: no-cache")
    print()

    # Return result
    print(response_json)



