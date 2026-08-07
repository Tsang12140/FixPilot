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
const logoutBtn = document.getElementById('logoutBtn');
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
const pinModal = document.getElementById('pinModal');
const pinTitle = document.getElementById('pinTitle');
const pinDesc = document.getElementById('pinDesc');
const pinInput = document.getElementById('pinInput');
const pinBoxes = document.getElementById('pinBoxes');
const pinClose = document.getElementById('pinClose');
const pinErr = document.getElementById('pinErr');

const TOKEN_KEY = 'fixpilot_token';
const USER_KEY = 'fixpilot_user';

/* ---------- 会话状态 ---------- */
let conversations = [];
let activeConvId = null;
let busy = false;
let canUse = true;

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
    if (d.status === 'need_pin') {
      // 需设置或输入 PIN 码
      openPinModal(d.mode, d.code);
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

/* ---------- PIN 码弹窗 ---------- */
let pendingCode = null;
let pendingPinMode = null;
let _pinLock = false;

function updatePinBoxes() {
  const v = (pinInput.value || '').replace(/\D/g, '').slice(0, 4);
  if (pinInput.value !== v) pinInput.value = v;
  pinBoxes.querySelectorAll('.pin-box').forEach((b, i) => {
    b.textContent = v[i] || '';
    b.classList.toggle('filled', !!v[i]);
    b.classList.toggle('active', i === v.length);
  });
}
function shakePin() {
  pinBoxes.classList.remove('shake');
  void pinBoxes.offsetWidth; /* 重新触发抖动动画 */
  pinBoxes.classList.add('shake');
}
function openPinModal(mode, code) {
  pendingCode = code;
  pendingPinMode = mode;
  _pinLock = false;
  pinErr.textContent = '';
  pinInput.value = '';
  if (mode === 'set') {
    pinTitle.textContent = '设置 PIN 码';
    pinDesc.textContent = '首次使用，请设置一个 4 位数字 PIN 码，下次登录时需要输入';
  } else {
    pinTitle.textContent = '输入 PIN 码';
    pinDesc.textContent = '请输入你的 4 位数字 PIN 码';
  }
  pinModal.style.display = 'flex';
  updatePinBoxes();
  setTimeout(() => pinInput.focus(), 80);
}
function closePinModal() {
  pinModal.style.display = 'none';
  pendingCode = null;
  pendingPinMode = null;
}
function pinFail(msg) {
  _pinLock = false;
  pinErr.textContent = msg || '';
  shakePin();
  pinInput.value = '';
  updatePinBoxes();
  setTimeout(() => pinInput.focus(), 120);
}
async function submitPin() {
  if (_pinLock) return;
  const pin = pinInput.value.trim();
  if (!/^\d{4}$/.test(pin)) { pinErr.textContent = 'PIN 码需为 4 位数字'; return; }
  _pinLock = true;
  pinErr.textContent = '';
  try {
    const r = await fetch('api/auth/invite-pin', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: pendingCode, pin })
    });
    const d = await r.json();
    if (!r.ok) { pinFail(d.detail || 'PIN 码校验失败'); return; }
    closePinModal();
    setSession(d.token, { role: d.role, code: d.code });
    await enterApp();
  } catch (e) {
    pinFail('网络错误，请重试');
  } finally {
    _pinLock = false;
  }
}

pinInput.addEventListener('input', () => {
  updatePinBoxes();
  if (pinInput.value.length === 4) submitPin();
});
pinInput.addEventListener('keydown', e => { if (e.key === 'Enter') submitPin(); });
pinClose.addEventListener('click', closePinModal);
pinModal.addEventListener('click', e => { if (e.target === pinModal) closePinModal(); });

async function doAdminLogin() {
  const username = adminUser.value.trim();
  const password = adminPass.value;
  if (!username || !password) { adminErr.textContent = '请输入账号和密码'; return; }
  adminErr.textContent = '';
  adminLoginBtn.disabled = true;
  try {
    const r = await fetch('api/auth/admin-login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password })
    });
    const d = await r.json();
    if (!r.ok) { adminErr.textContent = d.detail || '登录失败'; return; }
    setSession(d.token, { role: d.role, username: d.username });
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

logoutBtn.addEventListener('click', () => {
  clearSession();
  location.href = './';
});

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
    const r = await fetch('api/conversations/' + activeConvId + '/share', {
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
    const body = isBot ? mdToHtml(text) : '<p>' + escapeHtml(text) + '</p>';
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

/* ---------- 邀请码管理面板（主界面内嵌，管理员齿轮打开） ---------- */
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
  adminModal.style.display = 'none';
  const prev = adminBody.innerHTML;
  adminBody.innerHTML = '<div class="acard-title">邀请码 ' + code + ' 的对话历史</div><div id="aHistoryBody"><div class="aempty">加载中...</div></div>' +
    '<div class="aactions"><button class="a-btn ghost" id="aBack">返回</button></div>';
  document.getElementById('aBack').addEventListener('click', () => { adminBody.innerHTML = prev; adminModal.style.display = 'flex'; });
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
    if (me.role === 'admin') {
      // 管理员进入聊天窗，显示齿轮按钮进入后台
      document.getElementById('adminBtn').style.display = 'inline-flex';
      document.getElementById('quotaWrap').style.display = 'none';
      await loadConversations();
      showApp();
      return;
    }
    canUse = me.can_use;
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
  const wrap = document.createElement('div');
  wrap.className = 'quota-block';
  wrap.innerHTML = '<p><strong>邀请码次数已用完</strong></p>' +
    '<p>请联系管理员为你增加次数或延长有效期，刷新后即可继续使用。</p>' +
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
      maybeDivider(m.created_at);
      const div = document.createElement('div');
      div.className = 'msg ' + (m.role === 'user' ? 'user' : 'bot');
      if (m.role === 'bot') div.appendChild(botAvatar());
      const bubble = document.createElement('div');
      bubble.className = 'bubble';
      div.appendChild(bubble);
      if (m.role === 'bot') renderBotMsg(div, m.content); else bubble.textContent = m.content;
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
  a.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
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
      '<p>比如：<em>开机黑屏但风扇在转</em>、<em>游戏经常闪退</em>、<em>电脑没声音</em>。</p>' +
      '<blockquote>提示：上传图片时，我只能<strong>识别截图里的文字</strong>（比如蓝屏代码、报错信息），不能直接"看图"判断硬件外观或接线是否正确。</blockquote></div>' +
    '</div>' +
    '<div class="chips">' +
      '<button class="chip" data-q="游戏经常闪退怎么办">游戏经常闪退</button>' +
      '<button class="chip" data-q="开机黑屏，但风扇在转">开机黑屏</button>' +
      '<button class="chip" data-q="电脑鼠标卡顿漂移">鼠标卡顿</button>' +
      '<button class="chip" data-q="电脑没有声音">没有声音</button>' +
    '</div>' +
  '</div>';

function renderWelcome() {
  chatEl.innerHTML = WELCOME_HTML;
  chatEl.querySelector('.chips').addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (chip) { input.value = chip.dataset.q; send(); }
  });
  scrollDown(false);
}

/* ---------- 选项按钮 ---------- */
function parseOptions(text) {
  // 兼容「选项：」独立成行，或与正文/选项同行的两种输出
  const m = text.match(/选项\s*[:：]/);
  if (!m) return { main: text, options: [] };
  const main = text.slice(0, m.index).trim();
  let optStr = text.slice(m.index + m[0].length).trim();
  const options = [];
  // 支持同行连写：1.xxx2.yyy3.zzz
  const re = /\d+[.、)]\s*/g;
  let last = 0;
  let mm;
  while ((mm = re.exec(optStr))) {
    const item = optStr.slice(last, mm.index).trim();
    if (item) options.push(item);
    last = mm.index + mm[0].length;
  }
  const tail = optStr.slice(last).trim();
  if (tail) options.push(tail);
  // 兜底：没有编号时按行切分
  if (!options.length) {
    for (const l of optStr.split(/\n+/)) {
      const t = l.trim();
      if (t) options.push(t);
    }
  }
  return { main, options: options.slice(0, 4) };
}
/* 把紧跟在文字后、同行连写的编号步骤拆到新行，保留已有空行，便于排版 */
function breakNumbered(text) {
  return text.replace(/([^\n])(\d+[.、)])(?!\d)/g, '$1\n$2');
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
      b.addEventListener('click', () => { collapseOpts(wrap); input.value = o; send(); });
      wrap.appendChild(b);
    });
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
  bubble.innerHTML = '<div class="joke6">6</div>';
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
  if (d.toDateString() === now.toDateString()) {
    const h = d.getHours() % 12 === 0 ? 12 : d.getHours() % 12;
    return (d.getHours() < 12 ? '上午 ' : '下午 ') + h + ':' + pad(d.getMinutes());
  }
  const y = new Date(now);
  y.setDate(now.getDate() - 1);
  if (d.toDateString() === y.toDateString()) return '昨天 ' + hm;
  return (d.getMonth() + 1) + '月' + d.getDate() + '日 ' + hm;
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
  input.style.height = Math.min(input.scrollHeight, 140) + 'px';
}

/* ---------- 图片上传 ---------- */
const imgInput = document.getElementById('imgInput');
const imgBtn = document.getElementById('imgBtn');
const imgPreview = document.getElementById('imgPreview');
const previewImg = document.getElementById('previewImg');
const imgRemove = document.getElementById('imgRemove');
let pendingImage = null;

imgBtn.addEventListener('click', () => imgInput.click());
imgInput.addEventListener('change', async () => {
  const file = imgInput.files && imgInput.files[0];
  if (!file) return;
  try {
    const dataUrl = await compressImage(file);
    pendingImage = dataUrl;
    previewImg.src = pendingImage;
    imgPreview.style.display = 'flex';
  } catch (e) {}
  imgInput.value = '';
});
imgRemove.addEventListener('click', () => {
  pendingImage = null;
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

/* ---------- 发送 ---------- */
async function send() {
  const text = (input.value || '').trim();
  if ((!text && !pendingImage) || busy) return;
  if (!activeConvId) return;
  if (!canUse) { showQuotaBlock(); return; }

  const isFirst = chatEl.querySelector('.welcome') ? true : (chatEl.children.length === 0);
  const content = pendingImage ? [{ type: 'text', text }, { type: 'image_url', image_url: pendingImage }] : text;
  input.value = '';
  pendingImage = null;
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
  let jokeTimer = null;

  if (isFirst && text) genTitle(convId, text);

  try {
    const resp = await fetch('api/chat', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ messages: [{ role: 'user', content }], convId })
    });
    if (resp.status === 402) {
      bubble.innerHTML = '<p>邀请码次数已用完，请联系管理员。</p>';
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
        acc.push(data);
        if (!jokeLocked) {
          const full = acc.join('');
          if (full.includes('[JOKE6]')) {
            // 低级错误场景：先憋出一个"6"，再延迟上正片
            const clean = full.replace('[JOKE6]', '').trim();
            acc.length = 0;
            acc.push(clean);
            jokeLocked = true;
            showJoke6(bubble);
            jokeTimer = setTimeout(() => {
              jokeLocked = false;
              maybeDivider(new Date().toISOString());
              renderBotMsg(msgEl, acc.join(''));
              addMsgTime(msgEl);
              scrollDown();
            }, 1500);
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
  if (role === 'bot') renderBotMsg(div, content); else bubble.textContent = content;
  addMsgTime(div, iso);
  scrollDown();
  return div;
}
async function refreshQuota() {
  try {
    const r = await fetch('api/auth/me', { headers: authHeaders() });
    const me = await r.json();
    canUse = me.can_use;
    updateQuotaBadge(me);
  } catch (e) {}
}

/* ---------- 事件 ---------- */
sendBtn.addEventListener('click', send);
input.addEventListener('input', autoResize);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); }
});

/* ---------- 初始化 ---------- */
handleInviteParam();

const savedToken = getToken();
if (savedToken) {
  enterApp();
} else {
  showLogin();
}