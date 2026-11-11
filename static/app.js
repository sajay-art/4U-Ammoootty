const input=document.getElementById('fileInput'), zone=document.getElementById('dropzone'), browse=document.getElementById('browse'), selected=document.getElementById('selectedFile'), btn=document.getElementById('convertBtn'), format=document.getElementById('format'), notice=document.getElementById('notice'), progress=document.getElementById('progressWrap'), bar=document.getElementById('progressBar'), pct=document.getElementById('progressPct'), progressText=document.getElementById('progressText');
let chosen=null;
function choose(file){if(!file)return;chosen=file;selected.textContent='✓ '+file.name+' ('+(file.size/1024/1024).toFixed(1)+' MB)';btn.disabled=false;notice.style.display='none'}
browse.addEventListener('click',e=>{e.stopPropagation();input.click()});zone.addEventListener('click',()=>input.click());input.addEventListener('change',()=>choose(input.files[0]));
['dragenter','dragover'].forEach(ev=>zone.addEventListener(ev,e=>{e.preventDefault();zone.classList.add('drag')}));
['dragleave','drop'].forEach(ev=>zone.addEventListener(ev,e=>{e.preventDefault();zone.classList.remove('drag')}));
zone.addEventListener('drop',e=>choose(e.dataTransfer.files[0]));
function message(text,ok=false){notice.textContent=text;notice.className='notice'+(ok?' success':'');notice.style.display='block'}
btn.addEventListener('click',async()=>{if(!chosen)return;btn.disabled=true;progress.style.display='block';notice.style.display='none';bar.style.width='15%';pct.textContent='15%';progressText.textContent='Uploading and converting…';const data=new FormData();data.append('media',chosen);data.append('format',format.value);
try{const res=await fetch('/api/convert',{method:'POST',body:data});if(!res.ok){let err={};try{err=await res.json()}catch{}throw new Error(err.error||'Conversion failed. Please try again.')}
bar.style.width='100%';pct.textContent='100%';progressText.textContent='Your download is ready';const blob=await res.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='4U-Ammoootty.'+format.value;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);message('Done! Your converted file has been downloaded.',true);
}catch(e){message(e.message)}finally{btn.disabled=false;setTimeout(()=>{progress.style.display='none';bar.style.width='0'},2500)}});
document.querySelector('.menu').addEventListener('click',()=>{document.querySelector('nav').style.display=document.querySelector('nav').style.display==='flex'?'none':'flex'});
