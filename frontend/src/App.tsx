import {useEffect,useState} from "react";
type Client = {id:number; name:string; email:string; status:string};
type Project = {id:number; title:string; client_id:number; status:string};
type Summary = {clients:number;active_clients:number;projects:number;completed_projects:number};
type Page = "overview"|"clients"|"projects";
async function api<T>(path:string, options?:RequestInit):Promise<T>{
 const response=await fetch("/api"+path,{...options,headers:{"Content-Type":"application/json",...options?.headers}});
 if(!response.ok) throw new Error("Request failed ("+response.status+"). Check your inputs and backend.");
 return response.status===204 ? undefined as T : await response.json() as T;
}
export default function App(){
 const [page,setPage]=useState<Page>("overview");
 const [clients,setClients]=useState<Client[]>([]);
 const [projects,setProjects]=useState<Project[]>([]);
 const [summary,setSummary]=useState<Summary>({clients:0,active_clients:0,projects:0,completed_projects:0});
 const [error,setError]=useState("");
 const [clientName,setClientName]=useState("");
 const [clientEmail,setClientEmail]=useState("");
 const [projectTitle,setProjectTitle]=useState("");
 const [projectClient,setProjectClient]=useState("");
 const [busy,setBusy]=useState(false);
 async function refresh(){
  try{const [c,p,s]=await Promise.all([api<Client[]>("/clients"),api<Project[]>("/projects"),api<Summary>("/summary")]);
   setClients(c);setProjects(p);setSummary(s);setError("");
  }catch(e){setError((e as Error).message+" Start FastAPI on port 8000.")}
 }
 useEffect(()=>{void refresh()},[]);
 async function write(fn:()=>Promise<unknown>){setBusy(true);setError("");try{await fn();await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 const statusText=(s:string)=>s.replace("_"," ");
 return <div className="shell">
 <aside><div className="logo">◈ <span>workbase.</span></div><div className="sideLabel">WORKSPACE</div>
 <nav aria-label="Main navigation">
 <button className={page==="overview"?"selected":""} onClick={()=>setPage("overview")}>▦ &nbsp; Overview</button>
 <button className={page==="clients"?"selected":""} onClick={()=>setPage("clients")}>♧ &nbsp; Clients <small>{clients.length}</small></button>
 <button className={page==="projects"?"selected":""} onClick={()=>setPage("projects")}>▤ &nbsp; Projects <small>{projects.length}</small></button>
 </nav><div className="sideFooter"><b>D</b> Demo workspace <small>Local use only</small></div></aside>
 <section className="main"><div className="topbar">Workspace <span>/</span> {page==="overview"?"Overview":page==="clients"?"Clients":"Projects"} <span className="topRight">v0.1 · local demo</span></div>
 <main><div className="heading"><div className="eyebrow">WORKBASE / DASHBOARD</div><h1>{page==="overview"?"Good to see you.":page==="clients"?"Clients":"Projects"}</h1><p>{page==="overview"?"Here's what's happening in your workspace.":page==="clients"?"Keep track of your client relationships.":"Manage your projects and progress."}</p></div>
 {error&&<div role="alert" className="alert">{error} <button onClick={()=>void refresh()}>Retry</button></div>}
 {page==="overview"&&<><div className="metrics">
 {([["Total clients",summary.clients],["Active clients",summary.active_clients],["Projects",summary.projects],["Completed",summary.completed_projects]] as [string,number][]).map(([name,count])=><div className="metric" key={name}><p>{name}</p><strong>{count}</strong><small>Workspace overview</small></div>)}</div>
 <div className="panel"><div className="panelHead"><h2>Recent projects</h2><button className="linkBtn" onClick={()=>setPage("projects")}>View all →</button></div>
 {projects.length?<div className="scroll"><table><thead><tr><th>Project</th><th>Client</th><th>Status</th></tr></thead><tbody>{projects.slice(0,5).map(p=><tr key={p.id}><td>{p.title}</td><td>{clients.find(c=>c.id===p.client_id)?.name||"Unknown"}</td><td><span className="tag">{statusText(p.status)}</span></td></tr>)}</tbody></table></div>:<div className="empty">No projects yet. Add a client, then create a project.</div>}</div></>}
 {page==="clients"&&<><div className="panel formPanel"><h2>New client</h2><form onSubmit={e=>{e.preventDefault();void write(async()=>{await api("/clients",{method:"POST",body:JSON.stringify({name:clientName,email:clientEmail})});setClientName("");setClientEmail("")})}}>
 <label>Company<input required minLength={2} maxLength={100} placeholder="Company name" value={clientName} onChange={e=>setClientName(e.target.value)}/></label>
 <label>Email<input required type="email" placeholder="hello@example.com" value={clientEmail} onChange={e=>setClientEmail(e.target.value)}/></label><button className="primary" disabled={busy}>+ Add client</button></form></div>
 <div className="panel"><div className="panelHead"><h2>Clients</h2><span>{clients.length} records</span></div><div className="scroll"><table><thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Actions</th></tr></thead><tbody>{clients.map(c=><tr key={c.id}><td>{c.name}</td><td>{c.email}</td><td><select aria-label={"Status "+c.name} value={c.status} onChange={e=>void write(()=>api("/clients/"+c.id,{method:"PATCH",body:JSON.stringify({status:e.target.value})}))}><option value="lead">Lead</option><option value="active">Active</option><option value="inactive">Inactive</option></select></td><td><button className="danger" disabled={busy} onClick={()=>void write(()=>api("/clients/"+c.id,{method:"DELETE"}))}>Delete</button></td></tr>)}</tbody></table></div>{!clients.length&&<p className="empty">No clients yet.</p>}</div></>}
 {page==="projects"&&<><div className="panel formPanel"><h2>New project</h2><form onSubmit={e=>{e.preventDefault();void write(async()=>{await api("/projects",{method:"POST",body:JSON.stringify({title:projectTitle,client_id:Number(projectClient)})});setProjectTitle("")})}}>
 <label>Project name<input required minLength={2} maxLength={120} placeholder="Website redesign" value={projectTitle} onChange={e=>setProjectTitle(e.target.value)}/></label>
 <label>Client<select required value={projectClient} onChange={e=>setProjectClient(e.target.value)}><option value="">Select client</option>{clients.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label><button className="primary" disabled={busy||!clients.length}>+ Add project</button></form></div>
 <div className="panel"><div className="panelHead"><h2>Projects</h2><span>{projects.length} records</span></div><div className="scroll"><table><thead><tr><th>Project</th><th>Client</th><th>Status</th><th>Actions</th></tr></thead><tbody>{projects.map(p=><tr key={p.id}><td>{p.title}</td><td>{clients.find(c=>c.id===p.client_id)?.name||"Unknown"}</td><td><select aria-label={"Status "+p.title} value={p.status} onChange={e=>void write(()=>api("/projects/"+p.id,{method:"PATCH",body:JSON.stringify({status:e.target.value})}))}><option value="planned">Planned</option><option value="in_progress">In progress</option><option value="done">Done</option></select></td><td><button className="danger" disabled={busy} onClick={()=>void write(()=>api("/projects/"+p.id,{method:"DELETE"}))}>Delete</button></td></tr>)}</tbody></table></div>{!projects.length&&<p className="empty">No projects yet.</p>}</div></>}
 <p className="notice">This first release has no authentication or workspace isolation. Run it locally with sample data only.</p></main></section></div>;
}
