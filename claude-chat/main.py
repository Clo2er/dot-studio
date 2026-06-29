import os, json, base64, time, uuid, shutil, subprocess
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()
CLAUDE = shutil.which("claude") or "claude"
BASE_SYS = "你是一个有用的助手，请用简洁自然的方式回答。"
MODEL = "claude-opus-4-8"
SESS_FILE = "sessions.json"

def read_file(name):
    try:
        with open(name, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def build_system():
    s = BASE_SYS
    profile = read_file("profile.json") or read_file("profile.txt")
    history = read_file("history.json") or read_file("history.txt")
    if profile:
        s += "\n\n【关于用户的设定，请始终遵守】\n" + profile
    if history:
        s += "\n\n【用户过去的对话记录，供你了解背景】\n" + history
    return s

def save_image(data_url, name):
    os.makedirs("uploads", exist_ok=True)
    header, b64 = data_url.split(",", 1)
    ext = ".png"
    if "jpeg" in header or "jpg" in header: ext = ".jpg"
    elif "webp" in header: ext = ".webp"
    elif "gif" in header: ext = ".gif"
    path = os.path.abspath(os.path.join("uploads", str(int(time.time()*1000)) + ext))
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    return path

def load_store():
    try:
        with open(SESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"sessions": {}}

def save_store():
    with open(SESS_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

store = load_store()

PAGE = """<!doctype html><html lang="zh"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude · 通信档案</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{background:#FAF4E8;color:#3D2E1F;font-family:Georgia,'Times New Roman',serif;height:100vh;overflow:hidden}
#side{position:fixed;top:0;left:0;bottom:0;width:270px;background:#F5ECD7;border-right:2px solid #D4C5B0;
 transform:translateX(-100%);transition:transform .25s;z-index:20;display:flex;flex-direction:column;padding:18px 16px}
#side.open{transform:translateX(0);box-shadow:3px 0 20px rgba(90,70,48,.18)}
.side-h{font-size:10px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#8B7355;margin-bottom:14px;text-align:center}
#newbtn{width:100%;padding:11px;border:none;border-radius:7px;background:#8B4513;color:#F5ECD7;
 font-family:inherit;font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;cursor:pointer;margin-bottom:14px}
#list{flex:1;overflow-y:auto}
.sitem{display:flex;align-items:center;padding:10px 11px;border:1.5px solid transparent;border-radius:7px;cursor:pointer;font-size:13px;color:#5A4630;margin-bottom:5px}
.sitem:hover{background:#EDE3D0}.sitem.active{background:#FAF4E8;border-color:#D4C5B0}
.sitem .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.sitem .x{color:#A0522D;margin-left:8px;font-size:12px;opacity:.55}
#backdrop{position:fixed;inset:0;background:rgba(61,46,31,.28);z-index:15;display:none}
#backdrop.show{display:block}
#main{height:100vh;display:flex;flex-direction:column;align-items:center}
header{width:100%;background:#F5ECD7;border-bottom:2px solid #D4C5B0;padding:11px 16px 9px}
.hrow{display:flex;align-items:center;width:100%}
#menu{background:none;border:none;font-size:20px;cursor:pointer;color:#5A4630;font-family:inherit}
.brand{flex:1;display:flex;align-items:center;justify-content:center;gap:9px}
.dot{width:18px;height:18px;border-radius:50%;background:radial-gradient(circle,#C4956A 30%,#8B4513 100%);border:2px solid #D4C5B0}
.brand-t{font-size:14px;font-weight:700;letter-spacing:.24em;text-transform:uppercase;color:#5A4630}
.subt{text-align:center;font-size:8.5px;letter-spacing:.34em;color:#A89880;text-transform:uppercase;margin-top:6px}
#wrap{flex:1;width:100%;max-width:720px;overflow-y:auto;padding:20px 20px 10px}
.turn{margin:20px 0;display:flex;flex-direction:column}
.lbl{font-size:9px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#A89880;margin-bottom:5px}
.user{align-items:flex-end}
.user .bubble{background:#F5ECD7;border:1.5px solid #D4C5B0;border-radius:12px 12px 3px 12px;
 padding:12px 15px;max-width:82%;font-size:15px;line-height:1.65;color:#3D2E1F}
.bot{align-items:flex-start}
.bot .bubble{font-size:15px;line-height:1.8;white-space:pre-wrap;max-width:100%;color:#3D2E1F}
.thumb{max-width:220px;border-radius:8px;border:1.5px solid #D4C5B0;display:block;margin-bottom:8px}
.attag{font-size:11px;font-family:'Courier New',monospace;color:#8B7355;margin-bottom:6px;letter-spacing:.04em}
.cot{margin:0 0 10px 0;border:1.5px dashed #D4C5B0;border-radius:8px;background:#F5ECD7}
.cot summary{cursor:pointer;color:#8B4513;font-weight:700;letter-spacing:.12em;text-transform:uppercase;font-size:10px;padding:9px 12px}
.cotbody{white-space:pre-wrap;padding:0 12px 11px;line-height:1.6;font-family:'Courier New',monospace;font-size:12px;color:#6B5C4D}
#barwrap{width:100%;max-width:720px;padding:8px 18px 18px}
#chip{font-size:12px;font-family:'Courier New',monospace;color:#8B7355;margin:0 0 7px 2px;display:none}
#chip b{color:#8B4513}#chip span{cursor:pointer;color:#A0522D;margin-left:8px}
#bar{display:flex;gap:7px;align-items:flex-end;background:#F5ECD7;border:1.5px solid #D4C5B0;
 border-radius:14px;padding:9px 9px 9px 11px;box-shadow:0 2px 10px rgba(90,70,48,.08)}
.icon{flex:none;width:36px;height:36px;border:1.5px solid #D4C5B0;border-radius:8px;cursor:pointer;
 background:#FAF4E8;color:#6B5C4D;font-size:16px;display:flex;align-items:center;justify-content:center}
.icon.active{background:#8B4513;color:#F5ECD7;border-color:#8B4513}
#q{flex:1;border:none;outline:none;resize:none;font-family:Georgia,serif;font-size:15px;
 line-height:1.5;max-height:140px;background:transparent;color:#3D2E1F;padding:7px 4px}
#q::placeholder{color:#A89880}
#send{flex:none;width:38px;height:38px;border:none;border-radius:8px;cursor:pointer;
 background:#8B4513;color:#F5ECD7;font-size:17px;display:flex;align-items:center;justify-content:center}
#send:disabled{background:#C4B49A}
::-webkit-scrollbar{width:9px}::-webkit-scrollbar-thumb{background:#D4C5B0;border-radius:4px}
</style></head><body>
<div id="backdrop"></div>
<aside id="side"><div class="side-h">◆ 通信档案 ◆</div><button id="newbtn">+ 新建通信</button><div id="list"></div></aside>
<div id="main">
<header>
 <div class="hrow"><button id="menu">☰</button><div class="brand"><div class="dot"></div><span class="brand-t">Claude</span></div><span style="width:20px"></span></div>
 <div class="subt">✦&nbsp;&nbsp;私 人 通 信&nbsp;&nbsp;✦</div>
</header>
<div id="wrap"></div>
<div id="barwrap">
<div id="chip"></div>
<div id="bar">
<button class="icon" id="attach" title="上传附件/图片">📎</button>
<button class="icon" id="ext" title="深度思考">🧠</button>
<textarea id="q" rows="1" placeholder="提笔写信…"></textarea>
<button id="send">↑</button>
</div></div></div>
<input type="file" id="file" hidden>
<script>
const wrap=document.getElementById('wrap'),q=document.getElementById('q'),send=document.getElementById('send'),
 ext=document.getElementById('ext'),attach=document.getElementById('attach'),file=document.getElementById('file'),
 chip=document.getElementById('chip'),side=document.getElementById('side'),menu=document.getElementById('menu'),
 backdrop=document.getElementById('backdrop'),list=document.getElementById('list'),newbtn=document.getElementById('newbtn');
let extendOn=false, attached=null, curId=null;
function drawer(o){side.classList.toggle('open',o);backdrop.classList.toggle('show',o);}
menu.onclick=()=>drawer(!side.classList.contains('open'));
backdrop.onclick=()=>drawer(false);
q.addEventListener('input',()=>{q.style.height='auto';q.style.height=Math.min(q.scrollHeight,140)+'px';});
ext.onclick=()=>{extendOn=!extendOn;ext.classList.toggle('active',extendOn);};
attach.onclick=()=>file.click();
file.onchange=()=>{const f=file.files[0];if(!f)return;const rd=new FileReader();
 if(f.type.startsWith('image/')){rd.onload=()=>{attached={name:f.name,kind:'image',content:rd.result};showChip();};rd.readAsDataURL(f);}
 else{rd.onload=()=>{attached={name:f.name,kind:'text',content:rd.result};showChip();};rd.readAsText(f);}
 file.value='';};
function showChip(){if(!attached){chip.style.display='none';return;}chip.style.display='block';
 chip.innerHTML=(attached.kind==='image'?'🖼️':'📎')+' 已附加: <b>'+attached.name+'</b><span id="rm">✕</span>';
 document.getElementById('rm').onclick=()=>{attached=null;chip.style.display='none';};}
function addUser(text,att){const turn=document.createElement('div');turn.className='turn user';
 const l=document.createElement('div');l.className='lbl';l.textContent='你';turn.appendChild(l);
 const b=document.createElement('div');b.className='bubble';
 if(att&&att.kind==='image'){const im=document.createElement('img');im.src=att.content;im.className='thumb';b.appendChild(im);}
 if(att&&att.kind==='text'){const g=document.createElement('div');g.className='attag';g.textContent='📎 '+att.name;b.appendChild(g);}
 if(text){const tx=document.createElement('div');tx.textContent=text;b.appendChild(tx);}
 turn.appendChild(b);wrap.appendChild(turn);wrap.scrollTop=wrap.scrollHeight;}
function addBotStatic(text){const turn=document.createElement('div');turn.className='turn bot';
 const l=document.createElement('div');l.className='lbl';l.textContent='Claude';turn.appendChild(l);
 const b=document.createElement('div');b.className='bubble';b.textContent=text;turn.appendChild(b);
 wrap.appendChild(turn);wrap.scrollTop=wrap.scrollHeight;}
function addBot(){const turn=document.createElement('div');turn.className='turn bot';
 const l=document.createElement('div');l.className='lbl';l.textContent='Claude';turn.appendChild(l);
 const cot=document.createElement('details');cot.className='cot';cot.style.display='none';
 cot.innerHTML='<summary>💭 思考过程</summary><div class="cotbody"></div>';
 const b=document.createElement('div');b.className='bubble';b.textContent='…';
 turn.appendChild(cot);turn.appendChild(b);wrap.appendChild(turn);wrap.scrollTop=wrap.scrollHeight;
 return {cot:cot,body:cot.querySelector('.cotbody'),bubble:b};}
async function loadSessions(){const r=await fetch('/api/sessions');const items=await r.json();list.innerHTML='';
 items.forEach(it=>{const d=document.createElement('div');d.className='sitem'+(it.id===curId?' active':'');
  d.innerHTML='<div class="t"></div><div class="x">✕</div>';
  d.querySelector('.t').textContent=it.title||'新通信';
  d.querySelector('.t').onclick=()=>openSession(it.id);
  d.querySelector('.x').onclick=async(e)=>{e.stopPropagation();await fetch('/api/delete/'+it.id,{method:'POST'});
   if(it.id===curId)curId=null;await loadSessions();if(!curId)await ensureSession();};
  list.appendChild(d);});
 if(items.length===0){await newSession();}else if(!curId){openSession(items[0].id);}}
async function openSession(id){curId=id;const r=await fetch('/api/session/'+id);const d=await r.json();
 wrap.innerHTML='';(d.messages||[]).forEach(m=>{if(m[0]==='user')addUser(m[1],null);else addBotStatic(m[1]);});
 await loadSessions();drawer(false);q.focus();}
async function newSession(){const r=await fetch('/api/new',{method:'POST'});const d=await r.json();
 curId=d.id;wrap.innerHTML='';await loadSessions();drawer(false);q.focus();}
async function ensureSession(){const r=await fetch('/api/sessions');const items=await r.json();
 if(items.length)openSession(items[0].id);else newSession();}
newbtn.onclick=newSession;
async function ask(){const t=q.value.trim();if(!t&&!attached)return;q.value='';q.style.height='auto';
 const att=attached;addUser(t,att);send.disabled=true;const k=addBot();
 const body={session_id:curId,message:t,extend:extendOn};
 if(att&&att.kind==='text'){body.attachment=att.content;body.attachment_name=att.name;}
 if(att&&att.kind==='image'){body.image=att.content;body.image_name=att.name;}
 let answer='',thinking='';
 try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const reader=r.body.getReader();const dec=new TextDecoder();let buf='';k.bubble.textContent='';
  while(true){const{value,done}=await reader.read();if(done)break;buf+=dec.decode(value,{stream:true});
   let i;while((i=buf.indexOf('\\n\\n'))>=0){const chunk=buf.slice(0,i);buf=buf.slice(i+2);
    const line=chunk.replace(/^data: ?/,'');if(!line)continue;let d;try{d=JSON.parse(line);}catch(e){continue;}
    if(d.type==='text'){answer+=d.v;k.bubble.textContent=answer;wrap.scrollTop=wrap.scrollHeight;}
    else if(d.type==='thinking'){thinking+=d.v;k.cot.style.display='block';k.body.textContent=thinking;wrap.scrollTop=wrap.scrollHeight;}
    else if(d.type==='done'){if(d.session_id)curId=d.session_id;}}}
  if(!answer)k.bubble.textContent='(无返回)';}
 catch(e){k.bubble.textContent='错误: '+e;}
 send.disabled=false;attached=null;chip.style.display='none';q.focus();loadSessions();}
send.onclick=ask;
q.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask();}});
loadSessions();
</script></body></html>"""

class Msg(BaseModel):
    session_id: str = ""
    message: str = ""
    extend: bool = False
    attachment: str = ""
    attachment_name: str = ""
    image: str = ""
    image_name: str = ""

@app.get("/")
def index():
    return HTMLResponse(PAGE)

@app.get("/api/sessions")
def api_sessions():
    s = store["sessions"]
    items = [{"id": k, "title": v.get("title", "新通信"), "ts": v.get("ts", 0)} for k, v in s.items()]
    items.sort(key=lambda x: x["ts"], reverse=True)
    return JSONResponse(items)

@app.post("/api/new")
def api_new():
    sid = uuid.uuid4().hex[:12]
    store["sessions"][sid] = {"title": "新通信", "ts": time.time(), "messages": []}
    save_store()
    return JSONResponse({"id": sid, "title": "新通信"})

@app.get("/api/session/{sid}")
def api_session(sid: str):
    sess = store["sessions"].get(sid)
    if not sess:
        return JSONResponse({"messages": [], "title": ""})
    return JSONResponse({"messages": sess["messages"], "title": sess.get("title", "")})

@app.post("/api/delete/{sid}")
def api_delete(sid: str):
    store["sessions"].pop(sid, None)
    save_store()
    return JSONResponse({"ok": True})

@app.post("/api/chat")
def chat(msg: Msg):
    sid = msg.session_id
    sess = store["sessions"].get(sid)
    if sess is None:
        sid = uuid.uuid4().hex[:12]
        sess = {"title": "新通信", "ts": time.time(), "messages": []}
        store["sessions"][sid] = sess
    conv = sess["messages"]
    sys = build_system()
    lines = []
    for m in conv[-20:]:
        lines.append(("用户" if m[0] == "user" else "助手") + ": " + m[1])
    user_text = msg.message
    if msg.attachment:
        user_text += "\n\n【附件 " + (msg.attachment_name or "file") + " 的内容】\n" + msg.attachment
    img_path = None
    if msg.image:
        try:
            img_path = save_image(msg.image, msg.image_name or "img.png")
        except Exception as e:
            user_text += "\n\n(图片保存失败: " + str(e) + ")"
    if img_path:
        user_text = "请使用 Read 工具查看这张图片文件：" + img_path + "\n\n" + (user_text or "请描述这张图片。")
    if msg.extend:
        user_text += "\n\nultrathink"
    lines.append("用户: " + user_text)
    prompt = "\n".join(lines) + "\n助手:"

    cmd = [CLAUDE, "-p", "--model", MODEL]
    if img_path:
        cmd += ["--allowedTools", "Read"]
    else:
        cmd += ["--tools", "none"]
    cmd += ["--system-prompt", sys, "--output-format", "stream-json",
            "--verbose", "--include-partial-messages", prompt]

    def gen():
        parts = []
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    text=True, encoding="utf-8", errors="replace", bufsize=1)
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("type") == "stream_event":
                    e = ev.get("event", {})
                    if e.get("type") == "content_block_delta":
                        dd = e.get("delta", {})
                        if dd.get("type") == "thinking_delta":
                            yield "data: " + json.dumps({"type": "thinking", "v": dd.get("thinking", "")}) + "\n\n"
                        elif dd.get("type") == "text_delta":
                            parts.append(dd.get("text", ""))
                            yield "data: " + json.dumps({"type": "text", "v": dd.get("text", "")}) + "\n\n"
                elif ev.get("type") == "result":
                    if not parts and ev.get("result"):
                        parts.append(ev.get("result", ""))
                        yield "data: " + json.dumps({"type": "text", "v": ev.get("result", "")}) + "\n\n"
            proc.wait()
        except Exception as e:
            yield "data: " + json.dumps({"type": "text", "v": "出错: " + str(e)}) + "\n\n"
        reply = "".join(parts).strip() or "(无返回)"
        conv.append(["user", msg.message or "(附件/图片)"])
        conv.append(["assistant", reply])
        if sess.get("title", "新通信") == "新通信" and msg.message:
            sess["title"] = msg.message[:18]
        sess["ts"] = time.time()
        save_store()
        yield "data: " + json.dumps({"type": "done", "session_id": sid}) + "\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
