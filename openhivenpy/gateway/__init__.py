"""

Module for the OpenHiven.py Gateway and Connection to Hiven

---

Under MIT License

Copyright © 2020 - 2021 Luna Klatzer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import logging
import os
import sys
from typing import Optional

from yarl import URL

from .http import *
from .messagebroker import *
from .websocket import *
from .. import utils, HivenObject
from ..exceptions import (RestartSessionError, WebSocketClosedError,
                          WebSocketFailedError, SessionCreateError,
                          KeepAliveError)

logger = logging.getLogger(__name__)


class Connection(HivenObject):
    """
    Connection Class used for interaction with the Hiven API and WebSocket
    Swarm
    """

    def __init__(
            self,
            client,
            *,
            host: Optional[str] = None,
            api_version: Optional[str] = None,
            heartbeat: Optional[int] = None,
            close_timeout: Optional[int] = None
    ):
        self.client = client
        self.http = None
        self._host = host if host is not None else os.getenv("HIVEN_HOST")
        self._api_version = api_version if api_version is not None else \
            os.getenv("HIVEN_API_VERSION")
        self._heartbeat = heartbeat if heartbeat is not None else \
            int(os.getenv("WS_HEARTBEAT"))
        self._close_timeout = close_timeout if close_timeout is not None else \
            int(os.getenv("WS_CLOSE_TIMEOUT"))
        self._endpoint = URL(os.getenv("WS_ENDPOINT"))

        self._connection_status = "CLOSED"
        self._ready = False
        self._closing = False
        self._closed = False
        self._force_closing = False
        self._ws = None

    def _set_default_properties(self):
        """ Sets the default properties for the Connection class """
        self._connection_status = "CLOSED"
        self._ready = False
        self._closing = False
        self._closed = False
        self._force_closing = False
        self._ws = None

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:
        info = [
            ('ready', self.ready),
            ('host', self.host),
            ('endpoint', self.endpoint.human_repr()),
            ('startup_time', self.ws.startup_time),
            ('connection_start', self.ws.connection_start),
            ('heartbeat', self.heartbeat)
        ]
        return '<Connection {}>'.format(' '.join('%s=%s' % t for t in info))

    @property
    def ready(self) -> bool:
        return all((
            getattr(self.http, 'ready', False),
            getattr(self.ws, 'ready', False)
        ))

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        return getattr(self.client, 'loop', None)

    @property
    def host(self) -> Optional[str]:
        return getattr(self, '_host', None)

    @property
    def api_version(self) -> Optional[str]:
        return getattr(self, '_api_version', None)

    @property
    def connection_status(self) -> Optional[str]:
        return getattr(self, '_connection_status', None)

    @property
    def endpoint(self) -> Optional[URL]:
        return getattr(self, '_endpoint', None)

    @property
    def startup_time(self) -> Optional[int]:
        return getattr(self.ws, '_startup_time', None)

    @property
    def ws(self) -> Optional[HivenWebSocket]:
        return getattr(self, '_ws', None)

    @property
    def keep_alive(self) -> Optional[KeepAlive]:
        return getattr(self.ws, 'keep_alive', None)

    @property
    def message_broker(self) -> Optional[MessageBroker]:
        return getattr(self.ws, 'message_broker', None)

    @property
    def heartbeat(self) -> Optional[int]:
        return getattr(self, '_heartbeat', None)

    @property
    def close_timeout(self) -> Optional[int]:
        return getattr(self, '_close_timeout', None)

    @property
    def closed(self) -> Optional[bool]:
        return getattr(self, '_closed', None)

    @property
    def socket_closed(self) -> Optional[bool]:
        return getattr(getattr(self.ws, 'socket', None), 'closed', True)

    async def connect(self, restart: bool) -> None:
        """
        Establishes a connection to Hiven and runs the background processes.
        Only closes if forced to using close() or an exception is raised and restart is False
        """
        try:
            self._connection_status = "OPENING"
            self.http = HTTP(self.client, host=self.host, api_version=self.api_version)
            await self.http.connect()

            while self.connection_status == "OPENING":
                try:
                    coro = HivenWebSocket.create_from_client(
                        self.client, endpoint=self.endpoint, close_timeout=self.close_timeout, heartbeat=self.heartbeat,
                        loop=self.loop
                    )
                    self._ws = await asyncio.wait_for(coro, 30)
                    await self.ws.send_auth()

                    self._closed = False
                    await asyncio.gather(
                        self.ws.listening_loop(), self.keep_alive.run(), self.ws.message_broker.run()
                    )

                except KeyboardInterrupt:
                    raise

                except asyncio.TimeoutError:
                    # If the timeout is hit the connection might not be
                    # possible or unstable, so a warning needs to be thrown
                    utils.log_traceback(
                        brief="[CONNECTION] Ignoring Timeout Traceback:",
                        exc_info=sys.exc_info()
                    )
                    logger.warning(
                        "[CONNECTION] The websocket exceeded the timeout limit!"
                        " Connection will be restarted!"
                    )

                except RestartSessionError:
                    # Encountered an exception inside the receive process of
                    # the WebSocket and the system should restart to make sure
                    # the user can continue to use the Client
                    logger.debug("[CONNECTION] Restarting the Websocket")

                except WebSocketClosedError:
                    continue

                except (Exception, WebSocketFailedError, KeepAliveError) as e:
                    if self.connection_status == "OPENING":
                        utils.log_traceback(
                            brief="[CONNECTION] Encountered an exception while"
                                  " initialising the websocket",
                            exc_info=sys.exc_info()
                        )
                    else:
                        utils.log_traceback(
                            brief="[CONNECTION] Encountered an exception while "
                                  "running the core modules ",
                            exc_info=sys.exc_info()
                        )

                    if restart is False:
                        self._reset_status("CLOSING")
                        raise RuntimeError(
                            "Websocket encountered an exception while running"
                        ) from e

                # Resetting the status
                self._reset_status("OPENING")

        except KeyboardInterrupt:
            ...
        except (RuntimeError, SessionCreateError, Exception) as e:
            utils.log_traceback(
                level='critical',
                brief=f"Failed to keep alive current connection to Hiven:",
                exc_info=sys.exc_info()
            )
            raise SessionCreateError(f"Failed to establish HivenClient session") from e
        finally:
            self._closing = True
            self._reset_status("CLOSING")

            if getattr(self, 'http', None):
                await self.http.close()

            if getattr(self, 'keep_alive', None):
                await self.keep_alive.stop()

                while getattr(self.keep_alive, 'active', None):
                    await asyncio.sleep(.05)

            if getattr(self.message_broker, 'message_broker', None):
                # Forcing the loop to stop making all tasks be cancelled
                await self.ws.message_broker.close_loop()

            self._connection_status = "CLOSED"
            self._closed = True

            await self._wait_until_ws_finished()
            del self._ws

            self._set_default_properties()
            self._closing = False

    def _reset_status(self, connection_status: str):
        """
        Resets the status to being currently opening and not being active

        Used when the websocket raises an exception and crashes or is restarting
        (aka. not available in the moment)
        """
        if getattr(self, 'ws', None):
            self.ws._open = False
            self.ws._ready = False
            self.ws._startup_time = None
        self._connection_status = connection_status

    async def _wait_until_ws_finished(self) -> None:
        """
        Waits until the websocket has finished to return and stop the process
         """
        while (getattr(getattr(self.ws, 'message_broker', None), 'running',
                       False)
               or not self.socket_closed):
            await asyncio.sleep(.05)

    async def close(self, force: bool = False) -> None:
        """
        Closes the Connection to Hiven and stops the running WebSocket and the
        Event Processing Loop

        Returns before the closing has finished to avoid the case where the
        close() method was called in an event_listener and therefore not
        returning would block the process to close in time

        :param force: If set to True the running event-listener workers will be
         forced closed, which may lead to running code of event-listeners being
         stopped while performing actions. If False the stopping will wait for
         all running event_listeners to finish
        """
        try:
            self._connection_status = "CLOSING"
            self._closing = True
            self._force_closing = force

            logger.info(
                f"[CONNECTION] Received force {'close ' if force else ''}"
                f"call to stop the running Client"
            )

            if getattr(self.ws, 'socket', None):
                await self.ws.socket.close()

            while not self.socket_closed:
                await asyncio.sleep(.05)

        except Exception as e:
            utils.log_traceback(
                level='critical',
                brief=f"Failed to close current connection to Hiven",
                exc_info=sys.exc_info()
            )
            raise RuntimeError(
                "Failed to stop client due to an exception occurring"
            ) from e
