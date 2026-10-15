export const TIERS = [
  { name: "Free", price: "€0", unit: "category checker only", cta: "START", href: "/checker", feats: ["Open / specific / certified determination", "Estimated SAIL, no dossier", "No account required"] },
  { name: "Per dossier", price: "€149", unit: "one authority-ready dossier", cta: "BUY ONE", href: "/app/settings/", feats: ["Full derivation trace", "DOCX export", "Rulebase pinning for 12 months"] },
  { name: "Pro", price: "€89", unit: "per month, one operator", cta: "START PRO", href: "/app/settings/", feats: ["Unlimited determinations", "Unlimited dossiers", "Fleet records and evidence vault", "Counterfactual advisor"] },
  { name: "Team", price: "€249", unit: "per month, five seats", cta: "START TEAM", href: "/app/settings/", feats: ["Everything in Pro", "Shared fleet and evidence", "Review and approval states", "Audit log export"] },
  { name: "Consultancy", price: "Contact", unit: "per client workspace", cta: "TALK TO US", href: "mailto:sales@soracopilot.eu", feats: ["Unlimited client workspaces", "White-label dossier cover", "National annex requests", "Data region selection"] },
];

export const FAQ = [
  ["Does SORA Copilot grant my authorisation?", "No. It prepares and verifies the assessment. Your national aviation authority grants the authorisation. The disclaimer appears on the verdict screen and in every export."],
  ["Which rulebase does a determination use?", "The one pinned to your organisation at the moment of the run. The version and date are stamped on the determination and carried into the dossier, so a result is reproducible months later."],
  ["What happens to facts I describe in prose?", "They arrive as unconfirmed chips. Nothing reaches the engine until you confirm it. The boundary between extraction and computation is visible in the interface."],
  ["Can I see why a SAIL came out the way it did?", "Every node of the derivation tree names the rule that fired and cites the clause. The raw facts sit at the leaves. Expand any branch down to the input."],
  ["Which authorities is it built against?", "JARUS SORA 2.5 as adopted under EU 2019/947, with national annexes for Austria, Germany and the Netherlands. Others on request."],
] as const;
