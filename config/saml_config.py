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
TOWER_ENTITY_ID = f"{TOWER_BASE_URL}/metadata"
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
        'x509cert': ''  # REQUIRED: Will be populated from metadata URL
    }
}

# SAML Attribute Mappings (from Azure AD claims)
SAML_ATTR_EMAIL = 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'
SAML_ATTR_NAME = 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name'
SAML_ATTR_GIVEN_NAME = 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname'
SAML_ATTR_SURNAME = 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname'
SAML_ATTR_GROUPS = 'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups'

# Azure AD Group for Access Control
# TODO: Replace with actual Group Object ID from Azure Portal → Groups → insideAccess
INSIDE_ACCESS_GROUP_ID = "REPLACE_WITH_ACTUAL_GROUP_OBJECT_ID"

# MFA Challenge Settings
MFA_CHALLENGE_TIMEOUT_MINUTES = 5
MFA_TOKEN_LENGTH = 32  # bytes for urlsafe token
