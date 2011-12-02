import sys

from twisted.conch.telnet import TelnetProtocol, TelnetTransport
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol, ServerFactory
from twisted.python import log

# TERMINAL-TYPE option
TTYPE = chr(24)

# SEND payload
SEND = chr(1)

class Nyancat(ProcessProtocol):

    def __init__(self, terminal):
        # Select terminals. 1 is best, 4 is worst. We only do 4 on request; no
        # known terminal has a TERM of "fallback".
        if "xterm" in terminal:
            self.terminal = "1\n"
        elif "linux" in terminal:
            self.terminal = "3\n"
        elif "fallback" in terminal:
            self.terminal = "4\n"
        elif terminal.startswith("rxvt"):
            self.terminal = "3\n"
        else:
            self.terminal = "2\n"

    def connectionMade(self):
        self.transport.write(self.terminal)
        self.transport.closeStdin()

    def outReceived(self, data):
        self.parent.transport.write(data)

class NyancatTelnet(TelnetProtocol):

    cat = None
    term = "ansi"

    def enableRemote(self, option):
        return option == TTYPE

    def connectionMade(self):
        # Plan to receive information on terminal type. This isn't guaranteed
        # to happen, but we're gonna ask for it.
        self.transport.negotiationMap[TTYPE] = self.setTerm

        # Tell the client that we're okay with them telling us about terminal
        # types.
        self.transport.do(TTYPE)

        # And now actually instruct the client to tell us their terminal type.
        # Apparently just because you can *do* something doesn't mean you
        # *will* do it, in telnet-land.
        self.transport.requestNegotiation(TTYPE, SEND)

        # Give the client time to react, and also to make sure that the
        # terminal type is negotiated correctly.
        self.transport.write("Starting cat in 2 seconds...")
        reactor.callLater(2, self.spawnCat)

    def connectionLost(self, reason):
        if self.cat:
            self.cat.transport.signalProcess("KILL")
            # Explicitly break cycles early, so that the GC has less work to
            # do.
            del self.cat.parent
            del self.cat

    def setTerm(self, data):
        # The first byte is IS (0x00), so don't store it.
        self.term = "".join(data[1:])

    def spawnCat(self):
        self.cat = Nyancat(self.term)
        self.cat.parent = self
        reactor.spawnProcess(self.cat, "./nyancat")

class NyancatFactory(ServerFactory):
    protocol = lambda self: TelnetTransport(NyancatTelnet)

log.startLogging(sys.stdout)

reactor.listenTCP(2323, NyancatFactory())
reactor.run()
