# Design System Document

## 1. Overview & Creative North Star: "The Kinetic Observatory"
This design system is built to transform complex financial backtesting from a static data exercise into a high-performance, immersive "observatory." We are moving away from the cluttered, "Excel-style" look of legacy trading platforms toward a **Kinetic Observatory** aesthetic. 

The goal is to provide a sense of **Instrumental Authority.** We achieve this through a "Dense-but-Deep" layout: information density is high (as required by professionals), but visual fatigue is mitigated through tonal layering rather than structural lines. By utilizing intentional asymmetry and "frosted" surfaces, we ensure the user feels they are looking *through* the data, not just at it.

---

## 2. Colors & Tonal Depth
The palette is rooted in the "Abyssal" spectrum—deep, dark blues and blacks—providing a high-contrast stage for vibrant neon indicators.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to section off the UI. 
*   **The Alternative:** Boundaries must be defined solely through background shifts. For example, a `surface-container-low` component should sit directly on a `background` or `surface` area. The change in hex code is the divider.
*   **Nesting:** To create focus, use a `surface-container-highest` for the most critical active data panel (e.g., the current backtest result), while secondary metrics sit on `surface-container-low`.

### The "Glass & Gradient" Rule
To elevate the UI from "Standard Dark Mode" to "Premium Dashboard," use **Glassmorphism** for floating overlays (modals, dropdowns, or hover-states). 
*   **Implementation:** Use a semi-transparent `surface-variant` with a 20px–40px backdrop-blur. 
*   **Signature Textures:** Main Action Buttons (CTAs) should never be flat. Apply a subtle linear gradient (Top-Left to Bottom-Right) from `primary` (#94aaff) to `primary-container` (#809bff) to give the button "weight" and a tactile, backlit feel.

---

## 3. Typography: Editorial Precision
The system utilizes a dual-font approach to balance data readability with brand sophistication.

*   **Display & Headlines (Manrope):** High-impact headlines use Manrope. Its wider apertures and modern geometric construction provide an "Editorial" feel. Use `display-lg` for total portfolio returns or win-rates to command immediate attention.
*   **Functional UI (Inter):** All data tables, ticker symbols, and body copy use Inter. Its tall x-height is optimized for legibility in dense environments.
*   **Information Hierarchy:** Use `label-sm` (0.6875rem) in `on-surface-variant` for metadata. This creates a clear distinction between the *label* and the *value* (which should be `title-sm` or `body-md`).

---

## 4. Elevation & Depth
In a trading environment, "Z-axis" depth dictates the order of operations. We use **Tonal Layering** to define this.

*   **The Layering Principle:** 
    1.  **Level 0 (Background):** `background` (#070e1e) – The void.
    2.  **Level 1 (Sections):** `surface-container-low` (#0b1325) – Large widget areas.
    3.  **Level 2 (Cards):** `surface-container` (#11192d) – Individual data points or chart containers.
*   **Ambient Shadows:** For "floating" elements like Tooltips, use a shadow with a 32px blur, 10% opacity, and a color hex of `#000000`. It should look like a soft glow of darkness, not a hard drop shadow.
*   **The "Ghost Border" Fallback:** If a border is required for accessibility (e.g., focused input states), use `outline-variant` at **15% opacity**. Never 100%.

---

## 5. Components

### Cards & Containers
*   **Style:** Use `xl` (0.75rem) rounding for outer containers and `md` (0.375rem) for internal nested elements.
*   **Rule:** Forbid the use of divider lines. Separate card sections using a vertical spacing of `1.5rem` or a subtle shift from `surface-container` to `surface-container-high`.

### Buttons
*   **Primary:** Gradient fill (`primary` to `primary-container`), white text, `md` rounding.
*   **Secondary (Neon Accents):** For "Buy/Long" use `secondary` (#59fdc5) text with a `secondary_container` ghost background. For "Sell/Short" use `tertiary` (#ff6e85).
*   **Tertiary:** Transparent background with `on-surface-variant` text; background shifts to `surface-bright` on hover.

### Input Fields
*   **State:** Default state is `surface-container-highest` with no border. 
*   **Focus:** A "Ghost Border" of `primary` at 40% opacity and a subtle outer glow using the `surface_tint`.

### Data Visualization Accents
*   **Success (Profit):** `secondary` (#59fdc5)
*   **Danger (Drawdown):** `tertiary` (#ff6e85)
*   **Execution (Signals):** `primary-dim` (#3367ff)
*   **Charts:** Use a 2px stroke width for line charts with a subtle gradient fill below the line (10% opacity to 0%).

---

## 6. Do’s and Don’ts

### Do
*   **Do** use asymmetrical layouts for the header. Place the "Run Backtest" CTA off-center to create visual interest.
*   **Do** use `letter-spacing: -0.02em` on all `headline-` styles to give them a premium, "tucked" appearance.
*   **Do** utilize `surface-container-lowest` (#000000) for the chart background to make the neon price action "pop."

### Don't
*   **Don't** use pure white (#FFFFFF) for text. Always use `on-surface` (#dfe5fc) to reduce eye strain in dark environments.
*   **Don't** use standard "Grey" for shadows. Use tinted shadows to maintain the deep blue atmosphere.
*   **Don't** use borders to separate table rows. Use alternating row colors (Zebra striping) with `surface-container` and `surface-container-low` at very low contrast.

---

## 7. Responsive Philosophy
*   **Desktop:** Maximum density. Use a 12-column grid but allow widgets to span 3, 6, or 9 columns to maintain "intentional gaps" (white space).
*   **Tablet:** Collapse the sidebar into a "Glass" icon-only rail. Cards should stack into a single column, but maintain the `xl` rounding and tonal layering to ensure depth is preserved.