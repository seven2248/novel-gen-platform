"""
Shared pool and constants — imported by multiple routers to avoid
circular imports and reduce duplication.
"""
from concurrent.futures import ThreadPoolExecutor

# Shared thread pool for LLM calls — bounded to avoid resource exhaustion.
# Single pool replaces two independent pools that each had max_workers=4.
_llm_pool = ThreadPoolExecutor(max_workers=4)

# Timeout for LLM HTTP wrappers (seconds)
LLM_TIMEOUT_SECONDS = 600  # 10 minutes

# Max size for story_state payload (bytes)
MAX_STORY_STATE_SIZE = 10 * 1024 * 1024  # 10 MB
