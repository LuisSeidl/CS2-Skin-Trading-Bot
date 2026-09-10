from abc import ABC, abstractmethod
from typing import Optional
from entities import StandardizedResult

class ClientInterface(ABC):
    """Interface for API clients"""
    keys = dict()
    limit = 0

    @abstractmethod
    def __init__(self, keys: dict, limit: int)-> None:
        """Initializes the client and assigns specific keys and values"""

    @abstractmethod
    def __call(self, method: str, path: str, payload: dict | None = None):
        """
        Calls the Client, returns the result (json list / dict) or None, raises error if occurred
        """

    @abstractmethod
    def __fetchMarketPage(self, cursor: Optional[str] = None) -> tuple[list[dict], Optional[str]]:
        """
        Fetches one page of market information fromn the market
        Returns (items_list, next_cursor)
        """

    @abstractmethod
    def __standardizeResult(self, content: dict | list) -> list[StandardizedResult]:
        """ 
        Builds a list of standardized instances for the result of the api call
        """

    @abstractmethod
    def getData(self, max_pages: int | None = None)->list[StandardizedResult]:
        """
        Entrypoint for Market-Clients
        1. Calls the API based on previously configured parameters
        2. Builds instances of weapon, item and listing
        3. Returns them in the format of list[StandardizedResult]
        """