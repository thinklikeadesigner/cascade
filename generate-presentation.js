const pptxgen = require('pptxgenjs');
const html2pptx = require('./node_modules/office-skills/html2pptx-local.cjs');
const fs = require('fs');
const path = require('path');

// Output directory
const outDir = 'outputs/cascade-pitch-deck';
const htmlDir = path.join(outDir, 'slides');

// Create directories
if (!fs.existsSync(htmlDir)) {
  fs.mkdirSync(htmlDir, { recursive: true });
}

// Dark minimal color palette (Aer-inspired)
const colors = {
  background: '#2A2D34',
  foreground: '#FFFFFF',
  muted: '#9CA3AF',
  accent: '#F59E0B',
  line: '#4B5563'
};

// Helper to create HTML slide
function createSlide(filename, content) {
  const html = `<!DOCTYPE html>
<html>
<head>
<style>
html { background: ${colors.background}; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: ${colors.background}; font-family: Arial, sans-serif;
  color: ${colors.foreground};
  display: flex;
}
.container { margin: 36pt 60pt 50pt 60pt; width: 600pt; }
.slide-num { font-size: 14pt; color: ${colors.muted}; margin-bottom: 20pt; }
h1 { font-size: 48pt; font-weight: bold; margin: 0 0 20pt 0; color: ${colors.foreground}; }
h2 { font-size: 36pt; font-weight: bold; margin: 0 0 16pt 0; color: ${colors.foreground}; }
h3 { font-size: 28pt; font-weight: bold; margin: 16pt 0 10pt 0; color: ${colors.foreground}; }
p { font-size: 18pt; margin: 0 0 14pt 0; color: ${colors.muted}; line-height: 1.4; }
.accent { color: ${colors.accent}; }
.large { font-size: 72pt; }
.medium { font-size: 32pt; }
.bold { font-weight: bold; }
.divider { width: 100%; height: 1pt; background: ${colors.line}; margin: 20pt 0; }
.accent-line { width: 240pt; height: 2pt; background: ${colors.accent}; margin: 16pt 0; }
.row { display: flex; justify-content: space-between; margin: 16pt 0; }
.col { flex: 1; margin-right: 30pt; }
.col:last-child { margin-right: 0; }
.metric { font-size: 16pt; color: ${colors.muted}; margin-bottom: 8pt; }
.value { font-size: 36pt; font-weight: bold; color: ${colors.accent}; }
</style>
</head>
<body>
<div class="container">
${content}
</div>
</body>
</html>`;

  fs.writeFileSync(path.join(htmlDir, filename), html);
  return path.join(htmlDir, filename);
}

async function generatePresentation() {
  // Slide 1: Title
  createSlide('slide01.html', `
    <p class="slide-num">/01</p>
    <h1 class="large">Cascade</h1>
    <p style="font-size: 32pt; margin: 0;">Executive coaching</p>
    <p style="font-size: 32pt; margin: 0 0 16pt 0;">at 1/10th the price</p>
    <div class="accent-line"></div>
    <p>AI-powered career acceleration for ambitious engineers</p>
  `);

  // Slide 2: Problem
  createSlide('slide02.html', `
    <p class="slide-num">/02</p>
    <h1>The Problem</h1>
    <div class="row">
      <div class="col">
        <p style="font-size: 24pt; font-weight: bold; margin: 0; color: ${colors.foreground};">No structured execution system</p>
        <p style="font-size: 16pt; margin: 8pt 0 0 0;">Big goals but no frameworks to execute consistently</p>
      </div>
      <div class="col">
        <p style="font-size: 24pt; font-weight: bold; margin: 0; color: ${colors.foreground};">$300-500/month</p>
        <p style="font-size: 16pt; margin: 8pt 0 0 0;">Traditional coaching is expensive and doesn't scale</p>
      </div>
    </div>
    <p style="font-size: 24pt; font-weight: bold; margin: 24pt 0 0 0; color: ${colors.foreground};">No accountability</p>
    <p style="font-size: 16pt; margin: 8pt 0 0 0;">Spreadsheets provide no guidance</p>
  `);

  // Slide 3: Customer
  createSlide('slide03.html', `
    <p class="slide-num">/03</p>
    <h1>Who We Serve</h1>
    <h2 class="accent" style="font-style: italic; margin-top: 12pt;">"The Optimizer"</h2>
    <div class="accent-line"></div>
    <p style="margin-bottom: 4pt;">Engineers, designers, PMs, founders • Age 22-35 • $80k-150k+</p>
    <p style="margin-bottom: 4pt;">Tech hubs: Austin, SF, NYC, Seattle</p>
    <p style="font-size: 14pt; font-weight: bold; margin-top: 20pt;">Early Adopters</p>
    <p style="margin: 4pt 0 0 0;">Self-taught → FAANG  •  Junior → Senior  •  Career Switchers</p>
  `);

  // Slide 4: Solution
  createSlide('slide04.html', `
    <p class="slide-num">/04</p>
    <h1>The Solution</h1>
    <p style="font-size: 36pt; font-weight: bold; color: ${colors.accent}; margin: 12pt 0 0 0;">24/7 AI career coach via WhatsApp</p>
    <div class="divider"></div>
    <div class="row">
      <div class="col">
        <p class="bold" style="color: ${colors.foreground}; font-size: 18pt; margin-bottom: 8pt;">Year → Week → Day</p>
        <p style="font-size: 14pt; margin: 0;">Break yearly goals into daily tasks</p>
      </div>
      <div class="col">
        <p class="bold" style="color: ${colors.foreground}; font-size: 18pt; margin-bottom: 8pt;">Weekly check-ins</p>
        <p style="font-size: 14pt; margin: 0;">Daily summaries, calendar integration</p>
      </div>
    </div>
    <p class="bold" style="color: ${colors.foreground}; font-size: 18pt; margin: 12pt 0 6pt 0;">1000+ coaching programs</p>
    <p style="font-size: 14pt; margin: 0;">Fine-tuned on HBR, tech leader content</p>
  `);

  // Slide 5: Why We Win
  createSlide('slide05.html', `
    <p class="slide-num">/05</p>
    <h1>Why Cascade Wins</h1>
    <div style="margin-top: 30pt;">
      <div style="display: flex; margin-bottom: 12pt;">
        <p style="font-size: 20pt; font-weight: bold; width: 260pt; color: ${colors.foreground}; margin: 0;">24/7 Access</p>
        <p style="font-size: 16pt; margin: 0;">vs scheduled calls</p>
      </div>
      <div style="display: flex; margin-bottom: 12pt;">
        <p style="font-size: 20pt; font-weight: bold; width: 260pt; color: ${colors.foreground}; margin: 0;">Unlimited Scale</p>
        <p style="font-size: 16pt; margin: 0;">AI-powered, no limits</p>
      </div>
      <div style="display: flex; margin-bottom: 12pt;">
        <p style="font-size: 20pt; font-weight: bold; width: 260pt; color: ${colors.foreground}; margin: 0;">$249/month</p>
        <p style="font-size: 16pt; margin: 0;">vs $300-500 for coaches</p>
      </div>
      <div style="display: flex; margin-bottom: 12pt;">
        <p style="font-size: 20pt; font-weight: bold; width: 260pt; color: ${colors.foreground}; margin: 0;">Tech-Focused</p>
        <p style="font-size: 16pt; margin: 0;">Vertical specialization</p>
      </div>
      <div style="display: flex;">
        <p style="font-size: 20pt; font-weight: bold; width: 260pt; color: ${colors.foreground}; margin: 0;">WhatsApp Native</p>
        <p style="font-size: 16pt; margin: 0;">Daily workflow</p>
      </div>
    </div>
  `);

  // Slide 6: Revenue
  createSlide('slide06.html', `
    <p class="slide-num">/06</p>
    <h1>Revenue Model</h1>
    <div class="row" style="margin-top: 24pt;">
      <div class="col">
        <p style="font-size: 14pt; color: ${colors.muted};">Tier 1</p>
        <p style="font-size: 32pt; font-weight: bold; color: ${colors.accent}; margin: 6pt 0;">$249/month</p>
        <p style="font-size: 16pt; font-weight: bold; color: ${colors.foreground}; margin-bottom: 6pt;">Career Acceleration</p>
        <ul style="font-size: 14pt; margin: 0; padding-left: 20pt;">
          <li>FAANG interview prep</li>
          <li>Career transition guidance</li>
          <li>Weekly accountability</li>
        </ul>
      </div>
      <div class="col">
        <p style="font-size: 14pt; color: ${colors.muted};">Tier 2</p>
        <p style="font-size: 32pt; font-weight: bold; color: ${colors.foreground}; margin: 6pt 0;">$149/month</p>
        <p style="font-size: 16pt; font-weight: bold; color: ${colors.foreground}; margin-bottom: 6pt;">General Goals</p>
        <ul style="font-size: 14pt; margin: 0; padding-left: 20pt;">
          <li>Fitness, learning, projects</li>
          <li>Standard methodology</li>
          <li>Weekly check-ins</li>
        </ul>
      </div>
    </div>
    <div style="width: 100%; height: 1pt; background: ${colors.line}; margin: 12pt 0;"></div>
    <p style="font-size: 14pt; margin: 0 0 2pt 0;">88% margin  •  <$100 CAC  •  $1,500+ LTV  •  Break-even: 3-4 clients</p>
  `);

  // Slide 7: Traction
  createSlide('slide07.html', `
    <p class="slide-num">/07</p>
    <h1>Growth Roadmap</h1>
    <div style="margin-top: 20pt;">
      <div style="display: flex; align-items: center; margin-bottom: 11pt; padding-bottom: 9pt; border-bottom: 1px solid ${colors.line};">
        <p style="font-size: 15pt; width: 100pt; margin: 0;">May 2026</p>
        <p style="font-size: 24pt; font-weight: bold; width: 110pt; margin: 0; color: ${colors.foreground};">$500</p>
        <p style="font-size: 15pt; width: 50pt; margin: 0;">MRR</p>
        <p style="font-size: 15pt; margin: 0;">2-3 clients</p>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 11pt; padding-bottom: 9pt; border-bottom: 1px solid ${colors.line};">
        <p style="font-size: 15pt; width: 100pt; margin: 0;">Q3 2026</p>
        <p style="font-size: 24pt; font-weight: bold; width: 110pt; margin: 0; color: ${colors.foreground};">$1,000</p>
        <p style="font-size: 15pt; width: 50pt; margin: 0;">MRR</p>
        <p style="font-size: 15pt; margin: 0;">5-7 clients</p>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 11pt; padding-bottom: 9pt; border-bottom: 1px solid ${colors.line};">
        <p style="font-size: 15pt; width: 100pt; margin: 0;">Q4 2026</p>
        <p style="font-size: 24pt; font-weight: bold; width: 110pt; margin: 0; color: ${colors.foreground};">$2,000</p>
        <p style="font-size: 15pt; width: 50pt; margin: 0;">MRR</p>
        <p style="font-size: 15pt; margin: 0;">10-15 clients</p>
      </div>
      <div style="display: flex; align-items: center;">
        <p style="font-size: 15pt; width: 100pt; margin: 0;">2027</p>
        <p style="font-size: 24pt; font-weight: bold; width: 110pt; margin: 0; color: ${colors.accent};">$5,000</p>
        <p style="font-size: 15pt; width: 50pt; margin: 0;">MRR</p>
        <p style="font-size: 15pt; margin: 0;">20-30 clients</p>
      </div>
    </div>
  `);

  // Slide 8: Go-to-Market
  createSlide('slide08.html', `
    <p class="slide-num">/08</p>
    <h1>Go-to-Market</h1>
    <p style="font-size: 14pt; font-weight: bold; margin-top: 12pt;">Primary Channel</p>
    <p style="font-size: 26pt; font-weight: bold; color: ${colors.accent}; margin: 4pt 0;">linkt.ai</p>
    <p style="font-size: 14pt; width: 500pt; margin: 0;">Direct access to ICP - founders and ambitious engineers already seeking growth</p>
    <div style="width: 100%; height: 1pt; background: ${colors.line}; margin: 9pt 0;"></div>
    <p style="font-size: 14pt; font-weight: bold; margin: 0;">Secondary Channels</p>
    <p style="font-size: 14pt; color: ${colors.foreground}; margin-top: 5pt;">Founder Network  •  Content Marketing  •  Referrals  •  Community</p>
  `);

  // Slide 9: Unfair Advantage
  createSlide('slide09.html', `
    <p class="slide-num">/09</p>
    <h1>Unfair Advantage</h1>
    <div style="margin-top: 10pt;">
      <p style="font-size: 16pt; font-weight: bold; color: ${colors.foreground}; margin-bottom: 3pt;">Founder-Market Fit</p>
      <p style="font-size: 13pt; margin: 2pt 0 5pt 0;">Rebecca is the ICP • Self-taught → engineer → FAANG attempt</p>
      <div style="width: 100%; height: 1pt; background: ${colors.line}; margin: 6pt 0;"></div>

      <p style="font-size: 16pt; font-weight: bold; color: ${colors.foreground}; margin-bottom: 3pt;">Proprietary Dataset</p>
      <p style="font-size: 13pt; margin: 2pt 0 5pt 0;">1000+ programs scraped • Competitive intelligence data moat</p>
      <div style="width: 100%; height: 1pt; background: ${colors.line}; margin: 6pt 0;"></div>

      <p style="font-size: 16pt; font-weight: bold; color: ${colors.foreground}; margin-bottom: 3pt;">Network Effects</p>
      <p style="font-size: 13pt; margin: 2pt 0 5pt 0;">Founder community access • Active on linkt.ai • Warm pipeline</p>
      <div style="width: 100%; height: 1pt; background: ${colors.line}; margin: 6pt 0;"></div>

      <p style="font-size: 16pt; font-weight: bold; color: ${colors.foreground}; margin-bottom: 3pt;">The Google Story</p>
      <p style="font-size: 13pt; margin: 2pt 0;">"I used this to get hired" • Unbeatable social proof</p>
    </div>
  `);

  // Slide 10: Validation
  createSlide('slide10.html', `
    <p class="slide-num">/10</p>
    <h1>What We're Testing</h1>
    <p style="font-size: 14pt; font-weight: bold; margin-top: 12pt;">Riskiest Assumption</p>
    <p style="font-size: 28pt; font-weight: bold; color: ${colors.accent}; margin: 6pt 0 0 0;">Will customers pay $200+ for AI coaching?</p>
    <div style="width: 100%; height: 1pt; background: ${colors.line}; margin: 10pt 0;"></div>
    <p style="font-size: 14pt; font-weight: bold; margin-bottom: 8pt;">Validation Timeline</p>
    <div style="display: flex; margin-bottom: 7pt;">
      <p style="font-size: 14pt; font-weight: bold; color: ${colors.accent}; width: 110pt; margin: 0;">Week 1-2</p>
      <p style="font-size: 14pt; width: 330pt; margin: 0; color: ${colors.foreground};">Pre-sell 2-3 people at $249/month</p>
      <p style="font-size: 13pt; margin: 0;">→ Pricing</p>
    </div>
    <div style="display: flex; margin-bottom: 7pt;">
      <p style="font-size: 14pt; font-weight: bold; color: ${colors.accent}; width: 110pt; margin: 0;">Week 3-6</p>
      <p style="font-size: 14pt; width: 330pt; margin: 0; color: ${colors.foreground};">Run beta cohort, collect feedback</p>
      <p style="font-size: 13pt; margin: 0;">→ Product value</p>
    </div>
    <div style="display: flex;">
      <p style="font-size: 14pt; font-weight: bold; color: ${colors.accent}; width: 110pt; margin: 0;">Week 7-10</p>
      <p style="font-size: 14pt; width: 330pt; margin: 0; color: ${colors.foreground};">Track retention and engagement</p>
      <p style="font-size: 13pt; margin: 0;">→ Business model</p>
    </div>
  `);

  // Slide 11: CTA
  createSlide('slide11.html', `
    <p class="slide-num">/11</p>
    <h1 style="font-size: 56pt; margin-top: 22pt;">Let's Connect</h1>
    <div class="accent-line"></div>
    <p style="font-size: 17pt; margin: 20pt 0 3pt 0; font-weight: bold; color: ${colors.foreground};">Looking for beta testers</p>
    <p style="font-size: 15pt; margin: 0;">Ambitious engineers and founders ready to level up</p>
    <p style="font-size: 17pt; margin: 16pt 0 3pt 0; font-weight: bold; color: ${colors.foreground};">Need feedback</p>
    <p style="font-size: 15pt; margin: 0;">Pricing validation, positioning insights, PMF signals</p>
    <p style="font-size: 17pt; margin: 16pt 0 3pt 0; font-weight: bold; color: ${colors.foreground};">Value introductions</p>
    <p style="font-size: 15pt; margin: 0;">Connections to target customers in tech hubs</p>
  `);

  // Generate presentation
  console.log('Converting HTML slides to PowerPoint...');

  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = 'Cascade';
  pptx.title = 'Cascade - AI Career Coach';

  // Add all slides
  for (let i = 1; i <= 11; i++) {
    const slideNum = String(i).padStart(2, '0');
    const htmlFile = path.join(htmlDir, `slide${slideNum}.html`);
    console.log(`Processing slide ${i}...`);
    await html2pptx(htmlFile, pptx);
  }

  // Save
  const outputFile = path.join(outDir, 'Cascade-Pitch-Deck.pptx');
  await pptx.writeFile({ fileName: outputFile });
  console.log(`✅ Presentation created: ${outputFile}`);
  console.log('   - Dark minimal aesthetic (Aer-inspired)');
  console.log('   - 11 slides with proper spacing');
  console.log('   - HTML-to-PowerPoint workflow');
}

generatePresentation().catch(console.error);
