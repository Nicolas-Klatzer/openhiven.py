import logging
import sys
import asyncio

from ._get_type import getType
import openhivenpy.exceptions as errs
from openhivenpy.gateway.http import HTTPClient

logger = logging.getLogger(__name__)

class Room():
    """`openhivenpy.types.Room`
    
    Data Class for a Hiven Room
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    The class inherits all the avaible data from Hiven(attr -> read-only)!
    
    Returned with house room lists and House.get_room()
    
    """
    def __init__(self, data: dict, http_client: HTTPClient, house): #These are all the attribs rooms have for now. Will add more when Phin says theyve been updated. Theres no functions. Yet.
        try:
            self._id = int(data.get('id')) if data.get('id') != None else None
            self._name = data.get('name')
            self._house = data.get('house_id')
            self._position = data.get('position')
            self._type = data.get('type') # 0 = Text, 1 = Portal
            self._emoji = data.get('emoji')
            self._description = data.get('description')
            self._last_message_id = data.get('last_message_id')
            
            self._house = house 
            
            self._http_client = http_client
            
        except AttributeError as e: 
            logger.error(f"Failed to initialize the Room object! Cause of Error: {str(sys.exc_info()[1])}, {str(e)} Data: {data}")
            raise errs.FaultyInitialization(f"Failed to initalize Room object! Most likely faulty data! Cause of error: {str(sys.exc_info()[1])}, {str(e)}")
        
        except Exception as e: 
            logger.error(f"Failed to initialize the Room object! Cause of Error: {str(sys.exc_info()[1])}, {str(e)} Data: {data}")
            raise errs.FaultyInitialization(f"Failed to initalize Room object! Possibly faulty data! Cause of error: {str(sys.exc_info()[1])}, {str(e)}")

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def house(self):
        return self._house

    @property
    def position(self):
        return self._position
    
    @property
    def type(self):
        return self._type #ToDo: Other room classes.

    @property
    def emoji(self):
        return self._emoji.get("data") if self._emoji != None else None #Random type attrib there aswell
    
    @property
    def description(self):
        return self._description

    async def send(self, content: str, delay: float) -> getType.Message: #ToDo: Attatchments. Requires to be binary
        """openhivenpy.types.Room.send(content)

        Sends a message in the room. Returns the message if successful.

        Parameter:
        ----------
        
        content: `str` - Content of the message
    
        delay: `str` - Seconds to wait until sending the message

        """
        #POST /rooms/roomid/messages
        #Media: POST /rooms/roomid/media_messages)
        execution_code = "Unknown"
        try:
            response = await self._http_client.post(endpoint="/rooms/{self.id}/messages", 
                                                    data={"content": content})
            execution_code = response.status
            await asyncio.sleep(delay=delay)
            msg = await getType.a_Message(response, self._http_client)
            return msg
        
        except Exception as e:
            logger.error(f"Failed to send message to Hiven! [CODE={execution_code}] Cause of Error: {str(sys.exc_info()[1])}, {str(e)}")
            raise errs.HTTPRequestError(f"Failed to send message to Hiven! [CODE={execution_code}] Cause of Error: {str(sys.exc_info()[1])}, {str(e)}") 
        
    async def edit(self, **kwargs) -> bool:
        """`openhivenpy.types.Room.edit()`
        
        Change the rooms data.
        
        Available options: emoji, name, description
        
        Returns `True` if successful
        
        """
        execution_code = None
        keys = "".join(key+" " for key in kwargs.keys()) if kwargs != {} else None
        try:
            for key in kwargs.keys():
                if key in ['emoji', 'name', 'description']:
                    response = await self._http_client.patch(endpoint=f"/rooms/{self.id}", data={key: kwargs.get(key)})
                    if response == None:
                        logger.debug(f"Failed to change the values {keys}for room {self.name} with id {self.id}!")
                        return False
                    else:
                        execution_code = response.status
                        return True
                else:
                    logger.error("The passed value does not exist in the user context!")
                    raise KeyError("The passed value does not exist in the user context!")
    
        except Exception as e:
            logger.critical(f"Failed to change the values {keys}for room {self.name} with id {self.id}. [CODE={execution_code}] Cause of Error: {str(sys.exc_info()[1])}, {str(e)}")
            raise errs.HTTPRequestError(f"Failed to change the values {keys}! Cause of Error: {str(sys.exc_info()[1])}, {str(e)}") 
        