%% 60_containment.lp — Step 9: containment.
%%
%% The build spec wants containment computed from a transcribed table; the design phase
%% deliberately computed nothing, because containment depends on the adjacent area.
%% PLAN.md section 6.4 records the resolution: follow the spec, but WHILE THE TABLE IS
%% UNVERIFIED every row yields assessment_required and no level.
%%
%% So the honest output today is "assessment required". When the containment section is
%% transcribed, the rows gain levels and this file needs no change.

adjacent_flag(true)  :- adjacent_area_populated.
adjacent_flag(false) :- not adjacent_area_populated.

%% Same bound-pattern shape as the ARC table; see 30_arc.lp.
cont_m_adj(P) :- containment_rule(_, _, _, P, _, _, _), wildcard(P).
cont_m_adj(P) :- containment_rule(_, _, _, P, _, _, _), adjacent_flag(P).

containment_row_matches(C) :-
    containment_rule(C, MinS, MaxS, Adj, _, _, _),
    sail(S), sail_index(S, Si), sail_index(MinS, Lo), sail_index(MaxS, Hi),
    Si >= Lo, Si <= Hi,
    cont_m_adj(Adj).

containment_first(C) :- C = #min{ D : containment_row_matches(D) }, containment_row_matches(_).

containment(Level, Required) :-
    containment_first(C), containment_rule(C, _, _, _, Level, Required, _).

conclusion_atom(containment(L, R)) :- containment(L, R).

because(containment(L, R), RuleId, (sail(S), adjacent_flag(A))) :-
    containment(L, R), containment_first(C), containment_rule(C, _, _, _, L, R, RuleId),
    sail(S), adjacent_flag(A).

%% Containment is only meaningful for a specific-category operation.
:- containment(_, _), certified_category.

tainted_conclusion(containment) :- containment(_, _), tainted(containment).
