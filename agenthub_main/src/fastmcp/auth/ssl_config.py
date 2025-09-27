"""
SSL Configuration for Self-Hosted Supabase

This module configures SSL settings for self-hosted Supabase instances
with self-signed certificates. It must be imported before any Supabase
or httpx clients are created.
"""

import os
import re
import ssl
import logging

logger = logging.getLogger(__name__)

def configure_ssl_for_self_hosted():
    """
    Configure SSL settings for self-hosted Supabase instances.
    
    This function detects if the Supabase URL points to a self-hosted
    instance (by checking for IP addresses) and disables SSL verification
    if needed.
    """
    supabase_url = os.getenv("SUPABASE_URL", "")
    
    # Check if this is a self-hosted instance (has IP address in URL)
    is_self_hosted = bool(re.search(r'\d+\.\d+\.\d+\.\d+', supabase_url))
    
    if is_self_hosted:
        logger.info(f"Detected self-hosted Supabase at: {supabase_url}")
        logger.info("Configuring SSL settings for self-signed certificates...")
        
        # Set environment variables to disable SSL verification
        os.environ["HTTPX_SSL_VERIFY"] = "0"
        os.environ["CURL_CA_BUNDLE"] = ""
        os.environ["REQUESTS_CA_BUNDLE"] = ""
        os.environ["SSL_CERT_FILE"] = ""
        os.environ["SSL_CERT_DIR"] = ""
        
        # Override the default SSL context
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
            logger.info("SSL verification disabled for self-hosted instance")
        except Exception as e:
            logger.warning(f"Could not override SSL context: {e}")
        
        # Disable urllib3 SSL warnings
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.info("SSL warnings suppressed")
        except ImportError:
            pass
        
        return True
    
    return False

# Run configuration on module import
IS_SELF_HOSTED = configure_ssl_for_self_hosted()