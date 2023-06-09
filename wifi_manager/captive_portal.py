import network
import socket
import uasyncio as asyncio
from microdot.microdot_asyncio import redirect

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


def _install_captive_portal_routes(wm):
    wm.add_url_rule(url="/ncsi.txt", func=_ncsi_txt)
    wm.add_url_rule(url="/connecttest.txt", func=_connecttest_txt)
    wm.add_url_rule(url="/redirect", func=_redirect)
    wm.add_url_rule(url="/generate_204", func=_generate_204)
    wm.add_url_rule(url="/hotspot-detect.html", func=_hotspot_detect)

async def async_recvfrom(sock, count):
    yield asyncio.core._io_queue.queue_read(sock)
    return sock.recvfrom(count)


async def captive_portal(wm):
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
        plen = 0
        try:
            packet, addr = await asyncio.wait_for(async_recvfrom(s, 256), 1)
            plen = len(packet)
        except asyncio.TimeoutError:
            continue

        # verify query, opcode 0, one question
        if (
            packet[2] & 0xF0 == 0x00 and  # query + opcode 0
            packet[4:6] == b"\x00\x01"  # one question
        ):
            response = bytearray(plen + 16)
            # change request into a response and append the answer
            response[:plen] = packet
            response[2] |= 0x80  # change from query to response
            response[3] = 0  # recursion not available and responsecode stays 0
            response[7] = 1  # number of answers
            # add 16 bytes of answer
            response[plen: plen + 2] = b"\xc0\x0c"  # point back to question
            response[plen + 2: plen + 4] = b"\x00\x01"  # A entry
            response[plen + 4: plen + 6] = b"\x00\x01"  # class IN
            response[plen + 6: plen + 10] = b"\x00\x00\x00\x00"  # TTL 0
            response[plen + 10: plen + 12] = b"\x00\x04"  # length of address
            response[plen + 12: plen + 16] = myip_bytes  # address
            s.sendto(response, addr)
