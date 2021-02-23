import logging
import sys
import types
import fastjsonschema

from .. import utils
from . import HivenObject
from ..exceptions import InvalidPassedDataError, InitializationError
logger = logging.getLogger(__name__)

__all__ = ['Embed']


class Embed(HivenObject):
    """
    Represents an embed message object
    """
    schema = {
        'type': 'object',
        'properties': {
            'url': {'type': 'string', 'default': None},
            'type': {'type': 'integer'},
            'title': {'type': 'string'},
            'image': {'type': 'string', 'default': None},
            'description': {
                'anyOf': [
                    {'type': 'object'},
                    {'type': 'null'}
                ],
                'default': None
            }
        },
        'additionalProperties': False,
        'required': ['type', 'title']
    }
    json_validator: types.FunctionType = fastjsonschema.compile(schema)

    @classmethod
    def validate(cls, data, *args, **kwargs):
        try:
            return cls.json_validator(data, *args, **kwargs)
        except Exception as e:
            utils.log_validation_traceback(cls, data, e)
            raise

    def __init__(self, **kwargs):
        """
        :param kwargs: Additional Parameter of the class that will be initialised with it
        """
        self._url = kwargs.get('url')
        self._type = kwargs.get('type')
        self._title = kwargs.get('title')
        self._image = kwargs.get('image')
        self._description = kwargs.get('description')

    @classmethod
    def form_object(cls, data: dict) -> dict:
        """
        Validates the data and appends data if it is missing that would be required for the creation of an
        instance.

        ---

        Does NOT contain other objects and only their ids!

        :param data: Dict for the data that should be passed
        :return: The modified dictionary
        """
        return cls.validate(data)

    @classmethod
    async def from_dict(cls, data: dict, client):
        """
        Creates an instance of the Embed Class with the passed data

        ---

        Does not update the cache and only read from it!
        Only intended to be used to create a instance to interact with Hiven!

        :param data: Dict for the data that should be passed
        :param client: Client used for accessing the cache
        :return: The newly constructed Embed Instance
        """
        try:
            instance = cls(**data)

        except Exception as e:
            utils.log_traceback(
                msg=f"Traceback in '{cls.__name__}' Validation:",
                suffix=f"Failed to initialise {cls.__name__} due to exception:\n"
                       f"{sys.exc_info()[0].__name__}: {e}!"
            )
            raise InitializationError(
                f"Failed to initialise {cls.__name__} due to exception:\n{sys.exc_info()[0].__name__}: {e}!"
            )
        else:
            instance._client = client
            return instance

    @property
    def url(self):
        return getattr(self, '_url', None)
    
    @property
    def type(self):
        return getattr(self, '_type', None)
    
    @property 
    def title(self):
        return getattr(self, '_title', None)

    @property 
    def image(self):
        return getattr(self, '_image', None)
    
    @property
    def description(self):
        return getattr(self, '_description', None)
