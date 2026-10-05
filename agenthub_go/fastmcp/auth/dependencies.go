// FastAPI authentication dependencies for token management, ported from
// agenthub_main/src/fastmcp/auth/dependencies.py.
//
// The FastAPI Depends/HTTPBearer plumbing has no Go meaning; what is ported is the
// token-decoding logic, the HTTPException branches and the User construction. PyJWT
// is a third-party Python library with no in-module Go equivalent available here, so
// the decode step is expressed through the TokenDecoder interface (a caller supplies
// the HS256 implementation).
package auth

import (
	"os"
	"time"

	authentities "agenthub/fastmcp/auth/domain/entities"
)

// DependenciesJWTSecretKey mirrors the module-level JWT_SECRET_KEY read. Python logs
// a CRITICAL SECURITY WARNING and leaves the value None when unset; here the empty
// string stands in for None.
var DependenciesJWTSecretKey = os.Getenv("JWT_SECRET_KEY")

// DependenciesJWTAlgorithm mirrors JWT_ALGORITHM (default HS256).
var DependenciesJWTAlgorithm = envOr("JWT_ALGORITHM", "HS256")

// TokenExpiredError signals the PyJWT ExpiredSignatureError branch; a TokenDecoder
// returns it (or an error wrapping it) for expired tokens.
type TokenExpiredError struct{}

func (TokenExpiredError) Error() string { return "signature has expired" }

// TokenDecoder decodes a JWT with PyJWT's jwt.decode(token, secret, algorithms=[alg]).
// Implementations return TokenExpiredError for an expired signature and any other
// error for an invalid token.
type TokenDecoder interface {
	DecodeJWT(token, secret, algorithm string) (map[string]any, error)
}

// GetCurrentUser mirrors get_current_user. credentials is the raw bearer token
// extracted by the FastAPI HTTPBearer dependence (the router passes it explicitly).
func GetCurrentUser(decoder TokenDecoder, credentials string) (*authentities.User, error) {
	if DependenciesJWTSecretKey == "" {
		return nil, &HTTPException{StatusCode: 500, Detail: "Server configuration error: JWT secret not set"}
	}

	payload, err := decoder.DecodeJWT(credentials, DependenciesJWTSecretKey, DependenciesJWTAlgorithm)
	if err != nil {
		if _, expired := err.(TokenExpiredError); expired {
			return nil, &HTTPException{StatusCode: 401, Detail: "Token expired"}
		}
		// PyJWT InvalidTokenError is the common branch; other errors fall through to
		// the generic handler in Python. Both yield a 401 here.
		return nil, &HTTPException{StatusCode: 401, Detail: "Invalid token"}
	}

	userID, _ := payload["sub"].(string)
	if userID == "" {
		userID, _ = payload["user_id"].(string)
	}
	email, _ := payload["email"].(string)

	if userID == "" {
		return nil, &HTTPException{StatusCode: 401, Detail: "Invalid authentication credentials"}
	}

	if exp, ok := payload["exp"]; ok {
		if v, ok := numericClaim(exp); ok && float64(time.Now().UnixNano())/1e9 > v {
			return nil, &HTTPException{StatusCode: 401, Detail: "Token expired"}
		}
	}

	if email == "" {
		email = userID + "@example.com"
	}
	username, _ := payload["username"].(string)
	if username == "" {
		if email != "" {
			username = email
		} else {
			username = userID
		}
	}

	return authentities.NewUser(authentities.User{
		ID:           &userID,
		Email:        email,
		Username:     username,
		PasswordHash: "authenticated-via-jwt", // Not used for JWT auth
	})
}

// GetOptionalCurrentUser mirrors get_optional_current_user: no credentials -> nil,
// any HTTPException from GetCurrentUser -> nil.
func GetOptionalCurrentUser(decoder TokenDecoder, credentials *string) *authentities.User {
	if credentials == nil {
		return nil
	}
	user, err := GetCurrentUser(decoder, *credentials)
	if err != nil {
		return nil
	}
	return user
}

func numericClaim(v any) (float64, bool) {
	switch n := v.(type) {
	case float64:
		return n, true
	case int64:
		return float64(n), true
	case int:
		return float64(n), true
	}
	return 0, false
}
