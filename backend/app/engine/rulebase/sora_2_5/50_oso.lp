%% 50_oso.lp — Step 8: the OSO set and its required robustness at the computed SAIL.
%%
%% Every OSO in the table gets a level, including "none". A not-required OSO is REPORTED
%% as not applicable rather than omitted, so the operator can see it was considered — an
%% absent row looks like an oversight, and a compliance officer will read it as one.

oso_required(Oso, Level) :- sail(S), oso_level(Oso, S, Level).

conclusion_atom(oso_required(Oso, Level)) :- oso_required(Oso, Level).

%% The title is bound in the body: an anonymous variable may not appear in a head.
because(oso_required(Oso, Level), "sora25.oso.assignment", (sail(S), oso(Oso, Title))) :-
    oso_required(Oso, Level), sail(S), oso(Oso, Title).

%% Under the certified category SORA's OSO set does not apply at all.
:- oso_required(_, _), certified_category.

oso_count(N) :- N = #count{ O : oso_required(O, L), L != none }.

tainted_conclusion(oso) :- oso_required(_, _), tainted(oso).
