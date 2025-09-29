(function(){
  const q = document.getElementById('question');
  const askBtn = document.getElementById('askBtn');
  const ans = document.getElementById('answer');
  const apiBase = document.getElementById('apiBase');
  const saveCfg = document.getElementById('saveCfg');
  const docId = document.getElementById('docId');
  const docType = document.getElementById('docType');
  const extractBtn = document.getElementById('extractBtn');
  const extractOut = document.getElementById('extractOut');

  // charge URL API depuis le stockage local si déjà saisie
  apiBase.value = localStorage.getItem('kc_api') || '';

  saveCfg.onclick = () => {
    localStorage.setItem('kc_api', apiBase.value.trim());
    alert('Config enregistrée.');
  };

  askBtn.onclick = async () => {
    const base = (apiBase.value || '').trim();
    const question = (q.value || '').trim();
    if(!base) return alert('Renseigne API base URL');
    if(!question) return alert('Pose une question');
    ans.textContent = '⏳ ...';
    try {
      const r = await fetch(base.replace(/\/$/,'') + '/ask?q=' + encodeURIComponent(question));
      const data = await r.json();
      ans.textContent = data.answer || JSON.stringify(data,null,2);
    } catch(e){ ans.textContent = 'Erreur: ' + e; }
  };

  extractBtn.onclick = async () => {
    const base = (apiBase.value || '').trim();
    const id = (docId.value || '').trim();
    const type = (docType.value || 'facture');
    if(!base) return alert('Renseigne API base URL');
    if(!id) return alert('Doc ID ?');
    extractOut.textContent = '⏳ ...';
    try {
      const url = base.replace(/\/$/,'') + `/extract?doc_id=${encodeURIComponent(id)}&doc_type=${encodeURIComponent(type)}`;
      const r = await fetch(url);
      const ct = r.headers.get('content-type') || '';
      if(ct.includes('application/json')){
        extractOut.textContent = JSON.stringify(await r.json(), null, 2);
      } else {
        extractOut.textContent = await r.text();
      }
    } catch(e){ extractOut.textContent = 'Erreur: ' + e; }
  };
})();
