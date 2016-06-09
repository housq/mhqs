from twisted.internet.protocol import Protocol, ClientFactory
from twisted.web.http import HTTPFactory
from twisted.web.proxy import ProxyRequest, Proxy


class TunnelProtocol(Protocol):
    def __init__(self, request):
        self._request = request
        self._channel = request.channel
        self._peertransport = request.channel.transport

    def connectionMade(self):
        self._channel._openTunnel(self)
        self._request.setResponseCode(200, 'Connection established')
        self._request.write('')

    def dataReceived(self, data):
        self._peertransport.write(data)

    def connectionLost(self, reason):
        self._request.finish()
        self._channel._closeTunnel()


class TunnelProtocolFactory(ClientFactory):
    protocol = TunnelProtocol

    def __init__(self, request):
        self._request = request

    def buildProtocol(self, addr):
        p = self.protocol(self._request)
        p.factory = self
        return p

    def clientConnectionFailed(self, connector, reason):
        self._request.setResponseCode(502, 'Bad Gateway')
        self._request.finish()


class InjectionProxyRequest(ProxyRequest):
    def process(self):
        for subdomain in ('goshawk', 'goshawk4g', 'corsair', 'skyhawk', 'viper', 'crusader'):
            self.uri = self.uri.replace(subdomain + '.capcom.co.jp', 'localhost:8081')
        if self.uri.find('localhost:8081') == -1 and self.uri.find('conntest.nintendowifi.net') == -1 :
            print "illegal url"
            ProxyRequest.setResponseCode(self,400,'Bad Request')
            ProxyRequest.finish(self)
        else:
            ProxyRequest.process(self)


class TunnelProxyRequest(InjectionProxyRequest):
    def process(self):
        if self.method == 'CONNECT':
            self._processConnect()
        else:
            InjectionProxyRequest.process(self)

    def _processConnect(self):
        try:
            host, portStr = self.uri.split(':', 1)
            port = int(portStr)
        except ValueError:
            self.setResponseCode(400, 'Bad Request')
            self.finish()
        else:
            if (host.find('nasc.nintendowifi.net') and port == 443) or (host.find('goshawk.capcom.co.jp') and port == 443):
            	self.reactor.connectTCP(host, port, TunnelProtocolFactory(self))
            else:
                self.setResponseCode(400, 'Bad Request')
                self.finish()


class InjectionProxy(Proxy):
    requestFactory = InjectionProxyRequest


class TunnelProxy(Proxy):
    requestFactory = TunnelProxyRequest

    def __init__(self):
        self._tunnel = None
        Proxy.__init__(self)

    def _openTunnel(self, tunnel):
        self._tunnel = tunnel

    def _closeTunnel(self):
        self._tunnel = None

    def dataReceived(self, data):
        if self._tunnel:
            self._tunnel.transport.write(data)
        else:
            Proxy.dataReceived(self, data)

    def connectionLost(self, reason):
        if self._tunnel:
            self._tunnel.transport.loseConnection()


class InjectionProxyFactory(HTTPFactory):
    protocol = InjectionProxy


class TunnelProxyFactory(HTTPFactory):
    protocol = TunnelProxy

