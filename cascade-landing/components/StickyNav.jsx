"use client";

import { useEffect, useState } from "react";

export default function StickyNav() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const hero = document.getElementById("hero");
    if (!hero) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setVisible(!entry.isIntersecting);
      },
      { threshold: 0.1 }
    );
    observer.observe(hero);
    return () => observer.disconnect();
  }, []);

  return (
    <nav className={`site-nav${visible ? " visible" : ""}`} id="site-nav">
      <div className="nav-inner">
        <a href="#hero" className="nav-logo">
          Cascade
        </a>
        <div className="nav-links">
          <a href="#model">How it works</a>
          <a href="#demo">Demo</a>
          <a href="#who">Who it&apos;s for</a>
          <a href="#final-cta" className="nav-cta">
            Get early access
          </a>
        </div>
      </div>
    </nav>
  );
}
