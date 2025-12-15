"""Connection Manager - Handles persistent AD connections with retry logic."""

import time
import threading
import logging
from typing import Optional, Callable
from enum import Enum
from ldap3 import Connection, Server, ALL
from services.config_service import ADConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ConnectionManager:
    """Manages persistent LDAP connections with automatic reconnection."""
    
    def __init__(self, ad_config: ADConfig, username: str, password: str,
                 max_retries: int = 5, initial_retry_delay: float = 1.0,
                 max_retry_delay: float = 60.0, health_check_interval: float = 30.0):
        """Initialize connection manager.
        
        Args:
            ad_config: AD configuration object
            username: AD username
            password: AD password
            max_retries: Maximum number of reconnection attempts
            initial_retry_delay: Initial delay between retries (seconds)
            max_retry_delay: Maximum delay between retries (seconds)
            health_check_interval: Interval for health checks (seconds)
        """
        self.ad_config = ad_config
        self.username = username
        self.password = password
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.health_check_interval = health_check_interval
        
        # Connection state
        self._connection: Optional[Connection] = None
        self._state = ConnectionState.DISCONNECTED
        self._state_lock = threading.Lock()
        self._connection_lock = threading.Lock()
        
        # Retry state
        self._retry_count = 0
        self._last_error: Optional[str] = None
        
        # Health monitoring
        self._health_check_timer: Optional[threading.Timer] = None
        self._stop_health_check = threading.Event()
        
        # Callbacks
        self._state_change_callbacks: list[Callable[[ConnectionState, Optional[str]], None]] = []
        self._auth_failure_callback: Optional[Callable[[], None]] = None
        
        # Start connection
        self._connect()
    
    def add_state_change_callback(self, callback: Callable[[ConnectionState, Optional[str]], None]):
        """Add a callback for connection state changes.
        
        Args:
            callback: Function that receives (state, error) parameters
        """
        self._state_change_callbacks.append(callback)
    
    def _set_state(self, new_state: ConnectionState, error: Optional[str] = None):
        """Set connection state and notify callbacks.
        
        Args:
            new_state: New connection state
            error: Optional error message
        """
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            self._last_error = error
            
            logger.info(f"Connection state changed: {old_state.value} -> {new_state.value}" + 
                       (f" (Error: {error})" if error else ""))
            
        # Notify callbacks
        for callback in self._state_change_callbacks:
            try:
                callback(new_state, error)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
                import traceback
                traceback.print_exc()
    
    def set_auth_failure_callback(self, callback: Callable[[], None]):
        """Set callback for authentication failures.
        
        Args:
            callback: Function to call when authentication fails
        """
        self._auth_failure_callback = callback
    
    def _trigger_auth_failure(self):
        """Trigger authentication failure callback if set."""
        if self._auth_failure_callback:
            try:
                logger.error(": Triggering auth failure callback")
                self._auth_failure_callback()
                logger.error(": Auth failure callback completed")
            except Exception as e:
                logger.error(f"Error in auth failure callback: {e}")
                import traceback
                traceback.print_exc()
        else:
            logger.error(": No auth failure callback set")
    
    def get_state(self) -> ConnectionState:
        """Get current connection state.
        
        Returns:
            Current connection state
        """
        with self._state_lock:
            return self._state
    
    def get_last_error(self) -> Optional[str]:
        """Get last connection error.
        
        Returns:
            Last error message or None
        """
        with self._state_lock:
            return self._last_error
    
    def _create_connection(self) -> Connection:
        """Create a new LDAP connection.
        
        Returns:
            New LDAP connection
            
        Raises:
            Exception: If connection fails
        """
        bind_dn = f"{self.username}@{self.ad_config.domain}"
        port = 636 if self.ad_config.use_ssl else 389
        server = Server(self.ad_config.server, port=port, 
                       use_ssl=self.ad_config.use_ssl, get_info=ALL)
        
        logger.info(f"Creating connection to {self.ad_config.server}:{port} as {bind_dn}")
        
        conn = Connection(server, user=bind_dn, password=self.password, auto_bind=True)
        
        if not self.ad_config.use_ssl:
            logger.warning("Connected without SSL. Password operations will be disabled.")
        
        return conn
    
    def _is_authentication_error(self, error_message: str) -> bool:
        """Check if error is related to authentication.
        
        Args:
            error_message: Error message to check
            
        Returns:
            True if this is an authentication error, False otherwise
        """
        if not error_message:
            return False
        
        error_lower = error_message.lower()
        auth_indicators = [
            'invalid credentials',
            'invalidcredentials',  # LDAP specific error
            'automatic bind not successful - invalidcredentials',  # Exact error from logs
            'authentication failed',
            'bind failed',
            'access denied',
            'login failed',
            'unauthorized',
            'invalid username',
            'invalid password'
        ]
        
        # Check for common authentication error phrases
        for indicator in auth_indicators:
            if indicator in error_lower:
                return True
        
        # Check for LDAP error code 49 (invalid credentials)
        if '49' in error_message or 'code 49' in error_lower:
            return True
            
        return False
    
    def _connect(self):
        """Establish initial connection."""
        self._set_state(ConnectionState.CONNECTING)
        
        try:
            with self._connection_lock:
                self._connection = self._create_connection()
            
            self._set_state(ConnectionState.CONNECTED)
            self._retry_count = 0
            
            # Start health monitoring
            self._start_health_check()
            
        except Exception as e:
            error_msg = f"Failed to connect: {e}"
            self._set_state(ConnectionState.FAILED, error_msg)
            logger.error(error_msg)
            
            # Check if this is an authentication error - don't retry auth errors
            if self._is_authentication_error(error_msg):
                logger.error(f"Authentication error detected during initial connect - not retrying: {e}")
                self._trigger_auth_failure()
                return
            
            # Start reconnection attempts for non-authentication errors
            self._schedule_reconnect()
    
    def _schedule_reconnect(self):
        """Schedule reconnection attempt with exponential backoff."""
        if self._retry_count >= self.max_retries:
            error_msg = f"Max retries ({self.max_retries}) exceeded"
            self._set_state(ConnectionState.FAILED, error_msg)
            logger.error(error_msg)
            return
        
        # Calculate delay with exponential backoff
        delay = min(self.initial_retry_delay * (2 ** self._retry_count), 
                   self.max_retry_delay)
        
        self._retry_count += 1
        self._set_state(ConnectionState.RECONNECTING, 
                       f"Reconnecting in {delay:.1f}s (attempt {self._retry_count}/{self.max_retries})")
        
        logger.info(f"Scheduling reconnection in {delay:.1f} seconds (attempt {self._retry_count})")
        
        # Schedule reconnection
        timer = threading.Timer(delay, self._reconnect)
        timer.daemon = True
        timer.start()
    
    def _reconnect(self):
        """Attempt to reconnect."""
        try:
            # Close existing connection if any
            with self._connection_lock:
                if self._connection:
                    try:
                        self._connection.unbind()
                    except:
                        pass
                    self._connection = None
            
            # Attempt new connection
            with self._connection_lock:
                self._connection = self._create_connection()
            
            self._set_state(ConnectionState.CONNECTED)
            self._retry_count = 0
            
            # Restart health monitoring
            self._start_health_check()
            
            logger.info("Reconnection successful")
            
        except Exception as e:
            error_msg = f"Reconnection failed: {e}"
            logger.error(error_msg)
            
            # Check if this is an authentication error - don't retry auth errors
            if self._is_authentication_error(error_msg):
                logger.error(f"Authentication error detected during reconnect - not retrying: {e}")
                self._trigger_auth_failure()
                return
            
            self._schedule_reconnect()
    
    def _health_check(self):
        """Perform connection health check."""
        if self._stop_health_check.is_set():
            return
        
        try:
            with self._connection_lock:
                if not self._connection:
                    return
                
                # Simple health check - perform a search operation
                if not self._connection.search(
                    self.ad_config.base_dn,
                    '(objectClass=*)',
                    search_scope='BASE',
                    attributes=['objectClass'],
                    size_limit=1
                ):
                    raise Exception("Health check search failed")
            
            # Connection is healthy
            if self.get_state() != ConnectionState.CONNECTED:
                self._set_state(ConnectionState.CONNECTED)
                self._retry_count = 0
            
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            
            # Connection appears to be dead, trigger reconnection
            if self.get_state() == ConnectionState.CONNECTED:
                self._set_state(ConnectionState.RECONNECTING, "Connection lost, attempting to reconnect")
                self._schedule_reconnect()
        
        # Schedule next health check
        if not self._stop_health_check.is_set():
            self._health_check_timer = threading.Timer(
                self.health_check_interval, self._health_check)
            self._health_check_timer.daemon = True
            self._health_check_timer.start()
    
    def _start_health_check(self):
        """Start periodic health checks."""
        # Stop existing health check if any
        self._stop_health_check.set()
        if self._health_check_timer:
            self._health_check_timer.cancel()
        
        # Reset stop event and start new health check
        self._stop_health_check.clear()
        self._health_check_timer = threading.Timer(
            self.health_check_interval, self._health_check)
        self._health_check_timer.daemon = True
        self._health_check_timer.start()
    
    def get_connection(self) -> Optional[Connection]:
        """Get a valid connection, reconnecting if necessary.
        
        Returns:
            Valid LDAP connection or None if connection failed
        """
        state = self.get_state()
        
        # If connected, return the connection
        if state == ConnectionState.CONNECTED:
            with self._connection_lock:
                return self._connection
        
        # If reconnecting, wait a bit and try again
        elif state == ConnectionState.RECONNECTING:
            # Wait up to 5 seconds for reconnection
            for _ in range(50):  # 50 * 0.1s = 5s
                time.sleep(0.1)
                if self.get_state() == ConnectionState.CONNECTED:
                    with self._connection_lock:
                        return self._connection
            
            # If still not connected after waiting, return None
            return None
        
        # If failed or disconnected, trigger reconnection
        elif state in [ConnectionState.FAILED, ConnectionState.DISCONNECTED]:
            if self._retry_count < self.max_retries:
                self._schedule_reconnect()
                return None
        
        return None
    
    def execute_with_retry(self, operation: Callable, *args, **kwargs):
        """Execute an LDAP operation with automatic retry.
        
        Args:
            operation: Function to execute (receives connection as first argument)
            *args: Additional arguments for operation
            **kwargs: Additional keyword arguments for operation
            
        Returns:
            Result of operation or None if failed
            
        Raises:
            Exception: If operation fails after retries
        """
        max_operation_retries = 3
        operation_retry_count = 0
        
        while operation_retry_count < max_operation_retries:
            conn = self.get_connection()
            if not conn:
                raise Exception("No connection available")
            
            try:
                return operation(conn, *args, **kwargs)
            
            except Exception as e:
                operation_retry_count += 1
                error_msg = str(e)
#                logger.warning(f"Operation failed (attempt {operation_retry_count}/{max_operation_retries}): {e}")
                
                # Check if this is an authentication error - don't retry auth errors
                if self._is_authentication_error(error_msg):
#                    logger.error(f"Authentication error detected - not retrying: {e}")
                    self._trigger_auth_failure()
                    raise Exception(f"Authentication failed: {error_msg}")
                
                if operation_retry_count >= max_operation_retries:
 #                   logger.error(f"Operation failed permanently after {max_operation_retries} attempts: {e}")
                    raise
                
                # Wait a bit before retry
                time.sleep(0.5)
    
    def close(self):
        """Close connection and cleanup resources."""
        logger.info("Closing connection manager")
        
        # Stop health checks
        self._stop_health_check.set()
        if self._health_check_timer:
            self._health_check_timer.cancel()
        
        # Close connection
        with self._connection_lock:
            if self._connection:
                try:
                    self._connection.unbind()
                except:
                    pass
                self._connection = None
        
        self._set_state(ConnectionState.DISCONNECTED)