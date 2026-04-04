import React, { useMemo } from 'react';
import { DayPicker } from 'react-day-picker';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '../lib/utils';
import { buttonVariants } from './ui/button';
import {
  computeWorkPeriods,
  computeManualWorkPeriods,
  mergeWorkPeriods,
  computeDayOverlapMap,
  getDeadlinesForDay,
  DOT_COLORS,
  MANUAL_BG_COLORS,
} from '../lib/calendar-utils';
import { isSameDay, startOfDay, format } from 'date-fns';

const DeadlineCalendar = ({ deadlines, isPlanningMode, planningSubMode, manualPlan, onDayClick, manualActiveDeadlineId }) => {
  const autoWorkPeriods = useMemo(() => computeWorkPeriods(deadlines, manualPlan), [deadlines, manualPlan]);
  const manualWorkPeriods = useMemo(
    () => computeManualWorkPeriods(deadlines, manualPlan || {}),
    [deadlines, manualPlan]
  );
  const workPeriods = useMemo(
    () => mergeWorkPeriods(autoWorkPeriods, manualWorkPeriods),
    [autoWorkPeriods, manualWorkPeriods]
  );
  const overlapMap = useMemo(() => computeDayOverlapMap(workPeriods), [workPeriods]);

  // Set of manual entry IDs (includes m_ prefixed and plain manual-only)
  const manualIdSet = useMemo(() => {
    const set = new Set();
    workPeriods.forEach((_, id) => {
      if (id.startsWith('m_')) {
        set.add(id);
      } else if (manualPlan?.[id]?.days?.length > 0 && !workPeriods.has('m_' + id)) {
        set.add(id);
      }
    });
    return set;
  }, [workPeriods, manualPlan]);

  const isManualEntry = (id) => manualIdSet.has(id);

  const dueDates = useMemo(
    () => deadlines.map((d) => startOfDay(new Date(d.dueDate))),
    [deadlines]
  );

  // Custom day renderer
  const renderDay = (date) => {
    const dayKey = format(date, 'yyyy-MM-dd');
    const overlappingIds = overlapMap.get(dayKey) || [];
    const deadlinesForDay = getDeadlinesForDay(date, workPeriods);
    const isDueDate = dueDates.some((d) => isSameDay(d, date));
    const overlapCount = overlappingIds.length;

    // Background style based on work periods and overlaps
    let bgStyle = {};
    if (overlapCount === 1) {
      const { colorIndex } = deadlinesForDay[0];
      bgStyle = { backgroundColor: MANUAL_BG_COLORS[colorIndex] || MANUAL_BG_COLORS[0] };
    } else if (overlapCount === 2) {
      bgStyle = { backgroundColor: 'hsla(173, 58%, 39%, 0.22)' };
    } else if (overlapCount >= 3) {
      bgStyle = { backgroundColor: 'hsla(12, 76%, 61%, 0.32)' };
    }

    const isManualPainting = planningSubMode === 'manual' && manualActiveDeadlineId;
    const isManualDayForActive = isManualPainting && manualPlan?.[manualActiveDeadlineId]?.days?.includes(dayKey);

    const hasTooltip = deadlinesForDay.length > 0 || isDueDate;

    return (
      <div
        className={cn(
          'group/day relative flex flex-col items-center justify-center w-10 h-10 rounded-md transition-colors duration-150',
          overlapCount > 0 && 'ring-1 ring-inset ring-slate-200/50 dark:ring-slate-600/50',
          isDueDate && 'font-bold',
          isManualPainting && 'cursor-pointer hover:ring-2 hover:ring-blue-300 dark:hover:ring-blue-600',
          isManualDayForActive && 'ring-2 ring-blue-400 dark:ring-blue-500'
        )}
        style={bgStyle}
        onClick={isManualPainting ? (e) => { e.stopPropagation(); onDayClick?.(dayKey); } : undefined}
      >
        <span
          className={cn(
            'text-sm leading-none z-10',
            isDueDate && 'text-red-600 dark:text-red-400 font-black'
          )}
        >
          {date.getDate()}
        </span>

        {/* Colored dots for each deadline */}
        {deadlinesForDay.length > 0 && (
          <div className="absolute bottom-0.5 flex gap-0.5 items-center">
            {deadlinesForDay.slice(0, 3).map(({ deadlineId, colorIndex }) => (
              <span
                key={deadlineId}
                className={cn(
                  'w-1.5 h-1.5 rounded-full',
                  DOT_COLORS[colorIndex] || DOT_COLORS[0]
                )}
              />
            ))}
            {deadlinesForDay.length > 3 && (
              <span className="text-[8px] text-slate-500 dark:text-slate-400 leading-none">
                +{deadlinesForDay.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Due date marker */}
        {isDueDate && !deadlinesForDay.length && (
          <div className="absolute bottom-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 block" />
          </div>
        )}

        {/* CSS hover tooltip — no portal, no flicker */}
        {hasTooltip && (
          <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 pb-1 z-50 opacity-0 group-hover/day:opacity-100 transition-opacity duration-150 delay-150 group-hover/day:delay-0">
            <div className="max-w-xs rounded-md px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-lg whitespace-nowrap">
              <div className="space-y-1">
                {isDueDate && (
                  <div className="text-xs font-semibold text-red-600 dark:text-red-400">
                    Deadline day
                  </div>
                )}
                {deadlinesForDay.map(({ deadlineId, colorIndex, deadline }) => {
                  const isManual = isManualEntry(deadlineId);
                  const sourceId = deadlineId.startsWith('m_') ? deadlineId.slice(2) : deadlineId;
                  return (
                    <div key={deadlineId} className="flex items-center gap-2 text-xs">
                      <span
                        className={cn('w-2 h-2 rounded-full shrink-0', DOT_COLORS[colorIndex] || DOT_COLORS[0])}
                      />
                      <span className="text-slate-700 dark:text-slate-300 font-medium">
                        {deadline.name}
                      </span>
                      <span className="text-slate-500 dark:text-slate-400">
                        {isManual ? `${manualPlan[sourceId]?.days?.length || 0}d manual` : `${deadline.daysNeeded}d`}
                      </span>
                    </div>
                  );
                })}
                {overlapCount >= 2 && (
                  <div className="text-[10px] text-amber-600 dark:text-amber-400 font-medium pt-0.5 border-t border-slate-100 dark:border-slate-700">
                    {overlapCount} tasks overlap
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Legend
  const activeWorkPeriods = useMemo(() => {
    const items = [];
    workPeriods.forEach(({ colorIndex, deadline }, deadlineId) => {
      const realId = deadlineId.startsWith('m_') ? deadlineId.slice(2) : deadlineId;
      const isManual = deadlineId.startsWith('m_') || (manualPlan?.[realId]?.days?.length > 0 && !workPeriods.has('m_' + realId));
      const manual = manualPlan?.[realId];
      items.push({
        name: deadline.name,
        colorIndex,
        daysNeeded: deadline.daysNeeded,
        isManual,
        manualDayCount: isManual ? (manual?.days?.length || 0) : 0,
      });
    });
    return items;
  }, [workPeriods, manualPlan]);

  const numberOfMonths = isPlanningMode ? 2 : 1;

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex flex-col md:flex-row items-start gap-6">
        <DayPicker
          numberOfMonths={numberOfMonths}
          showOutsideDays
          className={cn(
            'p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm',
            'transition-all duration-300'
          )}
          classNames={{
            months: 'flex flex-col sm:flex-row gap-4',
            month: 'space-y-3',
            caption: 'flex justify-center pt-1 relative items-center',
            caption_label: 'text-sm font-semibold text-slate-700 dark:text-slate-200',
            nav: 'space-x-1 flex items-center',
            nav_button: cn(
              buttonVariants({ variant: 'outline' }),
              'h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100 dark:border-slate-600'
            ),
            nav_button_previous: 'absolute left-1',
            nav_button_next: 'absolute right-1',
            table: 'w-full border-collapse',
            head_row: 'flex',
            head_cell:
              'text-slate-500 dark:text-slate-400 rounded-md w-10 font-medium text-[0.75rem] uppercase tracking-wider',
            row: 'flex w-full mt-1',
            cell: 'relative p-0 text-center text-sm overflow-visible',
            day: 'h-10 w-10 p-0 font-normal rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors overflow-visible',
            day_selected: 'bg-slate-200 dark:bg-slate-600',
            day_today:
              'bg-slate-100 dark:bg-slate-700/50 text-slate-900 dark:text-slate-100 font-semibold ring-1 ring-slate-300 dark:ring-slate-600',
            day_outside: 'text-slate-300 dark:text-slate-600 opacity-50',
            day_disabled: 'text-slate-300 dark:text-slate-600 opacity-30',
          }}
          components={{
            IconLeft: (props) => <ChevronLeft className="h-4 w-4" {...props} />,
            IconRight: (props) => <ChevronRight className="h-4 w-4" {...props} />,
            DayContent: ({ date }) => renderDay(date),
          }}
        />

        {/* Legend */}
        {activeWorkPeriods.length > 0 && (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-4 min-w-[180px]">
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
              Work Periods
            </h4>
            <div className="space-y-2">
              {activeWorkPeriods.map(({ name, colorIndex, daysNeeded, isManual, manualDayCount }, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span
                      className={cn('w-3 h-3 rounded-sm shrink-0', DOT_COLORS[colorIndex] || DOT_COLORS[0])}
                    />
                    <span className="text-xs text-slate-700 dark:text-slate-300 font-medium truncate">
                      {name}
                    </span>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 ml-auto whitespace-nowrap">
                      {isManual ? `${manualDayCount}d` : `${daysNeeded}d`}
                    </span>
                  </div>
              ))}
            </div>

            {/* Overlap legend */}
            <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700 space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: 'hsla(173, 58%, 39%, 0.22)' }} />
                <span className="text-[10px] text-slate-500 dark:text-slate-400">2 tasks overlap</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: 'hsla(12, 76%, 61%, 0.32)' }} />
                <span className="text-[10px] text-slate-500 dark:text-slate-400">3+ tasks overlap</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0 ml-0.5" />
                <span className="text-[10px] text-slate-500 dark:text-slate-400 ml-0.5">Deadline day</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DeadlineCalendar;
