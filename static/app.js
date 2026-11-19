const $=s=>document.querySelector(s), app=$('#app');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const CUR={RUB:'₽',USD:'$',EUR:'€'};
const money=(v,c='RUB')=>`<span class="money">${Number(v).toLocaleString('ru-RU',{minimumFractionDigits:0,maximumFractionDigits:2})} ${CUR[c]||c}</span>`;
let BANKS=[], hidden=false, tab='overview', range='30';
const api=async(u,o)=>{const r=await fetch(u,o&&{...o,headers:{'Content-Type':'application/json'},body:JSON.stringify(o.body)});const j=await r.json();if(!r.ok)throw new Error(j.error||'Ошибка');return j};
const toast=m=>{const t=$('#toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2400)};
const bank=id=>BANKS.find(b=>b.id===id)||BANKS[BANKS.length-1]||{c1:'#333',c2:'#666',ac:'#fff'};
const RK=['Низкий','Повышенный','Высокий'];
const rkPill=(c,t)=>`<span class="rk r${c}"><i></i>${t}</span>`;

function theme(){const d=document.documentElement;d.dataset.theme=d.dataset.theme==='dark'?'light':'dark';try{localStorage.setItem('theme',d.dataset.theme)}catch(e){}}
function topbar(title,sub,extra=''){const h=new Date().getHours(),g=h<6?'Доброй ночи':h<12?'Доброе утро':h<18?'Добрый день':'Добрый вечер';
 return `<div class="top"><div><h1>${title}</h1><small>${sub||g+' · '+new Date().toLocaleString('ru-RU',{weekday:'long',day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'})}</small></div>
 <div class="row">${extra}<button class="gbtn icon" data-act="hide" title="Скрыть баланс"><svg class="ic"><use href="#i-eye"/></svg></button><button class="gbtn icon" data-act="theme" title="Тема"><svg class="ic"><use href="#i-sun"/></svg></button></div></div>`}

function cardHTML(c,i=0,big=false){const b=bank(c.bank),a=!big,sty=`--c1:${b.c1};--c2:${b.c2};--ac:${b.ac};animation-delay:${i*70}ms`;
 const tag=a?`a href="#/card/${esc(c.id)}"`:'div';
 return `<${tag} class="bcard b-${esc(c.bank)} ${big?'big':''}" style="${sty}"><div class="inner">
 <div class="face front"><i class="deco"></i>${c.risk!==undefined?`<span class="rk r${c.risk_code}"><i></i>${esc(c.risk)}</span>`:''}
 <div class="bn">${esc(c.bank_name)}</div><div class="chip"></div>
 <div class="num">•••• •••• •••• ${esc(c.last4)}</div><div class="hold">${esc(c.title)}</div><div class="sys">${esc(c.system)}</div></div>
 <div class="face back"><div class="mag"></div><div class="sig">Данные карты не хранятся</div><div class="bk">P2P Guardian. Полный номер, CVV и PIN не вводятся и не сохраняются.</div></div></div></${a?'a':'div'}>`}
function tilt(root){root.querySelectorAll('.bcard').forEach(el=>{
 el.onmousemove=e=>{const r=el.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;
  el.style.transform=`perspective(900px) rotateY(${(x-.5)*16}deg) rotateX(${(.5-y)*16}deg) scale(1.03)`;el.style.setProperty('--mx',x*100+'%');el.style.setProperty('--my',y*100+'%')};
 el.onmouseleave=()=>el.style.transform='';})}
function chartHTML(ch){const m=Math.max(1,...ch.flatMap(x=>[x.in,x.out]));
 return `<div class="chart">${ch.map(x=>`<div title="${x.d}: +${x.in} / -${x.out}"><span style="display:flex;gap:2px;align-items:flex-end;height:120px"><i style="height:${x.in/m*100}%;width:10px"></i><i class="o" style="height:${x.out/m*100}%;width:10px"></i></span>${x.d}</div>`).join('')}</div>
 <p class="note"><span style="color:#6fc3ff">■</span> поступления <span style="color:#fb7185">■</span> расходы, последние 14 дней</p>`}

async function home(){const s=await api('/api/summary');
 const st=[['Общий баланс',money(s.balance)],['Поступления сегодня',money(s.today_in)],['Расходы сегодня',money(s.today_out)],['За неделю',money(s.week_in)],['За месяц',money(s.month_in)],
  ['Операций',s.ops],['Уникальных отправителей',s.senders],['Карт',s.cards],['Требуют проверки',s.review]];
 app.innerHTML=topbar('P2P Guardian','',`<button class="gbtn primary sm" data-act="add-tx-any" data-type="in">Поступление</button><button class="gbtn sm" data-act="add-tx-any" data-type="out">Расход</button>`)+`<div class="grid stats">${st.map(x=>`<div class="glass stat"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('')}</div>
 <div class="glass panel"><h2>Динамика</h2>${chartHTML(s.chart)}</div>
 <div class="top"><h2 class="sec" style="margin:0">Мои банковские карты</h2><button class="gbtn primary sm" data-act="add-card"><svg class="ic"><use href="#i-plus"/></svg>Добавить карту</button></div>
 ${s.list.length?`<div class="grid cards">${s.list.map((c,i)=>cardHTML(c,i)).join('')}</div>`:`<div class="glass panel empty">Карт пока нет. Добавьте первую карту: без CVV, PIN и полного номера.</div>`}`;
 tilt(app)}
async function cards(){const s=await api('/api/summary');app.innerHTML=topbar('Мои карты',s.cards+' шт.')+(s.list.length?`<div class="grid cards">${s.list.map((c,i)=>cardHTML(c,i)).join('')}</div>`:'<div class="glass panel empty">Карт пока нет</div>');tilt(app)}

const TABS=[['overview','Обзор'],['in','Поступления'],['out','Расходы'],['senders','Отправители'],['analytics','Аналитика'],['history','История']];
async function cardPage(id){
 let q='';const today=new Date(),f=n=>{const d=new Date(today);d.setDate(d.getDate()-n);return d.toISOString().slice(0,10)};
 if(range==='today')q=`?from=${f(0)}&to=${f(0)}`;else if(range==='yest')q=`?from=${f(1)}&to=${f(1)}`;else if(range==='7')q=`?from=${f(6)}`;else if(range==='30')q=`?from=${f(29)}`;else if(range==='month')q=`?from=${f(0).slice(0,8)}01`;
 const d=await api('/api/cards/'+id+q),c=d.card,s=d.stats;
 const txr=t=>`<tr><td>${esc(t.date)} ${esc(t.time)}</td><td class="${t.type}">${t.type==='in'?'+':'−'}${money(t.amount,c.currency)}</td><td>${t.type==='in'?esc(t.sender_label||('Отправитель '+t.sender))+(t.sender_bank?' <span class="mut">· '+esc(t.sender_bank)+'</span>':''):'—'}</td><td class="mut">${esc(t.comment||t.op_id||'')}${t.refund?' · возврат':''}</td><td>${t.doc?'док.':''}${t.deal?' · '+esc(t.deal):''}</td><td><button class="gbtn icon sm" data-del="${esc(t.id)}" style="width:36px;height:36px;padding:8px"><svg class="ic"><use href="#i-trash"/></svg></button></td></tr>`;
 const table=l=>l.length?`<div class="tw"><table><tr><th>Дата</th><th>Сумма</th><th>Отправитель</th><th>Комментарий</th><th>Сделка</th><th></th></tr>${l.map(txr).join('')}</table></div>`:'<div class="empty">Операций пока нет</div>';
 let body='';
 if(tab==='overview')body=`<div class="grid stats">${[['Общий оборот',money(s.turnover,c.currency)],['Поступления',money(s.income,c.currency)],['Расходы',money(s.expense,c.currency)],['Входящих',s.n_in],['Исходящих',s.n_out]].map(x=>`<div class="glass stat"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('')}</div><div class="glass panel"><h2>Динамика</h2>${chartHTML(d.chart)}</div>${c.note?`<div class="glass panel"><h2>Заметка</h2>${esc(c.note)}</div>`:''}<div class="glass panel"><h2>Последние операции</h2>${table(d.tx.slice(0,5))}</div>`;
 if(tab==='in')body=`<div class="glass panel"><div class="top" style="margin-bottom:8px"><h2 style="margin:0">Поступления</h2><button class="gbtn primary sm" data-act="add-tx" data-type="in"><svg class="ic"><use href="#i-down"/></svg>Добавить</button></div>${table(d.tx.filter(t=>t.type==='in'))}</div>`;
 if(tab==='out')body=`<div class="glass panel"><div class="top" style="margin-bottom:8px"><h2 style="margin:0">Расходы</h2><button class="gbtn primary sm" data-act="add-tx" data-type="out"><svg class="ic"><use href="#i-up"/></svg>Добавить</button></div>${table(d.tx.filter(t=>t.type==='out'))}</div>`;
 if(tab==='history')body=`<div class="glass panel"><h2>Все операции</h2>${table(d.tx)}</div>`;
 if(tab==='senders'){const r=d.senders,R=[['today','Сегодня'],['yest','Вчера'],['7','7 дней'],['30','30 дней'],['month','Месяц'],['all','Всё время']];
  body=`<div class="tabs">${R.map(x=>`<button class="gbtn sm ${range===x[0]?'on':''}" data-range="${x[0]}">${x[1]}</button>`).join('')}</div>
  <div class="grid stats">${[['Входящих операций',r.total_ops],['Уникальных отправителей',r.unique],['Повторных',r.repeat],['Новых за период',range==='all'?'—':r.new],['Сумма',money(r.sum,c.currency)],['Средняя',money(r.avg,c.currency)],['Максимум',money(r.max,c.currency)]].map(x=>`<div class="glass stat"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('')}</div>
  <div class="glass panel"><h2>Отправители</h2><p class="note" style="margin:-8px 0 10px">Хранятся только псевдонимы, без ФИО.</p>${r.rows.length?`<div class="tw"><table><tr><th>Псевдоним</th><th>Операций</th><th>Сумма</th><th>Последняя</th><th>История</th></tr>${r.rows.map(x=>`<tr><td>${esc(x.alias)} <span class="mut">#${esc(x.code)}</span>${x.new?' <span class="pill">новый</span>':''}</td><td>${x.count}</td><td>${money(x.sum,c.currency)}</td><td>${esc(x.last)}</td><td class="mut">${x.history.map(h=>esc(h.date.slice(5))+': '+h.amount).join(' · ')}</td></tr>`).join('')}</table></div>`:'<div class="empty">За выбранный период поступлений нет</div>'}</div>`}
 if(tab==='analytics'){const r=d.risk;body=`<div class="glass panel"><h2>Уровень внимания: <span class="rk r${r.code}" style="background:none;padding:0;font-size:inherit"><i></i>${r.level}</span></h2>
  ${r.factors.map(f=>`<div class="rf"><span class="rk r${f.level}" style="background:none;padding:0"><i></i></span><div><b>${esc(f.name)}</b> <span class="mut">· ${RK[f.level]}</span><p>${esc(f.why)}</p></div></div>`).join('')}<p class="note">${esc(r.note)}</p></div>`}
 app.innerHTML=topbar(esc(c.title),esc(c.bank_name)+' · •••• '+esc(c.last4),`<a href="#/" class="gbtn icon"><svg class="ic"><use href="#i-back"/></svg></a><button class="gbtn danger icon" data-del-card="${esc(c.id)}"><svg class="ic"><use href="#i-trash"/></svg></button>`)
 +cardHTML({...c,...s,balance:s.balance,risk:d.risk.level,risk_code:d.risk.code},0,true)
 +`<p class="note" style="text-align:center;margin:0 0 14px">Нажмите на карту, чтобы перевернуть</p><div class="actbar"><button class="gbtn primary" data-act="add-tx" data-type="in"><svg class="ic"><use href="#i-down"/></svg>Поступление</button><button class="gbtn" data-act="add-tx" data-type="out"><svg class="ic"><use href="#i-up"/></svg>Расход</button></div><div class="tabs">${TABS.map(t=>`<button class="gbtn sm ${tab===t[0]?'on':''}" data-tab="${t[0]}">${t[1]}</button>`).join('')}</div>`+body;
 tilt(app)}

function openModal(html){const m=$('#modal');m.querySelector('.sheet').innerHTML=html;m.hidden=false;return m.querySelector('.sheet')}
const closeModal=()=>{$('#modal').hidden=true};
function addCardModal(){let sel='';const sh=openModal(`<h3>Добавить карту</h3><p class="mut" style="margin:0">Не вводите PIN, CVV, пароли, SMS-коды и полный номер карты.</p>
 <input id="bs" placeholder="Поиск банка" style="margin-top:12px"><div class="banks" id="bl"></div>
 <div id="own" hidden><label>Название банка</label><input id="bname" maxlength="40"></div>
 <label>Название карты</label><input id="ctitle" maxlength="40" placeholder="Например, основная">
 <div class="f2"><div><label>Последние 4 цифры</label><input id="l4" inputmode="numeric" maxlength="4"></div><div><label>Платёжная система</label><select id="sys"><option>Мир</option><option>Visa</option><option>Mastercard</option><option>UnionPay</option></select></div></div>
 <div class="f2"><div><label>Начальный баланс</label><input id="ini" type="number" step="0.01" value="0"></div><div><label>Валюта</label><select id="cur"><option>RUB</option><option>USD</option><option>EUR</option></select></div></div>
 <label>Заметка</label><textarea id="note" rows="2" maxlength="300"></textarea><div class="err" id="er"></div>
 <div class="actions"><button class="gbtn sm" data-act="close">Отмена</button><button class="gbtn primary sm" id="ok">Добавить</button></div>`);
 const draw=()=>{const q=sh.querySelector('#bs').value.toLowerCase();sh.querySelector('#bl').innerHTML=BANKS.filter(b=>b.name.toLowerCase().includes(q)).map(b=>`<button class="gbtn ${sel===b.id?'on':''}" data-b="${b.id}" style="background:linear-gradient(135deg,${b.c1}cc,${b.c2}cc);color:#fff">${esc(b.name)}</button>`).join('')};
 draw();sh.querySelector('#bs').oninput=draw;
 sh.querySelector('#bl').onclick=e=>{const b=e.target.closest('[data-b]');if(!b)return;sel=b.dataset.b;sh.querySelector('#own').hidden=sel!=='other';draw()};
 sh.querySelector('#ok').onclick=async()=>{try{const v=i=>sh.querySelector(i).value;const c=await api('/api/cards',{method:'POST',body:{bank:sel,bank_name:v('#bname'),title:v('#ctitle'),last4:v('#l4'),system:v('#sys'),initial:v('#ini'),currency:v('#cur'),note:v('#note')}});closeModal();toast('Карта добавлена');location.hash='#/card/'+c.id;route()}catch(e){sh.querySelector('#er').textContent=e.message}}}
async function addTxModal(cid,type){let list=[];
 if(!cid){list=(await api('/api/summary')).list;if(!list.length){toast('Сначала добавьте карту');return}}
 const n=new Date(),p=x=>String(x).padStart(2,'0'),isIn=type==='in';
 const sh=openModal(`<h3>${isIn?'Новое поступление':'Новый расход'}</h3>
 ${list.length?`<label>Карта</label><select id="cc">${list.map(c=>`<option value="${esc(c.id)}">${esc(c.title)} · ${esc(c.bank_name)} •••• ${esc(c.last4)}</option>`).join('')}</select>`:''}
 <div class="f2"><div><label>Сумма</label><input id="am" type="number" step="0.01" min="0" inputmode="decimal"></div><div><label>Комиссия</label><input id="fee" type="number" step="0.01" value="0"></div></div>
 ${isIn?`<label>Кто отправил (имя и фамилия)</label><input id="snd" maxlength="80" placeholder="Например, Иван Петров"><p class="note" style="margin:4px 0 0">Сохраняется только имя и инициал фамилии, например «Иван П.».</p>
 <label>Банк отправителя</label><input id="sb" list="bl2" maxlength="40" placeholder="Начните вводить банк"><datalist id="bl2">${BANKS.map(b=>`<option value="${esc(b.name)}">`).join('')}</datalist>`:''}
 <div class="f2"><div><label>Дата</label><input id="dt" type="date" value="${n.getFullYear()}-${p(n.getMonth()+1)}-${p(n.getDate())}"></div><div><label>Время</label><input id="tm" type="time" value="${p(n.getHours())}:${p(n.getMinutes())}"></div></div>
 <label>Идентификатор операции</label><input id="op" maxlength="60"><label>Привязка к сделке</label><input id="deal" maxlength="60"><label>Комментарий</label><input id="cm" maxlength="300">
 <label class="chk"><input type="checkbox" id="doc">Есть подтверждающий документ</label><label class="chk"><input type="checkbox" id="rf">Возврат или спорный платёж</label>
 <div class="err" id="er"></div><div class="actions"><button class="gbtn" data-act="close">Отмена</button><button class="gbtn primary" id="ok">Сохранить</button></div>`);
 sh.querySelector('#ok').onclick=async()=>{try{const v=i=>sh.querySelector(i)?.value,k=i=>sh.querySelector(i).checked,id=v('#cc')||cid;
  await api('/api/cards/'+id+'/tx',{method:'POST',body:{type,amount:v('#am'),fee:v('#fee'),date:v('#dt'),time:v('#tm'),sender:v('#snd'),sender_bank:v('#sb'),op_id:v('#op'),deal:v('#deal'),comment:v('#cm'),doc:k('#doc'),refund:k('#rf')}});closeModal();toast('Сохранено');route()}catch(e){sh.querySelector('#er').textContent=e.message}}}

let ncat='',nfav=false,ntimer;
const NCATS=[['','Все'],['P2P','P2P'],['Криптовалюты','Крипто'],['Банки','Банки'],['115-ФЗ','115-ФЗ'],['161-ФЗ','161-ФЗ'],['Банк России','Банк России'],['Законодательство','Законы'],['Биржи','Биржи'],['Платёжные системы','Платежи']];
async function news(){app.innerHTML=topbar('Новости','P2P, банки и регуляторы · только из открытых источников')+
 `<div class="nbar"><input id="nq" placeholder="Поиск по новостям"><button class="gbtn sm" data-act="nfav">Избранное</button></div>
 <div class="tabs">${NCATS.map(c=>`<button class="gbtn sm" data-ncat="${c[0]}">${c[1]}</button>`).join('')}</div><div id="nl"><div class="empty">Загружаем новости…</div></div>`;
 $('#nq').oninput=()=>{clearTimeout(ntimer);ntimer=setTimeout(loadNews,350)};loadNews()}
async function loadNews(){const nl=$('#nl');if(!nl)return;
 document.querySelectorAll('[data-ncat]').forEach(b=>b.classList.toggle('on',b.dataset.ncat===ncat));
 document.querySelector('[data-act=nfav]')?.classList.toggle('primary',nfav);
 try{const r=await api(`/api/news?cat=${encodeURIComponent(ncat)}&q=${encodeURIComponent($('#nq')?.value||'')}&fav=${nfav?1:0}`);
  const fmt=d=>new Date(d).toLocaleString('ru-RU',{day:'numeric',month:'long',year:'numeric',hour:'2-digit',minute:'2-digit'});
  nl.innerHTML=(r.errors.length?`<p class="note" style="margin:0 0 10px">Сейчас недоступны источники: ${r.errors.map(esc).join(', ')}.</p>`:'')+
  (r.items.length?r.items.map(i=>`<article class="glass news ${i.image?'':'noimg'}">${i.image?`<img src="${esc(i.image)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentNode.classList.add('noimg');this.remove()">`:''}
   <div><div class="meta">${esc(i.source)} · ${esc(fmt(i.date))}</div><h3><a href="${esc(i.link)}" target="_blank" rel="noopener noreferrer">${esc(i.title)}</a></h3>
   ${i.summary?`<p>${esc(i.summary)}</p>`:''}<div class="chips">${i.cats.map(c=>`<span class="pill">${esc(c)}</span>`).join('')}</div>
   ${i.hint?`<div class="hint"><b>Что это может значить.</b> ${esc(i.hint)}</div>`:''}
   <div class="nact"><a class="gbtn sm" href="${esc(i.link)}" target="_blank" rel="noopener noreferrer">Открыть источник</a><button class="gbtn sm ${i.fav?'primary':''}" data-fav="${esc(i.link)}">${i.fav?'В избранном':'В избранное'}</button></div></div></article>`).join('')
  :'<div class="glass panel empty">Подходящих новостей сейчас нет. Это не значит, что их не было: проверьте фильтр или обновите позже.</div>')+
  '<p class="note">Описание взято из источника. AI-резюме появится после подключения AI API. Пояснения «что это может значить» это общая справка, а не совет.</p>'}
 catch(e){nl.innerHTML=`<div class="glass panel empty">${esc(e.message)}</div>`}}

async function route(){const h=location.hash||'#/';document.querySelectorAll('[data-nav]').forEach(a=>a.classList.toggle('on',a.getAttribute('href')===h||(h.startsWith('#/card/')&&a.dataset.nav==='cards')));
 try{if(!BANKS.length)BANKS=await api('/api/banks');
  if(h.startsWith('#/card/'))await cardPage(h.slice(7));else if(h==='#/cards')await cards();else if(h==='#/news')await news();else await home();
  document.body.classList.toggle('hide',hidden)}catch(e){app.innerHTML=`<div class="glass panel empty">${esc(e.message)}</div>`}}
document.addEventListener('click',async e=>{const t=e.target.closest('button,a,.bcard');if(!t)return;const d=t.dataset;
 if(d.act==='theme')theme();else if(d.act==='hide'){hidden=!hidden;document.body.classList.toggle('hide',hidden)}
 else if(d.act==='add-card')addCardModal();else if(d.act==='add-tx-any')addTxModal(null,d.type);else if(d.ncat!==undefined){ncat=d.ncat;loadNews()}else if(d.act==='nfav'){nfav=!nfav;loadNews()}else if(d.fav){await api('/api/news/fav',{method:'POST',body:{link:d.fav}});loadNews()}else if(d.act==='close')closeModal();
 else if(d.act==='add-tx')addTxModal(location.hash.slice(7),d.type);
 else if(d.tab){tab=d.tab;route()}else if(d.range){range=d.range;route()}
 else if(d.del){if(confirm('Удалить операцию? Действие попадёт в журнал.')){await api('/api/tx/'+d.del,{method:'DELETE'});route()}}
 else if(d.delCard){if(confirm('Удалить карту и все её операции?')){await api('/api/cards/'+d.delCard,{method:'DELETE'});location.hash='#/'}}
 else if(t.classList.contains('bcard')){if(t.tagName==='A'){tab='overview';range='30'}else t.classList.toggle('flip')}});
$('#modal').addEventListener('click',e=>{if(e.target.id==='modal')closeModal()});
addEventListener('hashchange',route);route();
