"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useStudent } from "@/components/auth/student-provider";
import { EmptyState, ErrorState, LoadingSkeleton, PageHeader, FilterPanel } from "@/components/shared";
import { Pagination } from "@/components/shared/catalog";
import { scholarshipList, scholarshipDetail, safeScholarshipLink, benefitQuotation, type ScholarshipV2 } from "@/services/scholarships-v2";
function OfficialLink({url,label}: {url:string|null;label:string}) {
 const safe=safeScholarshipLink(url);
 return safe ? <a className="text-link" href={safe} target="_blank" rel="noopener noreferrer">{label} ↗</a> : <span>Official link unavailable</span>;
}
function SaveScholarship({item}: {item:ScholarshipV2}) {
 const student=useStudent(), [error,setError]=useState("");
 const saved=(student.values["saved-scholarships"] ?? []) as string[], active=saved.includes(item.id);
 if(!student.user) return <Link href={"/login?returnTo="+encodeURIComponent("/scholarships/"+item.id)}>Sign in to save</Link>;
 if(!student.user.email_verified) return <Link href="/verify-email">Verify your email to save</Link>;
 return <><button className="button" disabled={student.busy||student.loading||!student.workspace} aria-pressed={active} onClick={async()=>{setError("");try{await student.update("saved-scholarships",active?saved.filter(id=>id!==item.id):[...saved,item.id]);}catch(e){setError(e instanceof Error?e.message:"Unable to save. Please retry.");}}}>{active?"Remove saved scholarship":"Save scholarship"}</button>{error&&<p role="alert">{error}</p>}</>;
}
export function ScholarshipDetails({item}: {item:ScholarshipV2}) {
 return <article className="scholarship-details"><p>{item.description}</p><p>Provider: {item.provider}</p><p>Intake: {item.intake_label??"Unknown"}</p>
 <p>Human review covers published terms. Admission, eligibility and an individual award are not guaranteed. No benefit is deducted from your Financial Twin.</p><OfficialLink url={item.official_url} label="Official scholarship source"/>
 <h2>Destination scope</h2><p>{item.applicability_state==="unknown"?"Destination applicability unknown":item.applicability_state==="unrestricted"?"Documented unrestricted destinations; applicant requirements still apply.":"Only the documented targets below are covered."}</p><ul>{item.scopes.map(s=><li key={s.id}>{item.scope_labels[s.id]??"Unknown destination"} · {s.degree_level??"Degree unknown"} · {s.scope_extent==="descendants"?"Documented descendants":"Exact target"}</li>)}</ul>
 <h2>Benefits and conditions</h2>{Object.entries(item.benefits??{}).map(([key,b])=><section className="panel scholarship-card" key={key}><h3>{b.label}</h3><p>{benefitQuotation(b)}</p><p>{b.condition_state==="conditional"?"Conditional funding":b.condition_state==="unknown"?"Conditions unknown":"Source states unconditional terms"}</p><p>{b.conditions??"Additional conditions unknown"}</p><p>Cap: {b.cap_amount===null?"Unknown":b.cap_amount+" "+(b.currency??"currency unknown")+" / "+(b.period??"period unknown")}</p><p>Payment months: {b.payment_months??"Unknown"} · Coverage months: {b.coverage_months??"Unknown"}</p><p>Renewal: {b.renewal_terms??"Unknown"}</p><p>Other awards: {b.stacking_terms??"Unknown"}</p></section>)}
 {!Object.keys(item.benefits??{}).length&&<p>Benefit terms unknown</p>}
 <h2>Applicant requirements</h2><p>{item.eligibility_summary}</p><ul>{Object.entries(item.requirements??{}).map(([key,r])=><li key={key}>{r.statement}{r.conditions&&" — "+r.conditions}<p>Nationality policy: {r.nationality_mode}; documented codes: {r.nationality_codes.join(", ")||"None stated"}. This is not an individual eligibility decision.</p></li>)}</ul>
 <h2>Deadlines</h2><ul>{Object.entries(item.deadlines??{}).map(([key,d])=><li key={key}>{d.stage}: {d.date??(d.closes_at?d.closes_at+" ("+(d.timezone??"timezone unknown")+")":d.deadline_state==="rolling"?"Rolling":"Unknown")}{d.conditions&&" — "+d.conditions}</li>)}</ul>
 <h2>Field evidence</h2><p>Evidence covers the named published fields only.</p><ul>{item.evidence.map((e,i)=><li key={e.field+i}><code>{e.field}</code> · {e.source.title} · {e.source.publisher} · Retrieved {e.source.retrieved_at?.slice(0,10)??"Unknown"} · <OfficialLink url={e.source.source_url} label="Inspect evidence"/></li>)}</ul></article>;
}
export function ScholarshipExplorer() {
 const [filters,setFilters]=useState<Record<string,string>>({}),[page,setPage]=useState(1),[retry,setRetry]=useState(0);
 const [data,setData]=useState<Awaited<ReturnType<typeof scholarshipList>>|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState("");
 const key=JSON.stringify({...filters,page,page_size:12});
 const [targetLabels,setTargetLabels]=useState<Record<string,string>>({});
 useEffect(()=>{let alive=true;const timer=setTimeout(()=>{setLoading(true);setError("");scholarshipList(JSON.parse(key)).then(result=>{if(alive){setData(result);setTargetLabels(previous=>Object.assign({},previous,...result.items.map(item=>item.scope_labels)));}}).catch(e=>{if(alive)setError(e.message);}).finally(()=>{if(alive)setLoading(false);});},250);return()=>{alive=false;clearTimeout(timer);};},[key,retry]);
 function filter(name:string,value:string){setPage(1);setFilters(previous=>({...previous,[name]:value}));}
 return <><PageHeader title="Scholarships with clear evidence" eyebrow="SCHOLARSHIP EXPLORER" description="Explore independently reviewed published terms. A listing does not establish your eligibility or award."/>
 <FilterPanel>{[["q","Search"],["country","Destination country"],["provider","Provider"],["intake","Intake"]].map(([name,label])=><label key={name}>{label}<input value={filters[name]??""} maxLength={name==="q"?200:120} onChange={e=>filter(name,e.target.value)}/></label>)}
 {["university","program"].map(kind=><label key={kind}>{kind==="university"?"University":"Program"}<select value={filters[kind]??""} onChange={e=>filter(kind,e.target.value)}><option value="">All {kind=== "university"?"universities":"programs"}</option>{Object.entries(targetLabels).filter(([key])=>key.startsWith(kind+":")).map(([key,label])=><option key={key} value={key.slice(kind.length+1)}>{label}</option>)}</select></label>)}
 <label>Degree<select value={filters.degree??""} onChange={e=>filter("degree",e.target.value)}><option value="">All degrees</option>{["Bachelor","Master","PhD"].map(d=><option key={d}>{d}</option>)}</select></label>
 <label>Funding type<select value={filters.funding??""} onChange={e=>filter("funding",e.target.value)}><option value="">All funding types</option><option>Full</option><option>Partial</option></select></label>
 <label>Deadline from<input type="date" value={filters.deadline_after??""} onChange={e=>filter("deadline_after",e.target.value)}/></label><label>Deadline through<input type="date" value={filters.deadline_before??""} onChange={e=>filter("deadline_before",e.target.value)}/></label>
 <button className="button" onClick={()=>{setFilters({});setPage(1);}}>Reset filters</button></FilterPanel>
 <p role="status">{loading?"Loading reviewed scholarships…":(data?.meta.total??0)+" published scholarships"}</p>
 {error?<ErrorState message={error} retry={()=>setRetry(v=>v+1)}/>:loading?<LoadingSkeleton/>:data?.items.length?<div className="scholarship-grid">{data.items.map(s=><article className="panel scholarship-card" key={s.id}><h2><Link href={"/scholarships/"+encodeURIComponent(s.id)}>{s.name}</Link></h2><p>{s.provider} · {s.intake_label??"Intake unknown"}</p><p>{s.coverage}</p><p>Published terms reviewed · Individual award not established</p><SaveScholarship item={s}/></article>)}</div>:<EmptyState title="No published scholarships available" description="No scholarships have passed publication approval and current human review for these filters. No sample awards or eligibility promises are shown."/>}
 {data&&!loading&&!error&&<Pagination {...data.meta} onChange={setPage}/>}</>;
}
export function ScholarshipDetail({id}: {id:string}) {
 const [item,setItem]=useState<ScholarshipV2|null>(null),[error,setError]=useState(""),[retry,setRetry]=useState(0);
 useEffect(()=>{let alive=true;const timer=setTimeout(()=>{setItem(null);setError("");scholarshipDetail(id).then(value=>{if(alive)setItem(value);}).catch(e=>{if(alive)setError(e.message);});},0);return()=>{alive=false;clearTimeout(timer);};},[id,retry]);
 return <><Link href="/scholarships">← All scholarships</Link>{error?<ErrorState message={error} retry={()=>setRetry(v=>v+1)}/>:item?<><PageHeader title={item.name} eyebrow="PUBLISHED SCHOLARSHIP TERMS" description={item.coverage}/><SaveScholarship item={item}/><ScholarshipDetails item={item}/></>:<p role="status">Loading scholarship…</p>}</>;
}
