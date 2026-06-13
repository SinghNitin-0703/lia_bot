import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # A dictionary to store active connections by session ID
        """funxtion summary and flow in very short  """
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """funxtion summary and flow in very short  """
        try:
            # Accept the WebSocket connection, ensuring we echo back the subprotocol 
            # if the client (e.g., browser) sent one for authentication.
            subprotocol = websocket.headers.get("sec-websocket-protocol")
            await websocket.accept(subprotocol=subprotocol)
            # Store it in our dictionary
            self.active_connections[session_id] = websocket
            logger.info(f"WebSocket connected successfully for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to connect WebSocket for session {session_id}: {e}", exc_info=True)

    def disconnect(self, session_id: str):
        """funxtion summary and flow in very short  """
        try:
            # Remove the connection from our dictionary if it exists
            if session_id in self.active_connections:
                del self.active_connections[session_id]
                logger.info(f"WebSocket disconnected for session: {session_id}")
        except Exception as e:
            logger.error(f"Error while disconnecting WebSocket for session {session_id}: {e}", exc_info=True)

    async def send_personal_message(self, message: str, session_id: str):
        """funxtion summary and flow in very short  """
        try:
            # Send a text message to a specific session if it is connected
            if session_id in self.active_connections:
                websocket = self.active_connections[session_id]
                await websocket.send_text(message)
                logger.info(f"Message sent to session {session_id}")
            else:
                logger.warning(f"Tried to send a message to session {session_id}, but it is not connected.")
        except Exception as e:
            logger.error(f"Failed to send message to session {session_id}: {e}", exc_info=True)

# Global singleton instance of the ConnectionManager
manager = ConnectionManager()
