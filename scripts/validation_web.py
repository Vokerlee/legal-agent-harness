#!/usr/bin/env python3
import cgi, html, json, sys, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from legal_agent_harness.validation_app import extract_graph, review_record, append_review, publish_hf, render_form
class Handler(BaseHTTPRequestHandler):
 def do_GET(self): self._send(render_form())
 def do_POST(self):
  form=cgi.FieldStorage(fp=self.rfile,headers=self.headers,environ={'REQUEST_METHOD':'POST','CONTENT_TYPE':self.headers.get('Content-Type',''),'CONTENT_LENGTH':self.headers.get('Content-Length','')})
  f=form['document']; data=f.file.read()
  if len(data)>20*1024*1024: return self._send(render_form(message='Файл больше 20 МБ'),400)
  try:
   g=extract_graph(f.filename,data,form.getfirst('authority','не указан'),form.getfirst('jurisdiction','RU'))
   r=review_record(g,int(form.getfirst('score','0')),form.getfirst('comments',''),'review-'+uuid.uuid4().hex[:12])
   append_review('validation/reviews.jsonl',r)
   ok,msg=publish_hf(r,form.getfirst('hf_token',''))
   return self._send(render_form(g,msg))
  except Exception as e: return self._send(render_form(message='Ошибка обработки: '+html.escape(type(e).__name__)),400)
 def _send(self, body, status=200):
  b=body.encode(); self.send_response(status); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
if __name__=='__main__':
 p=int(sys.argv[1]) if len(sys.argv)>1 else 8000; print('Откройте http://127.0.0.1:%d'%p); HTTPServer(('127.0.0.1',p),Handler).serve_forever()
