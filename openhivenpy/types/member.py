import logging
import sys
from marshmallow import Schema, fields, post_load, ValidationError, RAISE

from . import HivenObject
from . import user
from .. import utils
from ..exceptions import exception as errs

logger = logging.getLogger(__name__)

__all__ = ['Member']


class Member(user.User, HivenObject):
    """
    Represents a House Member on Hiven
    """
    def __init__(self, data: dict, house, http):
        try:
            super().__init__(data.get('user', data), http)
            self._user_id = self._id
            self._house_id = data.get('house_id')
            if self._house_id is None:
                self._house_id = house.id
            self._joined_at = data.get('joined_at')
            self._roles = utils.raise_value_to_type(data.get('roles', []), list)
            
            self._house = house
            self._http = http

        except Exception as e:
            utils.log_traceback(msg="[MEMBER] Traceback:",
                                suffix="Failed to initialize the Member object; \n" 
                                       f"{sys.exc_info()[0].__name__}: {e} >> Data: {data}")
            raise errs.FaultyInitialization(f"Failed to initialize Member object! Possibly faulty data! " 
                                            f"> {sys.exc_info()[0].__name__}: {e}")

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        info = [
            ('username', self.username),
            ('name', self.name),
            ('id', self.id),
            ('icon', self.icon),
            ('header', self.header),
            ('bot', self.bot),
            ('house_id', self.house_id),
            ('joined_house_at', self.joined_house_at)
        ]
        return '<Member {}>'.format(' '.join('%s=%s' % t for t in info))

    @property
    def user_id(self) -> int:
        return getattr(self, '_user_id', None)

    @property
    def joined_house_at(self) -> str:
        return getattr(self, '_joined_at', None)

    @property
    def house_id(self) -> int:
        return getattr(self, '_house_id', None)

    @property
    def roles(self) -> list:
        return getattr(self, '_roles', None)

    @property
    def joined_at(self) -> str:
        return getattr(self, '_joined_at', None)

    async def kick(self) -> bool:
        """
        Kicks a user from the house.

        The client needs permissions to kick, or else this will raise `HivenException.Forbidden`
            
        :return: True if the request was successful else HivenException.Forbidden()
        """
        # TODO! Needs be changed with the HTTP Exceptions Update
        resp = await self._http.delete(f"/{self._house_id}/members/{self._user_id}")
        if not resp.status < 300:
            raise errs.Forbidden()
        else:
            return True
