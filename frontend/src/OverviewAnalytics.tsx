import { BarChart3, ClipboardList, Headphones, TrendingUp } from "lucide-react";

type Project = { id: number; status: string };
type Ticket = { id: number; status: string; priority: string };
type Client = { id: number; status: string };

type Props = {
  projects: Project[];
  tickets: Ticket[];
  clients: Client[];
  onProjects: () => void;
  onTickets: () => void;
};

// Tiny progress bar. No chart library needed.
function ProgressRow({ label, count, total, tone }: { label: string; count: number; total: number; tone: string }) {
  const percent = total ? Math.round((count / total) * 100) : 0;
  return (
    <div className="progressRow">
      <div className="progressMeta"><span>{label}</span><span><b>{count}</b> / {total}</span></div>
      <div className="progressTrack" role="progressbar" aria-label={label} aria-valuenow={count} aria-valuemin={0} aria-valuemax={Math.max(total, 1)}>
        <div className={"progressFill " + tone} style={{ width: percent + "%" }} />
      </div>
    </div>
  );
}

// Count projects and tickets from real workspace data.
export default function OverviewAnalytics({ projects, tickets, clients, onProjects, onTickets }: Props) {
  const completed = projects.filter(p => p.status === "done").length;
  const inProgress = projects.filter(p => p.status === "in_progress").length;
  const planned = projects.filter(p => p.status === "planned").length;
  const resolved = tickets.filter(t => t.status === "resolved").length;
  const open = tickets.filter(t => t.status === "open").length;
  const working = tickets.filter(t => t.status === "in_progress").length;
  const high = tickets.filter(t => t.priority === "high" && t.status !== "resolved").length;
  const active = clients.filter(c => c.status === "active").length;

  return (
    <>
      <div className="insightsHeading">
        <div><h2>Workspace activity</h2><p>Live totals from your current workspace.</p></div>
      </div>
      <div className="insightsGrid">
        <section className="panel insightPanel" aria-label="Project progress">
          <div className="insightHeader"><div className="insightIcon projectsIcon"><ClipboardList size={19} /></div><button className="textBtn" onClick={onProjects}>View projects <span aria-hidden="true">↗</span></button></div>
          <h3>Project pipeline</h3>
          <p className="insightLead">{projects.length ? <><strong>{completed}</strong> of {projects.length} completed</> : "No projects tracked yet"}</p>
          <ProgressRow label="Completed" count={completed} total={projects.length} tone="toneGreen" />
          <ProgressRow label="In progress" count={inProgress} total={projects.length} tone="toneBlue" />
          <ProgressRow label="Planned" count={planned} total={projects.length} tone="toneNeutral" />
        </section>
        <section className="panel insightPanel" aria-label="Support ticket progress">
          <div className="insightHeader"><div className="insightIcon ticketsIcon"><Headphones size={19} /></div><button className="textBtn" onClick={onTickets}>View tickets <span aria-hidden="true">↗</span></button></div>
          <h3>Support queue</h3>
          <p className="insightLead">{tickets.length ? <><strong>{resolved}</strong> of {tickets.length} resolved</> : "No tickets recorded yet"}</p>
          <ProgressRow label="Resolved" count={resolved} total={tickets.length} tone="toneGreen" />
          <ProgressRow label="In progress" count={working} total={tickets.length} tone="toneBlue" />
          <ProgressRow label="Open" count={open} total={tickets.length} tone="toneAmber" />
        </section>
      </div>
      <div className="overviewHighlights">
        <div><TrendingUp size={18} /><span><strong>{active}</strong> active clients</span></div>
        <div><BarChart3 size={18} /><span><strong>{high}</strong> high-priority unresolved tickets</span></div>
      </div>
    </>
  );
}
