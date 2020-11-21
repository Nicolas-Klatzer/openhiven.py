import logging
import sys
import asyncio

from ._get_type import getType
from .Room import Room
from .User import User
import openhivenpy.Exception as errs
from openhivenpy.Gateway.http import HTTPClient

logger = logging.getLogger(__name__)

class PrivateRoom():
    """`openhivenpy.Types.Room`
    
    Data Class for a Private Chat Room
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    The class inherits all the avaible data from Hiven(attr -> read-only)!
    
    """
    def __init__(self, data: dict, http_client: HTTPClient):
        try:
            self._id = int(data['id']) if data.get('id') != None else None
            self._last_message_id = data.get('last_message_id')
            recipients = data.get("recipients")
            self._recipient = getType.User(recipients[0], http_client)
            self._name = f"Private chat with {recipients[0]['name']}"   
            self._type = data.get('type')
             
            self.http_client = http_client
            
        except AttributeError as e: 
            logger.error(f"Error while initializing a PrivateRoom object: {e}")
            raise errs.FaultyInitialization("The data of the object PrivateRoom is not in correct Format")
        
        except Exception as e: 
            logger.error(f"Error while initializing a PrivateRoom object: {e}")
            raise sys.exc_info()[0](e)
        
    @property
    def user(self) -> User:
        return self._recipient
    
    @property
    def recipient(self) -> User:
        return self._recipient
    
    @property
    def id(self) -> User:
        return self._id

    @property
    def last_message_id(self) -> User:
        return self._last_message_id    
        
    @property
    def name(self) -> User:
        return self._name 

    @property
    def type(self) -> User:
        return self._type 
