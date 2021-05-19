from tahoe.identity import User, Org
from tahoe.identity.config import WebSocketConfig
from loadconfig import get_identity_backend

_ID_B = get_identity_backend()

Org._backend = _ID_B
User._backend = _ID_b
WebSocketConfig._backend = _ID_B

u = _ID_B.find_user(email='jthom@unr.edu')
o = Org('unr_honeypot', u, u, 'UNR Honeypot') 

WebSocketConfig(
        "UNR Cowrie Amsterdam",
        "cowrie",
        o._hash,
        "US/Pacific",
        "ws://134.122.58.51:5000/"
    )

WebSocketConfig(
        "UNR Cowrie Bangalore",
        "cowrie",
        o._hash,
        "US/Pacific",
        "ws://165.22.222.1:5000/"
    )

WebSocketConfig(
        "UNR Cowrie London",
        "cowrie",
        o._hash,
        "US/Pacific",
        "ws://198.211.116.240:5000/"
    )

WebSocketConfig(
        "UNR Cowrie Singapore",
        "cowrie",
        o._hash,
        "US/Pacific",
        "ws://128.199.70.240:5000/"
    )


WebSocketConfig(
        "UNR Cowrie Toronto",
        "cowrie",
        o._hash,
        "US/Pacific",
        "ws://165.227.95.133:5000/"
    )








