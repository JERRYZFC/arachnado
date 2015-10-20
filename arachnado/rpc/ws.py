import json
import logging

import jsonrpclib
from tornado import websocket
from tornado.web import RequestHandler

from arachnado.utils.misc import json_encode


logger = logging.getLogger(__name__)
jsonrpclib.config.use_jsonclass = False


class JsonRpcWebsocketHandler(websocket.WebSocketHandler):

    def on_message(self, message):
        self._results = []
        try:
            msg = json.loads(message.encode('utf-8'))
            event, data = msg['event'], msg['data']
        except (TypeError, ValueError):
            logger.warn("Invalid message skipped" + message[:500])
            return
        if event == 'rpc:request':
            self.on_event(data)
        else:
            logger.warn("Unsupported event type: " + event)

    def on_event(self, data):
        self._RPC_.run(self, json_encode(data))

    def _result(self, result):
        """A little hacky way to not close WS stream"""
        self._RPC_finished = False
        super(JsonRpcWebsocketHandler, self)._result(result)

    def on_result(self, data):
        return self.write_event('rpc:response', data)

    def open(self):
        """Forward open event to resource objects"""
        for resource_name, resource in self.__dict__.iteritems():
            if hasattr(RequestHandler, resource_name):
                continue
            if hasattr(resource, '_on_open'):
                resource._on_open()

    def on_close(self):
        """Forward on_close event to resource objects"""
        self._RPC_finished = True
        for resource_name, resource in self.__dict__.iteritems():
            if hasattr(RequestHandler, resource_name):
                continue
            if hasattr(resource, '_on_close'):
                resource._on_close()

    def write_event(self, event, data):
        if isinstance(data, basestring):
            data = json.loads(data)
        message = json_encode({'event': event, 'data': data})
        self.write_message(message)