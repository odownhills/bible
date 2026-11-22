/* Two things at the top of every page of the Quran site (scripts/quran_ar.py, scripts/quran_site.py):

   The English | Arabic switch. It lands on the same verse in the other language: the verse at the top
   of the screen, or the verse being read aloud when Listen + Read is on. From an Arabic surah it goes to
   the English surah's page, and says so when that verse is not translated yet. The choice is remembered
   in this browser (quranLang): opening the site's address from outside with no place to go back to then
   opens the Arabic pages.

   The bar of sections on a long surah's page: it names the section on screen, and its list jumps to any
   other. During Listen + Read a jump also moves the voice there. */
(function(){
'use strict';
var d=document;
function get(k,v){try{var x=localStorage.getItem(k);return x==null?v:JSON.parse(x)}catch(e){return v}}
function put(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function cover(){   // the height of the bars that stay at the top of the screen
  var h=0,t=d.querySelector('.top'),s=d.getElementById('secbar');
  if(t&&getComputedStyle(t).position==='sticky') h+=t.offsetHeight;
  if(s) h+=s.offsetHeight;
  return h;
}
function verseHere(){
  var ch=d.getElementById('ch'); if(!ch)return 0;
  var now=ch.querySelector('.w.now');
  var vs=ch.querySelectorAll('sup.n[id^="v"]'),k,line=Math.max(96,cover()+24);
  if(!vs.length)return 0;
  var v=parseInt(vs[0].id.slice(1),10)||0;   // the page's first verse, until one has scrolled past the top
  if(now){   // Listen + Read: the verse of the word being read
    for(k=0;k<vs.length;k++){ if(vs[k].compareDocumentPosition(now)&4) v=parseInt(vs[k].id.slice(1),10)||v; else break; }
    return v;
  }
  // the last verse that starts above the line just under the bars; a section heading there counts as its first verse
  var els=ch.querySelectorAll('sup.n[id^="v"],h2.sec');
  for(k=0;k<els.length;k++){
    if(els[k].getBoundingClientRect().top>line) break;
    var e=els[k].tagName==='SUP'?els[k]:els[k+1];
    if(e&&e.tagName==='SUP') v=parseInt(e.id.slice(1),10)||v;
  }
  return v;
}
function note(text){
  var old=d.querySelector('.toast.lang-t'); if(old) old.remove();
  var t=d.createElement('div'); t.className='toast lang-t'; t.setAttribute('role','status');
  var p=d.createElement('p'); p.textContent=text; t.appendChild(p);
  var x=d.createElement('button'); x.type='button'; x.className='x'; x.setAttribute('aria-label','Close'); x.textContent='✕';
  x.onclick=function(){ t.remove(); }; t.appendChild(x);
  d.body.appendChild(t); setTimeout(function(){ if(t.parentNode) t.remove(); },9000);
}
d.addEventListener('click',function(e){
  var a=e.target.closest&&e.target.closest('a[data-lang]'); if(!a||e.button||e.metaKey||e.ctrlKey||e.shiftKey)return;
  var lang=a.getAttribute('data-lang'),v=verseHere(),href=a.getAttribute('href');
  put('quranLang',lang);
  if(!v){ return; }   // not a page of verses: the link goes where it says
  e.preventDefault();
  if(lang==='ar'){ location.href=href+(v>1?'#v'+v:''); return; }
  // Arabic to English: the surah's page, when the translation has reached this verse
  var upto=parseInt(a.getAttribute('data-upto')||'0',10),n=a.getAttribute('data-surah');
  if(v<=upto){ location.href=href+(v>1?'#v'+v:''); return; }
  put('quranLang','ar');
  if(!upto) note('Surah '+n+' is not translated into English yet.');
  else note('Verse '+v+' of surah '+n+' is not translated into English yet. The translation reaches verse '+upto+' so far.');
});
// The English home page, opened from outside with nowhere to go back to: open the Arabic pages if they were chosen last.
if(d.getElementById('resume')&&!/\/ar\//.test(location.pathname)&&get('quranLang','en')==='ar'&&!get('lastSpot',null)
   &&!/[?&]home/.test(location.search)&&!(d.referrer&&d.referrer.indexOf(location.origin)===0)) location.replace('ar/');

/* ---- the sections ---- */
// Looked up afresh whenever the page's text changes (Listen + Read can move on to the next surah in place).
var bar=null,btn,list,label,links=[],here=-1,raf=0;
function find(){
  var b=d.getElementById('secbar'); if(b===bar)return !!bar;
  bar=b; here=-1; if(!bar)return false;
  btn=d.getElementById('sec-now'); list=d.getElementById('sec-list'); label=d.getElementById('sec-name');
  links=Array.prototype.slice.call(list.querySelectorAll('a[data-at]'));
  return true;
}
function navh(){   // the section bar sits right under the top bar (a pixel under it, so no text shows between them)
  var t=d.querySelector('.top'); if(t) d.documentElement.style.setProperty('--navh',(t.getBoundingClientRect().height-1).toFixed(1)+'px');
}
function target(a){ return d.getElementById(a.getAttribute('data-at')); }
function current(){
  // the last section whose start has reached the line just under the bars, the first one until then;
  // during Listen + Read, the section of the word being read
  if(!find())return;
  var line=cover()+Math.min(window.innerHeight*0.25,140),k=0,i,el,now=d.body.classList.contains('lr')&&d.querySelector('#ch .w.now');
  for(i=0;i<links.length;i++){
    el=target(links[i]); if(!el)continue;
    if(now?(el.compareDocumentPosition(now)&4):el.getBoundingClientRect().top<=line) k=i; else break;
  }
  if(k!==here){
    if(here>=0){ links[here].classList.remove('on'); links[here].removeAttribute('aria-current'); }
    here=k; links[k].classList.add('on'); links[k].setAttribute('aria-current','true');
    label.textContent=links[k].querySelector('b').textContent;
  }
}
function open(on){
  if(!find())return;
  list.hidden=!on; btn.setAttribute('aria-expanded',String(on));
  if(on&&here>=0){ var a=links[here]; list.scrollTop=Math.max(0,a.offsetTop-list.clientHeight/2+a.offsetHeight/2); }
}
d.addEventListener('click',function(e){
  if(!find()||!e.target.closest)return;
  if(e.target.closest('#sec-now')){ open(list.hidden); return; }
  var a=e.target.closest('#sec-list a[data-at]');
  if(!a){ if(!list.hidden&&!bar.contains(e.target)) open(false); return; }
  e.preventDefault(); open(false);
  var el=target(a); if(!el)return;
  // During Listen + Read the voice goes there too (scripts/read.js moves the voice to a word that is tapped)
  if(d.body.classList.contains('lr')){
    var ws=d.querySelectorAll('#ch .w'),k;
    for(k=0;k<ws.length;k++) if(el.compareDocumentPosition(ws[k])&4){ ws[k].click(); return; }
  }
  var still=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.scrollTo({top:el.getBoundingClientRect().top+window.pageYOffset-cover()-12,behavior:still?'auto':'smooth'});
  try{ history.replaceState(history.state,'','#'+el.id); }catch(x){}
});
d.addEventListener('keydown',function(e){ if(e.key==='Escape'&&find()&&!list.hidden){ open(false); btn.focus(); } });
function soon(){ if(!raf) raf=requestAnimationFrame(function(){ raf=0; current(); }); }
window.addEventListener('scroll',soon,{passive:true});
d.addEventListener('timeupdate',soon,true);   // the recording's progress (media events reach the document only on the way down)
window.addEventListener('resize',function(){ navh(); current(); });
navh(); current();
})();
