%% 30_arc.lp — Step 4: initial air risk class, then the residual after strategic
%% mitigation.
%%
%% The decision tree is transcribed as ORDERED rows in arc.csv, each with a priority.
%% The first row whose conditions all hold wins, which is how a tree's precedence
%% survives being flattened into a table. "*" is a wildcard.

%% ---------------------------------------------------------------- the altitude band

alt_band(above_500ft) :- alt_cm(A), threshold(altitude_band_500ft, T), A > T.
alt_band(below_500ft) :- alt_cm(A), threshold(altitude_band_500ft, T), A <= T.

conclusion_atom(alt_band(B)) :- alt_band(B).
because(alt_band(B), "sora25.arc.altitude_band", (alt_cm(A), threshold(altitude_band_500ft, T))) :-
    alt_band(B), alt_cm(A), threshold(altitude_band_500ft, T).

%% ---------------------------------------------------------------- the environment

%% Urban is derived, not asked: a populated or assembly ground environment is urban for
%% the purposes of the air risk tree.
environment(urban) :- ground_env(populated).
environment(urban) :- ground_env(assembly_of_people).
environment(rural) :- ground_env(sparsely_populated).
environment(rural) :- ground_env(controlled_ground_area).

conclusion_atom(environment(E)) :- environment(E).
because(environment(E), "sora25.arc.environment", (ground_env(G),)) :-
    environment(E), ground_env(G).

%% ---------------------------------------------------------------- the ordered tree

%% One match predicate per column. The pattern argument is bound by the table row, so
%% each rule is safe to ground; the wildcard and the literal case are separate rules
%% rather than a disjunction.
arc_m_atyp(P)  :- arc_rule(_, P, _, _, _, _, _, _, _), wildcard(P).
arc_m_atyp(P)  :- arc_rule(_, P, _, _, _, _, _, _, _), flag_value(atypical, P).
arc_m_alt(P)   :- arc_rule(_, _, P, _, _, _, _, _, _), wildcard(P).
arc_m_alt(P)   :- arc_rule(_, _, P, _, _, _, _, _, _), alt_band(P).
arc_m_ctrl(P)  :- arc_rule(_, _, _, P, _, _, _, _, _), wildcard(P).
arc_m_ctrl(P)  :- arc_rule(_, _, _, P, _, _, _, _, _), flag_value(controlled, P).
arc_m_aero(P)  :- arc_rule(_, _, _, _, P, _, _, _, _), wildcard(P).
arc_m_aero(P)  :- arc_rule(_, _, _, _, P, _, _, _, _), flag_value(aerodrome, P).
arc_m_class(P) :- arc_rule(_, _, _, _, _, P, _, _, _), wildcard(P).
arc_m_class(P) :- arc_rule(_, _, _, _, _, P, _, _, _), airspace_class(P).
arc_m_env(P)   :- arc_rule(_, _, _, _, _, _, P, _, _), wildcard(P).
arc_m_env(P)   :- arc_rule(_, _, _, _, _, _, P, _, _), environment(P).

arc_row_matches(P) :-
    arc_rule(P, Atyp, Alt, Ctrl, Aero, Class, Env, _, _),
    arc_m_atyp(Atyp), arc_m_alt(Alt), arc_m_ctrl(Ctrl),
    arc_m_aero(Aero), arc_m_class(Class), arc_m_env(Env).

arc_first_match(P) :- P = #min{ Q : arc_row_matches(Q) }, arc_row_matches(_).

arc_rule_fired(RuleId) :- arc_first_match(P), arc_rule(P, _, _, _, _, _, _, _, RuleId).

arc_initial(A) :- arc_first_match(P), arc_rule(P, _, _, _, _, _, _, A, _).

conclusion_atom(arc_initial(A)) :- arc_initial(A).
conclusion_atom(arc_rule_fired(R)) :- arc_rule_fired(R).

because(arc_initial(A), RuleId, (alt_band(Alt), airspace_class(Class), environment(Env))) :-
    arc_initial(A), arc_first_match(P), arc_rule(P, _, _, _, _, _, _, A, RuleId),
    alt_band(Alt), airspace_class(Class), environment(Env).

because(arc_rule_fired(R), "sora25.arc.tree", (arc_initial(A),)) :-
    arc_rule_fired(R), arc_initial(A).

%% The tree must be total. A mission that matches no row is a transcription gap, and it
%% should stop the run rather than default to a class.
:- not arc_row_matches(_).

%% ---------------------------------------------------------------- residual ARC

arc_residual_default(R) :-
    arc_initial(A), flag_value(strategic, S), arc_residual_rule(A, S, R, _).

arc_residual_overridden :- arc_residual_override(_, _).
arc_residual(R) :- arc_residual_default(R), not arc_residual_overridden.
arc_residual(R) :- arc_residual_override(R, _).

conclusion_atom(arc_residual(R)) :- arc_residual(R).

because(arc_residual(R), RuleId, (arc_initial(A), mitigation(strategic_air, Rob))) :-
    arc_residual(R), arc_residual_default(R), not arc_residual_overridden,
    arc_initial(A), flag_value(strategic, S), arc_residual_rule(A, S, R, RuleId),
    mitigation(strategic_air, Rob).

because(arc_residual(R), RuleId, (arc_initial(A),)) :-
    arc_residual(R), arc_residual_default(R), not arc_residual_overridden,
    arc_initial(A), flag_value(strategic, S), arc_residual_rule(A, S, R, RuleId),
    not mitigation(strategic_air, _).

because(arc_residual(R), RuleId, (arc_residual_default(D),)) :-
    arc_residual(R), arc_residual_override(R, RuleId), arc_residual_default(D).

tainted_conclusion(arc) :- arc_initial(_), tainted(arc).
tainted_conclusion(arc_residual) :- arc_residual(_), tainted(arc_residual).

%% ---------------------------------------------------------------- TMPR

tmpr(T) :- arc_residual(R), tmpr_rule(R, T, _).
conclusion_atom(tmpr(T)) :- tmpr(T).
because(tmpr(T), RuleId, (arc_residual(R),)) :-
    tmpr(T), arc_residual(R), tmpr_rule(R, T, RuleId).

tainted_conclusion(tmpr) :- tmpr(_), tainted(tmpr).
