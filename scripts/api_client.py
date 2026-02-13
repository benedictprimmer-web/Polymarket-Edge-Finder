"""
Polymarket API Client
Centralized API client for interacting with Polymarket's Gamma and CLOB APIs.
Includes rate limiting, retry logic, and proper error handling.
"""

import logging
import time
import requests
from typing import Optional, Dict, List, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PolymarketClient:
    """
    Client for interacting with Polymarket APIs.
    
    Supports:
    - Gamma API: Market discovery and metadata
    - CLOB API: Orderbooks, prices, and live data
    
    Features:
    - Automatic retries with exponential backoff
    - Rate limiting to avoid throttling
    - Proper error handling
    - SSL verification (no insecure requests)
    """
    
    # API Base URLs
    GAMMA_API_BASE = "https://gamma-api.polymarket.com"
    CLOB_API_BASE = "https://clob.polymarket.com"
    
    def __init__(self, rate_limit_delay: float = 0.5, timeout: int = 10):
        """
        Initialize the Polymarket API client.
        
        Args:
            rate_limit_delay: Delay in seconds between requests (default: 0.5s)
            timeout: Request timeout in seconds (default: 10s)
        """
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout)),
        reraise=True
    )
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make an HTTP GET request with retry logic and error handling.
        
        Args:
            url: The URL to request
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.exceptions.RequestException: On request failures after retries
        """
        self._rate_limit()
        
        try:
            logger.debug(f"Making request to: {url} with params: {params}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            try:
                return response.json()
            except ValueError as e:
                logger.error(f"Failed to parse JSON response from {url}: {e}")
                raise
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error for {url}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            raise
    
    # Gamma API Methods
    
    def get_markets(self, limit: int = 100, offset: int = 0, closed: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Fetch markets from the Gamma API.
        
        Args:
            limit: Number of markets to fetch (default: 100, max: 100)
            offset: Offset for pagination (default: 0)
            closed: Filter by closed status (None = all, True = closed only, False = active only)
            
        Returns:
            List of market dictionaries
        """
        url = f"{self.GAMMA_API_BASE}/markets"
        params = {"limit": limit, "offset": offset}
        
        if closed is not None:
            params["closed"] = "true" if closed else "false"
        
        logger.info(f"Fetching markets: limit={limit}, offset={offset}, closed={closed}")
        
        try:
            data = self._make_request(url, params)
            # The API returns a list directly
            if isinstance(data, list):
                return data
            # Or it might be wrapped in a 'data' field
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            else:
                return data if data else []
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch event details from the Gamma API.
        
        Args:
            event_id: The event ID
            
        Returns:
            Event dictionary or None if not found
        """
        url = f"{self.GAMMA_API_BASE}/events/{event_id}"
        logger.info(f"Fetching event: {event_id}")
        
        try:
            return self._make_request(url)
        except Exception as e:
            logger.error(f"Error fetching event {event_id}: {e}")
            return None
    
    # CLOB API Methods
    
    def get_orderbook(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch orderbook for a token from the CLOB API.
        
        Args:
            token_id: The token ID (YES or NO token)
            
        Returns:
            Orderbook dictionary with 'bids' and 'asks' or None on error
        """
        url = f"{self.CLOB_API_BASE}/book"
        params = {"token_id": token_id}
        logger.debug(f"Fetching orderbook for token: {token_id}")
        
        try:
            return self._make_request(url, params)
        except Exception as e:
            logger.warning(f"Error fetching orderbook for token {token_id}: {e}")
            return None
    
    def get_price(self, token_id: str, side: str = "buy") -> Optional[Dict[str, Any]]:
        """
        Fetch current price for a token from the CLOB API.
        
        Args:
            token_id: The token ID
            side: 'buy' or 'sell'
            
        Returns:
            Price data dictionary or None on error
        """
        url = f"{self.CLOB_API_BASE}/price"
        params = {"token_id": token_id, "side": side}
        logger.debug(f"Fetching price for token: {token_id}, side: {side}")
        
        try:
            return self._make_request(url, params)
        except Exception as e:
            logger.warning(f"Error fetching price for token {token_id}: {e}")
            return None
    
    def get_midpoint(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch midpoint price for a token from the CLOB API.
        
        Args:
            token_id: The token ID
            
        Returns:
            Midpoint data dictionary or None on error
        """
        url = f"{self.CLOB_API_BASE}/midpoint"
        params = {"token_id": token_id}
        logger.debug(f"Fetching midpoint for token: {token_id}")
        
        try:
            return self._make_request(url, params)
        except Exception as e:
            logger.warning(f"Error fetching midpoint for token {token_id}: {e}")
            return None
    
    def get_clob_markets(self) -> List[Dict[str, Any]]:
        """
        Fetch all markets from the CLOB API.
        
        Returns:
            List of market dictionaries
        """
        url = f"{self.CLOB_API_BASE}/markets"
        logger.info("Fetching CLOB markets")
        
        try:
            data = self._make_request(url)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            else:
                return []
        except Exception as e:
            logger.error(f"Error fetching CLOB markets: {e}")
            return []
    
    def get_prices_history(self, token_id: str, interval: str = "max", fidelity: int = 60) -> Optional[Dict[str, Any]]:
        """
        Fetch historical prices for a token from the CLOB API.
        
        Args:
            token_id: The token ID
            interval: Time interval ('max' for all available data)
            fidelity: Data point frequency in seconds (default: 60 = 1 minute)
            
        Returns:
            Price history dictionary or None on error
        """
        url = f"{self.CLOB_API_BASE}/prices-history"
        params = {"market": token_id, "interval": interval, "fidelity": fidelity}
        logger.debug(f"Fetching price history for token: {token_id}")
        
        try:
            return self._make_request(url, params)
        except Exception as e:
            logger.warning(f"Error fetching price history for token {token_id}: {e}")
            return None
