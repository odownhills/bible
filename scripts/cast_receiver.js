/* The TV's side of casting (site/cast/, built by scripts/build.py): the page a Chromecast or Google TV opens when
   Watch is cast to it from a phone or a computer. Google's Cast framework plays each recording in this page's own
   audio element and takes the play, pause, seek and next commands from the phone; scripts/tv.js, the same player
   as Watch, shows the pictures and the words lighting up in time with it (window.TV_CAST_RECEIVER).

   What is playing comes with its own details (scripts/tv.js castLoad()): {id, root, script}. root is the site it
   belongs to, the Bible's or the Quran's; anything else is refused. This page lives on the Bible site, so the
   Quran site lets it read its files (its _headers, scripts/search.py).

   It needs the app registered in Google's Cast console with this page's address, and that app's id in
   scripts/tv.js (CAST_APP). Opened in an ordinary browser with ?c=<id> (and &root=...), it plays that chapter on
   its own, for checking how it looks. */
(function(){
'use strict';
var SITES=['https://bible.odownhills.workers.dev/','https://quran.odownhills.workers.dev/'];
var here=new URL('../',location.href).href;   // this site's own root (the Bible's, or a preview)
if(SITES.indexOf(here)<0) SITES.push(here);
var audio=document.getElementById('cast-audio'),splash=document.getElementById('splash'),last='';

function show(id,root,script){
  if(!id)return;
  if(SITES.indexOf(root)<0) root=here;
  var key=id+'|'+root+'|'+(script||'');
  if(key===last)return;
  last=key;
  if(splash) splash.hidden=true;
  window.TVMode.receive(id,root,script||null);
}

var framework=window.cast&&window.cast.framework;
if(!framework){
  // not on a Cast device: play a chapter by itself, to see how the TV shows it
  var q=new URLSearchParams(location.search),id=q.get('c');
  if(id){
    var root=q.get('root')||here;
    fetch(root+(/^ar-/.test(id)?'manifest-ar.json':/^en-/.test(id)?'manifest-en.json':'manifest.json'))
      .then(function(r){ return r.json(); }).then(function(m){
        var c=m.filter(function(x){ return x.id===id; })[0]; if(!c||!c.audio)return;
        audio.src=root+c.audio; if(q.get('t')) audio.currentTime=parseFloat(q.get('t'));
        audio.muted=q.has('mute'); var p=audio.play(); if(p&&p.catch) p.catch(function(){});
        show(id,root,c.script);
      });
  }
  return;
}

var ctx=framework.CastReceiverContext.getInstance(),pm=ctx.getPlayerManager(),E=framework.events.EventType;
function sync(){
  var mi=null; try{ mi=pm.getMediaInformation(); }catch(e){}
  if(!mi)return;
  var cd=mi.customData,m;
  if(cd&&cd.id){ show(cd.id,cd.root,cd.script); return; }
  // no details came with it: the recording's own address says which it is (audio/<book>/<n>.mp3)
  m=/^(https:\/\/[^\/]+\/)audio\/([a-z0-9\-]+)\/(\d+)\.mp3$/.exec(mi.contentUrl||mi.contentId||'');
  if(m) show(m[2]+'-'+m[3],m[1],null);
}
try{ if(pm.setMediaElement) pm.setMediaElement(audio); }catch(e){}
[E.PLAYER_LOAD_COMPLETE,E.LOAD_START,E.PLAYING].forEach(function(t){ if(t) pm.addEventListener(t,sync); });
setInterval(sync,800);   // and in case an event is missed

var o=new framework.CastReceiverOptions();
o.mediaElement=audio;
var Cmd=framework.messages&&framework.messages.Command;
if(Cmd) o.supportedCommands=Cmd.ALL_BASIC_MEDIA|Cmd.QUEUE_NEXT|Cmd.QUEUE_PREV;
ctx.start(o);
})();
