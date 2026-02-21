"""
backend/app/cors.py

CORS (Cross-Origin Resource Sharing) configuration for the FastAPI application.

Centralises all CORS settings so they can be applied consistently in main.py
and adjusted in a single place as the project evolves.
"""

from typing import List


def get_allowed_origins() -> List[str]:
    """
    Return the list of origins permitted to make cross-origin requests.

    Extend this list when deploying to staging/production environments.
    """
    return [
        "http://localhost:3000",    # React / Next.js dev server
        "http://localhost:5173",    # Vite dev server
        "http://localhost:8080",    # Alternative frontend port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]


# CORS policy settings — passed directly to CORSMiddleware in main.py
CORS_SETTINGS = {
    "allow_origins": get_allowed_origins(),
    "allow_credentials": True,          # Allow cookies / auth headers
    "allow_methods": ["*"],             # GET, POST, PUT, DELETE, OPTIONS, PATCH
    "allow_headers": ["*"],             # Accept all request headers
    "expose_headers": [                 # Headers the browser can read
        "X-Request-ID",
        "X-Process-Time",
    ],
}
