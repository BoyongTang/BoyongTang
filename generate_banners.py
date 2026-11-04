import os

HERE = os.path.dirname(os.path.abspath(__file__))

def generate_svg(theme="dark"):
    is_dark = theme == "dark"
    bg = "#071320" if is_dark else "#F4F1E9"
    border = "#163044" if is_dark else "#D6D3C9"
    grid = "#163044" if is_dark else "#E5E2D8"
    text_starlight = "#ECF3F0" if is_dark else "#1E2930"
    text_muted = "#B9CFD6" if is_dark else "#555851"
    text_dim = "#6F8EA0" if is_dark else "#8A8D86"
    cyan = "#82D0DC" if is_dark else "#1F6F7D"
    gold = "#E9C18F" if is_dark else "#965139"
    green = "#8FC3B4" if is_dark else "#37685E"
    nebula_color = "#163044" if is_dark else "#E9E6DC"
    
    cx, cy = 870, 190
    
    # Real topics only (mirrors src/data/atlas.ts on the site): (x, y, label, type)
    nodes = [
        (760, 95, "SURROGATE MODELS", "m"),
        (960, 75, "BAYESIAN OPT.", "m"),
        (1020, 175, "AL ≠ BO", "n"),
        (960, 295, "QUERY STRATEGIES", "m"),
        (790, 285, "MATERIALS", "q"),
        (710, 185, "EVALUATION", "m"),
        (cx, cy, "ACTIVE LEARNING", "core")
    ]
    
    # Edges (i, j, dash)
    edges = [
        (6, 0, ""),
        (6, 3, ""),
        (6, 5, ""),
        (4, 6, "7,6"),
        (0, 3, "3,6"),
        (0, 1, "3,6"),
        (2, 1, "1,5"),
        (2, 3, "1,5"),
    ]
    
    stars = [
        (660, 60, 1.2, 0.6), (720, 40, 0.8, 0.4), (820, 30, 1.5, 0.7), (910, 35, 0.9, 0.5),
        (1010, 45, 1.1, 0.6), (1070, 90, 0.7, 0.4), (1090, 190, 1.4, 0.7), (1060, 260, 0.8, 0.5),
        (1010, 330, 1.3, 0.7), (890, 350, 0.9, 0.4), (760, 340, 1.2, 0.6), (680, 310, 0.8, 0.4),
        (650, 240, 1.5, 0.7), (700, 130, 0.7, 0.3), (850, 110, 1.1, 0.5), (930, 140, 0.8, 0.4),
        (900, 250, 1.3, 0.6), (820, 230, 0.9, 0.5), (780, 170, 0.7, 0.3)
    ]
    
    lines_svg = []
    # Grid background
    for x in range(0, 1201, 50):
        lines_svg.append(f'<line x1="{x}" y1="0" x2="{x}" y2="380" stroke="{grid}" stroke-width="0.75" stroke-opacity="0.35"/>')
    for y in range(0, 381, 50):
        lines_svg.append(f'<line x1="0" y1="{y}" x2="1200" y2="{y}" stroke="{grid}" stroke-width="0.75" stroke-opacity="0.35"/>')
        
    star_svg = []
    for (sx, sy, sr, so) in stars:
        star_svg.append(f'<circle cx="{sx}" cy="{sy}" r="{sr}" fill="{text_starlight}" opacity="{so}"/>')
        
    edge_svg = []
    for (i, j, dash) in edges:
        x1, y1 = nodes[i][0], nodes[i][1]
        x2, y2 = nodes[j][0], nodes[j][1]
        d_attr = f' stroke-dasharray="{dash}"' if dash else ''
        edge_svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{cyan}" stroke-width="1.2" stroke-opacity="0.55"{d_attr}/>')
        
    node_svg = []
    for idx, (nx, ny, nlabel, ntype) in enumerate(nodes):
        if ntype == "core":
            node_svg.append(f'''
                <circle cx="{nx}" cy="{ny}" r="40" fill="url(#core-glow)" />
                <circle cx="{nx}" cy="{ny}" r="18" fill="none" stroke="{gold}" stroke-width="1.2" stroke-opacity="0.7" />
                <circle cx="{nx}" cy="{ny}" r="27" fill="none" stroke="{gold}" stroke-width="0.9" stroke-dasharray="3,3" stroke-opacity="0.5" />
                <circle cx="{nx}" cy="{ny}" r="6.5" fill="{gold}" />
            ''')
        else:
            is_right = nx >= cx
            anchor = "start" if is_right else "end"
            tx = nx + 12 if is_right else nx - 12
            node_svg.append(f'''
                <circle cx="{nx}" cy="{ny}" r="11" fill="none" stroke="{cyan}" stroke-width="1" stroke-opacity="0.3" />
                <circle cx="{nx}" cy="{ny}" r="4.5" fill="{text_starlight}" />
                <text x="{tx}" y="{ny + 3.5}" fill="{text_muted}" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="9" font-weight="500" letter-spacing="1.2" text-anchor="{anchor}">{nlabel}</text>
            ''')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 380" width="100%">
  <defs>
    <radialGradient id="nebula" cx="72%" cy="50%" r="55%">
      <stop offset="0%" stop-color="{nebula_color}" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="{bg}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="core-glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{gold}" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="{gold}" stop-opacity="0"/>
    </radialGradient>
    <style>
      .title {{ font-family: 'IBM Plex Sans', -apple-system, sans-serif; font-weight: 700; fill: {text_starlight}; letter-spacing: -0.5px; }}
      .mono {{ font-family: 'IBM Plex Mono', ui-monospace, monospace; }}
    </style>
  </defs>

  <!-- Background -->
  <rect width="1200" height="380" rx="10" fill="{bg}"/>
  <rect width="1200" height="380" rx="10" fill="url(#nebula)"/>
  <rect x="0.5" y="0.5" width="1199" height="379" rx="9.5" fill="none" stroke="{border}" stroke-width="1"/>

  <!-- Subtle Coordinate Grid -->
  <g opacity="0.6">
    {''.join(lines_svg)}
  </g>

  <!-- Instrument Circles on Right -->
  <g opacity="0.75">
    <circle cx="{cx}" cy="{cy}" r="150" fill="none" stroke="{border}" stroke-width="1"/>
    <circle cx="{cx}" cy="{cy}" r="115" fill="none" stroke="{border}" stroke-width="1" stroke-dasharray="2,5"/>
    <circle cx="{cx}" cy="{cy}" r="75" fill="none" stroke="{border}" stroke-width="1"/>
    <line x1="{cx - 170}" y1="{cy}" x2="{cx + 170}" y2="{cy}" stroke="{border}" stroke-width="1" stroke-dasharray="2,6"/>
    <line x1="{cx}" y1="{cy - 160}" x2="{cx}" y2="{cy + 160}" stroke="{border}" stroke-width="1" stroke-dasharray="2,6"/>
  </g>

  <!-- Stars & Constellation -->
  <g>
    {''.join(star_svg)}
    {''.join(edge_svg)}
    {''.join(node_svg)}
  </g>

  <!-- Left: Editorial Observatory Headers -->
  <g transform="translate(64, 0)">
    <!-- Top Meta Tag -->
    <text x="0" y="68" class="mono" font-size="11" font-weight="600" letter-spacing="2.8" fill="{text_dim}">O / Q · OBSERVATORY OF QUESTIONS</text>
    
    <!-- Main Title -->
    <text x="0" y="128" class="title" font-size="34">THE OBSERVATORY</text>
    <text x="0" y="168" class="title" font-size="34">OF QUESTIONS</text>

    <!-- Golden Separation Line -->
    <line x1="0" y1="188" x2="180" y2="188" stroke="{gold}" stroke-width="2"/>

    <!-- Subtitle & Worldview -->
    <text x="0" y="218" class="mono" font-size="11.5" font-weight="500" letter-spacing="1.5" fill="{text_muted}">ACTIVE LEARNING FOR MATERIALS SCIENCE</text>
    <text x="0" y="244" class="mono" font-size="10.5" font-weight="500" letter-spacing="1.8" fill="{cyan}">REPRODUCE FIRST · THEN BUILD A LOOP THAT TRANSFERS</text>

    <!-- Researcher Credentials Badge Box -->
    <g transform="translate(0, 276)">
      <rect width="460" height="48" rx="4" fill="{border}" fill-opacity="0.35" stroke="{border}" stroke-width="1"/>
      <text x="16" y="22" class="mono" font-size="11" font-weight="600" fill="{text_starlight}" letter-spacing="1.2">BOYONG TANG (けるゔぃん・とう)</text>
      <text x="16" y="38" class="mono" font-size="9.5" font-weight="400" fill="{text_dim}" letter-spacing="0.8">SICHUAN UNIVERSITY · APPLIED MATHEMATICS &amp; ARTIFICIAL INTELLIGENCE</text>
    </g>
  </g>

  <!-- Border Corner Accents -->
  <path d="M 12 24 L 12 12 L 24 12" fill="none" stroke="{gold}" stroke-width="1.5" opacity="0.8"/>
  <path d="M 1188 24 L 1188 12 L 1176 12" fill="none" stroke="{gold}" stroke-width="1.5" opacity="0.8"/>
  <path d="M 12 356 L 12 368 L 24 368" fill="none" stroke="{gold}" stroke-width="1.5" opacity="0.8"/>
  <path d="M 1188 356 L 1188 368 L 1176 368" fill="none" stroke="{gold}" stroke-width="1.5" opacity="0.8"/>
</svg>
'''

for theme in ("dark", "light"):
    with open(os.path.join(HERE, "assets", f"banner-{theme}.svg"), "w") as f:
        f.write(generate_svg(theme))

print("Banners generated successfully.")
