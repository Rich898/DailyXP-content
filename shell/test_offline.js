"use strict";
const fs = require("fs");
const { JSDOM } = require("jsdom");
const html = fs.readFileSync(__dirname + "/roshan/index.html", "utf8");
const TESTQUIZ = JSON.parse(fs.readFileSync(__dirname + "/y9.json", "utf8"));
let webhookUp = false, deliveries = 0;
const dom = new JSDOM(html, { url:"https://dailyxp-roshan.netlify.test/", runScripts:"dangerously", pretendToBeVisual:true,
  beforeParse(window){
    window.fetch = function(url, opts){
      url = String(url);
      if(url.indexOf("raw.githubusercontent.com")!==-1) return Promise.resolve({ok:true, json:()=>Promise.resolve(TESTQUIZ)});
      if(url.indexOf("script.google.com")!==-1){
        if(!webhookUp) return Promise.reject(new Error("offline"));
        deliveries++; return Promise.resolve({ok:true, json:()=>Promise.resolve({ok:true})});
      }
      return Promise.reject(new Error("unexpected "+url));
    };
  }});
const { window } = dom; const { document } = window;
const sleep = (ms)=>new Promise(r=>setTimeout(r,ms));
const btns = ()=>Array.from(document.querySelectorAll("button"));
const click = (t)=>{const b=btns().find(x=>x.textContent.indexOf(t)!==-1&&!x.disabled); if(!b) throw new Error("no btn "+t); b.dispatchEvent(new window.MouseEvent("click",{bubbles:true}));};
const opt = (v)=>{const b=btns().find(x=>x.classList.contains("opt")&&x.getAttribute("data-v")===v&&!x.disabled); b.dispatchEvent(new window.MouseEvent("click",{bubbles:true}));};
let ok=true; const check=(n,c,d)=>{ console.log((c?"  PASS  ":"  FAIL  ")+n+(d?"  ["+d+"]":"")); if(!c) ok=false; };
(async()=>{
  await sleep(80); click("Drop in"); await sleep(30);
  opt("56"); await sleep(1100);
  opt("Mercury"); await sleep(1100);
  opt("Experience Points"); await sleep(50); click("Sure"); await sleep(50); click("Lock it in"); await sleep(50); click("Next"); await sleep(30);
  const tb=document.getElementById("tb"); tb.value="x".repeat(90); tb.dispatchEvent(new window.Event("input",{bubbles:true})); await sleep(30); click("Send it"); await sleep(200);
  const stat=document.getElementById("sendStat");
  check("offline: kid told it's saved on phone", stat.textContent.indexOf("Saved on this phone")!==-1, stat.textContent.slice(0,40));
  const box=JSON.parse(window.localStorage.getItem("dxp_outbox_y9")||"[]");
  check("offline: payload queued in outbox", box.length===1 && box[0].student==="y9");
  webhookUp = true;               // internet comes back…
  window.flushOutbox();           // …and this is what boot() calls on next open
  await sleep(150);
  const box2=JSON.parse(window.localStorage.getItem("dxp_outbox_y9")||"[]");
  check("next open: outbox flushed to Sheet", deliveries===1 && box2.length===0, "deliveries="+deliveries);
  console.log(ok?"OFFLINE PATH: ALL CHECKS PASS":"OFFLINE FAILURES"); process.exit(ok?0:1);
})().catch(e=>{console.error("CRASH",e.message);process.exit(1);});
