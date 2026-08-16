export default function ScoreBadge({ score }) {
  const pct = Math.round((score ?? 0) * 100);
  let level = 'low';
  if (pct >= 70) level = 'high';
  else if (pct >= 40) level = 'medium';
  return <span className={`score-badge score-${level}`}>{pct}%</span>;
}
