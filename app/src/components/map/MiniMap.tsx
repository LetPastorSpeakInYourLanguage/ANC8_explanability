"use client";

import { useMemo } from "react";
import type { FeatureCollection, Position } from "geojson";
import { REGION_BY_PCODE } from "@/lib/regions";

/**
 * A small SVG map of the regions, for small multiples (ANC1+ | ANC4+ | ANC8+ side by
 * side) and as a locator in the region panel. No tiles and no library: the same
 * boundaries projected with a plain equirectangular projection (corrected for
 * Ethiopia's latitude), which is accurate enough at this size.
 */

const LON0 = 32.9, LAT1 = 15.0, LON1 = 48.0, LAT0 = 3.3;
const KX = Math.cos((9 * Math.PI) / 180);
const W = 300;
const H = Math.round((W * (LAT1 - LAT0)) / ((LON1 - LON0) * KX));

function project([lon, lat]: Position): [number, number] {
  return [((lon - LON0) / (LON1 - LON0)) * W, ((LAT1 - lat) / (LAT1 - LAT0)) * H];
}

function pathOf(coords: Position[][][]): string {
  return coords
    .map((poly) =>
      poly
        .map((ring) => ring.map((p, i) => `${i ? "L" : "M"}${project(p).map((v) => v.toFixed(1)).join(",")}`).join("") + "Z")
        .join(""),
    )
    .join("");
}

export function useRegionPaths(geo: FeatureCollection | null) {
  return useMemo(() => {
    if (!geo) return [];
    return geo.features.map((f) => {
      const g = f.geometry;
      const coords = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
      const pcode = (f.properties as { pcode: string }).pcode;
      return { pcode, region: REGION_BY_PCODE[pcode]?.name ?? null, d: pathOf(coords as Position[][][]) };
    });
  }, [geo]);
}

export default function MiniMap({
  paths,
  fills,
  selected,
  onSelect,
  title,
  className = "",
  noData = "#dfe5ec",
  stroke = "var(--panel)",
}: {
  paths: ReturnType<typeof useRegionPaths>;
  fills: Record<string, string>;
  selected?: string;
  onSelect?: (region: string) => void;
  title?: string;
  className?: string;
  noData?: string;
  stroke?: string;
}) {
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={`studio-minimap w-full h-auto ${className}`} role="img" aria-label={title}>
      {title && <title>{title}</title>}
      {paths.map((p) =>
        p.region ? (
          <path
            key={p.pcode}
            d={p.d}
            fill={fills[p.region] ?? noData}
            stroke={p.region === selected ? "var(--top)" : stroke}
            strokeWidth={p.region === selected ? 2 : 0.6}
            onClick={onSelect ? () => onSelect(p.region!) : undefined}
            className={onSelect ? "cursor-pointer hover:opacity-85" : ""}
          >
            <title>{p.region}</title>
          </path>
        ) : (
          <path key={p.pcode} d={p.d} fill="var(--panel3)" stroke={stroke} strokeWidth={0.4} strokeDasharray="2 2" />
        ),
      )}
    </svg>
  );
}
