'use strict';
let MODEL = null;
const $ = (id) => document.getElementById(id);
const textarea = $('tweet');
const button = $('analyze');
const counter = $('counter');

// The model exports an exact Python Porter stem for every known surface token.
// Unknown words cannot contribute to the score; they are deliberately ignored.
function tokenize(text) {
  // approximate TweetTokenizer for terms in known-word map; keep common emoticons.
  let s = text.replace(/^RT\s+/i, ' ')
    .replace(/https?:\/\/\S+|www\.\S+/gi, ' ')
    .replace(/\$\w+/g, ' ')
    .replace(/@\w+/g, ' ')
    .replace(/#/g, '')
    .toLowerCase()
    .replace(/([^\s])\1{3,}/g, '$1$1$1'); // approximate reduce_len=True
  return s.match(/[:;=8][-^]?[)(dp/\\]|<3|[\p{L}\p{N}_]+(?:['’][\p{L}]+)?/giu) || [];
}
function classify(text, model) {
  const stop = new Set(model.stopwords);
  const raw = tokenize(text).filter(w => !stop.has(w));
  const words = raw.map(w => model.stem_map[w]).filter(Boolean);
  let score = model.logprior;
  const contribution = [];
  for (const stem of words) {
    const delta = model.loglikelihood[stem];
    if (typeof delta === 'number') {
      score += delta;
      contribution.push({stem, delta});
    }
  }
  const probPositive = score >= 0 ? 1/(1+Math.exp(-score)) : Math.exp(score)/(1+Math.exp(score));
  const positive = score > 0;
  return {positive, score, confidence:positive?probPositive:1-probPositive,
    matched:contribution.length, contributions:contribution};
}
function renderResult(r) {
  $('result-empty').classList.add('hidden');
  $('result-ready').classList.remove('hidden');
  const label = $('prediction-class');
  label.textContent = r.positive?'ПОЗИТИВНА ТОНАЛЬНІСТЬ':'НЕГАТИВНА ТОНАЛЬНІСТЬ';
  label.classList.toggle('negative', !r.positive);
  $('confidence').textContent = (r.confidence*100).toFixed(1)+'%';
  $('log-odds').textContent = r.score.toFixed(3);
  $('matched').textContent = String(r.matched);
  $('meter-fill').style.width = (r.confidence*100).toFixed(1)+'%';
  $('meter-fill').classList.toggle('negative', !r.positive);
  const target = $('contribution-tags');
  target.replaceChildren();
  const top = r.contributions.sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta)).slice(0,7);
  if (!top.length) {
    const span=document.createElement('span'); span.textContent='Немає знайомих моделі слів';target.append(span);
  }
  top.forEach(item=>{
    const span=document.createElement('span'); span.className=item.delta>=0?'pos':'neg';
    span.textContent=item.stem+' '+(item.delta>=0?'+':'')+item.delta.toFixed(2);
    target.append(span);
  });
}
function analyze() {
  $('model-error').textContent='';
  if(!MODEL || !MODEL.trained) return;
  const value=textarea.value.trim();
  if(!value) { $('model-error').textContent='Введи текст англійською.';return; }
  const result=classify(value,MODEL);
  renderResult(result);
}
button.addEventListener('click', analyze);
textarea.addEventListener('input',()=>{counter.textContent=textarea.value.length+' / 500';});
textarea.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='Enter')analyze();});
document.querySelectorAll('.sample').forEach(b=>b.addEventListener('click',()=>{
  textarea.value=b.dataset.tweet.trim();counter.textContent=textarea.value.length+' / 500';
  if (MODEL && MODEL.trained)analyze();
  else textarea.focus();
}));
fetch('model.json', {cache:'no-store'}).then(response=>{
  if(!response.ok) throw new Error('model.json не знайдено');return response.json();
}).then(data=>{
  if(!data.trained) throw new Error('Модель ще не навчена. Запусти run_lab.bat і завантаж docs/model.json на GitHub.');
  MODEL=data;
  button.disabled=false;
  $('model-status').textContent='Модель завантажена';
  $('accuracy').textContent=(data.accuracy*100).toFixed(2)+'%';
  $('train-count').textContent=Number(data.train_count).toLocaleString('uk-UA');
}).catch(err=>{
  $('model-error').textContent=err.message + (location.protocol==='file:'?' Відкрий через GitHub Pages або локальний сервер.':'');
  $('model-status').textContent='Модель не готова';
});
