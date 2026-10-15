%% 90_national_de.lp — Germany (LBA) national overrides.
%%
%% Same contract as 90_national_at.lp. Nothing transcribed: the German annex has not been
%% supplied, so Germany uses the EU baseline and the trace says so.

national_baseline(de) :- country(de).
conclusion_atom(national_baseline(de)) :- national_baseline(de).
because(national_baseline(de), "de.baseline", (country(de),)) :- national_baseline(de).
