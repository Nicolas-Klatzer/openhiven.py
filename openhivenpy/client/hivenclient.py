import asyncio
import datetime
import logging
import os
import sys
from asyncio import AbstractEventLoop
from typing import Optional

from .cache import ClientCache
from .. import HivenObject
from .. import types
from .. import utils
from ..events import HivenParsers, HivenEventHandler
from ..exceptions import (SessionCreateError, InvalidTokenError,
                          WebSocketFailedError, HivenConnectionError)
from ..gateway import Connection, HTTP, MessageBroker

__all__ = ['HivenClient']

logger = logging.getLogger(__name__)


class HivenClient(HivenEventHandler, HivenObject):
    """ Main Class for connecting to Hiven and interacting with the API. """

    def __init__(
            self,
            *,
            token: str = None,
            loop: AbstractEventLoop = None,
            log_websocket: bool = False,
            queue_events: bool = False,
            host: Optional[str] = None,
            api_version: Optional[str] = None,
            heartbeat: Optional[int] = None,
            close_timeout: Optional[int] = None
    ):
        """
        :param token: Token that can be passed pre-runtime. If not set, the
         token will need to be passed at run-time. If a token is passed using
         local available environment variables and no other token is passed
         that one will be used.
        :param loop: Loop that will be used to run the Client. If a new one is
         passed on run() that one will be used instead
        :param log_websocket: If set to True will additionally log websocket
         messages and their content
        :param host: The host API endpoint of Hiven. Defaults to api.hiven.io
        :param api_version: The API version that should be used. Defaults to v1
        :param queue_events: If set to True the received events over the
         websocket will be queued and event_listeners will called one after
         another. If set to False all events are directly assigned to the
         asyncio event_loop and executed parallel
        :param heartbeat: Intervals in which the bot will send heartbeats to
         the Websocket. Defaults to the pre-set environment variable heartbeat
         (default at 30000)
        :param close_timeout: Seconds after the websocket will timeout after
         the end handshake didn't complete successfully. Defaults to the pre-set
         environment variable close_timeout (default at 40)
        """
        self._token = token
        self._loop = loop
        self._log_websocket = log_websocket
        self._queue_events = queue_events
        self._client_user = None
        self._storage = ClientCache(client=self, log_websocket=log_websocket,
                                    token=self._token)
        self._connection = Connection(
            self, api_version=api_version, host=host, heartbeat=heartbeat,
            close_timeout=close_timeout
        )

        # Inheriting the HivenEventHandler class that will call and trigger
        # the parsers for events
        super().__init__(client=self, parsers=HivenParsers(self))

    def __str__(self) -> str:
        return getattr(self, "name")

    def __repr__(self) -> str:
        info = [
            ('type', self.client_type),
            ('open', getattr(self, 'open', False)),
            ('bot', getattr(self, 'bot', 'na')),
            ('name', getattr(self.client_user, 'name', 'na')),
            ('id', getattr(self.client_user, 'id', 'na'))
        ]
        return '<{} {}>'.format(self.__class__.__name__, ' '.join('%s=%s' % t for t in info))

    @property
    def storage(self) -> Optional[ClientCache]:
        return getattr(self, '_storage', None)

    @property
    def token(self) -> Optional[str]:
        return self.storage.get('token')

    @property
    def client_type(self) -> Optional[str]:
        return self.__class__.__name__

    @property
    def log_websocket(self) -> Optional[str]:
        return self.storage.get('log_websocket', None)

    @property
    def http(self) -> Optional[HTTP]:
        return getattr(self.connection, 'http', None)

    @property
    def connection(self) -> Optional[Connection]:
        return getattr(self, '_connection', None)

    @property
    def queue_events(self) -> Optional[bool]:
        return getattr(self, '_queue_events', None)

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        return getattr(self, '_loop', None)

    def run(
            self,
            token: str = None,
            *,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            restart: bool = False
    ) -> None:
        """
        Standard function for establishing a connection to Hiven

        :param token: Token that should be used to connect to Hiven. If none is
         passed it will try to fetch the token using os.getenv()
        :param loop: Event loop that will be used to execute all async
         functions. Uses 'asyncio.get_event_loop()' to fetch the EventLoop.
         Will create a new one if no one was created yet. If the loop was
         passed during initialisation that one will be used if no loop is
         passed. If a new loop is passed, that one will be used for execution.
        :param restart: If set to True the Client will restart if an error is
         encountered!
        """
        try:
            if token is None:
                token = os.getenv('HIVEN_TOKEN')

            if self._loop is not None:
                self._loop = loop if loop is not None else self._loop
            else:
                try:
                    self._loop = loop if loop is not None else asyncio.get_event_loop()
                except RuntimeError as e:
                    # If the function is called outside of the main thread a
                    # new event_loop must be created, so that the process can
                    # still be run. This will raise an exception though if the
                    # user tries to start the client while another loop already
                    # is running! Therefore run() should only be used when no
                    # event_loop was created yet that could interfere with the
                    # process, else connect() is available
                    if "There is no current event loop in thread" in str(e):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        self._loop = asyncio.get_event_loop()
                    else:
                        raise

            self.loop.run_until_complete(self.connect(token, restart=restart))

        except KeyboardInterrupt:
            pass

        except (InvalidTokenError, WebSocketFailedError):
            raise

        except SessionCreateError:
            raise

        except Exception as e:
            utils.log_traceback(
                level='critical',
                brief=f"Failed to keep alive connection to Hiven:",
                exc_info=sys.exc_info()
            )
            raise HivenConnectionError(
                "Failed to keep alive connection to Hiven") from e

    async def connect(
            self,
            token: str = None,
            *,
            restart: bool = False
    ) -> None:
        """Establishes a connection to Hiven and does not return until finished

        :param token: Token that should be used to connect to Hiven. If none is
         passed it will try to fetch the token in the environment variables
         using os.getenv('HIVEN_TOKEN'). Will overwrite the pre-runtime passed
         token if one was passed
        :param restart: If set to True the Client will restart if an error is
         encountered!
        """
        try:
            if token is None:
                token = os.getenv('HIVEN_TOKEN')

            if self._token is None and token is not None:
                self._token = token

            self.storage['token'] = self._token

            user_token_len: int = utils.safe_convert(
                int, os.getenv("USER_TOKEN_LEN")
            )
            bot_token_len: int = utils.safe_convert(
                int, os.getenv("BOT_TOKEN_LEN")
            )

            if self._token is None or self._token == "":
                logger.critical(f"[HIVENCLIENT] Empty Token was passed!")
                raise InvalidTokenError("Empty Token was passed!")

            elif len(self._token) not in (user_token_len, bot_token_len):
                logger.critical(f"[HIVENCLIENT] Invalid Token was passed")
                raise InvalidTokenError("Invalid Token was passed")

            await self.connection.connect(restart=restart)

        except KeyboardInterrupt:
            pass

        except (InvalidTokenError, WebSocketFailedError):
            raise

        except SessionCreateError:
            raise

        except Exception as e:
            utils.log_traceback(
                level='critical',
                brief=f"Failed to keep alive connection to Hiven:",
                exc_info=sys.exc_info()
            )
            raise HivenConnectionError(
                f"Failed to keep alive connection to Hiven"
            ) from e

    async def close(self, force: bool = False) -> None:
        """
        Closes the Connection to Hiven and stops the running WebSocket and
        the Event Processing Loop

        :param force: If set to True the running event-listener workers will be
         forced closed, which may lead to running code of event-listeners being
         stopped while performing actions. If False the stopping will wait
         for all running event_listeners to finish
        """
        await self.connection.close(force)
        self.storage.closing_cleanup()
        logger.debug(f"[HIVENCLIENT] Client {repr(self)} was closed")

    @property
    def open(self) -> Optional[bool]:
        return getattr(self.connection, 'open', False)

    @property
    def connection_status(self) -> Optional[int]:
        return getattr(self.connection, 'connection_status', None)

    @property
    def startup_time(self) -> Optional[int]:
        return getattr(self.connection, 'startup_time', None)

    @property
    def message_broker(self) -> Optional[MessageBroker]:
        return getattr(self.connection.ws, 'message_broker', None)

    @property
    def initialised(self) -> Optional[bool]:
        return getattr(self.connection.ws, '_open', False)

    async def edit(self, **kwargs) -> bool:
        """
        Edits the Clients data on Hiven

        ---

        Available options: header, icon, bio, location, website, username

        :return: True if the request was successful else False
        """
        try:
            for key in kwargs.keys():
                if key in ['header', 'icon', 'bio', 'location', 'website',
                           'username']:
                    await self.http.patch(
                        endpoint="/users/@me", json={key: kwargs.get(key)}
                    )

                    return True

                else:
                    raise NameError("The passed value does not exist in the Client!")

        except Exception as e:
            keys = "".join(str(key + " ") for key in kwargs.keys())

            utils.log_traceback(
                brief=f"Failed change the values {keys}:",
                exc_info=sys.exc_info()
            )
            raise

    @property
    def client_user(self) -> Optional[types.User]:
        # Always prefers to fetch the most recent data
        if self.storage['client_user']:
            self._client_user = self.storage.init_client_user_obj()
            return self._client_user
        elif getattr(self, '_client_user', None) is not None:
            return self._client_user
        else:
            return None

    @property
    def username(self) -> Optional[str]:
        return getattr(self.client_user, 'username', 'na')

    @property
    def name(self) -> Optional[str]:
        return getattr(self.client_user, 'name', 'na')

    @property
    def id(self) -> Optional[str]:
        return getattr(self.client_user, 'id', 'na')

    @property
    def icon(self) -> Optional[str]:
        return getattr(self.client_user, 'icon', 'na')

    @property
    def header(self) -> Optional[str]:
        return getattr(self.client_user, 'header', 'na')

    @property
    def bot(self) -> Optional[bool]:
        return getattr(self.client_user, 'bot', 'na')

    @property
    def location(self) -> Optional[str]:
        return getattr(self.client_user, 'location', 'na')

    @property
    def website(self) -> Optional[str]:
        return getattr(self.client_user, 'website', 'na')

    @property
    def presence(self) -> Optional[str]:
        return getattr(self.client_user, 'presence', 'na')

    @property
    def joined_at(self) -> Optional[datetime.datetime]:
        return getattr(self.client_user, 'joined_at', 'na')

    def get_user(self, user_id: str) -> Optional[types.User]:
        """
        Fetches a User instance from the cache based on the passed id

        ---

        The returned data of the instance is only a copy from the cache and if
        changes are made while
        the instance exists the data will not be updated!

        :param user_id: id of the User
        :return: The User instance if it was found else None
        """
        raw_data = self.find_user(user_id)
        if raw_data:
            return types.User(raw_data, self)
        else:
            return None

    def find_user(self, user_id: str) -> Optional[dict]:
        """
        Fetches a dictionary from the cache based on the passed id

        ---

        The returned dict is only a copy from the cache

        :param user_id: id of the User
        :return: The cached dict if it exists in the cache else None
        """
        raw_data = self.storage['users'].get(user_id)
        if raw_data:
            return dict(raw_data)
        else:
            return None

    def get_house(self, house_id: str) -> Optional[types.House]:
        """
        Fetches a House from the cache based on the passed id

        ---

        The returned data of the instance is only a copy from the cache and if
        changes are made while
        the instance exists the data will not be updated!

        :param house_id: id of the House
        :return: The house instance if it was found else None
        """
        raw_data = self.find_house(house_id)
        if raw_data:
            return types.House(raw_data, self)
        else:
            return None

    def find_house(self, house_id: str) -> Optional[dict]:
        """
        Fetches a dictionary from the cache based on the passed id

        ---

        The returned dict is only a copy from the cache

        :param house_id: id of the House
        :return: The cached dict if it exists in the cache else None
        """
        raw_data = self.storage['houses'].get(house_id)
        if raw_data:
            return dict(raw_data)
        else:
            return None

    def get_entity(self, entity_id: str) -> Optional[types.Entity]:
        """
        Fetches a Entity instance from the cache based on the passed id

        ---

        The returned data of the instance is only a copy from the cache and if
        changes are made while the instance exists the data will not be
        updated!

        :param entity_id: id of the Entity
        :return: The Entity instance if it was found else None
        """
        raw_data = self.find_entity(entity_id)
        if raw_data:
            return types.Entity(raw_data, self)
        else:
            return None

    def find_entity(self, entity_id: str) -> Optional[dict]:
        """
        Fetches a dictionary from the cache based on the passed id

        ---

        The returned dict is only a copy from the cache

        :param entity_id: id of the Entity
        :return: The cached dict if it exists in the cache else None
        """
        raw_data = self.storage['entities'].get(entity_id)
        if raw_data:
            return dict(raw_data)
        else:
            return None

    def get_room(self, room_id: str) -> Optional[types.TextRoom]:
        """
        Fetches a Room from the cache based on the passed id

        ---

        The returned data of the instance is only a copy from the cache and if changes are made while
        the instance exists the data will not be updated!

        :param room_id: id of the Room
        :return: The Room instance if it was found else None
        """
        raw_data = self.find_room(room_id)
        if raw_data:
            return types.TextRoom(raw_data, self)
        else:
            return None

    def find_room(self, room_id: str) -> Optional[dict]:
        """
        Fetches a dictionary from the cache based on the passed id

        ---

        The returned dict is only a copy from the cache

        :param room_id: id of the Room
        :return: The cached dict if it exists in the cache else None
        """
        raw_data = self.storage['rooms']['house'].get(room_id)
        if raw_data:
            return dict(raw_data)
        else:
            return None

    def get_private_room(self, room_id: str) -> Optional[types.PrivateRoom]:
        """
        Fetches a single PrivateRoom from the cache based on the passed id

        ---

        The returned data of the instance is only a copy from the cache and if changes are made while
        the instance exists the data will not be updated!

        :param room_id: id of the PrivateRoom
        :return: The PrivateRoom instance if it was found else None
        """
        raw_data = self.find_private_room(room_id)
        if raw_data:
            return types.PrivateRoom(raw_data, self)
        else:
            return None

    def find_private_room(self, room_id: str) -> Optional[dict]:
        """
        Fetches a dictionary from the cache based on the passed id

        ---

        The returned dict is only a copy from the cache

        :param room_id: id of the PrivateRoom
        :return: The cached dict if it exists in the cache else None
        """
        raw_data = self.storage['rooms']['private']['single'].get(room_id)
        if raw_data:
            return dict(raw_data)
        else:
            return None

    def get_private_group_room(self, room_id: str) -> Optional[types.PrivateGroupRoom]:
        """
        Fetches a multi PrivateGroupRoom from the cache based on the passed id

        ---

        The returned data of the instance is only a copy from the cache and if changes are made while
        the instance exists the data will not be updated!

        :param room_id: id of the PrivateGroupRoom
        :return: The PrivateGroupRoom instance if it was found else None
        """
        raw_data = self.find_private_group_room(room_id)
        if raw_data:
            return types.PrivateGroupRoom(raw_data, self)
        else:
            return None

    def find_private_group_room(self, room_id: str) -> Optional[dict]:
        """
        Fetches a dictionary from the cache based on the passed id

        ---

        The returned dict is only a copy from the cache

        :param room_id: id of the PrivateGroupRoom
        :return: The cached dict if it exists in the cache else None
        """
        raw_data = self.storage['rooms']['private']['group'].get(room_id)
        if raw_data:
            return dict(raw_data)
        else:
            return None

    def get_relationship(self, user_id: str) -> Optional[types.Relationship]:
        """
        Fetches a Relationship instance from the cache based on the passed id

        ---

        The returned data of the instance is only a copy from the cache and if changes are made while
        the instance exists the data will not be updated!

        :param user_id: user-id of the Relationship
        :return: The Relationship instance if it was found else None
        """
        raw_data = self.find_relationship(user_id)
        if raw_data:
            return types.Relationship(raw_data, self)
        else:
            return None

    def find_relationship(self, user_id: str) -> Optional[dict]:
        """
        Fetches a dictionary from the cache based on the passed id

        ---

        The returned dict is only a copy from the cache

        :param user_id: user-id of the Relationship
        :return: The cached dict if it exists in the cache else None
        """
        raw_data = self.storage['relationships'].get(user_id)
        if raw_data:
            return dict(raw_data)
        else:
            return None
