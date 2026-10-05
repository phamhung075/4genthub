package services

import (
	"bytes"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"math"
	"math/big"
	"regexp"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Token configuration.
const (
	JWTAlgorithm             = "HS256"
	AccessTokenExpireMinutes = 15 // short-lived access tokens
	RefreshTokenExpireDays   = 30 // long-lived refresh tokens
	ResetTokenExpireHours    = 24 // password reset tokens
	DefaultIssuer            = "agenthub"
	DefaultAudience          = "mcp-server"
)

// JWTService creates and validates HS256 tokens with PyJWT 2.10.1 semantics.
type JWTService struct {
	SecretKey string
	Issuer    string

	// Now is the clock (UTC); TokenHex is secrets.token_hex(n). Both are injectable.
	Now      func() time.Time
	TokenHex func(nBytes int) string
}

// NewJWTService requires a non-empty secret key (issuer default: DefaultIssuer).
func NewJWTService(secretKey, issuer string) (*JWTService, error) {
	if secretKey == "" {
		return nil, &value_objects.ValueError{Msg: "Secret key is required for JWT service"}
	}
	return &JWTService{
		SecretKey: secretKey, Issuer: issuer,
		Now: func() time.Time { return time.Now().UTC() },
		TokenHex: func(n int) string {
			b := make([]byte, n)
			if _, err := rand.Read(b); err != nil {
				panic(err)
			}
			return hex.EncodeToString(b)
		},
	}, nil
}

func (s *JWTService) now() time.Time { return s.Now().Truncate(time.Microsecond) }

// intDate is timegm(utctimetuple()): whole seconds, truncated.
func intDate(t time.Time) int64 { return t.UTC().Unix() }

// pemNames are the PEM labels PyJWT refuses as HMAC secrets.
var pemNames = []string{
	"CERTIFICATE", "TRUSTED CERTIFICATE", "PRIVATE KEY", "PUBLIC KEY", "ENCRYPTED PRIVATE KEY",
	"OPENSSH PRIVATE KEY", "DSA PRIVATE KEY", "RSA PRIVATE KEY", "RSA PUBLIC KEY", "EC PRIVATE KEY",
	"DH PARAMETERS", "NEW CERTIFICATE REQUEST", "CERTIFICATE REQUEST", "SSH2 PUBLIC KEY",
	"SSH2 ENCRYPTED PRIVATE KEY", "X509 CRL",
}

var pemRes []*regexp.Regexp

func init() {
	for _, n := range pemNames {
		pemRes = append(pemRes, regexp.MustCompile(`(?s)----[- ]BEGIN `+regexp.QuoteMeta(n)+`[- ]----\r?\n.+?\r?\n----[- ]END `+regexp.QuoteMeta(n)+`[- ]----\r?\n?`))
	}
}

var sshKeyFormats = []string{"ssh-ed25519", "ssh-rsa", "ssh-dss", "ecdsa-sha2-nistp256", "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521"}

var errInvalidKey = errors.New("The specified key is an asymmetric key or x509 certificate and should not be used as an HMAC secret.")

// hmacKey is HMACAlgorithm.prepare_key.
func (s *JWTService) hmacKey() ([]byte, error) {
	key := []byte(s.SecretKey)
	for _, re := range pemRes {
		if re.Match(key) {
			return nil, errInvalidKey
		}
	}
	for _, f := range sshKeyFormats {
		if bytes.HasPrefix(key, []byte(f)) {
			return nil, errInvalidKey
		}
	}
	return key, nil
}

func b64urlEncode(b []byte) string { return base64.RawURLEncoding.EncodeToString(b) }

// b64urlDecode is PyJWT's base64url_decode: the raw segment is padded with '=' to a
// multiple of 4 (garbage characters count), '-' and '_' become '+' and '/', and the result
// goes through CPython's non-strict binascii.a2b_base64.
func b64urlDecode(in []byte) ([]byte, error) {
	if rem := len(in) % 4; rem > 0 {
		in = append(append([]byte{}, in...), strings.Repeat("=", 4-rem)...)
	}
	const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
	var out []byte
	quadPos, pads := 0, 0
	var left byte
	completed := false
loop:
	for _, c := range in {
		switch c {
		case '-':
			c = '+'
		case '_':
			c = '/'
		case '=':
			// Once a pad completes the quad nothing after it is parsed.
			pads++
			if quadPos >= 2 && quadPos+pads >= 4 {
				completed = true
				break loop
			}
			continue
		}
		v := strings.IndexByte(alphabet, c)
		if v < 0 {
			continue // characters outside the alphabet are discarded
		}
		pads = 0
		b := byte(v)
		switch quadPos {
		case 0:
			quadPos, left = 1, b
		case 1:
			out = append(out, left<<2|b>>4)
			quadPos, left = 2, b&0xf
		case 2:
			out = append(out, left<<4|b>>2)
			quadPos, left = 3, b&3
		case 3:
			out = append(out, left<<6|b)
			quadPos, left = 0, 0
		}
	}
	if !completed && quadPos != 0 {
		return nil, errors.New("Incorrect padding")
	}
	return out, nil
}

// encode is jwt.encode(payload, key, "HS256"): sorted header {"alg","typ"}, compact
// ensure_ascii payload in insertion order.
func (s *JWTService) encode(payload *entities.OrderedMap[any]) (string, error) {
	key, err := s.hmacKey()
	if err != nil {
		return "", err
	}
	body, err := value_objects.PyJSONDumpsCompact(payload)
	if err != nil {
		return "", err
	}
	signingInput := b64urlEncode([]byte(`{"alg":"HS256","typ":"JWT"}`)) + "." + b64urlEncode([]byte(body))
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(signingInput))
	return signingInput + "." + b64urlEncode(mac.Sum(nil)), nil
}

func (s *JWTService) claims(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

// CreateAccessToken creates an access token; additionalClaims are merged last (an
// existing key keeps its position, new keys are appended).
func (s *JWTService) CreateAccessToken(userID, email string, roles []string, additionalClaims *entities.OrderedMap[any], audience string) (string, error) {
	now := s.now()
	// roles is written as given: a nil list is JSON null, like Python's None.
	var rolesClaim any
	if roles != nil {
		rolesClaim = roles
	}
	p := s.claims(
		"sub", userID, "email", email, "roles", rolesClaim, "type", "access", "aud", audience,
		"iat", intDate(now), "exp", intDate(now.Add(AccessTokenExpireMinutes*time.Minute)),
		"iss", s.Issuer, "jti", s.TokenHex(16),
	)
	if additionalClaims != nil {
		for _, k := range additionalClaims.Keys() {
			v, _ := additionalClaims.Get(k)
			p.Set(k, v)
		}
	}
	return s.encode(p)
}

// CreateRefreshToken creates a refresh token and returns it with its token family; an
// empty tokenFamily generates a new family id.
func (s *JWTService) CreateRefreshToken(userID, tokenFamily string, tokenVersion int) (string, string, error) {
	return s.createRefreshToken(userID, tokenFamily, int64(tokenVersion))
}

// createRefreshToken takes the raw claim values (refresh_access_token passes whatever the
// old token carried).
func (s *JWTService) createRefreshToken(sub, family any, version any) (string, string, error) {
	now := s.now()
	if !value_objects.PyTruthy(family) {
		family = s.TokenHex(16)
	}
	p := s.claims(
		"sub", sub, "type", "refresh", "family", family, "version", version,
		"iat", intDate(now), "exp", intDate(now.Add(RefreshTokenExpireDays*24*time.Hour)),
		"iss", s.Issuer, "jti", s.TokenHex(16),
	)
	tok, err := s.encode(p)
	return tok, value_objects.PyStr(family), err
}

// CreateResetToken creates a password reset token.
func (s *JWTService) CreateResetToken(userID, email string) (string, error) {
	now := s.now()
	return s.encode(s.claims(
		"sub", userID, "email", email, "type", "reset",
		"iat", intDate(now), "exp", intDate(now.Add(ResetTokenExpireHours*time.Hour)),
		"iss", s.Issuer, "jti", s.TokenHex(16),
	))
}

// GenerateToken generates an API token with scopes and an expiry in days.
func (s *JWTService) GenerateToken(userID string, scopes []string, expiresInDays int, tokenID, audience string) (string, error) {
	now := s.now()
	if scopes == nil {
		scopes = []string{}
	}
	return s.encode(s.claims(
		"sub", userID, "scopes", scopes, "type", "api_token", "aud", audience,
		"iat", intDate(now), "exp", intDate(now.Add(time.Duration(expiresInDays)*24*time.Hour)),
		"iss", s.Issuer, "jti", tokenID,
	))
}

// decodeJSONObject decodes a JSON object; integers stay int64, other numbers float64.
func decodeJSONObject(b []byte) (map[string]any, error) {
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.UseNumber()
	var v any
	if err := dec.Decode(&v); err != nil {
		return nil, err
	}
	if dec.More() {
		return nil, errors.New("Extra data")
	}
	m, ok := convertNumbers(v).(map[string]any)
	if !ok {
		return nil, errors.New("must be a json object")
	}
	return m, nil
}

func convertNumbers(v any) any {
	switch x := v.(type) {
	case json.Number:
		if i, err := x.Int64(); err == nil {
			return i
		}
		f, _ := x.Float64()
		return f
	case []any:
		for i := range x {
			x[i] = convertNumbers(x[i])
		}
	case map[string]any:
		for k := range x {
			x[k] = convertNumbers(x[k])
		}
	}
	return v
}

// loadToken is jws._load: three segments, JSON-object header, decoded payload and signature.
func loadToken(token string) (payload, signingInput []byte, header map[string]any, signature []byte, err error) {
	raw := []byte(token)
	i := bytes.LastIndexByte(raw, '.')
	if i < 0 {
		return nil, nil, nil, nil, errors.New("Not enough segments")
	}
	signingInput, cryptoSeg := raw[:i], raw[i+1:]
	j := bytes.IndexByte(signingInput, '.')
	if j < 0 {
		return nil, nil, nil, nil, errors.New("Not enough segments")
	}
	headerSeg, payloadSeg := signingInput[:j], signingInput[j+1:]
	headerData, err := b64urlDecode(headerSeg)
	if err != nil {
		return nil, nil, nil, nil, err
	}
	if header, err = decodeJSONObject(headerData); err != nil {
		return nil, nil, nil, nil, err
	}
	if b64, ok := header["b64"].(bool); ok && !b64 {
		return nil, nil, nil, nil, errors.New("Invalid header string: b64 must be true")
	}
	if payload, err = b64urlDecode(payloadSeg); err != nil {
		return nil, nil, nil, nil, err
	}
	if signature, err = b64urlDecode(cryptoSeg); err != nil {
		return nil, nil, nil, nil, err
	}
	return payload, signingInput, header, signature, nil
}

// pyIntClaim is int(value) for a claim: numbers truncate, bool is 0/1, strings use
// int(str); anything else (and NaN / infinity) fails.
func pyIntClaim(v any) (float64, bool) {
	switch x := v.(type) {
	case int64:
		return float64(x), true
	case float64:
		if math.IsNaN(x) || math.IsInf(x, 0) {
			return 0, false
		}
		return math.Trunc(x), true
	case bool:
		if x {
			return 1, true
		}
		return 0, true
	case string:
		n, ok := value_objects.PyParseInt(x)
		if !ok {
			return 0, false
		}
		f, _ := new(big.Float).SetInt(n).Float64()
		return f, true
	}
	return 0, false
}

// validateClaims is PyJWT's claim validation with verify_iss off (no issuer is
// requested): iat / nbf / exp when present, sub and jti must be strings, and the
// audience when one is expected.
func (s *JWTService) validateClaims(payload map[string]any, audience string) error {
	now := float64(s.now().UnixMicro()) / 1e6
	if v, ok := payload["iat"]; ok {
		iat, ok := pyIntClaim(v)
		if !ok {
			return errors.New("Issued At claim (iat) must be an integer.")
		}
		if iat > now {
			return errors.New("The token is not yet valid (iat)")
		}
	}
	if v, ok := payload["nbf"]; ok {
		nbf, ok := pyIntClaim(v)
		if !ok {
			return errors.New("Not Before claim (nbf) must be an integer.")
		}
		if nbf > now {
			return errors.New("The token is not yet valid (nbf)")
		}
	}
	if v, ok := payload["exp"]; ok {
		exp, ok := pyIntClaim(v)
		if !ok {
			return errors.New("Expiration Time claim (exp) must be an integer.")
		}
		if exp <= now {
			return errors.New("Signature has expired")
		}
	}
	if audience != "" {
		aud, present := payload["aud"]
		if !present || !value_objects.PyTruthy(aud) {
			return errors.New("Token is missing the \"aud\" claim")
		}
		var claims []string
		switch a := aud.(type) {
		case string:
			claims = []string{a}
		case []any:
			for _, e := range a {
				str, ok := e.(string)
				if !ok {
					return errors.New("Invalid claim format in token")
				}
				claims = append(claims, str)
			}
		default:
			return errors.New("Invalid claim format in token")
		}
		matched := false
		for _, c := range claims {
			if c == audience {
				matched = true
			}
		}
		if !matched {
			return errors.New("Audience doesn't match")
		}
	}
	if v, ok := payload["sub"]; ok {
		if _, isStr := v.(string); !isStr {
			return errors.New("Subject must be a string")
		}
	}
	if v, ok := payload["jti"]; ok {
		if _, isStr := v.(string); !isStr {
			return errors.New("JWT ID must be a string")
		}
	}
	return nil
}

// decode verifies the signature and claims. Python first tries with the issuer and then
// without it, so a token is accepted exactly when the issuer-less decode succeeds.
func (s *JWTService) decode(token, expectedAudience string) (map[string]any, error) {
	payloadBytes, signingInput, header, signature, err := loadToken(token)
	if err != nil {
		return nil, err
	}
	if alg, _ := header["alg"].(string); alg != JWTAlgorithm {
		return nil, errors.New("The specified alg value is not allowed")
	}
	key, err := s.hmacKey()
	if err != nil {
		return nil, err
	}
	mac := hmac.New(sha256.New, key)
	mac.Write(signingInput)
	if !hmac.Equal(mac.Sum(nil), signature) {
		return nil, errors.New("Signature verification failed")
	}
	payload, err := decodeJSONObject(payloadBytes)
	if err != nil {
		return nil, err
	}
	if err := s.validateClaims(payload, expectedAudience); err != nil {
		return nil, err
	}
	return payload, nil
}

// VerifyToken verifies and decodes a token; nil when invalid, expired, of the wrong
// type or (when expectedAudience is non-empty) for the wrong audience. An api_token is
// accepted as an access token and vice versa, and a token without a type is accepted.
func (s *JWTService) VerifyToken(token, expectedType, expectedAudience string) map[string]any {
	payload, err := s.decode(token, expectedAudience)
	if err != nil || len(payload) == 0 {
		return nil
	}
	tokenType, hasType := payload["type"]
	if tokenType != any(expectedType) {
		switch {
		case expectedType == "access" && tokenType == any("api_token"):
		case expectedType == "api_token" && tokenType == any("access"):
		case !hasType || tokenType == nil:
		default:
			return nil
		}
	}
	return payload
}

func (s *JWTService) VerifyAccessToken(token, expectedAudience string) map[string]any {
	return s.VerifyToken(token, "access", expectedAudience)
}

func (s *JWTService) VerifyRefreshToken(token string) map[string]any {
	return s.VerifyToken(token, "refresh", "")
}

func (s *JWTService) VerifyResetToken(token string) map[string]any {
	return s.VerifyToken(token, "reset", "")
}

// RefreshAccessToken exchanges a valid refresh token for a new access token and a new
// refresh token with the version incremented; ok is false for an invalid token. A
// non-numeric version claim raises TypeError in Python and is an error here.
func (s *JWTService) RefreshAccessToken(refreshToken string) (access, refresh string, ok bool, err error) {
	payload := s.VerifyRefreshToken(refreshToken)
	if len(payload) == 0 {
		return "", "", false, nil
	}
	sub := payload["sub"]
	family := payload["family"]
	var version any = int64(0)
	if v, present := payload["version"]; present {
		version = v
	}
	var next any
	switch v := version.(type) {
	case int64:
		next = v + 1
	case float64:
		next = v + 1
	case bool:
		if v {
			next = int64(2)
		} else {
			next = int64(1)
		}
	default:
		return "", "", false, &value_objects.TypeError{Msg: "unsupported operand type(s) for +: version and 'int'"}
	}

	now := s.now()
	access, err = s.encode(s.claims(
		"sub", sub, "type", "access", "iat", intDate(now),
		"exp", intDate(now.Add(AccessTokenExpireMinutes*time.Minute)),
		"iss", s.Issuer, "jti", s.TokenHex(16),
	))
	if err != nil {
		return "", "", false, err
	}
	refresh, _, err = s.createRefreshToken(sub, family, next)
	if err != nil {
		return "", "", false, err
	}
	return access, refresh, true, nil
}

// ExtractTokenFromHeader returns the token of a "Bearer <token>" header.
func (s *JWTService) ExtractTokenFromHeader(authorizationHeader string) (string, bool) {
	if authorizationHeader == "" {
		return "", false
	}
	parts := value_objects.PySplit(authorizationHeader)
	if len(parts) != 2 || value_objects.PyLower(parts[0]) != "bearer" {
		return "", false
	}
	return parts[1], true
}

// GetTokenExpiry decodes the token without verification and returns its expiry.
func (s *JWTService) GetTokenExpiry(token string) (time.Time, bool) {
	payloadBytes, _, _, _, err := loadToken(token)
	if err != nil {
		return time.Time{}, false
	}
	payload, err := decodeJSONObject(payloadBytes)
	if err != nil {
		return time.Time{}, false
	}
	exp := payload["exp"]
	if !value_objects.PyTruthy(exp) {
		return time.Time{}, false
	}
	var secs float64
	switch v := exp.(type) {
	case int64:
		secs = float64(v)
	case float64:
		secs = v
	case bool:
		secs = 1
	default:
		return time.Time{}, false
	}
	// datetime.fromtimestamp is limited to years 1..9999.
	if math.IsNaN(secs) || secs < -62135596800 || secs >= 253402300800 {
		return time.Time{}, false
	}
	whole, frac := math.Modf(secs)
	us := math.RoundToEven(frac * 1e6)
	return time.Unix(int64(whole), int64(us)*1000).UTC(), true
}

// IsTokenExpired: no readable expiry counts as expired.
func (s *JWTService) IsTokenExpired(token string) bool {
	expiry, ok := s.GetTokenExpiry(token)
	if !ok {
		return true
	}
	return s.now().After(expiry)
}
