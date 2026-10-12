#!/usr/bin/env python3
"""Local-only static preview; never sends form data or publishes code.
Run: python preview.py --port 8767
Open: http://127.0.0.1:8767
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
import argparse, webbrowser
ROOT=Path(__file__).resolve().parent/'site'
PAGES={'/':'index.html','/commercial-industrial':'commercial-industrial.html','/residential-construction':'residential-construction.html','/south-fulton-distribution':'south-fulton-distribution.html','/accessibility':'accessibility.html','/404':'404.html'}
REDIRECTS={'/index.html':'/',**{p+'.html':p for p in PAGES if p not in ('/','/404')},'/home-repair':'/residential-construction#home-repair','/home-repair.html':'/residential-construction#home-repair'}
class PreviewHandler(SimpleHTTPRequestHandler):
    def log_message(self,fmt,*args):pass
    def end_headers(self):
        for key,val in {'X-Robots-Tag':'noindex, nofollow','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin','X-Frame-Options':'DENY'}.items():self.send_header(key,val)
        super().end_headers()
    def do_POST(self):
        data=b'Preview only. No request was sent. Use your browser Back button to return.'
        self.send_response(405);self.send_header('Content-Type','text/plain; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):self._serve(False)
    def do_HEAD(self):self._serve(True)
    def _serve(self,head):
        url=urlsplit(self.path);path=unquote(url.path)
        if path in REDIRECTS:
            main,sep,anchor=REDIRECTS[path].partition('#')
            location=main+('?' + url.query if url.query else '')+('#'+anchor if sep else '')
            self.send_response(301);self.send_header('Location',location);self.send_header('Content-Length','0');self.end_headers();return
        status=200;name=PAGES.get(path)
        if name:
            p=ROOT/name
            if path=='/404':status=404
        else:
            p=ROOT/path.lstrip('/')
            if not p.resolve().is_relative_to(ROOT.resolve()) or p.is_symlink() or not p.is_file() or p.suffix not in {'.webp','.png','.js','.txt'}:
                p=ROOT/'404.html';status=404
        data=p.read_bytes();self.send_response(status)
        self.send_header('Content-Type',self.guess_type(str(p))+('; charset=utf-8' if p.suffix in {'.html','.txt','.js'} else ''))
        self.send_header('Content-Length',str(len(data)));self.end_headers()
        if not head:self.wfile.write(data)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--port',type=int,default=8767);ap.add_argument('--open',action='store_true',dest='open_browser');args=ap.parse_args()
    with ThreadingHTTPServer(('127.0.0.1',args.port),PreviewHandler) as server:
        print(f'Big 7 preview: http://127.0.0.1:{args.port} (local only; submissions disabled)',flush=True)
        if args.open_browser:webbrowser.open(f'http://127.0.0.1:{args.port}')
        try:server.serve_forever()
        except KeyboardInterrupt:pass
if __name__=='__main__':main()
