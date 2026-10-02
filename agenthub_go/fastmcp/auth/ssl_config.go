package auth

import (
	"os"
	"regexp"
)

// selfHostedIPPattern is re.search(r"\d+\.\d+\.\d+\.\d+", url): an IPv4-looking
// substring anywhere in the URL.
var selfHostedIPPattern = regexp.MustCompile(`\d+\.\d+\.\d+\.\d+`)

// ConfigureSSLForSelfHosted mirrors configure_ssl_for_self_hosted. It reads
// SUPABASE_URL, detects an IP address in it, and sets the same environment
// variables. The Python override of ssl._create_default_https_context and the
// urllib3 warning suppression have no Go equivalent and are not ported.
func ConfigureSSLForSelfHosted() bool {
	supabaseURL := os.Getenv("SUPABASE_URL")

	isSelfHosted := selfHostedIPPattern.MatchString(supabaseURL)

	if isSelfHosted {
		os.Setenv("HTTPX_SSL_VERIFY", "0")
		os.Setenv("CURL_CA_BUNDLE", "")
		os.Setenv("REQUESTS_CA_BUNDLE", "")
		os.Setenv("SSL_CERT_FILE", "")
		os.Setenv("SSL_CERT_DIR", "")
		return true
	}

	return false
}

// ISSelfHosted is IS_SELF_HOSTED, computed at module import.
var ISSelfHosted = ConfigureSSLForSelfHosted()
