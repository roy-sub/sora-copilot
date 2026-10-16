%% 00_core.lp — types, the justification contract, and the closed-world declarations.
%%
%% THE JUSTIFICATION CONTRACT
%%
%% Every conclusion this rulebase derives must carry a because/3 atom naming the rule
%% that fired and the premises it rested on. The integrity constraint at the bottom of
%% this file makes a model UNSATISFIABLE if any conclusion lacks one.
%%
%% That is the whole point: a determination without a complete trace cannot be produced.
%% Not produced-and-flagged — not produced. The trace formatter reads because/3 only.
%%
%% Pattern to follow in every rule:
%%
%%   conclusion(V) :- premises...
%%   because(conclusion(V), "rule.id", (premise1, premise2)) :- premises...
%%
%% and declare the conclusion so the constraint covers it:
%%
%%   conclusion_atom(conclusion(V)) :- conclusion(V).

#const unset = unset.

%% ---------------------------------------------------------------- domains

sail_roman("I").  sail_roman("II").  sail_roman("III").
sail_roman("IV"). sail_roman("V").   sail_roman("VI").

%% The SAIL ordering, so counterfactuals and containment ranges can compare them.
sail_index("I", 1). sail_index("II", 2). sail_index("III", 3).
sail_index("IV", 4). sail_index("V", 5). sail_index("VI", 6).

arc_class(a). arc_class(b). arc_class(c). arc_class(d).
arc_index(a, 1). arc_index(b, 2). arc_index(c, 3). arc_index(d, 4).

robustness(none). robustness(low). robustness(medium). robustness(high).
robustness_index(none, 0). robustness_index(low, 1).
robustness_index(medium, 2). robustness_index(high, 3).

ground_environment(controlled_ground_area).
ground_environment(sparsely_populated).
ground_environment(populated).
ground_environment(assembly_of_people).

operation_kind(vlos). operation_kind(evlos). operation_kind(bvlos).

airspace_letter(a). airspace_letter(b). airspace_letter(c). airspace_letter(d).
airspace_letter(e). airspace_letter(f). airspace_letter(g).

%% ---------------------------------------------------------------- input sanity

%% Exactly one of each required fact. A mission that does not supply them is a bug in
%% facts.py, and it should fail here rather than produce half a determination.
:- not fact_count(ground_env, 1).
:- not fact_count(airspace_class, 1).
:- not fact_count(operation_type, 1).
:- not fact_count(dim_cm, 1).
:- not fact_count(speed_cms, 1).
:- not fact_count(alt_cm, 1).

fact_count(ground_env, N)     :- N = #count{ E : ground_env(E) }.
fact_count(airspace_class, N) :- N = #count{ C : airspace_class(C) }.
fact_count(operation_type, N) :- N = #count{ O : operation_type(O) }.
fact_count(dim_cm, N)         :- N = #count{ V : dim_cm(V) }.
fact_count(speed_cms, N)      :- N = #count{ V : speed_cms(V) }.
fact_count(alt_cm, N)         :- N = #count{ V : alt_cm(V) }.

%% ---------------------------------------------------------------- helpers

%% A threshold that the tables did not define is a transcription gap, not a default.
:- not threshold(altitude_band_150m, _).
:- not threshold(small_ua_mtom, _).
:- not threshold(small_ua_speed, _).
:- not threshold(grc_certified_ceiling, _).

%% The ordered decision tables use "*" as a wildcard. Matching cannot be written as a
%% generative matches/2 rule — both arguments would be unbound and the program would not
%% ground — so each table position gets its own match predicate whose pattern argument is
%% bound by the table row itself. See the arc_*_match rules in 30_arc.lp.
wildcard("*").

%% Boolean mission facts, rendered as the SAME constants the CSV generator emits for
%% true/false cells. A string here and a constant there would ground cleanly and then
%% match nothing, which is the worst kind of bug in a table-driven rulebase.
flag_value(atypical, true)    :- atypical_airspace.
flag_value(atypical, false)   :- not atypical_airspace.
flag_value(controlled, true)  :- controlled_airspace.
flag_value(controlled, false) :- not controlled_airspace.
flag_value(aerodrome, true)   :- near_aerodrome.
flag_value(aerodrome, false)  :- not near_aerodrome.
flag_value(tmz, true)         :- transponder_mandatory_zone.
flag_value(tmz, false)        :- not transponder_mandatory_zone.
flag_value(strategic, true)   :- strategic_claimed.
flag_value(strategic, false)  :- not strategic_claimed.
strategic_claimed :- mitigation(strategic_air, R), R != none.

%% ---------------------------------------------------------------- UNVERIFIED tainting

%% A conclusion drawn from a table that has not been checked against the official
%% document is tainted, and the taint rides all the way out to the user. This is how
%% "no invented regulatory values" becomes visible rather than merely true.
tainted(Table) :- table_unverified(Table).

%% ---------------------------------------------------------------- the contract

justified(X) :- because(X, _, _).

%% The constraint that makes the contract real.
:- conclusion_atom(X), not justified(X).

%% A conclusion may not be justified twice by different rules: that means two rules
%% fired for the same value and the rulebase is ambiguous.
:- conclusion_atom(X), #count{ R : because(X, R, _) } > 1.

#show because/3.
#show conclusion_atom/1.
#show igrc/1.
#show grc/1.
#show arc_initial/1.
#show arc_residual/1.
#show sail/1.
#show oso_required/2.
#show containment/2.
#show tmpr/1.
#show out_of_scope/1.
#show tainted/1.
#show rulebase_version/1.
#show igrc_column_used/1.
#show ground_band/1.
#show grc_mitigation_applied/3.
#show arc_rule_fired/1.
#show threshold/2.
