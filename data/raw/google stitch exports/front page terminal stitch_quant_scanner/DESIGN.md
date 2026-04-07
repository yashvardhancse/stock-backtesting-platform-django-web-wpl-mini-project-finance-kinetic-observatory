# Design System Specification: Quantitative Precision

## 1. Overview & Creative North Star
**Creative North Star: "The Kinetic Ledger"**

This design system rejects the "SaaS-standard" of bubbly, oversized components and soft pastels. Instead, it embraces a high-density, authoritative aesthetic that honors the heritage of terminal-based trading while integrating the fluidity of modern digital product design. 

We break the "template" look through **Intentional Brutalism**: a commitment to 0px border radii (hard edges), razor-sharp typography, and a "No-Line" architectural philosophy. By removing rounded corners and traditional dividers, we create an environment of absolute precision, where every pixel is dedicated to data clarity rather than decorative fluff. The UI should feel like a high-performance engine: cold, efficient, and impeccably organized.

---

## 2. Colors & Surface Architecture

The palette is anchored in deep charcoals and cyans to reduce eye strain during 12-hour trading sessions, punctuated by aggressive, high-chroma signals for market action.

### The "No-Line" Rule
Traditional 1px solid borders are strictly prohibited for layout sectioning. In this design system, boundaries are defined exclusively through **Background Shift**. To separate a sidebar from a main chart area, transition from `surface` (#111318) to `surface-container-low` (#1a1c20). This creates a "machined" look where components appear to be milled from a single block of dark glass.

### Surface Hierarchy & Nesting
Use the `surface-container` tiers to create logical data grouping. 
- **Global Background:** `surface` (#111318)
- **Primary Workspaces:** `surface-container-low` (#1a1c20)
- **Active Data Tables/Cards:** `surface-container` (#1e2024)
- **Popovers/Modals:** `surface-container-highest` (#333539)

### The "Glass & Gradient" Rule
To prevent the UI from feeling "flat" or "dead," use subtle material effects:
- **Floating Overlays:** Use `surface-container-highest` with a `backdrop-blur` of 20px and 60% opacity to create a "Smoked Glass" effect.
- **Signature Gradients:** For primary CTAs or "Execute" states, use a linear gradient from `primary` (#00daf3) to `primary_container` (#009fb2) at a 135-degree angle. This adds a "lithographic" depth that solid fills lack.

---

## 3. Typography
We utilize a dual-font strategy to balance editorial authority with mathematical precision.

*   **Primary Typeface:** **Inter**. Used for all UI labels, navigation, and headings. It provides a neutral, high-legibility foundation.
*   **Data Typeface:** **JetBrains Mono** (or equivalent high-end Monospaced font). Required for all ticker symbols, price values, and quantitative metrics to ensure character alignment in rapidly updating data streams.

### Typography Scale
- **Display (Large/Med):** `display-lg` (3.5rem) for high-level portfolio totals.
- **Headline (Sm):** `headline-sm` (1.5rem) for major module headers (e.g., "Order Book").
- **Title (Sm):** `title-sm` (1rem) for table headers, using `on_surface_variant` (#c1c6d7) to de-emphasize metadata.
- **Label (Sm):** `label-sm` (0.6875rem) in **All Caps** for ultra-compact data labels.

---

## 4. Elevation & Depth
Depth is achieved through **Tonal Layering**, not shadows.

*   **The Layering Principle:** A "Buy" ticket should not "float" with a shadow; it should be "raised" by placing a `surface-container-high` (#282a2e) element onto a `surface` background.
*   **Ambient Shadows:** If a floating state is unavoidable (e.g., a context menu), use a shadow with a 40px blur, 0% offset, and 12% opacity using the `surface-container-lowest` color. It should feel like an ambient glow rather than a drop shadow.
*   **The "Ghost Border" Fallback:** For extreme density where tonal shifts aren't enough, use a "Ghost Border": 1px stroke using `outline_variant` (#414755) at 30% opacity. 

---

## 5. Components

### Primitive Styling
- **Buttons:**
    - **Primary:** Gradient fill (Primary to Primary-Container), 0px radius, `label-md` bold type.
    - **Secondary (Buy/Sell):** Use `secondary` (#40e56c) for Buy and `tertiary_container` (#ff525f) for Sell. No outlines.
- **Input Fields:** Use `surface-container-lowest` (#0c0e12) for the field background to create an "inset" feel. No borders. Use `primary` (#00daf3) for a 2px bottom-border on focus only.
- **Data Tables:**
    - **No Dividers:** Use `spacing-1` (0.2rem) between rows to create separation. 
    - **Zebra Striping:** Use `surface-container-low` on even rows.
    - **Alignment:** Numbers are always right-aligned and monospaced.

### Specialized Quant Components
- **The "Pulse" Indicator:** A 4px square using `secondary` (Green) or `error` (Red) that flashes when a trade executes.
- **The Sparkline:** Ultra-thin (1px) lines using `primary_fixed_dim` (#00daf3) for trend visualization within tables.
- **The Tape:** A high-density scrolling list using `body-sm` typography and `spacing-0.5` (0.1rem) vertical padding between entries.

---

## 6. Do's and Don'ts

### Do
- **DO** use 0px border radius on every single element.
- **DO** lean on `JetBrains Mono` for any value that includes a decimal point.
- **DO** use `spacing-px` (1px) for the most granular alignment needs.
- **DO** use `surface-bright` (#37393e) sparingly for "hover" states on interactive rows.

### Don't
- **DON'T** use 1px solid borders to wrap containers; use background color steps instead.
- **DON'T** use soft grays. All neutrals must have a slight blue/charcoal tint (`#111318` base).
- **DON'T** use standard "SaaS Blue." Use the `primary` cyan (#00daf3) for an electric, high-tech feel.
- **DON'T** use animations slower than 150ms. Transitions must be "snappy" and professional.