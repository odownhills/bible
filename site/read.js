/* Listen + Read mode for chapter pages: plays the chapter's recording while the words on the page
   brighten as the voice reaches them, a soft marker glides from word to word, and the page stays
   still while the voice reads down it, gliding up now and then to keep the words in view.
   Alternate readings and notes (not read aloud) are shown dimmed; "Hide alt" hides them.
   Word start times come from audio/<book>/<n>.json (made by scripts/align.py). */
(function(){
'use strict';
var d=document,ch=null,words=[],T=null,cur=-1,active=false,want=false,busy=false,ready=false,dragging=false;
var follow=true,followT=0,raf=0,lastSave=0,wake=null,blobs={},bar=null,audio=null,serial=0;
var pill=null,pillTop=null,glideRaf=0,gliding=false;
var still=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
var PLAY='<path class="solid" d="M8 5.200v13.600a.6.6 0 0 0 .900.500l11-6.800a.6.6 0 0 0 0-1L8.900 4.700a.6.6 0 0 0-.900.500z"/>';
var PAUSE='<path class="solid" d="M7 5h3.500v14H7zM13.500 5H17v14h-3.500z"/>';
var LEAD=0.06;   // light a word up a moment early so the eye is never behind the voice
function $(id){return d.getElementById(id)}
function get(k,v){try{var x=localStorage.getItem(k);return x==null?v:JSON.parse(x)}catch(e){return v}}
function put(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function fmt(s){if(!isFinite(s)||s<0)s=0;s=Math.floor(s);var m=Math.floor(s/60),x=s%60;return m+':'+(x<10?'0':'')+x}
function abs(rel){return new URL(rel,location.href).href}
function rate(){return parseFloat($('lr-rate').value)||1.25}

function chapter(){
  ch=$('ch'); words=ch?Array.prototype.slice.call(ch.querySelectorAll('.w')):[];
  for(var k=0;k<words.length;k++) words[k]._k=k;
  cur=-1; T=null; pill=null; pillTop=null;
}

function build(){
  if(bar)return;
  bar=d.createElement('div'); bar.className='lr-bar'; bar.id='lr-bar'; bar.hidden=true;
  bar.innerHTML='<div class="lr-in">'+
    '<input class="seek" id="lr-seek" type="range" min="0" max="100" step="0.1" value="0" aria-label="Position in chapter" disabled>'+
    '<div class="times"><span id="lr-cur">0:00</span><button class="alt-t" id="lr-alt" type="button" hidden>Hide alt</button><span id="lr-rem">0:00</span></div>'+
    '<div class="lr-row">'+
      '<select class="chip" id="lr-rate" aria-label="Speed">'+
        '<option value="1">1&times;</option><option value="1.1">1.1&times;</option><option value="1.25">1.25&times;</option>'+
        '<option value="1.4">1.4&times;</option><option value="1.5">1.5&times;</option><option value="1.75">1.75&times;</option><option value="2">2&times;</option>'+
      '</select>'+
      '<div class="lr-mid">'+
        '<button class="tb skip" id="lr-back" type="button" aria-label="Back 10 seconds"><svg viewBox="0 0 24 24"><path d="M4 12a8 8 0 1 0 2.600-5.900"/><path d="M3.500 3.500v3.500H7"/></svg><span>10</span></button>'+
        '<button class="tb main" id="lr-play" type="button" aria-label="Play"><svg viewBox="0 0 24 24" id="lr-ico">'+PLAY+'</svg></button>'+
        '<button class="tb skip" id="lr-fwd" type="button" aria-label="Forward 10 seconds"><svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.600-5.900"/><path d="M20.500 3.500v3.500H17"/></svg><span>10</span></button>'+
      '</div>'+
      '<button class="tb x" id="lr-close" type="button" aria-label="Close Listen + Read"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>'+
    '</div>'+
    '<p class="lr-msg" id="lr-msg" hidden></p></div>';
  d.body.appendChild(bar);
  audio=d.createElement('audio'); audio.preload='auto'; d.body.appendChild(audio);
  $('lr-rate').value=String(get('readRate','1.25')); if(!$('lr-rate').value) $('lr-rate').value='1.25';

  audio.addEventListener('timeupdate',function(){ if(!active)return; paint(); mark(); savePos(false); });
  audio.addEventListener('play',function(){ want=true; icon(); loop(); awake(true); posState(); });
  audio.addEventListener('pause',function(){ if(busy||audio.ended||audio.seeking)return; want=false; icon(); savePos(true); awake(false); });
  audio.addEventListener('ended',ended);
  audio.addEventListener('seeked',function(){ mark(); });
  audio.addEventListener('ratechange',posState);
  audio.addEventListener('error',function(){ if(active&&audio.getAttribute('src')){ want=false; icon(); msg('This recording could not be loaded. Check your connection and press play again.'); } });
  var seek=$('lr-seek');
  seek.addEventListener('input',function(){ dragging=true; paint(); });
  seek.addEventListener('change',function(){ var v=parseFloat(seek.value); dragging=false; if(isFinite(audio.duration)) jump(v); });
  $('lr-play').onclick=function(){ want?pause():play(); };
  $('lr-back').onclick=function(){ jump(audio.currentTime-10); };
  $('lr-fwd').onclick=function(){ jump(audio.currentTime+10); };
  $('lr-close').onclick=close;
  $('lr-alt').onclick=function(){ put('lrAlts',!get('lrAlts',true)); alts(); pillTop=null; marker(); scrollToWord(true); };
  window.addEventListener('resize',function(){ if(active){ pillTop=null; marker(); } });
  $('lr-rate').onchange=function(){ put('readRate',$('lr-rate').value); audio.defaultPlaybackRate=rate(); audio.playbackRate=rate(); paint(); };

  // A finger on the text pauses the auto-scroll; it picks up again a few seconds after the last touch.
  ['touchstart','touchmove','wheel'].forEach(function(ev){
    window.addEventListener(ev,function(e){ if(!active||(e.target.closest&&e.target.closest('.lr-bar')))return;
      follow=false; clearTimeout(followT); followT=setTimeout(function(){ follow=true; scrollToWord(true); },4000); },{passive:true});
  });
  d.addEventListener('visibilitychange',function(){ if(d.hidden) savePos(true); else if(active&&want) awake(true); });
  window.addEventListener('pagehide',function(){ savePos(true); });
}
function hooks(){
  // The lock screen's buttons. Set again each time Listen + Read starts, because TV mode (scripts/tv.js)
  // uses them while it is open and clears them when it closes.
  if(!('mediaSession' in navigator))return;
  var set=function(a,f){try{navigator.mediaSession.setActionHandler(a,f)}catch(e){}};
  set('play',function(){ if(active)play(); }); set('pause',function(){ if(active)pause(); });
  set('seekbackward',function(){ if(active)jump(audio.currentTime-10); }); set('seekforward',function(){ if(active)jump(audio.currentTime+10); });
  set('seekto',function(x){ if(active&&x&&isFinite(x.seekTime)) jump(x.seekTime); });
  set('previoustrack',null);
  set('nexttrack',function(){ if(active&&ch&&ch.dataset.next) go(ch.dataset.next,want); });
}

function alts(){
  // Alternate readings are shown unless the reader chose to hide them; the choice is remembered.
  var show=get('lrAlts',true),b=$('lr-alt');
  d.body.classList.toggle('noalt',!show);
  if(b){ b.textContent=show?'Hide alt':'Show alt'; b.setAttribute('aria-pressed',String(!show)); b.hidden=!(ch&&ch.querySelector('.aside')); }
}
function msg(t){ var m=$('lr-msg'); m.hidden=!t; m.textContent=t||''; }
function icon(){ $('lr-ico').innerHTML=want?PAUSE:PLAY; $('lr-play').setAttribute('aria-label',want?'Pause':'Play'); }
function awake(on){
  if(!('wakeLock' in navigator))return;
  if(on){ if(!wake&&!d.hidden) navigator.wakeLock.request('screen').then(function(w){ wake=w; w.addEventListener('release',function(){ if(wake===w) wake=null; }); if(!want||!active){ w.release(); } }).catch(function(){}); }
  else if(wake){ var w=wake; wake=null; w.release().catch(function(){}); }
}
function posState(){
  if(!('mediaSession' in navigator)||!navigator.mediaSession.setPositionState||!isFinite(audio.duration))return;
  try{navigator.mediaSession.setPositionState({duration:audio.duration,playbackRate:audio.playbackRate,position:Math.min(audio.currentTime,audio.duration)});}catch(e){}
}
function savePos(force){
  if(!active||!ready||!ch)return; var now=Date.now(); if(!force&&now-lastSave<4000)return; lastSave=now;
  var pos=get('listenPos',{}),id=ch.dataset.id;
  if(audio.currentTime>3&&(!audio.duration||audio.currentTime<audio.duration-3)) pos[id]=Math.floor(audio.currentTime); else delete pos[id];
  put('listenPos',pos);
  spot({mode:'lr',t:pos[id]||0});
}
function paint(){
  var seek=$('lr-seek'),dur=audio.duration,t=audio.currentTime||0;
  if(!isFinite(dur))dur=0;
  seek.max=dur||100; if(!dragging) seek.value=t;
  var shown=dragging?parseFloat(seek.value):t;
  seek.style.setProperty('--p',(dur?Math.min(100,shown/dur*100):0)+'%');
  $('lr-cur').textContent=ready?fmt(shown):'Loading…'; $('lr-rem').textContent=dur?'-'+fmt((dur-shown)/rate()):'';
}

/* ---- the words ---- */
function estimate(dur){
  // No measured timings for this chapter: spread the words evenly over the recording by their length.
  var skip=2.4,total=0,k,run=0,out=[];
  for(k=0;k<words.length;k++) total+=words[k].textContent.length+2;
  for(k=0;k<words.length;k++){ out.push(skip+(dur-skip)*run/total); run+=words[k].textContent.length+2; }
  return out;
}
function mark(){
  if(!active||!T||!words.length)return;
  var t=audio.currentTime+LEAD,lo=0,hi=T.length-1,k=-1;
  while(lo<=hi){ var mid=(lo+hi)>>1; if(T[mid]<=t){ k=mid; lo=mid+1; } else hi=mid-1; }
  if(k===cur)return;
  var j;
  if(cur>=0) words[cur].classList.remove('now');
  if(k>cur){ for(j=Math.max(cur,0);j<=k;j++) words[j].classList.add('on'); }
  else { for(j=k+1;j<=cur;j++) words[j].classList.remove('on'); }
  cur=k;
  if(k>=0) words[k].classList.add('now');
  marker();
  if(follow) scrollToWord(false);
}
function marker(){
  // One soft marker slides from word to word (instead of a box popping on and off each word);
  // on a new line it moves there at once, since the eye jumps to the next line anyway.
  if(!ch)return;
  if(!pill||!ch.contains(pill)){ pill=d.createElement('span'); pill.className='lr-pill'; pill.setAttribute('aria-hidden','true'); ch.appendChild(pill); pillTop=null; }
  var w=cur>=0?words[cur]:null,r=w&&(w.getClientRects()[0]);
  if(!r){ pill.style.opacity='0'; pillTop=null; return; }
  var o=ch.getBoundingClientRect(),x=r.left-o.left-4,y=r.top-o.top-2,jump=pillTop===null||Math.abs(y-pillTop)>4;
  if(jump) pill.style.transition='none';
  pill.style.transform='translate('+x.toFixed(1)+'px,'+y.toFixed(1)+'px)';
  pill.style.width=(r.width+8).toFixed(1)+'px'; pill.style.height=(r.height+4).toFixed(1)+'px'; pill.style.opacity='1';
  if(jump){ void pill.offsetWidth; pill.style.transition=''; }
  pillTop=y;
}
function scrollToWord(always){
  // The page holds still while the voice reads down it. Once the word being read passes 60% of
  // the visible area (or is off screen), the page glides up slowly to bring it back near the top.
  if(!active)return;
  var w=words[Math.max(cur,0)]; if(!w)return;
  var r=w.getBoundingClientRect(),room=window.innerHeight-(bar?bar.offsetHeight:0),target=room*0.3;
  if(always){ if(Math.abs(r.top-target)>4) glideBy(r.top-target,450); return; }
  if(gliding)return;
  if(r.top>room*0.6||r.top<room*0.06) glideBy(r.top-target,900);
}
function glideBy(delta,ms){
  cancelAnimationFrame(glideRaf); gliding=false;
  if(still){ window.scrollBy(0,delta); return; }
  var from=window.scrollY,start=null; gliding=true;
  glideRaf=requestAnimationFrame(function step(now){
    if(start===null) start=now;
    var p=Math.min(1,(now-start)/ms),e=p<0.5?4*p*p*p:1-Math.pow(-2*p+2,3)/2;   // ease in and out
    window.scrollTo(0,from+delta*e);
    if(p<1&&active&&follow) glideRaf=requestAnimationFrame(step); else gliding=false;
  });
}
function loop(){ if(raf)return; raf=requestAnimationFrame(function step(){ raf=0; if(!active||audio.paused)return; mark(); raf=requestAnimationFrame(step); }); }
function clearWords(){ for(var k=0;k<words.length;k++) words[k].classList.remove('on','now'); cur=-1; if(pill) pill.style.opacity='0'; pillTop=null; }

/* ---- playback ---- */
function whole(url){
  // The site's host does not answer partial-file requests, so a recording is downloaded whole and
  // played from memory; otherwise the browser cannot jump around inside it.
  if(blobs[url])return blobs[url];
  var keys=Object.keys(blobs); if(keys.length>3){ var old=keys[0]; blobs[old].then(function(u){ if(u.indexOf('blob:')===0&&audio.src!==u) URL.revokeObjectURL(u); }); delete blobs[old]; }
  return blobs[url]=fetch(url).then(function(r){ if(!r.ok)throw 0; return r.blob(); })
    .then(function(b){ return URL.createObjectURL(b); }).catch(function(){ delete blobs[url]; return url; });
}
function begin(auto,note){
  build(); hooks(); chapter();
  if(!ch||!ch.dataset.audio){ if(active) { want=false; icon(); msg('This chapter has no recording yet. It will be added soon.'); } return; }
  var mine=++serial,id=ch.dataset.id,src=abs(ch.dataset.audio),sync=ch.dataset.sync?abs(ch.dataset.sync):null,skip=parseInt(ch.dataset.skip||'0',10);
  active=true; busy=true; ready=false; follow=true; want=!!auto; d.body.classList.add('lr'); bar.hidden=false; msg(''); icon(); alts();
  $('lr-seek').disabled=true; audio.pause(); paint(); put('listenAt',id);
  spot({mode:'lr',t:get('listenPos',{})[id]||0});
  var timing=sync?fetch(sync).then(function(r){ return r.ok?r.json():null; }).catch(function(){ return null; }):Promise.resolve(null);
  Promise.all([whole(src),timing]).then(function(got){
    if(mine!==serial)return;
    var j=got[1];
    audio.defaultPlaybackRate=rate(); audio.src=got[0]; audio.playbackRate=rate();
    audio.addEventListener('loadedmetadata',function once(){ audio.removeEventListener('loadedmetadata',once);
      if(mine!==serial)return;
      T=(j&&j.t&&j.t.length-skip===words.length)?j.t.slice(skip).map(function(x){return x/100}):estimate(audio.duration);
      var resume=get('listenPos',{})[id]||0;
      if(resume&&resume<audio.duration-5) audio.currentTime=resume;
      busy=false; ready=true; $('lr-seek').disabled=false; paint(); mark(); posState(); scrollToWord(true);
      if(note&&!want) msg(resume?'Back where you left off, at '+fmt(resume)+'. Press play to carry on.':'Press play to start.');
      if(ch.dataset.nextAudio) whole(abs(ch.dataset.nextAudio));
    });
    audio.load();
    if(want) audio.play().catch(function(){ want=false; icon(); });
    if('mediaSession' in navigator){ try{navigator.mediaSession.metadata=new MediaMetadata({title:ch.dataset.title,artist:'The Bible, Freshly Translated',album:'Listen + Read'});}catch(e){} }
  });
}
function play(){ want=true; icon(); if(busy)return; msg(''); audio.playbackRate=rate(); audio.play().catch(function(){ want=false; icon(); }); }
function pause(){ want=false; icon(); if(busy)return; audio.pause(); }
function jump(t){
  if(!ready||!isFinite(audio.duration))return;
  audio.currentTime=Math.max(0,Math.min(audio.duration-0.2,t)); follow=true; clearTimeout(followT);
  paint(); mark(); posState(); savePos(true);
}
function close(){
  if(!active)return; savePos(true); serial++; audio.pause(); active=false; want=false; ready=false; awake(false);
  d.body.classList.remove('lr'); bar.hidden=true; clearWords();
}
function ended(){
  if(!active||!ch)return;
  var done=get('listenDone',{}),pos=get('listenPos',{}); done[ch.dataset.id]=1; delete pos[ch.dataset.id]; put('listenDone',done); put('listenPos',pos);
  if(ch.dataset.next&&ch.dataset.nextAudio){ go(ch.dataset.next,true); return; }
  want=false; icon(); awake(false);
  msg(ch.dataset.next?'The next chapter has no recording yet. It will be added soon.':'You are all caught up. More chapters arrive every day.');
}
function go(rel,auto){
  // Move to another chapter without leaving the page, so the voice can carry straight on.
  var url=abs(rel),mine=++serial; busy=true; savePos(true); audio.pause();
  fetch(url).then(function(r){ if(!r.ok)throw 0; return r.text(); }).then(function(html){
    if(mine!==serial)return;
    var doc=new DOMParser().parseFromString(html,'text/html'),fresh=doc.querySelector('.wrap');
    if(!fresh||!doc.getElementById('ch'))throw 0;
    d.querySelector('.wrap').innerHTML=fresh.innerHTML; d.title=doc.title;
    history.pushState({lr:1},'',url); window.scrollTo(0,0);
    begin(auto);
  }).catch(function(){ location.href=url+(auto?'#listen-read':''); });
}

d.addEventListener('click',function(e){
  var t=e.target; if(!t.closest)return;
  if(t.closest('#lr-start')){ e.preventDefault(); if(active){ follow=true; scrollToWord(true); if(!want)play(); } else begin(true); return; }
  if(!active)return;
  var w=t.closest('#ch .w');
  if(w&&T&&ready){ jump(T[w._k]-LEAD+0.01); if(!want)play(); return; }
  var a=t.closest('.pn a');
  if(a){ e.preventDefault(); go(a.getAttribute('href'),want); }
});
window.addEventListener('popstate',function(){ if(active||history.state&&history.state.lr) location.reload(); });
d.addEventListener('keydown',function(e){ if(!active||/SELECT|INPUT|BUTTON|A/.test(e.target.tagName))return;
  if(e.key===' '){ e.preventDefault(); want?pause():play(); } else if(e.key==='ArrowLeft') jump(audio.currentTime-10); else if(e.key==='ArrowRight') jump(audio.currentTime+10); });

/* ---- your place ----
   Everything is kept in this browser's own storage (no account, no server):
   lastSpot  the one place the site reopens to: {mode:'read'|'lr'|'listen', id, url, label, v (verse), t (seconds)}
   readPos   the verse you had reached in each chapter you left partway through */
function spot(o){
  var c=$('ch'); if(!c)return;
  o.id=c.dataset.id; o.url=c.dataset.url; o.label=c.dataset.title; o.at=Date.now(); put('lastSpot',o);
}
var moved=false,placeT=0;
function verseAtTop(c){
  var vs=c.querySelectorAll('sup.n'),line=90,v=1;
  for(var k=0;k<vs.length;k++){ if(vs[k].getBoundingClientRect().top<=line) v=parseInt(vs[k].id.slice(1),10)||v; else break; }
  return v;
}
function savePlace(){
  var c=$('ch'); if(!c||active)return;
  var id=c.dataset.id,pos=get('readPos',{}),pn=d.querySelector('.pn'),v=verseAtTop(c);
  var end=pn&&window.scrollY>200&&pn.getBoundingClientRect().top<window.innerHeight-20;
  delete pos[id];
  if(end){
    // Finished the chapter: next time, start the next one from the top.
    var nx=d.querySelector('.pn a.next');
    if(nx&&c.dataset.next){ var u=c.dataset.next.replace(/^\.\.\//,''); put('lastSpot',{mode:'read',id:u.replace('/','-').replace('.html',''),url:u,label:nx.textContent.replace(/^[^A-Za-z0-9]+/,''),v:1,at:Date.now()}); }
    else spot({mode:'read',v:v});
  }else{
    if(v>1) pos[id]=v;
    spot({mode:'read',v:v});
  }
  var keys=Object.keys(pos); while(keys.length>80) delete pos[keys.shift()];
  put('readPos',pos);
}
function toast(text,actions){
  var t=d.createElement('div'); t.className='toast'; t.setAttribute('role','status');
  var p=d.createElement('p'); p.textContent=text; t.appendChild(p);
  actions.forEach(function(a){
    var el=d.createElement(typeof a[1]==='string'?'a':'button'); el.textContent=a[0];
    if(typeof a[1]==='string') el.href=a[1]; else { el.type='button'; el.onclick=function(){ a[1](); t.remove(); }; }
    t.appendChild(el);
  });
  var x=d.createElement('button'); x.type='button'; x.className='x'; x.setAttribute('aria-label','Close'); x.textContent='\u2715'; x.onclick=function(){ t.remove(); }; t.appendChild(x);
  d.body.appendChild(t); setTimeout(function(){ if(t.parentNode) t.remove(); },12000);
}
function restore(){
  var c=$('ch'); if(!c)return;
  var ls=get('lastSpot',null);
  // Left this chapter in Listen + Read: reopen it that way, paused at the same second.
  if(ls&&ls.mode==='lr'&&ls.id===c.dataset.id&&c.dataset.audio){ begin(false,true); return; }
  var v=get('readPos',{})[c.dataset.id],s=v&&$('v'+v);
  if(!s){ spot({mode:'read',v:1}); return; }
  if('scrollRestoration' in history) history.scrollRestoration='manual';
  var to=function(){ if(!moved) window.scrollTo(0,s.getBoundingClientRect().top+window.scrollY-64); };
  s.classList.add('here'); setTimeout(function(){ s.classList.remove('here'); },6000);
  to(); window.addEventListener('load',to); setTimeout(to,400);
  spot({mode:'read',v:v});
  toast('Back where you left off, at verse '+v+'.',[['Start of chapter',function(){ moved=true; window.scrollTo({top:0,behavior:'smooth'}); }],['All books','../?home']]);
}
['touchstart','wheel','keydown','mousedown'].forEach(function(ev){ window.addEventListener(ev,function(){ moved=true; },{passive:true}); });
window.addEventListener('scroll',function(){ if(active)return; clearTimeout(placeT); placeT=setTimeout(savePlace,350); },{passive:true});
d.addEventListener('visibilitychange',function(){ if(d.hidden&&!active&&moved) savePlace(); });
window.addEventListener('pagehide',function(){ if(!active&&moved) savePlace(); });

var h=location.hash,hasAudio=$('ch')&&$('ch').dataset.audio;
if((h==='#listen-read'||h==='#resume-lr')&&hasAudio){ history.replaceState(null,'',location.pathname+location.search); begin(h==='#listen-read',h==='#resume-lr'); }
else if(!h) restore();
})();
