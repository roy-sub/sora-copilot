%% 70_sts_pdra.lp — Standard Scenarios and Predefined Risk Assessments.
%%
%% An STS or PDRA is a published shortcut: an operation that fits one declares against
%% it instead of running the full assessment. They are written here as DEFEASIBLE
%% OVERRIDES over the core conclusions — the non-monotonic pattern 00_core.lp sets out —
%% so the core rules are never edited to accommodate a shortcut.
%%
%% NO SHORTCUT IS TRANSCRIBED YET. Adding one means transcribing its applicability
%% conditions and its assigned values from the published document, exactly like any other
%% regulatory value. The shape below is the contract a transcription must satisfy; it
%% fires for nothing, because inventing a shortcut's conditions would be inventing the
%% most consequential regulatory value in the product.
%%
%% The contract, for whoever transcribes the first one:
%%
%%   pdra_applicable("pdra.s01") :- <conditions from the published document>.
%%   sail_override(S, "pdra.s01.sail") :- pdra_declared("pdra.s01"), <assigned SAIL>.
%%   oso_override(Oso, Level, "pdra.s01.oso") :- ...
%%
%% A shortcut only takes effect when the operator DECLARES it — pdra_declared/1 is a
%% mission fact, not something the engine infers. An operation that merely happens to fit
%% PDRA-S01 has not declared against it, and the authority reads the declaration.

%% Declaring a shortcut the engine does not know is an input error, not a silent no-op.
:- pdra_declared(P), not pdra_known(P).

%% Declaring one that does not apply to this operation is also an error.
:- pdra_declared(P), pdra_known(P), not pdra_applicable(P).

%% No shortcut is known yet, so pdra_known/1 is empty and any declaration fails loudly.
