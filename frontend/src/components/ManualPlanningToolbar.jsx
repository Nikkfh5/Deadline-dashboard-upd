import React from 'react';
import { Eraser } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '../lib/utils';
import { MANUAL_DOT_COLORS } from '../lib/calendar-utils';

const ManualPlanningToolbar = ({ selectedDeadline, selectedColorIndex, onColorChange, onClear, dayCount }) => {
  if (!selectedDeadline) return null;

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm">
      <span className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate max-w-[140px]">
        {selectedDeadline.name}
      </span>

      <div className="flex items-center gap-1.5">
        {MANUAL_DOT_COLORS.map((color, idx) => (
          <button
            key={idx}
            onClick={() => onColorChange(idx)}
            className={cn(
              'w-5 h-5 rounded-full transition-all duration-150',
              color,
              idx === selectedColorIndex
                ? 'ring-2 ring-offset-2 ring-slate-400 dark:ring-slate-300 dark:ring-offset-slate-800 scale-110'
                : 'hover:scale-110 opacity-70 hover:opacity-100'
            )}
          />
        ))}
      </div>

      {dayCount > 0 && (
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {dayCount}d
        </span>
      )}

      <Button
        variant="ghost"
        size="sm"
        onClick={onClear}
        className="h-7 px-2 text-slate-500 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400"
      >
        <Eraser className="w-3.5 h-3.5" />
      </Button>

      <span className="text-xs text-slate-400 dark:text-slate-500 hidden sm:inline">
        Click days on calendar
      </span>
    </div>
  );
};

export default ManualPlanningToolbar;
