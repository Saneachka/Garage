import React,{useRef,useState} from 'react';
import {api,dateTime} from './api';
import {Button,ErrorBox,Resource,useResource} from './ui';
export default function Attachments({type,id,user}){
 const r=useResource(()=>api(`/${type}/${id}/files`),[type,id]);const [error,setError]=useState(null),[busy,setBusy]=useState(false);const input=useRef(null);
 const canUpload=type==='diagnostics'?user.role==='master':user.role==='admin';
 async function upload(e){e.preventDefault();const files=input.current.files;if(!files.length)return;setBusy(true);setError(null);try{const form=new FormData();Array.from(files).forEach(f=>form.append('files',f));const response=await fetch(`/api/${type}/${id}/files`,{method:'POST',credentials:'same-origin',body:form});if(!response.ok){const body=await response.json();throw Error(typeof body.detail==='string'?body.detail:'Не удалось загрузить файлы');}input.current.value='';r.reload();}catch(e){setError(e);}finally{setBusy(false);}}
 return <section className="attachments"><h3>Файлы</h3><Resource resource={r}>{rows=>rows.length?<ul>{rows.map(f=><li key={f.id}><a href={`/api/files/${f.id}`} target="_blank" rel="noreferrer">{f.filename}</a><small> · {Math.ceil(f.size/1024)} КБ · {dateTime(f.created_at)}</small></li>)}</ul>:<p className="muted">Файлы не приложены.</p>}</Resource>{canUpload&&<form onSubmit={upload}><label>Приложить файлы<input ref={input} type="file" multiple accept=".pdf,.txt,.docx,.png,.jpg,.jpeg" disabled={busy}/></label><Button loading={busy}>Загрузить</Button><ErrorBox error={error}/></form>}</section>;
}
