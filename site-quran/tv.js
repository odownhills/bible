/* Watch (called "TV mode" until 2026-11-23; its code and files keep the name "tv"): a chapter's recording with
   a picture for each part of it and the words lighting up as they are spoken, full screen. It opens over the
   page it is started from (a chapter page's "Watch" button, or a chapter on a Watch page), so one tap goes
   straight to the full-screen picture with the voice playing, and carries on from chapter to chapter.

   It reuses what Listen + Read already has: the recording, the read-aloud text (text/<book>/<n>.txt, which
   never holds alternate readings or notes) and the start time of every word (audio/<book>/<n>.json, made
   by scripts/align.py). The only extra data is tv/<book>/<n>.json: where each verse starts and which
   picture starts at which word (scripts/build.py). A chapter whose pictures are not made yet plays with
   its words alone on a quiet background.

   The Quran site uses it too, for whole surahs in English (scripts/quran_site.py, manifest-en.json, ids
   "en-<surah>") and in Arabic (scripts/quran_ar.py, manifest-ar.json, ids "ar-<surah>"). Their recordings
   play straight from the server instead of being downloaded whole first (they can be hours long), the
   seek bar marks where each section of the surah starts, and the Arabic words are shown right to left in
   the Quran font, a verse or a phrase at a time. The Arabic is shown in the spelling the reader chose
   (Obay, 2026-11-23): modern spelling in an everyday font (manifest-ar.json, the default), or the traditional
   Uthmani script in the Quran font (manifest-ar-uthmani.json): the spelling of the page TV mode is opened from, else the choice remembered in
   this browser (arScript, scripts/lang.js).

   Verse numbers (Obay, 2026-11-22: "the video doesn't show the verse numbers"): the top-left corner names the
   book, chapter and verse being read ("1 John 4 · verse 4"); without pictures, the title and verse sit at the
   top in the middle instead. The words themselves are only the text, cleanly written, with no verse numbers
   in them, in English or Arabic (Obay, 2026-11-23: "we already have it in the top left corner").

   Written in plain old JavaScript on purpose, so that the browsers built into TVs can run it. */
(function(){
'use strict';
var d=document,win=window;
if(win.TVMode)return;
var here=d.currentScript&&d.currentScript.src,ROOT=new URL('.',here||new URL('../tv.js',location.href).href).href;
var LEAD=0.06,RATES=[1,1.1,1.25,1.5],SITE='The Quran, Freshly Translated';
var WORD;   // one spoken word: the same rule as scripts/build.py
try{ WORD=new RegExp('[^\\s\\u2014\\u2013]*[\\p{L}\\p{N}_][^\\s\\u2014\\u2013]*','gu'); }
catch(e){ WORD=/[^\s—–]*[\wÀ-ɏ][^\s—–]*/g; }
var SILENT='data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';

var I={
  play:'<path class="tv-s" d="M8 5.2v13.6a.6.6 0 0 0 .9.5l11-6.8a.6.6 0 0 0 0-1L8.900 4.700a.6.6 0 0 0-.9.5z"/>',
  pause:'<path class="tv-s" d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/>',
  back:'<path d="M4 12a8 8 0 1 0 2.6-5.9"/><path d="M3.5 3.5V7H7"/>',
  fwd:'<path d="M20 12a8 8 0 1 1-2.6-5.9"/><path d="M20.5 3.5V7H17"/>',
  prev:'<path class="tv-s" d="M18 6.2v11.6L9.500 12z"/><path d="M6.500 6v12"/>',
  next:'<path class="tv-s" d="M6 6.2v11.6l8.500-5.800z"/><path d="M17.500 6v12"/>',
  words:'<rect x="3" y="5" width="18" height="14" rx="2.500"/><path d="M7 11h4M13.500 11H17M7 15h7"/>',
  wordsOff:'<rect x="3" y="5" width="18" height="14" rx="2.500"/><path d="M5 20.500L19.500 3.500"/>',
  full:'<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  small:'<path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/>',
  x:'<path d="M6 6l12 12M18 6L6 18"/>'
};
function svg(p){ return '<svg viewBox="0 0 24 24" aria-hidden="true">'+p+'</svg>'; }

var CSS=
'html.tv-open,html.tv-open body{overflow:hidden}'+
'#tv{position:fixed;left:0;top:0;right:0;bottom:0;z-index:1000;background:#000;color:#E8E2F2;overflow:hidden;outline:none;'+
  'font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-size:16px;line-height:1.4;text-align:left;'+
  '-webkit-user-select:none;user-select:none;-webkit-tap-highlight-color:transparent;touch-action:manipulation}'+
'#tv[hidden]{display:none}'+
'#tv *{box-sizing:border-box}'+
'#tv.tv-idle{cursor:none}'+
'#tv button{font:inherit;color:inherit;background:none;border:0;padding:0;margin:0;cursor:pointer;-webkit-tap-highlight-color:transparent}'+
'#tv button:focus,#tv a:focus{outline:2px solid #B79BE8;outline-offset:2px}'+
'#tv button:focus:not(:focus-visible),#tv a:focus:not(:focus-visible){outline:none}'+
'#tv svg{width:1.5rem;height:1.5rem;fill:none;stroke:#fff;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round;display:block}'+
'#tv svg .tv-s{fill:#fff;stroke:none}'+

/* the pictures: two layers that fade into each other, each drifting slowly while it is up */
'.tv-pic{position:absolute;left:0;top:0;right:0;bottom:0;opacity:0;transition:opacity 1.4s ease;overflow:hidden}'+
'.tv-pic.tv-on{opacity:1}'+
'.tv-pic img{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;object-position:50% 12%;'+
  '-webkit-transform-origin:50% 30%;transform-origin:50% 30%;-webkit-animation:20s linear both;animation:20s linear both;will-change:transform}'+
'#tv.tv-paused .tv-pic img{-webkit-animation-play-state:paused;animation-play-state:paused}'+
'@keyframes tvkb0{from{transform:scale(1.02) translate(-.8%,0)}to{transform:scale(1.1) translate(.8%,-.6%)}}'+
'@keyframes tvkb1{from{transform:scale(1.1) translate(.8%,-.4%)}to{transform:scale(1.02) translate(-.6%,0)}}'+
'@keyframes tvkb2{from{transform:scale(1.02) translate(.6%,.4%)}to{transform:scale(1.1) translate(-.8%,-.4%)}}'+
'@keyframes tvkb3{from{transform:scale(1.1) translate(-.6%,-.6%)}to{transform:scale(1.02) translate(.6%,0)}}'+
'.tv-scrim{position:absolute;left:0;top:0;right:0;bottom:0;pointer-events:none;transition:opacity 1.2s ease;'+
  'background:linear-gradient(to bottom,rgba(0,0,0,.42) 0,rgba(0,0,0,0) 16%,rgba(0,0,0,0) 52%,rgba(8,5,16,.62) 76%,rgba(8,5,16,.9) 100%)}'+

/* a chapter with no pictures yet: a quiet background and the words in the middle */
'.tv-plain{position:absolute;left:0;top:0;right:0;bottom:0;opacity:0;transition:opacity 1.2s ease;overflow:hidden;pointer-events:none;'+
  'background:#171223;background:radial-gradient(120% 95% at 50% 0%,#2C2247 0%,#171223 58%,#0E0A18 100%)}'+
'.tv-plain i{position:absolute;border-radius:50%;animation:tvglow 38s ease-in-out infinite alternate}'+
'.tv-plain i:first-child{width:70vw;height:70vw;left:-22vw;top:-34vw;background:radial-gradient(closest-side,rgba(96,70,168,.5),rgba(96,70,168,0))}'+
'.tv-plain i+i{width:60vw;height:60vw;right:-18vw;bottom:-36vw;background:radial-gradient(closest-side,rgba(183,155,232,.22),rgba(183,155,232,0));animation-duration:47s;animation-direction:alternate-reverse}'+
'@keyframes tvglow{from{transform:translate(0,0) scale(1)}to{transform:translate(7vw,4vw) scale(1.18)}}'+
'#tv.tv-paused .tv-plain i{animation-play-state:paused}'+
'.tv-plain div{position:absolute;left:0;right:0;top:15%;text-align:center;padding:0 6vw}'+
'.tv-plain b{display:block;font-family:Georgia,"Times New Roman",Times,serif;font-weight:normal;color:#C9B8EC;opacity:.9;font-size:2.4rem;font-size:clamp(1.6rem,4.6vw,4.2rem);line-height:1.15}'+
'.tv-plain em{display:block;min-height:1.3em;margin-top:.45em;font-style:normal;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-size:.9rem;font-size:clamp(.8rem,1.5vw,1.35rem);letter-spacing:.16em;text-transform:uppercase;color:#B79BE8}'+
'.tv-plain small{display:block;margin-top:.7em;font-size:.72rem;font-size:clamp(.66rem,1.05vw,.95rem);letter-spacing:.16em;text-transform:uppercase;color:#B3A7C9;opacity:.75}'+
'#tv.tv-noimg .tv-plain{opacity:1}'+
'#tv.tv-noimg .tv-scrim,#tv.tv-noimg .tv-tag{opacity:0}'+
'#tv.tv-noimg .tv-pic{opacity:0}'+

/* where we are */
'.tv-tag{position:absolute;top:3.2vh;top:max(3.2vh,env(safe-area-inset-top));left:3vw;left:max(3vw,env(safe-area-inset-left));font-size:.8rem;font-size:clamp(.72rem,1.25vw,1.15rem);'+
  'letter-spacing:.14em;text-transform:uppercase;color:#fff;opacity:.86;text-shadow:0 1px 6px rgba(0,0,0,.8);transition:opacity .6s ease;pointer-events:none}'+
'.tv-tag span{color:#B79BE8;margin-left:.9em}'+

/* the words, lighting up as they are spoken */
'.tv-cap{position:absolute;left:50%;bottom:9vh;bottom:max(9vh,calc(env(safe-area-inset-bottom) + 3.4rem));width:88vw;width:min(88vw,34em);'+
  '-webkit-transform:translateX(-50%);transform:translateX(-50%);font-family:Georgia,"Times New Roman",Times,serif;font-size:2rem;font-size:clamp(1.25rem,3.3vw,3.3rem);line-height:1.32;'+
  'text-align:center;text-wrap:balance;color:rgba(232,226,242,.8);text-shadow:0 2px 3px rgba(0,0,0,.9),0 0 22px rgba(0,0,0,.75);'+
  'transition:opacity .22s ease,transform .3s ease,-webkit-transform .3s ease;pointer-events:none}'+
'.tv-cap.tv-out{opacity:0}'+
'.tv-cap .tv-w{transition:color .12s linear}'+
'.tv-cap .tv-w.tv-on{color:#fff}'+
/* over a picture the words sit on a soft dark box, so they stay easy to read on bright pictures;
   the box is fitted to the lines of words (fit()), so it hides as little of the picture as it can */
'.tv-cap>span{position:relative}'+
'.tv-box{position:absolute;left:0;top:0;width:0;height:0;border-radius:.42em;background:rgba(10,7,20,.74)}'+
'#tv.tv-noimg .tv-box{display:none}'+
'#tv.tv-ui .tv-cap{-webkit-transform:translate(-50%,-1.9rem);transform:translate(-50%,-1.9rem)}'+
/* a phone held sideways: the words sit lower, over the plain foreground, and rise above the controls when they show */
'@media (orientation:landscape) and (max-height:500px){'+
  '.tv-cap{bottom:6vh;bottom:max(6vh,calc(env(safe-area-inset-bottom) + 1.3rem))}'+
  '#tv.tv-ui .tv-cap{-webkit-transform:translate(-50%,-4rem);transform:translate(-50%,-4rem)}}'+
'#tv.tv-nowords .tv-cap{display:none}'+
'#tv.tv-noimg .tv-cap{bottom:auto;top:43%;text-shadow:none}'+
'#tv.tv-noimg.tv-ui .tv-cap{-webkit-transform:translateX(-50%);transform:translateX(-50%)}'+
'#tv.tv-rtl .tv-cap{direction:rtl;font-family:"Quran Text","Noto Naskh Arabic","Geeza Pro",serif;font-size:2.4rem;font-size:clamp(1.6rem,4.4vw,4.4rem);line-height:1.75;width:88vw;width:min(90vw,26em)}'+
'#tv.tv-modern .tv-cap{font-family:"Arabic Text","Noto Naskh Arabic","Geeza Pro",serif;line-height:1.85}'+
'#tv.tv-rtl.tv-noimg.tv-ui .tv-cap{opacity:.22}'+

/* controls: they come up on a tap, a key or a move of the mouse, and leave again while it plays */
'.tv-ctl{opacity:0;visibility:hidden;transition:opacity .25s ease,visibility 0s linear .25s}'+
'#tv.tv-ui .tv-ctl{opacity:1;visibility:visible;transition:opacity .25s ease}'+
'#tv.tv-busy .tv-mid,#tv.tv-covered .tv-ctl{opacity:0;visibility:hidden}'+
'#tv.tv-covered .tv-cap,#tv.tv-covered .tv-tag,#tv.tv-covered .tv-plain div{opacity:0}'+
'.tv-x{position:absolute;top:2vh;top:max(2vh,env(safe-area-inset-top));right:2vw;right:max(2vw,env(safe-area-inset-right))}'+
'#tv .tv-x button{width:3rem;height:3rem;border-radius:50%;background:rgba(12,8,22,.5);display:flex;align-items:center;justify-content:center}'+
'.tv-mid{position:absolute;left:50%;top:50%;-webkit-transform:translate(-50%,-50%);transform:translate(-50%,-50%);display:flex;align-items:center}'+
'#tv .tv-mid button{position:relative;display:flex;align-items:center;justify-content:center;border-radius:50%;background:rgba(12,8,22,.5);width:3.6rem;height:3.6rem;margin:0 1.1rem;margin:0 clamp(.7rem,3vw,2.2rem)}'+
'#tv .tv-mid button svg{width:2.1rem;height:2.1rem}'+
'#tv .tv-mid button span{position:absolute;left:50%;top:50%;transform:translate(-50%,-38%);font-size:.62rem;font-weight:700}'+
'#tv .tv-mid .tv-big{width:5rem;height:5rem;background:rgba(183,155,232,.92)}'+
'#tv .tv-mid .tv-big svg{width:2.5rem;height:2.5rem}'+
'#tv .tv-mid .tv-big svg .tv-s{fill:#171223}'+
'#tv .tv-x button:hover,#tv .tv-mid button:hover{background:rgba(60,45,95,.8)}'+
'#tv .tv-mid .tv-big:hover{background:#C9B8EC}'+
'@media (max-height:480px){#tv .tv-mid button{width:3.1rem;height:3.1rem}#tv .tv-mid .tv-big{width:4.1rem;height:4.1rem}}'+
'.tv-bar{position:absolute;left:0;right:0;bottom:0;display:flex;align-items:center;font-size:.82rem;color:#fff;'+
  'padding:1.8rem 2.5vw .5rem;padding:1.8rem max(2.5vw,env(safe-area-inset-right)) max(.5rem,env(safe-area-inset-bottom)) max(2.5vw,env(safe-area-inset-left));'+
  'background:linear-gradient(to top,rgba(0,0,0,.85),rgba(0,0,0,0))}'+
'.tv-r1{flex:1;display:flex;align-items:center;min-width:0}'+
'.tv-r2{display:flex;align-items:center;margin-left:.4rem}'+
'#tv .tv-bar button{min-width:2.75rem;height:2.75rem;flex:none;display:flex;align-items:center;justify-content:center;border-radius:999px}'+
'#tv .tv-bar button:hover{background:rgba(255,255,255,.14)}'+
'#tv .tv-bar button[disabled]{opacity:.32;cursor:default;background:none}'+
'#tv .tv-bar .tv-rate{padding:0 .7rem;font-variant-numeric:tabular-nums}'+
'#tv .tv-bar .tv-off svg{opacity:.55}'+
'.tv-t{font-variant-numeric:tabular-nums;min-width:2.9em;text-align:center;opacity:.92}'+
'.tv-seekw{position:relative;flex:1;min-width:3rem;height:2.75rem;margin:0 .45rem}'+
'.tv-ticks{position:absolute;left:8px;right:8px;top:50%;height:0;pointer-events:none}'+
'.tv-ticks i{position:absolute;top:-4px;width:2px;height:8px;margin-left:-1px;border-radius:1px;background:rgba(255,255,255,.6)}'+
'#tv .tv-seek{position:absolute;left:0;top:0;width:100%;height:100%;margin:0;padding:0;background:transparent;-webkit-appearance:none;appearance:none;cursor:pointer;touch-action:none}'+
'#tv .tv-seek:focus{outline:2px solid #B79BE8;outline-offset:-6px;border-radius:8px}'+
'#tv .tv-seek:focus:not(:focus-visible){outline:none}'+
'#tv .tv-seek::-webkit-slider-runnable-track{height:4px;border-radius:2px;background:rgba(255,255,255,.3);background:linear-gradient(to right,#B79BE8 var(--p,0%),rgba(255,255,255,.3) var(--p,0%))}'+
'#tv .tv-seek::-moz-range-track{height:4px;border-radius:2px;background:rgba(255,255,255,.3)}'+
'#tv .tv-seek::-moz-range-progress{height:4px;border-radius:2px;background:#B79BE8}'+
'#tv .tv-seek::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:#fff;margin-top:-6px;border:0}'+
'#tv .tv-seek::-moz-range-thumb{width:16px;height:16px;border:0;border-radius:50%;background:#fff}'+

/* the opening and closing card */
'.tv-cover{position:absolute;left:0;top:0;right:0;bottom:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:6vh 6vw;background:rgba(12,8,22,.68)}'+
'.tv-cover[hidden]{display:none}'+
'.tv-kick{font-size:.8rem;font-size:clamp(.72rem,1.2vw,1rem);letter-spacing:.2em;text-transform:uppercase;color:#B79BE8}'+
'.tv-title{font-family:Georgia,"Times New Roman",Times,serif;color:#fff;font-size:3rem;font-size:clamp(2rem,6vw,5rem);line-height:1.15;margin-top:.9rem;text-shadow:0 2px 18px rgba(0,0,0,.7)}'+
'.tv-msg{color:#B3A7C9;font-size:.95rem;font-size:clamp(.85rem,1.3vw,1.05rem);max-width:30em;margin-top:.9rem}'+
'.tv-msg:empty{display:none}'+
'#tv .tv-go{display:inline-flex;align-items:center;font-size:1.1rem;font-size:clamp(1rem,1.5vw,1.25rem);color:#171223;background:#B79BE8;border-radius:999px;padding:.8rem 1.6rem .8rem 1.25rem;margin-top:1.5rem}'+
'#tv .tv-go:hover{background:#C9B8EC}'+
'#tv .tv-go[hidden]{display:none}'+
'#tv .tv-go svg{width:1.3em;height:1.3em;margin-right:.55rem}'+
'#tv .tv-go svg .tv-s{fill:#171223}'+
'.tv-alt{margin-top:1.3rem;display:flex;flex-wrap:wrap;justify-content:center}'+
'#tv .tv-alt button,#tv .tv-alt a{font-size:.9rem;color:#C4B4E2;text-decoration:underline;text-underline-offset:.2em;margin:.35rem .9rem;padding:.3rem .1rem;border-radius:4px}'+
'#tv .tv-alt [hidden]{display:none}'+
'.tv-spin{position:absolute;left:50%;top:50%;width:3rem;height:3rem;margin:-1.5rem 0 0 -1.5rem;border:3px solid rgba(255,255,255,.22);border-top-color:#fff;border-radius:50%;animation:tvspin .9s linear infinite}'+
'.tv-spin[hidden]{display:none}'+
'@keyframes tvspin{to{transform:rotate(360deg)}}'+

/* short notes at the top, and the mark a double tap leaves */
'.tv-toast{position:absolute;left:50%;top:3vh;top:max(3vh,env(safe-area-inset-top));-webkit-transform:translate(-50%,-.6rem);transform:translate(-50%,-.6rem);opacity:0;visibility:hidden;'+
  'transition:opacity .3s ease,transform .3s ease,visibility 0s linear .3s;display:flex;align-items:center;max-width:92vw;background:rgba(23,18,35,.9);border:1px solid rgba(183,155,232,.5);'+
  'border-radius:999px;padding:.5rem 1.1rem;font-size:.88rem;color:#E8E2F2;box-shadow:0 6px 24px rgba(0,0,0,.45)}'+
'.tv-toast.tv-on{opacity:1;visibility:visible;-webkit-transform:translate(-50%,0);transform:translate(-50%,0);transition:opacity .3s ease,transform .3s ease}'+
'#tv .tv-toast button{margin:0 -.55rem 0 .9rem;padding:.3rem .85rem;border-radius:999px;background:#B79BE8;color:#171223;font-size:.82rem;white-space:nowrap}'+
'#tv .tv-toast button[hidden]{display:none}'+
'.tv-nudge{position:absolute;top:50%;margin-top:-1.4rem;height:2.8rem;line-height:2.8rem;padding:0 1.1rem;border-radius:999px;background:rgba(12,8,22,.6);font-size:.95rem;font-weight:600;opacity:0;transition:opacity .35s ease;pointer-events:none}'+
'.tv-nudge.tv-l{left:9vw}.tv-nudge.tv-r{right:9vw}'+
'.tv-nudge.tv-on{opacity:1;transition:none}'+

/* a phone held upright: the wide picture sits on top with the words below it */
'@media (orientation:portrait){'+
  '#tv .tv-pic{bottom:auto;height:58vh}'+
  '#tv .tv-scrim{background:linear-gradient(to bottom,rgba(0,0,0,.42) 0,rgba(0,0,0,0) 12%,rgba(0,0,0,0) 40%,#000 58%,#000 100%)}'+
  '#tv .tv-cap,#tv.tv-ui .tv-cap{bottom:auto;top:58vh;height:calc(42vh - 7.5rem);display:flex;align-items:center;justify-content:center;width:88vw;font-size:1.6rem;font-size:clamp(1.35rem,6.4vw,2.3rem);-webkit-transform:translateX(-50%);transform:translateX(-50%)}'+
  '#tv .tv-box{display:none}'+
  '#tv.tv-noimg .tv-cap{top:34vh;height:auto}'+
  '#tv.tv-rtl .tv-cap,#tv.tv-rtl.tv-ui .tv-cap{font-size:1.8rem;font-size:clamp(1.6rem,7.4vw,2.8rem)}'+
  '#tv .tv-mid{top:29vh}'+
  '#tv.tv-noimg .tv-mid{top:auto;bottom:8.5rem;-webkit-transform:translateX(-50%);transform:translateX(-50%)}'+
  '#tv .tv-bar{flex-direction:column;align-items:stretch;padding-top:1rem;background:linear-gradient(to top,#000 60%,rgba(0,0,0,0))}'+
  '#tv .tv-r2{margin:0;justify-content:space-between}'+
'}'+
'@media (prefers-reduced-motion:reduce){.tv-pic img,.tv-plain i{-webkit-animation:none!important;animation:none!important}.tv-pic{transition-duration:.4s}}';

var stage=null,audio,cap,capIn,capBox,seek,layers,el={};
var S={open:false,serial:0,ready:false,ui:false,top:0,scene:-1,card:-1,word:-1,verse:-2,words:[],seps:[],T:[],cards:[],scenes:[],verses:[],saved:0};
var manifests={},cache={},order=[],wake=null,raf=0,idleT=0,toastT=0,nudgeT=0,cw=null,lastType='mouse',tapAt=0,tapZone=0,mx=-1,my=-1;

function get(k,v){try{var x=localStorage.getItem(k);return x==null?v:JSON.parse(x)}catch(e){return v}}
function put(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function fmt(s){if(!isFinite(s)||s<0)s=0;s=Math.floor(s);var m=Math.floor(s/60),x=s%60;return m+':'+(x<10?'0':'')+x}
function rate(){var r=parseFloat(get('tvRate',1));return RATES.indexOf(r)<0?1:r}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function noop(){}
function json(u){return fetch(u).then(function(r){if(!r.ok)throw new Error('load');return r.json()})}
function name(c){return c.title||c.book+' '+c.chapter}
function home(){return !!(d.getElementById('tv-resume')||d.getElementById('tv-list'))}   // a Watch page, not a chapter page
function listPage(c){   // the Watch page that lists a chapter: its book's (the Bible), or the surahs in English or Arabic
  var id=(c&&c.id)||'';
  return ROOT+(/^ar-/.test(id)?'ar/watch.html':/^en-/.test(id)||!c?'watch/':'watch/'+c.slug+'/');
}
function coarse(){return !!(win.matchMedia&&win.matchMedia('(pointer:coarse)').matches)}

/* ---- what a chapter needs: fetched once, the next chapter ahead of time ---- */
function manifest(id){
  // the Quran's whole surahs have their own lists, in Arabic and in English
  var f=/^ar-/.test(id||'')?(script()==='uthmani'?'manifest-ar-uthmani.json':'manifest-ar.json'):/^en-/.test(id||'')?'manifest-en.json':'manifest.json';
  if(!manifests[f]){ manifests[f]=json(ROOT+f); manifests[f].catch(function(){ delete manifests[f]; }); }
  return manifests[f];
}
function script(){   // the Arabic's spelling: the page's own, else the reader's choice
  var ch=d.getElementById('ch'); return ch&&ch.getAttribute('data-script')||get('arScript','modern');
}
function bundle(c){
  var key=c.id+(c.script?'.'+c.script:'');   // one surah in two spellings
  if(cache[key])return cache[key];
  // The recording is downloaded whole and played from memory, as Listen + Read does: it can then be
  // moved around in at once, and the next chapter starts without a gap.
  var p=Promise.all([
    json(ROOT+(c.tv||'tv/'+c.slug+'/'+c.chapter+'.json')).catch(function(){return {verses:[],scenes:[]}}),
    fetch(ROOT+c.text).then(function(r){if(!r.ok)throw new Error('load');return r.text()}),
    c.sync?json(ROOT+c.sync).catch(function(){return null}):null,
    c.stream?ROOT+c.audio:fetch(ROOT+c.audio).then(function(r){if(!r.ok)throw new Error('load');return r.blob()}).then(function(b){return URL.createObjectURL(b)})
  ]).then(function(g){return {tv:g[0],text:g[1],sync:g[2],src:g[3]}});
  cache[key]=p; order.push(key);
  p.catch(function(){ if(cache[key]===p){ delete cache[key]; order.splice(order.indexOf(key),1); } });
  while(order.length>3){
    var old=order[0]; if(S.me&&old===S.me.id+(S.me.script?'.'+S.me.script:'')){ if(order.length<2)break; order.push(order.shift()); continue; }
    order.shift(); (function(q){ if(q) q.then(function(b){ if(b.src.indexOf('blob:')===0) URL.revokeObjectURL(b.src); },noop); })(cache[old]); delete cache[old];
  }
  return p;
}

/* ---- the screen ---- */
function build(){
  if(stage)return;
  var st=d.createElement('style'); st.textContent=CSS; d.head.appendChild(st);
  stage=d.createElement('div'); stage.id='tv'; stage.className='tv-paused'; stage.hidden=true; stage.tabIndex=-1;
  stage.setAttribute('role','dialog'); stage.setAttribute('aria-label','Watch');
  function b(id,label,inner,cls){ return '<button type="button" id="tv-'+id+'" aria-label="'+label+'" title="'+label+'"'+(cls?' class="'+cls+'"':'')+'>'+inner+'</button>'; }
  stage.innerHTML=
    '<div class="tv-pic"><img alt=""></div><div class="tv-pic"><img alt=""></div>'+
    '<div class="tv-plain"><i></i><i></i><div><b id="tv-ptitle"></b><em id="tv-pverse"></em><small></small></div></div>'+
    '<div class="tv-scrim"></div>'+
    '<div class="tv-tag" id="tv-tag"></div>'+
    '<div class="tv-cap tv-out" id="tv-cap" aria-live="off"><i class="tv-box"></i><span></span></div>'+
    '<div class="tv-nudge tv-l" id="tv-nl">&minus;10 s</div><div class="tv-nudge tv-r" id="tv-nr">+10 s</div>'+
    '<div class="tv-ctl tv-mid">'+
      b('back','Back 10 seconds',svg(I.back)+'<span>10</span>')+
      b('play','Play',svg(I.play),'tv-big')+
      b('fwd','Forward 10 seconds',svg(I.fwd)+'<span>10</span>')+
    '</div>'+
    '<div class="tv-ctl tv-bar">'+
      '<div class="tv-r1"><span class="tv-t" id="tv-cur">0:00</span>'+
        '<div class="tv-seekw"><div class="tv-ticks" id="tv-ticks"></div><input class="tv-seek" id="tv-seek" type="range" min="0" max="100" step="1" value="0" aria-label="Position"></div>'+
        '<span class="tv-t" id="tv-rem">0:00</span></div>'+
      '<div class="tv-r2">'+
        b('prev','Before this',svg(I.prev))+
        b('next','Next',svg(I.next))+
        b('rate','Speed','1&times;','tv-rate')+
        b('words','Hide the words',svg(I.words))+
        b('full','Full screen',svg(I.full))+
      '</div>'+
    '</div>'+
    '<div class="tv-ctl tv-x">'+b('close','Close',svg(I.x))+'</div>'+
    '<div class="tv-cover" id="tv-cover" hidden>'+
      '<div class="tv-kick" id="tv-kick">Watch</div><div class="tv-title" id="tv-title">&nbsp;</div><div class="tv-msg" id="tv-msg"></div>'+
      '<button class="tv-go" id="tv-go" type="button">'+svg(I.play)+'<span id="tv-go-t">Play</span></button>'+
      '<div class="tv-alt"><button type="button" id="tv-again" hidden>Start from the beginning</button><a id="tv-all" href="'+ROOT+'watch/" hidden>Choose another surah</a><button type="button" id="tv-leave">Close</button></div>'+
    '</div>'+
    '<div class="tv-spin" id="tv-spin" hidden></div>'+
    '<div class="tv-toast" id="tv-toast" role="status"><span></span><button type="button" hidden></button></div>';
  d.body.appendChild(stage);
  audio=d.createElement('audio'); audio.preload='auto'; stage.appendChild(audio);
  ['tag','cap','seek','ticks','cur','rem','play','back','fwd','prev','next','rate','words','full','close','cover','kick','title','msg','go','go-t','again','all','leave','spin','toast','nl','nr','ptitle','pverse']
    .forEach(function(k){ el[k]=d.getElementById('tv-'+k); });
  cap=el.cap; capBox=cap.firstChild; capIn=cap.lastChild; seek=el.seek; layers=stage.querySelectorAll('.tv-pic');

  audio.addEventListener('play',function(){ if(!S.ready)return; stage.classList.remove('tv-paused'); icons(); loop(); awake(true); poke(); });
  audio.addEventListener('pause',function(){ if(!S.ready)return; stage.classList.add('tv-paused'); icons(); awake(false); if(!audio.ended){ savePos(true); poke(); } });
  audio.addEventListener('timeupdate',function(){ if(!S.ready)return; paint(); mark(); savePos(false); });
  audio.addEventListener('seeked',function(){ if(!S.ready)return; paint(); mark(); });
  audio.addEventListener('ratechange',posState);
  audio.addEventListener('ended',ended);
  audio.addEventListener('error',function(){ if(S.ready){ S.ready=false; fail('load'); } });

  el.play.onclick=toggle;
  el.back.onclick=function(){ nudge(-10); };
  el.fwd.onclick=function(){ nudge(10); };
  el.prev.onclick=function(){ if(S.prev) load(S.prev.id,{play:true,t:0}); };
  el.next.onclick=function(){ if(S.next) load(S.next.id,{play:true,t:0}); };
  el.rate.onclick=function(){ var r=RATES[(RATES.indexOf(rate())+1)%RATES.length]; put('tvRate',r); audio.defaultPlaybackRate=r; audio.playbackRate=r; paint(); icons(); };
  el.words.onclick=function(){ put('tvWords',!get('tvWords',true)); icons(); };
  el.full.onclick=function(){ if(fsEl()){ S.leaving=true; leaveFull(); } else goFull(); };
  el.close.onclick=close; el.leave.onclick=close;
  el.go.onclick=function(){
    if(S.cover==='error'){ load(S.id,{play:true}); return; }
    if(!S.ready)return;
    if(S.cover==='end') audio.currentTime=0;
    play(); goFull();   // the voice first: asking for the full screen uses up the tap
  };
  el.again.onclick=function(){ if(!S.ready)return; audio.currentTime=0; play(); goFull(); };
  el.toast.lastChild.onclick=function(){ var f=S.toastDo; toast(null); if(f) f(); };

  seek.addEventListener('input',function(){ S.drag=true; paint(); mark(); poke(); });
  seek.addEventListener('change',function(){ var v=parseFloat(seek.value); S.drag=false; jump(v); });

  stage.addEventListener('pointerdown',function(e){ lastType=e.pointerType||'mouse'; },true);
  stage.addEventListener('touchstart',function(){ lastType='touch'; },{passive:true,capture:true});
  stage.addEventListener('mousemove',function(e){ if(e.clientX===mx&&e.clientY===my)return; mx=e.clientX; my=e.clientY; if(lastType!=='touch') poke(); });
  stage.addEventListener('click',function(e){
    var t=e.target;
    if(t.closest('.tv-ctl')||t.closest('.tv-cover')||t.closest('.tv-toast')){ poke(); return; }
    if(!S.ready||S.cover)return;
    if(lastType==='touch'){
      // a tap brings the controls up or sends them away; a double tap at either side moves 10 seconds
      var now=Date.now(),x=e.clientX/stage.clientWidth,zone=x<0.34?-1:x>0.66?1:0;
      if(zone&&zone===tapZone&&now-tapAt<340){ tapAt=0; nudge(zone*10,true); if(!audio.paused) ui(false); return; }
      tapAt=now; tapZone=zone;
      if(S.ui&&!audio.paused) ui(false); else poke();
    }else{ toggle(); poke(); }
  });
  stage.addEventListener('dblclick',function(e){
    var t=e.target; if(lastType==='touch'||t.closest('.tv-ctl')||t.closest('.tv-cover')||t.closest('.tv-toast'))return;
    if(fsEl()){ S.leaving=true; leaveFull(); } else goFull();
  });
  d.addEventListener('keydown',key,true);
  d.addEventListener('focusin',function(e){ if(S.open&&!stage.contains(e.target)) focusStage(); });
  ['fullscreenchange','webkitfullscreenchange'].forEach(function(ev){ d.addEventListener(ev,fsChange); });
  d.addEventListener('visibilitychange',function(){ if(!S.open)return; if(d.hidden) savePos(true); else if(!audio.paused) awake(true); });
  win.addEventListener('pagehide',function(){ if(S.open) savePos(true); });
  win.addEventListener('resize',function(){ if(S.open) fit(); });
  if(d.fonts&&d.fonts.addEventListener) d.fonts.addEventListener('loadingdone',function(){ if(S.open) fit(); });   // e.g. the Arabic font arriving after the first words
}
function focusStage(){ try{ stage.focus({preventScroll:true}); }catch(e){ stage.focus(); } }
function icons(){
  var paused=audio.paused||!S.ready,words=get('tvWords',true),full=!!fsEl();
  el.play.innerHTML=svg(paused?I.play:I.pause); label(el.play,paused?'Play':'Pause');
  el.words.innerHTML=svg(words?I.words:I.wordsOff); el.words.className=words?'':'tv-off'; label(el.words,words?'Hide the words':'Show the words');
  stage.classList.toggle('tv-nowords',!words);
  el.full.innerHTML=svg(full?I.small:I.full); label(el.full,full?'Leave full screen':'Full screen');
  el.rate.innerHTML=String(rate())+'&times;';
  el.prev.disabled=!S.prev; el.next.disabled=!S.next;
  label(el.prev,S.prev?name(S.prev):'Before this'); label(el.next,S.next?name(S.next):'Next');
}
function label(b,t){ b.setAttribute('aria-label',t); b.title=t; }
function ui(on){
  S.ui=on; stage.classList.toggle('tv-ui',on); clearTimeout(idleT);
  if(!on){ stage.classList.add('tv-idle'); if(stage.contains(d.activeElement)&&d.activeElement!==stage) focusStage(); }
  else stage.classList.remove('tv-idle');
}
function poke(){
  if(!S.open)return;
  ui(true);
  if(S.ready&&!audio.paused) idleT=setTimeout(function(){ if(S.ready&&!audio.paused&&!S.drag&&!S.cover) ui(false); },3200);
}
function spin(on){ el.spin.hidden=!on; stage.classList.toggle('tv-busy',!!on); }
function toast(text,action,fn,ms){
  clearTimeout(toastT); var t=el.toast;
  if(!text){ t.classList.remove('tv-on'); S.toastDo=null; return; }
  t.firstChild.textContent=text; t.lastChild.hidden=!action; t.lastChild.textContent=action||''; S.toastDo=fn||null;
  t.classList.add('tv-on'); toastT=setTimeout(function(){ toast(null); },ms||7000);
}
function cover(kind,pos){
  S.cover=kind||null; el.cover.hidden=!kind; stage.classList.toggle('tv-covered',!!kind);
  if(!kind)return;
  var c=S.me,plain=S.ready&&!S.scenes.length,go='Play',msg='',kick='Watch',title=c?name(c):'Watch',again=false,all=false;
  if(kind==='start'){
    if(pos>5){ go='Carry on from '+fmt(pos); again=true; }
    if(plain) msg='';
  }else if(kind==='end'){
    kick='End of '+name(c); title='You are all caught up'; msg=''; go='Play '+name(c)+' again'; all=!home();
  }else{
    go=kind==='error'?'Try again':'';
    msg=kind==='noaudio'?'This has no recording yet. It will be added soon.':
        kind==='unknown'?'That was not found.':'This could not be loaded. Check your connection and try again.';
    all=!home();
  }
  el.kick.textContent=kick; el.title.textContent=title; el.msg.textContent=msg;
  el.go.hidden=!go; el['go-t'].textContent=go; el.again.hidden=!again; el.all.hidden=!all; el.all.href=listPage(c);
  el.leave.textContent=d.getElementById('ch')?'Back to the surah':home()?'Back to the list':'Close';
  ui(false); stage.classList.remove('tv-idle'); spin(false);
  if(stage.contains(d.activeElement)||d.activeElement===d.body) (go?el.go:el.leave).focus();
}
function fail(why){ S.ready=false; cover(why==='unknown'||why==='noaudio'?why:'error'); }

/* ---- loading a chapter ---- */
function load(id,o){
  var mine=++S.serial; o=o||{};
  if(S.ready) savePos(true);
  S.ready=false; S.id=id; S.drag=false;
  try{ audio.pause(); }catch(e){}
  S.scene=S.card=S.word=-1; S.verse=-2; cap.classList.add('tv-out'); cover(null); toast(null); spin(true);
  stage.classList.add('tv-paused'); ui(false); stage.classList.remove('tv-idle');
  manifest(id).then(function(m){
    var i=-1,k; for(k=0;k<m.length;k++) if(m[k].id===id){ i=k; break; }
    S.me=i<0?null:m[i]; S.prev=S.next=null;
    if(!S.me) throw new Error('unknown');
    // the chapter before and the next one that have a recording, with or without pictures
    for(k=i-1;k>=0;k--) if(m[k].audio){ S.prev=m[k]; break; }
    for(k=i+1;k<m.length;k++) if(m[k].audio){ S.next=m[k]; break; }
    el.tag.innerHTML=esc(name(S.me)); el.ptitle.textContent=name(S.me); el.pverse.textContent=''; icons();
    if(!S.me.audio) throw new Error('noaudio');
    return bundle(S.me);
  }).then(function(b){ if(mine===S.serial) setup(b,o,mine); })
  .catch(function(e){ if(mine===S.serial) fail(e&&e.message); });
}
function setup(b,o,mine){
  var text=b.text,m,last=0,c=S.me;
  S.words=[]; S.seps=[]; WORD.lastIndex=0;
  while((m=WORD.exec(text))){ S.seps.push(text.slice(last,m.index)); S.words.push(m[0]); last=m.index+m[0].length; }
  // a scene with no picture (a surah whose later parts are not pictured yet) shows the quiet background there
  S.scenes=(b.tv.scenes||[]).map(function(s){ return {w:s.w,img:s.img?ROOT+s.img:''}; }); S.verses=b.tv.verses||[];
  S.rtl=c.lang==='ar'; S.modern=S.rtl&&c.script==='modern'; S.brk={};
  (b.tv.breaks||[]).forEach(function(k){ S.brk[k]=1; });   // the modern words a pause sign follows (it is not shown)
  stage.classList.toggle('tv-noimg',!S.scenes.length||!S.scenes[0].img); stage.classList.toggle('tv-rtl',S.rtl); stage.classList.toggle('tv-modern',S.modern);
  if(!S.scenes.length){ layers[0].classList.remove('tv-on'); layers[1].classList.remove('tv-on'); }
  function go(){
    audio.removeEventListener('loadedmetadata',go); if(mine!==S.serial)return;
    var dur=audio.duration,sync=b.sync;
    S.T=(sync&&sync.t&&sync.t.length===S.words.length)?sync.t.map(function(x){return x/100}):spread(dur);
    makeCards(); S.scenes.forEach(function(s){ s.at=s.w>0?Math.max(0,S.T[s.w]-0.35):0; });
    var h='',k,at=S.scenes.map(function(s){ return s.at; });
    if(!at.length&&b.tv.sections) at=b.tv.sections.map(function(s){ return S.T[s[0]]; });   // no pictures: where each section starts
    for(k=1;k<at.length;k++) if(isFinite(at[k])) h+='<i style="left:'+(at[k]/dur*100).toFixed(2)+'%"></i>'; el.ticks.innerHTML=h;
    var pos=o.t!=null?o.t:(o.auto?0:(get('listenPos',{})[c.id]||0)),back=false;
    if(pos>5&&pos<dur-8){ audio.currentTime=pos; back=o.t==null; } else pos=0;
    S.ready=true; S.ended=false; seek.max=Math.floor(dur); spin(false); icons(); paint(); mark(); posState();
    put('listenAt',c.id); media();
    if(o.play){
      play();
      if(back) toast('Carrying on from '+fmt(pos)+'.','Start from the beginning',function(){ jump(0); });
    }else cover('start',pos);
    // have the next chapter ready, so it follows without a gap
    setTimeout(function(){ if(mine===S.serial&&S.next) bundle(S.next).then(function(n){ if(n.tv.scenes&&n.tv.scenes[0]&&n.tv.scenes[0].img) (new Image()).src=ROOT+n.tv.scenes[0].img; },noop); },5000);
  }
  audio.addEventListener('loadedmetadata',go);
  audio.src=b.src; audio.defaultPlaybackRate=rate(); audio.playbackRate=rate(); audio.load();
}
function spread(dur){   // no measured timings: spread the words evenly by their length
  var total=0,run=0,out=[],k; for(k=0;k<S.words.length;k++) total+=S.words[k].length+2;
  for(k=0;k<S.words.length;k++){ out.push(dur*run/total); run+=S.words[k].length+2; } return out;
}
function makeCards(){
  // A card is what is on screen at once: a sentence, or a phrase of a long one. A new picture always starts a new card.
  var words=S.words,seps=S.seps,starts={},cards=[],from=0,len=0,k;
  S.scenes.forEach(function(s){ starts[s.w]=1; }); S.verses.forEach(function(v){ if(!starts[v[1]]) starts[v[1]]=2; });
  function cut(to){ if(to>from){ cards.push({a:from,b:to}); from=to; len=0; } }
  if(S.rtl){
    // Arabic: a new card at every verse; a long verse is cut after a pause mark, or else after about a line
    for(k=0;k<words.length;k++){
      if(starts[k]) cut(k);
      len+=words[k].length+1;
      if((len>=46&&(/[\u06d6-\u06dc]$/.test(words[k])||S.brk[k]))||len>=110) cut(k+1);
    }
    cut(words.length);
    S.cards=cards; return;
  }
  for(k=0;k<words.length;k++){
    if(starts[k]===1) cut(k);
    else if(starts[k]===2&&len>=34) cut(k);
    var w=words[k],dash=/[—–]/.test(seps[k+1]||''); len+=w.length+1;
    if(/[.?!]["'”’)]*$/.test(w)) cut(k+1);
    else if(len>=40&&(/[,;:]["'”’)]*$/.test(w)||dash)) cut(k+1);
    else if(len>=84) cut(k+1);
  }
  cut(words.length);
  // a card of one or two words joins the one before it, unless a picture starts there
  for(k=cards.length-1;k>0;k--){ var c=cards[k],p=cards[k-1];
    if(c.b-c.a<3&&starts[c.a]!==1&&textOf(p.a,c.b).length<=96){ p.b=c.b; cards.splice(k,1); } }
  S.cards=cards;
}
function textOf(a,b){ var s='',k; for(k=a;k<b;k++) s+=(k>a?S.seps[k]:'')+S.words[k]; return s; }

/* ---- drawing ---- */
function find(arr,t,key){ var lo=0,hi=arr.length-1,k=-1; while(lo<=hi){ var mid=(lo+hi)>>1,v=key==null?arr[mid]:arr[mid][key]; if(v<=t){k=mid;lo=mid+1}else hi=mid-1 } return k; }
function preload(i){ var s=S.scenes[i]; if(s&&s.img&&!s.pre){ s.pre=new Image(); s.pre.src=s.img; } }
function show(i){
  if(i===S.scene||!S.scenes[i])return; S.scene=i; preload(i+1);
  var s=S.scenes[i],lay=layers[S.top^1],img=lay.firstChild,end=S.scenes[i+1]?S.scenes[i+1].at:audio.duration,mine=S.serial;
  if(!s.img){ stage.classList.add('tv-noimg'); layers[0].classList.remove('tv-on'); layers[1].classList.remove('tv-on'); return; }
  function up(){
    if(S.scene!==i||mine!==S.serial)return;
    stage.classList.remove('tv-noimg');
    img.style.animationName='none'; void img.offsetWidth;
    img.style.animationDuration=Math.max(8,(end-s.at)/audio.playbackRate+3)+'s'; img.style.animationName='tvkb'+(i%4);
    lay.classList.add('tv-on'); layers[S.top].classList.remove('tv-on'); S.top^=1;
  }
  img.onload=img.onerror=null; img.src=s.img;
  if(img.decode) img.decode().then(up,function(){ if(img.complete&&img.naturalWidth) up(); });   // a picture that will not load: the one before it stays
  else if(img.complete) up(); else img.onload=up;
}
function card(i){
  if(i===S.card)return; S.card=i; S.word=-1;
  if(i<0){ cap.classList.add('tv-out'); return; }
  var c=S.cards[i],h='',k;
  for(k=c.a;k<c.b;k++){
    // only the words: the verse is named in the top-left corner (Obay, 2026-11-23)
    h+=(k>c.a?esc(S.seps[k]):'')+'<span class="tv-w">'+esc(S.words[k])+'</span>';
  }
  if(c.b<S.words.length&&/[—–]/.test(S.seps[c.b])) h+='—';
  capIn.innerHTML=h; cap.classList.remove('tv-out'); fit();
}
function fit(){
  // the dark box hugs the lines of words: as wide as the longest line, as tall as the lines, and no bigger
  if(!capBox)return;
  var r=d.createRange(),rs,c=cap.getBoundingClientRect(),l=1e9,t=1e9,rt=-1e9,b=-1e9,k,f=parseFloat(win.getComputedStyle(cap).fontSize)||16;
  r.selectNodeContents(capIn); rs=r.getClientRects();
  for(k=0;k<rs.length;k++){ if(!rs[k].width)continue; l=Math.min(l,rs[k].left); rt=Math.max(rt,rs[k].right); t=Math.min(t,rs[k].top); b=Math.max(b,rs[k].bottom); }
  var bs=capBox.style; if(rt<l){ bs.width=bs.height='0'; return; }
  bs.left=(l-c.left-.6*f)+'px'; bs.top=(t-c.top-.22*f)+'px'; bs.width=(rt-l+1.2*f)+'px'; bs.height=(b-t+.52*f)+'px';
}
function mark(){
  if(!S.ready)return;
  var t=S.drag?parseFloat(seek.value):audio.currentTime,T=S.T,cards=S.cards,k;
  if(S.scenes.length){ var s=find(S.scenes,t,'at'); show(s<0?0:s); }
  var w=find(T,t+LEAD),ci=0;
  if(w>=0){
    for(ci=Math.max(S.card,0);ci<cards.length;ci++) if(w<cards[ci].b)break;
    if(ci>=cards.length||w<cards[ci].a){ for(ci=0;ci<cards.length-1;ci++) if(w<cards[ci].b)break; }
  }
  // bring the next card up just before its first word, so the eye is ready for it
  if(cards[ci+1]&&T[cards[ci+1].a]-t<0.18) ci++;
  if(!cards.length)return;
  card(ci);
  if(w!==S.word){ var sp=capIn.querySelectorAll('.tv-w'),a=cards[ci].a; for(k=0;k<sp.length;k++) sp[k].className=a+k<=w?'tv-w tv-on':'tv-w'; S.word=w; }
  var v=find(S.verses,w<0?0:w,1);
  if(v!==S.verse){ S.verse=v; el.tag.innerHTML=esc(name(S.me))+(v>=0?'<span>verse '+S.verses[v][0]+'</span>':''); el.pverse.textContent=v>=0&&S.verses[v][0]>0?'verse '+S.verses[v][0]:''; }
}
function paint(){
  var dur=isFinite(audio.duration)?audio.duration:0,t=S.drag?parseFloat(seek.value):(audio.currentTime||0);
  if(!S.drag) seek.value=t;
  seek.style.setProperty('--p',(dur?Math.min(100,t/dur*100):0)+'%');
  el.cur.textContent=fmt(t); el.rem.textContent='-'+fmt((dur-t)/(audio.playbackRate||1));
}
function loop(){ if(raf)return; raf=requestAnimationFrame(function step(){ raf=0; if(!S.open)return; mark(); if(!audio.paused) raf=requestAnimationFrame(step); }); }

/* ---- playing ---- */
function play(){
  if(!S.ready)return; S.ended=false; cover(null); audio.playbackRate=rate();
  var p=audio.play();
  if(p&&p.then) p.then(function(){
    if(!S.hinted&&!fsEl()&&win.matchMedia&&win.matchMedia('(orientation:portrait)').matches&&coarse()&&!el.toast.classList.contains('tv-on')){
      S.hinted=true; toast('Turn your phone sideways for the full picture.',null,null,5000); }
  },function(){ if(S.ready&&audio.paused) cover('start',audio.currentTime); });   // the browser wants a tap first
}
function toggle(){ if(!S.ready)return; if(audio.paused) play(); else audio.pause(); }
function jump(t){ if(!S.ready)return; audio.currentTime=Math.max(0,Math.min(audio.duration-0.2,t)); paint(); mark(); posState(); savePos(true); }
function nudge(by,flash){
  if(!S.ready)return; jump(audio.currentTime+by);
  if(flash){ var n=by<0?el.nl:el.nr; n.classList.add('tv-on'); clearTimeout(nudgeT); nudgeT=setTimeout(function(){ el.nl.classList.remove('tv-on'); el.nr.classList.remove('tv-on'); },450); }
}
function ended(){
  if(!S.ready)return; S.ended=true;
  var done=get('listenDone',{}),pos=get('listenPos',{}); done[S.me.id]=1; delete pos[S.me.id]; put('listenDone',done); put('listenPos',pos);
  if(S.next){ load(S.next.id,{play:true,auto:true}); return; }
  awake(false); cover('end');
}
function savePos(force){
  if(!S.ready||!S.me)return; var now=Date.now(); if(!force&&now-S.saved<4000)return; S.saved=now;
  var pos=get('listenPos',{}),id=S.me.id,t=audio.currentTime;
  if(t>3&&(!audio.duration||t<audio.duration-3)) pos[id]=Math.floor(t); else delete pos[id];
  put('listenPos',pos);
  // the one place the site reopens to (see scripts/read.js), and the Watch page's "Keep watching"
  var spot={mode:'tv',id:id,url:S.me.url,label:name(S.me),t:pos[id]||0,at:now};
  put('lastSpot',spot); put('tvLast',spot);
}
function awake(on){
  if(!('wakeLock' in navigator))return;
  if(on){ if(!wake&&!d.hidden) navigator.wakeLock.request('screen').then(function(w){ wake=w; w.addEventListener('release',function(){ if(wake===w) wake=null; }); if(!S.open||audio.paused) w.release(); }).catch(noop); }
  else if(wake){ var w=wake; wake=null; w.release().catch(noop); }
}
function posState(){
  if(!S.ready||!('mediaSession' in navigator)||!navigator.mediaSession.setPositionState||!isFinite(audio.duration))return;
  try{ navigator.mediaSession.setPositionState({duration:audio.duration,playbackRate:audio.playbackRate,position:Math.min(audio.currentTime,audio.duration)}); }catch(e){}
}
function media(){
  if(!('mediaSession' in navigator))return;
  try{ navigator.mediaSession.metadata=new MediaMetadata({title:name(S.me),artist:SITE,album:'Watch',
    artwork:S.me.poster?[{src:ROOT+S.me.poster,sizes:'640x362',type:'image/jpeg'}]:[]}); }catch(e){}
}
function hooks(on){
  // The lock screen's buttons. Listen + Read sets its own again whenever it starts.
  if(!('mediaSession' in navigator))return;
  var set=function(a,f){ try{ navigator.mediaSession.setActionHandler(a,on?f:null); }catch(e){} };
  set('play',play); set('pause',function(){ audio.pause(); });
  set('seekbackward',function(){ nudge(-10); }); set('seekforward',function(){ nudge(10); });
  set('seekto',function(x){ if(x&&isFinite(x.seekTime)) jump(x.seekTime); });
  set('previoustrack',function(){ if(S.prev) load(S.prev.id,{play:true,t:0}); });
  set('nexttrack',function(){ if(S.next) load(S.next.id,{play:true,t:0}); });
}

/* ---- full screen ---- */
function fsEl(){ return d.fullscreenElement||d.webkitFullscreenElement||null; }
function goFull(){
  var req=stage.requestFullscreen||stage.webkitRequestFullscreen; if(!req||fsEl())return;
  function turn(){ try{ var o=screen.orientation; if(o&&o.lock) o.lock('landscape').catch(noop); }catch(e){} }   // the pictures are wide
  try{ var p=req.call(stage,{navigationUI:'hide'}); if(p&&p.then) p.then(turn,noop); else turn(); }catch(e){}
}
function leaveFull(){ var x=d.exitFullscreen||d.webkitExitFullscreen; if(x&&fsEl()){ try{ var p=x.call(d); if(p&&p.catch) p.catch(noop); }catch(e){} } }
function fsChange(){
  if(!stage)return; var on=!!fsEl(),mine=S.leaving; S.leaving=false; icons();
  // On a phone, the back gesture leaves full screen; that is taken as leaving Watch, back to the page.
  if(!on&&S.open&&!mine&&coarse()) setTimeout(function(){ if(S.open&&!d.hidden&&!fsEl()) close(); },350);
}

/* ---- keys: a keyboard, or a TV remote's arrows and OK ---- */
function controls(){ return [el.close,el.back,el.play,el.fwd,seek,el.prev,el.next,el.rate,el.words,el.full].filter(function(b){ return !b.disabled; }); }
function key(e){
  if(!S.open||e.altKey||e.ctrlKey||e.metaKey)return;
  var k=e.key,c=e.keyCode,t=e.target,on=t&&t!==stage&&stage.contains(t),isSeek=t===seek,used=true,list,i;
  if(k==='Tab'){ poke(); return; }
  if(S.cover){   // the opening and closing card: only its own buttons
    if(k==='Escape'||k==='Esc'||c===461||c===10009) close();
    else if(/^Arrow|^(Left|Right|Up|Down)$/.test(k)){ list=[el.go,el.again,el.all,el.leave].filter(function(b){ return !b.hidden; }); i=list.indexOf(t);
      i=i<0?0:(i+(/Left|Up/.test(k)?-1:1)+list.length)%list.length; list[i].focus(); }
    else if((k==='Enter'||k===' ')&&!on&&!el.go.hidden) el.go.click();
    else used=false;
    if(used){ e.preventDefault(); e.stopPropagation(); }
    return;
  }
  if(k==='Escape'||k==='Esc'||c===461||c===10009){ if(on&&S.ui&&!audio.paused){ focusStage(); ui(false); e.preventDefault(); e.stopPropagation(); return; } if(fsEl()){ S.leaving=true; leaveFull(); } else close(); }
  else if(k===' '||k==='Spacebar'||k==='Enter'){ if(on&&!isSeek) used=false; else toggle(); }
  else if(k==='k'||k==='K'||k==='MediaPlayPause'||c===179) toggle();
  else if(k==='MediaPlay'||c===415) play();
  else if(k==='MediaPause'||k==='MediaStop'||c===19||c===413) audio.pause();
  else if(k==='MediaFastForward'||c===417) nudge(10);
  else if(k==='MediaRewind'||c===412) nudge(-10);
  else if(k==='MediaTrackNext'||k==='n'||k==='N'){ if(S.next) el.next.click(); }
  else if(k==='MediaTrackPrevious'||k==='p'||k==='P'){ if(S.prev) el.prev.click(); }
  else if(k==='ArrowLeft'||k==='Left'||k==='ArrowRight'||k==='Right'){
    var fwd=k==='ArrowRight'||k==='Right';
    if(on&&!isSeek&&S.ui){ list=controls(); i=list.indexOf(t); list[(i+(fwd?1:-1)+list.length)%list.length].focus(); }   // along the controls
    else nudge(fwd?10:-10,!S.ui);
  }
  else if(k==='ArrowUp'||k==='Up'||k==='ArrowDown'||k==='Down'){
    // up and down step between the picture, the middle buttons, the bar and the close button
    var down=k==='ArrowDown'||k==='Down',mid=t===el.back||t===el.play||t===el.fwd,bar=on&&!mid&&t!==el.close&&!isSeek,shown=S.ui;
    poke();   // the controls have to be up before one of them can take the focus
    if(!on||!shown) el.play.focus();
    else if(t===el.close) (down?el.play:seek).focus();
    else if(mid) (down?seek:el.close).focus();
    else if(isSeek) (down?el.rate:el.play).focus();
    else if(bar) (down?el.close:seek).focus();
  }
  else if(k==='f'||k==='F') el.full.click();
  else if(k==='c'||k==='C') el.words.click();
  else if(k==='0'||k==='Home') jump(0);
  else used=false;
  if(used){ e.preventDefault(); e.stopPropagation(); }
  poke();
}

/* ---- opening and closing ---- */
function open(id,o){
  o=o||{}; build();
  if(!S.open){
    S.open=true; S.opener=o.opener||null; stage.hidden=false; d.documentElement.classList.add('tv-open');
    // Listen + Read hands over: it stops and keeps its place, and Watch carries on from that same second
    var lr=d.getElementById('lr-close'); if(lr&&d.body.classList.contains('lr')) lr.click();
    if('CloseWatcher' in win){ try{ cw=new win.CloseWatcher(); cw.onclose=function(){ cw=null; close(); }; }catch(e){ cw=null; } }
    hooks(true); focusStage();
  }
  if(o.gesture){
    // inside the tap itself: a silent start, so the browser lets the voice begin once it has loaded, then the
    // full screen (in that order: asking for the full screen uses up the tap)
    try{ audio.src=SILENT; var p=audio.play(); if(p&&p.catch) p.catch(noop); }catch(e){}
    goFull();
  }
  load(id,{play:!!o.gesture});
}
function close(){
  if(!S.open)return;
  var c=S.me,v=S.verse>=0&&S.verses[S.verse]?S.verses[S.verse][0]:1,done=S.ended;
  savePos(true); S.open=false; S.serial++; S.ready=false;
  try{ audio.pause(); audio.removeAttribute('src'); audio.load(); }catch(e){}
  awake(false); hooks(false); clearTimeout(idleT); toast(null); leaveFull();
  if(cw){ try{ cw.destroy(); }catch(e){} cw=null; }
  stage.hidden=true; stage.className='tv-paused'; d.documentElement.classList.remove('tv-open');
  layers[0].classList.remove('tv-on'); layers[1].classList.remove('tv-on');
  var ch=d.getElementById('ch');
  if(ch&&c){
    // back in the text at the verse the voice had reached
    if(ch.getAttribute('data-id')!==c.id){ location.href=ROOT+c.url+(v>1&&!done?'#v'+v:''); return; }
    var s=!done&&v>1&&d.getElementById('v'+v),top=0,t=d.querySelector('.top'),sb=d.getElementById('secbar');
    if(t&&getComputedStyle(t).position==='sticky') top+=t.offsetHeight;   // the Quran site's bars that stay at the top
    if(sb) top+=sb.offsetHeight;
    if(s) win.scrollTo(0,s.getBoundingClientRect().top+win.pageYOffset-Math.max(64,top+16));
  }
  if(home()){ resume(); if(/[?&]c=/.test(location.search)){ try{ history.replaceState(null,'',location.pathname); }catch(e){} } }
  if(S.opener&&S.opener.focus&&d.body.contains(S.opener)){ try{ S.opener.focus({preventScroll:true}); }catch(e){} }
}

/* ---- the pages ---- */
function resume(){   // the Watch page's "Keep watching"
  var a=d.getElementById('tv-resume'),s=get('tvLast',null); if(!a||!s||!s.id)return;
  var t=get('listenPos',{})[s.id]||0;
  a.href='?c='+encodeURIComponent(s.id); a.setAttribute('data-tv',s.id);
  a.querySelector('b').textContent=s.label+(t>3?' · at '+fmt(t):''); a.hidden=false;
}
d.addEventListener('click',function(e){
  if(e.defaultPrevented||e.button||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||!e.target.closest)return;
  var a=e.target.closest('[data-tv]'); if(!a||(stage&&stage.contains(a)))return;
  e.preventDefault(); open(a.getAttribute('data-tv'),{gesture:true,opener:a});
});
win.TVMode={open:open,close:close};
resume();
var asked=home()&&/[?&]c=([^&#]+)/.exec(location.search);
if(asked) open(decodeURIComponent(asked[1]),{});   // a link straight to a chapter: its opening card, one tap from playing
})();
