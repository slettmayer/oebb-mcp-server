"""Constants for the OeBB MCP server."""

OEBB_API_ENDPOINT = "https://fahrplan.oebb.at/bin/mgate.exe"
OEBB_API_TIMEOUT = 15
OEBB_AUTH_AID = "OWDL4fE4ixNiPBBm"
OEBB_CLIENT_ID = "OEBB"
OEBB_CLIENT_TYPE = "WEB"
OEBB_CLIENT_NAME = "webapp"
OEBB_CLIENT_L = "vs_webapp"
OEBB_API_VERSION = "1.67"
OEBB_API_LANG = "deu"

# All 16 bits set — includes all product classes, notably bit 12 (4096)
# for private operators like Westbahn and RegioJet.
OEBB_ALL_PRODUCTS = 65535
