/* FixPilot 前端逻辑：登录 + 多窗口会话(后端存储) + 聊天 */
/* URL 参数 ?bg=N 切换登录页布局主题（1-5），默认 2（左右分栏） */
const _bg = new URLSearchParams(location.search).get('bg') || '2';
if (/^[1-5]$/.test(_bg)) document.body.classList.add('bg-' + _bg);

/* 兼容不支持 background-clip:text 的设备：品牌名回退为纯色文字，避免出现渐变方框 */
if (window.CSS && CSS.supports && !CSS.supports('background-clip', 'text')) {
  document.body.classList.add('no-textclip');
}

/* 部署前缀：应用可挂载到子路径（如 /fixpilot），本地根路径时为空串 */
const BASE = (function () {
  const p = location.pathname.replace(/\/+$/, '').split('/');
  return (p.length > 1 && p[1]) ? '/' + p[1] : '';
})();

const chatEl = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const convList = document.getElementById('convList');
const sidebar = document.getElementById('sidebar');
const scrim = document.getElementById('scrim');
const menuBtn = document.getElementById('menuBtn');
const newChatBtn = document.getElementById('newChat');
const quotaBadge = document.getElementById('quotaBadge');
const shareBtn = document.getElementById('shareBtn');
const shareMenu = document.getElementById('shareMenu');
const shareImgOpt = document.getElementById('shareImgOpt');
const shareLinkOpt = document.getElementById('shareLinkOpt');

/* 登录界面元素 */
const loginScreen = document.getElementById('loginScreen');
const appEl = document.getElementById('app');
const tabBtns = document.querySelectorAll('.login-tab');
const invitePanel = document.getElementById('invitePanel');
const adminPanel = document.getElementById('adminPanel');
const inviteCode = document.getElementById('inviteCode');
const codeBoxes = document.getElementById('codeBoxes');
const inviteLoginBtn = document.getElementById('inviteLoginBtn');
const inviteErr = document.getElementById('inviteErr');
const adminUser = document.getElementById('adminUser');
const adminPass = document.getElementById('adminPass');
const adminLoginBtn = document.getElementById('adminLoginBtn');
const adminErr = document.getElementById('adminErr');

const TOKEN_KEY = 'fixpilot_token';
const USER_KEY = 'fixpilot_user';

/* ---------- 会话状态 ---------- */
let conversations = [];
let activeConvId = null;
let busy = false;
let canUse = true;
/* 当前登录身份与绑定状态（enterApp 时从 /me 同步） */
let currentRole = null;       // 'admin' | 'user'
let boundUsername = null;     // 邀请码用户已绑定的账号名，null 表示未绑定
let bindBannerShown = false;  // 本次会话是否已弹过绑定提示条
let bindBannerDismissed = false; // 用户已手动关闭提示条，本次会话不再弹
let currentUser = null;       // /api/auth/me 返回的完整用户对象
let currentProfile = null;    // 后端保存的回答偏好与技术水平画像

/* ---------- 随机用户头像（42 张 WebP，首次登录随机分配） ---------- */
const AVATAR_KEY = 'fixpilot_avatar';
const AVATAR_COUNT = 42;
function getAvatarIdx() {
  let idx = parseInt(localStorage.getItem(AVATAR_KEY) || '0', 10);
  if (!idx || idx < 1 || idx > AVATAR_COUNT) {
    idx = Math.floor(Math.random() * AVATAR_COUNT) + 1;
    localStorage.setItem(AVATAR_KEY, String(idx));
  }
  return idx;
}
function avatarUrl() { return 'avatars/' + getAvatarIdx() + '.webp'; }

/* ---------- 自定义 API（用户自带 Key） ---------- */
const API_SETTINGS_KEY = 'fixpilot_api_settings';
/* 各服务商默认地址与常用模型列表 */
const API_PRESETS = {
  deepseek: {
    base: 'https://api.deepseek.com',
    models: ['deepseek-chat', 'deepseek-reasoner'],
  },
  volcengine: {
    base: 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
    models: ['deepseek-v4-flash'],
    keyPlaceholder: '\u706b\u5c71\u65b9\u821f API Key',
  },
  openai: {
    base: 'https://api.openai.com/v1',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  },
};
function getApiSettings() {
  try { return JSON.parse(localStorage.getItem(API_SETTINGS_KEY) || 'null'); } catch (e) { return null; }
}
function saveApiSettings(s) { localStorage.setItem(API_SETTINGS_KEY, JSON.stringify(s)); }
function clearApiSettings() { localStorage.removeItem(API_SETTINGS_KEY); }
/** 返回当前应随 chat 请求发送的自定义 API 参数，无则返回 null */
function chatApiParams() {
  const s = getApiSettings();
  if (!s || !s.apiKey) return null;
  return { apiKey: s.apiKey, apiBase: s.apiBase || '', model: s.model || '' };
}

/* ---------- 认证 ---------- */
function getToken() { return localStorage.getItem(TOKEN_KEY) || ''; }
function getUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch (e) { return null; }
}
function setSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}
function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
function defaultProfile() {
  return {
    technical_level: 'unknown', technical_level_source: 'inferred_pending',
    technical_confidence: 'low', response_style: 'normal',
    onboarding_completed: 0, onboarding_seen: 0, onboarding_nudge_shown: 0,
  };
}
function useProfile(profile) {
  currentProfile = Object.assign(defaultProfile(), profile || {});
}
function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  const t = getToken();
  if (t) h['Authorization'] = 'Bearer ' + t;
  return h;
}

/* 顶部居中 Toast */
let _toastTimer = null;
const toastEl = document.getElementById('toast');
function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2200);
}

function showLogin() {
  loginScreen.style.display = 'flex';
  appEl.style.display = 'none';
}
function showApp() {
  loginScreen.style.display = 'none';
  appEl.style.display = 'flex';
  shareBtn.style.display = 'inline-flex';
  closeShareMenu();
}

/* 登录 Tab 切换 */
tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    tabBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    invitePanel.style.display = tab === 'invite' ? 'flex' : 'none';
    adminPanel.style.display = tab === 'admin' ? 'flex' : 'none';
  });
});

/* 邀请码 8 格显示（可选中、复制、粘贴，自动转大写） */
function updateCodeBoxes() {
  const v = (inviteCode.value || '').replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 6);
  if (inviteCode.value !== v) inviteCode.value = v;
  codeBoxes.querySelectorAll('.code-box').forEach((b, i) => {
    b.textContent = v[i] || '';
    b.classList.toggle('filled', !!v[i]);
    b.classList.toggle('active', i === v.length);
  });
}
inviteCode.addEventListener('input', updateCodeBoxes);

/* 分享链接直达：?code=XXX 自动填入邀请码并聚焦 */
function handleInviteParam() {
  const p = new URLSearchParams(location.search);
  const code = p.get('code');
  if (code) {
    inviteCode.value = code.trim().toUpperCase();
    updateCodeBoxes();
    inviteCode.focus();
  }
}

async function doInviteLogin(code) {
  if (!code) { inviteErr.textContent = '请输入邀请码'; return; }
  inviteErr.textContent = '';
  inviteLoginBtn.disabled = true;
  try {
    const r = await fetch('api/auth/invite-login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code })
    });
    const d = await r.json();
    if (!r.ok) {
      inviteErr.textContent = d.detail || '登录失败';
      return;
    }
    setSession(d.token, { role: d.role, code: d.code });
    await enterApp();
  } catch (e) {
    inviteErr.textContent = '网络错误，请重试';
  } finally {
    inviteLoginBtn.disabled = false;
  }
}

async function doAdminLogin() {
  const username = adminUser.value.trim();
  const password = adminPass.value;
  if (!username || !password) { adminErr.textContent = '请输入账号和密码'; return; }
  adminErr.textContent = '';
  adminLoginBtn.disabled = true;
  try {
    /* 账号密码登录：后端先查管理员表，再查用户绑定账号，任一命中即返回对应 role 的 token */
    const r = await fetch('api/auth/account-login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password })
    });
    const d = await r.json();
    if (!r.ok) { adminErr.textContent = d.detail || '登录失败'; return; }
    /* 用户账号需额外存 code 用于会话归属；管理员只存 username */
    const sessionUser = { role: d.role, username: d.username };
    if (d.role === 'user' && d.code) sessionUser.code = d.code;
    setSession(d.token, sessionUser);
    await enterApp();
  } catch (e) {
    adminErr.textContent = '网络错误，请重试';
  } finally {
    adminLoginBtn.disabled = false;
  }
}

inviteLoginBtn.addEventListener('click', () => doInviteLogin(inviteCode.value.trim()));
inviteCode.addEventListener('keydown', e => { if (e.key === 'Enter') doInviteLogin(inviteCode.value.trim()); });
adminLoginBtn.addEventListener('click', doAdminLogin);
adminPass.addEventListener('keydown', e => { if (e.key === 'Enter') doAdminLogin(); });

function doLogout() {
  clearSession();
  location.href = './';
}

/* 联系我们：点击复制邮箱并提示 */
document.getElementById('contactBtn').addEventListener('click', () => {
  const email = 'silver26719@gmail.com';
  const doCopy = () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(email).catch(() => copyFallback(email));
    } else {
      copyFallback(email);
    }
  };
  doCopy();
  toast('已复制邮箱 ' + email);
});
function copyFallback(text) {
  const t = document.createElement('textarea');
  t.value = text; document.body.appendChild(t); t.select();
  try { document.execCommand('copy'); } catch (e) {}
  t.remove();
}

/* ---------- 分享对话 ---------- */
function closeShareMenu() { shareMenu.style.display = 'none'; }
shareBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  const show = shareMenu.style.display === 'none';
  if (show) shareBtn.style.display = 'inline-flex';
  shareMenu.style.display = show ? 'block' : 'none';
});
document.addEventListener('click', (e) => {
  if (!shareMenu.contains(e.target) && e.target !== shareBtn) closeShareMenu();
});

async function getActiveMessages() {
  if (!activeConvId) return [];
  try {
    const r = await fetch('api/conversations/' + activeConvId + '/messages', { headers: authHeaders() });
    if (!r.ok) return [];
    const d = await r.json();
    return d.messages || [];
  } catch (e) { return []; }
}

/* 复制分享链接 */
shareLinkOpt.addEventListener('click', async () => {
  closeShareMenu();
  if (!activeConvId) { toast('还没有可分享的对话'); return; }
  try {
    const r = await fetch('api/conversations/' + activeConvId + '/share?avatar=' + getAvatarIdx(), {
      method: 'POST', headers: authHeaders()
    });
    const d = await r.json();
    if (!r.ok) { toast(d.detail || '分享失败'); return; }
    const url = location.origin + BASE + d.url;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(url);
    } else {
      const t = document.createElement('textarea');
      t.value = url; document.body.appendChild(t); t.select();
      document.execCommand('copy'); t.remove();
    }
    toast('分享链接已复制');
  } catch (e) { toast('网络错误'); }
});

/* 生成长图 */
shareImgOpt.addEventListener('click', async () => {
  closeShareMenu();
  if (!activeConvId) { toast('还没有可分享的对话'); return; }
  const msgs = await getActiveMessages();
  if (!msgs.length) { toast('还没有可分享的对话内容'); return; }
  const conv = conversations.find(c => c.id === activeConvId);
  await makeShareImage(msgs, (conv && conv.title) || '对话');
});

function loadHtml2canvas() {
  return new Promise((resolve, reject) => {
    if (window.html2canvas) return resolve(window.html2canvas);
    const s = document.createElement('script');
    s.src = 'html2canvas.min.js';
    s.onload = () => resolve(window.html2canvas);
    s.onerror = () => reject(new Error('load failed'));
    document.head.appendChild(s);
  });
}

function inlineLogoSvg(size) {
  return '<svg xmlns="http://www.w3.org/2000/svg" width="' + size + '" height="' + size + '" viewBox="40 55 315 300" fill="none">' +
    '<path d="M 179.41 100.91 C 171.84 101.60, 164.15 103.58, 157.06 106.40 C 149.98 109.23, 143.03 113.25, 136.90 117.85 C 130.76 122.46, 124.99 128.06, 120.24 134.04 C 115.50 140.02, 111.42 146.79, 108.43 153.74 C 105.44 160.70, 103.84 168.24, 102.32 175.75 C 100.80 183.26, 100.53 191.19, 99.31 198.81 C 98.08 206.43, 97.61 214.38, 94.96 221.46 C 92.31 228.53, 85.96 234.61, 83.42 241.24 C 80.89 247.86, 76.59 257.99, 79.75 261.22 C 82.92 264.45, 96.48 258.39, 102.42 260.61 C 108.36 262.83, 111.38 268.88, 115.41 274.54 C 119.44 280.20, 121.40 289.37, 126.59 294.55 C 131.79 299.72, 140.24 305.90, 146.59 305.59 C 152.95 305.28, 158.79 294.05, 164.73 292.69 C 170.67 291.32, 175.68 295.01, 182.22 297.40 C 188.76 299.80, 197.40 307.35, 203.97 307.06 C 210.53 306.77, 216.22 299.51, 221.61 295.68 C 227.00 291.85, 230.07 284.88, 236.32 284.08 C 242.57 283.28, 252.48 291.72, 259.12 290.87 C 265.76 290.02, 273.86 284.81, 276.16 278.99 C 278.46 273.16, 270.56 261.49, 272.93 255.91 C 275.29 250.34, 284.78 250.01, 290.35 245.53 C 295.92 241.06, 305.78 233.84, 306.37 229.06 C 306.97 224.29, 299.53 220.32, 293.92 216.89 C 288.31 213.47, 277.37 213.43, 272.73 208.50 C 268.10 203.57, 267.70 194.80, 266.10 187.33 C 264.51 179.86, 264.81 171.31, 263.18 163.69 C 261.56 156.07, 259.71 148.34, 256.35 141.62 C 252.99 134.91, 248.35 128.65, 243.03 123.38 C 237.70 118.11, 231.14 113.52, 224.39 110.00 C 217.64 106.48, 210.00 103.77, 202.50 102.25 C 195.00 100.74, 186.99 100.21, 179.41 100.91 Z" fill="#FDF7F0" stroke="#F6F1EA" stroke-width="16" stroke-linejoin="round"/>' +
    '<path d="M 179.41 100.91 C 171.84 101.60, 164.15 103.58, 157.06 106.40 C 149.98 109.23, 143.03 113.25, 136.90 117.85 C 130.76 122.46, 124.99 128.06, 120.24 134.04 C 115.50 140.02, 111.42 146.79, 108.43 153.74 C 105.44 160.70, 103.84 168.24, 102.32 175.75 C 100.80 183.26, 100.53 191.19, 99.31 198.81 C 98.08 206.43, 97.61 214.38, 94.96 221.46 C 92.31 228.53, 85.96 234.61, 83.42 241.24 C 80.89 247.86, 76.59 257.99, 79.75 261.22 C 82.92 264.45, 96.48 258.39, 102.42 260.61 C 108.36 262.83, 111.38 268.88, 115.41 274.54 C 119.44 280.20, 121.40 289.37, 126.59 294.55 C 131.79 299.72, 140.24 305.90, 146.59 305.59 C 152.95 305.28, 158.79 294.05, 164.73 292.69 C 170.67 291.32, 175.68 295.01, 182.22 297.40 C 188.76 299.80, 197.40 307.35, 203.97 307.06 C 210.53 306.77, 216.22 299.51, 221.61 295.68 C 227.00 291.85, 230.07 284.88, 236.32 284.08 C 242.57 283.28, 252.48 291.72, 259.12 290.87 C 265.76 290.02, 273.86 284.81, 276.16 278.99 C 278.46 273.16, 270.56 261.49, 272.93 255.91 C 275.29 250.34, 284.78 250.01, 290.35 245.53 C 295.92 241.06, 305.78 233.84, 306.37 229.06 C 306.97 224.29, 299.53 220.32, 293.92 216.89 C 288.31 213.47, 277.37 213.43, 272.73 208.50 C 268.10 203.57, 267.70 194.80, 266.10 187.33 C 264.51 179.86, 264.81 171.31, 263.18 163.69 C 261.56 156.07, 259.71 148.34, 256.35 141.62 C 252.99 134.91, 248.35 128.65, 243.03 123.38 C 237.70 118.11, 231.14 113.52, 224.39 110.00 C 217.64 106.48, 210.00 103.77, 202.50 102.25 C 195.00 100.74, 186.99 100.21, 179.41 100.91 Z" fill="#FDF7F0" stroke="#1D2233" stroke-width="7" stroke-linejoin="round"/>' +
    '<ellipse cx="137.75" cy="178.1" rx="11.5" ry="19.5" fill="#1F2434"/><ellipse cx="196.78" cy="179.06" rx="12" ry="19.5" fill="#1F2434"/>' +
    '<path d="M159 198 Q166 207 173 198" fill="none" stroke="#1F2434" stroke-width="6" stroke-linecap="round"/>' +
    '<g fill="none" stroke="#F6F1EA" stroke-width="7" stroke-linecap="round"><path d="M282 104 L289 88"/><path d="M299 117 L316 103"/><path d="M305 136 L322 135"/></g>' +
    '</svg>';
}
const USER_ICON_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
function msgText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    const parts = [];
    for (const c of content) {
      if (c && c.type === 'text') parts.push(c.text || '');
      else if (c && c.type === 'image_url') parts.push('〔图片〕');
    }
    return parts.join(' ');
  }
  return '';
}
function buildShareNode(msgs, title) {
  const root = document.createElement('div');
  root.className = 'share-node';
  root.style.cssText = 'position:fixed;left:-10000px;top:0;width:680px;background:#f4f5f7;z-index:-1;';
  let html =
    '<div class="share-head">' +
      inlineLogoSvg(34) +
      '<div class="share-brand">FixPilot</div>' +
      '<div class="share-tag">对话分享</div>' +
    '</div>' +
    '<div class="share-title">' + escapeHtml(title) + '</div>' +
    '<div class="share-sub">FixPilot 电脑故障排查助手</div>';
  for (const m of msgs) {
    const isBot = m.role !== 'user';
    const text = msgText(m.content);
    const memeId = isBot ? memeIdFromMessage(text) : null;
    if (memeId) {
      html += '<div class="msg bot meme-msg"><div class="avatar bot-avatar">' + inlineLogoSvg(38) + '</div><div class="bubble meme-card"><img class="meme-img" src="' + memeSrc(memeId) + '" alt="FixPilot meme" /></div><span class="msg-time">' + fmtMsgTime(m.created_at) + '</span></div>';
      continue;
    }
    let body;
    if (isBot) {
      body = mdToHtml(text);
    } else {
      body = (m.image ? '<img class="msg-img" src="' + m.image + '" alt="图片" />' : '') + '<p>' + escapeHtml(text) + '</p>';
    }
    html += '<div class="msg ' + (isBot ? 'bot' : 'user') + '">' +
      (isBot
        ? '<div class="avatar bot-avatar">' + inlineLogoSvg(38) + '</div>'
        : '') +
      '<div class="bubble">' + body + '</div>' +
      (isBot ? '' : '<div class="avatar user-avatar">' + USER_ICON_SVG + '</div>') +
      '<span class="msg-time">' + fmtMsgTime(m.created_at) + '</span>' +
    '</div>';
  }
  html += '<div class="share-foot">由 FixPilot 生成</div>';
  root.innerHTML = html;
  document.body.appendChild(root);
  return root;
}

async function makeShareImage(msgs, title) {
  let h2c;
  try { h2c = await loadHtml2canvas(); }
  catch (e) { toast('生成长图组件加载失败'); return; }
  const node = buildShareNode(msgs, title);
  try {
    const canvas = await h2c(node, { backgroundColor: '#f4f5f7', scale: 2, useCORS: true, logging: false });
    const a = document.createElement('a');
    a.download = 'FixPilot对话_' + Date.now() + '.png';
    a.href = canvas.toDataURL('image/png');
    document.body.appendChild(a);
    a.click();
    a.remove();
    toast('长图已生成');
  } catch (e) {
    toast('生成长图失败');
  } finally {
    node.remove();
  }
}

/* ---------- 邀请码管理面板（整页弹窗） ---------- */
const adminModal = document.getElementById('adminModal');
const adminBody = document.getElementById('adminBody');
document.getElementById('adminBtn').addEventListener('click', openAdminModal);
document.getElementById('adminClose').addEventListener('click', closeAdminModal);
adminModal.addEventListener('click', e => { if (e.target === adminModal) closeAdminModal(); });

function openAdminModal() {
  adminBody.innerHTML = adminBodyHtml();
  bindAdminEvents();
  loadInvites();
  adminModal.style.display = 'flex';
}
function closeAdminModal() { adminModal.style.display = 'none'; }

function adminBodyHtml() {
  return '' +
    '<div class="acard">' +
      '<div class="acard-title">生成邀请码</div>' +
      '<div class="aform">' +
        '<label class="arow"><input type="checkbox" id="aqtyOn" checked /><span>次数限制</span><input class="anum" id="aqty" type="number" value="50" min="1" /></label>' +
        '<label class="arow"><input type="checkbox" id="aexpOn" checked /><span>有效期</span><input class="anum" id="aexpVal" type="number" value="3" min="1" /><select id="aexpUnit"><option value="days" selected>天</option><option value="hours">小时</option></select></label>' +
        '<label class="arow"><span>数量</span><input class="anum" id="acount" type="number" value="1" min="1" max="50" /></label>' +
        '<label class="arow grow"><span>备注</span><input id="anote" placeholder="给朋友1 / 张三等" /></label>' +
      '</div>' +
      '<div class="aactions"><button class="a-btn" id="aGen">生成</button></div>' +
      '<div class="agen-result" id="agenResult"></div>' +
    '</div>' +
    '<div class="acard"><div class="acard-title">未使用邀请码 <span class="abadge" id="aUnusedCount"></span></div><div id="aUnusedList"></div></div>' +
    '<div class="acard"><div class="acard-title">已使用邀请码 <span class="abadge" id="aUsedCount"></span></div><div id="aUsedList"></div></div>';
}

function bindAdminEvents() {
  document.getElementById('aGen').addEventListener('click', createInvites);
}

async function createInvites() {
  const qtyOn = document.getElementById('aqtyOn').checked;
  const expOn = document.getElementById('aexpOn').checked;
  const qty = qtyOn ? (parseInt(document.getElementById('aqty').value) || 50) : -1;
  const expVal = parseInt(document.getElementById('aexpVal').value) || 0;
  const expUnit = document.getElementById('aexpUnit').value;
  const hours = expOn && expVal > 0 ? (expUnit === 'days' ? expVal * 24 : expVal) : null;
  const count = parseInt(document.getElementById('acount').value) || 1;
  const note = document.getElementById('anote').value.trim();
  try {
    const r = await fetch('api/admin/invites', {
      method: 'POST', headers: authHeaders(), body: JSON.stringify({ quota: qty, count, hours, note })
    });
    const d = await r.json();
    if (!r.ok) { toast(d.detail || '生成失败'); return; }
    document.getElementById('agenResult').innerHTML = '<div class="agen-codes">新邀请码：' +
      d.codes.map(c => '<code class="acode" onclick="copyCode(\'' + c.code + '\')">' + c.code + '</code>').join('') + '</div>';
    document.getElementById('anote').value = '';
    loadInvites();
  } catch (e) { toast('网络错误'); }
}

async function loadInvites() {
  try {
    const r = await fetch('api/admin/invites', { headers: authHeaders() });
    const d = await r.json();
    renderInvites(d.invites || []);
  } catch (e) {}
}

function fmtExp(exp) {
  if (!exp) return '长期';
  const d = new Date(exp);
  return (d.getMonth() + 1) + '/' + d.getDate() + ' ' + d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
}
function fmtLogin(l) {
  if (!l) return '从未登录';
  const d = new Date(l);
  return (d.getMonth() + 1) + '/' + d.getDate() + ' ' + d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
}
function quotaText(iv) {
  return iv.quota_total === -1 ? '不限' : (iv.quota_used + '/' + iv.quota_total);
}
function statusTag(iv) {
  if (iv.expired) return '<span class="atag atag-expired">已过期</span>';
  if (iv.quota_total === -1) return '<span class="atag atag-unlimited">不限次</span>';
  if (iv.remaining <= 0) return '<span class="atag atag-exhausted">已用完</span>';
  return '<span class="atag atag-ok">可用 ' + iv.remaining + '</span>';
}

function renderInvites(invites) {
  const unused = invites.filter(iv => !iv.used);
  const used = invites.filter(iv => iv.used);
  document.getElementById('aUnusedCount').textContent = unused.length;
  document.getElementById('aUsedCount').textContent = used.length;
  renderUnused(unused);
  renderUsed(used);
}

function renderUnused(list) {
  const box = document.getElementById('aUnusedList');
  if (!list.length) { box.innerHTML = '<div class="aempty">暂无未使用的邀请码</div>'; return; }
  let html = '<table class="atable"><thead><tr><th>邀请码</th><th>次数</th><th>有效期</th><th>备注</th><th>操作</th></tr></thead><tbody>';
  for (const iv of list) {
    html += '<tr>' +
      '<td class="acode">' + iv.code + '</td>' +
      '<td>' + quotaText(iv) + '</td>' +
      '<td>' + fmtExp(iv.expires_at) + '</td>' +
      '<td>' + (iv.note ? escapeHtml(iv.note) : '') + '</td>' +
      '<td><button class="amini" onclick="copyCode(\'' + iv.code + '\')">复制</button>' +
      '<button class="amini" onclick="copyShareText(\'' + iv.code + '\')">分享文案</button></td>' +
      '</tr>';
  }
  box.innerHTML = html + '</tbody></table>';
}

function renderUsed(list) {
  const box = document.getElementById('aUsedList');
  if (!list.length) { box.innerHTML = '<div class="aempty">暂无已使用的邀请码</div>'; return; }
  let html = '<table class="atable"><thead><tr><th>邀请码</th><th>次数</th><th>有效期</th><th>最近登录</th><th>状态</th><th>操作</th></tr></thead><tbody>';
  for (const iv of list) {
    html += '<tr>' +
      '<td class="acode">' + iv.code + '</td>' +
      '<td>' + quotaText(iv) + '</td>' +
      '<td>' + fmtExp(iv.expires_at) + '</td>' +
      '<td>' + fmtLogin(iv.last_login_at) + '</td>' +
      '<td>' + statusTag(iv) + '</td>' +
      '<td><button class="amini" onclick="addQuota(\'' + iv.code + '\')">+次数</button>' +
      '<button class="amini" onclick="addHours(\'' + iv.code + '\')">+时间</button>' +
      '<button class="amini" onclick="showHistory(\'' + iv.code + '\')">历史</button>' +
      '<button class="amini danger" onclick="delInvite(\'' + iv.code + '\')">删除</button></td>' +
      '</tr>';
  }
  box.innerHTML = html + '</tbody></table>';
}

async function addQuota(code) {
  const v = prompt('追加次数（输入正整数）');
  if (v === null) return;
  const n = parseInt(v);
  if (!n || n <= 0) { toast('无效次数'); return; }
  const r = await fetch('api/admin/invites/' + code + '/update', {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ addQuota: n })
  });
  if (r.ok) { toast('已追加 ' + n + ' 次'); loadInvites(); } else toast('操作失败');
}
async function addHours(code) {
  const v = prompt('追加有效期（小时数）');
  if (v === null) return;
  const n = parseInt(v);
  if (!n || n <= 0) { toast('无效小时数'); return; }
  const r = await fetch('api/admin/invites/' + code + '/update', {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ addHours: n })
  });
  if (r.ok) { toast('已延长 ' + n + ' 小时'); loadInvites(); } else toast('操作失败');
}
async function delInvite(code) {
  if (!confirm('确定删除邀请码 ' + code + ' 吗？')) return;
  const r = await fetch('api/admin/invites/' + code, { method: 'DELETE', headers: authHeaders() });
  if (r.ok) { toast('已删除'); loadInvites(); } else toast('操作失败');
}

async function showHistory(code) {
  const prev = adminBody.innerHTML;
  adminBody.innerHTML = '<div class="acard-title">邀请码 ' + code + ' 的对话历史</div><div id="aHistoryBody"><div class="aempty">加载中...</div></div>' +
    '<div class="aactions"><button class="a-btn ghost" id="aBack">返回</button></div>';
  document.getElementById('aBack').addEventListener('click', () => { adminBody.innerHTML = prev; bindAdminEvents(); });
  try {
    const r = await fetch('api/admin/invites/' + code + '/conversations', { headers: authHeaders() });
    const d = await r.json();
    const convs = d.conversations || [];
    const hb = document.getElementById('aHistoryBody');
    if (!convs.length) { hb.innerHTML = '<div class="aempty">该邀请码还没有对话</div>'; return; }
    let html = '';
    for (const c of convs) {
      html += '<div class="ahist-conv">' + escapeHtml(c.conv.title) + '</div>';
      for (const m of c.messages) {
        html += '<div class="ahist-msg ' + (m.role === 'user' ? 'user' : 'bot') + '"><span class="ahist-role">' +
          (m.role === 'user' ? '用户' : '助手') + '</span><div>' + escapeHtml(m.content) + '</div></div>';
      }
    }
    hb.innerHTML = html;
  } catch (e) {
    document.getElementById('aHistoryBody').innerHTML = '<div class="aempty">加载失败</div>';
  }
}

async function copyCode(code) {
  try { await navigator.clipboard.writeText(code); toast('已复制 ' + code); }
  catch (e) { fallbackCopy(code, () => toast('已复制 ' + code)); }
}
function copyShareText(code) {
  const url = location.origin + BASE + '/?code=' + code;
  const text = '我正在邀请你使用 FixPilot 电脑故障排查助手，你的邀请码是：' + code + '，点击链接即可自动填入并登录：' + url;
  fallbackCopy(text, () => toast('分享文案已复制'));
}
function fallbackCopy(text, done) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => { const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select(); try { document.execCommand('copy'); done(); } catch (e) { toast('复制失败'); } t.remove(); });
  } else {
    const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select();
    try { document.execCommand('copy'); done(); } catch (e) { toast('复制失败'); }
    t.remove();
  }
}

/* 进入主界面：校验 token，加载会话 */
async function enterApp() {
  const user = getUser();
  if (!user) { showLogin(); return; }
  try {
    const r = await fetch('api/auth/me', { headers: authHeaders() });
    if (!r.ok) {
      clearSession(); showLogin(); return;
    }
    const me = await r.json();
    useProfile(me.profile);
    /* 同步身份与绑定状态到全局，供提示条与收藏逻辑使用 */
    currentRole = me.role;
    boundUsername = me.bound_username || null;
    bindBannerShown = false;
    bindBannerDismissed = false;
    document.getElementById('bindBanner').style.display = 'none';
    initFavIcon();
    updateModelPicker();
    if (me.role === 'admin') {
      document.getElementById('adminBtn').style.display = 'inline-flex';
      document.getElementById('quotaWrap').style.display = 'none';
      await loadConversations();
      showApp();
      return;
    }
    document.getElementById('adminBtn').style.display = 'none';
    canUse = me.role === 'admin' ? true : me.can_use;
    currentUser = me;
    updateQuotaBadge(me);
    await loadConversations();
    showApp();
    if (!canUse) showQuotaBlock();
  } catch (e) {
    showLogin();
  }
}

function updateQuotaBadge(me) {
  const wrap = document.getElementById('quotaWrap');
  const quotaExp = document.getElementById('quotaExp');
  // 管理员或无额度字段时隐藏剩余次数标签，避免显示 NaN
  if (!me || me.role === 'admin' || me.quota_total == null) {
    wrap.style.display = 'none';
    return;
  }
  // 检测到自定义 API 时隐藏次数显示
  if (getApiSettings()) {
    wrap.style.display = 'none';
    return;
  }
  const total = me.quota_total;
  wrap.style.display = 'inline-flex';
  if (total === -1) {
    quotaBadge.textContent = '不限次数';
  } else {
    quotaBadge.textContent = '剩余 ' + Math.max(0, total - me.quota_used) + ' 次';
  }
  quotaExp.textContent = me.expires_at ? fmtExpDate(me.expires_at) + ' 到期' : '长期有效';
}
function fmtExpDate(exp) {
  const d = new Date(exp);
  return (d.getMonth() + 1) + '/' + d.getDate() + ' ' + d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
}

function showQuotaBlock() {
  if (chatEl.querySelector('.quota-block')) return;
  // 不清空对话，只在对话末尾追加一条提示
  const reason = (currentUser && currentUser.reason) || '';
  const isExpired = reason === 'expired';
  const title = isExpired ? '使用期限已到' : '次数已用完';
  const hint = isExpired
    ? '当前邀请码已过期，可在右上角设置中填入自己的 API Key 继续使用。'
    : '当前邀请码次数已用完，可在右上角设置中填入自己的 API Key 继续使用。';
  const wrap = document.createElement('div');
  wrap.className = 'quota-block';
  wrap.innerHTML = '<p><strong>' + title + '</strong></p>' +
    '<p>' + hint + '</p>' +
    '<p class="quota-contact">联系我们：<a class="contact-link" href="mailto:silver26719@gmail.com">silver26719@gmail.com</a></p>';
  chatEl.appendChild(wrap);
}

/* ---------- 会话列表 ---------- */
async function loadConversations() {
  try {
    const r = await fetch('api/conversations', { headers: authHeaders() });
    if (!r.ok) return;
    const d = await r.json();
    conversations = d.conversations || [];
    renderList();
    if (conversations.length) {
      activeConvId = conversations[0].id;
      await openConversation(activeConvId);
    } else {
      await newConversation();
    }
  } catch (e) {}
}

async function newConversation() {
  if (busy) return;
  try {
    const r = await fetch('api/conversations', {
      method: 'POST', headers: authHeaders(), body: JSON.stringify({ title: '新对话' })
    });
    const d = await r.json();
    const c = { id: d.id, title: '新对话' };
    conversations.unshift(c);
    activeConvId = c.id;
    renderList();
    renderWelcome();
    closeDrawer();
  } catch (e) {}
}

async function openConversation(id) {
  activeConvId = id;
  renderList();
  closeDrawer();
  try {
    const r = await fetch('api/conversations/' + id + '/messages', { headers: authHeaders() });
    const d = await r.json();
    const msgs = d.messages || [];
    if (!msgs.length) { renderWelcome(); return; }
    chatEl.innerHTML = '';
    lastMsgTime = null;
    msgs.forEach(m => {
      const isBot = m.role !== 'user';
      const memeId = isBot ? memeIdFromMessage(m.content) : null;
      if (memeId) { addMemeMsg(memeId, m.created_at); return; }
      maybeDivider(m.created_at);
      const div = document.createElement('div');
      div.className = 'msg ' + (isBot ? 'bot' : 'user');
      if (isBot) div.appendChild(botAvatar());
      const bubble = document.createElement('div');
      bubble.className = 'bubble';
      div.appendChild(bubble);
      if (m.role === 'user') div.appendChild(userAvatar());
      if (isBot) renderBotMsg(div, m.content); else renderUserMsg(div, m.content, m.image || null);
      addMsgTime(div, m.created_at);
      chatEl.appendChild(div);
    });
    scrollDown(false);
  } catch (e) {}
}

async function deleteConversation(id, e) {
  e.stopPropagation();
  if (busy) return;
  try {
    await fetch('api/conversations/' + id, { method: 'DELETE', headers: authHeaders() });
    conversations = conversations.filter(c => c.id !== id);
    if (activeConvId === id) {
      activeConvId = conversations.length ? conversations[0].id : null;
      if (activeConvId) await openConversation(activeConvId);
      else await newConversation();
    }
    renderList();
  } catch (e) {}
}

function renderList() {
  convList.innerHTML = '';
  if (!conversations.length) return;
  conversations.forEach(c => {
    const item = document.createElement('div');
    item.className = 'conv-item' + (c.id === activeConvId ? ' active' : '');
    const title = document.createElement('span');
    title.className = 'conv-title';
    title.textContent = c.title;
    title.title = c.title;
    const del = document.createElement('button');
    del.className = 'conv-del';
    del.setAttribute('aria-label', '删除');
    del.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    del.addEventListener('click', (e2) => deleteConversation(c.id, e2));
    item.addEventListener('click', (e2) => { if (e2.target.closest('.conv-del')) return; openConversation(c.id); });
    item.appendChild(title);
    item.appendChild(del);
    convList.appendChild(item);
  });
}

/* ---------- 标题生成 ---------- */
async function genTitle(convId, question) {
  try {
    const d = await fetch('api/title', {
      method: 'POST', headers: authHeaders(), body: JSON.stringify({ question, convId })
    });
    const r = await d.json();
    const c = conversations.find(x => x.id === convId);
    if (c && r.title) { c.title = r.title; renderList(); }
  } catch (e) {}
}

/* ---------- 侧边栏（移动端抽屉） ---------- */
function openDrawer() { sidebar.classList.add('open'); scrim.classList.add('show'); }
function closeDrawer() { sidebar.classList.remove('open'); scrim.classList.remove('show'); }
menuBtn.addEventListener('click', openDrawer);
scrim.addEventListener('click', closeDrawer);
newChatBtn.addEventListener('click', newConversation);

/* ---------- 轻量 Markdown 渲染 ---------- */
function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function inline(s) {
  s = escapeHtml(s);
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  return s;
}
function mdToHtml(text) {
  const parts = text.split(/```/);
  let html = '';
  for (let i = 0; i < parts.length; i++) {
    if (i % 2 === 1) {
      html += '<pre><code>' + escapeHtml(parts[i].replace(/^[a-zA-Z]+\n/, '')) + '</code></pre>';
    } else {
      html += mdBlock(parts[i]);
    }
  }
  return html;
}
function mdBlock(src) {
  const lines = src.split('\n');
  let out = ''; let inList = false; let listType = '';
  const closeList = () => { if (inList) { out += '</' + listType + '>'; inList = false; } };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { closeList(); continue; }
    let m;
    if ((m = line.match(/^(#{1,6})\s+(.*)/))) {
      closeList();
      const lvl = m[1].length;
      out += '<h' + lvl + '>' + inline(m[2]) + '</h' + lvl + '>';
    } else if (/^[-*]\s+/.test(line)) {
      if (!inList) { inList = true; listType = 'ul'; out += '<ul>'; }
      out += '<li>' + inline(line.replace(/^[-*]\s+/, '')) + '</li>';
    } else if (/^>\s?/.test(line)) {
      closeList();
      out += '<blockquote>' + inline(line.replace(/^>\s?/, '')) + '</blockquote>';
    } else if ((m = line.match(/^\d+[.、)]\s*(.*)/))) {
      if (!inList) { inList = true; listType = 'ol'; out += '<ol>'; }
      out += '<li>' + inline(m[1]) + '</li>';
    } else {
      closeList();
      out += '<p>' + inline(line) + '</p>';
    }
  }
  closeList();
  return out;
}

/* ---------- DOM ---------- */
function botAvatar() {
  const a = document.createElement('div');
  a.className = 'avatar bot-avatar';
  a.setAttribute('aria-hidden', 'true');
  a.innerHTML = '<img src="logo.svg?v=2" alt="" />';
  return a;
}
function userAvatar() {
  const a = document.createElement('div');
  a.className = 'avatar user-avatar';
  a.setAttribute('aria-hidden', 'true');
  a.innerHTML = '<img src="' + avatarUrl() + '" alt="" />';
  return a;
}
const WELCOME_HTML =
  '<div class="welcome">' +
    '<div class="hero">' +
      '<img class="hero-logo" src="logo.svg?v=2" alt="FixPilot" />' +
      '<div class="hero-title">FixPilot</div>' +
      '<div class="hero-sub">电脑故障排查、快速定位、一键解决</div>' +
    '</div>' +
    '<div class="msg bot">' +
      '<div class="avatar bot-avatar" aria-hidden="true"><img src="logo.svg?v=2" alt="" /></div>' +
      '<div class="bubble"><p>你好，我是 <strong>FixPilot</strong>。描述一下你遇到的电脑问题，我会帮你逐步定位故障并给出解决办法。</p>' +
      '<p>比如：<em>开机黑屏但风扇在转</em>、<em>游戏经常闪退</em>、<em>电脑没声音</em>。</p></div>' +
    '</div>' +
    '<div class="chips">' +
      '<button class="chip" data-q="游戏经常闪退怎么办">游戏经常闪退</button>' +
      '<button class="chip" data-q="开机黑屏，但风扇在转">开机黑屏</button>' +
      '<button class="chip" data-q="电脑鼠标卡顿漂移">鼠标卡顿</button>' +
      '<button class="chip" data-q="电脑没有声音">没有声音</button>' +
    '</div>' +
  '</div>';

function onboardingStep() {
  const p = currentProfile || defaultProfile();
  if (p.onboarding_completed) return '';
  if (p.technical_level !== 'unknown' && p.technical_level_source === 'explicit') return 'style';
  if (p.technical_level === 'unknown' && !p.onboarding_seen) return 'level';
  return '';
}
function levelGuideHtml() {
  return '<div class="welcome onboarding-guide onboarding-first" data-step="level">' +
    '<div class="hero"><img class="hero-logo" src="logo.svg?v=2" alt="FixPilot" />' +
    '<div class="hero-title">先让我了解一下你。</div><div class="hero-sub">这样我知道该讲多细。</div></div>' +
    '<div class="onboarding-cards">' +
      '<button class="onboarding-card" data-level="beginner"><strong>不太懂</strong><span>出问题一般靠教程</span></button>' +
      '<button class="onboarding-card" data-level="intermediate"><strong>会折腾一点</strong><span>重装、驱动这些能自己搞</span></button>' +
      '<button class="onboarding-card" data-level="advanced"><strong>比较熟</strong><span>BIOS、硬件排查也接触过</span></button>' +
    '</div><button class="onboarding-direct" type="button">直接问我也可以 →</button>' +
    '<div class="onboarding-nudge" aria-live="polite"></div></div>';
}
function styleGuideHtml() {
  return '<div class="welcome onboarding-guide" data-step="style">' +
    '<div class="hero"><img class="hero-logo" src="logo.svg?v=2" alt="FixPilot" />' +
    '<div class="hero-title">最后一个，你喜欢我怎么说话？</div><div class="hero-sub">以后随时可以改。</div></div>' +
    '<div class="onboarding-cards">' +
      '<button class="onboarding-card" data-style="normal"><strong>正常点</strong><span>正常解释，靠谱解决</span></button>' +
      '<button class="onboarding-card" data-style="roast"><strong>嘴毒点</strong><span>电脑认真修，嘴上不一定饶你</span></button>' +
      '<button class="onboarding-card" data-style="concise"><strong>少废话</strong><span>直接结论 + 操作步骤</span></button>' +
    '</div><button class="onboarding-direct" type="button">直接问我也可以 →</button></div>';
}
async function saveProfilePreference(payload) {
  const r = await fetch('api/profile/preferences', {
    method: 'POST', headers: authHeaders(), body: JSON.stringify(payload)
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || '保存失败');
  useProfile(d.profile);
}
function bindOnboardingGuide() {
  const guide = chatEl.querySelector('.onboarding-guide');
  if (!guide) return;
  guide.addEventListener('click', async e => {
    const level = e.target.closest('[data-level]');
    const style = e.target.closest('[data-style]');
    const direct = e.target.closest('.onboarding-direct');
    if (direct) { input.focus(); return; }
    if (!level && !style) return;
    guide.querySelectorAll('button').forEach(button => { button.disabled = true; });
    try {
      if (level) await saveProfilePreference({ technicalLevel: level.dataset.level, onboardingSeen: true });
      if (style) await saveProfilePreference({ responseStyle: style.dataset.style, onboardingCompleted: true, onboardingSeen: true });
      renderWelcome();
    } catch (err) {
      toast(err.message || '保存失败，请重试');
      guide.querySelectorAll('button').forEach(button => { button.disabled = false; });
    }
  });
}
async function showOnboardingNudge() {
  const guide = chatEl.querySelector('.onboarding-guide[data-step="level"]');
  const p = currentProfile || defaultProfile();
  if (!guide || p.onboarding_nudge_shown) return;
  guide.classList.add('nudging');
  const note = guide.querySelector('.onboarding-nudge');
  if (note) note.textContent = '选一下，我能少说很多你不需要听的东西。';
  try {
    const r = await fetch('api/profile/onboarding-nudge', { method: 'POST', headers: authHeaders() });
    const d = await r.json();
    if (r.ok) useProfile(d.profile);
  } catch (e) {}
}
function renderWelcome() {
  const step = onboardingStep();
  chatEl.innerHTML = step === 'level' ? levelGuideHtml() : (step === 'style' ? styleGuideHtml() : WELCOME_HTML);
  if (step) bindOnboardingGuide();
  else {
    chatEl.querySelector('.chips').addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (chip) { input.value = chip.dataset.q; send(); }
    });
  }
  scrollDown(false);
}
input.addEventListener('focus', showOnboardingNudge);

/* ---------- 选项按钮 ---------- */
const MAX_CLICKABLE_OPTIONS = 4;

/*
 * Options are the only model output rendered as controls. Prefer the strict
 * marker protocol, then conservatively recover legacy numbered choice lists.
 * Ordinary numbered instructions must remain ordinary text.
 */
function extractNumberedOptionBlock(source) {
  const re = /(?:^|\n)[ \t]*(\d{1,2})[.\u3001)]\s+([^\n]*)/g;
  let best = null;
  let current = null;
  let match;
  while ((match = re.exec(source))) {
    const number = Number(match[1]);
    const start = match.index;
    const end = match.index + match[0].length;
    const item = (match[2] || '').trim();
    const isAdjacent = current && /^\s*$/.test(source.slice(current.end, start));
    if (number === 1) {
      if (current && current.items.length >= 2 && (!best || current.items.length > best.items.length)) best = current;
      current = { start, end, items: [item] };
    } else if (current && isAdjacent && number === current.items.length + 1) {
      current.items.push(item);
      current.end = end;
    } else {
      if (current && current.items.length >= 2 && (!best || current.items.length > best.items.length)) best = current;
      current = null;
    }
  }
  if (current && current.items.length >= 2 && (!best || current.items.length > best.items.length)) best = current;
  return best;
}

function mergeBrokenOptionFragments(items) {
  const merged = [];
  for (const raw of items) {
    const item = raw.trim();
    const previous = merged[merged.length - 1];
    const looksLikeContinuation = previous && /^[.\u3002\u2026\uff0c,\u3001\uff1b;:\uff1a\uff09\]\u3011}]/.test(item);
    if (!looksLikeContinuation) {
      if (item) merged.push(item);
      continue;
    }
    /* A model can rarely split a value such as 0xc... into a fake next item. */
    if (/0x[\da-f]*$/i.test(previous) && /^[.\u3002\u2026]+/.test(item)) {
      merged[merged.length - 1] = previous + '...' + item.replace(/^[.\u3002\u2026]+/, '');
    } else {
      merged[merged.length - 1] = previous + item;
    }
  }
  return merged;
}

function parseOptions(text) {
  const marker = text.match(/(?:^|\n)\s*\u9009\u9879\s*[:\uff1a]/);
  let source = text;
  let prefix = '';
  let strict = false;
  if (marker) {
    strict = true;
    prefix = text.slice(0, marker.index).trim();
    source = text.slice(marker.index + marker[0].length);
  }

  const block = extractNumberedOptionBlock(source);
  if (!block) return { main: text, options: [] };

  const suffix = source.slice(block.end).trim();
  if (!strict) {
    const context = source.slice(Math.max(0, block.start - 280), block.start);
    const hasQuestion = /[\uff1f?]/.test(context);
    const hasChoiceCue = /(?:\u6311(?:\u4e00|\u4e2a)|\u9009(?:\u4e00|\u4e2a|\u62e9)|\u54ea(?:\u79cd|\u4e00\u9879|\u4e2a)|\u6700\u8d34\u8fd1|\u66f4\u63a5\u8fd1|\u544a\u8bc9\u6211|\u56de\u590d(?:\u6211|\u5bf9\u5e94)?|\u6709\u6ca1\u6709|\u662f\u5426)/.test(context + suffix);
    const looksLikeProcedure = /(?:\u6309(?:\u7167|\u4ee5\u4e0b|\u4e0b\u9762)|\u64cd\u4f5c\u6b65\u9aa4|\u4f9d\u6b21|\u6b65\u9aa4\u5982\u4e0b)/.test(context);
    if (!hasQuestion || !hasChoiceCue || looksLikeProcedure) return { main: text, options: [] };
    prefix = source.slice(0, block.start).trim();
  }

  const options = mergeBrokenOptionFragments(block.items).slice(0, MAX_CLICKABLE_OPTIONS);
  if (options.length < 2) return { main: text, options: [] };
  const main = [prefix, suffix].filter(Boolean).join('\n\n');
  return { main, options };
}

function isGenericOption(option) {
  return /^(?:\u5176\u4ed6|\u5176\u5b83|\u90fd\u4e0d\u662f|\u4ee5\u4e0a\u5747\u4e0d\u662f|\u6211\u6765\u63cf\u8ff0|\u81ea\u5df1\u63cf\u8ff0|\u624b\u52a8\u8f93\u5165|\u81ea\u5b9a\u4e49)/.test(option.trim());
}
/* 把紧跟在文字后、同行连写的编号步骤拆到新行，保留已有空行，便于排版 */
function breakNumbered(text) {
  /* 前导空格/字符保留原样，但空格不单独成行，避免打断 ol */
  return text.replace(/([^\n])(\d+[.、)])(?!\d)/g, (_, before, num) =>
    before.trim() ? before + '\n' + num : '\n' + num
  );
}
function renderBotMsg(div, text) {
  const { main, options } = parseOptions(text);
  const bubble = div.querySelector('.bubble');
  bubble.innerHTML = mdToHtml(breakNumbered(main));
  let wrap = div.querySelector('.opts');
  if (wrap) wrap.remove();
  if (options.length) {
    wrap = document.createElement('div');
    wrap.className = 'opts';
    options.forEach(o => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'opt';
      b.textContent = o;
      /* 泛化选项（如"其他问题""我来描述"）视为"其他"入口，聚焦输入框而非发送，避免浪费 token */
      const isGeneric = isGenericOption(o);
      b.addEventListener('click', () => {
        collapseOpts(wrap);
        if (isGeneric) {
          input.placeholder = '输入你的情况...';
          input.focus();
        } else {
          input.value = o;
          send();
        }
      });
      wrap.appendChild(b);
    });
    if (!options.some(isGenericOption)) {
      const otherBtn = document.createElement('button');
    otherBtn.type = 'button';
    otherBtn.className = 'opt other';
    otherBtn.textContent = '其他';
    otherBtn.addEventListener('click', () => {
      collapseOpts(wrap);
      input.placeholder = '输入你的情况...';
      input.focus();
    });
      wrap.appendChild(otherBtn);
    }
    div.appendChild(wrap);
  }
}
function collapseOpts(wrap) {
  if (!wrap) return;
  wrap.classList.add('collapsing');
  wrap.addEventListener('animationend', () => wrap.remove(), { once: true });
}
function addTyping() {
  const div = document.createElement('div');
  div.className = 'msg bot';
  div.appendChild(botAvatar());
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
  div.appendChild(bubble);
  chatEl.appendChild(div);
  scrollDown();
  return div;
}
function showJoke6(bubble) {
  /* 阶段 1：显示"对方正在输入中..."，点从 1 个递增到 6 个，持续 2 秒 */
  bubble.innerHTML = '<span class="typing-text">对方正在输入中</span><span class="typing-dots">.</span>';
  const dotsEl = bubble.querySelector('.typing-dots');
  let count = 1;
  const dotTimer = setInterval(() => {
    count = (count % 6) + 1;
    dotsEl.textContent = '.'.repeat(count);
  }, 333);
  /* 阶段 2：2 秒后换成正常字号的 "6" */
  setTimeout(() => {
    clearInterval(dotTimer);
    bubble.innerHTML = '<p>6</p>';
  }, 2000);
}
const MEME_ASSETS = Object.freeze({
  you_ok: '\u4f60\u6ca1\u4e8b\u5427.png',
  sick: '\u4f60\u75c5\u5f97\u4e0d\u8f7b.png',
  head_hold: '\u62b1\u5934\u65e0\u5948.png',
  face_cover: '\u6342\u8138\u65e0\u5948.png',
  awkward_laugh: '\u5c2c\u7b11\u65e0\u5948.png',
  sweat: '\u6d41\u6c57\u65e0\u5948.png',
  sweat_2: '\u6d41\u6c57\u65e0\u59482.png',
  cool_gun: '\u51b7\u9177\u6301\u67aa\u6307\u7740\u5bf9\u65b9.png',
  stop_bothering: '\u80fd\u522b\u6574\u6211\u4e86\u4e0d\uff1f.png'
});
function memeIdFromMessage(content) {
  const match = typeof content === 'string' && content.trim().match(/^\[MEME:([a-z_]+)\]$/);
  return match && Object.prototype.hasOwnProperty.call(MEME_ASSETS, match[1]) ? match[1] : null;
}
function memeSrc(memeId) {
  return 'memes/' + memeId + '.png';
}
function renderMemeMsg(div, memeId) {
  const filename = MEME_ASSETS[memeId];
  if (!filename) return false;
  const bubble = div.querySelector('.bubble');
  div.classList.add('meme-msg');
  bubble.className = 'bubble meme-card';
  bubble.textContent = '';
  const img = document.createElement('img');
  img.className = 'meme-img';
  img.src = memeSrc(memeId);
  img.alt = 'FixPilot meme';
  img.decoding = 'async';
  bubble.appendChild(img);
  return true;
}
function addMemeMsg(memeId, iso) {
  maybeDivider(iso);
  const div = document.createElement('div');
  div.className = 'msg bot meme-msg';
  div.appendChild(botAvatar());
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  div.appendChild(bubble);
  renderMemeMsg(div, memeId);
  addMsgTime(div, iso);
  chatEl.appendChild(div);
  scrollDown();
  return div;
}
function showJokeEffect(msgEl, effect) {
  if (effect && effect.kind === 'meme' && renderMemeMsg(msgEl, effect.meme)) {
    addMsgTime(msgEl);
    scrollDown();
    return;
  }
  showJoke6(msgEl.querySelector('.bubble'));
}
function jokeEffectDelay(effect) {
  return effect && effect.kind === 'meme' ? 1150 : 3500;
}

/* 时间戳：气泡右下角弱化小字（今天只显示时分，跨天带日期） */
function fmtMsgTime(iso) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  if (d.toDateString() === new Date().toDateString()) return hh + ':' + mm;
  return (d.getMonth() + 1) + '月' + d.getDate() + '日 ' + hh + ':' + mm;
}
function addMsgTime(container, iso) {
  if (!container || container.querySelector('.msg-time')) return;
  const t = document.createElement('span');
  t.className = 'msg-time';
  t.textContent = fmtMsgTime(iso) || fmtMsgTime(new Date().toISOString());
  container.appendChild(t);
}

/* 时间分隔条：间隔超过阈值时，在消息前插入居中的淡色时间条 */
const DIVIDER_MS = 5 * 60 * 1000;
let lastMsgTime = null;
function fmtDividerTime(d) {
  const pad = n => String(n).padStart(2, '0');
  const hm = pad(d.getHours()) + ':' + pad(d.getMinutes());
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return hm;
  const y = new Date(now);
  y.setDate(now.getDate() - 1);
  if (d.toDateString() === y.toDateString()) return '\u6628\u5929 ' + hm;
  return (d.getMonth() + 1) + '\u6708' + d.getDate() + '\u65e5 ' + hm;
}
function maybeDivider(iso) {
  const t = new Date(iso || Date.now());
  if (lastMsgTime && (t - lastMsgTime) >= DIVIDER_MS) {
    const d = document.createElement('div');
    d.className = 'time-divider';
    d.textContent = fmtDividerTime(t);
    chatEl.appendChild(d);
  }
  lastMsgTime = t;
}
function scrollDown(anim = true) { chatEl.scrollTop = chatEl.scrollHeight; }
function autoResize() {
  input.style.height = 'auto';
  input.style.height = input.scrollHeight + 'px'; /* 不设上限，超高时整体向上顶，无滚动条 */
}

/* ---------- 图片上传 ---------- */
const imgInput = document.getElementById('imgInput');
const imgBtn = document.getElementById('imgBtn');
const imgPreview = document.getElementById('imgPreview');
const previewImg = document.getElementById('previewImg');
const imgRemove = document.getElementById('imgRemove');
let pendingImage = null;
let pendingThumb = null;

imgBtn.addEventListener('click', () => imgInput.click());
imgInput.addEventListener('change', async () => {
  const file = imgInput.files && imgInput.files[0];
  if (!file) return;
  try {
    const dataUrl = await compressImage(file);
    pendingImage = dataUrl;
    pendingThumb = await makeThumb(dataUrl);
    previewImg.src = pendingImage;
    imgPreview.style.display = 'flex';
  } catch (e) {}
  imgInput.value = '';
});
imgRemove.addEventListener('click', () => {
  pendingImage = null;
  pendingThumb = null;
  imgPreview.style.display = 'none';
});

function compressImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = e => {
      const img = new Image();
      img.onload = () => {
        const MAX = 1280;
        let { width, height } = img;
        if (width > MAX || height > MAX) {
          const ratio = Math.min(MAX / width, MAX / height);
          width = Math.round(width * ratio);
          height = Math.round(height * ratio);
        }
        const canvas = document.createElement('canvas');
        canvas.width = width; canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        let quality = 0.85;
        let url = canvas.toDataURL('image/jpeg', quality);
        while (url.length > 1024 * 1024 && quality > 0.5) {
          quality -= 0.1;
          url = canvas.toDataURL('image/jpeg', quality);
        }
        resolve(url);
      };
      img.onerror = reject;
      img.src = e.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/* 生成几十 KB 的缩略图，用于存进对话历史与分享页展示 */
function makeThumb(dataUrl) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const MAX = 480;
      let { width, height } = img;
      if (width > MAX || height > MAX) {
        const ratio = Math.min(MAX / width, MAX / height);
        width = Math.round(width * ratio);
        height = Math.round(height * ratio);
      }
      const canvas = document.createElement('canvas');
      canvas.width = width; canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);
      let quality = 0.7;
      let url = canvas.toDataURL('image/jpeg', quality);
      while (url.length > 60 * 1024 && quality > 0.3) {
        quality -= 0.1;
        url = canvas.toDataURL('image/jpeg', quality);
      }
      resolve(url);
    };
    img.onerror = reject;
    img.src = dataUrl;
  });
}

/* ---------- 发送 ---------- */
async function send() {
  const text = (input.value || '').trim();
  if ((!text && !pendingImage) || busy) return;
  if (!activeConvId) return;
  if (!canUse) { showQuotaBlock(); return; }

  const isFirst = chatEl.querySelector('.welcome') ? true : (chatEl.children.length === 0);
  if (chatEl.querySelector('.onboarding-guide')) { showOnboardingNudge(); }
  /* 首次提问后展开「转为长期账号」提示条（仅未绑定邀请码用户） */
  if (isFirst) showBindBanner();
  const content = pendingImage
    ? [{ type: 'text', text }, { type: 'image_url', image_url: { url: pendingImage, thumbnail: pendingThumb || pendingImage } }]
    : text;
  input.value = '';
  pendingImage = null;
  pendingThumb = null;
  imgPreview.style.display = 'none';
  autoResize();
  if (chatEl.querySelector('.welcome')) chatEl.innerHTML = '';

  addMsg('user', content);
  const convId = activeConvId;

  busy = true;
  sendBtn.disabled = true;
  const msgEl = addTyping();
  const bubble = msgEl.querySelector('.bubble');
  const acc = [];
  let jokeLocked = false;
  let jokeStartTime = 0;
  let jokeEffect = null;
  let profileNoticeText = '';

  if (isFirst && text) genTitle(convId, text);

  try {
    const resp = await fetch('api/chat', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(Object.assign(
        { messages: [{ role: 'user', content }], convId },
        chatApiParams() || {}
      ))
    });
    if (resp.status === 402) {
      const d = await resp.json().catch(() => ({}));
      bubble.innerHTML = '<p>' + escapeHtml(d.detail || '次数已用完，可在设置中填入自己的 API 继续使用') + '</p>';
      canUse = false;
      return;
    }
    if (!resp.ok) {
      const d = await resp.json().catch(() => ({}));
      bubble.innerHTML = '<p>' + escapeHtml(d.detail || '请求失败') + '</p>';
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data:')) continue;
        const data = line.slice(5).trim();
        if (data === '__start__') continue;
        if (data === '__end__') { break; }
        if (data.startsWith('__error__:')) {
          bubble.innerHTML = '<p>服务出错：' + escapeHtml(data.slice(10)) + '</p>';
          return;
        }
        if (data.startsWith('__profile_notice__:')) {
          try { profileNoticeText = JSON.parse(data.slice(19)); } catch (e) { profileNoticeText = data.slice(19); }
          continue;
        }
        /* 后端 JSON 编码了 token（避免 \n 破坏 SSE），此处解码还原 */
        if (data.startsWith('__joke__:')) {
          try { jokeEffect = JSON.parse(data.slice(9)); } catch (e) { jokeEffect = { kind: 'six' }; }
          if (!jokeEffect || (jokeEffect.kind === 'meme' && !MEME_ASSETS[jokeEffect.meme])) jokeEffect = { kind: 'six' };
          jokeLocked = true;
          jokeStartTime = Date.now();
          showJokeEffect(msgEl, jokeEffect);
          continue;
        }
        let token;
        try { token = JSON.parse(data); } catch (e) { token = data; }
        acc.push(token);
        if (!jokeLocked) {
          const full = acc.join('');
          if (full.includes('[JOKE6]')) {
            const clean = full.replace('[JOKE6]', '').trim();
            acc.length = 0;
            acc.push(clean);
            jokeLocked = true;
            jokeStartTime = Date.now();
            showJokeEffect(msgEl, { kind: 'six' });
            continue;
          }
          renderBotMsg(msgEl, full);
          scrollDown();
        }
      }
    }
    if (!acc.length) {
      bubble.innerHTML = '<p>未收到回复，请确认后端已配置 DeepSeek API Key。</p>';
    }
    if (!jokeLocked) {
      maybeDivider(new Date().toISOString());
      renderBotMsg(msgEl, acc.join(''));
      addMsgTime(msgEl);
      if (profileNoticeText) addProfileNotice(profileNoticeText);
    } else {
      /* 彩蛋模式：等"6"显示满 1.5 秒后，追加新气泡显示正片 */
      const elapsed = Date.now() - jokeStartTime;
      const delay = Math.max(0, jokeEffectDelay(jokeEffect) - elapsed);
      setTimeout(() => {
        addMsg('bot', acc.join(''));
        if (profileNoticeText) addProfileNotice(profileNoticeText);
        scrollDown();
      }, delay);
    }
    refreshQuota();
  } catch (e) {
    bubble.innerHTML = '<p>请求失败：' + escapeHtml(e.message) + '</p>';
  } finally {
    busy = false;
    scrollDown();
    sendBtn.disabled = false;
    input.focus();
  }
}
function addMsg(role, content, iso) {
  maybeDivider(iso);
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  if (role === 'bot') div.appendChild(botAvatar());
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  div.appendChild(bubble);
  if (role === 'user') div.appendChild(userAvatar());
  chatEl.appendChild(div);
  if (role === 'bot') renderBotMsg(div, content); else renderUserMsg(div, content, null);
  addMsgTime(div, iso);
  scrollDown();
  return div;
}
function addProfileNotice(text) {
  if (!text) return;
  const note = document.createElement('div');
  note.className = 'profile-notice';
  note.textContent = text;
  chatEl.appendChild(note);
  scrollDown();
}

/* 渲染用户消息：支持带图片（content 可能是数组带 image_url，image 是历史缩略图） */
function renderUserMsg(div, content, image) {
  const bubble = div.querySelector('.bubble');
  let text = '';
  let img = image || null;
  if (typeof content === 'string') {
    text = content;
  } else if (Array.isArray(content)) {
    for (const c of content) {
      if (c && c.type === 'text') text += c.text || '';
      else if (c && c.type === 'image_url') {
        const iu = c.image_url;
        img = (typeof iu === 'object' && iu) ? (iu.thumbnail || iu.url) : iu;
      }
    }
  }
  if (img) {
    const imgel = document.createElement('img');
    imgel.className = 'msg-img';
    imgel.src = img;
    imgel.alt = '图片';
    bubble.appendChild(imgel);
  }
  if (text) {
    const p = document.createElement('p');
    p.textContent = text;
    bubble.appendChild(p);
  }
}
async function refreshQuota() {
  try {
    const r = await fetch('api/auth/me', { headers: authHeaders() });
    const me = await r.json();
    currentUser = me;
    useProfile(me.profile || currentProfile);
    canUse = me.role === 'admin' ? true : me.can_use;
    updateQuotaBadge(me);
  } catch (e) {}
}

/* ---------- 统一设置弹窗 ---------- */
const settingsModal = document.getElementById('settingsModal');
const accountSection = document.getElementById('accountPane');
const apiProviderSel = document.getElementById('apiProvider');
const apiKeyInput = document.getElementById('apiKeyInput');
const apiBaseInput = document.getElementById('apiBaseInput');
const apiModelInput = document.getElementById('apiModelInput');
const apiStatus = document.getElementById('apiStatus');
const preferencesSection = document.getElementById('preferencesPane');
const apiProviderHint = document.getElementById('apiProviderHint');
const API_PROVIDER_HINTS = {
  deepseek: '\u76f4\u63a5\u586b\u5165 DeepSeek API Key\u5373\u53ef\u3002',
  volcengine: '\u4f7f\u7528\u706b\u5c71\u65b9\u821f\u7684 API Key\u3002\u63a8\u8350\u4f7f\u7528\u514d\u8d39\u989d\u5ea6\u5df2\u5f00\u901a\u7684 DeepSeek-V4-Flash\uff1b\u5176\u4ed6\u6a21\u578b\u8bf7\u6309\u65b9\u821f\u63a7\u5236\u53f0\u7684 Model ID \u586b\u5199\u3002',
  openai: '\u9002\u7528\u4e8e\u5176\u4ed6 OpenAI \u517c\u5bb9\u670d\u52a1\uff0c\u8bf7\u81ea\u884c\u786e\u8ba4\u5730\u5740\u548c\u6a21\u578b\u540d\u3002',
};
function applyApiProviderPreset(provider, replaceValues = false) {
  const preset = API_PRESETS[provider] || API_PRESETS.deepseek;
  if (replaceValues) {
    apiBaseInput.value = preset.base;
    apiModelInput.value = preset.models[0];
  } else {
    apiBaseInput.placeholder = preset.base;
    apiModelInput.placeholder = preset.models[0];
  }
  apiKeyInput.placeholder = preset.keyPlaceholder || 'sk-...';
  if (apiProviderHint) apiProviderHint.textContent = API_PROVIDER_HINTS[provider] || API_PROVIDER_HINTS.openai;
}

function openSettings(tab) {
  renderAccountSection();
  renderAvatarGrid();
  renderPreferencesSection();
  /* API 设置回填 */
  const s = getApiSettings() || {};
  apiProviderSel.value = API_PRESETS[s.provider] ? s.provider : 'deepseek';
  apiKeyInput.value = s.apiKey || '';
  apiBaseInput.value = s.apiBase || '';
  apiModelInput.value = s.model || '';
  applyApiProviderPreset(apiProviderSel.value, false);
  apiStatus.textContent = '';
  apiStatus.className = 'api-status';
  /* 指定标签打开（如 API），否则默认账号标签 */
  switchSettingsTab(tab || 'account');
  settingsModal.style.display = 'flex';
}
function closeSettings() { settingsModal.style.display = 'none'; }
function switchSettingsTab(tab) {
  /* 切换标签高亮 */
  settingsModal.querySelectorAll('.settings-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tab);
  });
  /* 切换内容面板 */
  settingsModal.querySelectorAll('.settings-pane').forEach(p => {
    p.classList.toggle('active', p.dataset.pane === tab);
  });
}
settingsModal.querySelectorAll('.settings-tab').forEach(tab => {
  if (tab.id === 'logoutTab') {
    tab.addEventListener('click', doLogout);
  } else {
    tab.addEventListener('click', () => switchSettingsTab(tab.dataset.tab));
  }
});
document.getElementById('settingsBtn').addEventListener('click', openSettings);
document.getElementById('settingsClose').addEventListener('click', closeSettings);
/* A native select can finish outside the card. Only close on a complete backdrop click. */
let settingsBackdropPointerStarted = false;
settingsModal.addEventListener('pointerdown', e => {
  settingsBackdropPointerStarted = e.target === settingsModal;
});
settingsModal.addEventListener('click', e => {
  if (e.target === settingsModal && settingsBackdropPointerStarted) closeSettings();
  settingsBackdropPointerStarted = false;
});

/* ---------- 头像选择网格（并入账号标签页后，绑定 accountPane 内网格点击） ---------- */
function renderAvatarGrid() {
  const grid = accountSection.querySelector('.avatar-grid');
  if (!grid) return;
  grid.querySelectorAll('.avatar-opt').forEach(img => {
    img.addEventListener('click', () => {
      const idx = parseInt(img.dataset.idx, 10);
      localStorage.setItem(AVATAR_KEY, String(idx));
      grid.querySelectorAll('.avatar-opt').forEach(el => el.classList.remove('selected'));
      img.classList.add('selected');
      toast('头像已更新');
    });
  });
}

/* ---------- 账号与密码区域 ---------- */
function renderAccountSection() {
  if (currentRole === 'admin') {
    const u = getUser() || {};
    accountSection.innerHTML =
      '<div class="pane-title">账号</div>' +
      '<div class="account-info">管理员：<b>' + escapeHtml(u.username || 'admin') + '</b></div>' +
      renderAvatarBlock();
    return;
  }
  if (boundUsername) {
    accountSection.innerHTML =
      '<div class="pane-title">账号</div>' +
      '<div class="account-info"><b>' + escapeHtml(boundUsername) + '</b></div>' +
      renderAvatarBlock() +
      '<div class="pane-title" style="margin-top:16px">修改密码</div>' +
      '<label class="settings-label">原密码</label>' +
      '<input class="settings-input" id="oldPass" type="password" placeholder="输入原密码" autocomplete="current-password" />' +
      '<label class="settings-label">新密码</label>' +
      '<input class="settings-input" id="newPass" type="password" placeholder="至少 6 位" autocomplete="new-password" />' +
      '<label class="settings-label">确认新密码</label>' +
      '<input class="settings-input" id="newPass2" type="password" placeholder="再输一次" autocomplete="new-password" />' +
      '<div class="login-err" id="changePassErr"></div>' +
      '<div class="btn-row"><button class="settings-btn" id="changePassBtn">修改密码</button></div>';
    document.getElementById('changePassBtn').addEventListener('click', submitChangePassword);
    document.getElementById('newPass2').addEventListener('keydown', e => { if (e.key === 'Enter') submitChangePassword(); });
  } else {
    accountSection.innerHTML =
      '<div class="pane-title">绑定账号</div>' +
      '<div class="settings-hint">设置账号密码后，下次可用账号密码登录，无需再输邀请码</div>' +
      '<label class="settings-label">账号</label>' +
      '<input class="settings-input" id="bindUser" placeholder="3-20 位字母/数字/下划线" autocomplete="off" />' +
      '<label class="settings-label">密码</label>' +
      '<input class="settings-input" id="bindPass" type="password" placeholder="至少 6 位" autocomplete="new-password" />' +
      '<div class="login-err" id="bindErr"></div>' +
      '<div class="btn-row"><button class="settings-btn" id="bindSubmitBtn">绑定</button></div>' +
      renderAvatarBlock();
    document.getElementById('bindSubmitBtn').addEventListener('click', submitBind);
    document.getElementById('bindPass').addEventListener('keydown', e => { if (e.key === 'Enter') submitBind(); });
  }
}

/* 头像选择块（并入账号标签页） */
function renderAvatarBlock() {
  const current = getAvatarIdx();
  let html = '<div class="pane-title" style="margin-top:16px">选择头像</div>';
  html += '<div class="avatar-grid">';
  for (let i = 1; i <= AVATAR_COUNT; i++) {
    html += '<img src="avatars/' + i + '.webp" class="avatar-opt' + (i === current ? ' selected' : '') + '" data-idx="' + i + '" alt="" />';
  }
  html += '</div>';
  return html;
}

async function submitBind() {
  const username = document.getElementById('bindUser').value.trim();
  const password = document.getElementById('bindPass').value;
  const errEl = document.getElementById('bindErr');
  errEl.textContent = '';
  if (!/^[A-Za-z0-9_]{3,20}$/.test(username)) { errEl.textContent = '账号需为 3-20 位字母/数字/下划线'; return; }
  if (password.length < 6) { errEl.textContent = '密码至少 6 位'; return; }
  try {
    const r = await fetch('api/auth/bind-account', {
      method: 'POST', headers: authHeaders(), body: JSON.stringify({ username, password })
    });
    const d = await r.json();
    if (!r.ok) { errEl.textContent = d.detail || '绑定失败'; return; }
    boundUsername = d.username;
    const u = getUser() || {};
    u.username = d.username;
    localStorage.setItem(USER_KEY, JSON.stringify(u));
    dismissBindBanner(true);
    renderAccountSection();
    toast('已绑定账号 ' + d.username);
  } catch (e) {
    errEl.textContent = '网络错误，请重试';
  }
}

async function submitChangePassword() {
  const oldP = document.getElementById('oldPass').value;
  const newP = document.getElementById('newPass').value;
  const newP2 = document.getElementById('newPass2').value;
  const errEl = document.getElementById('changePassErr');
  errEl.textContent = '';
  if (!oldP) { errEl.textContent = '请输入原密码'; return; }
  if (newP.length < 6) { errEl.textContent = '新密码至少 6 位'; return; }
  if (newP !== newP2) { errEl.textContent = '两次新密码不一致'; return; }
  try {
    const r = await fetch('api/user/change-password', {
      method: 'POST', headers: authHeaders(), body: JSON.stringify({ oldPassword: oldP, newPassword: newP })
    });
    const d = await r.json();
    if (!r.ok) { errEl.textContent = d.detail || '修改失败'; return; }
    toast('密码已修改');
    document.getElementById('oldPass').value = '';
    document.getElementById('newPass').value = '';
    document.getElementById('newPass2').value = '';
  } catch (e) {
    errEl.textContent = '网络错误，请重试';
  }
}
/* ---------- 回答偏好设置 ---------- */
function profileLevelLabel(level) {
  return { beginner: '不太懂', intermediate: '会折腾一点', advanced: '比较熟', unknown: '让 FixPilot 自动判断' }[level] || '让 FixPilot 自动判断';
}
function renderPreferencesSection() {
  if (!preferencesSection) return;
  const p = currentProfile || defaultProfile();
  const explicitLevel = p.technical_level_source === 'explicit' ? p.technical_level : 'unknown';
  const inferred = p.technical_level_source === 'inferred' ? '目前自动适配为「' + profileLevelLabel(p.technical_level) + '」，你随时可以改成手动。' : '不确定时，FixPilot 会根据有效对话逐步适配。';
  preferencesSection.innerHTML =
    '<div class="pane-title">回答偏好</div>' +
    '<label class="settings-label">电脑水平</label>' +
    '<select class="settings-input" id="technicalLevelSelect">' +
      '<option value="unknown">让 FixPilot 自动判断</option>' +
      '<option value="beginner">不太懂</option><option value="intermediate">会折腾一点</option><option value="advanced">比较熟</option>' +
    '</select><div class="settings-hint">' + inferred + '</div>' +
    '<label class="settings-label">说话方式</label>' +
    '<select class="settings-input" id="responseStyleSelect">' +
      '<option value="normal">正常点</option><option value="roast">嘴毒点</option><option value="concise">少废话</option>' +
    '</select><div class="settings-hint">嘴毒只会在事实已确认的低级乌龙时出现，不会影响排障和安全提醒。</div>' +
    '<div class="login-err" id="preferencesErr"></div><div class="btn-row"><button class="settings-btn" id="savePreferencesBtn">保存</button></div>';
  document.getElementById('technicalLevelSelect').value = explicitLevel;
  document.getElementById('responseStyleSelect').value = p.response_style || 'normal';
  document.getElementById('savePreferencesBtn').addEventListener('click', savePreferences);
}
async function savePreferences() {
  const err = document.getElementById('preferencesErr');
  err.textContent = '';
  try {
    await saveProfilePreference({
      technicalLevel: document.getElementById('technicalLevelSelect').value,
      responseStyle: document.getElementById('responseStyleSelect').value,
      onboardingCompleted: true,
      onboardingSeen: true,
    });
    renderPreferencesSection();
    toast('回答偏好已更新');
  } catch (e) { err.textContent = e.message || '保存失败，请重试'; }
}

/* ---------- API 设置（内嵌在设置弹窗中） ---------- */
async function saveApiSettings_action() {
  const provider = apiProviderSel.value;
  const apiKey = apiKeyInput.value.trim();
  if (!apiKey) { apiStatus.textContent = '请输入 API Key'; apiStatus.className = 'api-status err'; return; }
  const preset = API_PRESETS[provider] || API_PRESETS.deepseek;
  const apiBase = apiBaseInput.value.trim() || preset.base;
  const model = apiModelInput.value.trim() || preset.models[0];
  /* 先测试连通性 */
  apiStatus.textContent = '正在测试 API 连通性...';
  apiStatus.className = 'api-status';
  try {
    const res = await fetch('/api/test-api', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
      body: JSON.stringify({ apiKey, apiBase, model }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      let detail = data.detail;
      if (Array.isArray(detail)) detail = detail.map(e => e.msg || e.message || '').filter(Boolean).join('；');
      else if (typeof detail === 'object' && detail !== null) detail = detail.message || detail.msg || JSON.stringify(detail);
      apiStatus.textContent = '测试失败：' + (detail || '未知错误，请检查填写是否正确');
      apiStatus.className = 'api-status err';
      return;
    }
  } catch (e) {
    apiStatus.textContent = '测试失败：网络错误';
    apiStatus.className = 'api-status err';
    return;
  }
  /* 测试通过，保存 */
  saveApiSettings({ provider, apiKey, apiBase, model });
  apiStatus.textContent = 'API 测试通过，已保存';
  apiStatus.className = 'api-status ok';
  updateModelPicker();
  updateQuotaBadge(currentUser);
}
function clearApiSettings_action() {
  clearApiSettings();
  apiKeyInput.value = '';
  apiBaseInput.value = '';
  apiModelInput.value = '';
  apiStatus.textContent = '已清除，将使用默认 API';
  apiStatus.className = 'api-status ok';
  updateModelPicker();
  updateQuotaBadge(currentUser);
}
apiProviderSel.addEventListener('change', () => applyApiProviderPreset(apiProviderSel.value, true));
document.getElementById('apiSaveBtn').addEventListener('click', saveApiSettings_action);
document.getElementById('apiClearBtn').addEventListener('click', clearApiSettings_action);

/* ---------- 收藏网址（尝试真实书签，兜底下载 .url 快捷方式） ---------- */
function starSvg() {
  return '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="none" stroke="currentColor"/>';
}
function initFavIcon() {
  const favIcon = document.getElementById('favIcon');
  if (favIcon) favIcon.innerHTML = starSvg();
}
function tryBookmark() {
  const url = window.location.href;
  const title = document.title || 'FixPilot';
  // 1. IE / 旧 Edge
  try {
    if (window.external && window.external.AddFavorite) {
      window.external.AddFavorite(url, title);
      toast('已添加到收藏夹');
      return;
    }
  } catch (e) {}
  // 2. 旧 Firefox
  try {
    if (window.sidebar && window.sidebar.addPanel) {
      window.sidebar.addPanel(title, url, '');
      toast('已添加到书签');
      return;
    }
  } catch (e) {}
  // 3. 现代浏览器无法直接操作书签：提示用户按 Ctrl+D 手动添加
  toast('请按 Ctrl+D 将本页加入浏览器书签');
}
document.getElementById('favBtn').addEventListener('click', tryBookmark);

/* ---------- 转为长期账号提示条 ---------- */
function showBindBanner() {
  if (currentRole !== 'user' || boundUsername) return;
  if (bindBannerDismissed || bindBannerShown) return;
  bindBannerShown = true;
  document.getElementById('bindBanner').style.display = '';
}
function dismissBindBanner(silent) {
  bindBannerDismissed = true;
  document.getElementById('bindBanner').style.display = 'none';
}
document.getElementById('bbAction').addEventListener('click', () => { dismissBindBanner(true); openSettings(); });
document.getElementById('bbClose').addEventListener('click', () => dismissBindBanner(false));

/* ---------- 聊天框模型选择器 ---------- */
const modelPickerBtn = document.getElementById('modelPickerBtn');
const modelPickerLabel = document.getElementById('modelPickerLabel');
const modelDropdown = document.getElementById('modelDropdown');
let _modelList = [];

/* 移动端：把模型选择器从输入框移入顶栏（按钮左侧），节省输入框空间 */
function relocateModelPicker() {
  const pickerWrap = modelPickerBtn.parentNode;
  const topbarRight = document.querySelector('.topbar-right');
  const composer = document.querySelector('.composer');
  const mobile = window.matchMedia('(max-width: 767px)').matches;
  if (mobile && pickerWrap !== topbarRight && topbarRight && composer) {
    topbarRight.insertBefore(modelPickerBtn, topbarRight.firstChild);
    topbarRight.insertBefore(modelDropdown, modelPickerBtn.nextSibling);
  } else if (!mobile && pickerWrap !== composer && composer) {
    composer.insertBefore(modelPickerBtn, composer.querySelector('#imgBtn'));
    composer.insertBefore(modelDropdown, modelPickerBtn.nextSibling);
  }
}
relocateModelPicker();
window.addEventListener('resize', relocateModelPicker);

function updateModelPicker() {
  const s = getApiSettings();
  if (!s || !s.apiKey) {
    modelPickerBtn.style.display = 'none';
    modelDropdown.style.display = 'none';
    return;
  }
  modelPickerBtn.style.display = 'inline-flex';
  const preset = API_PRESETS[s.provider] || API_PRESETS.deepseek;
  _modelList = preset.models.slice();
  if (s.model && !_modelList.includes(s.model)) _modelList.unshift(s.model);
  modelPickerLabel.textContent = s.model || preset.models[0];
}
function toggleModelDropdown() {
  const show = modelDropdown.style.display === 'none';
  if (!show) { modelDropdown.style.display = 'none'; modelPickerBtn.classList.remove('open'); return; }
  const s = getApiSettings();
  const current = (s && s.model) || (API_PRESETS[s && s.provider] && API_PRESETS[s.provider].models[0]) || '';
  modelDropdown.innerHTML = _modelList.map(m =>
    '<button type="button" class="model-opt' + (m === current ? ' active' : '') + '" data-model="' + m + '">' + m + '</button>'
  ).join('') + '<button type="button" class="model-opt model-custom" data-model="__custom">自定义...</button>';
  modelDropdown.style.display = 'block';
  modelPickerBtn.classList.add('open');
}
modelPickerBtn.addEventListener('click', (e) => { e.stopPropagation(); toggleModelDropdown(); });
document.addEventListener('click', (e) => {
  if (!modelDropdown.contains(e.target) && e.target !== modelPickerBtn) { modelDropdown.style.display = 'none'; modelPickerBtn.classList.remove('open'); }
});
modelDropdown.addEventListener('click', (e) => {
  const btn = e.target.closest('.model-opt');
  if (!btn) return;
  const m = btn.dataset.model;
  modelDropdown.style.display = 'none';
  modelPickerBtn.classList.remove('open');
  if (m === '__custom') {
    openSettings('api');
    return;
  }
  const s = getApiSettings();
  if (s) { s.model = m; saveApiSettings(s); }
  updateModelPicker();
  toast('已切换模型：' + m);
});

/* ---------- 事件 ---------- */
sendBtn.addEventListener('click', send);
input.addEventListener('input', autoResize);
input.addEventListener('keydown', (e) => {
  // Enter 发送，Alt+Enter 换行（WPS 习惯）
  if (e.key === 'Enter' && !e.altKey && !e.isComposing) { e.preventDefault(); send(); }
});

/* ---------- 初始化 ---------- */
handleInviteParam();

const savedToken = getToken();
if (savedToken) {
  enterApp();
} else {
  showLogin();
}