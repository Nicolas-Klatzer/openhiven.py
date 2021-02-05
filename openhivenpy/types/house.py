"""House Module for Hiven House Objects"""
import logging
import sys
import typing
from marshmallow import Schema
from marshmallow import fields
from marshmallow import post_load
from marshmallow import ValidationError, RAISE, INCLUDE

from . import HivenObject, invite, user
from ..utils import utils
from ..exceptions import exception as errs
from . import entity
from . import member
from . import room

logger = logging.getLogger(__name__)

__all__ = ['House', 'LazyHouse']


class LazyHouseSchema(Schema):
    # Validations to check for the datatype and that it's passed correctly =>
    # will throw exception 'ValidationError' in case of an faulty data parsing

    id = fields.Int(required=True)
    name = fields.Str(required=True)
    icon = fields.Str(required=True, allow_none=True)
    owner_id = fields.Int(default=None)
    rooms = fields.List(fields.Field(), default=[], allow_none=True)

    @post_load
    def make_house(self, data, **kwargs):
        """
        Returns an instance of the class using the @classmethod inside the Class to initialise the object

        :param data: Dictionary that will be passed to the initialisation
        :param kwargs: Additional Data that can be passed
        :return: A new Attachment Object
        """
        return LazyHouse(**data)


class HouseSchema(LazyHouseSchema):
    # Validations to check for the datatype and that it's passed correctly =>
    # will throw exception 'ValidationError' in case of an faulty data parsing

    banner = fields.Raw(allow_none=True)
    roles = fields.List(fields.Raw(), required=True, allow_none=True)
    default_permissions = fields.Int(required=True)
    entities = fields.Raw(required=True, default=[])
    members = fields.List(fields.Raw(), default=[])
    client_member = fields.Raw(default=None, allow_none=True)

    @post_load
    def make_house(self, data, **kwargs):
        """
        Returns an instance of the class using the @classmethod inside the Class to initialise the object

        :param data: Dictionary that will be passed to the initialisation
        :param kwargs: Additional Data that can be passed
        :return: A new Attachment Object
        """
        return House(**data)


class LazyHouse(HivenObject):
    """
    Low-Level Data Class for a Hiven House

    Note! This class is a lazy class and does not have every available data!

    Consider fetching for more data the regular house object with utils.get()
    """
    def __init__(self, kwargs: dict):
        self._id = kwargs.get('id')
        self._name = kwargs.get('name')
        self._icon = kwargs.get('icon')
        self._owner_id = kwargs.get('owner_id')
        self._rooms = kwargs.get('rooms')

    def __str__(self):
        return self.name

    @classmethod
    async def from_dict(cls, data: dict, http, **kwargs):
        """
        Creates an instance of the LazyHouse Class with the passed data

        :param data: Dict for the data that should be passed
        :param http: HTTP Client for API-interaction and requests
        :return: The newly constructed LazyHouse Instance
        """
        try:
            instance = LazyHouseSchema().load(data, unknown=INCLUDE)

            # Updating the rooms afterwards when the object was already created
            _rooms = data.get('rooms')
            if _rooms is not None:
                instance._rooms = list(room.Room(d, http, instance) for d in _rooms)
            else:
                instance._rooms = None

            # Adding the http attribute for http interaction
            instance._http = http
            return instance

        except ValidationError as e:
            utils.log_validation_traceback(cls, e)
            return None

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def icon(self) -> str:
        return "https://media.hiven.io/v1/houses/{}/icons/{}".format(self.id, self._icon)

    @property
    def owner_id(self) -> int:
        return self._owner_id

    @property
    def rooms(self) -> list:
        return self._rooms


class House(LazyHouse):
    """
    Data Class for a Hiven House
    """
    def __init__(self, **kwargs):
        self._roles = kwargs.get('roles')
        self._entities = kwargs.get('entities')
        self._default_permissions = kwargs.get('default_permissions')
        self._members = kwargs.get('members')
        self._client_member = kwargs.get('client_member')
        self._banner = kwargs.get('banner')
        super().__init__(kwargs)

    def __repr__(self) -> str:
        info = [
            ('name', self.name),
            ('id', self.id),
            ('banner', self.banner),
            ('owner_id', self.owner_id)
        ]
        return '<House {}>'.format(' '.join('%s=%s' % t for t in info))

    @classmethod
    async def from_dict(cls, data: dict, http, **kwargs):
        """
        Creates an instance of the House Class with the passed data

        :param data: Dict for the data that should be passed
        :param http: HTTP Client for API-interaction and requests
        :param kwargs: Additional parameter or instances required for the initialisation
        :return: The newly constructed House Instance
        """
        try:
            data['client_member'] = None
            instance = HouseSchema().load(dict(data), unknown=RAISE)
            # Adding the http attribute for http interaction
            instance._http = http

            entities = [await entity.Entity.from_dict(e, http) for e in data.get('entities')]
            instance._entities = entities
            instance._default_permissions = data.get('default_permissions')

            members = data.get('members')
            rooms = data.get('rooms')
            instance._members = list(member.Member(d, instance, http) for d in members)
            instance._rooms = list(room.Room(d, http, instance) for d in rooms)
            instance._client_member = utils.get(instance.members, user_id=kwargs.get('client_id'))

            # Fetching the Owner of the House
            raw_data = await http.request(f"/users/{instance.owner_id}")
            if raw_data:
                data = raw_data.get('data')
                if data:
                    instance._owner = user.User(data=data, http=http)
                else:
                    raise errs.HTTPReceivedNoData()
            else:
                raise errs.HTTPFaultyResponse()

            return instance

        except ValidationError as e:
            utils.log_validation_traceback(cls, e)
            return None
    
        except Exception as e:
            utils.log_traceback(msg=f"Traceback in '{cls.__name__}' Validation:",
                                suffix=f"Failed to initialise {cls.__name__} due to exception:\n"
                                       f"{sys.exc_info()[0].__name__}: {e}!")

    @property
    def banner(self) -> list:
        return self._banner

    @property
    def roles(self) -> list:
        return self._roles

    @property
    def entities(self) -> list:
        return self._entities

    @property
    def users(self) -> list:
        return self._members

    @property
    def members(self) -> list:
        return self._members

    async def get_member(self, member_id: int):
        """openhivenpy.types.House.get_member()

        Returns a Hiven Member Object based on the passed ID.

        Returns the Member if it exists else returns None
        """
        try:
            cached_member = utils.get(self._members, id=member_id)
            if cached_member:
                _raw_data = await self._http.request(f"/houses/{self.id}/users/{member_id}")

                if _raw_data:
                    _data = _raw_data.get('data')
                    if _data:
                        return member.Member(
                            data=_data,
                            http=self._http,
                            house=self)
                    else:
                        raise errs.HTTPReceivedNoData()
                else:
                    raise errs.HTTPReceivedNoData()
            else:
                logger.warning(f"[HOUSE] Found no member with specified id={member_id} in {repr(self)}!")

            return None

        except Exception as e:
            utils.log_traceback(msg="[HOUSE] Traceback:",
                                suffix=f"Failed to get the member with id {member_id}; \n"
                                       f"{sys.exc_info()[0].__name__}: {e}")
            return False

    async def get_room(self, room_id: int):
        """openhivenpy.types.House.get_room()

        Returns a Hiven Room Object based on the passed ID.

        Returns the Room if it exists else returns None
        """
        try:
            cached_room = utils.get(self._rooms, id=room_id)
            if cached_room:
                return cached_room
                # Not Possible yet
                # data = await self._http.request(f"/rooms/{room_id}")
                # return Room(data, self._http)
            else:
                logger.warning(f"[HOUSE] Found no room with specified id={room_id} in the client cache!")

            return None
        except Exception as e:
            utils.log_traceback(msg="[HOUSE] Traceback:",
                                suffix=f"Failed to get the room with id {room_id} in house {repr(self)}; \n"
                                       f"{sys.exc_info()[0].__name__}: {e}")
            return False

    async def create_room(
            self,
            name: str,
            parent_entity_id: typing.Optional[typing.Union[float, int]] = None) -> typing.Union[room.Room, None]:
        """
        Creates a Room in the house with the specified name. 
        
        :return: A Room Instance for the Hiven Room that was created if successful else None
        """
        try:
            json = {'name': name}
            if parent_entity_id:
                json['parent_entity_id'] = parent_entity_id
            else:
                # If no ID was passed it will default to the Rooms category which serves as default for all
                # entities
                entity = utils.get(self.entities, name="Rooms")
                json['parent_entity_id'] = entity.id

            # Creating the room using the api
            resp = await self._http.post(
                f"/houses/{self._id}/rooms",
                json=json)

            if resp.status < 300:
                data = (await resp.json()).get('data')
                if data:
                    _room = room.Room(data, self._http, self)

                    return _room
                else:
                    raise errs.HTTPReceivedNoData()
            else:
                raise errs.HTTPFaultyResponse("Unknown! See HTTP Logs!")

        except Exception as e:
            utils.log_traceback(msg="[HOUSE] Traceback:",
                                suffix=f"Failed to create room '{name}' in house {repr(self)}; \n"
                                       f"{sys.exc_info()[0].__name__}: {e}")
            return None

    # TODO! Delete Room!

    async def create_entity(self, name: str) -> typing.Union[entity.Entity, None]:
        """openhivenpy.types.House.create_entity()

        Creates a entity in the house with the specified name.

        """
        try:
            json = {'name': name, 'type': 1}
            resp = await self._http.post(
                endpoint=f"/houses/{self._id}/entities",
                json=json)

            if resp.status < 300:
                raw_data = await resp.json()
                data = raw_data.get('data')
                if data:
                    _entity = entity.Entity(data, self._http)
                    self._entities.append(_entity)
                    return _entity
                else:
                    raise errs.HTTPReceivedNoData()
            else:
                raise errs.HTTPFaultyResponse("Unknown! See HTTP Logs!")

        except Exception as e:
            utils.log_traceback(msg="[HOUSE] Traceback:",
                                suffix=f"Failed to create category '{name}' in house {repr(self)}; \n"
                                       f"{sys.exc_info()[0].__name__}: {e}")
            return None

    async def leave(self) -> bool:
        """openhivenpy.types.House.leave()

        Leaves the house.
        
        Returns the house ID if successful.
        
        """
        try:
            resp = await self._http.delete(endpoint=f"/users/@me/houses/{self.id}")

            if resp.status < 300:
                return True
            else:
                raise errs.HTTPFaultyResponse("Unknown! See HTTP Logs!")

        except Exception as e:
            utils.log_traceback(msg="[HOUSE] Traceback:",
                                suffix=f"Failed to leave {repr(self)}; \n"
                                       f"{sys.exc_info()[0].__name__}: {e}")
            return False

    async def edit(self, **kwargs) -> bool:
        """
        Changes the houses data on Hiven.

        Available options: name, icon(base64)

        :return: True if the request was successful else False
        """
        try:
            for key in kwargs.keys():
                if key in ['name']:
                    resp = await self._http.patch(
                        endpoint=f"/houses/{self.id}",
                        json={key: kwargs.get(key)})

                    if resp.status < 300:
                        return True
                    else:
                        raise errs.HTTPFaultyResponse("Unknown! See HTTP Logs!")
                else:
                    raise NameError("The passed value does not exist in the user context!")

        except Exception as e:
            keys = "".join(key + " " for key in kwargs.keys()) if kwargs != {} else ''

            utils.log_traceback(msg="[HOUSE] Traceback:",
                                suffix=f"Failed edit request of values '{keys}' in house {repr(self)}; \n"
                                       f"{sys.exc_info()[0].__name__}: {e}")
            return False

    async def create_invite(self, max_uses: int) -> typing.Union[invite.Invite, None]:
        """
        Creates an invite for the current house. 

        :param max_uses: Maximal uses for the invite code
        :return: The invite url if successful.
        """
        try:
            # TODO! Needs implementation for max_uses
            resp = await self._http.post(endpoint=f"/houses/{self.id}/invites")

            if resp.status < 300:
                raw_data = await resp.json()
                data = raw_data.get('data', {})

                if data:
                    return invite.Invite(data, self, self._http)
                else:
                    raise errs.HTTPReceivedNoData()
            else:
                raise errs.HTTPFaultyResponse("Unknown! See HTTP Logs!")

        except Exception as e:
            utils.log_traceback(msg="[HOUSE] Traceback:",
                                suffix=f"Failed to create invite for house {self.name} with id {self.id}; \n"
                                       f"{sys.exc_info()[0].__name__}: {e}")
            return None

    async def delete(self) -> typing.Union[int, None]:
        """
        Deletes the house if permissions are sufficient!
        
        :return: The house ID if successful else None
        """
        try:
            resp = await self._http.delete(f"/houses/{self.id}")

            if resp.status < 300:
                return self.id
            else:
                return None

        except Exception as e:
            utils.log_traceback(msg="[HOUSE] Traceback:",
                                suffix=f"Failed to delete House {repr(self)}; \n"
                                       f"{sys.exc_info()[0].__name__}: {e}")
            return None
