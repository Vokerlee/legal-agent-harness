#!/usr/bin/env python3
import html, json, sys, uuid
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from legal_agent_harness.validation_app import extract_graph, review_record, append_review, publish_hf, render_form
def parse_form(content_type, body):
 msg=BytesParser(policy=HTTP).parsebytes(b'Content-Type: '+content_type.encode('latin-1')+b'\r\n\r\n'+body)
 fields,files={},{}
 if not msg.is_multipart(): return fields,files
 for part in msg.iter_parts():
  name=part.get_param('name',header='content-disposition')
  if name is None: continue
  data=part.get_payload(decode=True) or b''
  if part.get_filename() is not None: files[name]=(part.get_filename(),data)
  elif data: fields.setdefault(name,data.decode('utf-8','replace'))
 return fields,files
class Handler(BaseHTTPRequestHandler):
 def do_GET(self): self._send(render_form())
 def do_POST(self):
  body=self.rfile.read(int(self.headers.get('Content-Length') or 0))
  form,files=parse_form(self.headers.get('Content-Type',''),body)
  filename,data=files['document']
  if len(data)>20*1024*1024: return self._send(render_form(message='Файл больше 20 МБ'),400)
  try:
   g=extract_graph(filename,data,form.get('authority','не указан'),form.get('jurisdiction','RU'))
   r=review_record(g,int(form.get('score','0')),form.get('comments',''),'review-'+uuid.uuid4().hex[:12])
   append_review('validation/reviews.jsonl',r)
   ok,msg=publish_hf(r,form.get('hf_token',''))
   return self._send(render_form(g,msg))
  except Exception as e: return self._send(render_form(message='Ошибка обработки: '+html.escape(type(e).__name__)),400)
 def _send(self, body, status=200):
  b=body.encode(); self.send_response(status); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
if __name__=='__main__':
 p=int(sys.argv[1]) if len(sys.argv)>1 else 8000; print('Откройте http://127.0.0.1:%d'%p); HTTPServer(('127.0.0.1',p),Handler).serve_forever()
