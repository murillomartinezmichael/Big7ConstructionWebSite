'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../site/big7.js'),'utf8');
function run(search='', options={}) {
  const radios=['commercial-new','trades-only','tenant-improvement'].map(value=>({value,checked:value===options.selected}));
  const message={value:options.message||'',dispatchEvent(){}};
  const source={value:'commercial-industrial-page'};
  const reply={value:''};
  const email={addEventListener(){}};
  const form={addEventListener(){},querySelector(q){
    if(q==='input[name="projectType"]:checked')return radios.find(r=>r.checked)||null;
    const m=q.match(/^input\[name="projectType"\]\[value="([^"]+)"\]$/);if(m)return radios.find(r=>r.value===m[1])||null;
    if(q==='textarea[name="message"]')return message;
    if(q==='input[name="source"]')return source;
    if(q==='[name="email"]')return email;
    if(q==='[name="_replyto"]')return reply;
    return null;
  }};
  const document={addEventListener(){},querySelector(q){
    if(q==='form.cform')return options.noForm?null:form;
    return null;
  }};
  const window={location:{pathname:options.pathname||'/commercial-industrial',search},dataLayer:[]};
  const ctx={window,document,URLSearchParams,WeakMap,Event:class{},setTimeout,clearTimeout};
  vm.createContext(ctx);vm.runInContext(code,ctx);
  return {radios,message,source,window,page:ctx.BIG7_PAGE,events:window.dataLayer};
}

test('safe framing intent maps to the existing commercial-new value',()=>{
 const r=run('?intent=service:enterprise-framing&src=example');assert.equal(r.radios.find(x=>x.checked).value,'commercial-new');assert.equal(r.source.value,'example');assert.match(r.message.value,/Interested in: Enterprise Framing/);
});
test('new drywall intent keeps the existing trades-only backend value',()=>{
 const r=run('?intent=service:drywall');assert.equal(r.radios.find(x=>x.checked).value,'trades-only');
});
test('explicit type takes precedence over intent',()=>{
 const r=run('?intent=service:enterprise-framing&type=trades-only');assert.equal(r.radios.find(x=>x.checked).value,'trades-only');
});
test('typed message and already-selected service are not overwritten',()=>{
 const r=run('?intent=service:enterprise-framing',{message:'Keep typed details',selected:'trades-only'});assert.equal(r.message.value,'Keep typed details');assert.equal(r.radios.find(x=>x.checked).value,'trades-only');
});
test('utm_source accepted when explicit src absent',()=>{
 const r=run('?utm_source=example-campaign');assert.equal(r.source.value,'example-campaign');
});
test('explicit src is more specific than utm_source',()=>{
 const r=run('?src=example-a&utm_source=example-b');assert.equal(r.source.value,'example-a');
});
test('selector and markup payloads are rejected before DOM access',()=>{
 const r=run('?intent=%22%5D%3Balert(1)&type=%3Cscript%3E&src=alice%40example.test');assert.equal(r.events.length,0);assert.equal(r.radios.some(x=>x.checked),false);assert.equal(r.source.value,'commercial-industrial-page');
});
test('overlong attribution values are rejected',()=>{
 const r=run('?src='+'a'.repeat(65));assert.equal(r.events.length,0);
});
test('unknown but safe service does not select an unrelated radio',()=>{
 const r=run('?type=not-a-supported-service');assert.equal(r.radios.some(x=>x.checked),false);assert.equal(r.events[0].did_radio,false);
});
test('missing form does not break the page',()=>{
 const r=run('?intent=service:drywall&src=example',{noForm:true});assert.equal(r.events[0].did_radio,false);assert.equal(r.events[0].did_text,false);assert.equal(r.events[0].did_source,false);
});
test('landing event retains the agreed attribution keys, never contact fields',()=>{
 const r=run('?intent=service:drywall&src=example');assert.deepEqual(Object.keys(r.events[0]).sort(),['event','intent','type','src','page','did_radio','did_text','did_source'].sort());
});
test('legacy and clean paths keep a common analytics page key',()=>{
 for(const pathname of ['/commercial-industrial','/commercial-industrial.html','/commercial-industrial/'])assert.equal(run('',{pathname}).page,'commercial-industrial');
 for(const pathname of ['/','/index.html'])assert.equal(run('',{pathname}).page,'home');
});
