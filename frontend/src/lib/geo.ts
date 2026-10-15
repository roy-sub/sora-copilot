/**
 * Client-side geometry, for drawing and for showing an area while the pointer moves.
 *
 * The **server** is authoritative: `POST /geo/derive` computes the volumes that reach
 * the engine, in a centred equal-area projection. What is here exists so the map can
 * show a plausible area during a drag without a request per frame, and it is replaced by
 * the server's numbers the moment the vertex is released.
 */

import type { GeoJSONPolygon } from "@/lib/api-client";

export interface LngLat {
  lng: number;
  lat: number;
}

const EARTH_RADIUS_M = 6_378_137;
const DEG = Math.PI / 180;

/** Metres per degree of longitude at a latitude, and per degree of latitude. */
export function metresPerDegree(lat: number): { x: number; y: number } {
  return {
    x: EARTH_RADIUS_M * DEG * Math.cos(lat * DEG),
    y: EARTH_RADIUS_M * DEG,
  };
}

/** Spherical-excess area of a ring, in m². Good to a fraction of a percent at this scale. */
export function ringAreaM2(ring: LngLat[]): number {
  if (ring.length < 3) return 0;
  let total = 0;
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i];
    const b = ring[(i + 1) % ring.length];
    total += (b.lng - a.lng) * DEG * (2 + Math.sin(a.lat * DEG) + Math.sin(b.lat * DEG));
  }
  return Math.abs((total * EARTH_RADIUS_M * EARTH_RADIUS_M) / 2);
}

export const areaKm2 = (ring: LngLat[]): number => ringAreaM2(ring) / 1_000_000;

/** Great-circle distance in metres. */
export function distanceM(a: LngLat, b: LngLat): number {
  const dLat = (b.lat - a.lat) * DEG;
  const dLng = (b.lng - a.lng) * DEG;
  const lat = ((a.lat + b.lat) / 2) * DEG;
  const x = dLng * Math.cos(lat);
  return Math.hypot(x, dLat) * EARTH_RADIUS_M;
}

export function perimeterM(ring: LngLat[]): number {
  if (ring.length < 2) return 0;
  let total = 0;
  for (let i = 0; i < ring.length; i++) total += distanceM(ring[i], ring[(i + 1) % ring.length]);
  return total;
}

/** A ring's centroid, for centring the map on it. */
export function centroid(ring: LngLat[]): LngLat {
  if (!ring.length) return { lng: 15.44, lat: 47.07 };
  const lng = ring.reduce((s, p) => s + p.lng, 0) / ring.length;
  const lat = ring.reduce((s, p) => s + p.lat, 0) / ring.length;
  return { lng, lat };
}

export function bounds(ring: LngLat[]): [[number, number], [number, number]] | null {
  if (!ring.length) return null;
  let minLng = ring[0].lng;
  let maxLng = ring[0].lng;
  let minLat = ring[0].lat;
  let maxLat = ring[0].lat;
  for (const p of ring) {
    minLng = Math.min(minLng, p.lng);
    maxLng = Math.max(maxLng, p.lng);
    minLat = Math.min(minLat, p.lat);
    maxLat = Math.max(maxLat, p.lat);
  }
  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ];
}

/**
 * Whether a ring's edges cross each other.
 *
 * The backend refuses a self-intersecting outline rather than repairing it, so the map
 * says so while the operator is still drawing instead of after they press Continue.
 */
export function selfIntersects(ring: LngLat[]): boolean {
  const n = ring.length;
  if (n < 4) return false;
  const segments: [LngLat, LngLat][] = [];
  for (let i = 0; i < n; i++) segments.push([ring[i], ring[(i + 1) % n]]);
  for (let i = 0; i < segments.length; i++) {
    for (let j = i + 1; j < segments.length; j++) {
      // Adjacent segments share a vertex by construction.
      if (j === i + 1 || (i === 0 && j === segments.length - 1)) continue;
      if (segmentsCross(segments[i], segments[j])) return true;
    }
  }
  return false;
}

function segmentsCross([p1, p2]: [LngLat, LngLat], [p3, p4]: [LngLat, LngLat]): boolean {
  const d = (a: LngLat, b: LngLat, c: LngLat) =>
    (b.lng - a.lng) * (c.lat - a.lat) - (b.lat - a.lat) * (c.lng - a.lng);
  const d1 = d(p3, p4, p1);
  const d2 = d(p3, p4, p2);
  const d3 = d(p1, p2, p3);
  const d4 = d(p1, p2, p4);
  return ((d1 > 0) !== (d2 > 0)) && ((d3 > 0) !== (d4 > 0));
}

/** A closed GeoJSON polygon from an open ring of vertices. */
export function toPolygon(ring: LngLat[]): GeoJSONPolygon | null {
  if (ring.length < 3) return null;
  const coords = ring.map((p) => [p.lng, p.lat]);
  coords.push([ring[0].lng, ring[0].lat]);
  return { type: "Polygon", coordinates: [coords] };
}

/** The open ring from a GeoJSON polygon's exterior, dropping the repeated last point. */
export function fromPolygon(polygon: GeoJSONPolygon | null | undefined): LngLat[] {
  const ring = polygon?.coordinates?.[0];
  if (!ring?.length) return [];
  const out = ring.map(([lng, lat]) => ({ lng, lat }));
  const first = out[0];
  const last = out[out.length - 1];
  if (out.length > 1 && first.lng === last.lng && first.lat === last.lat) out.pop();
  return out;
}

/** A buffered outline, for showing a derived volume before the server answers. */
export function bufferRing(ring: LngLat[], metres: number): LngLat[] {
  if (ring.length < 3 || metres <= 0) return ring;
  const c = centroid(ring);
  const per = metresPerDegree(c.lat);
  // Scale outward from the centroid by the ratio that adds `metres` to the mean radius.
  const radii = ring.map((p) =>
    Math.hypot((p.lng - c.lng) * per.x, (p.lat - c.lat) * per.y),
  );
  const mean = radii.reduce((s, r) => s + r, 0) / radii.length || 1;
  const scale = (mean + metres) / mean;
  return ring.map((p) => ({
    lng: c.lng + (p.lng - c.lng) * scale,
    lat: c.lat + (p.lat - c.lat) * scale,
  }));
}

/** A default square around a point, so the map step starts with something to adjust. */
export function defaultRing(centre: LngLat = { lng: 15.44, lat: 47.12 }, halfSideM = 700): LngLat[] {
  const per = metresPerDegree(centre.lat);
  const dLng = halfSideM / per.x;
  const dLat = halfSideM / per.y;
  return [
    { lng: centre.lng - dLng, lat: centre.lat - dLat },
    { lng: centre.lng + dLng, lat: centre.lat - dLat },
    { lng: centre.lng + dLng, lat: centre.lat + dLat },
    { lng: centre.lng - dLng, lat: centre.lat + dLat },
  ];
}

export const fmtKm2 = (v: number): string =>
  v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const fmtM = (v: number): string =>
  v.toLocaleString("en-GB", { maximumFractionDigits: 0 });
