/**
 * A small "?" beside a technical term, linking to its plain-language entry in
 * the Analysis record tab. A plain hash link, so it works from any component
 * without passing a navigation callback down.
 */
export default function TermLink({ id, label }: { id: string; label?: string }) {
  return (
    <a
      href={`#record/term-${id}`}
      title={`What does ${label ?? "this"} mean?`}
      aria-label={`Explain ${label ?? id}`}
      className="inline-flex items-center justify-center rounded-full align-middle ml-1 text-[0.62rem] font-semibold no-underline"
      style={{ width: 15, height: 15, border: "1px solid var(--line)", color: "var(--muted)" }}
    >
      ?
    </a>
  );
}
