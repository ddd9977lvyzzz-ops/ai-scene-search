const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const labels={solo:'自己看',family:'和家人',friends:'和朋友',couple:'和对象',weekend:'周末',party:'聚会',late_night:'睡前',meal:'饭后',light:'轻松',relaxing:'放松',healing:'治愈',funny:'好笑',exciting:'刺激',tense:'紧张',thought_provoking:'烧脑',romantic:'恋爱感',movie:'电影',series:'电视剧',variety:'综艺',animation:'动漫',documentary:'纪录片',low:'低负担',high:'高信息量',Romance:'恋爱/爱情',Comedy:'喜剧',Thriller:'悬疑',Mystery:'推理',Action:'动作',Horror:'恐怖',niche:'小众优先',mainstream:'热门优先',sweet:'偏甜',gentle:'温柔',realistic:'现实',bittersweet:'苦甜',dark:'偏暗黑',playful:'轻快',warm:'温暖',precise:'精准匹配',balanced:'适度探索',explore:'探索模式',no_character_death:'没有角色死亡',happy_ending:'明确偏圆满',no_animal_harm:'无动物伤害',no_infidelity:'无出轨主线',no_gore:'无血腥重点',no_jump_scares:'无跳吓重点',no_sexual_content:'无明显大尺度',family_safe:'家庭共看友好',closed_ending:'结局收束',romance_central:'恋爱主线',friendship_central:'友情主线',career_central:'事业成长',social_embarrassment:'尴尬/社死桥段',violence_possible:'暴力内容',emotionally_heavy:'情绪沉重',fear_or_horror:'恐怖/惊吓',iqiyi:'爱奇艺',tencent_video:'腾讯视频',youku:'优酷',mango_tv:'芒果TV',netflix:'Netflix',disney_plus:'Disney+',max:'Max',prime_video:'Prime Video'};
const starters=[
  '今天下班很累，想看轻松一点的','我只看爱奇艺，想找2026年的国产剧','和朋友聚会，想看轻松好笑的电影',
  '和家人一起看，想找温暖一点的','像《功夫》一样有喜剧节奏，但换个题材','周末想看悬疑一点，但别太吓人',
  '最近想探索小众一点的华语电影','别给我列表，直接替我选一部','想看一部90分钟左右、不拖沓的电影',
  '想找适合雨天一个人看的电影','今天情绪有点低，想看温柔但不煽情的','想看高信息量、需要认真看的悬疑片',
  '和对象看，想浪漫一点但不要俗套','最近只想看2026年新出的国产内容','给我一部视觉很好看的科幻片',
  '想找友情线很强、恋爱线很弱的作品','周末下午想看慢一点、有余味的电影','想看女性成长题材，但不要鸡汤感',
  '吃饭的时候看，最好能随时暂停','想看一部气质很特别但不晦涩的电影','今晚想看爽一点的，但不要太吵',
  '想找节奏舒缓、画面很美的剧','最近想补一部被低估的经典','看完想有点讨论空间，但别太沉重'
];
const CONFIG=window.YING_CONFIG||{apiBase:'',preferBackend:false,pagesPreview:true};
const state={catalog:[],profile:freshProfile(),seen:new Set(),busy:false,lastQuery:'',backendReady:false,backendSession:null,agentMode:'local-retrieval'};
const STORAGE_PREFIX='ying:v1:';
const account={user:null,watchlist:[],token:null};
const COMMUNITY_SCENES=[
  {id:'parents-safe',title:'和爸妈看，不尴尬',desc:'避开明显大尺度、跳吓和尴尬桥段，优先轻松、家庭共看友好。',tags:['家庭共看','低尴尬','轻松'],prompt:'和爸妈一起看，轻松一点，不要尴尬也不要大尺度'},
  {id:'zero-death',title:'今晚不要有人死',desc:'把“没有角色死亡”当成剧情事实硬条件；未知不会自动当安全。',tags:['没人死','低压力','硬边界'],prompt:'我想看没有任何人死去的电影，最好结局也圆满'},
  {id:'weekday-90',title:'工作日 90 分钟以内',desc:'短时长、低认知负荷，适合下班后不想做复杂选择的时候。',tags:['≤90min','低负担','工作日'],prompt:'工作日晚上一个人看，90分钟以内，不想动脑'},
  {id:'friends-laugh',title:'朋友聚会先把气氛带起来',desc:'优先笑点密度与可打断性，不把高压剧情当成“刺激=适合聚会”。',tags:['朋友','好笑','可打断'],prompt:'和朋友聚会，想看轻松好笑的电影'}
];
function apiUrl(path){const base=(CONFIG.apiBase||'').replace(/\/$/,'');return base+path}
async function initBackend(){
  if(!CONFIG.preferBackend||!CONFIG.apiBase)return false;
  try{
    const r=await fetch(apiUrl('/health'),{headers:{Accept:'application/json'}});
    if(!r.ok)return false;
    const data=await r.json();
    state.backendReady=Boolean(data.openai_agent_enabled);
    state.agentMode=data.agent_mode||'backend';
    return state.backendReady;
  }catch(e){return false}
}
async function ensureBackendSession(){
  if(!state.backendReady)return null;
  if(state.backendSession)return state.backendSession;
  const r=await fetch(apiUrl('/v1/sessions'),{method:'POST',headers:{'Content-Type':'application/json'}});
  if(!r.ok)throw new Error('session_create_failed');
  const data=await r.json();state.backendSession=data.session_id;return state.backendSession;
}
function syncProfileFromBackend(p,plan){
  if(!p)return;
  state.profile={
    contentTypes:arr(p.content_types),requiredGenres:arr(p.required_genres),avoidGenres:arr(p.avoid_genres),
    requiredSignals:arr(p.required_signals),avoidRisks:arr(p.avoid_risks),requiredFacts:arr(p.required_facts),
    avoidFacts:arr(p.avoid_facts),moods:arr(p.moods),relationship:arr(p.relationship_focus),
    tone:arr(p.tone_preferences),pace:arr(p.pace_preferences),companions:p.companions||null,scene:p.scene||null,
    cognitive:p.cognitive_load||null,popularity:p.popularity_preference||null,language:p.language||null,
    runtimeMax:p.runtime_max||null,yearMin:p.year_min||null,platform:arr(p.platforms)[0]||null,
    explore:(p.exploration_mode||'precise')!=='precise',pickOne:(plan&&plan.decision_style)==='pick_one',
    sourceReference:p.source_reference||null
  };
  profileChips();
}
function backendCatalogItem(r){
  return {
    id:r.content_id,t:r.title,ot:r.original_title||r.title,ct:r.content_type,y:r.release_year,
    rt:r.runtime_minutes,ert:r.episode_runtime_minutes,co:arr(r.countries),g:arr(r.genres),
    d:r.description||'',p:r.poster_url||'',pl:arr(r.platforms),op:arr(r.origin_platforms),
    sc:arr(r.scene_tags),em:arr(r.emotion_tags),cl:r.cognitive_load||null,pa:arr(r.pace_tags),
    ri:arr(r.risk_tags),re:arr(r.relationship_tags),th:arr(r.theme_tags),to:arr(r.tone_tags),
    sn:arr(r.surprise_notes).length?arr(r.surprise_notes):arr(r.surprise_tags),
    rn:arr(r.risk_notes),pb:r.popularity_bucket||'unknown',uc:r.understanding_confidence||r.tag_confidence||.7,
    facts:r.content_facts||{},src:r.source||'canonical FastAPI catalog',sourceUrl:r.source_url||''
  };
}
function mergeCatalogItem(x){
  const existing=state.catalog.findIndex(v=>v.id===x.id);
  if(existing>=0)state.catalog[existing]={...state.catalog[existing],...x};else state.catalog.unshift(x);
  return x;
}
function backendItem(r){
  const x=backendCatalogItem({
    content_id:r.content_id,title:r.title,content_type:r.content_type,release_year:r.release_year,
    runtime_minutes:r.runtime_minutes,genres:r.genres,poster_url:r.poster_url,platforms:r.platforms,
    tone_tags:r.tone_tags,surprise_notes:r.surprises,risk_notes:r.watchouts,
    popularity_bucket:r.popularity_bucket,understanding_confidence:r.evidence_level,
    source:'canonical FastAPI catalog'
  });
  x.backendWhy=r.why||'';
  x.evidence=r.evidence||{};
  return mergeCatalogItem(x);
}
async function loadBackendCatalog(limitPages=5){
  if(!state.backendReady)return null;
  const pages=Array.from({length:limitPages},(_,i)=>i*60);
  const settled=await Promise.allSettled(pages.map(offset=>fetch(apiUrl('/v1/catalog/browse?limit=60&offset='+offset)).then(r=>{
    if(!r.ok)throw new Error('catalog '+r.status);return r.json();
  })));
  const rows=settled.flatMap(x=>x.status==='fulfilled'?arr(x.value.results):[]);
  const items=rows.map(backendCatalogItem).filter(x=>isRealPoster(x.p));
  if(!items.length)throw new Error('backend catalog empty');
  return {version:'backend-canonical',count:items.length,full_catalog_count:null,items};
}
async function backendChat(text){
  const sid=await ensureBackendSession();
  const r=await fetch(apiUrl('/v1/sessions/'+encodeURIComponent(sid)+'/chat'),{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})
  });
  if(!r.ok){const msg=await r.text();throw new Error(msg||('HTTP '+r.status))}
  return await r.json();
}
function renderBackendResponse(data){
  syncProfileFromBackend(data.profile,data.llm_plan);
  if(data.type==='clarify'){
    renderClarify({question:data.question,options:arr(data.options)});
    return;
  }
  if(data.type==='no_match'){
    const html='<div class="turn-agent"><div class="agent-avatar">影</div><div><p class="agent-intro">'+esc(data.suggestion||'这组条件暂时没有可靠候选。')+'</p></div></div>';
    $('#messages').insertAdjacentHTML('beforeend',html);profileChips();scrollEnd();return;
  }
  const items=arr(data.results).map(backendItem);
  render(items,data.assistant_message||data.decision_summary||null);
  const actions=arr(data.follow_up_suggestions).length?data.follow_up_suggestions:data.quick_actions;
  if(actions&&actions.length)$('#quick-actions').innerHTML=actions.slice(0,6).map(x=>'<button type="button" data-prompt="'+esc(x)+'">'+esc(x)+'</button>').join('');
}
function storeGet(key,fallback){try{const v=localStorage.getItem(STORAGE_PREFIX+key);return v?JSON.parse(v):fallback}catch(e){return fallback}}
function storeSet(key,value){try{localStorage.setItem(STORAGE_PREFIX+key,JSON.stringify(value))}catch(e){}}
function accountKey(){return account.user&&account.user.email?'watchlist:'+account.user.email:'watchlist:guest'}
function loadAccount(){account.user=storeGet('user',null);account.token=storeGet('auth_token',null);account.watchlist=storeGet(accountKey(),[]);syncAccountUI()}
async function syncAccountFromBackend(){if(!state.backendReady||!account.token)return;try{const r=await fetch(apiUrl('/v1/me'),{headers:{Authorization:'Bearer '+account.token}});if(!r.ok)throw new Error('auth');const data=await r.json();account.user={name:data.user.display_name,email:data.user.email,user_id:data.user.user_id};account.watchlist=arr(data.watchlist);const wr=await fetch(apiUrl('/v1/me/watchlist'),{headers:{Authorization:'Bearer '+account.token}});if(wr.ok){const wd=await wr.json();arr(wd.items).forEach(v=>mergeCatalogItem(backendCatalogItem(v)))}storeSet('user',account.user);storeSet(accountKey(),account.watchlist);syncAccountUI();renderCollection()}catch(e){account.token=null;storeSet('auth_token',null)}}
function syncAccountUI(){const b=$('#account-button'),logout=$('#auth-logout');if(b)b.textContent=account.user&&account.user.name?account.user.name:'登录';if(logout)logout.classList.toggle('hidden',!account.user)}
function isSaved(id){return account.watchlist.indexOf(id)>=0}
async function toggleSave(id){
  if(!account.user){$('#auth-dialog').showModal();toast('先登录，再保存片单');return}
  const wasSaved=isSaved(id);
  if(state.backendReady&&account.token){
    try{
      const r=await fetch(apiUrl('/v1/me/watchlist/'+encodeURIComponent(id)),{
        method:wasSaved?'DELETE':'POST',headers:{Authorization:'Bearer '+account.token}
      });
      if(!r.ok)throw new Error('watchlist_sync_failed');
    }catch(e){toast('片单同步失败，请稍后重试');return}
  }
  account.watchlist=wasSaved?account.watchlist.filter(function(x){return x!==id}):account.watchlist.concat([id]);
  storeSet(accountKey(),account.watchlist);renderCollection();toast(isSaved(id)?'已加入我的片单':'已取消收藏');
  document.querySelectorAll('[data-save]').forEach(function(btn){if(btn.dataset.save===id){btn.classList.toggle('saved',isSaved(id));btn.textContent=isSaved(id)?'已收藏':'收藏'}});
}
function collectionMarkup(){
  const items=account.watchlist.map(function(id){return state.catalog.find(function(x){return x.id===id})}).filter(Boolean);
  if(!items.length)return '<div class="collection-empty">还没有收藏。推荐卡片上的“收藏”会把作品放进这里。</div>';
  return items.map(function(x){
    const platforms=arr(x.pl).map(function(p){return labels[p]||p}).join(' / ');
    const meta=[x.y,labels[x.ct]||x.ct,platforms].filter(Boolean).join(' · ');
    return '<article class="collection-item"><img src="'+esc(posterFor(x))+'" alt="'+esc(x.t)+' 海报" onerror="this.classList.add(\'poster-broken\');this.alt=\'海报加载失败\'"><div><h4>'+esc(x.t)+'</h4><p>'+esc(meta)+'</p><div class="collection-actions"><button data-detail="'+esc(x.id)+'">查看</button><button data-save="'+esc(x.id)+'">移除</button></div></div></article>';
  }).join('');
}
function renderCollection(){
  const markup=collectionMarkup();
  const dialog=$('#collection-body');if(dialog)dialog.innerHTML=markup;
  const page=$('#library-page-body');if(page)page.innerHTML=markup;
}
function communityMarkup(){
  return COMMUNITY_SCENES.map(function(s){
    return '<article class="community-card"><span class="community-meta">Scene Card · 社区方案</span><h3>'+esc(s.title)+'</h3><p>'+esc(s.desc)+'</p><div class="scene-tags">'+s.tags.map(function(t){return '<span>'+esc(t)+'</span>'}).join('')+'</div><button class="save-button" data-prompt="'+esc(s.prompt)+'">用这个场景找片</button></article>';
  }).join('');
}
function renderCommunity(){
  const markup=communityMarkup();
  const dialog=$('#community-body');if(dialog)dialog.innerHTML=markup;
  const page=$('#community-page-body');if(page)page.innerHTML=markup;
}
const DISCOVER_SCENES=[
  {k:'AFTER WORK',title:'下班后不想费脑',desc:'低认知负荷、节奏顺滑、可被打断。',prompt:'今晚下班后一个人看，轻松一点，别太费脑'},
  {k:'WITH FRIENDS',title:'朋友聚会先把气氛带起来',desc:'笑点、节奏与群体观看体验优先。',prompt:'和朋友聚会，想看节奏快又好笑的电影'},
  {k:'PLATFORM',title:'只在一个平台里选',desc:'平台是 Hard Gate，未知可用性不会混进结果。',prompt:'我只看爱奇艺，想找2026年的国产剧'},
  {k:'EXPLORE',title:'离开热门榜',desc:'在合法候选内增加小众和新鲜度，不突破边界。',prompt:'最近想探索小众一点的华语电影，给我点惊喜'},
  {k:'REFERENCE',title:'从一部喜欢的作品出发',desc:'参考片只负责“像什么”，你的新条件仍然优先。',prompt:'像《功夫》一样有喜剧节奏，但换个题材'},
  {k:'DECISION',title:'不想比较，直接替我选',desc:'保留全部约束，只输出排序最高的一个。',prompt:'别给我列表，今晚直接替我选一部轻松一点的电影'}
];
function renderDiscover(){
  const body=$('#discover-grid');if(!body)return;
  body.innerHTML=DISCOVER_SCENES.map(s=>'<article class="feature-card"><span class="feature-kicker">'+esc(s.k)+'</span><h3>'+esc(s.title)+'</h3><p>'+esc(s.desc)+'</p><button data-prompt="'+esc(s.prompt)+'">进入 Agent</button></article>').join('');
}
function switchView(name){
  const agent=name==='agent';
  $('#welcome')?.classList.toggle('hidden',!agent || !$('#conversation').classList.contains('hidden'));
  $('#conversation')?.classList.toggle('hidden',!agent || $('#messages').children.length===0);
  $('#agent-composer')?.classList.toggle('hidden',!agent);
  $('#agent-system-note')?.classList.toggle('hidden',!agent);
  ['discover','community','library'].forEach(v=>$('#view-'+v)?.classList.toggle('hidden',name!==v));
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));
  if(name==='discover')renderDiscover();
  if(name==='community')renderCommunity();
  if(name==='library')renderCollection();
  if(location.hash!=='#'+name)history.replaceState(null,'','#'+name);
  window.scrollTo({top:0,behavior:'smooth'});
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
function isRealPoster(url){return /^https?:\/\//i.test(String(url||''))}
function posterFor(x){return isRealPoster(x.p)?x.p:'';}
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
  if(/电影/.test(q)) p.contentTypes=['movie']; else if(/电视剧|剧集|国产剧|国剧|追一部.*剧|想看.*剧|恋爱剧|爱情剧|甜宠剧|小甜剧/.test(q)) p.contentTypes=['series'];
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
  $('#messages').insertAdjacentHTML('beforeend',`<div class="turn-agent"><div class="agent-avatar">影</div><div><p class="agent-intro">${esc(item.question)}</p><div class="clarify-options">${item.options.map(x=>`<button type="button" data-prompt="${esc(x)}">${esc(x)}</button>`).join('')}</div></div></div>`);
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
function profileChipData(){
  const p=state.profile, chips=[];
  const add=(key,value,label)=>{if(value!==null&&value!==undefined&&value!=='')chips.push({key,value,label})};
  add('companions',p.companions,labels[p.companions]||p.companions);
  add('scene',p.scene,labels[p.scene]||p.scene);
  p.moods.forEach(v=>add('moods',v,labels[v]||v));
  add('cognitive',p.cognitive,labels[p.cognitive]||p.cognitive);
  p.contentTypes.forEach(v=>add('contentTypes',v,labels[v]||v));
  p.requiredGenres.forEach(v=>add('requiredGenres',v,labels[v]||v));
  p.relationship.forEach(v=>add('relationship',v,labels[v]||v));
  p.pace.forEach(v=>add('pace',v,labels[v]||v));
  if(p.language)add('language',p.language,'中文/国产');
  if(p.sourceReference)add('sourceReference',p.sourceReference,`类似《${p.sourceReference}》`);
  if(p.popularity)add('popularity',p.popularity,labels[p.popularity]||p.popularity);
  if(p.runtimeMax)add('runtimeMax',String(p.runtimeMax),`≤ ${p.runtimeMax} 分钟`);
  if(p.yearMin)add('yearMin',String(p.yearMin),`${p.yearMin}+`);
  if(p.platform)add('platform',p.platform,`只看 ${labels[p.platform]||p.platform}`);
  if(p.pickOne)add('pickOne','1','帮我拍板');
  p.requiredFacts.forEach(v=>add('requiredFacts',v,labels[v]||v));
  if(p.explore)add('explore','1','探索模式');
  p.avoidGenres.forEach(v=>add('avoidGenres',v,`不要 ${labels[v]||v}`));
  p.avoidRisks.forEach(v=>add('avoidRisks',v,v==='emotionally_heavy'?'不要太虐':v==='fear_or_horror'?'不要惊吓':`避开 ${labels[v]||v}`));
  const seen=new Set();return chips.filter(x=>{const k=x.key+'|'+x.value;if(seen.has(k))return false;seen.add(k);return true});
}
async function removeProfileFilter(key,value){
  const p=state.profile;
  const arrays=new Set(['moods','contentTypes','requiredGenres','relationship','pace','requiredFacts','avoidGenres','avoidRisks']);
  if(arrays.has(key))p[key]=p[key].filter(x=>String(x)!==String(value));
  else if(key==='runtimeMax'||key==='yearMin')p[key]=null;
  else if(key==='pickOne'||key==='explore')p[key]=false;
  else if(Object.prototype.hasOwnProperty.call(p,key))p[key]=null;
  profileChips();toast('已移除条件');
  if(state.backendReady&&state.backendSession){
    try{
      const r=await fetch(apiUrl('/v1/sessions/'+encodeURIComponent(state.backendSession)+'/profile/remove'),{
        method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,value})
      });
      if(r.ok){const data=await r.json();syncProfileFromBackend(data.profile,null)}
    }catch(e){console.warn('profile remove sync failed',e)}
  }
}
function profileChips(){
  const p=state.profile,tokens=[];
  const push=(kind,value,label)=>{if(value!==null&&value!==undefined&&value!=='')tokens.push({kind,value,label})};
  push('companions',p.companions,labels[p.companions]||p.companions);
  push('scene',p.scene,labels[p.scene]||p.scene);
  p.moods.forEach(x=>push('moods',x,labels[x]||x));
  push('cognitive',p.cognitive,labels[p.cognitive]||p.cognitive);
  p.contentTypes.forEach(x=>push('contentTypes',x,labels[x]||x));
  p.requiredGenres.forEach(x=>push('requiredGenres',x,labels[x]||x));
  p.relationship.forEach(x=>push('relationship',x,labels[x]||x));
  p.pace.forEach(x=>push('pace',x,labels[x]||x));
  if(p.language)push('language',p.language,'中文/国产');
  if(p.sourceReference)push('sourceReference',p.sourceReference,`类似《${p.sourceReference}》`);
  if(p.popularity)push('popularity',p.popularity,labels[p.popularity]||p.popularity);
  if(p.runtimeMax)push('runtimeMax',String(p.runtimeMax),`≤ ${p.runtimeMax} 分钟`);
  if(p.yearMin)push('yearMin',String(p.yearMin),`${p.yearMin}+`);
  if(p.platform)push('platform',p.platform,`只看 ${labels[p.platform]||p.platform}`);
  if(p.pickOne)push('pickOne','1','帮我拍板');
  p.requiredFacts.forEach(x=>push('requiredFacts',x,labels[x]||x));
  if(p.explore)push('explore','1','探索模式');
  p.avoidGenres.forEach(x=>push('avoidGenres',x,`不要 ${labels[x]||x}`));
  p.avoidRisks.forEach(x=>push('avoidRisks',x,`避开 ${labels[x]||x}`));
  const n=$('#active-profile');
  n.innerHTML=tokens.map(t=>`<button class="profile-chip" type="button" data-remove-filter="${esc(t.kind)}" data-filter-value="${esc(t.value)}"><span>${esc(t.label)}</span><i aria-hidden="true">×</i></button>`).join('');
  n.classList.toggle('hidden',!tokens.length);
}
function startConversation(){$('#welcome').classList.add('hidden');$('#conversation').classList.remove('hidden')}
function addUser(t){startConversation();$('#messages').insertAdjacentHTML('beforeend',`<div class="turn-user"><p>${esc(t)}</p></div>`)}
function card(x,i){
  const rt=x.rt||x.ert;
  const platformText=arr(x.pl).map(p=>labels[p]||p).join(' / ');
  const meta=[x.y,rt?`${rt} 分钟`:null,labels[x.ct]||x.ct,x.pb==='low'?'偏冷门':x.pb==='high'?'较热门':null].filter(Boolean).join(' · ');
  const tags=[...arr(x.g).slice(0,2),...arr(x.to).slice(0,2),...arr(x.cf).slice(0,2)].map(v=>`<span>${esc(labels[v]||v)}</span>`).join('');
  const rn=arr(x.rn).slice(0,2).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);
  const sn=arr(x.sn).slice(0,2).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);
  const poster=posterFor(x);
  const proof=state.profile.requiredFacts.length?`<p class="rec-proof"><b>剧情边界</b>${state.profile.requiredFacts.map(f=>esc(labels[f]||f)).join(' · ')} <span>✓</span></p>`:'';
  return `<article class="rec-card"><img class="rec-poster" src="${esc(poster)}" alt="${esc(x.t)} 海报" loading="lazy" onerror="this.classList.add('poster-broken');this.alt='海报加载失败'"><div class="rec-copy"><div class="rec-top"><div><h3 class="rec-title">${i+1}. ${esc(x.t)}</h3><p class="rec-meta">${esc(meta)}${platformText?`<span class="platform-pill">${esc(platformText)}</span>`:''}</p></div><span class="rec-score">${Math.round(Math.min(99,72+score(x)*3))} 匹配</span></div><p class="rec-why">${esc(x.backendWhy||reason(x))}</p>${proof}${rn.length?`<p class="rec-insight"><b>可能雷点</b>${esc(rn.join(' · '))}</p>`:''}${sn.length?`<p class="rec-insight"><b>无剧透看点</b>${esc(sn.join(' · '))}</p>`:''}<div class="rec-tags">${tags}</div><p class="rec-source">召回：Hard Gate + 稀疏召回 + Scene Vector + Semantic / RRF</p><button class="rec-more" type="button" data-detail="${esc(x.id)}">查看内容依据</button><button class="save-button ${isSaved(x.id)?'saved':''}" type="button" data-save="${esc(x.id)}">${isSaved(x.id)?'已收藏':'收藏'}</button></div></article>`;
}
function socialDiscovery(items){
  if(!items.length)return '';
  const shown=new Set(items.map(x=>x.id));
  const extras=state.catalog.filter(x=>hardOk(x)&&!shown.has(x.id)).sort((a,b)=>score(b)-score(a)).slice(0,2);
  const platform=state.profile.platform?labels[state.profile.platform]:null;
  const sources='小红书公开索引 / 公众号公开文章 / 百度 AI Search / X Recent Search';
  const cards=extras.length?extras.map(x=>{
    const platformText=arr(x.pl).map(p=>labels[p]||p).join(' / ');
    return `<div class="social-source"><b>猜你还会想看 · ${esc(x.t)}</b><p>${esc(reason(x))}${platformText?' · '+esc(platformText):''}</p><p>联网层会检索：${esc(sources)}，并做实体匹配、来源可信度、去重、时效和跨平台一致性校验。</p><button class="rec-more" type="button" data-social="${esc(x.id)}">联网看口碑</button><div class="social-live-result" data-social-result="${esc(x.id)}"></div></div>`;
  }).join(''):'<div class="social-source"><b>联网观点层</b><p>当前硬条件已经非常窄，没有额外合法候选可做“猜你想看”。</p></div>';
  const platformNote=platform?` 当前仍严格限定在 ${esc(platform)} 已验证可用候选内。`:'';
  return `<section class="social-discovery"><div class="social-discovery-head"><div><h4>猜你还想看</h4><p class="social-sub">不是再做一轮普通相似推荐，而是把候选放进公开社媒与全网观点层做二次验证。社媒只影响合法候选内部排序，不会突破平台和剧情边界。${platformNote}</p></div><span class="social-badge">Social Evidence</span></div><div class="social-source-grid">${cards}</div></section>`;
}
async function loadSocialContext(id,button){
  const box=document.querySelector('[data-social-result="'+CSS.escape(id)+'"]');
  if(location.hostname.endsWith('github.io')){
    if(box)box.innerHTML='<p>Pages Demo 不暴露搜索 API 密钥；完整 FastAPI 已实现 /social-context 实时接口。这里不会伪造小红书、公众号或 X 的实时帖子。</p>';
    return;
  }
  if(button){button.disabled=true;button.textContent='联网检索中…'}
  try{
    const r=await fetch('/v1/content/'+encodeURIComponent(id)+'/social-context?refresh=true');
    if(!r.ok)throw new Error('HTTP '+r.status);
    const data=await r.json(),agg=data.aggregate||{},ev=arr(data.evidence).slice(0,4);
    const rows=ev.map(v=>`<p><b>${esc(v.platform||'web')}</b> · ${esc(v.source_title||'公开内容')} · 可信度 ${Math.round((v.authenticity_score||0)*100)}%</p>`).join('');
    if(box)box.innerHTML=`<p>社媒综合信号 ${Math.round((agg.score||0)*100)} / 100 · 置信度 ${Math.round((agg.confidence||0)*100)}%</p>${rows||'<p>当前未获得足够可靠的公开讨论。</p>'}`;
  }catch(e){if(box)box.innerHTML='<p>联网观点暂不可用；推荐本身仍按内容硬边界返回。</p>'}
  finally{if(button){button.disabled=false;button.textContent='刷新联网口碑'}}
}
function render(items,introOverride=null){
  const intro=introOverride||(items.length?'我先锁住平台、剧情事实和风险边界，再做多路召回。社媒热度只影响合法候选内部的排序，不会把别的平台或踩雷内容推回来。':'这组条件没有足够确定的候选，我不会把“未知”冒充“满足”。下面给出最接近但没过线的原因。');
  let body='';
  if(items.length){
    body=`<div class="recommend-list">${items.map(card).join('')}</div>${socialDiscovery(items)}`;
  }else{
    const misses=nearMisses();
    body=`<div class="no-match"><p>没有找到同时满足全部硬条件的候选。</p>${misses.length?`<div class="near-miss"><b>最接近但被拦截</b>${misses.map(({x,fail})=>`<p>《${esc(x.t)}》：缺少/冲突 ${esc(fail.join('、'))}</p>`).join('')}</div>`:''}<p class="rec-source">“未知”不会自动当成“有”：平台可用性、死亡/出轨等剧情事实都需要正向证据。</p></div>`;
  }
  $('#messages').insertAdjacentHTML('beforeend',`<div class="turn-agent"><div class="agent-avatar">影</div><div><p class="agent-intro">${intro}</p>${body}</div></div>`);
  profileChips();
  const qa=['换一批','只替我选一个','更轻松一点','更小众一点','更新一点','给我点惊喜'];
  $('#quick-actions').innerHTML=qa.map(x=>`<button type="button" data-prompt="${x}">${x}</button>`).join('');
  $('#quick-actions').classList.remove('hidden');scrollEnd();
}
function scrollEnd(){requestAnimationFrame(()=>window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'}))}
async function sendMessage(text){
  text=(text||'').trim();if(!text||state.busy)return;
  state.busy=true;$('#send').disabled=true;addUser(text);$('#message-input').value='';
  try{
    if(state.backendReady){
      const data=await backendChat(text);renderBackendResponse(data);
    }else if(CONFIG.requireBackend){
      $('#messages').insertAdjacentHTML('beforeend','<div class="turn-agent"><div class="agent-avatar">影</div><div><p class="agent-intro">AI Agent 后端当前未连接，所以我不会把本地检索伪装成模型回答。请检查服务端 /health 与 OPENAI_API_KEY。</p></div></div>');
      scrollEnd();
    }else{
      parse(text);const clarify=nextClarification();
      if(clarify)renderClarify(clarify);else render(recommend());
    }
  }catch(e){
    console.error(e);
    state.backendReady=false;
    if(CONFIG.requireBackend){
      $('#messages').insertAdjacentHTML('beforeend','<div class="turn-agent"><div class="agent-avatar">影</div><div><p class="agent-intro">这次没有返回模型结果：AI 后端调用失败。为避免把检索结果冒充 Agent 回答，本次不自动降级。</p></div></div>');
      toast('AI Agent 后端调用失败');scrollEnd();
    }else{
      toast('Pages 预览：AI 后端不可用，使用本地检索逻辑');
      parse(text);const clarify=nextClarification();
      if(clarify)renderClarify(clarify);else render(recommend());
    }
  }finally{state.busy=false;$('#send').disabled=false}
}
async function openDetail(id){
  let x=state.catalog.find(v=>v.id===id);
  if(state.backendReady){
    try{
      const r=await fetch(apiUrl('/v1/content/'+encodeURIComponent(id)));
      if(r.ok)x=mergeCatalogItem(backendCatalogItem(await r.json()));
    }catch(e){console.warn('detail hydrate failed',e)}
  }
  if(!x)return;
  const risks=arr(x.rn).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);
  const surprises=arr(x.sn).map(v=>typeof v==='string'?v:(v.text||v.note||v.label||v.tag)).filter(Boolean);
  const facts=[...factSet(x)].map(v=>labels[v]||v);
  const platforms=arr(x.pl).map(v=>labels[v]||v);
  $('#detail-body').innerHTML=`<div class="detail"><img src="${esc(posterFor(x))}" onerror="this.classList.add('poster-broken');this.alt='海报加载失败'" alt="${esc(x.t)} 海报"><div><small>${esc([x.y,labels[x.ct],(x.rt||x.ert)?(x.rt||x.ert)+' 分钟':null].filter(Boolean).join(' · '))}</small><h2>${esc(x.t)}</h2><p>${esc(x.d||'暂无简介')}</p><p><strong>平台快照：</strong>${platforms.length?esc(platforms.join(' / ')):'未验证；指定平台时不会把未知当作可用'}</p><p><strong>类型：</strong>${arr(x.g).map(esc).join(' / ')||'未标注'}</p><p><strong>氛围：</strong>${arr(x.to).map(v=>esc(labels[v]||v)).join(' / ')||'暂无'}</p>${facts.length?`<p><strong>结构化剧情事实：</strong>${esc(facts.join(' / '))}</p>`:'<p><strong>结构化剧情事实：</strong>当前证据不足，不把“未知”当成“没有”。</p>'}${risks.length?`<p><strong>可能雷点：</strong>${esc(risks.slice(0,5).join(' / '))}</p>`:'<p><strong>可能雷点：</strong>证据不足，不等于确定没有雷点。</p>'}${surprises.length?`<p><strong>无剧透看点：</strong>${esc(surprises.slice(0,5).join(' / '))}</p>`:''}<button class="save-button ${isSaved(x.id)?'saved':''}" type="button" data-save="${esc(x.id)}">${isSaved(x.id)?'已收藏':'收藏到我的片单'}</button><p><small>内容理解置信度：${Math.round((x.uc||0)*100)}% · 数据层：${esc(x.src||'canonical catalog')}</small></p></div></div>`;
  $('#detail-dialog').showModal();
}
function reset(){state.profile=freshProfile();state.seen.clear();state.lastQuery='';state.backendSession=null;$('#messages').innerHTML='';$('#conversation').classList.add('hidden');$('#welcome').classList.remove('hidden');$('#active-profile').classList.add('hidden');$('#quick-actions').classList.add('hidden');window.scrollTo({top:0,behavior:'smooth'})}
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

,{id:"cn26:jingzhe",t:"惊蛰无声",ct:"movie",y:2026,co:["中国大陆"],g:["Thriller","Crime","Action"],d:"国安小组围绕重要情报外泄展开调查，在无声较量中追查风险源。",rt:115,p:"https://media.bjnews.com.cn/image/2026/01/22/5678358836604382139.jpg",sc:["solo","friends"],em:["tense","exciting"],cl:"high",pa:["fast"],ri:["violence_possible"],re:["team"],to:["realistic","dark"],cf:["closed_ending"],rn:["涉及谍战、追查与潜在暴力情境"],sn:["现实题材的高压调查感"],pb:"high",uc:.72,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:biaoren",t:"镖人：风起大漠",ct:"movie",y:2026,co:["中国大陆"],g:["Action","Adventure","Drama"],d:"大漠镖客受托护送神秘人物前往长安，途中遭遇围剿与宿命牵连。",rt:125,p:"https://k.sinaimg.cn/n/sinakd20260226s/320/w800h1120/20260226/228c-27c3ae5d1587e27d133e8ecf0498ef24.jpg/w700d1q75cms.jpg",sc:["friends","weekend"],em:["exciting","tense"],cl:"medium",pa:["fast"],ri:["violence_possible"],to:["dark"],cf:[],rn:["武侠动作与围剿场面较多"],sn:["大漠武侠、公路护送与群像关系"],pb:"high",uc:.72,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:feichi3",t:"飞驰人生3",ct:"movie",y:2026,co:["中国大陆"],g:["Comedy","Drama","Sport"],d:"最后一届巴音布鲁克拉力赛落幕后，赛车手回到现实并面对新的生活与竞技挑战。",rt:120,p:"https://wx4.sinaimg.cn/middle/007cUgzRly1i9kks3gzxej31jk2cle82.jpg",sc:["friends","family","weekend"],em:["funny","light","exciting"],cl:"low",pa:["fast","lively"],ri:[],to:["playful","warm"],cf:["no_gore","no_jump_scares"],rn:["赛车运动存在紧张和事故风险"],sn:["赛车喜剧与现实生活的反差"],pb:"high",uc:.7,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:xinghe",t:"星河入梦",ct:"movie",y:2026,co:["中国大陆"],g:["Science-Fiction","Adventure","Comedy"],d:"近未来虚拟梦境系统“良梦”中，管理员与舰长穿梦闯关，展开脑洞型冒险。",rt:118,p:"https://imgcache.dealmoon.com/thumbimg.dealmoon.com/us2603/dealmoon/4cf/abc/6f0/2c206a410fdbbe0235a9f1cx1440x2300x1414.jpeg_1080_0_3_462d.jpeg",sc:["friends","weekend"],em:["exciting","funny","thought_provoking"],cl:"medium",pa:["fast"],ri:[],to:["playful","stylized"],cf:["no_gore"],rn:["包含虚拟梦境危机场景"],sn:["梦境世界与现实规则之间的设定玩法"],pb:"high",uc:.72,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:panda",t:"熊猫计划之部落奇遇记",ct:"movie",y:2026,co:["中国大陆"],g:["Comedy","Adventure","Family"],d:"熊猫胡胡与国际巨星意外进入神奇部落，在冒险中帮助部落解决难题。",rt:100,p:"https://p9.qhimg.com/t11508c75c81ba0e41daa77c045.jpg",sc:["family","friends"],em:["funny","light","relaxing"],cl:"low",pa:["lively"],ri:[],to:["playful","warm"],cf:["family_safe","no_gore","no_jump_scares","no_sexual_content","no_infidelity"],rn:["家庭向冒险中的轻度危机"],sn:["真人与熊猫的错位组合"],pb:"high",uc:.68,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:boonie",t:"熊出没·年年有熊",ct:"movie",y:2026,co:["中国大陆"],g:["Animation","Comedy","Family","Adventure"],d:"不速之客引发危机后，熊大、熊二和光头强再次合作化解问题。",rt:99,p:"https://www.yuleonstar.com/media/uploads/2026/02/02/lowddu.jpg",sc:["family"],em:["funny","light","relaxing"],cl:"low",pa:["lively"],ri:[],to:["playful","warm"],cf:["family_safe","no_gore","no_sexual_content","no_infidelity"],rn:["动画冒险中有轻度危机"],sn:["熟人角色组合与合家欢冒险"],pb:"high",uc:.7,src:"国家电影局 2026 春节档片单"}
,{id:"cn26:qunxing",t:"群星闪耀时",ct:"movie",y:2026,co:["中国大陆"],g:["Science-Fiction","Adventure","Drama"],d:"航天员在太空遭遇险情，并收到来自过去的神秘电子信号，需要破译信号援救未来。",rt:125,p:"https://x0.ifengimg.com/ucms/2026_16/2880742387955756C1F6AF7F1B2691B3D244D23A_size315_w1080_h1080.jpg",sc:["friends","solo"],em:["tense","exciting","thought_provoking"],cl:"high",pa:["fast"],ri:["violence_possible"],to:["realistic"],cf:[],rn:["太空险情与生存压力"],sn:["跨时间信号与航天救援"],pb:"medium",uc:.7,src:"国家电影局 2026 暑期档片单"}
,{id:"cn26:jiaye",t:"家业",ct:"series",y:2026,co:["中国大陆"],g:["Drama","History","Romance"],d:"明朝徽州贡墨案后，李祯以制墨天赋重振家业，并与骆文谦从竞争走向合作。",ert:45,p:"https://s.yimg.com/ny/api/res/1.2/fX2hmMSrGOINdRfCcdYYGA--/YXBwaWQ9aGlnaGxhbmRlcjt3PTk2MDtoPTEyMDA-/https%3A/media.zenfs.com/zh-tw/ebc_star_440/2a033ee36abf8a3241b4d497b8f780ae",ra:8.8,sc:["solo","family"],em:["romantic","thought_provoking"],cl:"medium",pa:["moderate"],ri:["emotionally_heavy"],re:["romantic","family"],to:["realistic","warm"],cf:["happy_ending","closed_ending","career_central","romance_central"],rn:["家族兴衰、竞争和阶段性死亡/离别议题"],sn:["非遗制墨、女性事业成长与合作型关系"],pb:"high",uc:.88,src:"爱奇艺 2026 正片页",pl:["iqiyi"]}

,{id:"cn26:yiouchun",t:"一瓯春",ct:"series",y:2026,co:["中国大陆"],g:["Drama","Romance","History"],d:"谢清圆与沈润在高门与朝堂暗流中互相试探、携手复仇，并最终走向新生。",ert:45,p:"https://pbs.twimg.com/media/HDmzGWzbAAA5WVS.jpg",sc:["solo"],em:["romantic","tense"],cl:"medium",pa:["moderate"],ri:["violence_possible","emotionally_heavy"],re:["romantic"],to:["realistic","dark","bittersweet"],cf:["happy_ending","closed_ending","romance_central"],rn:["复仇、权谋与暴力情节；不是纯甜恋爱"],sn:["双强关系与复仇线并进"],pb:"high",uc:.86,src:"爱奇艺 2026 正片页",pl:["iqiyi"]}
,{id:"cn26:shenyuan",t:"深渊无间",ct:"series",y:2026,co:["中国大陆"],g:["Thriller","Mystery","Crime"],d:"推理网文与多年悬案细节高度重合，新警李成在多方嫌疑人之间展开高智对弈。",ert:45,p:"https://www.palmyule.com/uploads/20251203/234b85986b1e644d7b7aa81ed2ad6df5.jpg",sc:["solo"],em:["tense","thought_provoking"],cl:"high",pa:["fast"],ri:["violence_possible","emotionally_heavy"],to:["dark","realistic"],cf:["closed_ending"],rn:["悬案、犯罪与令人扼腕的亲情友情真相"],sn:["网文与真实悬案互相映照的元叙事入口"],pb:"high",uc:.86,src:"爱奇艺 2026 正片页",pl:["iqiyi"]}
,{id:"safe:intern",t:"实习生",ct:"movie",y:2015,co:["United States"],g:["Comedy","Drama"],d:"退休老人进入互联网创业公司成为高龄实习生，在代际相处中重新找到生活节奏。",rt:121,p:"https://s3.beautimode.com/upload/media/8f634ebeafb0a4570eb01acfeff464f7.JPG",sc:["solo","family"],em:["funny","light","relaxing","healing"],cl:"low",pa:["moderate"],ri:[],re:["friendship","workplace"],to:["warm","gentle"],cf:["no_character_death","no_animal_harm","no_gore","no_jump_scares","no_sexual_content","family_safe","closed_ending"],rn:["存在婚姻关系压力，但不是暴力或惊吓型内容"],sn:["代际友谊和职场陪伴感"],pb:"medium",uc:.76,src:"demo curated content-facts"}
,{id:"safe:chef",t:"落魄大厨",ct:"movie",y:2014,co:["United States"],g:["Comedy","Drama"],d:"厨师离开受挫的餐厅工作后开起餐车，与家人和朋友重新建立连接。",rt:114,p:"https://resize-image.vocus.cc/resize?norotation=true&quality=80&sign=RzUB-BBte71zfTB4xwEK2k1ln2eqnU38-wiY3IILXNk&url=https%3A%2F%2Fimages.vocus.cc%2F1001b568-6932-40d8-86a2-0815cb042694.jpg&width=480",sc:["solo","family","friends"],em:["funny","light","relaxing","healing"],cl:"low",pa:["lively"],ri:[],re:["family","friendship"],to:["warm","playful"],cf:["no_character_death","happy_ending","no_gore","no_jump_scares","closed_ending"],rn:["少量成人语言"],sn:["美食、公路与亲子关系的修复"],pb:"medium",uc:.78,src:"demo curated content-facts"}
,{id:"safe:legally",t:"律政俏佳人",ct:"movie",y:2001,co:["United States"],g:["Comedy","Romance"],d:"女主因感情挫折进入法学院，逐步把外界偏见转化成自我证明。",rt:96,p:"https://i.ebayimg.com/images/g/7AAAAOSwzjxjNN6W/s-l1600.jpg",sc:["solo","friends"],em:["funny","light","relaxing"],cl:"low",pa:["lively"],ri:[],re:["romantic","friendship"],to:["playful","warm"],cf:["no_character_death","happy_ending","no_gore","no_jump_scares","closed_ending"],rn:["有情感分手和轻度成人话题"],sn:["从恋爱动机转向自我成长"],pb:"medium",uc:.78,src:"demo curated content-facts"}
,{id:"safe:schoolrock",t:"摇滚校园",ct:"movie",y:2003,co:["United States"],g:["Comedy","Music","Family"],d:"失意乐手冒充代课老师，把一群孩子组织成摇滚乐队。",rt:109,p:"https://moviesmoviesmovies.co.uk/cdn/shop/files/IMG_0007_BM15970.jpg?v=1736249007&width=1946",sc:["family","friends"],em:["funny","light","relaxing"],cl:"low",pa:["lively"],ri:[],re:["friendship"],to:["playful","warm"],cf:["no_character_death","no_gore","no_jump_scares","no_sexual_content","no_infidelity","family_safe","closed_ending"],rn:["有撒谎与学校规则冲突"],sn:["音乐排练、群体协作与舞台释放"],pb:"medium",uc:.78,src:"demo curated content-facts"}
,{id:"safe:paddington2",t:"帕丁顿熊2",ct:"movie",y:2017,co:["United Kingdom"],g:["Comedy","Family","Adventure"],d:"帕丁顿为了买礼物努力打工，却被卷入误会，需要家人与朋友帮忙找出真相。",rt:103,p:"https://p2.cri.cn/M00/51/7C/CqgNOlpApcqABlxiAAAAAAAAAAA053.681x1000.jpg",sc:["family","friends"],em:["funny","light","relaxing","healing"],cl:"low",pa:["lively"],ri:[],re:["family","friendship"],to:["warm","playful"],cf:["no_character_death","happy_ending","no_gore","no_jump_scares","no_sexual_content","no_infidelity","family_safe","closed_ending"],rn:["包含轻度追逐、误会和监狱情节"],sn:["极高善意密度和群像回馈"],pb:"medium",uc:.82,src:"demo curated content-facts"}
,{id:"safe:kiki",t:"魔女宅急便",ct:"movie",y:1989,co:["Japan"],g:["Animation","Family","Fantasy"],d:"年轻魔女离家修行，在海边城市经营送货服务并度过自我怀疑期。",rt:103,p:"https://www.movieposters.com/cdn/shop/products/Kikisdeliveryservice_1024x1024.jpg?v=1762968201",sc:["solo","family"],em:["light","relaxing","healing"],cl:"low",pa:["moderate"],ri:[],re:["friendship"],to:["gentle","warm"],cf:["no_character_death","no_gore","no_jump_scares","family_safe","closed_ending"],rn:["后段有短暂高空救援危机"],sn:["成长焦虑被处理得非常轻盈"],pb:"medium",uc:.82,src:"demo curated content-facts"}
,{id:"safe:yearmeeting",t:"年会不能停！",ct:"movie",y:2023,co:["中国大陆"],g:["Comedy","Drama"],d:"普通工人阴差阳错进入集团总部，在荒诞职场流程中一路被误认为管理人才。",rt:117,p:"https://doc-fd.zol-img.com.cn/t_s640x2000/g7/M00/0D/0D/ChMkLGYYgyaIKdjyAAHP6ssb0KcAAc4cgK1Cn0AAdAC946.jpg",sc:["friends","solo"],em:["funny","light"],cl:"low",pa:["lively"],ri:[],re:["workplace","friendship"],to:["playful","realistic"],cf:["no_character_death","no_gore","no_jump_scares","closed_ending"],rn:["职场裁员、权力压迫和高强度社畜共鸣"],sn:["流程荒诞和组织语言错位"],pb:"high",uc:.76,src:"demo curated content-facts"}
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
    const sourcePlatform=normalizePlatform(s.webChannel?.name||s.network?.name||''); const item={id:'tvmaze-live:'+s.id,t:s.name,ot:s.name,ct:type,y:Number((s.premiered||'').slice(0,4))||null,co:country?[country]:[],g:arr(s.genres),d:stripHtml(s.summary).slice(0,420),ert:s.averageRuntime||s.runtime||null,p:s.image?.original||s.image?.medium||'',ra:s.rating?.average??null,sc:type==='variety'?['friends','party']:['solo'],...inf,pb:(s.weight||0)>85?'high':(s.weight||0)>45?'medium':'low',uc:.62,cf:[],pl:sourcePlatform?[sourcePlatform]:[]}; return item;
  });
  const byId=new Map(FALLBACK_ITEMS.filter(x=>isRealPoster(x.p)).map(x=>[x.id,{...x,pl:arr(x.pl)}])); for(const x of mapped.filter(x=>isRealPoster(x.p)))if(!byId.has(x.id))byId.set(x.id,x);
  const items=[...byId.values()].map(x=>({...x,pl:arr(x.pl)}));
  if(items.length<150)throw new Error('live catalog too small');
  return {version:'live-tvmaze-plus-curated',count:items.length,full_catalog_count:3339,items};
}
async function loadCatalog(){
  if(state.backendReady){try{return await loadBackendCatalog();}catch(e){console.warn('Backend catalog unavailable; falling back to preview catalog.',e)}}
  try{return await loadLiveCatalog();}
  catch(e){console.warn('Live catalog unavailable; using curated fallback.',e);const items=FALLBACK_ITEMS.filter(x=>isRealPoster(x.p)).map(x=>({...x,pl:arr(x.pl)}));return {version:'curated-fallback',count:items.length,full_catalog_count:3339,items};}
}
function renderPromptStream(){
  const lanes=[
    ['#prompt-lane-a',starters.slice(0,8)],
    ['#prompt-lane-b',starters.slice(8,16)],
    ['#prompt-lane-c',starters.slice(16,24)]
  ];
  const lane=xs=>[...xs,...xs].map(x=>`<button class="starter" type="button" data-prompt="${esc(x)}">${esc(x)}</button>`).join('');
  lanes.forEach(([sel,items])=>{const el=$(sel);if(el)el.innerHTML=lane(items)});
}
async function init(){
  loadAccount();renderCommunity();renderDiscover();renderPromptStream();
  const aiReady=await initBackend();
  if(aiReady)await syncAccountFromBackend();
  try{
    const data=await loadCatalog();
    state.catalog=data.items||[];
    renderCollection();
    $('#catalog-status').innerHTML=aiReady?`<i></i>AI Agent · ${state.catalog.length.toLocaleString()} 部预览内容`:`<i></i>Pages 预览 · ${state.catalog.length.toLocaleString()} 部真实海报内容`;
    renderPromptStream();
    const initial=(location.hash||'#agent').slice(1);switchView(['agent','discover','community','library'].includes(initial)?initial:'agent');
  }catch(e){console.error(e);toast('片库加载失败，请刷新页面')}
}
document.addEventListener('click',e=>{
  const nav=e.target.closest('[data-view]');if(nav){switchView(nav.dataset.view);return}
  const rm=e.target.closest('[data-remove-filter]');if(rm){removeProfileFilter(rm.dataset.removeFilter,rm.dataset.filterValue);return}
  const legacyChip=e.target.closest('[data-profile-kind]');if(legacyChip){removeProfileFilter(legacyChip.dataset.profileKind,legacyChip.dataset.profileValue);return}
  const p=e.target.closest('[data-prompt]');
  if(p){
    const community=$('#community-dialog');if(community&&community.open)community.close();
    switchView('agent');sendMessage(p.dataset.prompt);return;
  }
  const d=e.target.closest('[data-detail]');if(d){openDetail(d.dataset.detail);return}
  const s=e.target.closest('[data-save]');if(s){toggleSave(s.dataset.save);return}
  const social=e.target.closest('[data-social]');if(social){loadSocialContext(social.dataset.social,social);return}
});
$('#composer')?.addEventListener('submit',e=>{e.preventDefault();sendMessage($('#message-input').value)});
$('#message-input')?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage(e.target.value)}});
$('#new-chat')?.addEventListener('click',()=>{reset();switchView('agent')});
$('#detail-close')?.addEventListener('click',()=>$('#detail-dialog').close());
$('#account-button')?.addEventListener('click',()=>{
  if(account.user){$('#auth-name').value=account.user.name;$('#auth-email').value=account.user.email}
  syncAccountUI();$('#auth-dialog').showModal();
});
$('#auth-close')?.addEventListener('click',()=>$('#auth-dialog').close());
$('#collection-close')?.addEventListener('click',()=>$('#collection-dialog').close());
$('#community-close')?.addEventListener('click',()=>$('#community-dialog').close());
$('#auth-form')?.addEventListener('submit',async e=>{
  e.preventDefault();
  const name=$('#auth-name').value.trim(),email=$('#auth-email').value.trim().toLowerCase();
  if(!name||!email)return;
  try{
    if(state.backendReady){
      const r=await fetch(apiUrl('/v1/auth/demo'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,display_name:name})});
      if(!r.ok)throw new Error('login_failed');
      const data=await r.json();account.token=data.token;account.user={name:data.user.display_name,email:data.user.email,user_id:data.user.user_id};
      storeSet('auth_token',account.token);storeSet('user',account.user);await syncAccountFromBackend();toast('已登录完整账户模式');
    }else{
      account.user={name,email};storeSet('user',account.user);account.watchlist=storeGet(accountKey(),[]);toast('Pages 预览使用本地账户');
    }
    syncAccountUI();renderCollection();$('#auth-dialog').close();
  }catch(err){toast('登录失败，请检查 AI 后端')}
});
$('#auth-logout')?.addEventListener('click',()=>{
  storeSet('user',null);storeSet('auth_token',null);account.user=null;account.token=null;account.watchlist=[];syncAccountUI();renderCollection();
  $('#auth-name').value='';$('#auth-email').value='';$('#auth-dialog').close();toast('已退出本地 Demo 账户');
});
init();
