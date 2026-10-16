%% 30_arc.lp — Step #4: the initial air risk class, Step #5: the residual after
%% strategic mitigation, and Step #6: the TMPR that follows from it.
%%
%% Annex C Table C.1 is transcribed as ORDERED rows in arc.csv, each carrying its
%% airspace encounter class (AEC) and a priority. The first row whose conditions all
%% hold wins, which is how the Figure 6 decision tree's precedence survives being
%% flattened into a table. "*" is a wildcard.

%% ---------------------------------------------------------------- the altitude band

%% Three bands, not two. Table C.1 has a category above flight level 600 (AEC 11) where
%% the encounter rate falls again, and leaving it out would score a stratospheric
%% operation as if it were at 400 ft.
alt_band(above_fl600) :- alt_cm(A), threshold(altitude_fl600, F), A > F.
alt_band(above_150m)  :- alt_cm(A), threshold(altitude_band_150m, T), threshold(altitude_fl600, F),
                         A > T, A <= F.
alt_band(below_150m)  :- alt_cm(A), threshold(altitude_band_150m, T), A <= T.

conclusion_atom(alt_band(B)) :- alt_band(B).
because(alt_band(B), "sora25.arc.altitude_band", (alt_cm(A), threshold(altitude_band_150m, T))) :-
    alt_band(B), alt_cm(A), threshold(altitude_band_150m, T).

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

%% ---------------------------------------------------------------- the ordered table

%% One match predicate per column. The pattern argument is bound by the table row, so
%% each rule is safe to ground; the wildcard and the literal case are separate rules
%% rather than a disjunction.
arc_m_atyp(P)  :- arc_rule(_, _, P, _, _, _, _, _, _, _, _), wildcard(P).
arc_m_atyp(P)  :- arc_rule(_, _, P, _, _, _, _, _, _, _, _), flag_value(atypical, P).
arc_m_alt(P)   :- arc_rule(_, _, _, P, _, _, _, _, _, _, _), wildcard(P).
arc_m_alt(P)   :- arc_rule(_, _, _, P, _, _, _, _, _, _, _), alt_band(P).
arc_m_tmz(P)   :- arc_rule(_, _, _, _, P, _, _, _, _, _, _), wildcard(P).
arc_m_tmz(P)   :- arc_rule(_, _, _, _, P, _, _, _, _, _, _), flag_value(tmz, P).
arc_m_ctrl(P)  :- arc_rule(_, _, _, _, _, P, _, _, _, _, _), wildcard(P).
arc_m_ctrl(P)  :- arc_rule(_, _, _, _, _, P, _, _, _, _, _), flag_value(controlled, P).
arc_m_aero(P)  :- arc_rule(_, _, _, _, _, _, P, _, _, _, _), wildcard(P).
arc_m_aero(P)  :- arc_rule(_, _, _, _, _, _, P, _, _, _, _), flag_value(aerodrome, P).
arc_m_class(P) :- arc_rule(_, _, _, _, _, _, _, P, _, _, _), wildcard(P).
arc_m_class(P) :- arc_rule(_, _, _, _, _, _, _, P, _, _, _), airspace_class(P).
arc_m_env(P)   :- arc_rule(_, _, _, _, _, _, _, _, P, _, _), wildcard(P).
arc_m_env(P)   :- arc_rule(_, _, _, _, _, _, _, _, P, _, _), environment(P).

arc_row_matches(P) :-
    arc_rule(P, _, Atyp, Alt, Tmz, Ctrl, Aero, Class, Env, _, _),
    arc_m_atyp(Atyp), arc_m_alt(Alt), arc_m_tmz(Tmz), arc_m_ctrl(Ctrl),
    arc_m_aero(Aero), arc_m_class(Class), arc_m_env(Env).

arc_first_match(P) :- P = #min{ Q : arc_row_matches(Q) }, arc_row_matches(_).

arc_rule_fired(RuleId) :- arc_first_match(P), arc_rule(P, _, _, _, _, _, _, _, _, _, RuleId).

arc_initial(A) :- arc_first_match(P), arc_rule(P, _, _, _, _, _, _, _, _, A, _).

%% The AEC is a conclusion in its own right: it is what keys the reduction table, and an
%% authority reads it as the airspace class of the assessment.
arc_aec(Aec) :- arc_first_match(P), arc_rule(P, Aec, _, _, _, _, _, _, _, _, _).

conclusion_atom(arc_initial(A)) :- arc_initial(A).
conclusion_atom(arc_aec(E)) :- arc_aec(E).
conclusion_atom(arc_rule_fired(R)) :- arc_rule_fired(R).

because(arc_initial(A), RuleId, (alt_band(Alt), airspace_class(Class), environment(Env))) :-
    arc_initial(A), arc_first_match(P), arc_rule(P, _, _, _, _, _, _, _, _, A, RuleId),
    alt_band(Alt), airspace_class(Class), environment(Env).

because(arc_aec(Aec), RuleId, (arc_initial(A),)) :-
    arc_aec(Aec), arc_initial(A), arc_first_match(P),
    arc_rule(P, Aec, _, _, _, _, _, _, _, _, RuleId).

because(arc_rule_fired(R), "sora25.arc.tree", (arc_initial(A),)) :-
    arc_rule_fired(R), arc_initial(A).

%% The table must be total. A mission that matches no row is a transcription gap, and it
%% should stop the run rather than default to a class.
:- not arc_row_matches(_).

%% ---------------------------------------------------------------- residual ARC

%% Table C.2 does not sell a class reduction for a claimed mitigation; it sells one for
%% a DEMONSTRATED local density rating, lower than the generalised rating Table C.1
%% assigns the environment. Without that demonstration there is no row, and the residual
%% ARC is the initial one.
arc_residual_default(R) :-
    arc_aec(Aec), arc_initial(A), strategic_claimed,
    demonstrated_air_density(D), arc_residual_rule(Aec, A, D, R, _).

arc_residual_default(A) :-
    arc_initial(A), not arc_reduction_available.

arc_reduction_available :-
    arc_aec(Aec), arc_initial(A), strategic_claimed,
    demonstrated_air_density(D), arc_residual_rule(Aec, A, D, _, _).

arc_residual_overridden :- arc_residual_override(_, _).
arc_residual(R) :- arc_residual_default(R), not arc_residual_overridden.
arc_residual(R) :- arc_residual_override(R, _).

conclusion_atom(arc_residual(R)) :- arc_residual(R).

because(arc_residual(R), RuleId, (arc_aec(Aec), demonstrated_air_density(D), mitigation(strategic_air, Rob))) :-
    arc_residual(R), not arc_residual_overridden, arc_reduction_available,
    arc_aec(Aec), arc_initial(A), demonstrated_air_density(D),
    arc_residual_rule(Aec, A, D, R, RuleId), mitigation(strategic_air, Rob).

because(arc_residual(R), "sora25.arc.residual.none", (arc_initial(R),)) :-
    arc_residual(R), not arc_residual_overridden, not arc_reduction_available,
    arc_initial(R).

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
