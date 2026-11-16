import os, re, secrets, socket, ipaddress, tempfile, shutil
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import yt_dlp

app=FastAPI(title="VideoCep API")
KEY=os.environ.get("VIDEOCEP_API_KEY","")
if not KEY: raise RuntimeError("VIDEOCEP_API_KEY environment variable is required")
origins=[x.strip() for x in os.environ.get("ALLOWED_ORIGINS","*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=["GET","POST","OPTIONS"],allow_headers=["Content-Type","X-API-Key"])
ALLOWED={"youtube.com","youtu.be","youtube-nocookie.com","instagram.com","instagr.am","tiktok.com"}
class Link(BaseModel): url: HttpUrl
class Download(Link): format_id: str
def auth(k):
 if not k or not secrets.compare_digest(k,KEY): raise HTTPException(401,"API anahtarı geçersiz.")
def validate(raw):
 p=urlparse(raw); host=(p.hostname or "").lower().rstrip(".")
 if p.scheme!="https" or not any(host==d or host.endswith("."+d) for d in ALLOWED): raise HTTPException(400,"Desteklenmeyen bağlantı.")
 try:
  for x in socket.getaddrinfo(host,None):
   if not ipaddress.ip_address(x[4][0]).is_global: raise HTTPException(400,"Güvenli olmayan adres.")
 except socket.gaierror: raise HTTPException(400,"Alan adı bulunamadı.")
 return raw
def opts(): return {"quiet":True,"no_warnings":True,"noplaylist":True,"socket_timeout":20,"retries":2,"cachedir":False,"restrictfilenames":True}
@app.get("/")
def root(): return {"service":"VideoCep API","status":"ok"}
@app.post("/info")
def info(d:Link,x_api_key:str|None=Header(default=None)):
 auth(x_api_key); url=validate(str(d.url))
 try:
  with yt_dlp.YoutubeDL({**opts(),"skip_download":True}) as y: data=y.extract_info(url,download=False)
  found={}
  for f in data.get("formats",[]):
   h=f.get("height"); v=f.get("vcodec") not in (None,"none")
   if h and v:
    audio=f.get("acodec") not in (None,"none"); label=f"{h}p"+(" • sesli" if audio else " • video")+(" • "+f["ext"] if f.get("ext") else "")
    if h not in found or audio: found[h]={"format_id":str(f["format_id"]),"height":h,"label":label}
  return {"title":data.get("title","Video"),"formats":sorted(found.values(),key=lambda z:z["height"],reverse=True)}
 except Exception: raise HTTPException(422,"Video okunamadı; özel, silinmiş veya platformca kısıtlanmış olabilir.")
@app.post("/download")
def download(d:Download,x_api_key:str|None=Header(default=None)):
 auth(x_api_key); url=validate(str(d.url))
 if not re.fullmatch(r"[A-Za-z0-9_-]{1,30}",d.format_id): raise HTTPException(400,"Geçersiz format.")
 folder=tempfile.mkdtemp(prefix="vc_"); template=str(Path(folder)/"%(title).70B.%(ext)s")
 try:
  with yt_dlp.YoutubeDL({**opts(),"format":d.format_id,"outtmpl":template,"merge_output_format":"mp4","max_filesize":500*1024*1024}) as y: y.download([url])
  files=[p for p in Path(folder).iterdir() if p.is_file() and not p.name.endswith((".part",".ytdl"))]
  if not files: raise RuntimeError("No output")
  f=files[0]
  return FileResponse(f,filename=f.name,media_type="application/octet-stream",background=None)
 except Exception:
  shutil.rmtree(folder,ignore_errors=True); raise HTTPException(422,"İndirme başarısız; bu format veya platform desteklenmiyor olabilir.")
