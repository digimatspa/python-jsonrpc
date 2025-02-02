#!/usr/bin/env python
# coding: utf-8
from __future__ import unicode_literals
import six

if six.PY3:
    unicode = str

jsonrpcerrors = {}


def get_traceback_string():
    """
    Returns the traceback unicode string for the last error
    """

    from sys import exc_info as _exc_info
    exc = _exc_info()
    if exc == (None, None, None):
        return ""
    import traceback
    tb = "".join(traceback.format_exception(*exc))

    # Fertig
    return unicode(tb).encode(errors="replace")


class JsonRpcError(RuntimeError):
    code = None
    message = None
    data = None

    def __init__(self, message = None, data = None, code = None):
        RuntimeError.__init__(self)
        self.message = message or self.message
        self.data = data
        self.code = code or self.code
        assert self.code, "Error without code is not allowed."

    def __str__(self):
        return "JsonRpcError({code}): {message}".format(
            code = self.code,
            message = str(self.message)
        )

    def __unicode__(self):
        return "JsonRpcError({code}): {message}".format(
                code = self.code,
                message = self.message
            )

jsonrpcerrors[JsonRpcError.code] = JsonRpcError


class ParseError(JsonRpcError):
    code = -32700

    message = "Invalid JSON was received by the server."

    def __init__(self, message = None, data = None):
        JsonRpcError.__init__(self, message = message, data = data)

jsonrpcerrors[ParseError.code] = ParseError


class InvalidRequest(JsonRpcError):
    code = -32600
    message = "The JSON sent is not a valid Request object."
    

    def __init__(self, message = None, data = None):
        JsonRpcError.__init__(self, message = message, data = data)

jsonrpcerrors[InvalidRequest.code] = InvalidRequest


class MethodNotFound(JsonRpcError):
    code = -32601

    message = "The method does not exist / is not available."

    def __init__(self, message = None, data = None):
        JsonRpcError.__init__(self, message = message, data = data)

jsonrpcerrors[MethodNotFound.code] = MethodNotFound


class InvalidParams(JsonRpcError):
    code = -32602

    message = "Invalid method parameter(s)."

    def __init__(self, message = None, data = None):
        JsonRpcError.__init__(self, message = message, data = data)

jsonrpcerrors[InvalidParams.code] = InvalidParams


class InternalError(JsonRpcError):
    code = -32603

    message = "Internal JSON-RPC error."

    def __init__(self, message = None, data = None):
        JsonRpcError.__init__(self, message = message, data = data)

jsonrpcerrors[InternalError.code] = InternalError


