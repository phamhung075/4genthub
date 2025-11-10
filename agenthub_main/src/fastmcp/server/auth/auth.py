"""
OAuth provider compatibility layer
This module provides minimal OAuth classes for import compatibility.
Actual authentication uses JWT tokens.
"""

from dataclasses import dataclass

from pydantic import BaseModel


# MCP OAuth types for compatibility
class ClientRegistrationOptions(BaseModel):
    """Client registration options for OAuth"""
    enabled: bool = False
    client_name: str | None = None
    client_uri: str | None = None
    redirect_uris: list[str] = []

class RevocationOptions(BaseModel):
    """Token revocation options for OAuth"""
    enabled: bool = False
    revocation_endpoint: str | None = None

class OAuthProvider:
    """Minimal OAuth provider stub for compatibility"""
    
    def __init__(
        self,
        issuer_url: str,
        service_documentation_url: str | None = None,
        client_registration_options: ClientRegistrationOptions | None = None,
        revocation_options: RevocationOptions | None = None,
        required_scopes: list[str] | None = None,
    ):
        self.issuer_url = issuer_url
        self.service_documentation_url = service_documentation_url
        self.client_registration_options = client_registration_options
        self.revocation_options = revocation_options
        self.required_scopes = required_scopes or []

# Additional classes that may be imported
@dataclass
class AuthorizationCode:
    """OAuth authorization code"""
    code: str
    state: str | None = None

@dataclass
class RefreshToken:
    """OAuth refresh token"""
    token: str
    expires_at: int | None = None

@dataclass
class AccessToken:
    """OAuth access token"""
    token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    scope: str | None = None