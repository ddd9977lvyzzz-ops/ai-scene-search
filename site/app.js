const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const labels={solo:'自己看',family:'和家人',friends:'和朋友',couple:'和对象',weekend:'周末',party:'聚会',late_night:'睡前',meal:'饭后',light:'轻松',relaxing:'放松',healing:'治愈',funny:'好笑',exciting:'刺激',tense:'紧张',thought_provoking:'烧脑',romantic:'恋爱感',movie:'电影',series:'电视剧',variety:'综艺',animation:'动漫',documentary:'纪录片',low:'低负担',high:'高信息量',Romance:'恋爱/爱情',Comedy:'喜剧',Thriller:'悬疑',Mystery:'推理',Action:'动作',Horror:'恐怖',niche:'小众优先',mainstream:'热门优先',sweet:'偏甜',gentle:'温柔',realistic:'现实',bittersweet:'苦甜',dark:'偏暗黑',playful:'轻快',warm:'温暖',precise:'精准匹配',balanced:'适度探索',explore:'探索模式'};
const starters=['我想看小众恋爱片','最近想自己追一部国产剧，节奏快一点，不要太虐','和朋友聚会，想看轻松好笑的电影','一个人睡前看，想治愈一点，90分钟内','像《功夫》一样好笑的电影','悬疑一点，但不要恐怖'];
const state={catalog:[],profile:freshProfile(),seen:new Set(),busy:false,lastQuery:''};
function freshProfile(){return {contentTypes:[],requiredGenres:[],avoidGenres:[],requiredSignals:[],avoidRisks:[],moods:[],relationship:[],tone:[],pace:[],companions:null,scene:null,cognitive:null,popularity:null,language:null,runtimeMax:null,explore:false,sourceReference:null};}
function toast(m){const n=$('#toast');n.textContent=m;n.classList.add('show');setTimeout(()=>n.classList.remove('show'),2200)}
function arr(v){return Array.isArray(v)?v:[]}
function lower(v){return String(v||'').toLowerCase()}
function hasGenre(x,g){return arr(x.g).some(v=>lower(v).includes(lower(g))) || (g==='Romance'&&arr(x.re).includes('romantic'));}
function hasAny(x,keys,field){const vals=arr(x[field]);return keys.some(k=>vals.includes(k));}
function mergeUnique(a,b){return [...new Set([...a,...b])];}
function removeMood(conflicts){state.profile.moods=state.profile.moods.filter(x=>!conflicts.includes(x));}
function parse(text){
  const p=state.profile; const q=text.trim(); state.lastQuery=q;
  if(/换一批|再来一批|换几个/.test(q)) return;
  if(/给我点惊喜|惊喜一点|探索/.test(q)) p.explore=true;
  if(/电影/.test(q)) p.contentTypes=['movie']; else if(/电视剧|剧集|追一部.*剧|想看.*剧/.test(q)) p.contentTypes=['series'];
  if(/国产|中国大陆|中文/.test(q)) p.language='Chinese';
  if(/恋爱|爱情|纯爱|甜宠/.test(q)){p.requiredGenres=mergeUnique(p.requiredGenres,['Romance']);p.relationship=mergeUnique(p.relationship,['romantic']);}
  if(/喜剧|好笑|搞笑|逗/.test(q)){p.requiredSignals=mergeUnique(p.requiredSignals,['funny']);}
  if(/节奏快|快节奏|紧凑/.test(q)){p.requiredSignals=mergeUnique(p.requiredSignals,['fast']);p.pace=mergeUnique(p.pace,['fast']);}
  if(/悬疑|推理/.test(q)) p.requiredGenres=mergeUnique(p.requiredGenres,[/推理/.test(q)?'Mystery':'Thriller']);
  if(/动作/.test(q)) p.requiredGenres=mergeUnique(p.requiredGenres,['Action']);
  if(/科幻/.test(q)) p.requiredGenres=mergeUnique(p.requiredGenres,['Sci-Fi']);
  if(/不要.*恐怖|别.*恐怖|不想.*恐怖/.test(q)){p.avoidGenres=mergeUnique(p.avoidGenres,['Horror']);p.avoidRisks=mergeUnique(p.avoidRisks,['fear_or_horror']);}
  if(/不要.*爱情|别.*恋爱|不想.*恋爱/.test(q)) p.avoidGenres=mergeUnique(p.avoidGenres,['Romance']);
  if(/不要太虐|别太虐|不虐/.test(q)) p.avoidRisks=mergeUnique(p.avoidRisks,['emotionally_heavy']);
  if(/和朋友|朋友聚会|朋友看/.test(q)){p.companions='friends';p.scene='party';}
  if(/和家人|跟家人|爸妈|父母/.test(q)){p.companions='family';p.scene=/饭后|吃饭/.test(q)?'meal':p.scene;}
  if(/和对象|跟对象|约会|情侣/.test(q)) p.companions='couple';
  if(/一个人|自己看|自己追/.test(q)) p.companions='solo';
  if(/睡前|躺床|晚上睡/.test(q)) p.scene='late_night';
  if(/饭后|吃饭/.test(q)) p.scene='meal';
  if(/周末/.test(q)) p.scene=p.scene||'weekend';
  if(/小众|冷门|宝藏/.test(q)) p.popularity='niche';
  if(/热门|大众/.test(q)) p.popularity='mainstream';
  if(/治愈/.test(q)){removeMood(['exciting','tense','thought_provoking']);p.moods=mergeUnique(p.moods,['healing','relaxing']);p.cognitive='low';}
  if(/轻松|放松|下饭|不想动脑/.test(q)){removeMood(['exciting','tense','thought_provoking']);p.moods=mergeUnique(p.moods,['light','relaxing']);p.cognitive='low';}
  if(/刺激/.test(q)){removeMood(['light','relaxing']);p.moods=mergeUnique(p.moods,['exciting']);}
  if(/烧脑/.test(q)) p.moods=mergeUnique(p.moods,['thought_provoking']);
  const m=q.match(/(?:两小时|2小时)/); if(m) p.runtimeMax=120;
  const mins=q.match(/(\d{2,3})\s*分钟/); if(mins) p.runtimeMax=Number(mins[1]);
  const ref=q.match(/《([^》]{1,30})》/); if(ref) p.sourceReference=ref[1].trim();
}
function hardOk(x){const p=state.profile;
  if(p.contentTypes.length&&!p.contentTypes.includes(x.ct))return false;
  if(p.runtimeMax&&(!x.rt&& !x.ert || Number(x.rt||x.ert)>p.runtimeMax))return false;
  if(p.language==='Chinese'&&!arr(x.co).some(c=>String(c).includes('中国大陆'))&&!['中文','Chinese','Mandarin','Cantonese'].includes(x.la))return false;
  if(p.requiredGenres.some(g=>!hasGenre(x,g)))return false;
  if(p.avoidGenres.some(g=>hasGenre(x,g)))return false;
  if(p.avoidRisks.some(r=>arr(x.ri).includes(r)))return false;
  if(p.requiredSignals.includes('funny')&&!(hasGenre(x,'Comedy')||arr(x.em).includes('funny')||arr(x.to).includes('playful')))return false;
  if(p.requiredSignals.includes('fast')&&!(arr(x.pa).includes('fast')||arr(x.em).includes('exciting')||['Action','Thriller','Adventure'].some(g=>hasGenre(x,g))))return false;
  return true;
}
function overlap(a,b){if(!a.length||!b.length)return 0;const s=new Set(b);return a.filter(x=>s.has(x)).length/a.length;}
function anchorScore(x){const ref=state.profile.sourceReference;if(!ref)return 0;const a=state.catalog.find(i=>i.t===ref||i.ot===ref||arr(i.al).includes(ref));if(!a)return 0;return 0.4*overlap(arr(a.g),arr(x.g))+0.2*overlap(arr(a.em),arr(x.em))+0.2*overlap(arr(a.to),arr(x.to))+0.2*overlap(arr(a.th),arr(x.th));}
function score(x){const p=state.profile;let s=0;
  if(p.requiredGenres.length)s+=3*p.requiredGenres.filter(g=>hasGenre(x,g)).length;
  if(p.relationship.length)s+=2.2*overlap(p.relationship,arr(x.re));
  if(p.moods.length)s+=1.8*overlap(p.moods,arr(x.em));
  if(p.tone.length)s+=1.2*overlap(p.tone,arr(x.to));
  if(p.pace.length)s+=1.5*overlap(p.pace,arr(x.pa));
  if(p.scene&&arr(x.sc).includes(p.scene))s+=1.1;
  if(p.companions&&arr(x.sc).includes(p.companions))s+=0.9;
  if(p.cognitive&&x.cl===p.cognitive)s+=1.0;
  if(p.popularity==='niche')s+=({low:1.7,medium:1.0,unknown:.4,high:-1.2}[x.pb]??0);
  if(p.popularity==='mainstream')s+=({high:1.5,medium:.8,unknown:.2,low:-.4}[x.pb]??0);
  if(p.requiredSignals.includes('funny'))s+=hasGenre(x,'Comedy')?2.1:1;
  if(p.requiredSignals.includes('fast'))s+=arr(x.pa).includes('fast')?1.7:.6;
  s+=anchorScore(x)*2.2;
  if(x.ra!=null)s+=Math.max(0,(Number(x.ra)-6)/4)*.45;
  if(x.uc!=null)s+=Number(x.uc)*.25;
  if(p.explore){s+=(arr(x.g).length*.03)+(x.pb==='low'?.5:0)+((hash(x.id)%100)/100)*.35;}
  else s+=((hash(x.id)%100)/100)*.03;
  return s;
}
function hash(s){let h=0;for(let i=0;i<String(s).length;i++)h=((h<<5)-h)+String(s).charCodeAt(i)|0;return Math.abs(h)}
function recommend(){let pool=state.catalog.filter(x=>hardOk(x)&&!state.seen.has(x.id)); if(state.profile.sourceReference)pool=pool.filter(x=>x.t!==state.profile.sourceReference&&x.ot!==state.profile.sourceReference);
  pool.sort((a,b)=>score(b)-score(a)); const top=pool.slice(0,5); top.forEach(x=>state.seen.add(x.id)); return top;}
function reason(x){const p=state.profile;const bits=[];
  if(p.requiredGenres.includes('Romance'))bits.push('恋爱/关系线符合明确要求');
  if(p.requiredSignals.includes('funny'))bits.push('喜剧或好笑特征满足硬条件');
  if(p.requiredSignals.includes('fast'))bits.push('节奏偏快');
  if(p.popularity==='niche'&&['low','medium'].includes(x.pb))bits.push('热度更偏小众');
  if(p.scene&&arr(x.sc).includes(p.scene))bits.push(`适配${labels[p.scene]||p.scene}场景`);
  if(p.moods.length&&overlap(p.moods,arr(x.em))>0)bits.push('情绪氛围匹配');
  if(p.sourceReference&&anchorScore(x)>.15)bits.push(`与《${p.sourceReference}》在类型/氛围上有相似点`);
  return bits.slice(0,3).join('；')||'在当前合法候选里，综合类型、场景和内容理解得分靠前。';}
function profileChips(){const p=state.profile;const raw=[p.companions,p.scene,...p.moods,p.cognitive,...p.contentTypes,...p.requiredGenres,...p.relationship,...p.pace].filter(Boolean);let vals=raw.map(x=>labels[x]||x);if(p.language)vals.push('中文/国产');if(p.sourceReference)vals.push(`类似《${p.sourceReference}》`);if(p.popularity)vals.push(labels[p.popularity]);if(p.runtimeMax)vals.push(`≤ ${p.runtimeMax} 分钟`);if(p.explore)vals.push('探索模式');p.avoidGenres.forEach(x=>vals.push(`不要 ${labels[x]||x}`));p.avoidRisks.forEach(x=>vals.push(x==='emotionally_heavy'?'不要太虐':x==='fear_or_horror'?'不要惊吓':`避开 ${x}`));const n=$('#active-profile');n.innerHTML=[...new Set(vals)].map(x=>`<span>${esc(x)}</span>`).join('');n.classList.toggle('hidden',!vals.length)}
function startConversation(){$('#welcome').classList.add('hidden');$('#conversation').classList.remove('hidden')}
function addUser(t){startConversation();$('#messages').insertAdjacentHTML('beforeend',`<div class="turn-user"><p>${esc(t)}</p></div>`)}
function card(x,i){const rt=x.rt||x.ert;const meta=[x.y,rt?`${rt} 分钟`:null,labels[x.ct]||x.ct,x.pb==='low'?'偏冷门':x.pb==='high'?'较热门':null].filter(Boolean).join(' · ');const tags=[...arr(x.g).slice(0,2),...arr(x.to).slice(0,2)].map(v=>`<span>${esc(labels[v]||v)}</span>`).join('');const rn=arr(x.rn).slice(0,2).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);const sn=arr(x.sn).slice(0,2).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);return `<article class="rec-card"><img class="rec-poster" src="${esc(x.p)}" alt="${esc(x.t)} 海报" loading="lazy" onerror="this.style.visibility='hidden'"><div class="rec-copy"><div class="rec-top"><div><h3 class="rec-title">${i+1}. ${esc(x.t)}</h3><p class="rec-meta">${esc(meta)}</p></div><span class="rec-score">${Math.round(Math.min(99,72+score(x)*3))} 匹配</span></div><p class="rec-why">${esc(reason(x))}</p>${rn.length?`<p class="rec-insight"><b>可能雷点</b>${esc(rn.join(' · '))}</p>`:''}${sn.length?`<p class="rec-insight"><b>无剧透看点</b>${esc(sn.join(' · '))}</p>`:''}<div class="rec-tags">${tags}</div><button class="rec-more" type="button" data-detail="${esc(x.id)}">查看内容依据</button></div></article>`}
function render(items){const intro=items.length?'我先锁住你明确说出的类型、时长、平台/风险边界，再用场景和内容特征排序。探索只发生在满足硬条件的候选里。':'这组硬条件下暂时没有足够可靠的结果，可以放宽一个条件再试。';$('#messages').insertAdjacentHTML('beforeend',`<div class="turn-agent"><div class="agent-avatar">此</div><div><p class="agent-intro">${intro}</p>${items.length?`<div class="recommend-list">${items.map(card).join('')}</div>`:'<div class="no-match"><p>没有找到满足全部硬条件的候选。</p></div>'}</div></div>`);profileChips();const qa=['换一批','更轻松一点','更小众一点','给我点惊喜'];$('#quick-actions').innerHTML=qa.map(x=>`<button type="button" data-prompt="${x}">${x}</button>`).join('');$('#quick-actions').classList.remove('hidden');scrollEnd()}
function scrollEnd(){requestAnimationFrame(()=>window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'}))}
async function sendMessage(text){text=(text||'').trim();if(!text||state.busy)return;state.busy=true;$('#send').disabled=true;addUser(text);$('#message-input').value='';parse(text);render(recommend());state.busy=false;$('#send').disabled=false;}
function openDetail(id){const x=state.catalog.find(v=>v.id===id);if(!x)return;const risks=arr(x.rn).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);const surprises=arr(x.sn).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);$('#detail-body').innerHTML=`<div class="detail"><img src="${esc(x.p)}" alt="${esc(x.t)} 海报"><div><small>${esc([x.y,labels[x.ct],(x.rt||x.ert)?(x.rt||x.ert)+' 分钟':null].filter(Boolean).join(' · '))}</small><h2>${esc(x.t)}</h2><p>${esc(x.d||'暂无简介')}</p><p><strong>类型：</strong>${arr(x.g).map(esc).join(' / ')||'未标注'}</p><p><strong>氛围：</strong>${arr(x.to).map(v=>esc(labels[v]||v)).join(' / ')||'暂无'}</p>${risks.length?`<p><strong>可能雷点：</strong>${esc(risks.slice(0,5).join(' / '))}</p>`:'<p><strong>可能雷点：</strong>证据不足，不等于确定没有雷点。</p>'}${surprises.length?`<p><strong>无剧透看点：</strong>${esc(surprises.slice(0,5).join(' / '))}</p>`:''}<small>内容理解置信度：${Math.round((x.uc||0)*100)}% · 来源：${esc(x.src||'catalog')}</small></div></div>`;$('#detail-dialog').showModal()}
function reset(){state.profile=freshProfile();state.seen.clear();state.lastQuery='';$('#messages').innerHTML='';$('#conversation').classList.add('hidden');$('#welcome').classList.remove('hidden');$('#active-profile').classList.add('hidden');$('#quick-actions').classList.add('hidden');window.scrollTo({top:0,behavior:'smooth'})}
async function loadCatalog(){
  const manifest=await fetch('./catalog.parts/manifest.json').then(r=>{if(!r.ok)throw new Error(`manifest ${r.status}`);return r.json()});
  const chunks=await Promise.all(manifest.parts.map(name=>fetch(`./catalog.parts/${name}`).then(r=>{if(!r.ok)throw new Error(`${name} ${r.status}`);return r.text()})));
  const binary=atob(chunks.join('').trim());
  const bytes=new Uint8Array(binary.length);
  for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
  if(typeof DecompressionStream==='undefined')throw new Error('This browser needs DecompressionStream support.');
  const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  const text=await new Response(stream).text();
  return JSON.parse(text);
}
async function init(){try{const data=await loadCatalog();state.catalog=data.items||[];$('#catalog-status').innerHTML=`<i></i>${state.catalog.length.toLocaleString()} 部真实内容 · 浏览器本地检索`;$('#starter-grid').innerHTML=starters.map(x=>`<button class="starter" type="button" data-prompt="${esc(x)}">${esc(x)}</button>`).join('');}catch(e){console.error(e);toast('片库加载失败，请刷新页面')}}
document.addEventListener('click',e=>{const p=e.target.closest('[data-prompt]');if(p)sendMessage(p.dataset.prompt);const d=e.target.closest('[data-detail]');if(d)openDetail(d.dataset.detail)});$('#composer').addEventListener('submit',e=>{e.preventDefault();sendMessage($('#message-input').value)});$('#message-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage(e.target.value)}});$('#new-chat').addEventListener('click',reset);$('#detail-close').addEventListener('click',()=>$('#detail-dialog').close());init();
