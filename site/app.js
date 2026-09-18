const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const labels={solo:'自己看',family:'和家人',friends:'和朋友',couple:'和对象',weekend:'周末',party:'聚会',late_night:'睡前',meal:'饭后',light:'轻松',relaxing:'放松',healing:'治愈',funny:'好笑',exciting:'刺激',tense:'紧张',thought_provoking:'烧脑',romantic:'恋爱感',movie:'电影',series:'电视剧',variety:'综艺',animation:'动漫',documentary:'纪录片',low:'低负担',high:'高信息量',Romance:'恋爱/爱情',Comedy:'喜剧',Thriller:'悬疑',Mystery:'推理',Action:'动作',Horror:'恐怖',niche:'小众优先',mainstream:'热门优先',sweet:'偏甜',gentle:'温柔',realistic:'现实',bittersweet:'苦甜',dark:'偏暗黑',playful:'轻快',warm:'温暖',precise:'精准匹配',balanced:'适度探索',explore:'探索模式',no_character_death:'没有角色死亡',happy_ending:'明确偏圆满',no_animal_harm:'无动物伤害',no_infidelity:'无出轨主线',no_gore:'无血腥重点',no_jump_scares:'无跳吓重点',no_sexual_content:'无明显大尺度',family_safe:'家庭共看友好',closed_ending:'结局收束',romance_central:'恋爱主线',friendship_central:'友情主线',career_central:'事业成长',iqiyi:'爱奇艺',tencent_video:'腾讯视频',youku:'优酷',mango_tv:'芒果TV',netflix:'Netflix',disney_plus:'Disney+',max:'Max',prime_video:'Prime Video'};
const starters=['我想看小众恋爱片','我想看没有任何人死去的电影，最好结局也圆满','我只看爱奇艺，想找2026年的国产剧','和朋友聚会，想看轻松好笑的电影','和爸妈一起看，不要尴尬也不要大尺度','像《功夫》一样好笑，但不要太暴力','悬疑一点，但不要恐怖，也别有跳吓','给我一部我平时不会主动搜到、但很适合今晚的片'];
const state={catalog:[],profile:freshProfile(),seen:new Set(),busy:false,lastQuery:''};
const STORAGE_PREFIX='ying:v1:';
const account={user:null,watchlist:[]};
const COMMUNITY_SCENES=[
  {id:'parents-safe',title:'和爸妈看，不尴尬',desc:'避开明显大尺度、跳吓和尴尬桥段，优先轻松、家庭共看友好。',tags:['家庭共看','低尴尬','轻松'],prompt:'和爸妈一起看，轻松一点，不要尴尬也不要大尺度'},
  {id:'zero-death',title:'今晚不要有人死',desc:'把“没有角色死亡”当成剧情事实硬条件；未知不会自动当安全。',tags:['没人死','低压力','硬边界'],prompt:'我想看没有任何人死去的电影，最好结局也圆满'},
  {id:'weekday-90',title:'工作日 90 分钟以内',desc:'短时长、低认知负荷，适合下班后不想做复杂选择的时候。',tags:['≤90min','低负担','工作日'],prompt:'工作日晚上一个人看，90分钟以内，不想动脑'},
  {id:'friends-laugh',title:'朋友聚会先把气氛带起来',desc:'优先笑点密度与可打断性，不把高压剧情当成“刺激=适合聚会”。',tags:['朋友','好笑','可打断'],prompt:'和朋友聚会，想看轻松好笑的电影'}
];
function storeGet(key,fallback){try{const v=localStorage.getItem(STORAGE_PREFIX+key);return v?JSON.parse(v):fallback}catch(e){return fallback}}
function storeSet(key,value){try{localStorage.setItem(STORAGE_PREFIX+key,JSON.stringify(value))}catch(e){}}
function accountKey(){return account.user&&account.user.email?'watchlist:'+account.user.email:'watchlist:guest'}
function loadAccount(){account.user=storeGet('user',null);account.watchlist=storeGet(accountKey(),[]);syncAccountUI()}
function syncAccountUI(){const b=$('#account-button'),logout=$('#auth-logout');if(b)b.textContent=account.user&&account.user.name?account.user.name:'登录';if(logout)logout.classList.toggle('hidden',!account.user)}
function isSaved(id){return account.watchlist.indexOf(id)>=0}
function toggleSave(id){
  if(!account.user){$('#auth-dialog').showModal();toast('先创建一个本地 Demo 账户，再保存片单');return}
  account.watchlist=isSaved(id)?account.watchlist.filter(function(x){return x!==id}):account.watchlist.concat([id]);
  storeSet(accountKey(),account.watchlist);renderCollection();toast(isSaved(id)?'已加入我的片单':'已取消收藏');
  document.querySelectorAll('[data-save]').forEach(function(btn){if(btn.dataset.save===id){btn.classList.toggle('saved',isSaved(id));btn.textContent=isSaved(id)?'已收藏':'收藏'}});
}
function renderCollection(){
  const body=$('#collection-body');if(!body)return;
  const items=account.watchlist.map(function(id){return state.catalog.find(function(x){return x.id===id})}).filter(Boolean);
  if(!items.length){body.innerHTML='<div class="collection-empty">还没有收藏。推荐卡片上的“收藏”会把作品放进这里。</div>';return}
  body.innerHTML=items.map(function(x){
    const platforms=arr(x.pl).map(function(p){return labels[p]||p}).join(' / ');
    const meta=[x.y,labels[x.ct]||x.ct,platforms].filter(Boolean).join(' · ');
    return '<article class="collection-item"><img src="'+esc(posterFor(x))+'" data-fallback="'+esc(generatedPoster(x))+'" onerror="this.onerror=null;this.src=this.dataset.fallback"><div><h4>'+esc(x.t)+'</h4><p>'+esc(meta)+'</p><div class="collection-actions"><button data-detail="'+esc(x.id)+'">查看</button><button data-save="'+esc(x.id)+'">移除</button></div></div></article>';
  }).join('');
}
function renderCommunity(){
  const body=$('#community-body');if(!body)return;
  body.innerHTML=COMMUNITY_SCENES.map(function(s){
    return '<article class="community-card"><span class="community-meta">场景方案 · Demo 社区</span><h3>'+esc(s.title)+'</h3><p>'+esc(s.desc)+'</p><div class="scene-tags">'+s.tags.map(function(t){return '<span>'+esc(t)+'</span>'}).join('')+'</div><button class="save-button" data-prompt="'+esc(s.prompt)+'">用这个场景找片</button></article>';
  }).join('');
}
function freshProfile(){return {contentTypes:[],requiredGenres:[],avoidGenres:[],requiredSignals:[],avoidRisks:[],requiredFacts:[],avoidFacts:[],moods:[],relationship:[],tone:[],pace:[],companions:null,scene:null,cognitive:null,popularity:null,language:null,runtimeMax:null,yearMin:null,platform:null,explore:false,pickOne:false,sourceReference:null};}
function toast(m){const n=$('#toast');n.textContent=m;n.classList.add('show');setTimeout(()=>n.classList.remove('show'),2200)}
function arr(v){return Array.isArray(v)?v:[]}
function lower(v){return String(v||'').toLowerCase()}
function hasGenre(x,g){return arr(x.g).some(v=>lower(v).includes(lower(g))) || (g==='Romance'&&arr(x.re).includes('romantic'));}
function hasAny(x,keys,field){const vals=arr(x[field]);return keys.some(k=>vals.includes(k));}
function mergeUnique(a,b){return [...new Set([...a,...b])];}
function removeMood(conflicts){state.profile.moods=state.profile.moods.filter(x=>!conflicts.includes(x));}
function factSet(x){return new Set(arr(x.cf).concat(Object.entries(x.facts||{}).filter(([,v])=>v===true).map(([k])=>k)));}
function hasFact(x,f){return factSet(x).has(f);}
function generatedPoster(x){
  const seed=hash((x.id||'')+(x.t||'')); const h1=seed%360, h2=(h1+42+(seed%70))%360;
  const title=String(x.t||'此刻看什么').slice(0,14), year=x.y||'';
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="hsl(${h1} 35% 18%)"/><stop offset="1" stop-color="hsl(${h2} 48% 44%)"/></linearGradient></defs><rect width="600" height="900" rx="28" fill="url(#g)"/><circle cx="485" cy="155" r="130" fill="white" opacity=".08"/><circle cx="80" cy="760" r="180" fill="white" opacity=".06"/><text x="52" y="650" fill="white" font-family="system-ui, sans-serif" font-size="25" opacity=".72">SCENE • ${year}</text><foreignObject x="48" y="680" width="510" height="160"><div xmlns="http://www.w3.org/1999/xhtml" style="font:700 58px/1.15 system-ui;color:white;letter-spacing:-2px;word-break:break-all">${esc(title)}</div></foreignObject><text x="52" y="850" fill="white" font-family="system-ui, sans-serif" font-size="18" opacity=".62">AI SCENE SEARCH · DEMO POSTER</text></svg>`;
  return 'data:image/svg+xml;charset=UTF-8,'+encodeURIComponent(svg);
}
function posterFor(x){return x.p||generatedPoster(x);}
const VECTOR_DIMS=['funny','light','relaxing','healing','romantic','exciting','tense','thought_provoking','scary','fast','slow','romantic_rel','friendship','family','sweet','gentle','realistic','bittersweet','dark','playful','warm','niche','no_character_death','happy_ending','family_safe','no_gore','no_jump_scares'];
function itemVector(x){
  const s=new Set([...arr(x.em),...arr(x.pa),...arr(x.re),...arr(x.to),...arr(x.cf)]);
  if(x.pb==='low')s.add('niche');
  if(hasGenre(x,'Comedy'))s.add('funny');
  if(hasGenre(x,'Romance'))s.add('romantic_rel');
  return VECTOR_DIMS.map(d=>s.has(d)?1:0);
}
function queryVector(p){
  const s=new Set([...p.moods,...p.pace,...p.relationship,...p.tone,...p.requiredFacts]);
  if(p.popularity==='niche')s.add('niche');
  if(p.requiredSignals.includes('funny'))s.add('funny');
  if(p.requiredSignals.includes('fast'))s.add('fast');
  if(p.requiredGenres.includes('Romance'))s.add('romantic_rel');
  return VECTOR_DIMS.map(d=>s.has(d)?1:0);
}
function cosine(a,b){let dot=0,aa=0,bb=0;for(let i=0;i<a.length;i++){dot+=a[i]*b[i];aa+=a[i]*a[i];bb+=b[i]*b[i];}return aa&&bb?dot/Math.sqrt(aa*bb):0;}
function vectorScore(x){return cosine(queryVector(state.profile),itemVector(x));}
function parse(text){
  const p=state.profile; const q=text.trim(); state.lastQuery=q;
  if(/换一批|再来一批|换几个/.test(q)) return;
  if(/都可以|电影剧集都可以|不限/.test(q)) p.contentTypes=[];
  if(/给我点惊喜|惊喜一点|探索|不会主动搜|意外一点/.test(q)) p.explore=true;
  if(/只给我一个|直接选一个|替我选一个|帮我拍板|别给列表/.test(q)) p.pickOne=true;
  if(/电影/.test(q)) p.contentTypes=['movie']; else if(/电视剧|剧集|追一部.*剧|想看.*剧|恋爱剧|爱情剧|甜宠剧|小甜剧/.test(q)) p.contentTypes=['series'];
  if(/国产|中国大陆|中文/.test(q)) p.language='Chinese';
  if(/爱奇艺|iQIYI/i.test(q)) p.platform='iqiyi';
  else if(/腾讯视频|WeTV/i.test(q)) p.platform='tencent_video';
  else if(/优酷|Youku/i.test(q)) p.platform='youku';
  else if(/芒果(?:TV|tv)?/.test(q)) p.platform='mango_tv';
  else if(/Netflix|网飞/i.test(q)) p.platform='netflix';
  const y=q.match(/(20\d{2})/); if(y)p.yearMin=Number(y[1]);
  if(/恋爱|爱情|纯爱|甜宠/.test(q)){p.requiredGenres=mergeUnique(p.requiredGenres,['Romance']);p.relationship=mergeUnique(p.relationship,['romantic']);}
  if(/喜剧|好笑|搞笑|逗|想笑/.test(q)){p.requiredSignals=mergeUnique(p.requiredSignals,['funny']);}
  if(/节奏快|快节奏|紧凑|不拖沓/.test(q)){p.requiredSignals=mergeUnique(p.requiredSignals,['fast']);p.pace=mergeUnique(p.pace,['fast']);}
  if(/悬疑|推理/.test(q)) p.requiredGenres=mergeUnique(p.requiredGenres,[/推理/.test(q)?'Mystery':'Thriller']);
  if(/动作/.test(q)) p.requiredGenres=mergeUnique(p.requiredGenres,['Action']);
  if(/科幻/.test(q)) p.requiredGenres=mergeUnique(p.requiredGenres,['Sci-Fi']);
  if(/不要.*恐怖|别.*恐怖|不想.*恐怖/.test(q)){p.avoidGenres=mergeUnique(p.avoidGenres,['Horror']);p.avoidRisks=mergeUnique(p.avoidRisks,['fear_or_horror']);}
  if(/不要.*爱情|别.*恋爱|不想.*恋爱/.test(q)) p.avoidGenres=mergeUnique(p.avoidGenres,['Romance']);
  if(/不要太虐|别太虐|不虐|别太沉重/.test(q)) p.avoidRisks=mergeUnique(p.avoidRisks,['emotionally_heavy']);
  if(/不要太暴力|别太暴力|不要暴力/.test(q)) p.avoidRisks=mergeUnique(p.avoidRisks,['violence_possible']);
  if(/不要尴尬|别尴尬|不尴尬/.test(q)) p.avoidRisks=mergeUnique(p.avoidRisks,['social_embarrassment']);
  if(/不要大尺度|别有亲密戏|不想看亲密戏/.test(q)) p.requiredFacts=mergeUnique(p.requiredFacts,['no_sexual_content']);
  if(/不要跳吓|别有跳吓|没有跳吓/.test(q)) p.requiredFacts=mergeUnique(p.requiredFacts,['no_jump_scares']);
  if(/不要血腥|不血腥|没有血腥/.test(q)) p.requiredFacts=mergeUnique(p.requiredFacts,['no_gore']);
  if(/没有.*人死|没有任何人死|没人死|不要有人死|不死人|不能死人/.test(q)) p.requiredFacts=mergeUnique(p.requiredFacts,['no_character_death']);
  if(/结局.*圆满|圆满结局|happy ending|HE\b|大团圆/i.test(q)) p.requiredFacts=mergeUnique(p.requiredFacts,['happy_ending']);
  if(/不要出轨|没有出轨|无出轨/.test(q)) p.requiredFacts=mergeUnique(p.requiredFacts,['no_infidelity']);
  if(/不要伤害动物|动物不要死|没有动物伤害/.test(q)) p.requiredFacts=mergeUnique(p.requiredFacts,['no_animal_harm']);
  if(/和朋友|朋友聚会|朋友看/.test(q)){p.companions='friends';p.scene='party';}
  if(/和家人|跟家人|爸妈|父母/.test(q)){p.companions='family';p.scene=/饭后|吃饭/.test(q)?'meal':p.scene;}
  if(/和对象|跟对象|约会|情侣/.test(q)) p.companions='couple';
  if(/一个人|自己看|自己追/.test(q)) p.companions='solo';
  if(/睡前|躺床|晚上睡/.test(q)) p.scene='late_night';
  if(/饭后|吃饭/.test(q)) p.scene='meal';
  if(/周末/.test(q)) p.scene=p.scene||'weekend';
  if(/小众|冷门|宝藏|不会主动搜/.test(q)) p.popularity='niche';
  if(/热门|大众/.test(q)) p.popularity='mainstream';
  if(/治愈/.test(q)){removeMood(['exciting','tense','thought_provoking']);p.moods=mergeUnique(p.moods,['healing','relaxing']);p.cognitive='low';}
  if(/轻松|放松|下饭|不想动脑/.test(q)){removeMood(['exciting','tense','thought_provoking']);p.moods=mergeUnique(p.moods,['light','relaxing']);p.cognitive='low';}
  if(/刺激/.test(q)){removeMood(['light','relaxing']);p.moods=mergeUnique(p.moods,['exciting']);}
  if(/烧脑/.test(q)) p.moods=mergeUnique(p.moods,['thought_provoking']);
  if(/现实一点|写实|成年人恋爱/.test(q)) p.tone=mergeUnique(p.tone,['realistic']);
  if(/甜一点|偏甜/.test(q)) p.tone=mergeUnique(p.tone,['sweet']);
  const m=q.match(/(?:两小时|2小时)/); if(m) p.runtimeMax=120;
  const mins=q.match(/(\d{2,3})\s*分钟/); if(mins) p.runtimeMax=Number(mins[1]);
  const ref=q.match(/《([^》]{1,30})》/); if(ref) p.sourceReference=ref[1].trim();
}
function nextClarification(){
  const p=state.profile;
  const strong=Boolean(p.requiredFacts.length||p.requiredGenres.length||p.requiredSignals.length||p.sourceReference||p.popularity||p.yearMin);
  if(strong) return null;
  if(!p.companions&&!p.contentTypes.length){
    return {question:'这次是自己看，还是和别人一起看？',options:['一个人看','和朋友看','跟家人看','和对象看']};
  }
  if(!p.moods.length&&!p.requiredSignals.length&&!p.scene&&!p.requiredFacts.length){
    return {question:'你更想获得哪种感觉：轻松、刺激、治愈，还是烧脑？',options:['轻松一点','刺激一点','治愈一点','想烧脑']};
  }
  if(!p.contentTypes.length&&!p.sourceReference){
    return {question:'内容形态上更想看电影还是剧集？',options:['只看电影','只看剧','都可以']};
  }
  return null;
}
function renderClarify(item){
  startConversation();
  $('#messages').insertAdjacentHTML('beforeend',`<div class="turn-agent"><div class="agent-avatar">此</div><div><p class="agent-intro">${esc(item.question)}</p><div class="clarify-options">${item.options.map(x=>`<button type="button" data-prompt="${esc(x)}">${esc(x)}</button>`).join('')}</div></div></div>`);
  profileChips();
  $('#quick-actions').classList.add('hidden');
  scrollEnd();
}
function failedConstraints(x){const p=state.profile,fail=[];
  if(p.contentTypes.length&&!p.contentTypes.includes(x.ct))fail.push('内容形态');
  if(p.yearMin&&(!x.y||Number(x.y)<p.yearMin))fail.push(`${p.yearMin}+ 年份`);
  if(p.runtimeMax&&(!x.rt&&!x.ert||Number(x.rt||x.ert)>p.runtimeMax))fail.push(`≤${p.runtimeMax}分钟`);
  if(p.language==='Chinese'&&!arr(x.co).some(c=>String(c).includes('中国大陆'))&&!['中文','Chinese','Mandarin','Cantonese'].includes(x.la))fail.push('国产/中文');
  if(p.platform&&!arr(x.pl).includes(p.platform))fail.push(labels[p.platform]||p.platform);
  p.requiredGenres.filter(g=>!hasGenre(x,g)).forEach(g=>fail.push(labels[g]||g));
  p.avoidGenres.filter(g=>hasGenre(x,g)).forEach(g=>fail.push('排除 '+(labels[g]||g)));
  p.avoidRisks.filter(r=>arr(x.ri).includes(r)).forEach(r=>fail.push('雷点 '+(labels[r]||r)));
  p.requiredFacts.filter(f=>!hasFact(x,f)).forEach(f=>fail.push(labels[f]||f));
  p.avoidFacts.filter(f=>hasFact(x,f)).forEach(f=>fail.push('排除 '+(labels[f]||f)));
  if(p.requiredSignals.includes('funny')&&!(hasGenre(x,'Comedy')||arr(x.em).includes('funny')||arr(x.to).includes('playful')))fail.push('必须好笑');
  if(p.requiredSignals.includes('fast')&&!(arr(x.pa).includes('fast')||arr(x.em).includes('exciting')||['Action','Thriller','Adventure'].some(g=>hasGenre(x,g))))fail.push('快节奏');
  return [...new Set(fail)];
}
function hardOk(x){return failedConstraints(x).length===0;}
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
  s+=vectorScore(x)*2.4;
  if(p.requiredFacts.length)s+=2.6*overlap(p.requiredFacts,[...factSet(x)]);
  if(x.ra!=null)s+=Math.max(0,(Number(x.ra)-6)/4)*.45;
  if(x.uc!=null)s+=Number(x.uc)*.25;
  if(p.explore){s+=(arr(x.g).length*.03)+(x.pb==='low'?.5:0)+((hash(x.id)%100)/100)*.35;}
  else s+=((hash(x.id)%100)/100)*.03;
  return s;
}
function hash(s){let h=0;for(let i=0;i<String(s).length;i++)h=((h<<5)-h)+String(s).charCodeAt(i)|0;return Math.abs(h)}
function recommend(){let pool=state.catalog.filter(x=>hardOk(x)&&!state.seen.has(x.id)); if(state.profile.sourceReference)pool=pool.filter(x=>x.t!==state.profile.sourceReference&&x.ot!==state.profile.sourceReference);
  pool.sort((a,b)=>score(b)-score(a)); const top=pool.slice(0,state.profile.pickOne?1:5); top.forEach(x=>state.seen.add(x.id)); return top;}
function nearMisses(){
  return state.catalog
    .filter(x=>!state.seen.has(x.id))
    .map(x=>({x,fail:failedConstraints(x)}))
    .filter(v=>v.fail.length>0&&v.fail.length<=2)
    .sort((a,b)=>a.fail.length-b.fail.length||score(b.x)-score(a.x))
    .slice(0,3);
}
function reason(x){const p=state.profile;const bits=[];
  if(p.requiredGenres.includes('Romance'))bits.push('恋爱/关系线符合明确要求');
  if(p.requiredSignals.includes('funny'))bits.push('喜剧或好笑特征满足硬条件');
  if(p.requiredSignals.includes('fast'))bits.push('节奏偏快');
  if(p.popularity==='niche'&&['low','medium'].includes(x.pb))bits.push('热度更偏小众');
  if(p.scene&&arr(x.sc).includes(p.scene))bits.push(`适配${labels[p.scene]||p.scene}场景`);
  if(p.moods.length&&overlap(p.moods,arr(x.em))>0)bits.push('情绪氛围匹配');
  if(p.requiredFacts.length&&p.requiredFacts.every(f=>hasFact(x,f)))bits.push('剧情事实边界已命中');
  if(p.platform&&arr(x.pl).includes(p.platform))bits.push(`${labels[p.platform]||p.platform} 平台已验证`);
  if(vectorScore(x)>.25)bits.push('场景特征向量相似度较高');
  if(p.sourceReference&&anchorScore(x)>.15)bits.push(`与《${p.sourceReference}》在类型/氛围上有相似点`);
  return bits.slice(0,3).join('；')||'在当前合法候选里，综合类型、场景和内容理解得分靠前。';}
function profileChips(){const p=state.profile;const raw=[p.companions,p.scene,...p.moods,p.cognitive,...p.contentTypes,...p.requiredGenres,...p.relationship,...p.pace].filter(Boolean);let vals=raw.map(x=>labels[x]||x);if(p.language)vals.push('中文/国产');if(p.sourceReference)vals.push(`类似《${p.sourceReference}》`);if(p.popularity)vals.push(labels[p.popularity]);if(p.runtimeMax)vals.push(`≤ ${p.runtimeMax} 分钟`);if(p.yearMin)vals.push(`${p.yearMin}+`);if(p.platform)vals.push(`只看 ${labels[p.platform]||p.platform}`);if(p.pickOne)vals.push('帮我拍板');p.requiredFacts.forEach(x=>vals.push(labels[x]||x));if(p.explore)vals.push('探索模式');p.avoidGenres.forEach(x=>vals.push(`不要 ${labels[x]||x}`));p.avoidRisks.forEach(x=>vals.push(x==='emotionally_heavy'?'不要太虐':x==='fear_or_horror'?'不要惊吓':`避开 ${x}`));const n=$('#active-profile');n.innerHTML=[...new Set(vals)].map(x=>`<span>${esc(x)}</span>`).join('');n.classList.toggle('hidden',!vals.length)}
function startConversation(){$('#welcome').classList.add('hidden');$('#conversation').classList.remove('hidden')}
function addUser(t){startConversation();$('#messages').insertAdjacentHTML('beforeend',`<div class="turn-user"><p>${esc(t)}</p></div>`)}
function card(x,i){
  const rt=x.rt||x.ert;
  const platformText=arr(x.pl).map(p=>labels[p]||p).join(' / ');
  const meta=[x.y,rt?`${rt} 分钟`:null,labels[x.ct]||x.ct,x.pb==='low'?'偏冷门':x.pb==='high'?'较热门':null].filter(Boolean).join(' · ');
  const tags=[...arr(x.g).slice(0,2),...arr(x.to).slice(0,2),...arr(x.cf).slice(0,2)].map(v=>`<span>${esc(labels[v]||v)}</span>`).join('');
  const rn=arr(x.rn).slice(0,2).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);
  const sn=arr(x.sn).slice(0,2).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);
  const fallback=generatedPoster(x), poster=posterFor(x);
  const proof=state.profile.requiredFacts.length?`<p class="rec-proof"><b>剧情边界</b>${state.profile.requiredFacts.map(f=>esc(labels[f]||f)).join(' · ')} <span>✓</span></p>`:'';
  return `<article class="rec-card"><img class="rec-poster" src="${esc(poster)}" data-fallback="${esc(fallback)}" alt="${esc(x.t)} 海报" loading="lazy" onerror="this.onerror=null;this.src=this.dataset.fallback"><div class="rec-copy"><div class="rec-top"><div><h3 class="rec-title">${i+1}. ${esc(x.t)}</h3><p class="rec-meta">${esc(meta)}${platformText?`<span class="platform-pill">${esc(platformText)}</span>`:''}</p></div><span class="rec-score">${Math.round(Math.min(99,72+score(x)*3))} 匹配</span></div><p class="rec-why">${esc(reason(x))}</p>${proof}${rn.length?`<p class="rec-insight"><b>可能雷点</b>${esc(rn.join(' · '))}</p>`:''}${sn.length?`<p class="rec-insight"><b>无剧透看点</b>${esc(sn.join(' · '))}</p>`:''}<div class="rec-tags">${tags}</div><p class="rec-source">召回：Hard Gate + 稀疏召回 + Scene Vector + Semantic / RRF</p><button class="rec-more" type="button" data-detail="${esc(x.id)}">查看内容依据</button><button class="save-button ${isSaved(x.id)?'saved':''}" type="button" data-save="${esc(x.id)}">${isSaved(x.id)?'已收藏':'收藏'}</button></div></article>`;
}
function socialDiscovery(items){
  if(!items.length)return '';
  const focus=items[0];
  const platform=state.profile.platform?labels[state.profile.platform]:null;
  const sources=[
    ['小红书','合规 Web Search','按片名 + 场景词检索公开索引内容；不直接绕过平台反爬。'],
    ['公众号','合规 Web Search','检索被公开索引的文章与媒体内容，保留原始链接、作者和发布时间。'],
    ['百度','AI Search API','负责中文全网检索、新闻时效与跨站结果；生产端通过服务端 API 调用。'],
    ['X','Recent Search API','通过官方 Posts Search 读取公开讨论、时间和互动指标。']
  ];
  const rows=sources.map(s=>`<div class="social-source"><b>${esc(s[0])} · ${esc(s[1])}</b><p>${esc(s[2])}</p></div>`).join('');
  const platformNote=platform?` 当前仍严格限定在 ${esc(platform)} 已验证可用的候选内。`:'';
  return `<section class="social-discovery"><div class="social-discovery-head"><div><h4>猜你还想确认：《${esc(focus.t)}》在全网为什么被讨论？</h4><p class="social-sub">这里展示联网观点层的来源策略，不伪造实时帖子。生产版会把社媒讨论作为弱排序信号，并保留来源、时间、作者与可信度。${platformNote}</p></div><span class="social-badge">Social Evidence</span></div><div class="social-source-grid">${rows}</div></section>`;
}
function render(items){
  const intro=items.length?'我先锁住平台、剧情事实和风险边界，再做多路召回。社媒热度只影响合法候选内部的排序，不会把别的平台或踩雷内容推回来。':'这组条件没有足够确定的候选，我不会把“未知”冒充“满足”。下面给出最接近但没过线的原因。';
  let body='';
  if(items.length){
    body=`<div class="recommend-list">${items.map(card).join('')}</div>${socialDiscovery(items)}`;
  }else{
    const misses=nearMisses();
    body=`<div class="no-match"><p>没有找到同时满足全部硬条件的候选。</p>${misses.length?`<div class="near-miss"><b>最接近但被拦截</b>${misses.map(({x,fail})=>`<p>《${esc(x.t)}》：缺少/冲突 ${esc(fail.join('、'))}</p>`).join('')}</div>`:''}<p class="rec-source">“未知”不会自动当成“有”：平台可用性、死亡/出轨等剧情事实都需要正向证据。</p></div>`;
  }
  $('#messages').insertAdjacentHTML('beforeend',`<div class="turn-agent"><div class="agent-avatar">影</div><div><p class="agent-intro">${intro}</p>${body}</div></div>`);
  profileChips();
  const qa=['换一批','只替我选一个','不要有人死','结局要圆满','不要跳吓','更小众一点','给我点惊喜'];
  $('#quick-actions').innerHTML=qa.map(x=>`<button type="button" data-prompt="${x}">${x}</button>`).join('');
  $('#quick-actions').classList.remove('hidden');scrollEnd();
}
function scrollEnd(){requestAnimationFrame(()=>window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'}))}
async function sendMessage(text){text=(text||'').trim();if(!text||state.busy)return;state.busy=true;$('#send').disabled=true;addUser(text);$('#message-input').value='';parse(text);const clarify=nextClarification();if(clarify){renderClarify(clarify);}else{render(recommend());}state.busy=false;$('#send').disabled=false;}
function openDetail(id){
  const x=state.catalog.find(v=>v.id===id);if(!x)return;
  const risks=arr(x.rn).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);
  const surprises=arr(x.sn).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);
  const facts=[...factSet(x)].map(v=>labels[v]||v);
  const platforms=arr(x.pl).map(v=>labels[v]||v);
  const fallback=generatedPoster(x);
  $('#detail-body').innerHTML=`<div class="detail"><img src="${esc(posterFor(x))}" data-fallback="${esc(fallback)}" onerror="this.onerror=null;this.src=this.dataset.fallback" alt="${esc(x.t)} 海报"><div><small>${esc([x.y,labels[x.ct],(x.rt||x.ert)?(x.rt||x.ert)+' 分钟':null].filter(Boolean).join(' · '))}</small><h2>${esc(x.t)}</h2><p>${esc(x.d||'暂无简介')}</p><p><strong>平台快照：</strong>${platforms.length?esc(platforms.join(' / ')):'未验证；指定平台时不会把未知当作可用'}</p><p><strong>类型：</strong>${arr(x.g).map(esc).join(' / ')||'未标注'}</p><p><strong>氛围：</strong>${arr(x.to).map(v=>esc(labels[v]||v)).join(' / ')||'暂无'}</p>${facts.length?`<p><strong>结构化剧情事实：</strong>${esc(facts.join(' / '))}</p>`:'<p><strong>结构化剧情事实：</strong>当前证据不足，不把“未知”当成“没有”。</p>'}${risks.length?`<p><strong>可能雷点：</strong>${esc(risks.slice(0,5).join(' / '))}</p>`:'<p><strong>可能雷点：</strong>证据不足，不等于确定没有雷点。</p>'}${surprises.length?`<p><strong>无剧透看点：</strong>${esc(surprises.slice(0,5).join(' / '))}</p>`:''}<button class="save-button ${isSaved(x.id)?'saved':''}" type="button" data-save="${esc(x.id)}">${isSaved(x.id)?'已收藏':'收藏到我的片单'}</button><p><small>内容理解置信度：${Math.round((x.uc||0)*100)}% · 数据层：${esc(x.src||'curated / public metadata')}</small></p></div></div>`;
  $('#detail-dialog').showModal();
}
function reset(){state.profile=freshProfile();state.seen.clear();state.lastQuery='';$('#messages').innerHTML='';$('#conversation').classList.add('hidden');$('#welcome').classList.remove('hidden');$('#active-profile').classList.add('hidden');$('#quick-actions').classList.add('hidden');window.scrollTo({top:0,behavior:'smooth'})}
const FALLBACK_ITEMS=[
{id:"seed:ljx",t:"临江仙",ct:"series",y:2025,co:["中国大陆"],g:["Drama","Romance"],d:"相爱相杀的仙侠关系线，重点在误解、共同经历与关系修复。",ert:45,p:"https://static.tvmaze.com/uploads/images/original_untouched/571/1429084.jpg",sc:["solo"],em:["romantic"],cl:"medium",pa:["moderate"],ri:["romance_theme"],re:["romantic"],to:["romantic"],pb:"low",uc:.82},
{id:"seed:wzxh",t:"我只喜欢你",ct:"series",y:2019,co:["中国大陆"],g:["Drama","Romance"],d:"从校园到职场的成长型恋爱故事，关系线是明确主轴。",ert:45,p:"https://static.tvmaze.com/uploads/images/original_untouched/198/495887.jpg",sc:["solo"],em:["romantic"],cl:"medium",pa:["moderate"],ri:["romance_theme"],re:["romantic"],to:["romantic","warm"],pb:"low",uc:.82},
{id:"seed:sx",t:"失笑",ct:"series",y:2024,co:["中国大陆"],g:["Romance","Comedy"],d:"脱口秀演员与情绪表达困难的男性相遇，在都市生活里逐渐靠近。",ert:45,p:"https://static.tvmaze.com/uploads/images/original_untouched/539/1349951.jpg",sc:["solo","friends"],em:["funny","light","relaxing","romantic"],cl:"low",pa:["lively"],ri:["romance_theme"],re:["romantic"],to:["romantic","playful","warm"],pb:"low",uc:.82},
{id:"seed:kd",t:"开端",ct:"series",y:2022,co:["中国大陆"],g:["Drama","Science-Fiction","Thriller"],d:"公交爆炸后的时间循环，两位普通人反复寻找阻止事故与接近真相的方法。",ert:44,p:"https://static.tvmaze.com/uploads/images/original_untouched/389/974203.jpg",ra:7.8,sc:["solo"],em:["exciting","tense"],cl:"high",pa:["fast"],ri:["violence_possible"],to:["dark"],pb:"low",uc:.8},
{id:"seed:cang",t:"偷偷藏不住",ct:"series",y:2023,co:["中国大陆"],g:["Comedy","Romance"],d:"从暗恋到成年后的再次靠近，整体偏轻松、甜感和日常陪伴。",ert:45,p:"https://static.tvmaze.com/uploads/images/original_untouched/465/1164886.jpg",ra:8,sc:["solo","friends"],em:["funny","light","relaxing","romantic"],cl:"low",pa:["lively"],ri:["romance_theme"],re:["romantic"],to:["romantic","playful","warm","sweet"],pb:"low",uc:.82},
{id:"seed:feiben",t:"当我飞奔向你",ct:"series",y:2023,co:["中国大陆"],g:["Comedy","Romance"],d:"青春校园关系线，明亮外向与克制内向的性格差构成主要看点。",ert:45,p:"https://static.tvmaze.com/uploads/images/original_untouched/464/1162285.jpg",sc:["solo","friends"],em:["funny","light","relaxing","romantic"],cl:"low",pa:["lively"],ri:["romance_theme"],re:["friendship","romantic"],to:["romantic","playful","warm","sweet"],pb:"medium",uc:.82},
{id:"seed:atm2",t:"ATM 2 Romance Error",ct:"series",y:2014,co:["Thailand"],g:["Drama","Comedy","Romance"],d:"职场情侣因为公司禁止内部恋爱而陷入又甜又闹的关系博弈。",ert:45,p:"https://static.tvmaze.com/uploads/images/original_untouched/13/33933.jpg",sc:["solo","friends"],em:["funny","light","relaxing","romantic"],cl:"low",pa:["lively"],ri:["romance_theme"],re:["romantic"],to:["romantic","playful","warm"],pb:"low",uc:.8},
{id:"seed:greatestlove",t:"The Greatest Love",ct:"series",y:2011,co:["Korea, Republic of"],g:["Drama","Comedy","Romance"],d:"过气女歌手与顶级明星之间的浪漫喜剧，娱乐圈身份差与关系拉扯是主线。",ert:70,p:"https://static.tvmaze.com/uploads/images/original_untouched/459/1149924.jpg",ra:6.9,sc:["solo","friends"],em:["funny","light","relaxing","romantic"],cl:"low",pa:["lively"],ri:["romance_theme"],re:["romantic"],to:["romantic","playful","warm"],pb:"low",uc:.8},
{id:"seed:kf",t:"功夫",ct:"movie",y:2004,co:["中国大陆"],g:["Action","Comedy","Fantasy"],d:"小人物误入高手云集的社区，在夸张武术、黑帮冲突与喜剧节奏中改变自己。",rt:99,p:"https://commons.wikimedia.org/wiki/Special:FilePath/ChowKL2.JPG",sc:["friends","weekend"],em:["exciting","funny","light","relaxing"],cl:"low",pa:["fast","lively"],ri:["violence_possible"],to:["playful","warm"],pb:"unknown",uc:.7},
{id:"seed:citylights",t:"城市之光",ct:"movie",y:1931,co:["United States"],g:["Comedy","Drama","Romance"],d:"流浪汉与盲女之间温柔又克制的关系故事，喜剧外壳下有很强的情感后劲。",rt:87,p:"https://commons.wikimedia.org/wiki/Special:FilePath/City%20Lights%20%281931%20theatrical%20poster%20-%20retouched%29.jpg",sc:["solo","couple"],em:["funny","romantic","warm"],cl:"low",pa:["moderate"],ri:["emotionally_heavy","romance_theme"],re:["romantic"],to:["warm","bittersweet"],pb:"medium",uc:.75},
{id:"seed:crashers",t:"冒牌伴郎生擒姊妹團",ct:"movie",y:2005,co:["United States"],g:["Comedy","Romance"],d:"两个婚礼蹭客在一次婚礼上卷入真正的感情关系，偏闹腾的浪漫喜剧。",rt:119,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Wedding%20Crashers.png",sc:["friends"],em:["funny","light","romantic"],cl:"low",pa:["lively"],ri:["mature_rating","romance_theme"],re:["romantic"],to:["playful"],pb:"medium",uc:.7},
{id:"seed:cyrano",t:"大鼻子情聖",ct:"movie",y:1990,co:["France"],g:["Comedy","Drama","Romance"],d:"才华横溢却自卑的诗人替他人写情书追求自己深爱的人，爱情与自我认同并行。",rt:137,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Depardieu%20Cannes%20Cyrano.jpg",sc:["solo","couple"],em:["romantic"],cl:"medium",pa:["moderate"],ri:["emotionally_heavy","romance_theme"],re:["romantic"],to:["bittersweet"],pb:"low",uc:.72},
{id:"seed:wings",t:"柏林蒼穹下",ct:"movie",y:1987,co:["Germany"],g:["Drama","Fantasy","Romance"],d:"天使旁观城市众生，并因爱意产生进入人间生活的愿望，气质诗意而克制。",rt:128,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Berlin%20Anhalter%20Bahnhof.jpg",sc:["solo"],em:["romantic","thought_provoking"],cl:"medium",pa:["slow"],ri:["romance_theme"],re:["romantic"],to:["gentle","bittersweet"],pb:"low",uc:.72},
{id:"seed:fiveflowers",t:"五朵金花",ct:"movie",y:1959,co:["中国大陆"],g:["Music","Romance"],d:"以寻找同名姑娘展开的爱情与歌舞故事，具有鲜明年代和地域气质。",rt:105,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Wu%20duo%20Jinhua.jpg",sc:["family","solo"],em:["romantic","light"],cl:"low",pa:["moderate"],ri:["romance_theme"],re:["romantic"],to:["warm"],pb:"low",uc:.68},
{id:"seed:liusan",t:"刘三姐",ct:"movie",y:1960,co:["中国大陆"],g:["Drama","Music","Romance"],d:"以山歌、劳动生活与爱情关系展开的经典歌舞电影。",rt:117,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Li%C3%BA%20S%C4%81n%20Ji%C4%9B.jpg",sc:["family","solo"],em:["romantic"],cl:"low",pa:["moderate"],ri:["romance_theme"],re:["romantic"],to:["warm"],pb:"low",uc:.68},
{id:"seed:strangelove",t:"奇爱博士",ct:"movie",y:1964,co:["United States"],g:["Comedy","War"],d:"以极端黑色幽默处理核战争与制度失控，不是轻松甜喜剧。",rt:95,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Dr.%20Strangelove%20-%20General%20Buck%20Turgidson.png",sc:["friends","solo"],em:["funny","thought_provoking"],cl:"high",pa:["lively"],ri:["violence_possible"],to:["dark","playful"],pb:"medium",uc:.76},
{id:"seed:12angry",t:"十二怒漢",ct:"movie",y:1957,co:["United States"],g:["Drama"],d:"陪审团围绕一桩案件展开高密度讨论，几乎完全依靠人物观点与推理推进。",rt:96,p:"https://commons.wikimedia.org/wiki/Special:FilePath/12%20Angry%20Men%20%281957%20film%20poster%29.jpg",sc:["solo"],em:["tense","thought_provoking"],cl:"high",pa:["moderate"],ri:[],to:["realistic"],pb:"medium",uc:.8},
{id:"seed:inception",t:"盗梦空间",ct:"movie",y:2010,co:["United States"],g:["Action","Science-Fiction","Thriller"],d:"团队进入多层梦境执行任务，规则、时间层级与信息密度构成主要观看门槛。",rt:148,p:"https://commons.wikimedia.org/wiki/Special:FilePath/InceptionCast2July10.jpg",sc:["solo","friends"],em:["exciting","tense","thought_provoking"],cl:"high",pa:["fast"],ri:["violence_possible"],to:["dark"],pb:"high",uc:.8},
{id:"seed:rashomon",t:"羅生門",ct:"movie",y:1950,co:["Japan"],g:["Crime","Drama","Mystery"],d:"同一事件由不同人物给出互相冲突的叙述，核心是视角、真相与人性判断。",rt:88,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Rashomon%20%281950%29%20Press%20Photo%20of%20Toshiro%20Mifune%20and%20Machiko%20Ky%C5%8D.jpg",sc:["solo"],em:["tense","thought_provoking"],cl:"high",pa:["moderate"],ri:["violence_possible"],to:["dark"],pb:"low",uc:.78},
{id:"seed:2001",t:"2001太空漫遊",ct:"movie",y:1968,co:["United Kingdom","United States"],g:["Adventure","Mystery","Science-Fiction"],d:"以宇宙探索、人工智能与人类演化为核心，节奏慢、留白多、需要较高耐心。",rt:149,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Photo%20A%20scene%20from%202001.%20A%20Space%20Odyssey%2C%20a%201968%20film%20directed%20by%20Stanley%20Kubrick%201968%20-%20Touring%20Club%20Italiano%2004%200826.jpg",sc:["solo"],em:["thought_provoking"],cl:"high",pa:["slow"],ri:[],to:["gentle"],pb:"medium",uc:.8},
{id:"seed:avatar",t:"阿凡達",ct:"movie",y:2009,co:["United States"],g:["Action","Adventure","Science-Fiction"],d:"异星世界、殖民冲突与沉浸式视觉构成主要体验，适合大屏和朋友观看。",rt:162,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Avatar%20Flight%20of%20Passage%20%2833825582954%29.jpg",sc:["friends","weekend"],em:["exciting"],cl:"medium",pa:["fast"],ri:["violence_possible"],to:["warm"],pb:"high",uc:.75},
{id:"seed:tokyo",t:"東京物語",ct:"movie",y:1953,co:["Japan"],g:["Drama","Family"],d:"老年父母探望成年子女的家庭故事，节奏克制，情感并不轻飘。",rt:136,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Tokyo%20Monogatari%201953.jpg",sc:["solo","family"],em:["thought_provoking"],cl:"medium",pa:["slow"],ri:["emotionally_heavy"],re:["family"],to:["gentle","bittersweet"],pb:"low",uc:.8},
{id:"seed:kickass",t:"特攻聯盟",ct:"movie",y:2010,co:["United States","United Kingdom"],g:["Action","Comedy","Crime"],d:"普通人模仿超级英雄引发失控冲突，喜剧与高强度暴力并存。",rt:117,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Kick-ass.svg",sc:["friends"],em:["funny","exciting"],cl:"low",pa:["fast","lively"],ri:["violence_possible","mature_rating"],to:["playful","dark"],pb:"medium",uc:.72},
{id:"seed:childrenmen",t:"人類之子",ct:"movie",y:2006,co:["United Kingdom","United States"],g:["Drama","Science-Fiction","Thriller"],d:"在全球失去生育能力的近未来社会，一次护送任务牵动政治与人道危机。",rt:109,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Children%20of%20Men%20Baby.JPG",sc:["solo"],em:["tense","thought_provoking"],cl:"high",pa:["fast"],ri:["violence_possible","emotionally_heavy"],to:["dark"],pb:"medium",uc:.78},
{id:"seed:caligari",t:"卡里加里博士的小屋",ct:"movie",y:1920,co:["Germany"],g:["Horror","Mystery","Thriller"],d:"德国表现主义经典，视觉、心理不安与不可靠叙事是主要体验。",rt:77,p:"https://commons.wikimedia.org/wiki/Special:FilePath/Das%20Cabinet%20des%20Dr.%20Caligari.JPG",sc:["solo"],em:["scary","tense"],cl:"high",pa:["moderate"],ri:["fear_or_horror"],to:["dark"],pb:"low",uc:.78}

,{id:"cn26:jingzhe",t:"惊蛰无声",ct:"movie",y:2026,co:["中国大陆"],g:["Thriller","Crime","Action"],d:"国安小组围绕重要情报外泄展开调查，在无声较量中追查风险源。",rt:115,p:"",sc:["solo","friends"],em:["tense","exciting"],cl:"high",pa:["fast"],ri:["violence_possible"],re:["team"],to:["realistic","dark"],cf:["closed_ending"],rn:["涉及谍战、追查与潜在暴力情境"],sn:["现实题材的高压调查感"],pb:"high",uc:.72,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:biaoren",t:"镖人：风起大漠",ct:"movie",y:2026,co:["中国大陆"],g:["Action","Adventure","Drama"],d:"大漠镖客受托护送神秘人物前往长安，途中遭遇围剿与宿命牵连。",rt:125,p:"",sc:["friends","weekend"],em:["exciting","tense"],cl:"medium",pa:["fast"],ri:["violence_possible"],to:["dark"],cf:[],rn:["武侠动作与围剿场面较多"],sn:["大漠武侠、公路护送与群像关系"],pb:"high",uc:.72,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:feichi3",t:"飞驰人生3",ct:"movie",y:2026,co:["中国大陆"],g:["Comedy","Drama","Sport"],d:"最后一届巴音布鲁克拉力赛落幕后，赛车手回到现实并面对新的生活与竞技挑战。",rt:120,p:"",sc:["friends","family","weekend"],em:["funny","light","exciting"],cl:"low",pa:["fast","lively"],ri:[],to:["playful","warm"],cf:["no_gore","no_jump_scares"],rn:["赛车运动存在紧张和事故风险"],sn:["赛车喜剧与现实生活的反差"],pb:"high",uc:.7,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:xinghe",t:"星河入梦",ct:"movie",y:2026,co:["中国大陆"],g:["Science-Fiction","Adventure","Comedy"],d:"近未来虚拟梦境系统“良梦”中，管理员与舰长穿梦闯关，展开脑洞型冒险。",rt:118,p:"",sc:["friends","weekend"],em:["exciting","funny","thought_provoking"],cl:"medium",pa:["fast"],ri:[],to:["playful","stylized"],cf:["no_gore"],rn:["包含虚拟梦境危机场景"],sn:["梦境世界与现实规则之间的设定玩法"],pb:"high",uc:.72,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:panda",t:"熊猫计划之部落奇遇记",ct:"movie",y:2026,co:["中国大陆"],g:["Comedy","Adventure","Family"],d:"熊猫胡胡与国际巨星意外进入神奇部落，在冒险中帮助部落解决难题。",rt:100,p:"",sc:["family","friends"],em:["funny","light","relaxing"],cl:"low",pa:["lively"],ri:[],to:["playful","warm"],cf:["family_safe","no_gore","no_jump_scares","no_sexual_content","no_infidelity"],rn:["家庭向冒险中的轻度危机"],sn:["真人与熊猫的错位组合"],pb:"high",uc:.68,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:boonie",t:"熊出没·年年有熊",ct:"movie",y:2026,co:["中国大陆"],g:["Animation","Comedy","Family","Adventure"],d:"不速之客引发危机后，熊大、熊二和光头强再次合作化解问题。",rt:99,p:"",sc:["family"],em:["funny","light","relaxing"],cl:"low",pa:["lively"],ri:[],to:["playful","warm"],cf:["family_safe","no_gore","no_sexual_content","no_infidelity"],rn:["动画冒险中有轻度危机"],sn:["熟人角色组合与合家欢冒险"],pb:"high",uc:.7,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:qunxing",t:"群星闪耀时",ct:"movie",y:2026,co:["中国大陆"],g:["Science-Fiction","Adventure","Drama"],d:"航天员在太空遭遇险情，并收到来自过去的神秘电子信号，需要破译信号援救未来。",rt:125,p:"",sc:["friends","solo"],em:["tense","exciting","thought_provoking"],cl:"high",pa:["fast"],ri:["violence_possible"],to:["realistic"],cf:[],rn:["太空险情与生存压力"],sn:["跨时间信号与航天救援"],pb:"medium",uc:.7,src:"国家电影局 2026 暑期档片单"}
,{id:"cn26:jiaye",t:"家业",ct:"series",y:2026,co:["中国大陆"],g:["Drama","History","Romance"],d:"明朝徽州贡墨案后，李祯以制墨天赋重振家业，并与骆文谦从竞争走向合作。",ert:45,p:"",ra:8.8,sc:["solo","family"],em:["romantic","thought_provoking"],cl:"medium",pa:["moderate"],ri:["emotionally_heavy"],re:["romantic","family"],to:["realistic","warm"],cf:["happy_ending","closed_ending","career_central","romance_central"],rn:["家族兴衰、竞争和阶段性死亡/离别议题"],sn:["非遗制墨、女性事业成长与合作型关系"],pb:"high",uc:.88,src:"爱奇艺 2026 正片页",pl:["iqiyi"]}

,{id:"cn26:yiouchun",t:"一瓯春",ct:"series",y:2026,co:["中国大陆"],g:["Drama","Romance","History"],d:"谢清圆与沈润在高门与朝堂暗流中互相试探、携手复仇，并最终走向新生。",ert:45,p:"",sc:["solo"],em:["romantic","tense"],cl:"medium",pa:["moderate"],ri:["violence_possible","emotionally_heavy"],re:["romantic"],to:["realistic","dark","bittersweet"],cf:["happy_ending","closed_ending","romance_central"],rn:["复仇、权谋与暴力情节；不是纯甜恋爱"],sn:["双强关系与复仇线并进"],pb:"high",uc:.86,src:"爱奇艺 2026 正片页",pl:["iqiyi"]}
,{id:"cn26:shenyuan",t:"深渊无间",ct:"series",y:2026,co:["中国大陆"],g:["Thriller","Mystery","Crime"],d:"推理网文与多年悬案细节高度重合，新警李成在多方嫌疑人之间展开高智对弈。",ert:45,p:"",sc:["solo"],em:["tense","thought_provoking"],cl:"high",pa:["fast"],ri:["violence_possible","emotionally_heavy"],to:["dark","realistic"],cf:["closed_ending"],rn:["悬案、犯罪与令人扼腕的亲情友情真相"],sn:["网文与真实悬案互相映照的元叙事入口"],pb:"high",uc:.86,src:"爱奇艺 2026 正片页",pl:["iqiyi"]}
,{id:"safe:intern",t:"实习生",ct:"movie",y:2015,co:["United States"],g:["Comedy","Drama"],d:"退休老人进入互联网创业公司成为高龄实习生，在代际相处中重新找到生活节奏。",rt:121,p:"",sc:["solo","family"],em:["funny","light","relaxing","healing"],cl:"low",pa:["moderate"],ri:[],re:["friendship","workplace"],to:["warm","gentle"],cf:["no_character_death","no_animal_harm","no_gore","no_jump_scares","no_sexual_content","no_infidelity","family_safe","closed_ending"],rn:["存在婚姻关系压力，但不是暴力或惊吓型内容"],sn:["代际友谊和职场陪伴感"],pb:"medium",uc:.76,src:"demo curated content-facts"}
,{id:"safe:chef",t:"落魄大厨",ct:"movie",y:2014,co:["United States"],g:["Comedy","Drama"],d:"厨师离开受挫的餐厅工作后开起餐车，与家人和朋友重新建立连接。",rt:114,p:"",sc:["solo","family","friends"],em:["funny","light","relaxing","healing"],cl:"low",pa:["lively"],ri:[],re:["family","friendship"],to:["warm","playful"],cf:["no_character_death","happy_ending","no_gore","no_jump_scares","closed_ending"],rn:["少量成人语言"],sn:["美食、公路与亲子关系的修复"],pb:"medium",uc:.78,src:"demo curated content-facts"}
,{id:"safe:legally",t:"律政俏佳人",ct:"movie",y:2001,co:["United States"],g:["Comedy","Romance"],d:"女主因感情挫折进入法学院，逐步把外界偏见转化成自我证明。",rt:96,p:"",sc:["solo","friends"],em:["funny","light","relaxing"],cl:"low",pa:["lively"],ri:[],re:["romantic","friendship"],to:["playful","warm"],cf:["no_character_death","happy_ending","no_gore","no_jump_scares","closed_ending"],rn:["有情感分手和轻度成人话题"],sn:["从恋爱动机转向自我成长"],pb:"medium",uc:.78,src:"demo curated content-facts"}
,{id:"safe:schoolrock",t:"摇滚校园",ct:"movie",y:2003,co:["United States"],g:["Comedy","Music","Family"],d:"失意乐手冒充代课老师，把一群孩子组织成摇滚乐队。",rt:109,p:"",sc:["family","friends"],em:["funny","light","relaxing"],cl:"low",pa:["lively"],ri:[],re:["friendship"],to:["playful","warm"],cf:["no_character_death","no_gore","no_jump_scares","no_sexual_content","no_infidelity","family_safe","closed_ending"],rn:["有撒谎与学校规则冲突"],sn:["音乐排练、群体协作与舞台释放"],pb:"medium",uc:.78,src:"demo curated content-facts"}
,{id:"safe:paddington2",t:"帕丁顿熊2",ct:"movie",y:2017,co:["United Kingdom"],g:["Comedy","Family","Adventure"],d:"帕丁顿为了买礼物努力打工，却被卷入误会，需要家人与朋友帮忙找出真相。",rt:103,p:"",sc:["family","friends"],em:["funny","light","relaxing","healing"],cl:"low",pa:["lively"],ri:[],re:["family","friendship"],to:["warm","playful"],cf:["no_character_death","happy_ending","no_gore","no_jump_scares","no_sexual_content","no_infidelity","family_safe","closed_ending"],rn:["包含轻度追逐、误会和监狱情节"],sn:["极高善意密度和群像回馈"],pb:"medium",uc:.82,src:"demo curated content-facts"}
,{id:"safe:kiki",t:"魔女宅急便",ct:"movie",y:1989,co:["Japan"],g:["Animation","Family","Fantasy"],d:"年轻魔女离家修行，在海边城市经营送货服务并度过自我怀疑期。",rt:103,p:"",sc:["solo","family"],em:["light","relaxing","healing"],cl:"low",pa:["moderate"],ri:[],re:["friendship"],to:["gentle","warm"],cf:["no_character_death","no_gore","no_jump_scares","family_safe","closed_ending"],rn:["后段有短暂高空救援危机"],sn:["成长焦虑被处理得非常轻盈"],pb:"medium",uc:.82,src:"demo curated content-facts"}
,{id:"safe:yearmeeting",t:"年会不能停！",ct:"movie",y:2023,co:["中国大陆"],g:["Comedy","Drama"],d:"普通工人阴差阳错进入集团总部，在荒诞职场流程中一路被误认为管理人才。",rt:117,p:"",sc:["friends","solo"],em:["funny","light"],cl:"low",pa:["lively"],ri:[],re:["workplace","friendship"],to:["playful","realistic"],cf:["no_character_death","no_gore","no_jump_scares","closed_ending"],rn:["职场裁员、权力压迫和高强度社畜共鸣"],sn:["流程荒诞和组织语言错位"],pb:"high",uc:.76,src:"demo curated content-facts"}
];

function stripHtml(s){const d=document.createElement('div');d.innerHTML=String(s||'');return (d.textContent||'').replace(/\s+/g,' ').trim();}
function inferLive(show){
  const genres=arr(show.genres), low=genres.includes('Comedy')||genres.includes('Family')||genres.includes('Reality');
  const high=genres.some(g=>['Thriller','Mystery','Science-Fiction','Crime','Horror','Action'].includes(g));
  const em=[]; const ri=[]; const re=[]; const to=[]; const pa=[];
  if(genres.includes('Comedy'))em.push('funny','light','relaxing');
  if(genres.includes('Romance')){em.push('romantic');ri.push('romance_theme');re.push('romantic');to.push('romantic');}
  if(genres.some(g=>['Action','Thriller','Adventure'].includes(g))){em.push('exciting','tense');pa.push('fast');}
  if(genres.includes('Horror')){em.push('scary','tense');ri.push('fear_or_horror');to.push('dark');}
  if(genres.some(g=>['Crime','Action','War'].includes(g)))ri.push('violence_possible');
  if(!pa.length)pa.push(low?'lively':'moderate');
  return {em:[...new Set(em)],ri:[...new Set(ri)],re:[...new Set(re)],to:[...new Set(to)],pa,cl:high&&!low?'high':low?'low':'medium'};
}
function normalizePlatform(name){const n=lower(name).replace(/\s+/g,'');if(n.includes('iqiyi'))return 'iqiyi';if(n.includes('tencent')||n.includes('wetv'))return 'tencent_video';if(n.includes('youku'))return 'youku';if(n.includes('mango'))return 'mango_tv';if(n.includes('netflix'))return 'netflix';if(n.includes('disney'))return 'disney_plus';if(n.includes('amazon')||n.includes('primevideo'))return 'prime_video';if(n==='max'||n.includes('hbomax'))return 'max';return null;}
async function fetchJson(url,ms=12000){const ctl=new AbortController();const t=setTimeout(()=>ctl.abort(),ms);try{const r=await fetch(url,{signal:ctl.signal,headers:{Accept:'application/json'}});if(!r.ok)throw new Error(r.status);return await r.json();}finally{clearTimeout(t)}}
async function loadLiveCatalog(){
  const pages=[0,1,2,3];
  const settled=await Promise.allSettled(pages.map(p=>fetchJson('https://api.tvmaze.com/shows?page='+p,15000)));
  const shows=settled.flatMap(x=>x.status==='fulfilled'&&Array.isArray(x.value)?x.value:[]);
  const mapped=shows.map(s=>{
    const inf=inferLive(s);
    const country=s.network?.country?.name||s.webChannel?.country?.name||'';
    const type=(s.type==='Reality'||s.type==='Game Show'||s.type==='Talk Show')?'variety':(arr(s.genres).includes('Animation')?'animation':'series');
    const sourcePlatform=normalizePlatform(s.webChannel?.name||s.network?.name||''); const item={id:'tvmaze-live:'+s.id,t:s.name,ot:s.name,ct:type,y:Number((s.premiered||'').slice(0,4))||null,co:country?[country]:[],g:arr(s.genres),d:stripHtml(s.summary).slice(0,420),ert:s.averageRuntime||s.runtime||null,p:s.image?.original||s.image?.medium||'',ra:s.rating?.average??null,sc:type==='variety'?['friends','party']:['solo'],...inf,pb:(s.weight||0)>85?'high':(s.weight||0)>45?'medium':'low',uc:.62,cf:[],pl:sourcePlatform?[sourcePlatform]:[]}; item.p=item.p||generatedPoster(item); return item;
  });
  const byId=new Map(FALLBACK_ITEMS.map(x=>[x.id,{...x,p:posterFor(x),pl:arr(x.pl)}])); for(const x of mapped)if(!byId.has(x.id))byId.set(x.id,x);
  const items=[...byId.values()].map(x=>({...x,p:posterFor(x),pl:arr(x.pl)}));
  if(items.length<150)throw new Error('live catalog too small');
  return {version:'live-tvmaze-plus-curated',count:items.length,full_catalog_count:3339,items};
}
async function loadCatalog(){
  try{return await loadLiveCatalog();}
  catch(e){console.warn('Live catalog unavailable; using curated fallback.',e);const items=FALLBACK_ITEMS.map(x=>({...x,p:posterFor(x),pl:arr(x.pl)}));return {version:'curated-fallback',count:items.length,full_catalog_count:3339,items};}
}
async function init(){
  loadAccount();renderCommunity();
  try{
    const data=await loadCatalog();
    state.catalog=data.items||[];
    renderCollection();
    $('#catalog-status').innerHTML=`<i></i>${state.catalog.length.toLocaleString()} 部内容 · 海报 100% · 多通道召回`;
    $('#starter-grid').innerHTML=starters.map(x=>`<button class="starter" type="button" data-prompt="${esc(x)}">${esc(x)}</button>`).join('');
  }catch(e){console.error(e);toast('片库加载失败，请刷新页面')}
}
document.addEventListener('click',e=>{
  const p=e.target.closest('[data-prompt]');
  if(p){
    const community=$('#community-dialog');if(community&&community.open)community.close();
    sendMessage(p.dataset.prompt);
  }
  const d=e.target.closest('[data-detail]');if(d)openDetail(d.dataset.detail);
  const s=e.target.closest('[data-save]');if(s)toggleSave(s.dataset.save);
});
$('#composer').addEventListener('submit',e=>{e.preventDefault();sendMessage($('#message-input').value)});
$('#message-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage(e.target.value)}});
$('#new-chat').addEventListener('click',reset);
$('#detail-close').addEventListener('click',()=>$('#detail-dialog').close());
$('#account-button').addEventListener('click',()=>{
  if(account.user){$('#auth-name').value=account.user.name;$('#auth-email').value=account.user.email}
  syncAccountUI();$('#auth-dialog').showModal();
});
$('#auth-close').addEventListener('click',()=>$('#auth-dialog').close());
$('#collection-button').addEventListener('click',()=>{renderCollection();$('#collection-dialog').showModal()});
$('#collection-close').addEventListener('click',()=>$('#collection-dialog').close());
$('#community-button').addEventListener('click',()=>{renderCommunity();$('#community-dialog').showModal()});
$('#community-close').addEventListener('click',()=>$('#community-dialog').close());
$('#auth-form').addEventListener('submit',e=>{
  e.preventDefault();
  const name=$('#auth-name').value.trim(),email=$('#auth-email').value.trim().toLowerCase();
  if(!name||!email)return;
  account.user={name,email};storeSet('user',account.user);account.watchlist=storeGet(accountKey(),[]);
  syncAccountUI();renderCollection();$('#auth-dialog').close();toast('本地 Demo 账户已登录');
});
$('#auth-logout').addEventListener('click',()=>{
  storeSet('user',null);account.user=null;account.watchlist=[];syncAccountUI();renderCollection();
  $('#auth-name').value='';$('#auth-email').value='';$('#auth-dialog').close();toast('已退出本地 Demo 账户');
});
init();
