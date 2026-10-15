%% 40_sail.lp — Step 7: SAIL from the final GRC and the residual ARC.
%%
%% The table covers GRC 2 to 7. Below 2 clamps to the GRC-2 row; above the certified
%% ceiling the operation leaves SORA altogether, which is an OUTCOME and not an error.

grc_row(R) :- grc(G), G >= 2, G <= 7, R = G.
grc_row(2) :- grc(G), G < 2.

certified_category :- grc(G), threshold(grc_certified_ceiling, C), G > C.
certified_category :- out_of_scope(_).

sail_default(S) :- grc_row(R), arc_residual(A), sail_cell(R, A, S), not certified_category.

sail_overridden :- sail_override(_, _).
sail(S) :- sail_default(S), not sail_overridden.
sail(S) :- sail_override(S, _).

conclusion_atom(sail(S)) :- sail(S).

because(sail(S), "sora25.sail.lookup", (grc(G), arc_residual(A))) :-
    sail(S), sail_default(S), not sail_overridden, grc(G), arc_residual(A).

because(sail(S), RuleId, (sail_default(D),)) :-
    sail(S), sail_override(S, RuleId), sail_default(D).

%% The certified outcome, justified like any other conclusion.
conclusion_atom(certified_category) :- certified_category.

because(certified_category, "sora25.sail.certified", (grc(G), threshold(grc_certified_ceiling, C))) :-
    certified_category, grc(G), threshold(grc_certified_ceiling, C), G > C.

because(certified_category, "sora25.igrc.out_of_scope", (out_of_scope(Reason),)) :-
    certified_category, out_of_scope(Reason).

%% Exactly one of the two outcomes.
:- sail(_), certified_category.
:- not sail(_), not certified_category.

tainted_conclusion(sail) :- sail(_), tainted(sail).
