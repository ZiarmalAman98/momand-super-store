import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { apiRequest } from '../services/api'
import { useAuth } from '../context/AuthContext'

const empty={name:'',contact_name:'',phone:'',email:'',address:''}
export default function SuppliersPage(){
  const {user,ready}=useAuth();const [suppliers,setSuppliers]=useState([]);const [form,setForm]=useState(empty);const [error,setError]=useState('');const [loading,setLoading]=useState(true)
  async function reload(){try{const data=await apiRequest('/suppliers/');setSuppliers(data.results||data);setError('')}catch(err){setError(err.message)}finally{setLoading(false)}}
  useEffect(()=>{if(user?.is_staff)reload()},[user])
  if(!ready)return <section className="site-container page-section"><div className="product-skeleton detail-skeleton"/></section>
  if(!user)return <Navigate to="/login" replace/>
  if(!user.is_staff)return <section className="site-container page-section"><div className="state-card"><strong>Staff access required.</strong></div></section>
  async function create(event){event.preventDefault();setError('');try{await apiRequest('/suppliers/',{method:'POST',body:JSON.stringify(form)});setForm(empty);await reload()}catch(err){setError(err.data&&typeof err.data==='object'?Object.values(err.data).flat().join(' '):err.message)}}
  return <section className="site-container page-section"><div className="page-title-row"><div><span className="eyebrow">SUPPLIER DIRECTORY</span><h1>Suppliers</h1><p>Supplier contacts used when recording received purchases.</p></div></div>{error&&<div className="inline-error" role="alert">{error}</div>}
    <div className="inventory-grid"><article className="dashboard-panel"><h2>Add supplier</h2><form className="staff-form" onSubmit={create}>{[['name','Supplier name'],['contact_name','Contact name'],['phone','Phone'],['email','Email'],['address','Address']].map(([key,label])=><label key={key}>{label}<input required={key==='name'} type={key==='email'?'email':'text'} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})}/></label>)}<button className="button-primary">Save supplier</button></form></article>
    <article className="dashboard-panel"><h2>Supplier list</h2>{loading?<div className="product-skeleton detail-skeleton"/>:suppliers.length===0?<p className="muted-empty">No suppliers recorded.</p>:suppliers.map(s=><div className="dashboard-row" key={s.id}><span><strong>{s.name}</strong><br/>{s.contact_name} · {s.phone||s.email}</span><b>{s.is_active?'Active':'Inactive'}</b></div>)}</article></div>
  </section>
}
