%% 90_national_at.lp — Austria (Austro Control) national overrides.
%%
%% EU 2019/947 leaves specific decisions to the member state, and Austria's national
%% annex is where they live. Overrides are written with the default→override pattern from
%% 00_core.lp, so they defeat a core conclusion without editing it.
%%
%% NOTHING IS TRANSCRIBED YET. The Austrian annex has not been supplied, so this file
%% deliberately asserts nothing. An empty national pack is the correct state when the
%% document is not in hand: the alternative is a guess about another country's law.
%%
%% The contract, for whoever transcribes it:
%%
%%   grc_override(V, "at.grc.<rule>")          :- country(at), <conditions>.
%%   arc_residual_override(R, "at.arc.<rule>") :- country(at), <conditions>.
%%   oso_override(Oso, Level, "at.oso.<rule>") :- country(at), <conditions>.
%%
%% Each override's rule id must be added to tables/citations.csv pointing at the clause
%% of the annex that justifies it, or the trace formatter will refuse the node.

%% Austria uses the EU baseline until its annex is transcribed. Recorded as a conclusion
%% so the trace states it rather than leaving a silent gap.
national_baseline(at) :- country(at).
conclusion_atom(national_baseline(at)) :- national_baseline(at).
because(national_baseline(at), "at.baseline", (country(at),)) :- national_baseline(at).
