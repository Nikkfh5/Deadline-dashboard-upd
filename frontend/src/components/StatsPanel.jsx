import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, AlertTriangle, Calendar } from 'lucide-react';
import { Card } from './ui/card';
import { fetchStats, hasToken } from '../services/api';

const SOURCE_LABELS = { manual: 'Вручную', telegram: 'Telegram', wiki: 'Wiki' };
const SOURCE_COLORS = { manual: '#6366f1', telegram: '#3b82f6', wiki: '#10b981' };

const StatsPanel = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!hasToken()) return;
    const load = async () => {
      const data = await fetchStats();
      if (data) setStats(data);
    };
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) return null;

  const maxWeekCount = Math.max(...stats.week.map(d => d.count), 1);

  // Source pie - simple CSS-based
  const sourceTotal = Object.values(stats.by_source).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="mt-10 mb-8">
      <h2 className="text-xl font-semibold text-slate-700 dark:text-slate-200 mb-4 flex items-center gap-2">
        <BarChart3 className="w-5 h-5" />
        Статистика
      </h2>

      {/* Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Card className="p-4 text-center bg-white dark:bg-slate-800">
          <div className="text-2xl font-bold text-slate-800 dark:text-slate-100">{stats.total}</div>
          <div className="text-sm text-slate-500 dark:text-slate-400">Всего</div>
        </Card>
        <Card className="p-4 text-center bg-white dark:bg-slate-800">
          <div className="text-2xl font-bold text-blue-600 flex items-center justify-center gap-1">
            <TrendingUp className="w-5 h-5" />
            {stats.upcoming}
          </div>
          <div className="text-sm text-slate-500 dark:text-slate-400">Предстоящих</div>
        </Card>
        <Card className="p-4 text-center bg-white dark:bg-slate-800">
          <div className="text-2xl font-bold text-red-500 flex items-center justify-center gap-1">
            <AlertTriangle className="w-5 h-5" />
            {stats.overdue}
          </div>
          <div className="text-sm text-slate-500 dark:text-slate-400">Просрочено</div>
        </Card>
        <Card className="p-4 text-center bg-white dark:bg-slate-800">
          <div className="text-2xl font-bold text-amber-500">{stats.rescheduled}</div>
          <div className="text-sm text-slate-500 dark:text-slate-400">Перенесено</div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Week bar chart */}
        <Card className="p-4 bg-white dark:bg-slate-800">
          <h3 className="text-sm font-medium text-slate-600 dark:text-slate-300 mb-3 flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            Ближайшая неделя
          </h3>
          <div className="space-y-2">
            {stats.week.map((d, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-xs text-slate-500 dark:text-slate-400 w-16 text-right">{d.day}</span>
                <div className="flex-1 bg-slate-100 dark:bg-slate-700 rounded-full h-5 overflow-hidden">
                  <div
                    className="h-full bg-blue-500 dark:bg-blue-400 rounded-full transition-all duration-500 flex items-center justify-end pr-1"
                    style={{ width: `${Math.max((d.count / maxWeekCount) * 100, d.count > 0 ? 15 : 0)}%` }}
                  >
                    {d.count > 0 && (
                      <span className="text-xs text-white font-medium">{d.count}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          {stats.busiest_day && (
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
              Самый загруженный: {stats.busiest_day} ({stats.busiest_count} дедлайнов)
            </p>
          )}
        </Card>

        {/* Source breakdown */}
        <Card className="p-4 bg-white dark:bg-slate-800">
          <h3 className="text-sm font-medium text-slate-600 dark:text-slate-300 mb-3">По источникам</h3>
          <div className="space-y-3">
            {Object.entries(stats.by_source).map(([key, count]) => (
              <div key={key}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600 dark:text-slate-300">{SOURCE_LABELS[key] || key}</span>
                  <span className="text-slate-500 dark:text-slate-400">{count} ({Math.round((count / sourceTotal) * 100)}%)</span>
                </div>
                <div className="bg-slate-100 dark:bg-slate-700 rounded-full h-3 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(count / sourceTotal) * 100}%`,
                      backgroundColor: SOURCE_COLORS[key] || '#94a3b8',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default StatsPanel;
