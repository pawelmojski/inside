"""
SAML Configuration for Azure AD Integration
Tower URL: https://inside.ideo.pl
"""

# Azure AD SAML Endpoints
AZURE_TENANT_ID = "0d9653a4-4c3f-4752-9098-724fad471fa5"
AZURE_APP_ID = "05275222-1909-4d40-a0d0-2c41df7b512a"

AZURE_SAML_LOGIN_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/saml2"
AZURE_SAML_LOGOUT_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/saml2"
AZURE_ENTITY_ID = f"https://sts.windows.net/{AZURE_TENANT_ID}/"
AZURE_METADATA_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/federationmetadata/2007-06/federationmetadata.xml?appid={AZURE_APP_ID}"

# Tower SAML Configuration
TOWER_BASE_URL = "https://inside.ideo.pl"
TOWER_ENTITY_ID = f"inside.ideo.pl"
TOWER_ACS_URL = f"{TOWER_BASE_URL}/auth/saml/acs"
TOWER_SLS_URL = f"{TOWER_BASE_URL}/auth/saml/sls"
TOWER_METADATA_URL = f"{TOWER_BASE_URL}/auth/saml/metadata"

# python3-saml settings dictionary
SAML_SETTINGS = {
    'strict': True,
    'debug': False,
    
    # Service Provider (Tower)
    'sp': {
        'entityId': TOWER_ENTITY_ID,
        'assertionConsumerService': {
            'url': TOWER_ACS_URL,
            'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
        },
        'singleLogoutService': {
            'url': TOWER_SLS_URL,
            'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
        },
        'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
        'x509cert': '',  # Optional: Tower certificate for signing requests
        'privateKey': ''  # Optional: Tower private key
    },
    
    # Identity Provider (Azure AD)
    'idp': {
        'entityId': AZURE_ENTITY_ID,
        'singleSignOnService': {
            'url': AZURE_SAML_LOGIN_URL,
            'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
        },
        'singleLogoutService': {
            'url': AZURE_SAML_LOGOUT_URL,
            'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
        },
        'x509cert': 'MIIC8DCCAdigAwIBAgIQQ7aAc5D3AJhHUpFjIEe/ZDANBgkqhkiG9w0BAQsFADA0MTIwMAYDVQQDEylNaWNyb3NvZnQgQXp1cmUgRmVkZXJhdGVkIFNTTyBDZXJ0aWZpY2F0ZTAeFw0yNjAxMjcxMTI0MDNaFw0yOTAxMjcxMTI0MDNaMDQxMjAwBgNVBAMTKU1pY3Jvc29mdCBBenVyZSBGZWRlcmF0ZWQgU1NPIENlcnRpZmljYXRlMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtRf/yr17OQzPBBPfstMEfcQRcU3wOdHo4to6IOwQh4nFueIrYntxc5ROKMQKHkFbOuYXGec9NY0mmdv8/RKrodi0owC4c85UvDXe4N3e1Gvol3QF+Yg95pCzmpIbjW1+dLs5/iXkKHK5K0gC29K5HRTdwa3NtJrtwmDg7shQB0IzgLuhGKsR7Djolpg+9tZ6gNElhSYQOvEbXLPxOBCM3i31k02r1wBRv/u+q1neTNzSdOhB/7LjR8A+UOd+oGsw+O+o6g6ST4oTKw42VjgZhXBXT5CB9ej0xxLszn9ONR7CscVSjSvfgoJvS45iaE0r9qMgurvcmMsw07wB1Xu4UQIDAQABMA0GCSqGSIb3DQEBCwUAA4IBAQCR9SJfyroNQ0scvQUp9pWyvvN3tCkmcnuffJHU0km8IWETPMgzWSSnUYREnqV2VV3W/qNTQV1wUXpyRvcP8dRkKDjWojcKPpeyrk/FwuwHDAHzBhsEtKIJTzAMiCGdSoefltPOwb3hrPbwa8maoKutS8iwhoHbvaaySIKOlIvVxOEJQZzFPDioDP4cn48l8ccx9yUnSOI9ecGzojPZszif3D1nLOsW01HhBcSaHqTcjOUTNU/7uHwmHny9CbBuDUAurgdqP7wufG+8ohOkQj6ccsIHhLeoctBjZYIUB6pkmQ4JB24nmRLxtmTqbx/DWj0RyLTC9tbAD7hN6MVjVNcu'
    }
}

# SAML Attribute Mappings (from Azure AD claims)
SAML_ATTR_EMAIL = 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'
SAML_ATTR_NAME = 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name'
SAML_ATTR_GIVEN_NAME = 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname'
SAML_ATTR_SURNAME = 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname'
SAML_ATTR_GROUPS = 'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups'

# Azure AD Group for Access Control
# DISABLED: No group check - verify user exists in Inside users table instead
INSIDE_ACCESS_GROUP_ID = None  # Not used - all authenticated users checked against users table

# MFA Challenge Settings
MFA_CHALLENGE_TIMEOUT_MINUTES = 5
MFA_TOKEN_LENGTH = 32  # bytes for urlsafe token
