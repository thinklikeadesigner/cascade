"use client";

import { useState } from "react";

const faqData = [
  {
    q: "How is this different from Notion or a spreadsheet?",
    a: "Notion gives you a blank page. You still have to decide what goes on it, update it yourself, and remember it exists. Cascade breaks your goal into today\u2019s tasks and rewrites next week when this week doesn\u2019t go as planned.",
  },
  {
    q: "What does it cost?",
    a: "The CLI is open source and free. The hosted WhatsApp execution system is $49/month, all-in. No API keys, no setup. That\u2019s less than a single hour with a human coach ($234/hr average) for daily accountability that actually adapts to your results.",
  },
  {
    q: "What\u2019s an API key? Do I need one?",
    a: "Not for the WhatsApp agent \u2014 that\u2019s all-in at $49/month. The open source CLI version uses your own Anthropic API key (bring your own key). If you just want daily execution tracking via text, you don\u2019t need to know what an API key is.",
  },
  {
    q: "Do I need to download an app?",
    a: "No. Cascade runs in your terminal or over text messages. You text what you did, it texts back tomorrow\u2019s tasks. That\u2019s it.",
  },
  {
    q: "What kinds of goals does it work for?",
    a: "Anything that takes months and has a number attached. SaaS revenue targets, race finish times, side project launches, content milestones. If you can measure it weekly, Cascade can track it. Works best if WhatsApp is your daily driver.",
  },
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState(-1);

  return (
    <div className="faq-list fade-in">
      {faqData.map((item, i) => (
        <div
          key={i}
          className={`faq-item${openIndex === i ? " open" : ""}`}
        >
          <button
            className="faq-q"
            aria-expanded={openIndex === i}
            onClick={() => setOpenIndex(openIndex === i ? -1 : i)}
          >
            <span>{item.q}</span>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M8 3v10M3 8h10"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
          <div className="faq-a" role="region">
            <p>{item.a}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
