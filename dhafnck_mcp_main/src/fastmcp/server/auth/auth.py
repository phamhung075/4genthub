"""
OAuth provider compatibility layer
This module provides minimal OAuth classes for import compatibility.
Actual authentication uses JWT tokens.
"""

from typing import Optional, List, Any
from dataclasses import dataclass
from pydantic import BaseModel

# MCP OAuth types for compatibility
class ClientRegistrationOptions(BaseModel):
    """Client registration options for OAuth"""
    enabled: bool = False
    client_name: Optional[str] = None
    client_uri: Optional[str] = None
    redirect_uris: List[str] = []

class RevocationOptions(BaseModel):
    """Token revocation options for OAuth"""
    enabled: bool = False
    revocation_endpoint: Optional[str] = None

class OAuthProvider:
    """Minimal OAuth provider stub for compatibility"""
    
    def __init__(
        self,
        issuer_url: str,
        service_documentation_url: Optional[str] = None,
        client_registration_options: Optional[ClientRegistrationOptions] = None,
        revocation_options: Optional[RevocationOptions] = None,
        required_scopes: Optional[List[str]] = None,
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
    state: Optional[str] = None

@dataclass
class RefreshToken:
    """OAuth refresh token"""
    token: str
    expires_at: Optional[int] = None

@dataclass
class AccessToken:
    """OAuth access token"""
    token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    scope: Optional[str] = None