/* @ds-bundle: {"format":4,"namespace":"DronexDesignSystem_f3f897","components":[{"name":"ContentCard","sourcePath":"components/content/ContentCard.jsx"},{"name":"MediaFrame","sourcePath":"components/content/MediaFrame.jsx"},{"name":"StatCard","sourcePath":"components/content/StatCard.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"IconBadge","sourcePath":"components/core/IconBadge.jsx"},{"name":"Logo","sourcePath":"components/core/Logo.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"NewsletterForm","sourcePath":"components/forms/NewsletterForm.jsx"},{"name":"CarouselNav","sourcePath":"components/navigation/CarouselNav.jsx"},{"name":"SiteFooter","sourcePath":"components/navigation/SiteFooter.jsx"},{"name":"SiteHeader","sourcePath":"components/navigation/SiteHeader.jsx"}],"sourceHashes":{"components/content/ContentCard.jsx":"f76149f5315a","components/content/MediaFrame.jsx":"f93bba9865e4","components/content/StatCard.jsx":"3089bed4c4af","components/core/Button.jsx":"21ffc14a8a1d","components/core/Icon.jsx":"3bd5422f23ae","components/core/IconBadge.jsx":"d76f0669effb","components/core/Logo.jsx":"065ecf50a2cd","components/core/Tag.jsx":"399da25c49fd","components/forms/Input.jsx":"090ee37077c9","components/forms/NewsletterForm.jsx":"bff0ac145eb8","components/navigation/CarouselNav.jsx":"2e1bab5afe66","components/navigation/SiteFooter.jsx":"e462fd3c1419","components/navigation/SiteHeader.jsx":"36b2c55e508c","ui_kits/dronex-site/about.screen.jsx":"e5da71efebf6","ui_kits/dronex-site/drones.screen.jsx":"2463c544f01c","ui_kits/dronex-site/home.screen.jsx":"6baef5313873","ui_kits/dronex-site/mobile.screen.jsx":"502f8d275c75"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.DronexDesignSystem_f3f897 = window.DronexDesignSystem_f3f897 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/content/ContentCard.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Paper sheet holding an optional tag, a tight headline, body copy and a CTA.
   This is the workhorse block of the mobile/editorial layouts. */
function ContentCard({
  tag,
  title,
  body,
  tone = "paper",
  titleSize = "var(--size-h2)",
  media,
  mediaPosition = "below",
  footer,
  children,
  style,
  ...rest
}) {
  const skins = {
    paper: {
      background: "var(--surface-card)",
      color: "var(--text-heading)"
    },
    concrete: {
      background: "var(--surface-card-alt)",
      color: "var(--text-heading)"
    },
    ink: {
      background: "var(--surface-invert)",
      color: "var(--text-on-invert)"
    },
    accent: {
      background: "var(--surface-accent)",
      color: "var(--text-on-accent)"
    }
  }[tone];
  const bodyColor = tone === "ink" ? "var(--text-on-invert-muted)" : "var(--text-body)";
  return /*#__PURE__*/React.createElement("section", _extends({
    style: {
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-6)",
      padding: "var(--pad-card-lg)",
      borderRadius: "var(--radius-sheet)",
      ...skins,
      ...style
    }
  }, rest), tag && /*#__PURE__*/React.createElement("div", null, tag), mediaPosition === "above" && media, title && /*#__PURE__*/React.createElement("h2", {
    style: {
      font: `var(--weight-head) ${titleSize}/var(--leading-tight) var(--font-heading)`,
      letterSpacing: "var(--tracking-head)",
      margin: 0,
      textWrap: "pretty"
    }
  }, title), body && /*#__PURE__*/React.createElement("p", {
    style: {
      font: "var(--type-body-sm)",
      color: bodyColor,
      margin: 0,
      maxWidth: "62ch",
      textWrap: "pretty"
    }
  }, body), mediaPosition === "below" && media, children, footer);
}
Object.assign(__ds_scope, { ContentCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/ContentCard.jsx", error: String((e && e.message) || e) }); }

// components/content/MediaFrame.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const TICK = {
  position: "absolute",
  width: "var(--tick-length)",
  height: "var(--tick-thickness)",
  background: "var(--tick-color-invert)"
};

/* Photography container carrying the Dronex crop-mark motif: short dashes
   inset at the corners of the frame. */
function MediaFrame({
  src,
  alt = "",
  ratio,
  ticks = "top",
  tickTone = "light",
  radius = "var(--radius-media)",
  scrim = "none",
  zoomOnHover = false,
  children,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const color = tickTone === "dark" ? "var(--tick-color)" : "var(--tick-color-invert)";
  const corners = ticks === "none" ? [] : ticks === "all" ? ["tl", "tr", "bl", "br"] : ["tl", "tr"];
  const pos = {
    tl: {
      top: "var(--tick-inset)",
      left: "var(--tick-inset)"
    },
    tr: {
      top: "var(--tick-inset)",
      right: "var(--tick-inset)"
    },
    bl: {
      bottom: "var(--tick-inset)",
      left: "var(--tick-inset)"
    },
    br: {
      bottom: "var(--tick-inset)",
      right: "var(--tick-inset)"
    }
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      position: "relative",
      overflow: "hidden",
      borderRadius: radius,
      aspectRatio: ratio,
      background: "var(--concrete)",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("img", {
    src: src,
    alt: alt,
    style: {
      width: "100%",
      height: "100%",
      objectFit: "cover",
      display: "block",
      filter: "var(--image-filter)",
      transition: "var(--transition-media)",
      transform: zoomOnHover && hover ? "scale(var(--media-hover-scale))" : "none"
    }
  }), scrim !== "none" && /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      inset: 0,
      background: scrim === "bottom" ? "var(--scrim-bottom)" : scrim === "left" ? "var(--scrim-left)" : "var(--scrim-flat)"
    }
  }), corners.map(c => /*#__PURE__*/React.createElement("span", {
    key: c,
    style: {
      ...TICK,
      background: color,
      ...pos[c]
    }
  })), children);
}
Object.assign(__ds_scope, { MediaFrame });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/MediaFrame.jsx", error: String((e && e.message) || e) }); }

// components/content/StatCard.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Tall proof-point column: big number up top, label under it, supporting
   copy pinned to the bottom. Greys and lime alternate across a row. */
function StatCard({
  value,
  label,
  body,
  tone = "concrete",
  align = "space-between",
  style,
  ...rest
}) {
  const skins = {
    paper: {
      background: "var(--surface-card)",
      color: "var(--text-heading)"
    },
    concrete: {
      background: "var(--surface-card-alt)",
      color: "var(--text-heading)"
    },
    accent: {
      background: "var(--surface-accent)",
      color: "var(--text-on-accent)"
    },
    ink: {
      background: "var(--surface-invert)",
      color: "var(--text-on-invert)"
    }
  }[tone];
  const bodyColor = tone === "ink" ? "var(--text-on-invert-muted)" : "var(--text-body)";
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: "flex",
      flexDirection: "column",
      justifyContent: align,
      gap: "var(--space-16)",
      padding: "var(--pad-card-lg)",
      borderRadius: "var(--radius-sheet)",
      minHeight: 320,
      ...skins,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      font: "var(--type-stat)",
      letterSpacing: "var(--tracking-head)"
    }
  }, value), label && /*#__PURE__*/React.createElement("div", {
    style: {
      font: "var(--type-h4)",
      letterSpacing: "var(--tracking-head)",
      marginTop: "var(--space-3)"
    }
  }, label)), body && /*#__PURE__*/React.createElement("p", {
    style: {
      font: "var(--type-caption)",
      color: bodyColor,
      margin: 0,
      maxWidth: "34ch",
      textWrap: "pretty"
    }
  }, body));
}
Object.assign(__ds_scope, { StatCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/StatCard.jsx", error: String((e && e.message) || e) }); }

// components/core/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const LUCIDE = "https://unpkg.com/lucide-static@0.544.0/icons/";

/* Monochrome glyph rendered as a CSS mask so it inherits colour.
   Dronex ships no icon font of its own — Lucide stands in (see readme ICONOGRAPHY). */
function Icon({
  name = "arrow-right",
  size = 20,
  color = "currentColor",
  label,
  style,
  ...rest
}) {
  const url = `url(${LUCIDE}${name}.svg)`;
  return /*#__PURE__*/React.createElement("span", _extends({
    role: label ? "img" : "presentation",
    "aria-label": label,
    "aria-hidden": label ? undefined : true,
    style: {
      display: "inline-block",
      width: size,
      height: size,
      flex: "none",
      backgroundColor: color,
      WebkitMaskImage: url,
      maskImage: url,
      WebkitMaskRepeat: "no-repeat",
      maskRepeat: "no-repeat",
      WebkitMaskSize: "contain",
      maskSize: "contain",
      WebkitMaskPosition: "center",
      maskPosition: "center",
      ...style
    }
  }, rest));
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Dronex buttons. Four treatments, all taken from the source:
   outline pill, white pill with mark badge, solid lime pill, square lime block. */
function Button({
  variant = "outline",
  size = "md",
  icon,
  iconPosition = "right",
  markBadge = false,
  assetBase = "../../assets",
  full = false,
  disabled = false,
  children,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const [press, setPress] = React.useState(false);
  const sizes = {
    sm: {
      pad: "9px 18px",
      font: "10px",
      badge: 22
    },
    md: {
      pad: "13px 24px",
      font: "11px",
      badge: 30
    },
    lg: {
      pad: "19px 32px",
      font: "13px",
      badge: 38
    }
  }[size];
  const base = {
    display: full ? "flex" : "inline-flex",
    width: full ? "100%" : undefined,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    padding: markBadge ? `6px 24px 6px 6px` : sizes.pad,
    font: `var(--weight-head) ${sizes.font}/var(--leading-label) var(--font-ui)`,
    letterSpacing: "var(--tracking-label)",
    textTransform: "uppercase",
    whiteSpace: "nowrap",
    textDecoration: "none",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.35 : 1,
    transition: "var(--transition-control), transform var(--duration-fast) var(--ease-standard)",
    transform: press && !disabled ? "scale(var(--press-scale))" : "none",
    border: "var(--border-width) solid transparent",
    borderRadius: "var(--radius-pill)"
  };
  const skins = {
    outline: {
      background: hover && !disabled ? "var(--ink-06)" : "transparent",
      color: "var(--text-heading)",
      borderColor: hover && !disabled ? "var(--ink-20)" : "var(--border-hairline)"
    },
    pill: {
      background: "var(--white)",
      color: "var(--text-heading)",
      borderColor: "var(--white)",
      paddingLeft: markBadge ? 6 : undefined
    },
    accent: {
      background: hover && !disabled ? "var(--lime-press)" : "var(--lime)",
      color: "var(--text-on-accent)",
      borderColor: "transparent"
    },
    block: {
      background: hover && !disabled ? "var(--lime-press)" : "var(--lime)",
      color: "var(--text-on-accent)",
      borderRadius: "var(--radius-0)",
      borderColor: "transparent",
      padding: size === "lg" ? "22px 32px" : "17px 28px",
      letterSpacing: "-0.01em",
      textTransform: "none",
      font: `var(--weight-head) ${size === "lg" ? "18px" : "15px"}/1.2 var(--font-ui)`
    },
    invert: {
      background: hover && !disabled ? "var(--ink-80)" : "var(--black)",
      color: "var(--text-on-invert)",
      borderColor: "var(--black)"
    }
  }[variant];
  const glyph = icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: size === "lg" ? 18 : 14
  }) : null;
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    disabled: disabled,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => {
      setHover(false);
      setPress(false);
    },
    onMouseDown: () => setPress(true),
    onMouseUp: () => setPress(false),
    style: {
      ...base,
      ...skins,
      ...style
    }
  }, rest), markBadge && /*#__PURE__*/React.createElement("span", {
    style: {
      width: sizes.badge,
      height: sizes.badge,
      borderRadius: "var(--radius-pill)",
      background: "var(--black)",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none"
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: `${assetBase}/logo-mark-inverse.png`,
    alt: "",
    style: {
      width: sizes.badge * 0.72,
      height: sizes.badge * 0.72
    }
  })), iconPosition === "left" && glyph, /*#__PURE__*/React.createElement("span", null, children), iconPosition === "right" && glyph);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/IconBadge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Lime (or ink/paper) circular affordance holding one glyph — the diagonal
   arrow overlapping hero imagery in the source, carousel controls, socials. */
function IconBadge({
  icon = "arrow-down-right",
  tone = "accent",
  size = 48,
  label,
  onClick,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const skins = {
    accent: {
      background: hover ? "var(--lime-press)" : "var(--lime)",
      color: "var(--black)"
    },
    paper: {
      background: "var(--white)",
      color: "var(--black)"
    },
    ink: {
      background: hover ? "var(--ink-80)" : "var(--black)",
      color: "var(--paper)"
    },
    outline: {
      background: "transparent",
      color: "var(--text-heading)",
      border: "var(--border-outline)"
    }
  }[tone];
  const Tag = onClick ? "button" : "span";
  return /*#__PURE__*/React.createElement(Tag, _extends({
    type: onClick ? "button" : undefined,
    onClick: onClick,
    "aria-label": label,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      width: size,
      height: size,
      flex: "none",
      padding: 0,
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      borderRadius: "var(--radius-pill)",
      border: "none",
      cursor: onClick ? "pointer" : "default",
      transition: "var(--transition-control)",
      ...skins,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: Math.round(size * 0.45)
  }));
}
Object.assign(__ds_scope, { IconBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconBadge.jsx", error: String((e && e.message) || e) }); }

// components/core/Logo.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* The Dronex mark (quadcopter silhouette with a lime crosshair) plus the
   light geometric "Dronex" wordmark. Image asset lives in /assets. */
function Logo({
  variant = "lockup",
  tone = "dark",
  size = 44,
  assetBase = "../../assets",
  style,
  ...rest
}) {
  const inverse = tone === "light";
  const mark = `${assetBase}/logo-mark${inverse ? "-inverse" : ""}.png`;
  const img = /*#__PURE__*/React.createElement("img", {
    src: mark,
    alt: "Dronex",
    style: {
      width: size,
      height: size,
      display: "block",
      objectFit: "contain"
    }
  });
  if (variant === "mark") return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: "inline-flex",
      ...style
    }
  }, rest), img);
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: size * 0.22,
      color: inverse ? "var(--text-on-invert)" : "var(--text-heading)",
      ...style
    }
  }, rest), img, /*#__PURE__*/React.createElement("span", {
    style: {
      font: `var(--weight-wordmark) ${size * 1.42}px/var(--leading-wordmark) var(--font-wordmark)`,
      letterSpacing: "var(--tracking-wordmark)"
    }
  }, "Dronex"));
}
Object.assign(__ds_scope, { Logo });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Logo.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Small uppercase category label. Outline pill on paper, or filled lime. */
function Tag({
  variant = "outline",
  size = "md",
  children,
  style,
  ...rest
}) {
  const pad = size === "sm" ? "7px 14px" : "10px 20px";
  const font = size === "sm" ? "9px" : "10px";
  const skins = {
    outline: {
      background: "transparent",
      color: "var(--text-body)",
      border: "var(--border-outline)"
    },
    accent: {
      background: "var(--lime)",
      color: "var(--text-on-accent)",
      border: "var(--border-width) solid var(--lime)"
    },
    ink: {
      background: "var(--black)",
      color: "var(--text-on-invert)",
      border: "var(--border-width) solid var(--black)"
    }
  }[variant];
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: "inline-flex",
      alignSelf: "flex-start",
      alignItems: "center",
      padding: pad,
      borderRadius: "var(--radius-pill)",
      font: `var(--weight-head) ${font}/var(--leading-label) var(--font-ui)`,
      letterSpacing: "var(--tracking-label)",
      textTransform: "uppercase",
      ...skins,
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Pill field. The only input treatment in the source (newsletter capture). */
function Input({
  tone = "paper",
  placeholder = "",
  value,
  onChange,
  type = "text",
  trailing,
  full = true,
  style,
  ...rest
}) {
  const onDark = tone === "ink";
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: "flex",
      alignItems: "center",
      gap: "var(--space-2)",
      width: full ? "100%" : undefined,
      padding: trailing ? "5px 5px 5px 24px" : "16px 24px",
      background: onDark ? "transparent" : "var(--surface-field)",
      border: onDark ? "var(--border-outline-invert)" : "none",
      borderRadius: "var(--radius-field)",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("input", {
    type: type,
    value: value,
    onChange: onChange,
    placeholder: placeholder,
    style: {
      flex: 1,
      minWidth: 0,
      border: "none",
      outline: "none",
      background: "transparent",
      color: onDark ? "var(--text-on-invert)" : "var(--text-heading)",
      font: "var(--weight-head) 11px/1 var(--font-ui)",
      letterSpacing: "var(--tracking-label)",
      textTransform: "uppercase"
    }
  }), trailing);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/NewsletterForm.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Footer newsletter capture: white pill field with the lime submit docked inside. */
function NewsletterForm({
  placeholder = "YOUR EMAIL",
  cta = "Subscribe",
  onSubmit,
  style,
  ...rest
}) {
  const [value, setValue] = React.useState("");
  const [sent, setSent] = React.useState(false);
  return /*#__PURE__*/React.createElement("form", _extends({
    onSubmit: e => {
      e.preventDefault();
      setSent(true);
      onSubmit && onSubmit(value);
    },
    style: {
      width: "100%",
      maxWidth: 480,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Input, {
    type: "email",
    placeholder: placeholder,
    value: value,
    onChange: e => {
      setValue(e.target.value);
      setSent(false);
    },
    trailing: /*#__PURE__*/React.createElement(__ds_scope.Button, {
      variant: "accent",
      onClick: e => {
        e.preventDefault();
        setSent(true);
        onSubmit && onSubmit(value);
      }
    }, sent ? "Sent" : cta)
  }));
}
Object.assign(__ds_scope, { NewsletterForm });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/NewsletterForm.jsx", error: String((e && e.message) || e) }); }

// components/navigation/CarouselNav.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Previous / next pair that sits at the foot of a carousel sheet. */
function CarouselNav({
  onPrev,
  onNext,
  tone = "outline",
  size = 34,
  spread = "space-between",
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: "flex",
      justifyContent: spread,
      gap: "var(--space-3)",
      width: "100%",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.IconBadge, {
    icon: "arrow-left",
    tone: tone,
    size: size,
    label: "Previous",
    onClick: onPrev
  }), /*#__PURE__*/React.createElement(__ds_scope.IconBadge, {
    icon: "arrow-right",
    tone: tone,
    size: size,
    label: "Next",
    onClick: onNext
  }));
}
Object.assign(__ds_scope, { CarouselNav });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/CarouselNav.jsx", error: String((e && e.message) || e) }); }

// components/navigation/SiteFooter.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Black footer: social chips + newsletter on the top row, mark and link
   columns below. Children fill the top-right slot (usually NewsletterForm). */
function SiteFooter({
  columns = [],
  socials = ["instagram", "send", "facebook"],
  assetBase = "../../assets",
  children,
  note,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("footer", _extends({
    style: {
      background: "var(--surface-invert)",
      color: "var(--text-on-invert)",
      padding: "var(--space-16) var(--space-10) var(--space-10)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-20)",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "var(--space-10)",
      flexWrap: "wrap"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: "var(--space-3)"
    }
  }, socials.map(s => /*#__PURE__*/React.createElement(__ds_scope.IconBadge, {
    key: s,
    icon: s,
    tone: "paper",
    size: 38,
    label: s,
    onClick: () => {}
  }))), children), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "space-between",
      gap: "var(--space-10)",
      flexWrap: "wrap"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Logo, {
    variant: "lockup",
    tone: "light",
    size: 18,
    assetBase: assetBase
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: "var(--space-24)"
    }
  }, columns.map((col, i) => /*#__PURE__*/React.createElement("ul", {
    key: i,
    style: {
      listStyle: "none",
      margin: 0,
      padding: 0,
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-3)"
    }
  }, col.map((item, j) => /*#__PURE__*/React.createElement("li", {
    key: item,
    style: {
      font: "var(--type-label)",
      letterSpacing: "var(--tracking-label)",
      textTransform: "uppercase",
      color: j === 0 ? "var(--text-on-invert)" : "var(--text-on-invert-muted)"
    }
  }, item)))))), note && /*#__PURE__*/React.createElement("div", {
    style: {
      font: "var(--type-caption)",
      color: "var(--text-on-invert-muted)"
    }
  }, note));
}
Object.assign(__ds_scope, { SiteFooter });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/SiteFooter.jsx", error: String((e && e.message) || e) }); }

// components/navigation/SiteHeader.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Thin top bar: mark (or lockup) left, links or a hamburger right. */
function SiteHeader({
  tone = "paper",
  links = [],
  active,
  onNavigate,
  compact = false,
  assetBase = "../../assets",
  trailing,
  style,
  ...rest
}) {
  const onDark = tone === "ink";
  const ink = onDark ? "var(--text-on-invert)" : "var(--text-heading)";
  return /*#__PURE__*/React.createElement("header", _extends({
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "var(--space-8)",
      padding: compact ? "var(--space-4) var(--space-5)" : "var(--space-5) var(--space-8)",
      background: onDark ? "var(--surface-invert)" : "var(--surface-sheet)",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Logo, {
    variant: compact ? "mark" : "lockup",
    tone: onDark ? "light" : "dark",
    size: compact ? 22 : 26,
    assetBase: assetBase
  }), compact ? /*#__PURE__*/React.createElement("button", {
    type: "button",
    "aria-label": "Menu",
    style: {
      background: "none",
      border: "none",
      padding: 4,
      cursor: "pointer",
      color: ink
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "menu",
    size: 22
  })) : /*#__PURE__*/React.createElement("nav", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: "var(--space-8)"
    }
  }, links.map(l => {
    const isActive = (active || "") === l;
    return /*#__PURE__*/React.createElement("button", {
      key: l,
      type: "button",
      onClick: () => onNavigate && onNavigate(l),
      style: {
        background: "none",
        border: "none",
        padding: 0,
        cursor: "pointer",
        color: isActive ? ink : onDark ? "var(--text-on-invert-muted)" : "var(--text-body)",
        font: "var(--type-label)",
        letterSpacing: "var(--tracking-label)",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        borderBottom: isActive ? "var(--border-width) solid currentColor" : "var(--border-width) solid transparent",
        paddingBottom: 2,
        transition: "var(--transition-control)"
      }
    }, l);
  }), trailing));
}
Object.assign(__ds_scope, { SiteHeader });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/SiteHeader.jsx", error: String((e && e.message) || e) }); }

// ui_kits/dronex-site/about.screen.jsx
try { (() => {
const DS = window.DronexDesignSystem_f3f897;
function AboutScreen() {
  const {
    Tag,
    MediaFrame,
    StatCard,
    Button,
    SiteFooter,
    NewsletterForm,
    ContentCard
  } = DS;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: "var(--gap-sheet)"
    }
  }, /*#__PURE__*/React.createElement("section", {
    style: {
      display: "grid",
      gridTemplateColumns: "1.2fr 1fr",
      gap: "var(--gap-sheet)"
    }
  }, /*#__PURE__*/React.createElement(ContentCard, {
    title: "Driving the evolution of agriculture with advanced drone systems",
    titleSize: "var(--size-h1)",
    body: "We develop smart drone technologies that give farmers full control over their fields. From real-time crop monitoring to precision spraying, our solutions increase productivity while reducing resource waste and operational costs.",
    footer: /*#__PURE__*/React.createElement(Button, {
      variant: "outline",
      icon: "arrow-right",
      style: {
        alignSelf: "flex-start"
      }
    }, "About us"),
    style: {
      padding: "var(--space-16) var(--space-12)",
      gap: "var(--space-8)",
      justifyContent: "center"
    }
  }), /*#__PURE__*/React.createElement(MediaFrame, {
    src: "../../assets/imagery/farmer-portrait.png",
    alt: "Agronomist in the field at sunrise",
    ticks: "top",
    radius: "var(--radius-0)",
    style: {
      minHeight: 420
    }
  })), /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-accent)",
      padding: "var(--space-12)",
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: "var(--space-16)",
      alignItems: "end"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-6)"
    }
  }, /*#__PURE__*/React.createElement(Tag, {
    variant: "ink"
  }, "Performance"), /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      font: "var(--type-h2)",
      letterSpacing: "var(--tracking-head)",
      color: "var(--text-on-accent)",
      textWrap: "pretty"
    }
  }, "Creating measurable impact with cutting-edge drone technology")), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      font: "var(--type-body)",
      color: "var(--text-on-accent)",
      maxWidth: "48ch"
    }
  }, "Dronex helps farmers optimise every stage of crop care\u2014mapping, seeding, spraying\u2014so each pass over the field is accounted for.")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: "var(--gap-sheet)"
    }
  }, /*#__PURE__*/React.createElement(StatCard, {
    tone: "paper",
    value: "12k",
    label: "Hectares flown",
    body: "Mapped and treated across row crops, orchards and pasture in the 2025 season.",
    style: {
      minHeight: 260
    }
  }), /*#__PURE__*/React.createElement(StatCard, {
    tone: "concrete",
    value: "30%",
    label: "Less chemistry",
    body: "Average input reduction reported by farms running variable-rate spray maps.",
    style: {
      minHeight: 260
    }
  }), /*#__PURE__*/React.createElement(StatCard, {
    tone: "ink",
    value: "24h",
    label: "Support response",
    body: "Agronomy and flight-ops support, in season, from people who have flown the work.",
    style: {
      minHeight: 260
    }
  })), /*#__PURE__*/React.createElement(SiteFooter, {
    columns: [["Home", "Drones", "Services"], ["About us", "Dashboard", "Contacts"]],
    note: "\xA9 2026 Dronex \u2014 precision agriculture systems"
  }, /*#__PURE__*/React.createElement(NewsletterForm, null)));
}
Object.assign(window, {
  AboutScreen
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/dronex-site/about.screen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/dronex-site/drones.screen.jsx
try { (() => {
const DS = window.DronexDesignSystem_f3f897;
const DRONES = [{
  name: "Seeding and spreading drones are transforming",
  img: "../../assets/imagery/drone-product.png",
  body: "Dronex drones streamline seeding and spreading with consistent coverage and accurate delivery—built for modern, high-efficiency farming."
}, {
  name: "Survey and mapping drones for every season",
  img: "../../assets/imagery/farmer-walking-field.png",
  body: "Multispectral capture and centimetre-grade mapping, flown on a schedule your agronomist sets once."
}, {
  name: "Spraying drones with variable rate control",
  img: "../../assets/imagery/hand-controller.png",
  body: "Rate maps follow the terrain, so chemistry lands where the crop needs it and nowhere else."
}];
function DroneCard({
  item
}) {
  const {
    MediaFrame,
    Button
  } = DS;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: "var(--surface-sheet)",
      padding: "var(--space-6)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-5)"
    }
  }, /*#__PURE__*/React.createElement(MediaFrame, {
    src: item.img,
    alt: item.name,
    ratio: "16 / 10",
    ticks: "top",
    tickTone: "dark",
    zoomOnHover: true
  }), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      font: "var(--type-h3)",
      letterSpacing: "var(--tracking-head)",
      color: "var(--text-heading)",
      textWrap: "pretty"
    }
  }, item.name), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      font: "var(--type-body-sm)",
      color: "var(--text-body)",
      flex: 1
    }
  }, item.body), /*#__PURE__*/React.createElement(Button, {
    variant: "pill",
    markBadge: true,
    style: {
      alignSelf: "flex-start"
    }
  }, "Discover Dronex"));
}
function DronesScreen() {
  const {
    Tag,
    Button,
    CarouselNav,
    SiteFooter,
    NewsletterForm
  } = DS;
  const [offset, setOffset] = React.useState(0);
  const items = DRONES.map((_, i) => DRONES[(i + offset) % DRONES.length]);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: "var(--gap-sheet)"
    }
  }, /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-sheet)",
      padding: "var(--space-16) var(--space-12) var(--space-12)",
      display: "grid",
      gridTemplateColumns: "1.25fr 1fr",
      gap: "var(--space-16)",
      alignItems: "end"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-6)"
    }
  }, /*#__PURE__*/React.createElement(Tag, null, "Precision"), /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      font: "var(--type-h1)",
      letterSpacing: "var(--tracking-head)",
      color: "var(--text-heading)",
      textWrap: "pretty"
    }
  }, "Seed and Spread Smarter: Precision Drones for Field Operations")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-6)"
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      font: "var(--type-body)",
      color: "var(--text-body)",
      maxWidth: "46ch"
    }
  }, "Every airframe in the range is specified around one job on the farm\u2014survey, seeding, or spraying\u2014so crews fly less and cover more."), /*#__PURE__*/React.createElement(Button, {
    variant: "block",
    full: true
  }, "Survey & Mapping Drones"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: "var(--gap-sheet)"
    }
  }, items.map((item, i) => /*#__PURE__*/React.createElement(DroneCard, {
    key: i + item.name,
    item: item
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "var(--surface-sheet)",
      padding: "var(--space-5) var(--space-6)"
    }
  }, /*#__PURE__*/React.createElement(CarouselNav, {
    onPrev: () => setOffset(o => (o + DRONES.length - 1) % DRONES.length),
    onNext: () => setOffset(o => (o + 1) % DRONES.length)
  })), /*#__PURE__*/React.createElement(SiteFooter, {
    columns: [["Home", "Drones", "Services"], ["About us", "Dashboard", "Contacts"]],
    note: "\xA9 2026 Dronex \u2014 precision agriculture systems"
  }, /*#__PURE__*/React.createElement(NewsletterForm, null)));
}
Object.assign(window, {
  DronesScreen,
  DroneCard
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/dronex-site/drones.screen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/dronex-site/home.screen.jsx
try { (() => {
const DS = window.DronexDesignSystem_f3f897;
function HeroBand() {
  const {
    MediaFrame,
    StatCard,
    Logo,
    Button
  } = DS;
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1.5fr 1fr 1fr",
      gap: "var(--gap-sheet)",
      height: 430
    }
  }, /*#__PURE__*/React.createElement(MediaFrame, {
    src: "../../assets/imagery/farmer-wheat.png",
    alt: "Agronomist inspecting a wheat field",
    ticks: "top",
    radius: "var(--radius-0)",
    style: {
      height: "100%"
    }
  }), /*#__PURE__*/React.createElement(StatCard, {
    tone: "concrete",
    value: "10+",
    label: "Years of Expertise",
    body: "Over a decade of experience in agri-tech, delivering proven drone solutions tailored to real farming needs. Our expertise helps farms improve efficiency and maximize yields."
  }), /*#__PURE__*/React.createElement(StatCard, {
    tone: "accent",
    value: "85%",
    label: "Client Satisfaction",
    body: "Trusted by farmers for reliable performance, responsive support, and technology that delivers measurable results in the field across different crops and seasons year after year."
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "var(--surface-sheet)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 var(--space-12)",
      height: 184
    }
  }, /*#__PURE__*/React.createElement(Logo, {
    size: 58
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: "var(--space-3)"
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "outline"
  }, "Seed smarter"), /*#__PURE__*/React.createElement(Button, {
    variant: "outline"
  }, "Grow more"))));
}
function HomeScreen() {
  const {
    MediaFrame,
    SiteFooter,
    NewsletterForm
  } = DS;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: "var(--gap-sheet)"
    }
  }, /*#__PURE__*/React.createElement(HeroBand, null), /*#__PURE__*/React.createElement(MediaFrame, {
    src: "../../assets/imagery/drone-combine-field.png",
    alt: "Spraying drone flying beside a combine harvester",
    ratio: "16 / 7",
    ticks: "all",
    tickTone: "dark",
    radius: "var(--radius-0)"
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      position: "absolute",
      right: "9%",
      top: "38%",
      transform: "translateY(-50%)",
      margin: 0,
      font: "var(--type-h1)",
      letterSpacing: "var(--tracking-head)",
      color: "var(--text-heading)",
      textWrap: "pretty"
    }
  }, "Smarter spreading.", /*#__PURE__*/React.createElement("br", null), "Better yields")), /*#__PURE__*/React.createElement(SiteFooter, {
    columns: [["Home", "Drones", "Services"], ["About us", "Dashboard", "Contacts"]],
    note: "\xA9 2026 Dronex \u2014 precision agriculture systems"
  }, /*#__PURE__*/React.createElement(NewsletterForm, null)));
}
Object.assign(window, {
  HomeScreen,
  HeroBand
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/dronex-site/home.screen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/dronex-site/mobile.screen.jsx
try { (() => {
const DS = window.DronexDesignSystem_f3f897;
function MobileScreen() {
  const {
    SiteHeader,
    Logo,
    MediaFrame,
    IconBadge,
    Button,
    Tag,
    ContentCard,
    CarouselNav
  } = DS;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width: 390,
      background: "var(--surface-sheet)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--gap-sheet)",
      borderRadius: "var(--radius-card)",
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement(SiteHeader, {
    compact: true
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "var(--surface-sheet)",
      padding: "0 var(--page-margin-mobile) var(--space-4)"
    }
  }, /*#__PURE__*/React.createElement(Logo, {
    size: 32
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative",
      padding: "0 var(--page-margin-mobile)"
    }
  }, /*#__PURE__*/React.createElement(MediaFrame, {
    src: "../../assets/imagery/farmer-walking-field.png",
    alt: "Farmer walking a field under a survey drone",
    ratio: "4 / 5",
    ticks: "none",
    radius: "var(--radius-0)"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      left: 0,
      right: 0,
      bottom: 20,
      display: "flex",
      justifyContent: "center"
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "pill",
    markBadge: true
  }, "Discover Dronex"))), /*#__PURE__*/React.createElement(IconBadge, {
    icon: "arrow-down-right",
    size: 56,
    style: {
      position: "absolute",
      top: -18,
      right: 10
    }
  })), /*#__PURE__*/React.createElement(ContentCard, {
    title: "Driving the evolution of agriculture with advanced drone systems",
    titleSize: "var(--size-h3)",
    body: "We develop smart drone technologies that give farmers full control over their fields. From real-time crop monitoring to precision spraying, our solutions increase productivity while reducing resource waste and operational costs.",
    media: /*#__PURE__*/React.createElement(MediaFrame, {
      src: "../../assets/imagery/hand-controller.png",
      alt: "Hands on a drone controller",
      ratio: "16 / 9",
      ticks: "none",
      radius: "var(--radius-0)"
    }),
    style: {
      padding: "var(--space-6) var(--page-margin-mobile) var(--space-8)",
      gap: "var(--space-5)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement(MediaFrame, {
    src: "../../assets/imagery/farmer-wheat.png",
    alt: "",
    ticks: "none",
    radius: "var(--radius-0)",
    style: {
      width: 52,
      height: 32
    }
  }), /*#__PURE__*/React.createElement(Logo, {
    size: 13
  }))), /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-accent)",
      padding: "var(--space-6) var(--page-margin-mobile) var(--space-8)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-5)"
    }
  }, /*#__PURE__*/React.createElement(Tag, {
    variant: "ink",
    size: "sm"
  }, "Performance"), /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      font: "var(--type-h3)",
      letterSpacing: "var(--tracking-head)",
      color: "var(--text-on-accent)",
      textWrap: "pretty"
    }
  }, "Creating measurable impact with cutting-edge drone technology"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      font: "var(--type-body-sm)",
      color: "var(--text-on-accent)"
    }
  }, "Dronex helps farmers optimise every stage of crop care.")), /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-sheet)",
      padding: "var(--space-6) var(--page-margin-mobile)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-5)"
    }
  }, /*#__PURE__*/React.createElement(Tag, {
    size: "sm"
  }, "Precision"), /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      font: "var(--type-h2)",
      letterSpacing: "var(--tracking-head)",
      color: "var(--text-heading)",
      textWrap: "pretty"
    }
  }, "Seed and Spread Smarter: Precision Drones for Field Operations"), /*#__PURE__*/React.createElement(Button, {
    variant: "block",
    full: true
  }, "Survey & Mapping Drones"), /*#__PURE__*/React.createElement(MediaFrame, {
    src: "../../assets/imagery/drone-product.png",
    alt: "Dronex survey drone",
    ratio: "16 / 9",
    ticks: "all",
    tickTone: "dark",
    radius: "var(--radius-0)"
  }), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      font: "var(--type-h3)",
      letterSpacing: "var(--tracking-head)",
      color: "var(--text-heading)"
    }
  }, "Seeding and spreading drones are transforming"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      font: "var(--type-body-sm)",
      color: "var(--text-body)"
    }
  }, "Dronex drones streamline seeding and spreading with consistent coverage and accurate delivery\u2014built for modern, high-efficiency farming."), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "center"
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "pill",
    markBadge: true
  }, "Discover Dronex")), /*#__PURE__*/React.createElement(CarouselNav, null)));
}
Object.assign(window, {
  MobileScreen
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/dronex-site/mobile.screen.jsx", error: String((e && e.message) || e) }); }

__ds_ns.ContentCard = __ds_scope.ContentCard;

__ds_ns.MediaFrame = __ds_scope.MediaFrame;

__ds_ns.StatCard = __ds_scope.StatCard;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.IconBadge = __ds_scope.IconBadge;

__ds_ns.Logo = __ds_scope.Logo;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.NewsletterForm = __ds_scope.NewsletterForm;

__ds_ns.CarouselNav = __ds_scope.CarouselNav;

__ds_ns.SiteFooter = __ds_scope.SiteFooter;

__ds_ns.SiteHeader = __ds_scope.SiteHeader;

})();
