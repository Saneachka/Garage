import React, {useEffect, useRef, useState, useId} from 'react';
import {X, AlertCircle, LoaderCircle, ArrowUpRight, Wrench} from 'lucide-react';
import {labels} from './api';
export function Button({children,kind='',loading=false,disabled=false,...props}) { return <button className={`button ${kind}`} disabled={loading || disabled} {...props}>{loading && <LoaderCircle size={16} className="spin"/>}{children}</button>; }
export function ErrorBox({error}) { return error ? <div className="error" role="alert"><AlertCircle size={18}/><span>{error.message || error}</span></div> : null; }
export function Empty({title='Пока ничего нет',text,action}) {return <div className="empty"><div className="empty-icon"><Wrench size={25}/></div><h3>{title}</h3><p>{text}</p>{action}</div>;}
export function Loading() {return <div className="loading" role="status"><LoaderCircle className="spin"/> Загружаем данные…</div>;}
export function Badge({status}) {return <span className={`badge ${status}`}>{labels[status] || status}</span>;}
export function Field({label,children,...props}) {const id=useId();return <div className="field"><label htmlFor={id}>{label}</label>{children ? React.cloneElement(children,{id}) : <input id={id} {...props}/>}</div>;}
export function Modal({title,subtitle,children,onClose}) {
 const ref=useRef(null);
 useEffect(()=>{ const el=ref.current; el.showModal(); return ()=>el.close();},[]);
 return <dialog ref={ref} className="modal" onCancel={event=>{event.preventDefault();onClose();}} onClick={event=>{if(event.target===ref.current)onClose();}}><div className="modal-inner"><header><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><button className="icon-button" onClick={onClose} aria-label="Закрыть"><X/></button></header>{children}</div></dialog>;
}
export function SectionHead({eyebrow,title,description,action}) {return <div className="section-head"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>;}
export function PanelHead({title,action}) {return <div className="panel-head"><h2>{title}</h2>{action}</div>;}
export function TextLink({children,onClick}) {return <button className="text-link" onClick={onClick}>{children}<ArrowUpRight size={16}/></button>;}
export function useResource(loader, deps=[]) {
 const [state,setState]=useState({data:null,error:null,loading:true}); const [version,setVersion]=useState(0);
 useEffect(()=>{let alive=true;setState({data:null,error:null,loading:true});Promise.resolve().then(loader).then(data=>{if(alive)setState({data,error:null,loading:false});}).catch(error=>{if(alive)setState({data:null,error,loading:false});});return()=>{alive=false;};},[...deps,version]);
 return {...state,reload:()=>setVersion(v=>v+1)};
}
export function Resource({resource,children}) {if(resource.loading)return <Loading/>;if(resource.error)return <><ErrorBox error={resource.error}/><Button kind="secondary" onClick={resource.reload}>Повторить</Button></>;return children(resource.data);}
export function useSubmit(action) {
 const [busy,setBusy]=useState(false);const [error,setError]=useState(null);const lock=useRef(false);
 return {busy,error,run:async event=>{event?.preventDefault();if(lock.current)return;lock.current=true;setBusy(true);setError(null);try{await action();}catch(e){setError(e);}finally{lock.current=false;setBusy(false);}}};
}
