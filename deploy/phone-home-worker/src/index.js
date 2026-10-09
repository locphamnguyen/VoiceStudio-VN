// Worker gọi-về (phone-home) cho VoiceStudio-VN — trang trung tâm. Port từ ZaloCRM.
//
// Hợp đồng với bản cài (backend/core/announcement.py):
//   POST /voicestudio-phone-home/v1/ping   body { instanceId, version }
//   → 200 { announcement: null | { id, text, level, link, linkLabel, dismissible } }
//
// Nguyên tắc: KHÔNG ghi IP, KHÔNG ghi header, KHÔNG ghi gì ngoài hai trường gửi lên.
// Lỗi phía này trả 200 { announcement: null } khi có thể — bản cài không bao giờ cần biết
// trang trung tâm hỏng.
//
// Quản trị (Bearer ADMIN_TOKEN):
//   GET  /voicestudio-phone-home/v1/admin/stats               → { installed, activeLast7d, activeLast30d, byVersion }
//   GET  /voicestudio-phone-home/v1/admin/announcements       → danh sách
//   PUT  /voicestudio-phone-home/v1/admin/announcements/:id   → upsert { text, level?, link?, linkLabel?,
//                                                   dismissible?, enabled?, minVersion?, maxVersion?,
//                                                   targetInstanceId? }
//   DELETE /voicestudio-phone-home/v1/admin/announcements/:id

const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };

function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}

function isSafeId(s) {
  return typeof s === 'string' && s.length > 0 && s.length <= 100 && /^[A-Za-z0-9._:-]+$/.test(s);
}
function isSafeVersion(s) {
  return typeof s === 'string' && s.length > 0 && s.length <= 40 && /^[A-Za-z0-9.+-]+$/.test(s);
}

// semver thô: so phần số đầu "a.b.c", phần hậu tố bỏ qua. "unknown" coi như 0.0.0.
function parseVer(v) {
  const m = /^(\d+)(?:\.(\d+))?(?:\.(\d+))?/.exec(String(v || ''));
  return m ? [Number(m[1]), Number(m[2] || 0), Number(m[3] || 0)] : [0, 0, 0];
}
function cmpVer(a, b) {
  const [x, y] = [parseVer(a), parseVer(b)];
  for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
  return 0;
}

function matches(row, version, instanceId) {
  if (row.target_instance_id && row.target_instance_id !== instanceId) return false;
  if (row.min_version && cmpVer(version, row.min_version) < 0) return false;
  if (row.max_version && cmpVer(version, row.max_version) > 0) return false;
  return true;
}

function toAnnouncement(row) {
  return {
    id: row.id,
    text: row.text,
    level: row.level || 'info',
    link: row.link || null,
    linkLabel: row.link_label || null,
    // Mặc định không cho đóng: chỉ 1 mới hiện nút đóng trên giao diện.
    dismissible: row.dismissible === 1,
  };
}

async function handlePing(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ announcement: null }, 400);
  }
  const instanceId = body && body.instanceId;
  const version = body && body.version;
  if (!isSafeId(instanceId) || !isSafeVersion(version)) return json({ announcement: null }, 400);

  const now = new Date().toISOString();
  try {
    await env.DB.prepare(
      `INSERT INTO instances (instance_id, version, first_seen_at, last_seen_at, ping_count)
       VALUES (?1, ?2, ?3, ?3, 1)
       ON CONFLICT(instance_id) DO UPDATE SET
         version = excluded.version, last_seen_at = excluded.last_seen_at, ping_count = ping_count + 1`,
    ).bind(instanceId, version, now).run();
  } catch (err) {
    console.error('record failed', err);
    // Vẫn trả thông báo nếu đọc được — ghi hỏng không phải lỗi của bản cài.
  }

  let announcement = null;
  try {
    const { results } = await env.DB.prepare(
      `SELECT * FROM announcements WHERE enabled = 1 ORDER BY created_at DESC`,
    ).all();
    const hit = (results || []).find((r) => matches(r, version, instanceId));
    if (hit) announcement = toAnnouncement(hit);
  } catch (err) {
    console.error('read announcements failed', err);
  }
  return json({ announcement });
}

function authed(request, env) {
  const h = request.headers.get('authorization') || '';
  return env.ADMIN_TOKEN && h === `Bearer ${env.ADMIN_TOKEN}`;
}

async function handleAdmin(request, env, path) {
  if (!authed(request, env)) return json({ error: 'unauthorized' }, 401);

  if (request.method === 'GET' && path === '/admin/stats') {
    const d7 = new Date(Date.now() - 7 * 864e5).toISOString();
    const d30 = new Date(Date.now() - 30 * 864e5).toISOString();
    const [installed, a7, a30, byVersion] = await Promise.all([
      env.DB.prepare('SELECT COUNT(*) AS n FROM instances').first('n'),
      env.DB.prepare('SELECT COUNT(*) AS n FROM instances WHERE last_seen_at >= ?1').bind(d7).first('n'),
      env.DB.prepare('SELECT COUNT(*) AS n FROM instances WHERE last_seen_at >= ?1').bind(d30).first('n'),
      env.DB.prepare('SELECT version, COUNT(*) AS n FROM instances GROUP BY version ORDER BY n DESC').all(),
    ]);
    return json({ installed, activeLast7d: a7, activeLast30d: a30, byVersion: byVersion.results || [] });
  }

  if (request.method === 'GET' && path === '/admin/announcements') {
    const { results } = await env.DB.prepare('SELECT * FROM announcements ORDER BY created_at DESC').all();
    return json({ announcements: results || [] });
  }

  const m = /^\/admin\/announcements\/([A-Za-z0-9._:-]{1,100})$/.exec(path);
  if (m && request.method === 'PUT') {
    let b;
    try {
      b = await request.json();
    } catch {
      return json({ error: 'bad json' }, 400);
    }
    if (typeof b.text !== 'string' || !b.text.trim()) return json({ error: 'text required' }, 400);
    if (b.link && !/^https:\/\//.test(b.link)) return json({ error: 'link must be https' }, 400);
    const level = ['info', 'warning', 'critical'].includes(b.level) ? b.level : 'info';
    await env.DB.prepare(
      `INSERT INTO announcements (id, text, level, link, link_label, dismissible, enabled, min_version, max_version, target_instance_id)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)
       ON CONFLICT(id) DO UPDATE SET text=excluded.text, level=excluded.level, link=excluded.link,
         link_label=excluded.link_label, dismissible=excluded.dismissible, enabled=excluded.enabled,
         min_version=excluded.min_version, max_version=excluded.max_version,
         target_instance_id=excluded.target_instance_id`,
    )
      .bind(
        m[1],
        b.text.trim().slice(0, 500),
        level,
        b.link || null,
        b.linkLabel ? String(b.linkLabel).slice(0, 60) : null,
        b.dismissible === true ? 1 : 0,
        b.enabled === false ? 0 : 1,
        b.minVersion || null,
        b.maxVersion || null,
        b.targetInstanceId || null,
      )
      .run();
    return json({ ok: true, id: m[1] });
  }
  if (m && request.method === 'DELETE') {
    await env.DB.prepare('DELETE FROM announcements WHERE id = ?1').bind(m[1]).run();
    return json({ ok: true });
  }
  return json({ error: 'not found' }, 404);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/^\/voicestudio-phone-home\/v1/, '');
    if (path === '/ping') {
      if (request.method !== 'POST') return json({ announcement: null }, 405);
      return handlePing(request, env);
    }
    if (path.startsWith('/admin/')) return handleAdmin(request, env, path);
    return json({ error: 'not found' }, 404);
  },
};
