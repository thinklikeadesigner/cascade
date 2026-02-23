import AnimationInit from "@/components/AnimationInit";
import StickyNav from "@/components/StickyNav";
import FAQ from "@/components/FAQ";
import WaitlistForm from "@/components/WaitlistForm";


export default function Home() {
  return (
    <>
      <AnimationInit />
      <a href="#main-content" className="sr-only" style={{position:"absolute",top:0,left:0,padding:"8px 16px",background:"var(--accent)",color:"#fff",zIndex:200}}>Skip to content</a>
      <StickyNav />

      {/* HERO */}
      <section className="hero" id="hero">
        <svg className="hero-dot-grid" aria-hidden="true">
          <defs>
            <pattern id="dotgrid" x="0" y="0" width="32" height="32" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="0.8" fill="#64748B" />
            </pattern>
            <radialGradient id="herofade" cx="50%" cy="45%" r="50%">
              <stop offset="0%" stopColor="#EF4444" stopOpacity="0.08" />
              <stop offset="100%" stopColor="#0D0B0E" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect width="100%" height="100%" fill="url(#dotgrid)" />
          <rect width="100%" height="100%" fill="url(#herofade)" />
        </svg>

        <div className="container">
          <div className="hero-split">
            {/* LEFT: Copy */}
            <div className="hero-copy fade-in">
              <svg className="hero-logo" viewBox="0 0 200 240" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Cascade logo">
                <path d="M40 20 L100 50 L160 20" stroke="#EF4444" strokeWidth="3.5" fill="none" strokeLinecap="round" style={{filter: "drop-shadow(0 0 8px rgba(248,113,113,0.2))"}} />
                <path d="M52 65 L100 90 L148 65" stroke="#EF4444" strokeWidth="3" fill="none" strokeLinecap="round" style={{filter: "drop-shadow(0 0 8px rgba(248,113,113,0.2))"}} />
                <path d="M62 108 L100 128 L138 108" stroke="#EF4444" strokeWidth="2.5" fill="none" strokeLinecap="round" style={{filter: "drop-shadow(0 0 8px rgba(248,113,113,0.2))"}} />
                <path d="M72 148 L100 164 L128 148" stroke="#EF4444" strokeWidth="2" fill="none" strokeLinecap="round" style={{filter: "drop-shadow(0 0 8px rgba(248,113,113,0.2))"}} />
                <path d="M80 186 L100 198 L120 186" stroke="#EF4444" strokeWidth="1.5" fill="none" strokeLinecap="round" style={{filter: "drop-shadow(0 0 8px rgba(248,113,113,0.2))"}} />
                <circle cx="100" cy="225" r="4" fill="#F87171" />
                <circle cx="100" cy="225" r="12" fill="#F87171" />
              </svg>
              <h1>Your yearly goals die by March. Cascade makes them <span className="accent">survive.</span></h1>
              <p className="hero-sub">Text your goal. Get today{"\u2019"}s action. Cascade watches what you actually do and rewrites next week{"\u2019"}s plan based on this week{"\u2019"}s results.</p>
              <WaitlistForm id="hero">
                <div className="social-proof">
                  <a href="https://github.com/thinklikeadesigner/cascade" target="_blank" rel="noopener noreferrer" className="proof-badge">
                    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
                    Open source
                  </a>
                  <a href="https://www.indiehackers.com/rebeccabuilds" target="_blank" rel="noopener noreferrer" className="proof-badge">
                    Built by @rebeccabuilds
                  </a>
                </div>
              </WaitlistForm>
            </div>

            {/* RIGHT: Phone mockup */}
            <div className="hero-phone fade-in" role="img" aria-label="Phone showing a conversation with Cascade about setting a $5k MRR goal">
              <div className="phone-frame" aria-hidden="true">
                <div className="phone-island"></div>
                <div className="phone-statusbar">
                  <span className="phone-time">9:41</span>
                  <div className="phone-icons">
                    <svg width="13" height="10" viewBox="0 0 16 12"><rect x="0" y="5" width="3" height="7" rx=".5" fill="#F8FAFC" opacity=".4"/><rect x="4.5" y="3" width="3" height="9" rx=".5" fill="#F8FAFC" opacity=".6"/><rect x="9" y="1" width="3" height="11" rx=".5" fill="#F8FAFC" opacity=".8"/><rect x="13" y="0" width="3" height="12" rx=".5" fill="#F8FAFC"/></svg>
                    <svg width="18" height="10" viewBox="0 0 22 12"><rect x="0" y="1" width="18" height="10" rx="2" stroke="#F8FAFC" strokeWidth="1" fill="none"/><rect x="2" y="3" width="13" height="6" rx="1" fill="#22C55E"/><rect x="19" y="4" width="2" height="4" rx="1" fill="#F8FAFC" opacity=".4"/></svg>
                  </div>
                </div>
                <div className="phone-header">
                  <svg width="8" height="13" viewBox="0 0 10 16"><path d="M8 2L2 8L8 14" stroke="#EF4444" strokeWidth="2" fill="none" strokeLinecap="round"/></svg>
                  <div className="phone-avatar">
                    <svg width="14" height="14" viewBox="0 0 280 280" fill="none"><path d="M90 65 L140 90 L190 65" stroke="#EF4444" strokeWidth="5" fill="none" strokeLinecap="round"/><path d="M104 115 L140 135 L176 115" stroke="#EF4444" strokeWidth="4" fill="none" strokeLinecap="round" opacity=".6"/><path d="M116 160 L140 174 L164 160" stroke="#EF4444" strokeWidth="3" fill="none" strokeLinecap="round" opacity=".3"/><circle cx="140" cy="210" r="6" fill="#F87171" opacity=".5"/></svg>
                  </div>
                  <span className="phone-name">Cascade</span>
                </div>
                <div className="phone-msgs">
                  <div className="msg-t">Sunday 8:15 PM</div>
                  <div className="msg-u"><div>i want to hit $5k MRR by end of year with my saas</div></div>
                  <div className="msg-c"><div>Good. What{"\u2019"}s the product, and where are you now?</div></div>
                  <div className="msg-u"><div>project management tool for freelancers. $200 MRR, 12 paying users</div></div>
                  <div className="msg-c"><div>$200 to $5k MRR. That{"\u2019"}s 25x in 10 months. Aggressive but doable.</div></div>
                  <div className="msg-c"><div>
                    <div className="msg-box-label">Your cascade:</div>
                    <div className="msg-box">
                      <div className="msg-row"><span className="msg-row-icon">{"\u25CE"}</span><span className="msg-row-text">Build a profitable solo business</span></div>
                      <div className="msg-row" style={{paddingLeft: 10}}><span className="msg-row-icon" style={{opacity: 0.9}}>{"\u25C9"}</span><span className="msg-row-text" style={{opacity: 0.9}}>2025: $5k MRR by December</span></div>
                      <div className="msg-row" style={{paddingLeft: 20}}><span className="msg-row-icon" style={{opacity: 0.8}}>Q1</span><span className="msg-row-text" style={{opacity: 0.8}}>Fix retention + find a channel</span></div>
                      <div className="msg-row" style={{paddingLeft: 20}}><span className="msg-row-icon" style={{opacity: 0.7}}>Q2</span><span className="msg-row-text" style={{opacity: 0.7}}>Double down. Hit $1k MRR</span></div>
                    </div>
                  </div></div>
                  <div className="msg-u"><div>yes do it</div></div>
                  <div className="msg-c"><div>Done. I{"\u2019"}ll text you every morning with today{"\u2019"}s tasks. Nothing random.</div></div>
                </div>
                <div className="phone-input">
                  <div className="phone-input-row">
                    <span className="phone-input-text">Text Cascade...</span>
                    <div className="phone-send"><svg width="11" height="11" viewBox="0 0 14 14"><path d="M2 12L12 7L2 2V5.5L8 7L2 8.5V12Z" fill="#fff"/></svg></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Mobile scroll cue */}
          <div className="scroll-cue">
            <span>Scroll</span>
            <svg width="16" height="10" viewBox="0 0 16 10" fill="none">
              <path d="M2 2L8 8L14 2" stroke="#7C8DA2" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
        </div>
      </section>

      {/* PROBLEM */}
      <section className="problem" id="main-content">
        <div className="container">
          <p className="section-label fade-in">The Problem</p>
          <div className="fade-in">
            <p className="pain-point">Every January you open a doc and write three bullet points. By March the doc is buried and the goal is dead.</p>
          </div>
          <div className="fade-in">
            <p className="pain-point">Habit trackers feel productive. But checking boxes doesn{"\u2019"}t get you closer to the goal you actually care about.</p>
          </div>
          <div className="fade-in">
            <p className="pain-point">You fall behind for two weeks and the whole plan feels broken. So you abandon it and start over in Q3. Again.</p>
          </div>
        </div>
      </section>

      {/* BEFORE / AFTER */}
      <section className="before-after">
        <div className="container">
          <p className="section-label fade-in">The Difference</p>
          <div className="ba-grid fade-in">
            {/* BEFORE */}
            <div className="ba-panel ba-before">
              <p className="ba-label">Without Cascade</p>
              <div>
                <div className="scattered-task" style={{marginLeft: "10%"}}>Run more??</div>
                <div className="scattered-task" style={{marginLeft: "42%"}}>Swim 2x/week</div>
                <div className="scattered-task" style={{marginLeft: "5%"}}>Do a century ride somehow</div>
                <div className="scattered-task" style={{marginLeft: "48%"}}>Brick workout?</div>
                <div className="scattered-task" style={{marginLeft: "12%"}}>Fix nutrition</div>
                <div className="scattered-task" style={{marginLeft: "38%"}}>Sign up for a race</div>
                <div className="scattered-task struck" style={{marginLeft: "6%", opacity: 0.5}}>Stretch more</div>
              </div>
              <p className="ba-punchline-bad">Scattered goals. Dead by March.</p>
            </div>

            {/* AFTER */}
            <div className="ba-panel ba-after">
              <p className="ba-label">With Cascade</p>
              <div>
                <div className="structured-item" style={{marginLeft: 0}}>
                  <span className="structured-label" style={{opacity: 0.5}}>Vision</span>
                  <span className="structured-dot" style={{opacity: 0.5}}></span>
                  <span className="structured-text" style={{opacity: 0.5}}>Finish an Ironman</span>
                </div>
                <div className="structured-item" style={{marginLeft: 8}}>
                  <span className="structured-label" style={{opacity: 0.6}}>Year</span>
                  <span className="structured-dot" style={{opacity: 0.6}}></span>
                  <span className="structured-text" style={{opacity: 0.6}}>Ironman 70.3 in October</span>
                </div>
                <div className="structured-item" style={{marginLeft: 16}}>
                  <span className="structured-label" style={{opacity: 0.7}}>Q1</span>
                  <span className="structured-dot" style={{opacity: 0.7}}></span>
                  <span className="structured-text" style={{opacity: 0.7}}>Build aerobic base, swim technique</span>
                </div>
                <div className="structured-item" style={{marginLeft: 24}}>
                  <span className="structured-label" style={{opacity: 0.8}}>Jan</span>
                  <span className="structured-dot" style={{opacity: 0.8}}></span>
                  <span className="structured-text" style={{opacity: 0.8}}>3 swims/week, long ride Saturdays</span>
                </div>
                <div className="structured-item" style={{marginLeft: 32}}>
                  <span className="structured-label" style={{opacity: 0.9}}>This week</span>
                  <span className="structured-dot" style={{opacity: 0.9}}></span>
                  <span className="structured-text" style={{opacity: 0.9}}>Swim 3x, 40mi ride, 2 easy runs</span>
                </div>
                <div className="structured-item" style={{marginLeft: 40}}>
                  <span className="structured-label">Today</span>
                  <span className="structured-dot active"></span>
                  <span className="structured-text">1500m swim + 20min brick run</span>
                </div>
              </div>
              <p className="ba-punchline-good">Today{"\u2019"}s work traces back to the yearly goal.</p>
            </div>
          </div>
        </div>
      </section>

      {/* HOW YOU USE IT */}
      <section className="steps" id="model">
        <div className="container">
          <p className="section-label fade-in">How It Works</p>
          <div className="steps-grid stagger-in">
            <div className="step">
              <div className="step-num">1</div>
              <div className="step-title">Text your goal</div>
              <div className="step-desc">Tell Cascade your goal and your deadline. It breaks that down into what you should do this week and today.</div>
            </div>
            <div className="step">
              <div className="step-num">2</div>
              <div className="step-title">Get daily actions</div>
              <div className="step-desc">Every morning you get a text with today{"\u2019"}s tasks. They all connect to your yearly goal, no busywork.</div>
            </div>
            <div className="step">
              <div className="step-num">3</div>
              <div className="step-title">Text back when done</div>
              <div className="step-desc">Log progress by texting. Cascade sees what{"\u2019"}s working, what{"\u2019"}s not, and adjusts next week{"\u2019"}s plan.</div>
            </div>
          </div>
        </div>
      </section>

      {/* ANTI-APP */}
      <section className="anti-app">
        <div className="container">
          <div className="fade-in">
            <p className="anti-app-headline">No app. No dashboard. <span className="accent">No login.</span></p>
            <p className="anti-app-body">You already have 14 tabs open and 6 productivity apps you don{"\u2019"}t use. Cascade lives in the app you check 100 times a day. Your texts.</p>
            <div className="anti-app-stats">
              <div className="anti-app-stat">
                <div className="anti-app-stat-num">98%</div>
                <div className="anti-app-stat-label">text open rate</div>
              </div>
              <div className="anti-app-stat">
                <div className="anti-app-stat-num">3 min</div>
                <div className="anti-app-stat-label">avg response time</div>
              </div>
              <div className="anti-app-stat">
                <div className="anti-app-stat-num">0</div>
                <div className="anti-app-stat-label">apps to download</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* MID CTA */}
      <section className="mid-cta">
        <div className="container fade-in">
          <p>First 100 users shape the product.</p>
          <a href="#final-cta" className="btn">Get early access</a>
        </div>
      </section>

      {/* UNDER THE HOOD */}
      <section className="model">
        <div className="container">
          <p className="section-label fade-in">Under The Hood</p>
          <div className="cascade-stack stagger-in">
            {/* Level 1 */}
            <div style={{width: "100%", maxWidth: 600}}>
              <div className="cascade-node" style={{width: "100%"}}>
                <span className="cascade-node-label">Life Vision</span>
                <span className="cascade-node-example">{"\u201C"}Build AI products, not just prototypes{"\u201D"}</span>
              </div>
            </div>

            {/* Connector */}
            <div className="cascade-connector">
              <svg width="2" height="20"><line x1="1" y1="0" x2="1" y2="20" stroke="#EF4444" strokeWidth="1" opacity="0.35" strokeDasharray="3 3" /></svg>
            </div>

            {/* Level 2 */}
            <div style={{width: "88%", maxWidth: 528}}>
              <div className="cascade-node" style={{width: "100%"}}>
                <span className="cascade-node-label">Yearly Goal</span>
                <span className="cascade-node-example">{"\u201C"}Ship 3 production AI features by December{"\u201D"}</span>
              </div>
            </div>

            <div className="cascade-connector">
              <svg width="2" height="20"><line x1="1" y1="0" x2="1" y2="20" stroke="#EF4444" strokeWidth="1" opacity="0.3" strokeDasharray="3 3" /></svg>
            </div>

            {/* Level 3 */}
            <div style={{width: "76%", maxWidth: 456}}>
              <div className="cascade-node" style={{width: "100%"}}>
                <span className="cascade-node-label">Quarterly Focus</span>
                <span className="cascade-node-example">{"\u201C"}RAG pipeline + eval framework{"\u201D"}</span>
              </div>
            </div>

            <div className="cascade-connector">
              <svg width="2" height="20"><line x1="1" y1="0" x2="1" y2="20" stroke="#EF4444" strokeWidth="1" opacity="0.25" strokeDasharray="3 3" /></svg>
            </div>

            {/* Level 4 */}
            <div style={{width: "64%", maxWidth: 384}}>
              <div className="cascade-node" style={{width: "100%"}}>
                <span className="cascade-node-label">Monthly Theme</span>
                <span className="cascade-node-example">{"\u201C"}Build retrieval layer + benchmark accuracy{"\u201D"}</span>
              </div>
            </div>

            <div className="cascade-connector">
              <svg width="2" height="20"><line x1="1" y1="0" x2="1" y2="20" stroke="#EF4444" strokeWidth="1" opacity="0.2" strokeDasharray="3 3" /></svg>
            </div>

            {/* Level 5 */}
            <div style={{width: "52%", maxWidth: 312}}>
              <div className="cascade-node" style={{width: "100%"}}>
                <span className="cascade-node-label">Weekly Plan</span>
                <span className="cascade-node-example">{"\u201C"}Chunk strategy tests, deploy v1 to staging{"\u201D"}</span>
              </div>
            </div>

            <div className="cascade-connector">
              <svg width="2" height="20"><line x1="1" y1="0" x2="1" y2="20" stroke="#EF4444" strokeWidth="1" opacity="0.15" strokeDasharray="3 3" /></svg>
            </div>

            {/* Level 6 (active) */}
            <div style={{width: "40%", maxWidth: 240}}>
              <div className="cascade-node active" style={{width: "100%"}}>
                <span className="cascade-node-label">Daily Action</span>
                <span className="cascade-node-example">{"\u201C"}Test 3 chunk sizes, log recall scores{"\u201D"}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* PRODUCT DEMO */}
      <section className="demo" id="demo">
        <div className="demo-inner">
          <p className="section-label fade-in">A Day With Cascade</p>
          <p className="demo-sub fade-in">Your goals, broken down to today{"\u2019"}s tasks. Delivered by text.</p>
          <div className="phones-grid-wrapper">
          <div className="phones-grid fade-in">

            {/* Phone 1: Morning Check-in */}
            <div className="phone-wrapper" role="img" aria-label="Phone showing Cascade sending morning tasks and tracking completion via text">
              <div className="phone-frame" aria-hidden="true">
                <div className="phone-island"></div>
                <div className="phone-statusbar">
                  <span className="phone-time">9:41</span>
                  <div className="phone-icons">
                    <svg width="13" height="10" viewBox="0 0 16 12"><rect x="0" y="5" width="3" height="7" rx=".5" fill="#F8FAFC" opacity=".4"/><rect x="4.5" y="3" width="3" height="9" rx=".5" fill="#F8FAFC" opacity=".6"/><rect x="9" y="1" width="3" height="11" rx=".5" fill="#F8FAFC" opacity=".8"/><rect x="13" y="0" width="3" height="12" rx=".5" fill="#F8FAFC"/></svg>
                    <svg width="18" height="10" viewBox="0 0 22 12"><rect x="0" y="1" width="18" height="10" rx="2" stroke="#F8FAFC" strokeWidth="1" fill="none"/><rect x="2" y="3" width="13" height="6" rx="1" fill="#22C55E"/><rect x="19" y="4" width="2" height="4" rx="1" fill="#F8FAFC" opacity=".4"/></svg>
                  </div>
                </div>
                <div className="phone-header">
                  <svg width="8" height="13" viewBox="0 0 10 16"><path d="M8 2L2 8L8 14" stroke="#EF4444" strokeWidth="2" fill="none" strokeLinecap="round"/></svg>
                  <div className="phone-avatar">
                    <svg width="14" height="14" viewBox="0 0 280 280" fill="none"><path d="M90 65 L140 90 L190 65" stroke="#EF4444" strokeWidth="5" fill="none" strokeLinecap="round"/><path d="M104 115 L140 135 L176 115" stroke="#EF4444" strokeWidth="4" fill="none" strokeLinecap="round" opacity=".6"/><path d="M116 160 L140 174 L164 160" stroke="#EF4444" strokeWidth="3" fill="none" strokeLinecap="round" opacity=".3"/><circle cx="140" cy="210" r="6" fill="#F87171" opacity=".5"/></svg>
                  </div>
                  <span className="phone-name">Cascade</span>
                </div>
                <div className="phone-msgs">
                  <div className="msg-t">Today 7:02 AM</div>
                  <div className="msg-c"><div>Morning. Here{"\u2019"}s your cascade for today.</div></div>
                  <div className="msg-c"><div>
                    <div className="msg-box">
                      <div className="msg-row"><span className="msg-row-icon" style={{opacity: 0.4}}>{"\u25CE"}</span><span className="msg-row-text dim" style={{opacity: 0.4}}>$5k MRR by December</span></div>
                      <div className="msg-row" style={{paddingLeft: 10}}><span className="msg-row-icon" style={{opacity: 0.5}}>{"\u25B8"}</span><span className="msg-row-text dim" style={{opacity: 0.5}}>Q1: Fix retention + find a channel</span></div>
                      <div className="msg-row" style={{paddingLeft: 20}}><span className="msg-row-icon" style={{opacity: 0.7}}>{"\u25B8"}</span><span className="msg-row-text" style={{opacity: 0.7}}>Feb: Customer research + ship top feature</span></div>
                      <div className="msg-row" style={{paddingLeft: 30}}><span className="msg-row-icon" style={{color: "#EF4444"}}>{"\u25B9"}</span><span className="msg-row-text" style={{color: "#EF4444"}}>Week 2, Day 3</span></div>
                    </div>
                  </div></div>
                  <div className="msg-c"><div>
                    <div className="msg-box-label">Today{"\u2019"}s actions:</div>
                    <div className="msg-box" style={{gap: 3}}>
                      <div className="msg-task"><div className="msg-chk"></div><span className="msg-task-label">Email 3 churned users for exit interviews (20m)</span></div>
                      <div className="msg-task"><div className="msg-chk"></div><span className="msg-task-label">Ship calendar view MVP to staging (90m)</span></div>
                      <div className="msg-task"><div className="msg-chk"></div><span className="msg-task-label">Write + schedule 2 posts for IH (30m)</span></div>
                      <div className="msg-task"><div className="msg-chk"></div><span className="msg-task-label">Reply to all open support tickets (15m)</span></div>
                      <div className="msg-sep">~2h 35m total {"\u00B7"} revenue actions first</div>
                    </div>
                  </div></div>
                  <div className="msg-c"><div>Customer interviews matter most today. Start there.</div></div>
                  <div className="msg-u"><div>emails sent. one already replied, wants to jump on a call tomorrow</div></div>
                  <div className="msg-c"><div>Nice. Logged it. Book that call first thing.</div></div>
                  <div className="msg-c"><div>
                    <div className="msg-box" style={{gap: 3}}>
                      <div className="msg-task">
                        <div className="msg-chk-done"><svg width="7" height="7" viewBox="0 0 10 10"><path d="M2 5.5L4 7.5L8 3" stroke="#22C55E" strokeWidth="1.5" fill="none" strokeLinecap="round"/></svg></div>
                        <span className="msg-task-label struck">Email 3 churned users</span>
                        <span className="msg-done-tag">done</span>
                      </div>
                      <div className="msg-sep">3 remaining today {"\u00B7"} 6/10 user interviews this month</div>
                    </div>
                  </div></div>
                  <div className="msg-c"><div>Next: ship that calendar view. That{"\u2019"}s the feature 4 users asked for. Go build.</div></div>
                </div>
                <div className="phone-input">
                  <div className="phone-input-row">
                    <span className="phone-input-text">Text Cascade...</span>
                    <div className="phone-send"><svg width="11" height="11" viewBox="0 0 14 14"><path d="M2 12L12 7L2 2V5.5L8 7L2 8.5V12Z" fill="#fff"/></svg></div>
                  </div>
                </div>
              </div>
              <span className="phone-label">Daily execution</span>
            </div>

            {/* Phone 3: Accountability Nudge */}
            <div className="phone-wrapper" role="img" aria-label="Phone showing Cascade giving honest feedback when you get off track">
              <div className="phone-frame" aria-hidden="true">
                <div className="phone-island"></div>
                <div className="phone-statusbar">
                  <span className="phone-time">9:41</span>
                  <div className="phone-icons">
                    <svg width="13" height="10" viewBox="0 0 16 12"><rect x="0" y="5" width="3" height="7" rx=".5" fill="#F8FAFC" opacity=".4"/><rect x="4.5" y="3" width="3" height="9" rx=".5" fill="#F8FAFC" opacity=".6"/><rect x="9" y="1" width="3" height="11" rx=".5" fill="#F8FAFC" opacity=".8"/><rect x="13" y="0" width="3" height="12" rx=".5" fill="#F8FAFC"/></svg>
                    <svg width="18" height="10" viewBox="0 0 22 12"><rect x="0" y="1" width="18" height="10" rx="2" stroke="#F8FAFC" strokeWidth="1" fill="none"/><rect x="2" y="3" width="13" height="6" rx="1" fill="#22C55E"/><rect x="19" y="4" width="2" height="4" rx="1" fill="#F8FAFC" opacity=".4"/></svg>
                  </div>
                </div>
                <div className="phone-header">
                  <svg width="8" height="13" viewBox="0 0 10 16"><path d="M8 2L2 8L8 14" stroke="#EF4444" strokeWidth="2" fill="none" strokeLinecap="round"/></svg>
                  <div className="phone-avatar">
                    <svg width="14" height="14" viewBox="0 0 280 280" fill="none"><path d="M90 65 L140 90 L190 65" stroke="#EF4444" strokeWidth="5" fill="none" strokeLinecap="round"/><path d="M104 115 L140 135 L176 115" stroke="#EF4444" strokeWidth="4" fill="none" strokeLinecap="round" opacity=".6"/><path d="M116 160 L140 174 L164 160" stroke="#EF4444" strokeWidth="3" fill="none" strokeLinecap="round" opacity=".3"/><circle cx="140" cy="210" r="6" fill="#F87171" opacity=".5"/></svg>
                  </div>
                  <span className="phone-name">Cascade</span>
                </div>
                <div className="phone-msgs">
                  <div className="msg-t">Thursday 6:48 PM</div>
                  <div className="msg-c"><div>Checking in. You had 4 tasks today. I{"\u2019"}m seeing one completion. What happened?</div></div>
                  <div className="msg-u"><div>got sucked into redesigning the landing page all day. it looks way better though</div></div>
                  <div className="msg-c"><div>I hear you. But let{"\u2019"}s look at where that sits in your cascade.</div></div>
                  <div className="msg-c"><div>
                    <div className="msg-box">
                      <div className="msg-prio">PRIORITY CHECK</div>
                      <div className="msg-prog">
                        <div className="msg-prog-head"><span className="msg-prog-name">Churn interviews</span><span className="msg-prog-val" style={{color: "#EF4444"}}>6/10</span></div>
                        <div className="msg-prog-bar"><div className="msg-prog-fill" style={{width: "60%", background: "#EF4444"}}></div></div>
                      </div>
                      <div className="msg-prog">
                        <div className="msg-prog-head"><span className="msg-prog-name">Calendar view</span><span className="msg-prog-val" style={{color: "#FACC15"}}>70%</span></div>
                        <div className="msg-prog-bar"><div className="msg-prog-fill" style={{width: "70%", background: "#FACC15"}}></div></div>
                      </div>
                      <div className="msg-prog">
                        <div className="msg-prog-head"><span className="msg-prog-name">IH posts this week</span><span className="msg-prog-val" style={{color: "#EF4444"}}>1/4</span></div>
                        <div className="msg-prog-bar"><div className="msg-prog-fill" style={{width: "25%", background: "#EF4444"}}></div></div>
                      </div>
                    </div>
                  </div></div>
                  <div className="msg-c"><div>Landing page redesign isn{"\u2019"}t on your cascade right now. Your Q1 goal is retention and finding a channel. A prettier page doesn{"\u2019"}t fix churn.</div></div>
                  <div className="msg-c"><div>Not saying the redesign was useless. But tomorrow, can we get back to what moves the $5k number?</div></div>
                  <div className="msg-u"><div>you{"\u2019"}re right. i was avoiding the hard stuff</div></div>
                  <div className="msg-c"><div>Respect. I{"\u2019"}ll queue tomorrow around the calendar view and that user call. Get some rest.</div></div>
                  <div className="msg-t">Friday 7:01 AM</div>
                  <div className="msg-c"><div>New day. Here{"\u2019"}s what matters today.</div></div>
                </div>
                <div className="phone-input">
                  <div className="phone-input-row">
                    <span className="phone-input-text">Text Cascade...</span>
                    <div className="phone-send"><svg width="11" height="11" viewBox="0 0 14 14"><path d="M2 12L12 7L2 2V5.5L8 7L2 8.5V12Z" fill="#fff"/></svg></div>
                  </div>
                </div>
              </div>
              <span className="phone-label">Stay on track</span>
            </div>

          </div>
          </div>
          <p className="demo-bottom fade-in">It{"\u2019"}s just text messages. No app, no dashboard.</p>
        </div>
      </section>

      {/* Try It CTA */}
      <section className="try-cta">
        <div className="container fade-in" style={{textAlign: "center"}}>
          <p className="section-label">Try It Yourself</p>
          <p style={{color: "var(--text-secondary)", fontSize: "1rem", marginBottom: 32}}>
            Type a goal and watch Cascade break it into an execution plan.
          </p>
          <a href="/try" className="btn">Try the demo</a>
        </div>
      </section>

      {/* VALUE PROPS */}
      <section className="value-props">
        <div className="container">
          <p className="section-label fade-in">Why It Works</p>
          <div className="value-grid stagger-in">
            <div className="value-card">
              <div className="value-number">6</div>
              <div className="value-label">connected levels</div>
              <div className="value-sub">Your yearly goal becomes today{"\u2019"}s checklist</div>
            </div>
            <div className="value-card">
              <div className="value-number">{"\u221E"}</div>
              <div className="value-label">adapts weekly</div>
              <div className="value-sub">Next week{"\u2019"}s plan is built from this week{"\u2019"}s results</div>
            </div>
            <div className="value-card">
              <div className="value-number">{"</>"}</div>
              <div className="value-label">open source</div>
              <div className="value-sub">Inspect every line on GitHub</div>
            </div>
          </div>
        </div>
      </section>

      {/* WHO IT'S FOR */}
      <section className="who" id="who">
        <div className="container">
          <p className="section-label fade-in">Who This Is For</p>
          <div className="persona-grid stagger-in">
            <div className="persona">
              <div className="persona-icon">$</div>
              <h3>Founders chasing revenue</h3>
              <p>No co-founder, no board, no accountability. Cascade is the structure between your $200 MRR and your $5K goal.</p>
              <p className="persona-goal">{"\u201C"}$5K MRR by December{"\u201D"}</p>
            </div>
            <div className="persona">
              <div className="persona-icon">//</div>
              <h3>Athletes training for a race</h3>
              <p>Race day doesn{"\u2019"}t move. Your training plan cascades from finish line to today{"\u2019"}s workout.</p>
              <p className="persona-goal">{"\u201C"}Ironman 70.3 in October{"\u201D"}</p>
            </div>
            <div className="persona">
              <div className="persona-icon">{"{}"}</div>
              <h3>Builders shipping projects</h3>
              <p>You have the idea and the skills. You need daily structure to actually ship it, week after week.</p>
              <p className="persona-goal">{"\u201C"}Launch on Product Hunt by March{"\u201D"}</p>
            </div>
          </div>
        </div>
      </section>

      {/* PHILOSOPHY */}
      <section className="philosophy">
        <div className="container">
          <p className="section-label fade-in">What Makes This Different</p>
          <blockquote className="fade-in">
            Your to-do list doesn{"\u2019"}t know about your yearly goal. Your yearly goal doesn{"\u2019"}t know what you did today. Cascade is the <span className="accent">thing in between</span>.
          </blockquote>
          <div className="philosophy-points fade-in">
            <div className="philosophy-point">
              <h4>Execution</h4>
              <p>You don{"\u2019"}t need another plan. You need today{"\u2019"}s three tasks and a reason each one matters.</p>
            </div>
            <div className="philosophy-point">
              <h4>Honesty</h4>
              <p>Cascade tells you when you{"\u2019"}re behind. It won{"\u2019"}t sugarcoat a 40% week.</p>
            </div>
            <div className="philosophy-point">
              <h4>Adaptation</h4>
              <p>Had a bad week? Cool, next week{"\u2019"}s plan accounts for it. The system bends so you don{"\u2019"}t break.</p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="faq">
        <div className="container">
          <p className="section-label fade-in">Questions</p>
          <FAQ />
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="final-cta" id="final-cta">
        <div className="container">
          <h2 className="fade-in">Your goals shouldn{"\u2019"}t die in a Google Doc.</h2>
          <p className="sub fade-in">First 100 users shape what this becomes.</p>
          <WaitlistForm id="final">
            <div className="social-proof" style={{marginTop: 16}}>
              <a href="https://github.com/thinklikeadesigner/cascade" target="_blank" rel="noopener noreferrer" className="proof-badge">
                <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
                Open source
              </a>
              <a href="https://www.indiehackers.com/rebeccabuilds" target="_blank" rel="noopener noreferrer" className="proof-badge">
                Built by @rebeccabuilds
              </a>
            </div>
          </WaitlistForm>
        </div>
      </section>

      {/* FOOTER */}
      <footer>
        <div className="container">
          <p>built by <a href="https://www.indiehackers.com/rebeccabuilds" target="_blank" rel="noopener noreferrer">rebeccabuilds</a></p>
        </div>
      </footer>
    </>
  );
}
