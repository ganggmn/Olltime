/* 공연 일정: 올림픽공원 누리집 '일정안내'를 한 시간에 한 번 읽어 날짜별 시작 시각으로 풀어 줘요.
   GET /api/shows            오늘이 든 달부터 석 달
   GET /api/shows?from=2026-11-01&months=2
   못 읽은 공연은 skipped에, 못 받은 달은 failed에 이유와 함께 남겨요. 한 달도 못 받으면 502. */
import { fetchShows, monthsFrom } from './_shows.js';
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const q = req.query || {}, today = new Date(Date.now() + 9 * 36e5).toISOString().slice(0, 10);
  const from = /^\d{4}-\d{2}-\d{2}$/.test(q.from || '') ? q.from : today, n = Math.max(1, Math.min(4, parseInt(q.months, 10) || 3));
  const out = await fetchShows(monthsFrom(from, n));
  if (!out.months.length) { res.setHeader('Cache-Control', 'no-store'); return res.status(502).json({ ok: false, error: '공연 일정을 받아 오지 못했어요', failed: out.failed }); }
  res.setHeader('Cache-Control', 'public, s-maxage=3600, stale-while-revalidate=86400');
  return res.status(200).json({ ok: true, source: '한국체육산업개발 올림픽공원 누리집 일정안내', read_at: new Date().toISOString(), months: out.months, failed: out.failed, list: out.list, skipped: out.skipped });
}
