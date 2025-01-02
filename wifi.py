import network

SSID = 'BT-69CPT3-LEGACY'
KEY = 'CFXTPYLWMM'

def connect_to_wifi():
    """Connect to a defined wireless network."""
    wlan = network.WLAN(network.WLAN.IF_STA)
    wlan.active(True)

    if not wlan.isconnected():
        print(f'WiFi --> Connecting to {SSID}...')

        wlan.connect(SSID, KEY)
        while not wlan.isconnected():
            pass

    print(f'WiFi --> Connected to {SSID} - IPv4 {wlan.ipconfig('addr4')[0]}')
    return wlan