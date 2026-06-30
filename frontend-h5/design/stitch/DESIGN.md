---
name: Intimate Culinary Romance
colors:
  surface: '#fff8f5'
  surface-dim: '#e1d8d4'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fbf2ed'
  surface-container: '#f5ece7'
  surface-container-high: '#efe6e2'
  surface-container-highest: '#e9e1dc'
  on-surface: '#1e1b18'
  on-surface-variant: '#524346'
  inverse-surface: '#34302c'
  inverse-on-surface: '#f8efea'
  outline: '#847376'
  outline-variant: '#d6c1c5'
  surface-tint: '#894c5c'
  primary: '#894c5c'
  on-primary: '#ffffff'
  primary-container: '#f4a7b9'
  on-primary-container: '#733949'
  inverse-primary: '#ffb1c3'
  secondary: '#755a33'
  on-secondary: '#ffffff'
  secondary-container: '#ffdaaa'
  on-secondary-container: '#795e37'
  tertiary: '#5f5f59'
  on-tertiary: '#ffffff'
  tertiary-container: '#bdbcb5'
  on-tertiary-container: '#4c4c46'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffd9e0'
  primary-fixed-dim: '#ffb1c3'
  on-primary-fixed: '#380a1a'
  on-primary-fixed-variant: '#6e3545'
  secondary-fixed: '#ffddb2'
  secondary-fixed-dim: '#e4c192'
  on-secondary-fixed: '#291800'
  on-secondary-fixed-variant: '#5b421e'
  tertiary-fixed: '#e4e3db'
  tertiary-fixed-dim: '#c8c7bf'
  on-tertiary-fixed: '#1b1c17'
  on-tertiary-fixed-variant: '#474742'
  background: '#fff8f5'
  on-background: '#1e1b18'
  surface-variant: '#e9e1dc'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  caption:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding-mobile: 20px
  container-padding-desktop: 40px
  gutter: 16px
  section-gap: 32px
---

## Brand & Style

This design system is built to facilitate an intimate, shared experience around food and memories for couples. The aesthetic blends **Modern Minimalism** with **Glassmorphism**, creating a digital space that feels like a premium, soft-touch physical journal. 

The emotional response should be one of warmth, safety, and exclusivity. By utilizing high-quality whitespace and a gentle color story, the interface recedes to let the couple's photos and shared notes take center stage. The style is characterized by "soft depth"—using translucent layers and diffused glows rather than harsh lines—to evoke a romantic, dreamlike atmosphere that remains sophisticated and functional.

## Colors

The palette is anchored in a "Rose & Cream" narrative to establish a romantic but premium tone.

- **Primary (Soft Rose):** `#F4A7B9`. Used for key actions, active states, and emotional highlights.
- **Secondary (Delicate Peach):** `#FAD5A5`. Used for accent elements, categories, and secondary buttons.
- **Tertiary (Warm Cream):** `#FFFDF5`. The foundation of the UI, used for page backgrounds and large surface areas to provide a warmer, more inviting feel than pure white.
- **Neutral (Elegant Charcoal):** `#2D2926`. Reserved for typography and iconography to ensure high legibility and a grounded, professional finish.
- **Semantic Overlays:** Use a 40% opacity version of the primary color for soft background blurs and glassmorphism containers.

## Typography

The typography system utilizes **Plus Jakarta Sans** for its friendly, rounded terminals and contemporary geometric structure. It provides the perfect balance between high-end SaaS clarity and the soft, approachable nature of a lifestyle app.

- **Headlines:** Use SemiBold or Bold weights with slightly tighter letter spacing to create a strong visual "hug" for content titles.
- **Body Text:** Use Regular weight with generous line heights to ensure a relaxed, effortless reading experience.
- **Hierarchy:** Maintain a clear distinction between the "Shared" content (larger, bolder) and "Metadata" (labels and captions) to help users navigate their diary intuitively.

## Layout & Spacing

The layout philosophy is **Fluid & Airy**, prioritizing negative space to reduce cognitive load and enhance the "premium" feel.

- **Grid:** A standard 4-column grid for mobile and a 12-column centered grid for desktop/tablet. 
- **Margins:** Wider than average side margins (20px+) are used to "squeeze" the content, creating a focused, vertical journal aesthetic.
- **Rhythm:** An 8px linear scale is used. Components are separated by larger gaps (32px+) to signify different "memories" or entries, while internal element spacing remains tight (8px-12px) to show relatedness.

## Elevation & Depth

Depth is achieved through **Soft Tonal Layering** and **Glassmorphism** rather than traditional high-contrast shadows.

- **Surface Tiers:** The base layer is the Warm Cream. Cards and containers use a pure white surface or a semi-transparent glass effect.
- **Glassmorphism:** Use a `backdrop-filter: blur(12px)` with a white fill at 60% opacity for navigation bars and floating action buttons. This allows the colors of food photography to peak through.
- **Shadows:** Use a single, very soft "Ambient Glow" shadow: `0px 10px 30px rgba(244, 167, 185, 0.15)`. The shadow color is tinted with the primary rose hue to keep it warm and avoid a "dirty" grey look.

## Shapes

The shape language is defined by **organic softness**. 

- **Corners:** High radius values are applied to all interactive elements. Large containers (like recipe cards) should use `rounded-xl` (1.5rem/24px) to feel like smooth pebbles or modern stationery.
- **Buttons:** Buttons are fully rounded (pill-shaped) to invite interaction and feel friendly.
- **Icons:** Use icons with rounded caps and joins. Avoid sharp 90-degree angles in any stroke work.

## Components

- **Buttons:** Primary buttons use a solid Rose Pink fill with White text. Secondary buttons use a Peach outline or a subtle Cream-to-Peach gradient.
- **Cards (The "Diary Entry"):** Cards are the core component. They feature a pure white background, `rounded-xl` corners, and the signature soft rose-tinted shadow. Content inside should have generous 24px internal padding.
- **Input Fields:** Use a subtle Cream fill with a 1px Rose-tinted border that glows slightly when focused. Labels should be positioned above the field in Charcoal `label-sm`.
- **Chips/Tags:** Use for food categories (e.g., "Home Cooked," "Date Night"). These should be pill-shaped with a light Peach background and Charcoal text.
- **Lists:** Use "In-set" lists where items are separated by a soft horizontal rule that doesn't reach the edges of the screen, maintaining the airy feel.
- **Navigation:** A floating bottom tab bar using glassmorphism, with active states indicated by a small Rose Pink dot below the icon.