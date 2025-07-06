# realtime/realtime_manager.py

import asyncio
import threading
from pysignalr.client import SignalRClient

from .event_bus import event_bus
from monitoring.logger import Logger

class RealtimeManager:
    """
    Manages the real-time WebSocket connections to the broker's SignalR hubs.
    It runs the async WebSocket client in a separate thread to avoid blocking
    the main application logic.
    """
    def __init__(self, session_token: str, account_id: int):
        self.logger = Logger()
        self._session_token = session_token
        self._account_id = account_id
        self._base_url = "https://gateway-rtc-demo.s2f.projectx.com/hubs/"
        
        self._user_hub_url = f"{self._base_url}user?access_token={self._session_token}"
        self._market_hub_url = f"{self._base_url}market?access_token={self._session_token}"

        # Initialize the async SignalR clients
        self.user_hub_client = SignalRClient(self._user_hub_url, skip_negotiation=True)
        self.market_hub_client = SignalRClient(self._market_hub_url, skip_negotiation=True)
        
        # The asyncio loop will run in a dedicated daemon thread
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.loop = None

    def _run_async_loop(self):
        """Runs the asyncio event loop in a dedicated thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._start_hubs())
        except Exception as e:
            self.logger.error(f"Error in RealtimeManager async loop: {e}")

    async def _start_hubs(self):
        """Sets up and starts both the user and market hub connections."""
        self._setup_user_hub_handlers()
        self._setup_market_hub_handlers()

        self.logger.info("Starting User and Market hub connections...")
        await asyncio.gather(
            self.user_hub_client.start(),
            self.market_hub_client.start()
        )

    def start(self):
        """Starts the RealtimeManager connections in a separate thread."""
        self.logger.info("Starting RealtimeManager thread...")
        self._thread.start()

    def stop(self):
        """Stops the hub connections gracefully."""
        self.logger.info("Stopping RealtimeManager...")
        if self.loop and self._thread.is_alive():
            asyncio.run_coroutine_threadsafe(self.user_hub_client.stop(), self.loop)
            asyncio.run_coroutine_threadsafe(self.market_hub_client.stop(), self.loop)

    def subscribe_to_market_data(self, contract_id: str):
        """Subscribes to market data for a given contract from the main thread."""
        if not self.loop:
            self.logger.error("Event loop is not running. Cannot subscribe.")
            return

        async def _subscribe():
            self.logger.info(f"Subscribing to market data for {contract_id}")
            await self.market_hub_client.invoke('SubscribeContractTrades', contract_id)
            await self.market_hub_client.invoke('SubscribeContractQuotes', contract_id)
        
        # Schedule the subscription on the running asyncio loop from our thread
        asyncio.run_coroutine_threadsafe(_subscribe(), self.loop)

    def _setup_user_hub_handlers(self):
        """Sets up the event handlers that listen for messages from the user hub."""
        @self.user_hub_client.on("GatewayUserOrder")
        def _on_order_update(data):
            self.logger.info(f"Received order update: {data}")
            event_bus.publish("GATEWAY_ORDER_UPDATE", data)

        @self.user_hub_client.on("GatewayUserPosition")
        def _on_position_update(data):
            self.logger.info(f"Received position update: {data}")
            event_bus.publish("GATEWAY_POSITION_UPDATE", data)
            
        @self.user_hub_client.on("GatewayUserTrade")
        def _on_user_trade(data):
            self.logger.info(f"Received user trade update (fill): {data}")
            event_bus.publish("GATEWAY_USER_TRADE_UPDATE", data)
            
        async def _subscribe_user_data_on_connect():
            self.logger.info("User hub connected. Subscribing to user data...")
            await self.user_hub_client.invoke('SubscribeOrders', self._account_id)
            await self.user_hub_client.invoke('SubscribePositions', self._account_id)
            await self.user_hub_client.invoke('SubscribeTrades', self._account_id)
            
        self.user_hub_client.add_after_start_task(_subscribe_user_data_on_connect)

    def _setup_market_hub_handlers(self):
        """Sets up the event handlers that listen for messages from the market hub."""
        @self.market_hub_client.on("GatewayTrade")
        def _on_market_trade(contract_id, data):
            event_bus.publish("GATEWAY_MARKET_TRADE", {"contractId": contract_id, "data": data})

        @self.market_hub_client.on("GatewayQuote")
        def _on_market_quote(contract_id, data):
            event_bus.publish("GATEWAY_MARKET_QUOTE", {"contractId": contract_id, "data": data})
