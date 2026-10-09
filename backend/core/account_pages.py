"""Trang đăng nhập / đăng ký / chờ duyệt / tài khoản / thành viên (HTML máy chủ dựng).

Các trang này hiện ra TRƯỚC khi có phiên, nên không nằm trong bundle React.
Cùng một "vỏ" (logo + card + CSS) cho mọi trang để đổi giao diện một chỗ.

Mọi đường dẫn trong trang là TƯƠNG ĐỐI (``login``, ``register``…): cùng một trang
chạy được ở ``/account/…`` (bản build phục vụ từ backend) lẫn ``/api/account/…``
(máy chủ phát triển Vite chuyển tiếp ``/api``).
"""

from __future__ import annotations

import html
import json

# Câu cho tham số ``?loi=`` — khớp bảng REASONS ở core/accounts.py. Mã lạ → "he_thong".
LOGIN_ERRORS = {
    "chua_xac_minh": "Địa chỉ email chưa được Google xác minh.",
    "thieu_email": "Google không trả về địa chỉ email của tài khoản này.",
    "sai_mien": "Tài khoản này không thuộc tên miền được phép đăng nhập.",
    "google_tu_choi": "Bạn đã huỷ hoặc Google từ chối cấp quyền đăng nhập.",
    "phien_dang_nhap_hong": "Lượt đăng nhập đã hết hạn hoặc không hợp lệ. Vui lòng thử lại.",
    "google_chua_bat": "Đăng nhập bằng Google chưa được cấu hình trên máy chủ này.",
    "he_thong": "Hệ thống gặp sự cố khi đăng nhập. Vui lòng thử lại sau ít phút.",
}

_CSS = """
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:flex;align-items:center;
justify-content:center;padding:16px;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
background:radial-gradient(1200px 600px at 50% -10%,#1e1b3a,#0b0b12 60%);color:#ececf4}
.card{width:100%;max-width:420px;padding:36px 30px;background:#14141d;border:1px solid #262636;
border-radius:18px;box-shadow:0 20px 60px rgba(0,0,0,.45);text-align:center}
.card.wide{max-width:860px;text-align:left}
.brand{display:flex;align-items:center;justify-content:center;gap:11px;margin-bottom:24px}
.mark{width:44px;height:44px;border-radius:13px;display:grid;place-items:center;
background:linear-gradient(135deg,#a78bfa,#6d28d9);
box-shadow:0 6px 18px -6px rgba(167,139,250,.6),inset 0 1px 0 rgba(255,255,255,.4)}
.mark svg{display:block}
.bname{font-weight:800;font-size:21px;letter-spacing:-.02em;line-height:1;text-align:left}
.bname .d{color:#a78bfa}
.bsub{font-size:9px;color:#7c7c96;letter-spacing:.12em;text-transform:uppercase;
margin-top:4px;font-weight:600;text-align:left}
h1{font-size:18px;margin:0 0 8px}p{font-size:14px;color:#a3a3bd;margin:0 0 20px;line-height:1.5}
form{display:flex;flex-direction:column;gap:12px;text-align:left}
label{font-size:12px;font-weight:600;color:#a3a3bd;display:block;margin-bottom:5px}
input{width:100%;padding:11px 13px;border-radius:10px;border:1px solid #30304a;background:#0d0d14;
color:#ececf4;font-size:14px;outline:none}
input:focus{border-color:#a78bfa}
.hint{font-size:11.5px;color:#7c7c96;margin-top:4px}
.btn{display:flex;align-items:center;justify-content:center;gap:9px;width:100%;padding:12px 20px;
border-radius:10px;font-weight:700;font-size:14px;text-decoration:none;border:0;cursor:pointer;font-family:inherit}
.btn[disabled]{opacity:.6;cursor:not-allowed}
.primary{color:#fff;background:linear-gradient(135deg,#8b5cf6,#6d28d9)}
.secondary{color:#dcdcef;background:transparent;border:1px solid #30304a}
.secondary:hover{background:#1c1c2a}
.gicon{background:#fff;border-radius:3px;padding:2px;display:grid;place-items:center}
.or{display:flex;align-items:center;gap:10px;margin:18px 0;color:#7c7c96;font-size:12px}
.or:before,.or:after{content:"";flex:1;height:1px;background:#262636}
.alert{border-radius:10px;padding:10px 12px;font-size:13px;text-align:left;margin-bottom:16px;line-height:1.45}
.alert.err{background:#2a1418;border:1px solid #5b2530;color:#fda4af}
.alert.ok{background:#0f2a22;border:1px solid #1f5a47;color:#86efac}
.alert[hidden]{display:none}
.foot{margin-top:18px;font-size:13px;color:#a3a3bd;text-align:center}
.foot a{color:#c4b5fd;font-weight:600;text-decoration:none}
.foot a:hover{text-decoration:underline}
.btns{display:flex;flex-direction:column;gap:10px}
.row{display:flex;gap:10px;flex-wrap:wrap}.row .btn{width:auto;flex:1}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:9px 8px;border-bottom:1px solid #262636;text-align:left;vertical-align:middle}
th{color:#7c7c96;font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em}
.tag{display:inline-block;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:700}
.tag.active{background:#0f2a22;color:#86efac}.tag.pending{background:#2a2410;color:#fde68a}
.tag.disabled{background:#2a1418;color:#fda4af}.tag.admin{background:#221a3d;color:#c4b5fd}
.acts{display:flex;gap:6px;flex-wrap:wrap}
.acts button{padding:5px 9px;border-radius:7px;border:1px solid #30304a;background:#1a1a27;color:#dcdcef;
font-size:12px;cursor:pointer;font-family:inherit}
.acts button:hover{background:#25253a}.acts button.danger{color:#fda4af;border-color:#5b2530}
.tabs{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
.tabs a{padding:6px 12px;border-radius:99px;border:1px solid #30304a;color:#dcdcef;text-decoration:none;font-size:12.5px}
.tabs a.on{background:#6d28d9;border-color:#6d28d9;color:#fff}
.scroll{overflow-x:auto}
"""

_HEADER = """<div class="brand">
<span class="mark"><svg width="24" height="24" viewBox="0 0 24 24" fill="none"
stroke="#fff" stroke-width="2.4" stroke-linecap="round">
<path d="M2 10v3M6 6v11M10 3v18M14 8v7M18 5v13M22 10v3"/></svg></span>
<span><div class="bname">VoiceStudio<span class="d">.</span></div><div class="bsub">Bản tiếng Việt</div></span>
</div>"""

_GOOGLE_ICON = """<span class="gicon"><svg width="16" height="16" viewBox="0 0 48 48">
<path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.6 2.4 30.1 0 24 0 14.6 0 6.4 5.4 2.5 13.3l7.9 6.1C12.3 13.2 17.6 9.5 24 9.5z"/>
<path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.5 3-2.2 5.5-4.7 7.2l7.3 5.7c4.3-3.9 6.8-9.7 6.8-17.4z"/>
<path fill="#FBBC05" d="M10.4 28.6c-.5-1.5-.8-3-.8-4.6s.3-3.1.8-4.6l-7.9-6.1C.9 16.5 0 20.1 0 24s.9 7.5 2.5 10.7l7.9-6.1z"/>
<path fill="#34A853" d="M24 48c6.1 0 11.3-2 15-5.5l-7.3-5.7c-2 1.4-4.7 2.3-7.7 2.3-6.4 0-11.7-3.7-13.6-9.4l-7.9 6.1C6.4 42.6 14.6 48 24 48z"/>
</svg></span>"""

# Hàm dùng chung: gửi JSON (không nộp form kiểu cũ — máy chủ chỉ nhận
# application/json + header chống CSRF, nên form giả mạo từ trang khác không
# đi qua được) và tính địa chỉ gốc của ứng dụng từ đường dẫn hiện tại.
_COMMON_JS = """<script>
window.VS={
  root:function(){return location.pathname.replace(/(\\/api)?\\/account(\\/.*)?$/,'/')||'/'},
  go:function(r){location.href=(r==='/'?VS.root():r)},
  post:function(url,data){return fetch(url,{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','Accept':'application/json','X-VoiceStudio-CSRF':'1'},
    body:JSON.stringify(data||{})}).then(function(r){return r.json().catch(function(){return {}})
    .then(function(j){return {r:r,j:j}})})},
  err:function(x){return (x.j&&x.j.error&&x.j.error.message)||('Lỗi HTTP '+x.r.status)}
};
</script>"""

_FORM_JS = """<script>
(function(){
  var f=document.getElementById('f'),a=document.getElementById('msg'),b=f.querySelector('button');
  function show(kind,text){a.className='alert '+kind;a.textContent=text;a.hidden=false}
  f.addEventListener('submit',function(e){
    e.preventDefault();if(b.disabled)return;
    var data={};new FormData(f).forEach(function(v,k){data[k]=v});
    if(f.dataset.confirm&&data.password!==data.password2){show('err','Hai lần nhập mật khẩu không khớp.');return}
    delete data.password2;
    b.disabled=true;var label=b.textContent;b.textContent='Đang xử lý...';
    VS.post(f.dataset.action,data).then(function(x){
      if(x.j&&x.j.redirect){VS.go(x.j.redirect);return}
      if(x.r.ok){show('ok',(x.j&&x.j.message)||'Thành công.');f.reset();return}
      show('err',VS.err(x));
    })
    .catch(function(){show('err','Không kết nối được máy chủ. Vui lòng thử lại.')})
    .finally(function(){b.disabled=false;b.textContent=label});
  });
})();
</script>"""


def page(title: str, body_html: str, *, wide: bool = False) -> str:
    cls = "card wide" if wide else "card"
    return (
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex">'
        f"<title>{html.escape(title)} · VoiceStudio</title><style>{_CSS}</style>{_COMMON_JS}</head>"
        f'<body><div class="{cls}">{_HEADER}{body_html}</div></body></html>'
    )


def _alert(error: str | None) -> str:
    if not error:
        return '<div id="msg" class="alert" hidden></div>'
    text = LOGIN_ERRORS.get(error, LOGIN_ERRORS["he_thong"])
    return f'<div id="msg" class="alert err">{html.escape(text)}</div>'


def _google_block(google_enabled: bool, label: str) -> str:
    if not google_enabled:
        return ""
    return (
        '<div class="or">hoặc</div>'
        f'<a class="btn secondary" href="google">{_GOOGLE_ICON}{html.escape(label)}</a>'
    )


def login_page(google_enabled: bool, error: str | None = None) -> str:
    """Màn hình đầu tiên người chưa đăng nhập nhìn thấy."""
    body = (
        "<h1>Chào mừng đến VoiceStudio</h1>"
        "<p>Đăng nhập để bắt đầu nhân bản giọng, lồng tiếng và tạo giọng nói AI.</p>"
        f"{_alert(error)}"
        '<form id="f" data-action="login" novalidate>'
        '<div><label for="email">Email</label>'
        '<input id="email" name="email" type="email" autocomplete="username" required></div>'
        '<div><label for="password">Mật khẩu</label>'
        '<input id="password" name="password" type="password" autocomplete="current-password" required></div>'
        '<button class="btn primary" type="submit">Đăng nhập</button>'
        "</form>"
        f"{_google_block(google_enabled, 'Tiếp tục với Google')}"
        '<div class="foot">Chưa có tài khoản? <a href="register">Đăng ký</a></div>'
        f"{_FORM_JS}"
    )
    return page("Đăng nhập", body)


def register_page(google_enabled: bool, first_user: bool = False) -> str:
    intro = (
        "Bạn là người đầu tiên — tài khoản này sẽ là <strong>Quản trị viên</strong> "
        "và dùng được ngay."
        if first_user else
        "Tài khoản mới sẽ dùng được sau khi Quản trị viên duyệt."
    )
    body = (
        "<h1>Tạo tài khoản VoiceStudio</h1>"
        f"<p>{intro}</p>"
        '<div id="msg" class="alert" hidden></div>'
        '<form id="f" data-action="register" data-confirm="1" novalidate>'
        '<div><label for="full_name">Họ tên</label>'
        '<input id="full_name" name="full_name" autocomplete="name" required></div>'
        '<div><label for="email">Email</label>'
        '<input id="email" name="email" type="email" autocomplete="email" required></div>'
        '<div><label for="password">Mật khẩu</label>'
        '<input id="password" name="password" type="password" autocomplete="new-password" required>'
        '<div class="hint">Ít nhất 10 ký tự.</div></div>'
        '<div><label for="password2">Nhập lại mật khẩu</label>'
        '<input id="password2" name="password2" type="password" autocomplete="new-password" required></div>'
        '<button class="btn primary" type="submit">Đăng ký</button>'
        "</form>"
        f"{_google_block(google_enabled, 'Đăng ký bằng Google')}"
        '<div class="foot">Đã có tài khoản? <a href="login">Đăng nhập</a></div>'
        f"{_FORM_JS}"
    )
    return page("Đăng ký", body)


def pending_page() -> str:
    body = (
        "<h1>Tài khoản đang chờ duyệt</h1>"
        "<p>Yêu cầu của bạn đã được ghi nhận. Bạn sẽ dùng được VoiceStudio sau khi "
        "Quản trị viên duyệt tài khoản. Nếu đã chờ lâu, hãy liên hệ Quản trị viên.</p>"
        '<div class="btns">'
        '<a class="btn primary" href="login">Thử đăng nhập lại</a>'
        '<a class="btn secondary" href="logout">Dùng tài khoản khác</a>'
        "</div>"
    )
    return page("Chờ duyệt", body)


def profile_page(user: dict) -> str:
    """Trang "Tài khoản của tôi": thông tin, đổi mật khẩu, đăng xuất."""
    name = html.escape(user.get("full_name") or "")
    email = html.escape(user.get("email") or "")
    role = "Quản trị viên" if user.get("is_admin") else "Thành viên"
    members = (
        '<a class="btn secondary" href="members">Quản lý thành viên</a>' if user.get("is_admin") else ""
    )
    current_field = (
        '<div><label for="current">Mật khẩu hiện tại</label>'
        '<input id="current" name="current_password" type="password" autocomplete="current-password" required></div>'
        if user.get("has_password") else
        '<p class="hint">Tài khoản này đang đăng nhập bằng Google. Đặt mật khẩu để đăng nhập được cả bằng email.</p>'
    )
    body = (
        f"<h1>{name}</h1>"
        f"<p>{email} · {role}</p>"
        '<div class="btns">'
        '<a class="btn primary" id="back" href="#">Về ứng dụng</a>'
        f"{members}"
        '<a class="btn secondary" href="logout">Đăng xuất</a>'
        "</div>"
        '<div class="or">đổi mật khẩu</div>'
        '<div id="msg" class="alert" hidden></div>'
        '<form id="f" data-action="password" data-confirm="1" novalidate>'
        f"{current_field}"
        '<div><label for="password">Mật khẩu mới</label>'
        '<input id="password" name="password" type="password" autocomplete="new-password" required>'
        '<div class="hint">Ít nhất 10 ký tự.</div></div>'
        '<div><label for="password2">Nhập lại mật khẩu mới</label>'
        '<input id="password2" name="password2" type="password" autocomplete="new-password" required></div>'
        '<button class="btn primary" type="submit">Lưu mật khẩu</button>'
        "</form>"
        "<script>document.getElementById('back').href=VS.root();</script>"
        f"{_FORM_JS}"
    )
    return page("Tài khoản", body)


_MEMBERS_JS = """<script>
(function(){
  var me=__ME__, data={users:[]}, filter='pending';
  var a=document.getElementById('msg'), body=document.getElementById('rows'), tabs=document.getElementById('tabs');
  var LABEL={pending:'Chờ duyệt',active:'Đang hoạt động',disabled:'Đã khoá',all:'Tất cả'};
  var ACT={approve:'Duyệt',disable:'Khoá',make_admin:'Cấp quyền QTV',revoke_admin:'Gỡ quyền QTV',delete:'Xoá'};
  function show(kind,text){a.className='alert '+kind;a.textContent=text;a.hidden=false}
  function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML}
  function day(ts){return ts?new Date(ts*1000).toLocaleDateString('vi-VN'):'—'}
  function render(){
    var counts={pending:0,active:0,disabled:0,all:data.users.length};
    data.users.forEach(function(u){counts[u.status]++});
    tabs.innerHTML=['pending','active','disabled','all'].map(function(k){
      return '<a href="#" data-f="'+k+'" class="'+(k===filter?'on':'')+'">'+LABEL[k]+' ('+counts[k]+')</a>'}).join('');
    var list=data.users.filter(function(u){return filter==='all'||u.status===filter});
    if(!list.length){body.innerHTML='<tr><td colspan="5" style="color:#7c7c96">Không có tài khoản nào.</td></tr>';return}
    body.innerHTML=list.map(function(u){
      var acts=[];
      if(u.status!=='active')acts.push('approve');
      if(u.email!==me){
        if(u.status==='active')acts.push('disable');
        if(u.status==='active'&&!u.is_admin)acts.push('make_admin');
        if(u.is_admin)acts.push('revoke_admin');
        acts.push('delete');
      }
      return '<tr><td><strong>'+esc(u.full_name)+'</strong><br><span style="color:#7c7c96">'+esc(u.email)+'</span></td>'+
        '<td><span class="tag '+u.status+'">'+LABEL[u.status]+'</span>'+(u.is_admin?' <span class="tag admin">QTV</span>':'')+'</td>'+
        '<td>'+esc((u.providers||[]).join(', '))+'</td><td>'+day(u.created_at)+'</td>'+
        '<td><div class="acts">'+acts.map(function(k){
          return '<button data-e="'+esc(u.email)+'" data-a="'+k+'" class="'+(k==='delete'?'danger':'')+'">'+ACT[k]+'</button>'}).join('')+
        '</div></td></tr>'}).join('');
  }
  function load(){
    fetch('users',{credentials:'same-origin',headers:{'Accept':'application/json'}})
      .then(function(r){return r.json().then(function(j){return {r:r,j:j}})})
      .then(function(x){if(!x.r.ok){show('err',VS.err(x));return}
        data=x.j;if(filter==='pending'&&!data.pending)filter='all';render()})
      .catch(function(){show('err','Không kết nối được máy chủ.')});
  }
  tabs.addEventListener('click',function(e){var f=e.target.getAttribute('data-f');if(f){e.preventDefault();filter=f;render()}});
  body.addEventListener('click',function(e){
    var em=e.target.getAttribute('data-e'),act=e.target.getAttribute('data-a');if(!em||!act)return;
    if(act==='delete'&&!confirm('Xoá vĩnh viễn tài khoản '+em+'?'))return;
    e.target.disabled=true;
    VS.post('users/'+encodeURIComponent(em),{action:act}).then(function(x){
      if(!x.r.ok){show('err',VS.err(x));e.target.disabled=false;return}
      show('ok','Đã cập nhật '+em+'.');load()})
    .catch(function(){show('err','Không kết nối được máy chủ.');e.target.disabled=false});
  });
  document.getElementById('back').href=VS.root();
  load();
})();
</script>"""


def members_page(me_email: str) -> str:
    """Trang Quản trị viên: duyệt người đăng ký mới, khoá / xoá / cấp quyền."""
    body = (
        "<h1>Quản lý thành viên</h1>"
        "<p>Người đăng ký mới cần được duyệt trước khi dùng VoiceStudio.</p>"
        '<div class="row" style="margin-bottom:16px">'
        '<a class="btn secondary" id="back" href="#">Về ứng dụng</a>'
        '<a class="btn secondary" href="profile">Tài khoản của tôi</a></div>'
        '<div id="msg" class="alert" hidden></div>'
        '<div id="tabs" class="tabs"></div>'
        '<div class="scroll"><table><thead><tr><th>Người dùng</th><th>Trạng thái</th>'
        "<th>Đăng nhập bằng</th><th>Ngày tạo</th><th>Thao tác</th></tr></thead>"
        '<tbody id="rows"></tbody></table></div>'
        + _MEMBERS_JS.replace("__ME__", json.dumps(me_email).replace("</", "<\\/"))
    )
    return page("Thành viên", body, wide=True)
