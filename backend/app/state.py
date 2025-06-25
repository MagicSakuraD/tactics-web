
"""
Global state management for the application.
This module holds shared data, like active simulation sessions,
to avoid circular dependencies when accessing state from different parts
of the application.
"""
from typing import Dict, Any

# In-memory store for simulation sessions.
# Key: session_id (str)
# Value: session_data (Dict[str, Any])
sessions: Dict[str, Dict[str, Any]] = {}
