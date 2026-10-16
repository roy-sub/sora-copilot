%% 60_containment.lp — Step #8: the containment requirement.
%%
%% Tables 8 to 13 of AMC1 Article 11. A table is chosen by the UA's characteristic
%% dimension (and, at 3 m, by whether sheltering applies in the adjacent ground area);
%% a COLUMN is chosen by what the operation accepts as limits on the adjacent ground
%% area; the cell at that column and the operation's SAIL is the required robustness.
%%
%% S.4.8.3(d) decides the column: "considering the most stringent between the value of
%% the average population density and the outdoor assembly of people". The columns run
%% least to most restrictive, so the most stringent of the two is the LOWEST column
%% index either input qualifies for.

%% ---------------------------------------------------------------- which table

%% The smallest table whose dimension limit the UA still fits under. A 2 m UA is scored
%% on the 3 m table, not the 1 m one.
cont_table_fits(T) :- containment_table(T, MaxCm, Shelter), dim_cm(D), D <= MaxCm,
                      cont_shelter_ok(Shelter).

cont_shelter_ok(S) :- containment_table(_, _, S), wildcard(S).
cont_shelter_ok(S) :- containment_table(_, _, S), sheltering(S).

cont_table(T) :- T = #min{ U : cont_table_fits(U) }, cont_table_fits(_).

%% ---------------------------------------------------------------- which column

%% A column's density limit is met when the adjacent area's average density is below it.
%% "unlimited" is met by anything, including an operation that has not measured one.
cont_col_density_ok(T, C) :- containment_col(T, C, unlimited, _), cont_table(T).
cont_col_density_ok(T, C) :- containment_col(T, C, Max, _), Max != unlimited,
                             cont_table(T), adjacent_density(D), D < Max.

%% The assembly bands are ordinal, so they are compared as the numbers the table uses.
assembly_people(0)      :- adjacent_assembly("none").
assembly_people(39999)  :- adjacent_assembly("under_40k").
assembly_people(399999) :- adjacent_assembly("40k_to_400k").
assembly_people(400001) :- adjacent_assembly("over_400k").

cont_col_assembly_ok(T, C) :- containment_col(T, C, _, unlimited), cont_table(T).
cont_col_assembly_ok(T, C) :- containment_col(T, C, _, Max), Max != unlimited,
                              cont_table(T), assembly_people(P), P < Max.

%% Each input independently qualifies the operation for a best column: the RIGHTMOST
%% one whose limit it still meets. The columns run from least restrictive on the left
%% ("no upper limit") to most restrictive on the right, and accepting a tighter limit on
%% the adjacent ground area is what buys a lower containment robustness — so the best
%% column an input supports is the highest-numbered one it satisfies.
cont_col_by_density(C)  :- C = #max{ D : cont_col_density_ok(T, D), cont_table(T) },
                           cont_col_density_ok(_, _).
cont_col_by_assembly(C) :- C = #max{ D : cont_col_assembly_ok(T, D), cont_table(T) },
                           cont_col_assembly_ok(_, _).

%% S.4.8.3(d): "considering the most stringent between the value of the average
%% population density and the outdoor assembly of people". The more stringent
%% REQUIREMENT is the one that demands more containment, which is the lower column.
cont_col(C) :- C = #min{ D : cont_col_by_density(D); E : cont_col_by_assembly(E) },
               cont_col_by_density(_), cont_col_by_assembly(_).

%% ---------------------------------------------------------------- the cell

%% A column with no upper limit qualifies even when nothing has been measured, so the
%% level has to be gated on the inputs as well — otherwise an operation that has
%% answered neither Step #8 question is quietly scored in the least restrictive column.
cont_level(L) :- cont_table(T), cont_col(C), sail(S), containment_rule(T, C, S, L, _),
                 not cont_inputs_missing.

%% Everything the tables need is known, so a level is computed. The missing-input case
%% below is what happens instead when it is not.
containment(L, false) :- cont_level(L), L != out_of_scope.

%% "Out of scope" is the table's own answer: the combination is outside what SORA
%% supports. It is not a containment level and must not be reported as one.
containment(none, true) :- cont_level(out_of_scope).

%% Step #8 cannot be answered without the adjacent ground area's population density and
%% the assemblies expected within 1 km of the operational volume. Rather than assume
%% either, the engine says what it needs.
cont_inputs_missing :- not adjacent_density(_).
cont_inputs_missing :- not adjacent_assembly(_).
cont_inputs_missing :- not cont_table(_).

containment(none, true) :- cont_inputs_missing, sail(_), not cont_small_ua.

%% S.4.8.3(a): a UA under 250 g gets low containment with no adjacent-area limitations
%% at all, and skips the tables entirely.
cont_small_ua :- mtom_g(M), threshold(containment_small_ua_mtom, T), M < T.
containment(low, false) :- cont_small_ua, sail(_).

conclusion_atom(containment(L, R)) :- containment(L, R).

because(containment(L, false), RuleId, (sail(S), adjacent_density(D), adjacent_assembly(A))) :-
    containment(L, false), not cont_small_ua, cont_table(T), cont_col(C), sail(S),
    containment_rule(T, C, S, L, RuleId), adjacent_density(D), adjacent_assembly(A).

because(containment(none, true), RuleId, (sail(S), adjacent_density(D), adjacent_assembly(A))) :-
    containment(none, true), not cont_inputs_missing, cont_table(T), cont_col(C), sail(S),
    containment_rule(T, C, S, out_of_scope, RuleId), adjacent_density(D), adjacent_assembly(A).

because(containment(none, true), "sora25.containment.inputs_missing", (sail(S),)) :-
    containment(none, true), cont_inputs_missing, sail(S).

because(containment(low, false), "sora25.containment.small_ua", (mtom_g(M),)) :-
    cont_small_ua, containment(low, false), mtom_g(M).

%% Containment is only meaningful for a specific-category operation.
:- containment(_, _), certified_category.

%% One answer, or none. Two would mean the tables overlap.
:- containment(L1, _), containment(L2, _), L1 != L2.

tainted_conclusion(containment) :- containment(_, _), tainted(containment).
