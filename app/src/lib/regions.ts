/**
 * The survey's 14 regions, in the order the EDHS report lists them, with the codes of
 * the UN OCHA 2025 administrative boundaries (COD-AB, ADM1) they join to. The OCHA
 * file spells Gambella "Gambela"; the survey's spelling is used everywhere on screen.
 * The OCHA file's fifteenth polygon ("Contested", ET99) has no survey region and is
 * drawn as neutral hatching.
 */

export interface Region {
  name: string;
  pcode: string;
  short: string;
}

export const REGIONS: Region[] = [
  { name: "Tigray", pcode: "ET01", short: "TIG" },
  { name: "Afar", pcode: "ET02", short: "AFA" },
  { name: "Amhara", pcode: "ET03", short: "AMH" },
  { name: "Oromia", pcode: "ET04", short: "ORO" },
  { name: "Somali", pcode: "ET05", short: "SOM" },
  { name: "Benishangul-Gumuz", pcode: "ET06", short: "BEN" },
  { name: "Central Ethiopia", pcode: "ET07", short: "CEN" },
  { name: "South Ethiopia", pcode: "ET08", short: "SOU" },
  { name: "South West Ethiopia", pcode: "ET11", short: "SWE" },
  { name: "Gambella", pcode: "ET12", short: "GAM" },
  { name: "Harari", pcode: "ET13", short: "HAR" },
  { name: "Addis Ababa", pcode: "ET14", short: "ADD" },
  { name: "Dire Dawa", pcode: "ET15", short: "DIR" },
  { name: "Sidama", pcode: "ET16", short: "SID" },
];

export const REGION_BY_PCODE: Record<string, Region> = Object.fromEntries(
  REGIONS.map((r) => [r.pcode, r]),
);

export const REGION_NAMES = REGIONS.map((r) => r.name);

export function isRegion(name: string): boolean {
  return REGIONS.some((r) => r.name === name);
}
