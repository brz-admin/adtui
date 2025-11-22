"""History Service - Manages operation history for undo functionality."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict


@dataclass
class Operation:
    """Represents a single operation in history."""
    type: str
    details: Dict
    timestamp: datetime


class HistoryService:
    """Manages operation history for undo functionality."""
    
    def __init__(self, max_size: int = 50):
        """Initialize history service.
        
        Args:
            max_size: Maximum number of operations to track
        """
        self.operations: List[Operation] = []
        self.max_size = max_size
    
    def add(self, operation_type: str, details: Dict) -> None:
        """Add an operation to history.
        
        Args:
            operation_type: Type of operation (create_ou, move, delete, etc.)
            details: Dictionary containing operation details
        """
        operation = Operation(
            type=operation_type,
            details=details,
            timestamp=datetime.now()
        )
        
        self.operations.append(operation)
        
        # Keep only last max_size operations
        if len(self.operations) > self.max_size:
            self.operations.pop(0)
    
    def get_last(self) -> Optional[Operation]:
        """Get the last operation without removing it.
        
        Returns:
            Last operation or None if history is empty
        """
        if self.operations:
            return self.operations[-1]
        return None
    
    def pop_last(self) -> Optional[Operation]:
        """Get and remove the last operation.
        
        Returns:
            Last operation or None if history is empty
        """
        if self.operations:
            return self.operations.pop()
        return None
    
    def clear(self) -> None:
        """Clear all history."""
        self.operations.clear()
    
    def get_all(self) -> List[Operation]:
        """Get all operations in history.
        
        Returns:
            List of all operations
        """
        return self.operations.copy()
    
    def count(self) -> int:
        """Get number of operations in history.
        
        Returns:
            Number of operations
        """
        return len(self.operations)
    
    def can_undo(self) -> bool:
        """Check if there are operations to undo.
        
        Returns:
            True if history is not empty
        """
        return len(self.operations) > 0
