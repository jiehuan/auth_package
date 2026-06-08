"""
example_app.py
Minimal FastAPI application demonstrating auth package usage.

Corresponds to Java route-level annotations:
  @PreAuthorize("hasAuthority('read')")
  @PreAuthorize("hasAuthority('write')")
"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import azure_scheme, get_user_permissions, require_permission

app = FastAPI(
    title="SumComp API",
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": "your-client-id",  # Replace with actual client_id
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load OpenID config on startup so Swagger UI login works
@app.on_event("startup")
async def load_config():
    scheme = azure_scheme()
    await scheme.openid_config.load_config()


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/health")
async def health():
    """Public endpoint, no authentication required."""
    return {"status": "ok"}


@app.get(
    "/submissions",
    dependencies=[Depends(require_permission("read"))],
)
async def list_submissions():
    """Requires 'read' permission. Corresponds to Java @PreAuthorize("hasAuthority('read')")"""
    return {"submissions": []}


@app.post(
    "/submissions",
    dependencies=[Depends(require_permission("write"))],
)
async def create_submission():
    """Requires 'write' permission."""
    return {"status": "created"}


@app.delete(
    "/submissions/{submission_id}",
    dependencies=[Depends(require_permission("delete"))],
)
async def delete_submission(submission_id: str):
    """Requires 'delete' permission."""
    return {"status": "deleted", "id": submission_id}


@app.get("/me/permissions")
async def get_my_permissions(
    perms: set[str] = Depends(get_user_permissions),
):
    """Returns the current user's resolved permissions (useful for debugging)."""
    return {"permissions": sorted(perms)}
