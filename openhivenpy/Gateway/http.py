import aiohttp
import asyncio
import logging
from typing import Optional

from openhivenpy.Exception import ConnectionError

logger = logging.getLogger(__name__)

request_url_format = "{0}/{1}"

class HTTPClient():
    """`openhivenpy.Gateway`
    
    HTTPClient
    ~~~~~~~~~~
    
    HTTPClient for requests and interaction with the Hiven API
    
    Parameter:
    ----------
    
    api_url: `str` - Url for the API which will be used to interact with Hiven. Defaults to 'https://api.hiven.io' 
    
    api_version: `str` - Version string for the API Version. Defaults to 'v1' 
    
    token: `str` - Needed for the authorization to Hiven.
    
    event_loop: `asyncio.AbstractEventLoop` - Event loop that will be used to execute all async functions.
    
    """
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = asyncio.get_event_loop(), **kwargs):
        
        self._TOKEN = kwargs.get('token')
        self.api_url = kwargs.get('api_url', "v1")
        self.api_version = kwargs.get('api_version', "https://api.hiven.io")
        self.request_url = request_url_format.format(self.api_url, self.api_version)        
        
        self.headers = {"Content-Type": "application/json", 
                        "User-Agent":"openhiven.py by ©FrostbyteSpace on GitHub",
                        "Authorization": self._TOKEN}
        
        self.http_ready = False
        
        self.session = None
        self.loop = loop    
        
    async def connect(self) -> dict:
        """`openhivenpy.Gateway.HTTPClient.connect()`

        Establishes for the HTTPClient a connection to Hiven
        
        """
        try:
            self.session = aiohttp.ClientSession(loop=self.loop)
            
            async with self.session.get(url=f"{self.request_url}/users/@me", headers=self.headers) as r:
                if r.status == 200:
                    json = await r.json()
                    error = json.get('error', False)
                    if error == False:
                        return json
                    else:
                        error_code = ' '+json['error']['code'] if json['error'].get('code') != None else ''
                        error_message = json['error']['code'] if json['error'].get('message') != None else 'Faulty request!'
                        logger.debug(f"Error while inital request{error_code}: {error_message}")
                        
                        return None
                else:
                    raise ConnectionError(f"The Request to Hiven failed! Statuscode: {r.status}")
                
        except Exception as e:
            logger.error(f"An error occured while trying to request client data from Hiven: {e}")
            return None
            
    async def close(self) -> bool:
        """`openhivenpy.Gateway.HTTPClient.connect()`

        Closes the connection to Hiven
        
        """
        try:
            await self.session.close()
            self.http_ready = False
        except Exception as e:
            logger.error(f"An error occured while trying to close the HTTP Connection to Hiven: {e}")
    
    async def raw_request(self, endpoint: str, *, json_data: dict = None, timeout: int = 5, **kwargs) -> aiohttp.ClientResponse:
        """`openhivenpy.Gateway.HTTPClient.raw_request()`

        Wrapped HTTP request for a specified endpoint. 
        
        Returns the raw ClientResponse object
        
        Parameter:
        ----------
        
        endpoint: `str` - Url place in url format '/../../..' Will be appended to the standard link: 'https://api.hiven.io/version'
    
        json_data: `str` - JSON format data that will be appended to the request
        
        timeout: `int` - Time the server has time to respond before the connection timeouts. Defaults to 5
        
        method: `str` - HTTP Method that should be used to perform the request
        
        **kwargs: `any` - Other parameter for requesting. See https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession for more info
        
        """
        method = kwargs.get('method', 'get')
        if self.http_ready:
            async with self.session.request(url=f"{self.request_url}{endpoint}", 
                                            headers=self.headers, 
                                            json=json_data, 
                                            timeout=timeout,
                                            **kwargs) as r:
                json = await r.json()
                error = json.get('error', False)
                if error:
                    error_code = json['error']['code'] if json['error'].get('code') != None else 'Unknown'
                    error_message = json['error']['message'] if json['error'].get('message') != None else 'Faulty request!'
                else:
                    error_code = "Unknown"
                    error_message = "Faulty request!"
                    
                if r.status == 200 or r.status == 202 or r.status == 204:
                    if error == False:
                        return r
                    else:
                        logger.debug(f"An error with code {r.status} occured while performing HTTP {method} with endpoint: {self.request_url}{endpoint}")
                        logger.debug(f"Errormessage: {error_code} - {error_message}")
                        
                        return None
                else:
                    logger.debug(f"An error with code {r.status} occured while performing HTTP {method} with endpoint: {self.request_url}{endpoint}")
                    logger.debug(f"Errormessage: {error_code} - {error_message}")
                    return None
        else:
            logger.error("The HTTPClient was not ready when trying to HTTP {method}! The connection is either faulty initalized or closed!")
            return None    
    
    async def request(self, endpoint: str, *, json_data: dict = None, timeout: int = 5, **kwargs) -> dict:
        """`openhivenpy.Gateway.HTTPClient.request()`

        Wrapped HTTP request for a specified endpoint. 
        
        Returns a python dictionary containing the response data if successful and else returns `None`
        
        Parameter:
        ----------
        
        endpoint: `str` - Url place in url format '/../../..' Will be appended to the standard link: 'https://api.hiven.io/version'
    
        json_data: `str` - JSON format data that will be appended to the request
        
        timeout: `int` - Time the server has time to respond before the connection timeouts. Defaults to 5
        
        **kwargs: `any` - Other parameter for requesting. See https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession for more info
        
        """
        response = await self.raw_request(endpoint, method="get", timeout=timeout)
        if response != None:
            return await response.json()
        else:
            return None
    
    async def post(self, endpoint: str, *, json_data: dict = None, timeout: int = 5, **kwargs) -> aiohttp.ClientResponse:
        """`openhivenpy.Gateway.HTTPClient.post()`

        Wrapped HTTP Post for a specified endpoint.
        
        Returns the ClientResponse object if successful and else returns `None`
        
        Parameter:
        ----------
        
        endpoint: `str` - Url place in url format '/../../..' Will be appended to the standard link: 'https://api.hiven.io/version'
    
        json_data: `str` - JSON format data that will be appended to the request
        
        timeout: `int` - Time the server has time to respond before the connection timeouts. Defaults to 5
        
        **kwargs: `any` - Other parameter for requesting. See https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession for more info
        
        """
        return await self.raw_request(endpoint, json_data=json_data, timeout=timeout, method="post", **kwargs)
            
    async def delete(self, endpoint: str, *, timeout: int = 5, **kwargs) -> aiohttp.ClientResponse:
        """`openhivenpy.Gateway.HTTPClient.delete()`

        Wrapped HTTP delete for a specified endpoint.
        
        Returns the ClientResponse object if successful and else returns `None`
        
        Parameter:
        ----------
        
        endpoint: `str` - Url place in url format '/../../..' Will be appended to the standard link: 'https://api.hiven.io/version'
    
        json_data: `str` - JSON format data that will be appended to the request
        
        timeout: `int` - Time the server has time to respond before the connection timeouts. Defaults to 5
        
        **kwargs: `any` - Other parameter for requesting. See https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession for more info
        
        
        """
        return await self.raw_request(endpoint, timeout=timeout, method="delete", **kwargs)
        
    async def put(self, endpoint: str, *, json_data: dict = None, timeout: int = 5, **kwargs) -> aiohttp.ClientResponse:
        """`openhivenpy.Gateway.HTTPClient.put()`

        Wrapped HTTP put for a specified endpoint.
        
        Similar to post, but multiple requests do not affect performance
        
        Returns the ClientResponse object if successful and else returns `None`
        
        Parameter:
        ----------
        
        endpoint: `str` - Url place in url format '/../../..' Will be appended to the standard link: 'https://api.hiven.io/version'
    
        json_data: `str` - JSON format data that will be appended to the request
        
        timeout: `int` - Time the server has time to respond before the connection timeouts. Defaults to 5
        
        **kwargs: `any` - Other parameter for requesting. See https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession for more info
        
        
        """
        return await self.raw_request(endpoint, json_data=json_data, timeout=timeout, method="put", **kwargs)
        
    async def patch(self, endpoint: str, *, json_data: dict = None, timeout: int = 5, **kwargs) -> aiohttp.ClientResponse:
        """`openhivenpy.Gateway.HTTPClient.patch()`

        Wrapped HTTP patch for a specified endpoint.
        
        Returns the ClientResponse object if successful and else returns `None`
        
        Parameter:
        ----------
        
        endpoint: `str` - Url place in url format '/../../..' Will be appended to the standard link: 'https://api.hiven.io/version'
    
        json_data: `str` - JSON format data that will be appended to the request
        
        timeout: `int` - Time the server has time to respond before the connection timeouts. Defaults to 5
        
        **kwargs: `any` - Other parameter for requesting. See https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession for more info
        
        
        """
        return await self.raw_request(endpoint, json_data=json_data, timeout=timeout, method="patch", **kwargs)
    
    async def options(self, endpoint: str, *, json_data: dict = None, timeout: int = 5, **kwargs) -> aiohttp.ClientResponse:
        """`openhivenpy.Gateway.HTTPClient.options()`

        Wrapped HTTP options for a specified endpoint.
        
        Requests permission for performing communication with a URL or server
        
        Returns the ClientResponse object if successful and else returns `None`
        
        Parameter:
        ----------
        
        endpoint: `str` - Url place in url format '/../../..' Will be appended to the standard link: 'https://api.hiven.io/version'
    
        json_data: `str` - JSON format data that will be appended to the request
        
        timeout: `int` - Time the server has time to respond before the connection timeouts. Defaults to 5
        
        **kwargs: `any` - Other parameter for requesting. See https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession for more info
        
        """
        return await self.raw_request(endpoint, json_data=json_data, timeout=timeout, method="options", **kwargs)
    