// Plain-language summary of each OSO and the evidence that typically satisfies it.
// Wording is ours; the normative text is the rulebase (SORA 2.5 Annex E).
// VERIFY BEFORE PRODUCTION alongside src/engine/rulebase.ts.

export const OSO_TEXT: Record<number, { requires: string; evidence: string[] }> = {
  1: { requires: "The operator shows it has the organisation, procedures and experience to run this operation safely.", evidence: ["Operations manual covering this operation type", "Record of comparable operations flown", "Safety management or occurrence-reporting procedure"] },
  2: { requires: "The aircraft is built under controlled manufacturing so that each unit matches the design that was assessed.", evidence: ["Manufacturer quality statement", "Configuration and serial-number record", "Incoming inspection checklist"] },
  3: { requires: "Maintenance is planned, recorded and performed by people trained for this aircraft.", evidence: ["Maintenance programme", "Maintenance log for this airframe", "Maintenance staff training record"] },
  4: { requires: "Components whose failure could lead to loss of control are designed to a recognised airworthiness design standard.", evidence: ["Design standard compliance statement", "Component list with criticality", "Manufacturer declaration"] },
  5: { requires: "The design addresses failure conditions whose effects could reach the ground risk buffer.", evidence: ["Functional hazard assessment covering the failure set", "Manufacturer reliability statement or service history", "Third-party validation record"] },
  6: { requires: "The command, control and communication link has the range, latency and robustness the operation needs.", evidence: ["Link budget for the flight geography", "Spectrum authorisation", "Link-loss procedure and test record"] },
  7: { requires: "Before each flight the aircraft configuration is checked against the configuration that was assessed.", evidence: ["Pre-flight conformity checklist", "Configuration baseline document"] },
  8: { requires: "Normal, contingency and emergency procedures exist, have been validated, and are followed.", evidence: ["Normal procedures", "Contingency and emergency procedures", "Validation record (simulation or flight test)"] },
  9: { requires: "The remote crew is trained for this operation and keeps that training current.", evidence: ["Training syllabus", "Crew training and currency records", "Competency check results"] },
  13: { requires: "External services the operation depends on — positioning, weather, U-space — are adequate and monitored.", evidence: ["List of external services with performance needed", "Service-level agreements or availability evidence", "Procedure for loss of a service"] },
  16: { requires: "Where more than one person is involved, roles and communication are defined and practised.", evidence: ["Crew roles and responsibilities", "Communication procedure and phraseology", "Crew resource management training"] },
  17: { requires: "The remote crew is fit to operate: rested, not impaired, and within duty limits.", evidence: ["Fitness-to-fly policy", "Duty and rest limits", "Self-declaration record"] },
  18: { requires: "The aircraft automatically prevents the crew from flying it outside its safe flight envelope.", evidence: ["Flight-envelope protection description", "Test evidence for envelope limits"] },
  19: { requires: "The operation can recover safely from foreseeable human error.", evidence: ["Human-error analysis", "Recovery procedures", "Test or training evidence"] },
  20: { requires: "The human–machine interface has been evaluated and is appropriate for the task.", evidence: ["Human factors evaluation", "Ground control station description", "Crew feedback record"] },
  23: { requires: "Weather and environmental limits are defined, measurable during the operation, and respected.", evidence: ["Environmental limits (wind, temperature, precipitation)", "Means of measuring conditions on site", "Go/no-go procedure"] },
  24: { requires: "The aircraft is designed and qualified for the adverse conditions it may meet.", evidence: ["Environmental qualification statement", "Ingress protection rating", "Test or service evidence in adverse conditions"] },
};

export const ASSURANCE: Record<"low" | "medium" | "high", string> = {
  low: "At low robustness the applicant declares compliance.",
  medium: "At medium robustness the claim must be supported by evidence such as analysis, test or service history.",
  high: "At high robustness the evidence must be validated by a competent third party.",
};
