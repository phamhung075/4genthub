// Package auth ports fastmcp/server/auth — OAuth compatibility types.
package auth

// ClientRegistrationOptions mirrors the pydantic model in auth.py.
type ClientRegistrationOptions struct {
	Enabled      bool
	ClientName   *string
	ClientURI    *string
	RedirectURIs []string
}

// NewClientRegistrationOptions returns the pydantic defaults.
func NewClientRegistrationOptions() *ClientRegistrationOptions {
	return &ClientRegistrationOptions{Enabled: false, RedirectURIs: []string{}}
}

// RevocationOptions mirrors the pydantic model in auth.py.
type RevocationOptions struct {
	Enabled            bool
	RevocationEndpoint *string
}

// NewRevocationOptions returns the pydantic defaults.
func NewRevocationOptions() *RevocationOptions {
	return &RevocationOptions{Enabled: false}
}

// OAuthProvider is the minimal OAuth provider stub for compatibility.
type OAuthProvider struct {
	IssuerURL                 string
	ServiceDocumentationURL   *string
	ClientRegistrationOptions *ClientRegistrationOptions
	RevocationOptions         *RevocationOptions
	RequiredScopes            []string
}

// NewOAuthProvider mirrors OAuthProvider.__init__.
func NewOAuthProvider(
	issuerURL string,
	serviceDocumentationURL *string,
	clientRegistrationOptions *ClientRegistrationOptions,
	revocationOptions *RevocationOptions,
	requiredScopes []string,
) *OAuthProvider {
	if requiredScopes == nil {
		requiredScopes = []string{}
	}
	return &OAuthProvider{
		IssuerURL:                 issuerURL,
		ServiceDocumentationURL:   serviceDocumentationURL,
		ClientRegistrationOptions: clientRegistrationOptions,
		RevocationOptions:         revocationOptions,
		RequiredScopes:            requiredScopes,
	}
}

// AuthorizationCode is the OAuth authorization code dataclass.
type AuthorizationCode struct {
	Code  string
	State *string
}

// RefreshToken is the OAuth refresh token dataclass.
type RefreshToken struct {
	Token     string
	ExpiresAt *int
}

// AccessToken is the OAuth access token dataclass.
type AccessToken struct {
	Token     string
	TokenType string
	ExpiresIn *int
	Scope     *string
}

// NewAccessToken returns an AccessToken with the Python default token_type.
func NewAccessToken(token string) *AccessToken {
	return &AccessToken{Token: token, TokenType: "Bearer"}
}
