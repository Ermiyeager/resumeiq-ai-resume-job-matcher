import type { MandatoryItem } from "../types";
import { Pill, type Tone } from "./ui";

const label: Record<MandatoryItem["status"], [string, Tone]> = {
  MET: ["Met", "good"],
  PARTIAL: ["Partly shown", "warn"],
  NOT_FOUND: ["Not found", "bad"],
  UNKNOWN: ["Not enough info", "neutral"],
};

export default function MandatoryList({ items }: { items: MandatoryItem[] }) {
  if (!items.length) return null;
  const order = { NOT_FOUND: 0, UNKNOWN: 1, PARTIAL: 2, MET: 3 };
  const sorted = [...items].sort((a, b) => order[a.status] - order[b.status]);
  const gaps = items.filter((i) => i.status === "NOT_FOUND").length;

  return (
    <section
      className={`rounded-lg border p-5 ${gaps ? "border-bad/40 bg-bad-soft/40" : "border-line bg-surface"}`}
      aria-labelledby="mandatory-heading"
    >
      <h2 id="mandatory-heading" className="text-base font-semibold">
        {gaps ? `${gaps} required ${gaps === 1 ? "item" : "items"} not found` : "Required items"}
      </h2>
      <p className="mt-1 text-sm text-muted">
        Checked separately from the score, because missing one required item can matter more than a high overall fit.
      </p>
      <ul className="mt-3 divide-y divide-line">
        {sorted.map((item) => (
          <li key={item.kind + item.requirement} className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 py-2">
            <div className="min-w-0">
              <p className="text-sm font-medium">{item.requirement}</p>
              {item.evidence && <p className="mt-0.5 text-xs text-muted">{item.evidence}</p>}
            </div>
            <Pill tone={label[item.status][1]}>{label[item.status][0]}</Pill>
          </li>
        ))}
      </ul>
    </section>
  );
}
