"""ADSession - everything tied to one logged-in Active Directory."""

import itertools
from typing import Any, Optional

from .connection_manager import ConnectionManager
from .history_service import HistoryService
from .ldap_service import LDAPService
from .ou_index import OUIndex
from .path_service import PathService

_ids = itertools.count(1)


class ADSession:
    """One AD connection with its own services, history and tree widget.

    The app can hold several sessions at once (one per AD). Every action is
    performed with the session that owns the object currently selected.
    """

    def __init__(
        self,
        ad_config,
        username: str,
        connection_manager: ConnectionManager,
    ):
        self.id = next(_ids)
        self.ad_config = ad_config
        self.username = username
        self.connection_manager = connection_manager
        self.base_dn: str = ad_config.base_dn
        self.name: str = ad_config.domain

        self.ldap_service = LDAPService(connection_manager, self.base_dn)
        self.path_service = PathService(self.base_dn)
        self.history_service = HistoryService(max_size=50)
        self.ou_index = OUIndex(self.base_dn)

        # Set by the app once the tree widget has been created
        self.adtree: Optional[Any] = None

    @property
    def title(self) -> str:
        """Short label used as the tree border title."""
        return f"{self.name} · {self.username}"

    def close(self) -> None:
        """Disconnect without notifying the app (it is the one closing us)."""
        try:
            self.connection_manager._state_change_callbacks.clear()
            self.connection_manager.set_auth_failure_callback(None)
            self.connection_manager.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"<ADSession {self.id} {self.title}>"
