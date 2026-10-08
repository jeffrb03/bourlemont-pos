---
name: Champagne Bar Bourlemont POS & Inventory
colors:
  surface: '#111319'
  surface-dim: '#111319'
  surface-bright: '#37393f'
  surface-container-lowest: '#0c0e13'
  surface-container-low: '#191c21'
  surface-container: '#1d2025'
  surface-container-high: '#282a30'
  surface-container-highest: '#33353b'
  on-surface: '#e2e2ea'
  on-surface-variant: '#d0c5af'
  inverse-surface: '#e2e2ea'
  inverse-on-surface: '#2e3036'
  outline: '#99907c'
  outline-variant: '#4d4635'
  surface-tint: '#e9c349'
  primary: '#f2ca50'
  on-primary: '#3c2f00'
  primary-container: '#d4af37'
  on-primary-container: '#554300'
  inverse-primary: '#735c00'
  secondary: '#b9c8de'
  on-secondary: '#233143'
  secondary-container: '#39485a'
  on-secondary-container: '#a7b6cc'
  tertiary: '#eecb6c'
  on-tertiary: '#3d2f00'
  tertiary-container: '#d0b054'
  on-tertiary-container: '#564300'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffe088'
  primary-fixed-dim: '#e9c349'
  on-primary-fixed: '#241a00'
  on-primary-fixed-variant: '#574500'
  secondary-fixed: '#d4e4fa'
  secondary-fixed-dim: '#b9c8de'
  on-secondary-fixed: '#0d1c2d'
  on-secondary-fixed-variant: '#39485a'
  tertiary-fixed: '#ffe08d'
  tertiary-fixed-dim: '#e5c365'
  on-tertiary-fixed: '#241a00'
  on-tertiary-fixed-variant: '#584400'
  background: '#111319'
  on-background: '#e2e2ea'
  surface-variant: '#33353b'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '600'
    lineHeight: 48px
    letterSpacing: -0.03em
  headline-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  title-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: -0.01em
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 22px
    letterSpacing: 0em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0.005em
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.06em
  currency-display:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  space-2xs: 0.25rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
  space-3xl: 4rem
  margin-screen: 1.5rem
  gutter-panel: 1.25rem
---

## Brand & Style

This design system expresses quiet opulence, surgical precision, and fluid physical realism. Engineered for high-volume, luxury hospitality management, the aesthetic fuses Apple-grade computational design with the tactile atmosphere of grand reserve cellar salons. 

The emotional tone balances effortless speed with haute-couture refinement: sommeliers and managers interact with an interface that feels like polished crystal, dark basalt stone, and illuminated vintage cuvée. The style relies on **Liquid Glassmorphism**: multilayered frosted midnight planes, diffused golden light blooms, microscopic inner borders (light catchers), and organic squircle silhouettes. Every element maintains clarity under dim ambient bar lighting while elevating routine actions—like uncorking grand crus or balancing cellars—into fluid, tactile experiences.

## Colors

The palette is rooted in atmospheric nocturnal depths, accented by authentic precious metal tones. 

- **Background Canvas**: Deep Apple Midnight (`#07090E`), subtly modulated with low-frequency radial gradients (`#0B0F19`) to create infinite atmospheric depth.
- **Glass Surfaces**: Frosted midnight layers built with alpha-composited fills (`rgba(18, 24, 38, 0.65)` to `rgba(26, 34, 52, 0.75)`), overlaid with 1px hairline edges (`rgba(255, 255, 255, 0.08)` to `rgba(255, 255, 255, 0.15)`).
- **Champagne Gold**: Primary action surfaces and critical metric badges utilize Warm Champagne Gold (`#D4AF37`), with high-illumination states at `#E5C365` and structural anchoring at `#C5A028`. Active glass surfaces emit an ambient radiant glow (`rgba(212, 175, 55, 0.18)`).
- **Text & Contrast Hierarchy**: 
  - Pure Optical White (`#FFFFFF`) for primary headlines, ticket values, and bottle titles.
  - Cashmere / Platinum Slate (`#CBD5E1` for secondary, `#94A3B8` for tertiary metadata, labels, and VAT breakdowns).
  - Champagne Gold (`#D4AF37`) dedicated to financial yields, active states, and VIP cellar statuses.
- **Semantic Accents**: Low-saturation emerald (`#10B981`) for stock availability and positive yield, crimson rose (`#F43F5E`) for depleted inventory or cancellations.

## Typography

Typography relies entirely on Plus Jakarta Sans for its geometric precision, contemporary warmth, and Apple-like proportioning. 

- **Numerical Display**: Monetary figures, escandallo percentages, and ticket amounts must use tabular lining figures (`font-variant-numeric: tabular-nums`) to prevent shifting layouts in live order feeds.
- **Airy Tracking**: Small metadata, categories, and badge tags (`label-sm`, `label-md`) use uppercase formatting paired with open letter spacing (`0.04em` to `0.06em`) to emulate luxury horology engraving.
- **Header Tracking**: Large display headers are tightened slightly (`-0.02em` to `-0.03em`) for optical density against dark glass backdrops.
- **Editorial Balance**: Titles for cuvées and vintages maintain medium weights (`500`) to preserve an understated, high-end editorial feel rather than aggressive commercial weights.

## Layout & Spacing

The architecture operates on an 8pt dynamic fluid grid with a strict three-column split POS paradigm:
1. **Primary Navigation Pillar**: Slim collapsible sidebar (64px to 240px) displaying core modules (*Ventas del Día*, *Inventario*, *Escandallos*, *Historial*, *Recetas*).
2. **Interactive Workbench / Catalogue**: Flexible multi-card grid adapting between 2 to 4 columns depending on device width.
3. **Persistent Command Rail**: Right-anchored order checkout & live ticket panel (380px fixed width on desktop displays) ensuring instantaneous access to *Cobrar* and split billing.

### Form Factors & Adaptation
- **Desktop / iPad Pro Landscape (≥ 1024px)**: Complete three-panel arrangement with simultaneous catalogue browsing and real-time ticket composition.
- **Tablet Portrait (768px - 1023px)**: Left navigation collapses into an ultra-thin glass rail (icon-only); command ticket rail transitions into a bottom-anchored frosted sheet accessible via gesture swipe.
- **Mobile Handheld (≤ 767px)**: Viewports reflow into a single fluid canvas. The current ticket reduces to a floating bottom glass bar displaying total amount and a swift *Cobrar* CTA.

## Elevation & Depth

Visual hierarchy is communicated via layered transillumination, structural blur, and fine edge reflections rather than heavy drop shadows:

- **Atmospheric Floor (Level 0)**: Unfiltered Deep Apple Midnight (`#07090E`).
- **Recessed / Cavity (Level 1)**: Inset controls, search inputs, and table wells use darker translucency (`rgba(5, 7, 12, 0.6)`) with subtle inner shadow `inset 0 1px 2px rgba(0, 0, 0, 0.4)`.
- **Floating Panels (Level 2)**: Core workstation cards, catalogues, and sidebars utilize midnight glass (`rgba(18, 24, 38, 0.65)`), backed by `backdrop-filter: blur(20px) saturate(160%)`. They are framed with a fine 1px border `rgba(255, 255, 255, 0.08)` and a microscopic top inner highlight `inset 0 1px 0 rgba(255, 255, 255, 0.12)`.
- **Elevated Modals & Flyouts (Level 3)**: Action menus, bottle vintage pickers, and split-payment dialogues step forward with `rgba(26, 34, 52, 0.85)`, `backdrop-filter: blur(30px)`, dynamic golden ambient edge glows (`0 20px 40px -10px rgba(0, 0, 0, 0.6)`), and an outer hairline of `rgba(212, 175, 55, 0.25)`.
- **Active Radiant Tier**: Selected bottles and primary transaction triggers gain a soft champagne aura: `0 0 24px rgba(212, 175, 55, 0.22)`.

## Shapes

The interface embraces Apple’s continuous corner curvature (squircle geometry) for an organic, tactile aesthetic:

- **Small Interactive Units**: Chips, status tags, toggle pills, and icon circles adopt full pill curvature (`rounded-full`).
- **Standard Controls & Inputs**: Form fields, category chips, and secondary buttons utilize smooth rounded geometry (`rounded-xl` / `1.25rem`).
- **Glass Tiles & POS Product Cards**: Bottle inventory blocks and operational panes use `rounded-2xl` (`1.5rem`).
- **Hero Containers & Flyout Modals**: Primary sheets and master layout panels feature soft continuous bounds (`rounded-3xl` / `2rem`).

## Components

### Botones (Buttons)
- **Botón Primario (*Cobrar*, *Nueva Orden*)**: Pill-shaped or heavily rounded (`rounded-full`), filled with solid Champagne Gold (`#D4AF37`) gradient shading to `#C5A028`. High-contrast dark midnight typography (`#07090E`, `fontWeight: 600`). Subtle top rim highlight and an ambient gold radiance (`box-shadow: 0 4px 20px rgba(212, 175, 55, 0.3)`). Hover scales to `1.015` with enhanced illumination (`#E5C365`).
- **Botón Secundario / Fantasma**: Translucent frosted pill (`rgba(255, 255, 255, 0.05)`), 1px border (`rgba(255, 255, 255, 0.1)`), crisp white text.

### Badges e Indicadores (Chips & Status Badges)
- Completely pill-shaped (`rounded-full`) with micro typography (`label-sm`).
- *Stock Crítico / Agotado*: Background `rgba(244, 63, 94, 0.12)`, border `rgba(244, 63, 94, 0.3)`, text `#FDA4AF`.
- *Reserva / En Carta*: Background `rgba(212, 175, 55, 0.12)`, border `rgba(212, 175, 55, 0.35)`, text `#E5C365`.
- *Mesa Activa*: Glass dot with glowing inner pulse (`#10B981`).

### Campos de Entrada (Input Fields: *Buscar Referencia, Añada, Usuario*)
- Cavity glass styling: `rgba(7, 9, 14, 0.6)`, recessed inner shadow, soft border `rgba(255, 255, 255, 0.08)`.
- Focus state: Hairline shift to `rgba(212, 175, 55, 0.6)` with an ambient soft golden ring (`box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.15)`).
- Placeholder text styled in platinum slate (`#64748B`).

### Tarjetas de Producto / Inventario (Product & Bottle Cards)
- Midnight glass canvas (`rgba(18, 24, 38, 0.65)`), `backdrop-filter: blur(20px)`, heavy rounded corners (`rounded-2xl`).
- Micro-interaction: Smooth lift on tap/hover, border transition to `rgba(212, 175, 55, 0.3)`.
- Contains: Cuvée name, vintage year badge, glass/bottle toggle, live stock level indicator, and highlighted price in champagne gold.

### Tablas de Datos y Escandallos (Frosted Data Tables)
- Floating borderless table with alternating glass row striping (`rgba(255, 255, 255, 0.015)` and transparent).
- Header row fixed with sticky blurred background, typography uppercase `label-md` in slate grey (`#94A3B8`).
- Direct inline editing cells for recipe portions (ml, yield percentage, margin calculation).

### Ticket de Venta / Panel de Comanda (Order Ticket Rail)
- Persistent panel on desktop, docked right. Includes order item list with swipe-to-void actions, split-item toggles, tax breakdown, and primary gold *Cobrar* button.
- Subtotal and total rows isolated with crisp 1px borders and prominent currency display.