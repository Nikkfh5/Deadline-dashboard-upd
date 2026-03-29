import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, AlertTriangle, Calendar, Flame, CheckCircle2 } from 'lucide-react';
import { Card } from './ui/card';
import { fetchStats, hasToken } from '../services/api';

const StatsPanel = ({ refreshKey = 0 }) => {
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
  }, [refreshKey]);

  if (!stats) return null;

  const maxWeekCount = Math.max(...stats.week.map(d => d.count), 1);

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
          <div className="text-2xl font-bold text-green-500 flex items-center justify-center gap-1">
            <CheckCircle2 className="w-5 h-5" />
            {stats.completed_this_week || 0}
          </div>
          <div className="text-sm text-slate-500 dark:text-slate-400">Выполнено за неделю</div>
        </Card>
      </div>

      {/* Motivation */}
      {(stats.completed_this_week || 0) > 0 && (
        <div className="mb-6 text-center">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {stats.completed_this_week >= 10 ? 'Невероятная продуктивность!' :
             stats.completed_this_week >= 5 ? 'Отличная работа, так держать!' :
             stats.completed_this_week >= 3 ? 'Хороший темп!' :
             'Начало положено!'}
          </p>
        </div>
      )}

      {/* Week chart + busiest day */}
      <Card className="p-4 bg-white dark:bg-slate-800 mb-4">
        <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1">
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

        {/* Busiest day — inline highlight */}
        {stats.busiest_day && (
          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 flex items-center gap-3">
            <Flame className="w-5 h-5 text-orange-500" />
            <span className="text-base text-slate-500 dark:text-slate-400">
              Самый загруженный день: <span className="font-bold text-orange-500">{stats.busiest_day}</span>
              <span className="text-slate-500 dark:text-slate-400"> ({stats.busiest_count} дедл.)</span>
            </span>
          </div>
        )}
      </Card>
    </div>
  );
};

export default StatsPanel;
