"use client";

/**
 * The derivation tree. React Flow with a dagre layout, per the build spec.
 *
 * The design's orchestrated moment is preserved: edges draw from the leaves to the root
 * over about 1200 ms and each node settles 40 ms behind its incoming edge. React Flow
 * does not do that natively, so the edges are custom components animating
 * `stroke-dashoffset` and the nodes carry a per-node delay computed from their depth.
 * Under `prefers-reduced-motion` everything renders complete, immediately.
 *
 * The tree comes from the engine's trace, which is a variable-size graph — that is why a
 * layout engine is needed rather than the fixed canvas the design prototype used.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BaseEdge,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  getBezierPath,
  useEdgesState,
  useNodesInitialized,
  useNodesState,
  useReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import dagre from "dagre";
// Structural CSS only — positioning for the pane, the viewport and the nodes. Without
// it React Flow's absolute layout never applies, the transforms it writes mean nothing,
// and the graph renders somewhere below its own container: a blank panel where the
// derivation tree should be. `base.css` rather than `style.css` because every node and
// edge here is drawn by this file, and the full theme would fight the design system.
import "@xyflow/react/dist/base.css";
import { useReducedMotion } from "framer-motion";
import { CitationChip } from "@/components/Brand";
import { SailBadge, SailPlaceholder } from "@/components/SailBadge";
import { Button } from "@/components/ui/Button";
import type { Determination, TraceNode } from "@/lib/api-client";
import { sailLevel } from "@/lib/api-client";
import { cn } from "@/lib/cn";

const NODE_WIDTH = 236;
const FACT_HEIGHT = 86;
const DERIVED_HEIGHT = 136;
const ROOT_HEIGHT = 150;

/** motion.md: edge-draw 520ms with a 60ms stagger, node-settle 40ms behind its edge. */
const EDGE_MS = 520;
const EDGE_STAGGER = 60;
const NODE_SETTLE_MS = 240;
const NODE_OFFSET = 40;

type TraceData = {
  node: TraceNode;
  depth: number;
  changed: boolean;
  sailLevel: number | null;
  certified: boolean;
  expanded: boolean;
  onToggle: () => void;
};

/** OSO assignment produces one node per OSO; they belong in the gap analysis, not here. */
/** Premises, which the schema marks optional because the server defaults it. */
const premisesOf = (n: TraceNode): string[] => n.premises ?? [];

const isOsoNode = (n: TraceNode) =>
  n.rule_id === "sora25.oso.assignment" || n.id.startsWith("oso_required(");
const isOsoTableRow = (n: TraceNode) => n.rule_id === "table.oso";

export function visibleTrace(trace: TraceNode[]): TraceNode[] {
  return trace.filter((n) => !isOsoNode(n) && !isOsoTableRow(n));
}

/** Depth from the root, so the draw order runs leaves first. */
function depths(nodes: TraceNode[], rootId: string): Map<string, number> {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const out = new Map<string, number>();
  const walk = (id: string, depth: number) => {
    const existing = out.get(id);
    if (existing !== undefined && existing >= depth) return;
    out.set(id, depth);
    for (const p of byId.get(id)?.premises ?? [])
      if (byId.has(p)) walk(p, depth + 1);
  };
  walk(rootId, 0);
  for (const n of nodes) if (!out.has(n.id)) out.set(n.id, 1);
  return out;
}

/**
 * How the graph is framed.
 *
 * `minZoom` here is the floor for the *fit*, and it is far below the interactive
 * `minZoom` on purpose. A full trace is 27 nodes across half a dozen ranks, which needs
 * roughly 0.12 to fit a 560px panel — with the interactive floor of 0.3 applied to the
 * fit as well, React Flow clamped the zoom, could not fit, and left the whole tree
 * outside the visible box. The panel rendered empty, which is the one thing this
 * product cannot afford: the derivation tree *is* the claim.
 */
const FIT = { padding: 0.12, minZoom: 0.02, maxZoom: 1.2 } as const;

/**
 * Re-fit whenever the graph changes shape.
 *
 * The `fitView` prop only runs on mount, and it runs before the nodes have been
 * measured. Expanding a node changes every rank's height, so without this the view
 * drifts further off with each click.
 */
function FitOnChange({ signature }: { signature: string }) {
  const initialised = useNodesInitialized();
  const { fitView } = useReactFlow();
  useEffect(() => {
    if (!initialised) return;
    // Two frames: one for React Flow to measure, one for the layout to settle.
    const id = requestAnimationFrame(() =>
      requestAnimationFrame(() => void fitView(FIT)),
    );
    return () => cancelAnimationFrame(id);
  }, [initialised, signature, fitView]);
  return null;
}

function layout(nodes: Node<TraceData>[], edges: Edge[]): Node<TraceData>[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  // Left to right: facts on the left, the root on the right, as the design has it.
  g.setGraph({
    rankdir: "LR",
    nodesep: 18,
    ranksep: 56,
    marginx: 8,
    marginy: 8,
  });
  for (const n of nodes) {
    g.setNode(n.id, { width: NODE_WIDTH, height: heightOf(n) });
  }
  for (const e of edges) g.setEdge(e.source, e.target);
  dagre.layout(g);
  return nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      ...n,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - heightOf(n) / 2 },
    };
  });
}

const heightOf = (n: Node<TraceData>): number =>
  n.type === "root"
    ? ROOT_HEIGHT
    : n.data.node.kind === "fact" || n.data.node.kind === "default"
      ? FACT_HEIGHT
      : DERIVED_HEIGHT;

// ------------------------------------------------------------------ node renderers

function FactNode({ data }: NodeProps<Node<TraceData>>) {
  const { node, changed } = data;
  const isTable = node.rule_id.startsWith("table.");
  return (
    <div
      className={cn(
        "box-border p-3 bg-sheet border border-hairline w-[236px]",
        changed && "shadow-[inset_2px_0_0_var(--accent)]",
      )}
      style={settle(data.depth)}
    >
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <span className="t-micro-10 text-ink-low">
        {isTable ? "Rulebase table" : "Confirmed fact"}
      </span>
      <div className="mt-1.5 t-data-13 leading-[1.35] text-ink-hi pretty">
        {node.conclusion}
      </div>
    </div>
  );
}

function DerivedNode({ data }: NodeProps<Node<TraceData>>) {
  const { node, changed, expanded, onToggle } = data;
  return (
    <button
      type="button"
      aria-expanded={expanded}
      onClick={onToggle}
      className={cn(
        "box-border text-left p-3.5 bg-sheet-raised border w-[236px] tr-ui",
        expanded
          ? "border-accent-line"
          : "border-hairline-strong hover:border-ink-low",
        changed && "shadow-[inset_2px_0_0_var(--accent)]",
      )}
      style={settle(data.depth)}
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <div className="flex items-baseline justify-between gap-2">
        <span className="t-micro text-ink-low">{term(node)}</span>
        <span className="text-[20px] font-bold leading-none text-ink-hi tnum">
          {value(node)}
        </span>
      </div>
      <div className="mt-2 t-cap leading-[1.4] text-ink-mid line-clamp-3 pretty">
        {node.conclusion}
      </div>
      <div className="mt-2">
        <CitationChip reference={shortCitation(node)} />
      </div>
    </button>
  );
}

function RootNode({ data }: NodeProps<Node<TraceData>>) {
  const { node, sailLevel: level, certified } = data;
  return (
    <div
      className="box-border p-4 bg-sheet border-2 border-accent w-[236px] flex gap-3.5 items-center"
      style={settle(data.depth)}
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      {level ? (
        <SailBadge level={level as 1} size="md" />
      ) : (
        <SailPlaceholder size="md" label="CERT." />
      )}
      <div className="min-w-0">
        <span className="t-micro-10 text-ink-low">
          {certified ? "Outcome" : "SAIL"}
        </span>
        <div className="mt-1.5 t-cap leading-[1.4] text-ink-mid pretty">
          {node.conclusion}
        </div>
      </div>
    </div>
  );
}

function settle(depth: number): React.CSSProperties {
  // Deeper nodes (closer to the facts) settle first: the tree resolves leaves → root.
  const delay = EDGE_MS - depth * EDGE_STAGGER + NODE_OFFSET;
  return {
    animation: `node-settle ${NODE_SETTLE_MS}ms var(--ease-ui) ${Math.max(0, delay)}ms both`,
  };
}

function term(node: TraceNode): string {
  const [head] = node.conclusion.split(" = ");
  return head.split(" — ")[0];
}

function value(node: TraceNode): string {
  const parts = node.conclusion.split(" = ");
  return parts.length > 1 ? parts[1] : "";
}

function shortCitation(node: TraceNode): string {
  const section = node.citation.section.replace(/^.*?— /, "");
  return `${node.citation.document.replace("JARUS ", "")} · ${section}`;
}

// ------------------------------------------------------------------ edges

function DrawnEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const [path] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });
  const accent = Boolean((data as { accent?: boolean } | undefined)?.accent);
  const depth = Number((data as { depth?: number } | undefined)?.depth ?? 0);
  const reduce = Boolean((data as { reduce?: boolean } | undefined)?.reduce);
  const length = Math.hypot(targetX - sourceX, targetY - sourceY) + 120;
  const delay = Math.max(0, EDGE_MS - depth * EDGE_STAGGER - EDGE_MS);

  return (
    <BaseEdge
      path={path}
      style={{
        stroke: accent ? "var(--accent)" : "var(--hairline-strong)",
        strokeWidth: accent ? 2 : 1.5,
        ...(reduce
          ? {}
          : {
              strokeDasharray: length,
              animation: `edge-draw ${EDGE_MS}ms var(--ease-instrument) ${delay}ms both`,
            }),
      }}
    />
  );
}

const nodeTypes = { fact: FactNode, derived: DerivedNode, root: RootNode };
const edgeTypes = { drawn: DrawnEdge };

// ------------------------------------------------------------------ the tree

export function TraceTree({
  determination,
  changed,
  runKey,
  onReplay,
}: {
  determination: Determination;
  changed: Set<string>;
  runKey: number;
  onReplay: () => void;
}) {
  const reduce = useReducedMotion() ?? false;
  const trace = useMemo(
    () => visibleTrace(determination.trace),
    [determination.trace],
  );
  const rootId = useMemo(
    () =>
      trace.find(
        (n) => n.kind === "rule" && /^(SAIL =|Certified)/.test(n.conclusion),
      )?.id ??
      trace[trace.length - 1]?.id ??
      "",
    [trace],
  );
  const level = sailLevel(determination.sail);
  const certified = determination.sail === "certified_category";

  const [expanded, setExpanded] = useState<string[]>([]);
  const toggle = useCallback(
    (id: string) =>
      setExpanded((e) =>
        e.includes(id) ? e.filter((x) => x !== id) : [...e, id],
      ),
    [],
  );

  const built = useMemo(() => {
    const depth = depths(trace, rootId);
    const ids = new Set(trace.map((n) => n.id));

    const rawNodes: Node<TraceData>[] = trace.map((n) => ({
      id: n.id,
      type:
        n.id === rootId
          ? "root"
          : n.kind === "fact" || n.kind === "default"
            ? "fact"
            : "derived",
      position: { x: 0, y: 0 },
      draggable: false,
      connectable: false,
      selectable: false,
      data: {
        node: n,
        depth: depth.get(n.id) ?? 1,
        changed: changed.has(n.id),
        sailLevel: level,
        certified,
        expanded: expanded.includes(n.id),
        onToggle: () => toggle(n.id),
      },
    }));

    const rawEdges: Edge[] = [];
    for (const n of trace) {
      for (const p of premisesOf(n)) {
        if (!ids.has(p)) continue;
        rawEdges.push({
          id: `${p}->${n.id}`,
          source: p,
          target: n.id,
          type: "drawn",
          data: { accent: n.id === rootId, depth: depth.get(p) ?? 1, reduce },
        });
      }
    }
    return { nodes: layout(rawNodes, rawEdges), edges: rawEdges };
  }, [trace, rootId, changed, level, certified, expanded, toggle, reduce]);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node<TraceData>>(
    built.nodes,
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(built.edges);

  useEffect(() => {
    setNodes(built.nodes);
    setEdges(built.edges);
  }, [built, setNodes, setEdges, runKey]);

  const open = trace.filter((n) => expanded.includes(n.id));

  return (
    <div>
      <div className="flex items-baseline justify-between gap-4 mb-4 flex-wrap">
        <div>
          <h3 className="m-0 t-h3 text-ink-hi">Derivation</h3>
          <p className="mt-1 mb-0 t-body-sm text-ink-mid pretty">
            Leaves are the facts you confirmed and the rulebase rows they were
            read against. Every node names the rule that fired.
          </p>
        </div>
        <div className="flex gap-2.5">
          <Button
            variant="ghost"
            onClick={onReplay}
            className="t-micro-10 px-3"
          >
            Replay
          </Button>
          <Button
            variant="ghost"
            className="t-micro-10 px-3"
            onClick={() => copyTrace(determination)}
          >
            Copy trace
          </Button>
        </div>
      </div>

      {/* Desktop: the graph. */}
      <div
        className="hidden md:block bg-sheet-well rounded-sm"
        style={{ height: 560 }}
      >
        <ReactFlowProvider>
          <ReactFlow
            key={runKey}
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            fitViewOptions={FIT}
            proOptions={{ hideAttribution: true }}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            panOnScroll
            zoomOnDoubleClick={false}
            minZoom={0.06}
            maxZoom={1.6}
            aria-label="Derivation tree"
          >
            <FitOnChange
              signature={`${runKey}:${nodes.length}:${expanded.join(",")}`}
            />
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      {/* The inspector: every open node, with its rule, inputs and lookup. */}
      {open.length > 0 && (
        <div className="hidden md:grid mt-3 gap-sheet bg-hairline border border-hairline grid-cols-[repeat(auto-fit,minmax(260px,1fr))]">
          {open.map((n) => (
            <NodeInspector
              key={n.id}
              node={n}
              trace={trace}
              onClose={() => toggle(n.id)}
            />
          ))}
        </div>
      )}
      {open.length === 0 && (
        <p className="hidden md:block m-0 mt-3 t-cap text-ink-low">
          Select a node to see the rule, its inputs and the lookup it used.
        </p>
      )}

      {/* Mobile: an indented outline with identical node anatomy. */}
      <ol
        key={`outline-${runKey}`}
        className="md:hidden m-0 p-3 list-none bg-sheet-well rounded-sm flex flex-col gap-sheet"
      >
        {[...trace]
          .sort(
            (a, b) =>
              (depths(trace, rootId).get(b.id) ?? 0) -
              (depths(trace, rootId).get(a.id) ?? 0),
          )
          .map((n, i) => {
            const depth = depths(trace, rootId).get(n.id) ?? 0;
            const isOpen = expanded.includes(n.id);
            const isRoot = n.id === rootId;
            return (
              <li
                key={n.id}
                style={{ marginLeft: Math.min(depth, 4) * 10, ...settle(i) }}
                className={cn(
                  "bg-sheet",
                  isRoot && "border-l-2 border-accent",
                  changed.has(n.id) && "shadow-[inset_2px_0_0_var(--accent)]",
                )}
              >
                {n.kind === "fact" || n.kind === "default" ? (
                  <div className="p-3">
                    <span className="t-micro-10 text-ink-low">
                      {n.rule_id.startsWith("table.")
                        ? "Rulebase table"
                        : "Confirmed fact"}
                    </span>
                    <div className="mt-1.5 t-body-sm leading-[1.4] text-ink-mid pretty">
                      {n.conclusion}
                    </div>
                  </div>
                ) : (
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    onClick={() => toggle(n.id)}
                    className="w-full text-left bg-transparent border-0 p-3 min-h-11"
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="t-micro-10 text-ink-low">{term(n)}</span>
                      <span
                        aria-hidden
                        className={cn(
                          "text-ink-low text-xs tr-ui",
                          isOpen && "rotate-180",
                        )}
                      >
                        ▾
                      </span>
                    </span>
                    <span className="block mt-1.5 t-body-sm leading-[1.4] text-ink-hi pretty">
                      {n.conclusion}
                    </span>
                    {isOpen && (
                      <span className="mt-2 flex flex-col gap-1.5">
                        <CitationChip reference={shortCitation(n)} />
                        {!n.citation.verified && (
                          <span className="t-cap text-sail-3">
                            This table has not been verified against the
                            official text.
                          </span>
                        )}
                      </span>
                    )}
                  </button>
                )}
              </li>
            );
          })}
      </ol>
    </div>
  );
}

function NodeInspector({
  node,
  trace,
  onClose,
}: {
  node: TraceNode;
  trace: TraceNode[];
  onClose: () => void;
}) {
  const byId = new Map(trace.map((n) => [n.id, n]));
  return (
    <div className="bg-sheet-well p-4 flex flex-col gap-2.5 animate-[node-settle_240ms_var(--ease-ui)_both]">
      <div className="flex items-baseline justify-between gap-3">
        <span className="t-micro text-ink-low">{term(node)} · rule fired</span>
        <button
          type="button"
          aria-label={`Collapse ${term(node)}`}
          onClick={onClose}
          className="size-8 -m-1.5 bg-transparent border-0 text-ink-low hover:text-ink-hi"
        >
          ✕
        </button>
      </div>
      <p className="m-0 t-body-sm text-ink-hi pretty">{node.conclusion}</p>
      <CitationChip reference={shortCitation(node)} size="md" />
      <div className="flex flex-col gap-1">
        <span className="t-micro-10 text-ink-low">Rule</span>
        <span className="t-data-sm text-ink-mid break-words">
          {node.rule_id}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="t-micro-10 text-ink-low">Inputs</span>
        {premisesOf(node).length === 0 && (
          <span className="t-data-sm text-ink-low">None</span>
        )}
        {premisesOf(node).map((p) => {
          const premise = byId.get(p);
          return (
            <span key={p} className="t-data-sm text-ink-mid pretty">
              {premise ? premise.conclusion : p}
            </span>
          );
        })}
      </div>
      {!node.citation.verified && (
        <span className="t-cap text-sail-3 pretty">
          UNVERIFIED — this value is transcribed from a seed, not from{" "}
          {node.citation.document}.
        </span>
      )}
    </div>
  );
}

/** "Copy trace" emits the whole tree as markdown, per the build spec. */
export function traceMarkdown(d: Determination): string {
  const lines: string[] = [
    `# Derivation — SAIL ${d.sail}`,
    "",
    `Rulebase ${d.rulebase_version} · mission ${d.mission_hash.slice(0, 12)} · computed ${d.computed_at}`,
    "",
    `| Term | Value |`,
    `| --- | --- |`,
    `| iGRC | ${d.igrc ?? "—"} |`,
    `| Final GRC | ${d.final_grc ?? "—"} |`,
    `| ARC | ${d.initial_arc} |`,
    `| Residual ARC | ${d.residual_arc} |`,
    `| SAIL | ${d.sail} |`,
    `| TMPR | ${d.tmpr} |`,
    "",
    "## Nodes",
    "",
  ];
  for (const n of d.trace) {
    const verified = n.citation.verified ? "" : "  **UNVERIFIED**";
    lines.push(`- **${n.conclusion}**`);
    lines.push(`  - rule: \`${n.rule_id}\`${verified}`);
    lines.push(`  - citation: ${n.citation.document} · ${n.citation.section}`);
    const from = premisesOf(n);
    if (from.length) lines.push(`  - from: ${from.join(", ")}`);
  }
  if (d.warnings.length) {
    lines.push("", "## Warnings", "");
    for (const w of d.warnings) lines.push(`- ${w}`);
  }
  return lines.join("\n");
}

async function copyTrace(d: Determination): Promise<void> {
  try {
    await navigator.clipboard.writeText(traceMarkdown(d));
  } catch {
    // Clipboard access can be refused; the export button is the reliable path.
  }
}
