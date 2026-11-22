/* The English | Arabic switch at the top of every page of the Quran site (scripts/quran_ar.py).
   It lands on the same verse in the other language: the verse at the top of the screen, or the verse
   being read aloud when Listen + Read is on. The English translation comes in parts, so from an Arabic
   surah it goes to the part that holds that verse, and says so when that verse is not translated yet.
   The choice is remembered in this browser (quranLang): opening the site's address from outside with no
   place to go back to then opens the Arabic pages. */
(function(){
'use strict';
var d=document;
function get(k,v){try{var x=localStorage.getItem(k);return x==null?v:JSON.parse(x)}catch(e){return v}}
function put(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function verseHere(){
  var ch=d.getElementById('ch'); if(!ch)return 0;
  var now=ch.querySelector('.w.now');
  var vs=ch.querySelectorAll('sup.n[id^="v"]'),k;
  if(!vs.length)return 0;
  var v=parseInt(vs[0].id.slice(1),10)||0;   // the page's first verse, until one has scrolled past the top
  if(now){   // Listen + Read: the verse of the word being read
    for(k=0;k<vs.length;k++){ if(vs[k].compareDocumentPosition(now)&4) v=parseInt(vs[k].id.slice(1),10)||v; else break; }
    return v;
  }
  for(k=0;k<vs.length;k++){ if(vs[k].getBoundingClientRect().top<=96) v=parseInt(vs[k].id.slice(1),10)||v; else break; }
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
  // Arabic to English: the part of the translation that holds this verse
  var parts=(a.getAttribute('data-parts')||'').split(',').filter(Boolean),n=a.getAttribute('data-surah');
  for(var k=0;k<parts.length;k++){
    var r=parts[k].split('-'),lo=+r[0],hi=+r[1];
    if(v>=lo&&v<=hi){ location.href='../quran-'+n+'/'+(k+1)+'.html'+(v>lo?'#v'+v:''); return; }
  }
  put('quranLang','ar');
  if(!parts.length) note('Surah '+n+' is not translated into English yet.');
  else note('Verse '+v+' of surah '+n+' is not translated into English yet. The translation reaches verse '+parts[parts.length-1].split('-')[1]+' so far.');
});
// The English home page, opened from outside with nowhere to go back to: open the Arabic pages if they were chosen last.
if(d.getElementById('resume')&&!/\/ar\//.test(location.pathname)&&get('quranLang','en')==='ar'&&!get('lastSpot',null)
   &&!/[?&]home/.test(location.search)&&!(d.referrer&&d.referrer.indexOf(location.origin)===0)) location.replace('ar/');
})();
