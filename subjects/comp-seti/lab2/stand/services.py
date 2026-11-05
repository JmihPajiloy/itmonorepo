"""Real HTTP and FTP services in an isolated teaching network."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

root = Path('/lab/stand/www')
authorizer = DummyAuthorizer()
authorizer.add_anonymous(str(root), perm='elr')
FTPHandler.authorizer = authorizer
FTPHandler.passive_ports = range(30000, 30010)
Thread(target=ThreadingHTTPServer(('0.0.0.0', 8000),
       partial(SimpleHTTPRequestHandler, directory=str(root))).serve_forever,
       daemon=True).start()
FTPServer(('0.0.0.0', 21), FTPHandler).serve_forever()
