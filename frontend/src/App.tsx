import {useEffect,useState} from "react";
type Account={id:number;email:string;display_name:string;workspace_name:string;home_workspace_id:number};
type Workspace={id:number;name:string;role:"owner"|"editor"|"viewer"};
type Invitation={id:number;workspace_id:number;workspace_name:string;role:string};
type Ticket={id:number;client_id:number;subject:string;description:string;priority:"low"|"medium"|"high";status:"open"|"in_progress"|"resolved"};
type Member={id:number;email:string;display_name:string;role:string;accepted:boolean};
export default function App(){
 const [token,setToken]=useState(()=>sessionStorage.getItem("workbase_token")||"");
 const [account,setAccount]=useState<Account|null>(null);
 const [workspaces,setWorkspaces]=useState<Workspace[]>([]);
 const [activeWorkspace,setActiveWorkspace]=useState(0);
 const [formMode,setFormMode]=useState<"login"|"register">("register");
 const [name,setName]=useState("");
 const [workspace,setWorkspace]=useState("");
 const [email,setEmail]=useState("");
 const [password,setPassword]=useState("");
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(false);
 activeToken=token;
 useEffect(()=>{
   if(!token){setAccount(null);return;}
   api<Account>("/auth/me").then(async current=>{setAccount(current);const all=await api<Workspace[]>("/workspaces");setWorkspaces(all);setActiveWorkspace(current.home_workspace_id);}).catch(()=>{
     sessionStorage.removeItem("workbase_token");activeToken="";setToken("");setAccount(null);
   });
 },[token]);
 function logout(){sessionStorage.removeItem("workbase_token");activeToken="";setToken("");setAccount(null);}
 async function authenticate(event:React.FormEvent){
   event.preventDefault();setError("");setLoading(true);
   try {
     const body=formMode==="register"?{email,password,display_name:name,workspace_name:workspace}:{email,password};
     const response=await api<{access_token:string}>(formMode==="register"?"/auth/register":"/auth/login",{method:"POST",body:JSON.stringify(body)});
     activeToken=response.access_token;sessionStorage.setItem("workbase_token",response.access_token);setToken(response.access_token);
   }catch(e){setError((e as Error).message)}finally{setLoading(false)}
 }
 if(token&&(!account||!activeWorkspace))return <main style={{padding:40}}>Loading your workspace…</main>;
 if(account&&activeWorkspace)return <Dashboard key={account.id+"-"+activeWorkspace} account={account} workspaces={workspaces} activeWorkspace={activeWorkspace} onWorkspace={setActiveWorkspace} onRefreshWorkspaces={async()=>{const all=await api<Workspace[]>("/workspaces");setWorkspaces(all)}} onLogout={logout}/>;
 return <div className="authScreen"><div className="authCard"><div className="authLogo">◈ workbase.</div>
 <h1>{formMode==="register"?"Create your workspace":"Welcome back"}</h1>
 <p>{formMode==="register"?"Set up your account and start managing clients and projects.":"Sign in to your Workbase dashboard."}</p>
 {error&&<div className="alert" role="alert">{error}</div>}
 <form onSubmit={authenticate}>
 {formMode==="register"&&<><label>Your name<input minLength={2} maxLength={100} required value={name} onChange={e=>setName(e.target.value)}/></label>
 <label>Workspace name<input minLength={2} maxLength={100} required value={workspace} onChange={e=>setWorkspace(e.target.value)}/></label></>}
 <label>Email<input required type="email" value={email} onChange={e=>setEmail(e.target.value)}/></label>
 <label>Password<input required type="password" minLength={formMode==="register"?10:1} value={password} onChange={e=>setPassword(e.target.value)}/></label>
 <button type="submit" className="primary" disabled={loading}>{loading?"Working…":formMode==="register"?"Create account":"Sign in"}</button></form>
 <button className="textSwitch" onClick={()=>{setError("");setFormMode(formMode==="register"?"login":"register")}}>{formMode==="register"?"Already have an account? Sign in":"Need an account? Register"}</button>
 <small>Local development app. Don't enter personal or real client information.</small></div></div>;
}

type Client = {id:number; name:string; email:string; status:string};
type Project = {id:number; title:string; client_id:number; status:string};
type Summary = {clients:number;active_clients:number;projects:number;completed_projects:number;open_tickets:number;high_priority_tickets:number};
type Page = "overview"|"clients"|"projects"|"team"|"tickets";
let activeToken = "";
let workspaceId = 0;
async function api<T>(path:string, options?:RequestInit):Promise<T>{
 const response=await fetch("/api"+path,{...options,headers:{"Content-Type":"application/json",...(activeToken ? {Authorization:"Bearer "+activeToken}:{}),...(workspaceId ? {"X-Workspace-Id":String(workspaceId)}:{}),...options?.headers}});
 if(!response.ok) throw new Error("Request failed ("+response.status+"). Check your inputs and backend.");
 return response.status===204 ? undefined as T : await response.json() as T;
}
function Dashboard({account,workspaces,activeWorkspace,onWorkspace,onRefreshWorkspaces,onLogout}:{account:Account;workspaces:Workspace[];activeWorkspace:number;onWorkspace:(id:number)=>void;onRefreshWorkspaces:()=>Promise<void>;onLogout:()=>void}){
 workspaceId=activeWorkspace;
 const current=workspaces.find(w=>w.id===activeWorkspace);
 const canEdit=current?.role==="owner"||current?.role==="editor";
 const [page,setPage]=useState<Page>("overview");
 const [clients,setClients]=useState<Client[]>([]);
 const [projects,setProjects]=useState<Project[]>([]);
 const [tickets,setTickets]=useState<Ticket[]>([]);
 const [summary,setSummary]=useState<Summary>({clients:0,active_clients:0,projects:0,completed_projects:0,open_tickets:0,high_priority_tickets:0});
 const [error,setError]=useState("");
 const [clientName,setClientName]=useState("");
 const [clientEmail,setClientEmail]=useState("");
 const [projectTitle,setProjectTitle]=useState("");
 const [projectClient,setProjectClient]=useState("");
 const [busy,setBusy]=useState(false);
 async function refresh(){
  try{const [c,p,s,t]=await Promise.all([api<Client[]>("/clients"),api<Project[]>("/projects"),api<Summary>("/summary"),api<Ticket[]>("/tickets")]);
   setClients(c);setProjects(p);setSummary(s);setTickets(t);setError("");
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
 <button className={page==="tickets"?"selected":""} onClick={()=>setPage("tickets")}>▧ &nbsp; Tickets <small>{summary.open_tickets}</small></button>
 <button className={page==="team"?"selected":""} onClick={()=>setPage("team")}>◉ &nbsp; Team</button>
 </nav><div className="sideFooter"><b>D</b> Demo workspace <small>Local use only</small></div></aside>
 <section className="main"><div className="topbar">Workspace <span>/</span> {page==="overview"?"Overview":page==="clients"?"Clients":page==="projects"?"Projects":page==="tickets"?"Tickets":"Team"} <span className="topRight">v0.4 · local demo</span></div>
 <div className="workspaceSwitcher"><label>Active workspace <select value={activeWorkspace} onChange={e=>onWorkspace(Number(e.target.value))}>{workspaces.map(w=><option value={w.id} key={w.id}>{w.name} ({w.role})</option>)}</select></label></div>
 <main><div className="heading"><div className="eyebrow">WORKBASE / DASHBOARD</div><h1>{page==="overview"?"Good to see you.":page==="clients"?"Clients":page==="projects"?"Projects":page==="tickets"?"Tickets":"Team"}</h1><p>{page==="overview"?"Here's what's happening in your workspace.":page==="clients"?"Keep track of your client relationships.":page==="projects"?"Manage your projects and progress.":page==="tickets"?"Track and resolve client requests.":"People and permissions in your workspace."}</p></div>
 {error&&<div role="alert" className="alert">{error} <button onClick={()=>void refresh()}>Retry</button></div>}
 {page==="team"&&<Team key={activeWorkspace} workspace={current} onUpdated={onRefreshWorkspaces}/>}
 {page==="tickets"&&<Tickets clients={clients} tickets={tickets} canEdit={canEdit} canDelete={current?.role==="owner"} submit={write} busy={busy}/>}
 {page==="overview"&&<><div className="metrics">
 {([["Total clients",summary.clients],["Active clients",summary.active_clients],["Projects",summary.projects],["Completed",summary.completed_projects],["Open tickets",summary.open_tickets],["High priority",summary.high_priority_tickets]] as [string,number][]).map(([name,count])=><div className="metric" key={name}><p>{name}</p><strong>{count}</strong><small>Workspace overview</small></div>)}</div>
 <div className="panel"><div className="panelHead"><h2>Recent projects</h2><button className="linkBtn" onClick={()=>setPage("projects")}>View all →</button></div>
 {projects.length?<div className="scroll"><table><thead><tr><th>Project</th><th>Client</th><th>Status</th></tr></thead><tbody>{projects.slice(0,5).map(p=><tr key={p.id}><td>{p.title}</td><td>{clients.find(c=>c.id===p.client_id)?.name||"Unknown"}</td><td><span className="tag">{statusText(p.status)}</span></td></tr>)}</tbody></table></div>:<div className="empty">No projects yet. Add a client, then create a project.</div>}</div></>}
 {page==="clients"&&<>{canEdit&&<div className="panel formPanel"><h2>New client</h2><form onSubmit={e=>{e.preventDefault();void write(async()=>{await api("/clients",{method:"POST",body:JSON.stringify({name:clientName,email:clientEmail})});setClientName("");setClientEmail("")})}}>
 <label>Company<input required minLength={2} maxLength={100} placeholder="Company name" value={clientName} onChange={e=>setClientName(e.target.value)}/></label>
 <label>Email<input required type="email" placeholder="hello@example.com" value={clientEmail} onChange={e=>setClientEmail(e.target.value)}/></label><button className="primary" disabled={busy}>+ Add client</button></form></div>}
 <div className="panel"><div className="panelHead"><h2>Clients</h2><span>{clients.length} records</span></div><div className="scroll"><table><thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Actions</th></tr></thead><tbody>{clients.map(c=><tr key={c.id}><td>{c.name}</td><td>{c.email}</td><td><select aria-label={"Status "+c.name} disabled={!canEdit} value={c.status} onChange={e=>void write(()=>api("/clients/"+c.id,{method:"PATCH",body:JSON.stringify({status:e.target.value})}))}><option value="lead">Lead</option><option value="active">Active</option><option value="inactive">Inactive</option></select></td><td><button className="danger" disabled={busy||current?.role!=="owner"} onClick={()=>void write(()=>api("/clients/"+c.id,{method:"DELETE"}))}>Delete</button></td></tr>)}</tbody></table></div>{!clients.length&&<p className="empty">No clients yet.</p>}</div></>}
 {page==="projects"&&<>{canEdit&&<div className="panel formPanel"><h2>New project</h2><form onSubmit={e=>{e.preventDefault();void write(async()=>{await api("/projects",{method:"POST",body:JSON.stringify({title:projectTitle,client_id:Number(projectClient)})});setProjectTitle("")})}}>
 <label>Project name<input required minLength={2} maxLength={120} placeholder="Website redesign" value={projectTitle} onChange={e=>setProjectTitle(e.target.value)}/></label>
 <label>Client<select required value={projectClient} onChange={e=>setProjectClient(e.target.value)}><option value="">Select client</option>{clients.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label><button className="primary" disabled={busy||!clients.length}>+ Add project</button></form></div>}
 <div className="panel"><div className="panelHead"><h2>Projects</h2><span>{projects.length} records</span></div><div className="scroll"><table><thead><tr><th>Project</th><th>Client</th><th>Status</th><th>Actions</th></tr></thead><tbody>{projects.map(p=><tr key={p.id}><td>{p.title}</td><td>{clients.find(c=>c.id===p.client_id)?.name||"Unknown"}</td><td><select aria-label={"Status "+p.title} disabled={!canEdit} value={p.status} onChange={e=>void write(()=>api("/projects/"+p.id,{method:"PATCH",body:JSON.stringify({status:e.target.value})}))}><option value="planned">Planned</option><option value="in_progress">In progress</option><option value="done">Done</option></select></td><td><button className="danger" disabled={busy||!canEdit} onClick={()=>void write(()=>api("/projects/"+p.id,{method:"DELETE"}))}>Delete</button></td></tr>)}</tbody></table></div>{!projects.length&&<p className="empty">No projects yet.</p>}</div></>}
 <p className="notice">Signed in as {account.display_name} · {current?.name} ({current?.role}). Local development only.</p><button onClick={onLogout}>Sign out</button></main></section></div>;
}

function Team({workspace,onUpdated}:{workspace:Workspace|undefined;onUpdated:()=>Promise<void>}){
 const [members,setMembers]=useState<Member[]>([]);
 const [invitations,setInvitations]=useState<Invitation[]>([]);
 const [email,setEmail]=useState("");
 const [role,setRole]=useState("viewer");
 const [error,setError]=useState("");
 const [message,setMessage]=useState("");
 const refresh=async()=>{try{const [m,i]=await Promise.all([api<Member[]>("/workspaces/"+workspace?.id+"/members"),api<Invitation[]>("/invitations")]);setMembers(m);setInvitations(i)}catch(e){setError((e as Error).message)}};
 useEffect(()=>{void refresh()},[workspace?.id]);
 const run=async(fn:()=>Promise<unknown>)=>{setError("");setMessage("");try{await fn();await refresh();await onUpdated()}catch(e){setError((e as Error).message)}};
 return <><div className="panel formPanel"><h2>Team members</h2><p>Members can access this workspace after accepting an invitation.</p>{error&&<div className="alert">{error}</div>}{message&&<p>{message}</p>}
 <div className="scroll"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Access</th></tr></thead><tbody>{members.map(m=><tr key={m.id}><td>{m.display_name}</td><td>{m.email}</td><td>{m.role}</td><td>{m.accepted?"Active":"Invited"}</td></tr>)}</tbody></table></div></div>
 {workspace?.role==="owner"&&<div className="panel formPanel"><h2>Invite a member</h2><p>The person must already have a Workbase account. Invitations appear inside their Team page.</p><form onSubmit={e=>{e.preventDefault();void run(async()=>{await api("/workspaces/"+workspace.id+"/invite",{method:"POST",body:JSON.stringify({email,role})});setEmail("");setMessage("Invitation created.")})}}><label>Email<input type="email" required value={email} onChange={e=>setEmail(e.target.value)}/></label><label>Role<select value={role} onChange={e=>setRole(e.target.value)}><option value="viewer">Viewer</option><option value="editor">Editor</option></select></label><button className="primary">Invite</button></form></div>}
 <div className="panel formPanel"><h2>Your pending invitations</h2>{invitations.length===0?<p>No pending invitations.</p>:invitations.map(i=><div className="invitation" key={i.id}><span>{i.workspace_name} · {i.role}</span><button className="primary" onClick={()=>void run(()=>api("/invitations/"+i.id+"/accept",{method:"POST"}))}>Accept</button></div>)}</div></>;
}

function Tickets({clients,tickets,canEdit,canDelete,submit,busy}:{clients:Client[];tickets:Ticket[];canEdit:boolean;canDelete:boolean;submit:(fn:()=>Promise<unknown>)=>Promise<void>;busy:boolean}){
 const [subject,setSubject]=useState("");
 const [description,setDescription]=useState("");
 const [clientId,setClientId]=useState("");
 const [priority,setPriority]=useState("medium");
 const [filter,setFilter]=useState("all");
 const visible=tickets.filter(t=>filter==="all"||t.status===filter);
 return <>
 {canEdit&&<div className="panel formPanel"><h2>New support ticket</h2><p>Log an issue for a client in your workspace.</p>
 <form onSubmit={e=>{e.preventDefault();void submit(async()=>{await api("/tickets",{method:"POST",body:JSON.stringify({client_id:Number(clientId),subject,description,priority})});setSubject("");setDescription("")})}}>
 <label>Client<select value={clientId} required onChange={e=>setClientId(e.target.value)}><option value="">Choose client</option>{clients.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
 <label>Subject<input value={subject} required minLength={3} maxLength={140} onChange={e=>setSubject(e.target.value)} placeholder="Client needs help"/></label>
 <label>Priority<select value={priority} onChange={e=>setPriority(e.target.value)}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>
 <label>Description<input value={description} maxLength={2000} onChange={e=>setDescription(e.target.value)} placeholder="Issue details (optional)"/></label>
 <button className="primary" disabled={busy||!clients.length}>+ Create ticket</button></form></div>}
 <div className="panel"><div className="panelHead"><h2>Support tickets</h2><label>Filter <select value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All</option><option value="open">Open</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option></select></label></div>
 <div className="scroll"><table><thead><tr><th>Ticket</th><th>Client</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead><tbody>
 {visible.map(t=><tr key={t.id}><td><strong>{t.subject}</strong>{t.description&&<small className="ticketDescription">{t.description}</small>}</td><td>{clients.find(c=>c.id===t.client_id)?.name||"Unknown"}</td><td><span className={"tag "+(t.priority==="high"?"ticketHigh":"")}>{t.priority}</span></td><td><select aria-label={"Ticket status "+t.subject} disabled={!canEdit} value={t.status} onChange={e=>void submit(()=>api("/tickets/"+t.id,{method:"PATCH",body:JSON.stringify({status:e.target.value})}))}><option value="open">Open</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option></select></td>
 <td><button className="danger" disabled={!canDelete||busy} onClick={()=>void submit(()=>api("/tickets/"+t.id,{method:"DELETE"}))}>Delete</button></td></tr>)}
 </tbody></table></div>{visible.length===0&&<p className="empty">No tickets match this view.</p>}</div></>;
}
