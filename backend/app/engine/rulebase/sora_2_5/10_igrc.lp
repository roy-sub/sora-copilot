%% 10_igrc.lp — Step 2: intrinsic ground risk class.
%%
%% Two lookups and one override:
%%
%%   column  = the FIRST column whose dimension AND speed limits both hold
%%   row     = the density band, or the controlled ground area, or the top band if the
%%             operation is over an assembly of people
%%   iGRC    = the cell, unless the small-UA provision pins it to 1
%%
%% An absent cell means the combination is not part of SORA. It is never read as 0.

%% ---------------------------------------------------------------- the column

igrc_col_fits(I) :-
    igrc_col(I, MaxDim, MaxSpeed),
    dim_cm(D), D <= MaxDim,
    speed_cms(S), S <= MaxSpeed.

igrc_any_column :- igrc_col_fits(_).

igrc_column_used(I) :- igrc_any_column, I = #min{ J : igrc_col_fits(J) }.

conclusion_atom(igrc_column_used(I)) :- igrc_column_used(I).
because(igrc_column_used(I), "sora25.igrc.column", (dim_cm(D), speed_cms(S), igrc_col(I, MaxDim, MaxSpeed))) :-
    igrc_column_used(I), igrc_col(I, MaxDim, MaxSpeed), dim_cm(D), speed_cms(S).

%% Beyond the last column the aircraft is outside SORA entirely.
out_of_scope(dimension_or_speed) :- not igrc_any_column.
conclusion_atom(out_of_scope(dimension_or_speed)) :- out_of_scope(dimension_or_speed).
because(out_of_scope(dimension_or_speed), "sora25.igrc.out_of_scope", (dim_cm(D), speed_cms(S))) :-
    out_of_scope(dimension_or_speed), dim_cm(D), speed_cms(S).

%% ---------------------------------------------------------------- the row

%% Two environments pick the band directly rather than by density.
band_is_fixed :- ground_env(controlled_ground_area).
band_is_fixed :- ground_env(assembly_of_people).

ground_band(controlled_ground_area) :- ground_env(controlled_ground_area).
because(ground_band(controlled_ground_area), "sora25.igrc.controlled_area", (ground_env(controlled_ground_area),)) :-
    ground_env(controlled_ground_area).

%% An assembly of people is not a density band: it pins the top row whatever the
%% measured density says. PLAN.md section 6.2.
ground_band(B) :- ground_env(assembly_of_people), igrc_band_unbounded(_, B).
because(ground_band(B), "sora25.igrc.assembly", (ground_env(assembly_of_people),)) :-
    ground_env(assembly_of_people), igrc_band_unbounded(_, B).

%% Otherwise: the first band, in index order, whose ceiling the density has not reached.
band_fits(N) :- not band_is_fixed, igrc_band(N, _, Max), N > 0, density(D), D < Max.
band_fits(N) :- not band_is_fixed, igrc_band_unbounded(N, _), N > 0.

ground_band(B) :- not band_is_fixed, N = #min{ M : band_fits(M) }, igrc_band(N, B, _).
ground_band(B) :- not band_is_fixed, N = #min{ M : band_fits(M) }, igrc_band_unbounded(N, B).

because(ground_band(B), "sora25.igrc.density_band", (density(D), ground_env(E))) :-
    not band_is_fixed, ground_band(B), density(D), ground_env(E).

conclusion_atom(ground_band(B)) :- ground_band(B).

%% ---------------------------------------------------------------- the cell

igrc_lookup(V) :- igrc_column_used(I), ground_band(B), igrc_cell(B, I, V).

%% The small-UA provision overrides the lookup: at or under 250 g and 25 m/s the
%% intrinsic ground risk is 1 regardless of what is underneath.
small_ua :-
    mtom_g(M), threshold(small_ua_mtom, MaxM), M <= MaxM,
    speed_cms(S), threshold(small_ua_speed, MaxS), S <= MaxS.

igrc_override(1, "sora25.igrc.small_ua") :- small_ua.
igrc_overridden :- igrc_override(_, _).

igrc(V) :- igrc_lookup(V), not igrc_overridden.
igrc(V) :- igrc_override(V, _).

conclusion_atom(igrc(V)) :- igrc(V).

because(igrc(V), "sora25.igrc.lookup", (igrc_column_used(I), ground_band(B))) :-
    igrc(V), igrc_lookup(V), not igrc_overridden, igrc_column_used(I), ground_band(B).

because(igrc(V), RuleId, (mtom_g(M), speed_cms(S))) :-
    igrc(V), igrc_override(V, RuleId), mtom_g(M), speed_cms(S).

%% A column and band that have no cell: outside SORA, and NOT iGRC 0.
out_of_scope(density_for_this_aircraft) :-
    igrc_column_used(I), ground_band(B), not igrc_cell(B, I, _), not igrc_overridden.
conclusion_atom(out_of_scope(density_for_this_aircraft)) :- out_of_scope(density_for_this_aircraft).
because(out_of_scope(density_for_this_aircraft), "sora25.igrc.out_of_scope", (igrc_column_used(I), ground_band(B))) :-
    out_of_scope(density_for_this_aircraft), igrc_column_used(I), ground_band(B).

%% Everything above rests on the iGRC table, so taint rides with it.
tainted_conclusion(igrc) :- igrc(_), tainted(igrc).
