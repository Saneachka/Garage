import React from 'react';
import {api,labels,dateTime} from './api';
import {Button,ErrorBox,useSubmit} from './ui';
export function Workflow({appointment,user,onChange,orderId}) {
 const [action,setAction]=React.useState(null);
 const submit=useSubmit(async()=>{if(orderId&&action!=='confirm'&&user.role!=='client'){await api(`/work-orders/${orderId}/status`,{method:'POST',body:{status:{start:'in_progress',complete:'completed',cancel:'cancelled'}[action]}});}else{await api(`/appointments/${appointment.id}/${action}`,{method:'POST'});}setAction(null);onChange('Статусы записи и заказ-наряда обновлены');});
 if(!appointment)return null;
 const actions=[];
 if(user.role==='admin'&&appointment.status==='new')actions.push(['confirm','Подтвердить']);
 if(user.role!=='client'&&appointment.status==='confirmed')actions.push(['start','В работу']);
 if(user.role!=='client'&&appointment.status==='in_progress')actions.push(['complete','Завершить']);
 if((user.role==='admin'&&['new','confirmed','in_progress'].includes(appointment.status))||(user.role==='client'&&['new','confirmed'].includes(appointment.status)&&new Date(appointment.starts_at)>new Date()))actions.push(['cancel','Отменить']);
 return <div className="workflow"><p className="muted">Состояние обслуживания: {labels[appointment.status]}. Изменение применяется к записи и заказ-наряду; диагностический лист показывает состояние этой же записи.</p><div className="action-list">{actions.map(([a,label])=><Button key={a} kind={a==='cancel'?'danger':'secondary'} onClick={()=>setAction(a)}>{label}</Button>)}</div>{action&&<div className="workflow-confirm"><p>Подтвердить действие «{actions.find(a=>a[0]===action)?.[1]}» для записи № {appointment.id}?</p><ErrorBox error={submit.error}/><div className="action-list"><Button loading={submit.busy} onClick={submit.run}>Подтвердить действие</Button><Button disabled={submit.busy} kind="secondary" onClick={()=>setAction(null)}>Назад</Button></div></div>}</div>;
}
export function AppointmentInfo({appointment}){
 if(!appointment?.created_at)return null;
 return <dl className="document-info"><div><dt>Автомобиль клиента</dt><dd>{appointment.vehicle_label} {appointment.plate_number&&` · ${appointment.plate_number}`}</dd></div><div><dt>Клиент</dt><dd>{appointment.client_name}</dd></div><div><dt>Дата заявки</dt><dd>{dateTime(appointment.created_at)}</dd></div><div><dt>Дата записи</dt><dd>{dateTime(appointment.starts_at)} — {dateTime(appointment.ends_at)}</dd></div></dl>;
}
export function Filters({value,onChange,statuses=null,masters=null,dates=false,placeholder='Поиск…'}){
 return <div className="filters"><label><span>Поиск</span><input type="search" value={value.q||''} placeholder={placeholder} onChange={e=>onChange({...value,q:e.target.value})}/></label>{statuses&&<label><span>Статус</span><select value={value.status||''} onChange={e=>onChange({...value,status:e.target.value})}><option value="">Все статусы</option>{statuses.map(s=><option key={s} value={s}>{labels[s]||s}</option>)}</select></label>}{masters&&<label><span>Мастер</span><select value={value.master||''} onChange={e=>onChange({...value,master:e.target.value})}><option value="">Все мастера</option>{masters.map(m=><option key={m.id} value={m.id}>{m.full_name}</option>)}</select></label>}{dates&&<><label><span>С даты</span><input type="date" value={value.from||''} onChange={e=>onChange({...value,from:e.target.value})}/></label><label><span>По дату</span><input type="date" value={value.to||''} onChange={e=>onChange({...value,to:e.target.value})}/></label></>}<Button kind="secondary" onClick={()=>onChange({})}>Сбросить</Button></div>;
}
export function matches(value,text,status='',date='',master=''){
 return (!value.q||text.toLocaleLowerCase().includes(value.q.toLocaleLowerCase()))&&(!value.status||value.status===status)&&(!value.master||Number(value.master)===Number(master))&&(!value.from||date.slice(0,10)>=value.from)&&(!value.to||date.slice(0,10)<=value.to);
}
