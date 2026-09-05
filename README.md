<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,100:6366f1&height=220&section=header&text=Hi,%20I'm%20Ali%20👋&fontSize=48&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=BSCS%20Student%20%7C%20Aspiring%20Software%20Developer&descAlignY=55&descSize=18" width="100%"/>

</div>

<div align="center">
  
[![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=24&pause=1000&color=6366F1&center=true&vCenter=true&width=600&lines=3rd+Year+BSCS+Student+%40+PUP;Building+with+React+Native+%2B+TypeScript;Into+Networking%2C+Algorithms+%26+Databases;Open+to+Internships+%2F+Entry-Level+Remote+Roles)](https://git.io/typing-svg)

</div>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Location-San%20Jose%20del%20Monte%2C%20Bulacan-6366f1?style=for-the-badge&logo=googlemaps&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/University-PUP%20BSCS-0f172a?style=for-the-badge&logo=googlescholar&logoColor=white"/></a>
  <a href="#"><img src="https://img.shields.io/badge/Status-Open%20to%20Work-22c55e?style=for-the-badge&logo=indeed&logoColor=white"/></a>
</p>

---

### 🚀 About Me

```yaml
name: Ali
role: BSCS Student (Section 2-4) @ Polytechnic University of the Philippines
track: COSC
currently:
  - 📚 Balancing a heavy courseload while shipping side projects
  - 🛠️ Building BayaniRemit — a remittance & household budget tracker
  - 🕸️ Built NetForge — a mobile network topology simulator (6 graph algos!)
  - 💼 Exploring remote internships & entry-level dev roles
looking_for: "Internship / entry-level opportunities in software dev or IT"
fun_fact: "I like breaking things apart (pentesting/reversing) as much as building them"
```

---

### 🧰 Tech Stack

<div align="center">

<img src="https://skillicons.dev/icons?i=react,ts,py,postgres,mysql,linux,git,github,vscode,figma&theme=dark" />

</div>

<br/>

<div align="center">

![React Native](https://img.shields.io/badge/React_Native-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-005C84?style=for-the-badge&logo=mysql&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Cisco Packet Tracer](https://img.shields.io/badge/Packet_Tracer-1BA0D7?style=for-the-badge&logo=cisco&logoColor=white)

</div>

---

### 🌟 Featured Projects

<details open>
<summary><b>🌊 LIGTAS METRO — Flood-Aware Commute Radar</b></summary>
<br/>

Metro Manila's roads flood in minutes during Habagat/typhoon season, and apps like Google Maps or Waze just show a generic "slow" — no water depth, no clearance risk. **LIGTAS METRO** fixes that with real ground-truth data:

- 📸 **Dual-mode ground-truth inspection** — real 360° Mapillary street imagery near vulnerable corridors; if no recent photo exists nearby, it honestly falls back to hydrological sensor data instead of faking it
- 🌧️ **Hydrological telemetry** — live river basin data from Marikina River (Sto. Niño Station), Manggahan Floodway, and Pasig River, plus 6-hour rainfall sparklines
- 🚗 **Vehicle-specific passability matrix** — separate safety thresholds for sedans, high-axle/4x4s, and pedestrians based on actual water depth
- 🗺️ **MapLibre GL vector radar** — real-time flood polygons and safe detours, geocoded via OSM Nominatim (Philippines-bounded)
- 🎨 High-contrast editorial design (`#FFE142` clay-gold on `#000000`) built for readability in low-light, wet conditions

`React 19` · `Vite` · `Tailwind CSS` · `MapLibre GL` · `Mapillary JS API v4` · `Lucide React` · `OSM Nominatim`

</details>

<details>
<summary><b>🚌 PARA PO! — NCR Commute & PUV Transit Guide</b></summary>
<br/>

Google Maps and Waze fall apart on Philippine public transit — jeepneys, UV Express, tricycles, the Carousel, LRT/MRT/PNR — because commuters describe routes in casual Taglish and landmarks, not station names. **PARA PO!** treats Taglish as a first-class citizen:

- 💬 **Conversational route extraction** — type or speak a natural Taglish query (e.g. *"Mula Monumento paano pumunta ng BGC via carousel?"*); a multi-model Gemini cascade structures it into fares, steps, transfer landmarks, and duration
- 🎫 **Digital transit pass** — a neobank-style ticket with a scannable barcode, connecting route timeline, and vehicle-specific branding (jeep, UV Express, LRT/MRT, tricycle, etc.)
- 🔁 **Byahe Ko (My Trips)** — star recurring commutes, one-tap "Sakay Ulit" to re-run a saved trip, plus a "Bahay Ko" default home origin
- 📴 **Offline-first PWA** — service worker caches your last 5 trips so a dead signal in a station or tunnel doesn't strand you
- 🛠️ **Crowdsourced accuracy** — "Mali ba ito?" lets commuters flag wrong fares or closed terminals per step

`React 19` · `TypeScript` · `Vite` · `Tailwind CSS` · `Node.js` · `Express` · `Gemini API` · `SQLite` · `Capacitor (PWA → Android)`

</details>

<details>
<summary><b>💸 BayaniRemit — Remittance & Household Budget Tracker</b></summary>
<br/>

OFW remittance and household allocation tracker, originally built as a full relational database project (11-table, 3NF schema) — now being rebuilt into a real full-stack app with a budget-tracker feel.

`PostgreSQL` · `MySQL`

</details>

<details>
<summary><b>🔀 AIRelay — Chrome Extension</b></summary>
<br/>

Ever run out of tokens on Claude mid-conversation and have to start over on Gemini or ChatGPT, re-explaining everything? **AIRelay** kills that friction — one click extracts your chat and generates a ready-to-paste context-transfer prompt for the new AI.

- ⚡ **One-click extraction** — injects a script into the active tab that reads the page DOM and pulls out every message with its role (user/assistant)
- 🌐 **Cross-platform selectors** — dedicated DOM parsing for ChatGPT, Claude, Gemini, Grok, Copilot (Shadow DOM traversal), and Perplexity, with a generic fallback for anything else
- 📝 **4 output modes** — Full History, Condensed, Key Points, or a one-line TL;DR handoff
- 🔒 **100% local** — no servers, no data leaves your browser

`Chrome Extension` · `Manifest V3` · `Vanilla JS` · `chrome.scripting API`

</details>

---

### 📊 GitHub Stats

<div align="center">

<img height="165" src="https://github-readme-stats.vercel.app/api?username=a-ldnstntng&show_icons=true&theme=tokyonight&hide_border=true&count_private=true" />
<img height="165" src="https://github-readme-stats.vercel.app/api/top-langs/?username=a-ldnstntng&layout=compact&theme=tokyonight&hide_border=true" />

<br/>

<img src="https://github-readme-streak-stats.herokuapp.com/?user=a-ldnstntng&theme=tokyonight&hide_border=true" />

</div>

---

### 👾 Pac-Man Contribution Graph

<div align="center">

<img src="https://raw.githubusercontent.com/a-ldnstntng/a-ldnstntng/output/dist/pacman-contribution-graph.svg" />

</div>

---

### 📈 Activity Graph

<div align="center">

<img src="https://github-readme-activity-graph.vercel.app/graph?username=a-ldnstntng&theme=tokyo-night&hide_border=true" />

</div>

---

### 🤝 Connect With Me

<p align="center">
  <a href="mailto:andreiladines1901@gmail.com"><img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white"/></a>
  <a href="https://linkedin.com/in/tanting-ali-andrei-l-126a7140b"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"/></a>
</p>

<div align="center">

![Profile Views](https://komarev.com/ghpvc/?username=a-ldnstntng&color=6366f1&style=for-the-badge&label=PROFILE+VIEWS)

</div>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:6366f1,100:0f172a&height=120&section=footer" width="100%"/>
