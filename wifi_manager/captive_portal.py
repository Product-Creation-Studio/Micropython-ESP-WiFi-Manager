import network
import socket
import uasyncio as asyncio
from .wifi_manager import WifiManager
from microdot_asyncio import Response, render_template, redirect

DOMAIN = None
LOGGER = None


# microsoft windows redirects
# /ncsi.txt
def _ncsi_txt(request):
    LOGGER.info("AP ncsi.txt request received")
    return "", 200


# /connecttest.txt
def _connecttest_txt(request):
    LOGGER.info("AP connecttest.txt request received")
    return "", 200


# /redirect
def _redirect(request):
    LOGGER.info("AP redirect request received")
    return redirect(f"http://{DOMAIN}/", 302)


# android redirects
# /generate_204
def _generate_204(request):
    LOGGER.info("AP generate_204 request received")
    return redirect(f"http://{DOMAIN}/", 302)


# apple redir
# /hotspot-detect.html
def _hotspot_detect(request):
    LOGGER.info("AP hotspot-detect.html request received")
    # return render_template('guestbook.html')
    return redirect(f"http://{DOMAIN}/", 302)


def _install_captive_portal_routes(wm: WifiManager):
    wm.add_url_rule(url="/ncsi.txt", func=_ncsi_txt)
    wm.add_url_rule(url="/connecttest.txt", func=_connecttest_txt)
    wm.add_url_rule(url="/redirect", func=_redirect)
    wm.add_url_rule(url="/generate_204", func=_generate_204)
    wm.add_url_rule(url="/hotspot-detect.html", func=_hotspot_detect)


async def captive_portal(wm: WifiManager):
    _install_captive_portal_routes(wm)
    global DOMAIN, LOGGER
    ap = network.WLAN(network.AP_IF)
    myip = ap.ifconfig()[0]
    DOMAIN = myip
    LOGGER = wm.logger
    myip_bytes = bytes([int(x) for x in myip.split(".")])
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setblocking(False)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(socket.getaddrinfo(myip, 53)[0][-1])
    while True:
        yield asyncio.IORead(s)
        packet, addr = s.recvfrom(256)
        # verify query, opcode 0, one question
        if (
            packet[2] & 0xF0 == 0x00    # query + opcode 0
            and packet[4:6] == b"\x00\x01"  # one question
        ):
            packet_len = len(packet)
            response = bytearray(packet_len + 16)
            # change request into a response and append the answer
            response[:packet_len] = packet
            response[2] |= 0x80  # change from query to response
            response[3] = 0  # recursion not available and responsecode stays 0
            response[7] = 1  # number of answers
            # add 16 bytes of answer
            response[packet_len:packet_len+2] = b"\xc0\x0c"  # point back to question
            response[packet_len+2:packet_len+4] = b"\x00\x01"  # A entry
            response[packet_len+4:packet_len+6] = b"\x00\x01"  # class IN
            response[packet_len+6:packet_len+10] = b"\x00\x00\x00\x00"  # TTL 0
            response[packet_len+10:packet_len+12] = b"\x00\x04"  # length of address
            response[packet_len+12:packet_len+16] = myip_bytes  # address
            s.sendto(response, addr)
