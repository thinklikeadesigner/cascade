"use client";

import { useEffect } from "react";

export default function AnimationInit() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );

    document
      .querySelectorAll(".fade-in, .stagger-in")
      .forEach((el) => observer.observe(el));

    // Hero load animation
    requestAnimationFrame(() => {
      const hero = document.getElementById("hero");
      if (hero) hero.classList.add("loaded");
    });

    // Phone grid scroll affordance
    const phonesGrid = document.querySelector(".phones-grid");
    const phonesWrapper = document.querySelector(".phones-grid-wrapper");
    let handleScroll;
    if (phonesGrid && phonesWrapper) {
      handleScroll = () => {
        const atEnd =
          phonesGrid.scrollLeft + phonesGrid.clientWidth >=
          phonesGrid.scrollWidth - 10;
        phonesWrapper.classList.toggle("scrolled-end", atEnd);
      };
      phonesGrid.addEventListener("scroll", handleScroll);
    }

    return () => {
      observer.disconnect();
      if (phonesGrid && handleScroll) {
        phonesGrid.removeEventListener("scroll", handleScroll);
      }
    };
  }, []);

  return null;
}
