/* Search across the three sites: the Bible, the Quran and the study notes. How the index is made and laid out:
   scripts/search.py. Everything happens here in the browser; each site's index is plain files, and a search
   downloads only the pieces it needs (one small file per word typed, then the text of the results shown).

   What a search means:
   - a word finds every verse with that word or one of its forms (love: loved, loves, loving); a word the index
     does not know is taken as the start of words (forg: forgive, forgiven, forgiveness)
   - several words find the verses that have all of them; "words in quotes" must stand together, in that order
   - very common words (the, and, of ...) are only used to check a phrase in quotes
   - Arabic searches the Quran's Arabic (every surah), matching the start of a word after any of the small words
     joined to its front (and, so, with, the ...), with or without vowel marks */
(function(){
'use strict';
var d=document,$=function(id){return d.getElementById(id);};
var cfg=JSON.parse($('search-config').textContent);
var input=$('q'),form=$('sf'),scopeEl=$('scope'),stat=$('sstat'),res=$('res'),tips=$('stips');
var STOP=new Set(('a an and are as at be been but by did do for from had has have he her him his i if in into is it its '+
  'me my no not of on or our out said she so that the their them then there they this to up us was we were what when '+
  'which who will with you your all also shall').split(' '));
var PER_GROUP=5,PAGE=25;

// The sites, the one this page belongs to first; its own index is read from here, the others from their addresses.
var sites=cfg.sites.map(function(s){ return {id:s.id,name:s.name,root:s.id===cfg.home?'../':s.base+'/',meta:null,failed:false}; });
sites.sort(function(a,b){ return (b.id===cfg.home)-(a.id===cfg.home); });
var byId={}; sites.forEach(function(s){ byId[s.id]=s; });

var cache=new Map();
function fetchOnce(url,kind,fresh){
  if(!cache.has(url)){
    var p=fetch(url,fresh?{cache:'no-cache'}:{}).then(function(r){ if(!r.ok) throw new Error(r.status+' '+url); return kind==='text'?r.text():r.json(); });
    p.catch(function(){ cache.delete(url); });
    cache.set(url,p);
  }
  return cache.get(url);
}
function loadMeta(s){
  // a site that answers with another site's index (a Worker serving the wrong folder) counts as not reachable
  if(!s.metaP) s.metaP=fetchOnce(s.root+'search/meta.json','json',true).then(function(m){
      if(!m||m.site!==s.id) throw new Error('not this site');
      s.meta=m; s.failed=false; return m; })
    .catch(function(){ s.failed=true; s.metaP=null; return null; });
  return s.metaP;
}

// ---------------------------------------------------------------------------------------------- words
function esc(t){ return String(t).replace(/[&<>"]/g,function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
function normEn(t){ return t.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[\u2019\u02bc]/g,"'").replace(/[\u02be\u02bf]/g,''); }
function tokens(t){
  var out=[],m,re=/[a-z0-9]+(?:'[a-z0-9]+)*/g; t=normEn(t);
  while((m=re.exec(t))){ var w=m[0]; if(/'s$/.test(w)) w=w.slice(0,-2); w=w.replace(/'/g,''); if(w) out.push(w); }
  return out;
}
function normAr(t){
  return t.replace(/[\u064B-\u065F\u0670\u06D6-\u06ED\u0640]/g,'').replace(/[\u0671\u0623\u0625\u0622]/g,'\u0627')
    .replace(/\u0624/g,'\u0648').replace(/[\u0626\u0649]/g,'\u064A').replace(/\u0629/g,'\u0647')
    .replace(/\u0621\u0627/g,'\u0627').replace(/\u0627\u0627/g,'\u0627');
}
var AR=/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/;

/* The query: groups of words. A group is one word, or a phrase whose words must stand together in order. */
function parseQuery(q){
  q=q.replace(/[\u201c\u201d\u201e\u00ab\u00bb]/g,'"').replace(/(^|[\s"])\u064A\u0627\s+(?=[\u0600-\u06FF])/g,'$1\u064A\u0627');
  var groups=[],m,re=/"([^"]*)"?|([^\s"]+)/g;
  while((m=re.exec(q))){
    if(m[1]!==undefined){ var ws=AR.test(m[1])?arWords(m[1]):tokens(m[1]); if(ws.length) groups.push({words:ws,phrase:ws.length>1}); }
    else if(AR.test(m[2])){ var a=arWords(m[2]); if(a.length) groups.push({words:a,phrase:a.length>1}); }
    else { var t=tokens(m[2]); if(t.length) groups.push({words:t,phrase:t.length>1}); }
  }
  return {groups:groups,arabic:AR.test(q)};
}
function arWords(t){
  var ws=normAr(t).split(/\s+/).filter(function(w){ return w.length>0; }),out=[];
  // "O" (ya) is written joined to the word it calls: ya ayyuha is one word in the Quran's Arabic
  ws.forEach(function(w,i){ if(i&&out[out.length-1]==='\u064A\u0627') out[out.length-1]=normAr('\u064A\u0627'+w); else out.push(w); });
  return out;
}

// ---------------------------------------------------------------------------------------------- English
function decode(p,into){
  p.split(';').forEach(function(ch){
    var i=ch.indexOf(':'),k=+ch.slice(0,i),set=into.get(k);
    if(!set){ set=new Set(); into.set(k,set); }
    ch.slice(i+1).split(',').forEach(function(u){ set.add(+u); });
  });
  return into;
}
/* One word in one site's index: its forms there, and where they are ({key: Set of units}). */
function lookup(s,w,exact){
  var m=s.meta,key=w.slice(0,2);
  if(m.w.indexOf(key)<0) return Promise.resolve({forms:[],places:new Map()});
  return fetchOnce(s.root+'search/w/'+key+'.json?h='+m.h,'json').then(function(shard){
    var forms=[];
    if(shard[w]){ var fam=shard[w][0]||w; Object.keys(shard).forEach(function(x){ if((shard[x][0]||x)===fam) forms.push(x); }); }
    else if(!exact&&w.length>=3){ Object.keys(shard).forEach(function(x){ if(x.indexOf(w)===0) forms.push(x); }); }
    return Promise.all(forms.map(function(f){
      var p=shard[f][1];
      return p===1?fetchOnce(s.root+'search/w/_'+f+'.json?h='+m.h,'json'):p;
    })).then(function(lists){
      var places=new Map(); lists.forEach(function(p){ decode(p,places); });
      return {forms:forms,places:places};
    });
  });
}
function intersect(a,b){
  var out=new Map();
  a.forEach(function(set,k){ var o=b.get(k); if(!o)return; var x=new Set(); set.forEach(function(u){ if(o.has(u)) x.add(u); }); if(x.size) out.set(k,x); });
  return out;
}
function union(a,b){ b.forEach(function(set,k){ var o=a.get(k); if(!o){ o=new Set(); a.set(k,o); } set.forEach(function(u){ o.add(u); }); }); return a; }

/* Search one site for an English query: {hits:[[key,unit]], forms:Set, phrases:[[Set per word]]} */
function searchEn(s,Q){
  var words=[];   // every word to look up: {w, exact, group, i}
  var any=Q.groups.some(function(g){ return g.words.some(function(w){ return !STOP.has(w); }); });
  Q.groups.forEach(function(g,gi){ g.words.forEach(function(w,i){
    if(!any||!STOP.has(w)) words.push({w:w,exact:g.phrase,g:gi,i:i});
  }); });
  return Promise.all(words.map(function(x){ return lookup(s,x.w,x.exact); })).then(function(found){
    var forms=new Set(),phraseForms=Q.groups.map(function(g){ return g.words.map(function(w){ return new Set([w]); }); });
    var all=null,fallback=null;
    found.forEach(function(f,k){
      f.forms.forEach(function(x){ forms.add(x); });
      var x=words[k]; phraseForms[x.g][x.i]=new Set(f.forms.length?f.forms:[x.w]);
      all=all===null?new Map(f.places):intersect(all,f.places);
      fallback=union(fallback||new Map(),f.places);
    });
    function list(m){ var h=[]; (m||new Map()).forEach(function(set,k){ set.forEach(function(u){ h.push([k,u]); }); });
      return h.sort(function(a,b){ return a[0]-b[0]||a[1]-b[1]; }); }
    // places with any of the words, used only when no site has a place with all of them (and no phrase is asked)
    var some=words.length>1&&!Q.groups.some(function(g){ return g.phrase; })?list(fallback):[];
    var phrases=Q.groups.map(function(g,i){ return g.phrase?phraseForms[i]:null; }).filter(Boolean);
    return {hits:list(all),some:some,forms:forms,phrases:phrases};
  });
}
function hasPhrase(toks,ph){
  for(var i=0;i+ph.length<=toks.length;i++){
    var ok=true; for(var j=0;j<ph.length&&ok;j++) ok=ph[j].has(toks[i+j]);
    if(ok) return true;
  }
  return false;
}

// ---------------------------------------------------------------------------------------------- text of results
function place(s,key,unit){
  var m=s.meta,kind=m.site,b,c,name,slug,info={};
  if(kind==='quran'){
    var bk=m.b[key]||['Surah '+key,'quran-'+key];
    info.ref='Quran '+key+':'+unit; info.sub=bk[0];
    info.url=s.root+bk[1]+'/#v'+unit; info.file='t/'+key+'.json';
  }else{
    b=Math.floor(key/1000); c=key%1000; name=(m.b[b]||['',''])[0]; slug=(m.b[b]||['',''])[1];
    info.file='t/'+slug+'/'+c+'.json';
    if(kind==='bible'){ info.ref=unit?name+' '+c+':'+unit:name+' '+c+', title'; info.url=s.root+slug+'/'+c+'.html'+(unit?'#v'+unit:''); }
    else { info.ref=name+' '+c; info.url=s.root+slug+'/'+c+'.html'+(unit?'#s'+unit:''); }
  }
  return info;
}
function rowsOf(s,file){
  return fetchOnce(s.root+'search/'+file+'?h='+s.meta.h,'json').then(function(rows){
    if(!rows._at){ var at=new Map(); rows.forEach(function(r){ at.set(r[0],r); }); Object.defineProperty(rows,'_at',{value:at}); }
    return rows._at;
  });
}
/* Mark the words of a verse that the search matched; [alt: ...] and [notes] are styled as on the chapter page. */
function markWords(t,forms){
  var out='',i=0,m,re=/[A-Za-z0-9\u00c0-\u024f\u02bc-\u02bf'\u2019]+/g;
  while((m=re.exec(t))){
    out+=esc(t.slice(i,m.index));
    var w=m[0],n=normEn(w).replace(/'s$/,'').replace(/'/g,'');
    out+=forms.has(n)?'<mark>'+esc(w)+'</mark>':esc(w); i=re.lastIndex;
  }
  return out+esc(t.slice(i));
}
function markVerse(t,forms){
  var out='',i=0,m,re=/\[([^\[\]]+)\]/g;
  while((m=re.exec(t))){
    out+=markWords(t.slice(i,m.index),forms);
    var body=m[1],alt=/^alt:/i.test(body);
    out+='<span class="'+(alt?'alt':'note')+'">['+(alt?'alt: ':'')+markWords(alt?body.replace(/^alt:\s*/i,''):body,forms)+']</span>';
    i=re.lastIndex;
  }
  return out+markWords(t.slice(i),forms);
}
/* A long study section: the words around the first match. */
function excerpt(t,forms,phrases){
  var ws=t.split(/\s+/),first=-1;
  for(var i=0;i<ws.length&&first<0;i++){ var tk=tokens(ws[i]); if(tk.some(function(x){ return forms.has(x); })) first=i; }
  if(ws.length<=60) return markVerse(t,forms);
  var a=Math.max(0,(first<0?0:first)-18),z=Math.min(ws.length,a+50);
  return (a>0?'\u2026 ':'')+markVerse(ws.slice(a,z).join(' '),forms)+(z<ws.length?' \u2026':'');
}

// ---------------------------------------------------------------------------------------------- Arabic
var arData=null;
function loadArabic(s){
  if(!arData) arData=fetchOnce(s.root+'search/ar.txt?h='+(s.meta.ar||s.meta.h),'text').then(function(txt){
    var rows=[];
    txt.split('\n').forEach(function(line){
      if(!line)return;
      var p=line.split('\t'),sv=p[0].split(':');
      rows.push({s:+sv[0],v:+sv[1],i:rows.length,words:p[1].split(' ').map(function(w){ return w.split('|'); })});
    });
    return rows;
  },function(e){ arData=null; throw e; });
  return arData;
}
/* The Arabic of one verse as the pages show it (the verse's place in ar.txt picks its file). */
function arShown(s,i){
  var n=s.meta.arc||300;
  return fetchOnce(s.root+'search/ar/'+Math.floor(i/n)+'.txt?h='+(s.meta.ar||s.meta.h),'text').then(function(t){
    return t.split('\n')[i%n]||'';
  });
}
// small words joined to the front of an Arabic word: and, so, with, like, to, the, O ...
var PRE=['','\u0648','\u0641','\u0628','\u0643','\u0644','\u0627\u0644','\u0644\u0644','\u0648\u0627\u0644','\u0641\u0627\u0644','\u0628\u0627\u0644',
  '\u0643\u0627\u0644','\u0648\u0644\u0644','\u0641\u0644\u0644','\u0648\u0628','\u0648\u0644','\u0641\u0628','\u0641\u0644','\u0648\u0643',
  '\u0633','\u0648\u0633','\u0641\u0633','\u064A\u0627'];
function arQuery(w){
  // the reader may type the article: al-kitab finds kitab anywhere (but Allah stays whole)
  if(w.indexOf('\u0627\u0644')===0&&w.length-2>=3) w=w.slice(2);
  var alt=/\u0647$/.test(w)&&w.length>=3?w.slice(0,-1)+'\u062A':null;   // rahma -> rahmat-uhu
  return {w:w,alt:alt};
}
// endings that can follow a short word: his, her, their, your, our, my ...
var SUF=new Set(['','\u0647','\u0647\u0627','\u0647\u0645','\u0647\u0645\u0627','\u0647\u0646','\u0643','\u0643\u0645','\u0643\u0645\u0627',
  '\u0643\u0646','\u0646\u0627','\u064A','\u0646\u064A']);
function arHit(forms,q){
  for(var i=0;i<forms.length;i++){
    var f=forms[i];
    for(var k=0;k<PRE.length;k++){
      var p=PRE[k]; if(p&&f.indexOf(p)!==0) continue;
      var r=f.slice(p.length);
      // a word of two letters must be the whole word (with an ending at most); a longer one starts the word
      if(q.w.length<=2){ if(r.indexOf(q.w)===0&&SUF.has(r.slice(q.w.length))) return true; }
      else if(r.indexOf(q.w)===0||(q.alt&&r.indexOf(q.alt)===0)) return true;
    }
  }
  return false;
}
function searchAr(Q){
  var s=byId.quran;
  return loadArabic(s).then(function(rows){
    var groups=Q.groups.map(function(g){ return g.words.map(arQuery); });
    var hits=[];
    rows.forEach(function(r){
      var marked=new Set(),ok=groups.every(function(g){
        var found=false;
        for(var i=0;i+g.length<=r.words.length;i++){
          var j=0; while(j<g.length&&arHit(r.words[i+j],g[j])) j++;
          if(j===g.length){ found=true; for(j=0;j<g.length;j++) marked.add(i+j); }
        }
        return found;
      });
      if(ok) hits.push({row:r,marked:marked});
    });
    return hits;
  });
}

// ---------------------------------------------------------------------------------------------- the page
var state={q:'',scope:'all',results:null,shown:{}},run=0;
function setStat(html){ stat.innerHTML=html; }
function plural(n,one,many){ return n+' '+(n===1?one:many); }
function unitName(s,n){ return s.id==='study'?plural(n,'section','sections'):plural(n,'verse','verses'); }

function search(q){
  var my=++run; q=q.trim(); state.q=q;
  var url=location.pathname+(q?'?q='+encodeURIComponent(q)+(state.scope!=='all'?'&in='+state.scope:''):'');
  history.replaceState(null,'',url);
  tips.hidden=!!q;
  if(!q){ res.innerHTML=''; scopeEl.hidden=true; setStat(''); state.results=null; return; }
  var Q=parseQuery(q);
  if(!Q.groups.length){ res.innerHTML=''; scopeEl.hidden=true; setStat('Type a word to search.'); return; }
  setStat('Searching\u2026');
  var work;
  if(Q.arabic){
    work=loadMeta(byId.quran).then(function(m){
      if(!m) return {arabic:true,failed:true};
      return searchAr(Q).then(function(hits){ return {arabic:true,hits:hits}; });
    });
  }else{
    work=Promise.all(sites.map(function(s){
      return loadMeta(s).then(function(m){
        if(!m) return {site:s,failed:true,hits:[],forms:new Set(),phrases:[]};
        return searchEn(s,Q).then(function(r){ r.site=s; return r; },function(){ return {site:s,failed:true,hits:[],forms:new Set(),phrases:[]}; });
      });
    })).then(function(list){
      if(!list.some(function(r){ return r.hits.length; }))   // no place has all the words: show those with any of them
        list.forEach(function(r){ if(r.some&&r.some.length){ r.hits=r.some; r.loose=true; } });
      // a phrase in quotes: keep only the verses where its words stand together, in order
      return Promise.all(list.map(function(r){
        if(!r.phrases.length||!r.hits.length) return r;
        var keep=[];
        return Promise.all(r.hits.map(function(h){
          var p=place(r.site,h[0],h[1]);
          return rowsOf(r.site,p.file).then(function(at){
            var row=at.get(h[1]); if(!row)return;
            var toks=tokens(row[row.length-1].replace(/\[alt:\s*/gi,' '));
            if(r.phrases.every(function(ph){ return hasPhrase(toks,ph); })) keep.push(h);
          },function(){});
        })).then(function(){ keep.sort(function(a,b){ return a[0]-b[0]||a[1]-b[1]; }); r.hits=keep; return r; });
      })).then(function(list){ return {arabic:false,list:list}; });
    });
  }
  work.then(function(R){ if(my!==run)return; state.results=R; state.shown={}; render(); },
    function(){ if(my!==run)return; setStat('Search could not be finished. Check the connection and try again.'); });
}

function render(){
  var R=state.results; res.innerHTML='';
  if(R.arabic) return renderArabic(R);
  var list=R.list,total=0,forms=new Set(),loose=false,failed=[];
  list.forEach(function(r){ total+=r.hits.length; r.forms.forEach(function(f){ forms.add(f); }); if(r.loose) loose=true; if(r.failed) failed.push(r.site.name); });
  if(state.scope!=='all'&&!list.some(function(r){ return r.site.id===state.scope&&r.hits.length; })) state.scope='all';
  // the scope buttons: All, then each site with its count
  scopeEl.innerHTML='';
  scopeEl.appendChild(scopeButton('all','All',total));
  list.forEach(function(r){ scopeEl.appendChild(scopeButton(r.site.id,r.site.name,r.hits.length,r.failed)); });
  scopeEl.hidden=false;
  var typed=new Set(); parseQuery(state.q).groups.forEach(function(g){ g.words.forEach(function(w){ typed.add(w); }); });
  var extra=[...forms].filter(function(f){ return !typed.has(f); }).sort();
  var line=total?plural(total,'result','results')+'.':'Nothing found.';
  if(loose) line='No one place has all of these words, so these have any of them. '+line;
  if(extra.length) line+=' Also matching: <em>'+esc(extra.slice(0,12).join(', '))+(extra.length>12?', \u2026':'')+'</em>';
  if(failed.length) line+=' <br>'+esc(failed.map(function(n){ return n==='Study'?'The study notes':'The '+n; }).join(' and '))+' could not be reached just now.';
  setStat(line);
  list.forEach(function(r){
    if(!r.hits.length||(state.scope!=='all'&&state.scope!==r.site.id))return;
    var sec=d.createElement('section');
    var h=d.createElement('h2'); h.className='grp';
    h.innerHTML=esc(r.site.id==='study'?'Study notes':r.site.name)+'<span>'+esc(unitName(r.site,r.hits.length))+'</span>';
    sec.appendChild(h);
    var box=d.createElement('div'); sec.appendChild(box); res.appendChild(sec);
    showMore(r,box,sec,state.scope==='all'?PER_GROUP:PAGE,forms);
  });
}
function scopeButton(id,name,n,failed){
  var b=d.createElement('button'); b.type='button';
  b.setAttribute('aria-pressed',state.scope===id?'true':'false');
  b.innerHTML=esc(name)+'<b>'+(failed?'\u2013':n)+'</b>';
  b.disabled=!n&&id!=='all';
  b.onclick=function(){ state.scope=id; search(state.q); window.scrollTo(0,0); };
  return b;
}
function showMore(r,box,sec,step,forms){
  var from=box.childElementCount,slice=r.hits.slice(from,from+step);
  var old=sec.querySelector('.smore'); if(old) old.remove();
  Promise.all(slice.map(function(h){
    var p=place(r.site,h[0],h[1]);
    return rowsOf(r.site,p.file).then(function(at){ p.row=at.get(h[1]); return p; },function(){ return p; });
  })).then(function(items){
    items.forEach(function(p){
      var a=d.createElement('a'); a.className='hit'; a.href=p.url;
      // a verse's page marks the words found in it (scripts/read.js); a study section is shown as it is
      if(r.site.id!=='study'&&forms.size&&p.url.indexOf('#v')>0) a.href=p.url.replace('#','?hl='+encodeURIComponent([...forms].join(' '))+'#');
      var label=esc(p.ref);
      if(r.site.id==='study'&&p.row&&p.row[1]) label+=' <small>\u00b7 '+esc(p.row[1])+'</small>';
      if(r.site.id==='quran'&&p.sub) label+=' <small>\u00b7 '+esc(p.sub)+'</small>';
      var text=p.row?p.row[p.row.length-1]:'';
      a.innerHTML='<span class="ref">'+label+'</span><p>'+(r.site.id==='study'?excerpt(text,forms):markVerse(text,forms))+'</p>';
      box.appendChild(a);
    });
    var left=r.hits.length-box.childElementCount;
    if(left>0){
      var b=d.createElement('button'); b.type='button'; b.className='smore';
      if(state.scope==='all'){ b.textContent='See all '+unitName(r.site,r.hits.length)+(r.site.id==='study'?' of the study notes':' in the '+r.site.name);
        b.onclick=function(){ state.scope=r.site.id; search(state.q); window.scrollTo(0,0); }; }
      else { b.textContent='Show '+Math.min(PAGE,left)+' more'; b.onclick=function(){ showMore(r,box,sec,PAGE,forms); }; }
      sec.appendChild(b);
    }
  });
}
function renderArabic(R){
  scopeEl.hidden=true;
  if(R.failed){ setStat('The Quran site could not be reached just now.'); return; }
  setStat(R.hits.length?plural(R.hits.length,'verse','verses')+' in the Quran\u2019s Arabic.':'Nothing found in the Quran\u2019s Arabic.');
  var sec=d.createElement('section'),box=d.createElement('div');
  var h=d.createElement('h2'); h.className='grp'; h.innerHTML='Quran, Arabic<span>'+esc(plural(R.hits.length,'verse','verses'))+'</span>';
  sec.appendChild(h); sec.appendChild(box); res.appendChild(sec);
  moreArabic(R,box,sec);
}
function moreArabic(R,box,sec){
  var s=byId.quran,from=box.childElementCount,slice=R.hits.slice(from,from+PAGE);
  var old=sec.querySelector('.smore'); if(old) old.remove();
  Promise.all(slice.map(function(h){
    var en=s.meta.b[h.row.s]?rowsOf(s,'t/'+h.row.s+'.json').then(function(at){ return at.get(h.row.v); },function(){ return null; }):Promise.resolve(null);
    return Promise.all([en,arShown(s,h.row.i).catch(function(){ return ''; })]).then(function(x){ h.en=x[0]; h.shown=x[1]; return h; });
  })).then(function(items){
    items.forEach(function(h){
      var r=h.row,a=d.createElement('a'); a.className='hit'; a.href=s.root+'ar/'+r.s+'.html#v'+r.v;
      var shown=h.shown.split(' ').map(function(w,i){ return h.marked.has(i)?'<mark>'+esc(w)+'</mark>':esc(w); }).join(' ');
      var bk=s.meta.b[r.s];
      a.innerHTML='<span class="ref">Quran '+r.s+':'+r.v+(bk?' <small>\u00b7 '+esc(bk[0])+'</small>':'')+'</span>'+
        '<p class="ar" lang="ar" dir="rtl">'+shown+'</p>'+(h.en?'<p class="en">'+markVerse(h.en[1],new Set())+'</p>':'');
      box.appendChild(a);
    });
    var left=R.hits.length-box.childElementCount;
    if(left>0){ var b=d.createElement('button'); b.type='button'; b.className='smore'; b.textContent='Show '+Math.min(PAGE,left)+' more';
      b.onclick=function(){ moreArabic(R,box,sec); }; sec.appendChild(b); }
  });
}

var timer=0;
input.addEventListener('input',function(){ clearTimeout(timer); timer=setTimeout(function(){ search(input.value); },280); });
form.addEventListener('submit',function(e){ e.preventDefault(); clearTimeout(timer); search(input.value); input.blur(); });
tips.addEventListener('click',function(e){
  var c=e.target.closest('.chip'); if(!c)return;
  input.value=c.textContent; search(input.value);
});
var params=new URLSearchParams(location.search);
state.scope=params.get('in')||'all';
sites.forEach(loadMeta);   // start fetching the three indexes at once
if(params.get('q')){ input.value=params.get('q'); search(input.value); }
else input.focus();
})();
