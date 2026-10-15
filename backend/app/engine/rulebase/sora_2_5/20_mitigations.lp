%% 20_mitigations.lp — Step 3: ground risk mitigations M1 and M2 → final GRC.
%%
%% Each claimed mitigation contributes a delta from the transcribed table. A level the
%% table does not offer is REFUSED rather than silently ignored: claiming something
%% unclaimable is an input error the operator must see, not a value to round away.
%%
%% The sum is then floored at the controlled-ground-area value for the aircraft's own
%% column, because no mitigation can make the ground safer than an area you control.

%% ---------------------------------------------------------------- claims

claimed(Kind, Rob) :- mitigation(Kind, Rob), Rob != none.

%% Refuse a claim the table marks not claimable. The model goes unsatisfiable and the
%% runner reports it as an invalid claim, naming the kind and the level.
invalid_claim(Kind, Rob) :- claimed(Kind, Rob), mitigation_not_claimable(Kind, Rob).
:- invalid_claim(_, _).

%% A ground mitigation whose precondition is unmet cannot be claimed either.
unmet_precondition(Kind, Rob, Pre) :-
    claimed(Kind, Rob), mitigation_precondition(Kind, Rob, Pre),
    Pre = impact_reduction_fitted, not fitted(parachute).
:- unmet_precondition(_, _, _).

%% ---------------------------------------------------------------- the deltas

applied_delta(Kind, Rob, Delta) :- claimed(Kind, Rob), grc_delta(Kind, Rob, Delta).

grc_mitigation_applied(Kind, Rob, Delta) :- applied_delta(Kind, Rob, Delta).
conclusion_atom(grc_mitigation_applied(Kind, Rob, Delta)) :- grc_mitigation_applied(Kind, Rob, Delta).
because(grc_mitigation_applied(Kind, Rob, Delta), "sora25.grc.mitigation", (mitigation(Kind, Rob),)) :-
    grc_mitigation_applied(Kind, Rob, Delta).

total_delta(T) :- T = #sum{ Delta, Kind : applied_delta(Kind, _, Delta) }.

%% ---------------------------------------------------------------- the floor

%% The controlled-ground-area cell for this aircraft's column is the hard floor.
grc_floor(F) :- igrc_column_used(I), igrc_cell(controlled_ground_area, I, F).

grc_unfloored(V) :- igrc(G), total_delta(T), V = G + T.
grc_unfloored(V) :- igrc(V), not total_delta(_).

grc_default(V) :- grc_unfloored(U), grc_floor(F), U >= F, V = U.
grc_default(V) :- grc_unfloored(U), grc_floor(F), U < F, V = F.

%% default → override pattern, used consistently across the rulebase so national
%% annexes and PDRA shortcuts can defeat a core conclusion without editing it.
grc_overridden :- grc_override(_, _).
grc(V) :- grc_default(V), not grc_overridden.
grc(V) :- grc_override(V, _).

conclusion_atom(grc(V)) :- grc(V).

because(grc(V), "sora25.grc.default", (igrc(G), total_delta(T))) :-
    grc(V), grc_default(V), not grc_overridden, igrc(G), total_delta(T), grc_unfloored(U), U >= V.

because(grc(V), "sora25.grc.floor", (igrc(G), grc_floor(V))) :-
    grc(V), grc_default(V), not grc_overridden, igrc(G), grc_floor(V), grc_unfloored(U), U < V.

because(grc(V), "sora25.grc.default", (igrc(V),)) :-
    grc(V), grc_default(V), not grc_overridden, igrc(V), not total_delta(_).

because(grc(V), RuleId, (grc_default(D),)) :-
    grc(V), grc_override(V, RuleId), grc_default(D).

tainted_conclusion(grc) :- grc(_), tainted(m1_m2).
